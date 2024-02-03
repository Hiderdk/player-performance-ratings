import logging
from dataclasses import dataclass
from typing import Optional, Union

import pandas as pd
from sklearn.preprocessing import StandardScaler

from player_performance_ratings.predictor.transformer import SkLearnTransformerWrapper
from player_performance_ratings.transformation.pre_transformers import \
    SymmetricDistributionTransformer, MinMaxTransformer, GroupByTransformer, NetOverPredictedTransformer

from player_performance_ratings import ColumnNames

from player_performance_ratings.transformation.base_transformer import BaseTransformer


@dataclass
class ColumnWeight:
    name: str
    weight: float
    lower_is_better: bool = False

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError("Weight must be positive")
        if self.weight > 1:
            raise ValueError("Weight must be less than 1")


def auto_create_pre_performance_transformations(
        pre_transformations: list[BaseTransformer],
        column_weights: list[list[ColumnWeight]],
        column_names: list[ColumnNames],
        net_predict_transformers: Optional[list[NetOverPredictedTransformer]] = None
) -> list[BaseTransformer]:
    """
    Creates a list of transformers that ensure the performance column is generated in a way that makes sense for the rating model.
    Ensures columns aren't too skewed, scales them to similar ranges, ensure values are between 0 and 1,
    and then weights them according to the column_weights.
    """

    if not isinstance(column_weights[0], list):
        column_weights = [column_weights]

    all_feature_names = []
    for col_weights in column_weights:
        for col_weight in col_weights:
            if col_weight.name not in all_feature_names:
                all_feature_names.append(col_weight.name)

    contains_position = True if any([c.position is not None for c in column_names]) else False
    contains_not_position = True if any([c.position is None for c in column_names]) else False

    not_transformed_features = []
    transformed_features = []
    if contains_position:
        for idx, col_weights in enumerate(column_weights):
            feature_names = []
            if column_names[idx].position is None:
                granularity = []
            else:
                granularity = [column_names[idx].position]

            for column_weight in col_weights:
                feature = column_weight.name
                feature_names.append(feature)


            if net_predict_transformers is not None:
                not_transformed_features = feature_names.copy()
                feats = []
                for idx in range(len(net_predict_transformers)):

                    if net_predict_transformers[idx]._predictor.target in not_transformed_features:
                        not_transformed_features.remove(net_predict_transformers[idx]._predictor.target)

                    pre_transformations.append(net_predict_transformers[idx])
                    feats += net_predict_transformers[idx].features_out

                distribution_transformer = SymmetricDistributionTransformer(
                    features=feats,
                    granularity=granularity)

                pre_transformations.append(distribution_transformer)
                transformed_features += [f for f in distribution_transformer.features_out if f not in transformed_features]

            else:
                feats = []

                for col in column_weights[idx]:
                    if col.name not in feats:
                        feats.append(col.name)

                if column_names[idx].position is not None:
                    predict_transformer = GroupByTransformer(features=feats, agg_func='mean',
                                                             granularity=[column_names[idx].position],
                                                             prefix="")

                    default_net_predict_transformer = NetOverPredictedTransformer(
                        predict_transformer=predict_transformer,
                        prefix="",
                        features=[predict_transformer.features_out],
                    )
                    pre_transformations.append(default_net_predict_transformer)
                    distribution_transformer = SymmetricDistributionTransformer(
                        features=feature_names,
                        granularity=granularity,
                        prefix="")
                    pre_transformations.append(distribution_transformer)

                else:
                    not_transformed_features += [c.name for c in column_weights[idx]]

                transformed_features += [f for f in distribution_transformer.features_out if f not in transformed_features]
        #  for idx2, col_weight in enumerate(column_weights[idx]):
        #        column_weights[idx][
        #           idx2].name = distribution_transformer.prefix + position_predicted_transformer.prefix + col_weight.name

        all_feature_names = not_transformed_features + transformed_features
    else:
        not_transformed_features = all_feature_names

    if contains_not_position and net_predict_transformers is None:
        distribution_transformer = SymmetricDistributionTransformer(features=not_transformed_features)
   #     pre_transformations.append(distribution_transformer)

 #   pre_transformations.append(
  #      SkLearnTransformerWrapper(transformer=StandardScaler(), features=all_feature_names))

  #  pre_transformations.append(MinMaxTransformer(features=all_feature_names))
    return pre_transformations


class PerformancesGenerator():

    def __init__(self,
                 column_weights: Union[list[list[ColumnWeight]], list[ColumnWeight]],
                 column_names: Union[list[ColumnNames], ColumnNames],
                 pre_transformations: Optional[list[BaseTransformer]] = None,
                 net_predict_transformers: Optional[list[NetOverPredictedTransformer]] = None,
                 ):
        self.column_names = column_names if isinstance(column_names, list) else [column_names]
        self.column_weights = column_weights if isinstance(column_weights[0], list) else [column_weights]
        self.net_predict_transformers = net_predict_transformers

        self.pre_transformations = pre_transformations or []
        self.pre_transformations = auto_create_pre_performance_transformations(
            pre_transformations=self.pre_transformations, column_weights=column_weights,
            column_names=self.column_names, net_predict_transformers=self.net_predict_transformers)

    def generate(self, df):

        if self.pre_transformations:
            for pre_transformation in self.pre_transformations:
                df = pre_transformation.fit_transform(df)

        for idx, col_name in enumerate(self.column_names):
            if self.pre_transformations:
                max_idx = len(self.pre_transformations) - 1
                column_weighs_mapping = {col_weight.name: self.pre_transformations[max_idx].features_out[idx] for
                                         idx, col_weight in enumerate(self.column_weights[idx])}
            else:
                column_weighs_mapping = None

            df[col_name.performance] = self._weight_columns(df=df, col_name=col_name,
                                                            col_weights=self.column_weights[idx],
                                                            column_weighs_mapping=column_weighs_mapping)

            if df[col_name.performance].isnull().any():
                logging.error(
                    f"df[{col_name.performance}] contains nan values. Make sure all column_names used in column_weights are imputed beforehand")
                raise ValueError("performance contains nan values")

        return df

    def _weight_columns(self,
                        df: pd.DataFrame,
                        col_name: ColumnNames,
                        col_weights: list[ColumnWeight],
                        column_weighs_mapping: dict[str, str]
                        ) -> pd.DataFrame:
        df = df.copy()
        df[f"__{col_name.performance}"] = 0

        df['sum_cols_weights'] = 0
        for column_weight in col_weights:
            df[f'weight__{column_weight.name}'] = column_weight.weight
            df.loc[df[column_weight.name].isna(), f'weight__{column_weight.name}'] = 0
            df.loc[df[column_weight.name].isna(), column_weight.name] = 0
            df['sum_cols_weights'] = df['sum_cols_weights'] + df[f'weight__{column_weight.name}']

        drop_cols = ['sum_cols_weights', f"__{col_name.performance}"]
        for column_weight in col_weights:
            df[f'weight__{column_weight.name}'] / df['sum_cols_weights']
            drop_cols.append(f'weight__{column_weight.name}')

        for column_weight in col_weights:

            if column_weighs_mapping:
                feature_name = column_weighs_mapping[column_weight.name]
            else:
                feature_name = column_weight.name

            if column_weight.lower_is_better:
                df[f"__{col_name.performance}"] += df[f'weight__{column_weight.name}'] * (
                        1 - df[feature_name])
            else:
                df[f"__{col_name.performance}"] += df[f'weight__{column_weight.name}'] * df[feature_name]

        return df[f"__{col_name.performance}"]

    @property
    def features_out(self) -> list[str]:
        return [c.performance for c in self.column_names]
