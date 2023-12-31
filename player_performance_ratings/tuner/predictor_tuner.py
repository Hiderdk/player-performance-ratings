import copy
import inspect
from typing import Optional

import optuna
import pandas as pd
import pendulum
from optuna.samplers import TPESampler
from optuna.trial import BaseTrial

from player_performance_ratings.cross_validator.cross_validator import CrossValidator
from player_performance_ratings.tuner.match_predictor_factory import PipelineFactory

from player_performance_ratings.predictor import BaseMLWrapper

from player_performance_ratings.tuner.utils import ParameterSearchRange, add_params_from_search_range


class PredictorTuner():

    def __init__(self,
                 search_ranges: list[ParameterSearchRange],
                 date_column_name: str,
                 train_split_date: Optional[pendulum.datetime] = None,
                 default_params: Optional[dict] = None,
                 estimator_subclass_level: int = 0,
                 n_trials: int = 30
                 ):
        self.search_ranges = search_ranges
        self.date_column_name = date_column_name
        self.train_split_date = train_split_date
        self.default_params = default_params or {}
        self.estimator_subclass_level = estimator_subclass_level
        self.n_trials = n_trials

    def tune(self, df: pd.DataFrame,
             pipeline_factory: PipelineFactory, cross_validator: CrossValidator) -> BaseMLWrapper:

        if not self.train_split_date:
            self.train_split_date = df.iloc[int(len(df) / 1.3)][self.date_column_name]

        def objective(trial: BaseTrial, df: pd.DataFrame) -> float:

            predictor = pipeline_factory.predictor

            if self.estimator_subclass_level == 0:
                param_names = list(
                    inspect.signature(predictor.estimator.__class__.__init__).parameters.keys())[1:]
                params = {attr: getattr(predictor.estimator, attr) for attr in param_names if attr != 'kwargs'}
                if '_other_params' in predictor.estimator.__dict__:
                    params.update(predictor.estimator._other_params)
            elif self.estimator_subclass_level == 1:
                param_names = list(
                    inspect.signature(predictor.estimator.estimator.__class__.__init__).parameters.keys())[1:]
                params = {attr: getattr(predictor.estimator.estimator, attr) for attr in param_names if
                          attr != 'kwargs'}
                if '_other_params' in predictor.estimator.estimator.__dict__:
                    params.update(predictor.estimator.estimator._other_params)
            elif self.estimator_subclass_level == 2:
                param_names = list(
                    inspect.signature(predictor.estimator.estimator.estimator.__class__.__init__).parameters.keys())[1:]
                params = {attr: getattr(predictor.estimator.estimator.estimator, attr) for attr in param_names if
                          attr != 'kwargs'}
                if '_other_params' in predictor.estimator.estimator.estimator.__dict__:
                    params.update(predictor.estimator.estimator.estimator._other_params)

            else:
                raise ValueError(
                    f"estimator_subclass_level can't be higher than 2, got {self.estimator_subclass_level}")

            params = add_params_from_search_range(params=params,
                                                  trial=trial,
                                                  parameter_search_range=self.search_ranges)
            for param, value in self.default_params.items():
                params[param] = value

            predictor = copy.deepcopy(pipeline_factory.predictor)
            for param in params:
                if self.estimator_subclass_level == 1:
                    setattr(predictor.estimator.estimator, param, params[param])
                elif self.estimator_subclass_level == 2:
                    setattr(predictor.estimator.estimator.estimator, param, params[param])
                elif self.estimator_subclass_level > 2:
                    raise ValueError(
                        f"estimator_subclass_level can't be higher than 2, got {self.estimator_subclass_level}")
                else:
                    setattr(predictor.estimator, param, params[param])

            pipeline = pipeline_factory.create(predictor=predictor)
            return pipeline.cross_validate_score(df=df, create_performance=False, create_rating_features=False,
                                                                 cross_validator=cross_validator)

        direction = "minimize"
        study_name = "optuna_study"
        optuna_seed = 12
        sampler = TPESampler(seed=optuna_seed)
        study = optuna.create_study(direction=direction, study_name=study_name, sampler=sampler)
        callbacks = []
        study.optimize(lambda trial: objective(trial, df), n_trials=self.n_trials, callbacks=callbacks)
        best_estimator_params = study.best_params
        other_predictor_params = list(
            inspect.signature(pipeline_factory.predictor.__class__.__init__).parameters.keys())[1:]

        if self.estimator_subclass_level > 0:
            if self.estimator_subclass_level == 1:
                best_estimator_params.update(pipeline_factory.predictor.estimator.estimator._other_params)
            elif self.estimator_subclass_level == 2:
                best_estimator_params.update(
                    pipeline_factory.predictor.estimator.estimator.estimator._other_params)

        else:
            if '_other_params' in pipeline_factory.predictor.estimator.__dict__:
                best_estimator_params.update(pipeline_factory.predictor.estimator._other_params)

        other_predictor_params = {attr: getattr(pipeline_factory.predictor, attr) for attr in
                                  other_predictor_params if attr not in ('estimator')}

        predictor_class = pipeline_factory.predictor.__class__
        if self.estimator_subclass_level == 1:

            potential_parent_names = list(
                inspect.signature(
                    pipeline_factory.predictor.estimator.__class__.__init__).parameters.keys())[1:]
            other_parent_params = {attr: getattr(pipeline_factory.predictor.estimator, attr) for attr
                                   in
                                   potential_parent_names if attr != 'estimator'}

            estimator_class = pipeline_factory.predictor.estimator.estimator.__class__
            parent_estimator_class = pipeline_factory.predictor.estimator.__class__
            parent_estimator = parent_estimator_class(estimator=estimator_class(**best_estimator_params),
                                                      **other_parent_params)
            return predictor_class(estimator=parent_estimator, **other_predictor_params)
        elif self.estimator_subclass_level == 2:
            potential_parent_names = list(
                inspect.signature(
                    pipeline_factory.predictor.estimator.estimator.__class__.__init__).parameters.keys())[1:]
            other_parent_params = {attr: getattr(pipeline_factory.predictor.estimator.estimator, attr) for attr
                                   in
                                   potential_parent_names if attr != 'estimator'}
            estimator_class = pipeline_factory.predictor.estimator.estimator.estimator.__class__
            parent_estimator_class = pipeline_factory.predictor.estimator.estimator.__class__
            parent_estimator = parent_estimator_class(estimator=estimator_class(**best_estimator_params),
                                                      **other_parent_params)

            parent_parent_estimator_class = pipeline_factory.predictor.estimator.__class__
            parent_parent_estimator = parent_parent_estimator_class(estimator=parent_estimator)
            return predictor_class(estimator=parent_parent_estimator, **other_predictor_params)

        elif self.estimator_subclass_level == 0:

            estimator_class = pipeline_factory.predictor.estimator.__class__
            return predictor_class(estimator=estimator_class(**best_estimator_params), **other_predictor_params)

        else:
            raise ValueError(f"estimator_subclass_level can't be higher than 2, got {self.estimator_subclass_level}")
