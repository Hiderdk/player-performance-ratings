from typing import Optional

import pandas as pd
from sklearn.linear_model import LogisticRegression

from player_performance_ratings.consts import PredictColumnNames

from player_performance_ratings.data_structures import ColumnNames
from player_performance_ratings.predictor.estimators.base_estimator import BaseMLWrapper


class SkLearnGameTeamPredictor(BaseMLWrapper):

    def __init__(self,
                 game_id_colum: str,
                 team_id_column: str,
                 features: list[str],
                 weight_column: Optional[str] = None,
                 target: Optional[str] = PredictColumnNames.TARGET,
                 model: Optional = None,
                 multiclassifier: bool = False,
                 pred_column: Optional[str] = "prob",
                 ):
        """
        Wrapper for sklearn models that predicts game results.

        The GameTeam Predictor is intended to transform predictions from a lower granularity into a GameTeam level.
        So if input data is at game-player, data is converted to game_team before being trained
        Similar concept if it is at a granularity below game level.

        The weight_column makes it possible to weight certain rows more than others.
        For instance, if data is on game-player level and the participation rate of players is not equal -->
         setting participation_weight equal to weight_column will the feature values of the players with high participation_rates have higher weight before aggregating to game_team.


        :param game_id_colum:
        :param team_id_column:
        :param features:
        :param weight_column:
        :param target:
        :param model:
        :param multiclassifier:
        :param pred_column:
        """

        self.weight_column = weight_column
        self.game_id_colum = game_id_colum
        self.team_id_column = team_id_column
        self.features = features
        self._target = target
        self.multiclassifier = multiclassifier
        super().__init__(target=self._target, pred_column=pred_column, model=model or LogisticRegression())

    def train(self, df: pd.DataFrame) -> None:
        grouped = self._create_grouped(df)
        self.model.fit(grouped[self.features], grouped[self._target])

    def add_prediction(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds prediction to df

        :param df:
        :return: Input df with prediction column
        """

        grouped = self._create_grouped(df)

        if self.multiclassifier:
            grouped[self._pred_column] = self.model.predict_proba(grouped[self.features]).tolist()
        else:
            grouped[self._pred_column] = self.model.predict_proba(grouped[self.features])[:, 1]

        if self.pred_column in df.columns:
            df = df.drop(columns=[self.pred_column])

        df = df.merge(grouped[[self.game_id_colum, self.team_id_column] + [self._pred_column]],
                      on=[self.game_id_colum, self.team_id_column])

        return df

    def _create_grouped(self, df: pd.DataFrame) -> pd.DataFrame:

        if df[self._target].dtype == 'object':
            df.loc[:, self._target] = df[self._target].astype('int')

        if self.weight_column:
            for feature in self.features:
                df = df.assign(**{feature: df[self.weight_column] * df[feature]})


        grouped = df.groupby([self.game_id_colum, self.team_id_column]).agg({
            **{feature: 'sum' for feature in self.features},
            self._target: 'mean',
            self.weight_column: 'sum',
        }).reset_index()
        for feature in self.features:
            grouped[feature] = grouped[feature] / grouped[self.weight_column]

        grouped.drop(columns=[self.weight_column],inplace=True)
        grouped[self._target] = grouped[self._target].astype('int')
        return grouped


class SKLearnClassifierWrapper(BaseMLWrapper):

    def __init__(self,
                 features: list[str],
                 target: Optional[str] = PredictColumnNames.TARGET,
                 model: Optional = None,
                 multiclassifier: bool = False,
                 pred_column: Optional[str] = "prob",
                 column_names: Optional[ColumnNames] = None
                 ):
        self.features = features
        self._target = target
        self.multiclassifier = multiclassifier
        self.column_names = column_names

        super().__init__(target=self._target, pred_column=pred_column, model=model or LogisticRegression())

    def train(self, df: pd.DataFrame) -> None:
        self.model.fit(df[self.features], df[self._target])

    def add_prediction(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if self.multiclassifier:
            df[self._pred_column] = self.model.predict_proba(df[self.features]).tolist()
        else:
            df[self._pred_column] = self.model.predict_proba(df[self.features])[:, 1]
        return df