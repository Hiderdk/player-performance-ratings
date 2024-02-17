from unittest import mock

import pandas as pd
from deepdiff import DeepDiff

from player_performance_ratings import PipelineFactory
from player_performance_ratings.predictor import Predictor
from sklearn.linear_model import LogisticRegression


from player_performance_ratings.tuner.predictor_tuner import PredictorTuner
from player_performance_ratings.tuner.utils import ParameterSearchRange


def test_predictor_tuner():
    df = pd.DataFrame(
        {
            "game_id": [1, 1, 2, 2],
            "team_id": [1, 2, 1, 2],
            "player_id": [1, 2, 1, 2],
            "won": [1, 0, 0, 1],
            "rating_difference": [100, -100, -20, 20],
            "start_date": ["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-02"],
            "__target": [1, 0, 0, 1]
        }
    )

    predictor_factory = PipelineFactory(
        predictor=Predictor(estimator=LogisticRegression(), estimator_features=["rating_difference"], target="__target"),
    )

    search_ranges = [
        ParameterSearchRange(
            name='C',
            type='categorical',
            choices=[1.0, 0.5]
        )
    ]

    predictor_tuner = PredictorTuner(search_ranges=search_ranges, n_trials=2)
    cross_validator = mock.Mock()
    cross_validator.cross_validation_score.side_effect = [0.5, 0.3]
    best_predictor = predictor_tuner.tune(df=df, cross_validator=cross_validator,
                                          pipeline_factory=predictor_factory)

    expected_best_predictor = Predictor(estimator=LogisticRegression(C=0.5), estimator_features=["rating_difference"],
                                        target="__target")

    diff = DeepDiff(best_predictor.estimator, expected_best_predictor.estimator)
    assert diff == {}

    assert expected_best_predictor.estimator_features == best_predictor.estimator_features
    assert expected_best_predictor.target == best_predictor.target
