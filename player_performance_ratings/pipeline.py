from typing import List, Optional, Union

import pandas as pd

from player_performance_ratings.cross_validator.cross_validator import CrossValidator
from player_performance_ratings.ratings import PerformancesGenerator, ColumnWeight

from player_performance_ratings.consts import PredictColumnNames
from player_performance_ratings.predictor import BaseMLWrapper

from player_performance_ratings.data_structures import Match
from player_performance_ratings.ratings.league_identifier import LeagueIdentifier
from player_performance_ratings.ratings.match_generator import convert_df_to_matches
from player_performance_ratings.ratings.rating_generator import RatingGenerator

from player_performance_ratings.transformation.base_transformer import BasePostTransformer



class Pipeline():

    def __init__(self,
                 predictor: BaseMLWrapper,
                 rating_generators: Optional[Union[RatingGenerator, list[RatingGenerator]]] = None,
                 performances_generator: Optional[PerformancesGenerator] = None,
                 post_rating_transformers: Optional[List[BasePostTransformer]] = None,
                 column_weights: Optional[Union[list[list[ColumnWeight]], list[ColumnWeight]]] = None,
                 keep_features: bool = False,
                 ):

        """

        :param column_names:
        :param rating_generators:
        A single or a list of RatingGenerators.

        :param performances_generator:
        An optional transformer class that take place in order to convert one or multiple column names into the performance value that is used by the rating model

        :param post_rating_transformers:
            After rating-generation, additional feature engineering can be performed.

        :param predictor:
            The object which trains and returns predictions. Defaults to LGBMClassifier

        :param estimator: Sklearn-like estimator. If predictor is set, estimator will be ignored.
         Because it sometimes can be tricky to identify the names of all the features that must be passed to predictor, the user can decide to only pass in an estimator.
         The features will then be automatically identified based on features_created from the rating_generator, post_rating_transformers and other_features.
         If predictor is set, estimator will be ignored

        :param other_features: If estimator is set and predictor is not,
        other_features allows the user to pass in additional features that are not created by the rating_generator or post_rating_transformers to the predictor.

        :param other_categorical_features: Which of the other_features are categorical.
        It is not required to duplicate the categorical features in other_features and other_categorical_features.
        Simply passing an a categorical_feature in categorical_features will add it to other_features if it doesn't already exist.

        :param train_split_date:
            Date threshold which defines which periods to train the predictor on

        :param date_column_name:
            If rating_generators are not defined and train_split_date is used, then train_column_name must be set.

        :param use_auto_create_performance_calculator:
            If true, the pre_rating_transformers will be automatically generated to ensure the performance-value is done according to good practices.
            For new users, this is recommended.

        :param column_weights:
            If auto_create_pre_transformers is True, column_weights must be set.
            It is generally used when multiple columns are used to calculate ratings and the columns need to be weighted when converting it to a performance_value.
            Even if only 1  feature is used but auto_create_pre_transformers is used,
             then it must still be created in order for auto_create_pre_transformers to know which columns needs to be transformed.

        """

        self._estimator_features = []
        self.rating_generators: list[RatingGenerator] = rating_generators if isinstance(rating_generators, list) else [
            rating_generators]
        if rating_generators is None:
            self.rating_generators: list[RatingGenerator] = []

        self.post_rating_transformers = post_rating_transformers or []

        for c in self.post_rating_transformers:
            self._estimator_features += c.features_out
        for rating_idx, c in enumerate(self.rating_generators):
            for rating_feature in c.features_out:
                if len(self.rating_generators) > 1:
                    rating_feature_str = rating_feature + str(rating_idx)
                else:
                    rating_feature_str = rating_feature
                self._estimator_features.append(rating_feature_str)

        self.column_weights = column_weights
        if self.column_weights and isinstance(self.column_weights[0], ColumnWeight):
            self.column_weights = [self.column_weights]

        self.performances_generator = performances_generator
        self.keep_features = keep_features


        self.predictor = predictor

        self.predictor.set_target(PredictColumnNames.TARGET)

    def cross_validate_score(self,
                             df: pd.DataFrame,
                             cross_validator: CrossValidator,
                             matches: Optional[list[Match]] = None,
                             create_performance: bool = True,
                             create_rating_features: bool = True) -> float:


        if create_performance:
            df = self._add_performance(df=df)
        if create_rating_features:
            df = self._add_rating(matches=matches, df=df, store_ratings=False)

        validation_df = cross_validator.generate_validation_df(df=df, predictor=self.predictor,
                                                               post_transformers=self.post_rating_transformers,
                                                               estimator_features=self._estimator_features)
        return cross_validator.cross_validation_score(validation_df=validation_df)

    def generate_cross_validate_df(self,
                                   df: pd.DataFrame,
                                   cross_validator: CrossValidator,
                                   matches: Optional[list[Match]] = None,
                                   create_performance: bool = True,
                                   create_rating_features: bool = True) -> pd.DataFrame:

        if self.predictor.target not in df.columns:
            raise ValueError(f"Target {self.predictor.target } not in df columns. Target always needs to be set equal to {PredictColumnNames.TARGET}")

        if create_performance:
            df = self._add_performance(df=df)
        if create_rating_features:
            df = self._add_rating(matches=matches, df=df, store_ratings=False)

        return cross_validator.generate_validation_df(df=df, predictor=self.predictor,
                                                      post_transformers=self.post_rating_transformers,
                                                      estimator_features=self._estimator_features)

    def generate_historical(self, df: pd.DataFrame, matches: Optional[Union[list[Match], list[list[Match]]]] = None,
                            store_ratings: bool = True) -> pd.DataFrame:

        if self.predictor.target not in df.columns:
            raise ValueError(f"Target {self.predictor.target } not in df columns. Target always needs to be set equal to {PredictColumnNames.TARGET}")

        ori_cols = df.columns.tolist()
        df = self._add_performance(df=df)
        df = self._add_rating(matches=matches, df=df, store_ratings=store_ratings)

        for post_rating_transformer in self.post_rating_transformers:
            df = post_rating_transformer.fit_transform(df)

        self.predictor.train(df, estimator_features=self._estimator_features)
        df = self.predictor.add_prediction(df)
        if not self.keep_features:
            df = df[ori_cols + [self.predictor.pred_column]]

        return df

    def _add_performance(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if self.predictor.pred_column in df.columns:
            raise ValueError(
                f"Predictor column {self.predictor.pred_column} already in df columns. Remove or rename before generating predictions")


        elif self.performances_generator:
            df = self.performances_generator.generate(df)

        if self.predictor.target not in df.columns:
            raise ValueError(
                f"Target {self.predictor.target} not in df columns. Target always needs to be set equal to {PredictColumnNames.TARGET}")

        return df

    def _add_rating(self, matches: Optional[list[Match]], df: pd.DataFrame, store_ratings: bool = True):

        if matches:
            if isinstance(matches[0], Match):
                matches = [matches for _ in self.rating_generators]

        for rating_idx, rating_generator in enumerate(self.rating_generators):

            rating_column_names = rating_generator.column_names

            if matches is None:
                rating_matches = convert_df_to_matches(column_names=rating_column_names, df=df,
                                                       league_identifier=LeagueIdentifier())
            else:
                rating_matches = matches[rating_idx]

            if store_ratings:
                match_ratings = rating_generator.generate_historical(matches=rating_matches, df=df)
            else:
                match_ratings = rating_generator.generate_historical(matches=rating_matches)
            for rating_feature, values in match_ratings.items():
                if len(self.rating_generators) > 1:
                    rating_feature_str = rating_feature + str(rating_idx)
                else:
                    rating_feature_str = rating_feature
                df[rating_feature_str] = values

        return df

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        ori_cols = df.columns.tolist()
        for rating_idx, rating_generator in enumerate(self.rating_generators):
            rating_column_names = rating_generator.column_names

            matches = convert_df_to_matches(column_names=rating_column_names, df=df,
                                            league_identifier=LeagueIdentifier())

            match_ratings = rating_generator.generate_future(matches, df=df)
            for rating_feature in rating_generator.features_out:
                values = match_ratings[rating_feature]

                if len(self.rating_generators) > 1:
                    rating_feature_str = rating_feature + str(rating_idx)
                else:
                    rating_feature_str = rating_feature
                df[rating_feature_str] = values

        for post_rating_transformer in self.post_rating_transformers:
            df = post_rating_transformer.transform(df)

        df = self.predictor.add_prediction(df)

        if not self.keep_features:
            df = df[ori_cols + [self.predictor.pred_column]]
        return df

    @property
    def classes_(self) -> Optional[list[str]]:
        if 'classes_' not in dir(self.predictor.estimator):
            return None
        return self.predictor.estimator.classes_
