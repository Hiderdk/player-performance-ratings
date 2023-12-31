import logging
from dataclasses import dataclass, field
from typing import Literal, Optional, Union, Any

from optuna.trial import BaseTrial

@dataclass
class ParameterSearchRange:
    name: str
    type: Literal["uniform", "loguniform", "int", "categorical", "discrete_uniform"]
    low: Optional[Union[float, int]] = None
    high: Optional[Union[float, int]] = None
    choices: Optional[list[Any]] = None
    custom_params: dict[str, Any] = field(default_factory=dict)


def add_params_from_search_range(trial: BaseTrial, parameter_search_range: list[ParameterSearchRange],
                                 params: dict) -> dict:
    for config in parameter_search_range:
        if config.type == "uniform":
            params[config.name] = trial.suggest_uniform(config.name, low=config.low, high=config.high)
        elif config.type == "loguniform":
            params[config.name] = trial.suggest_loguniform(config.name, low=config.low, high=config.high)
        elif config.type == "int":
            params[config.name] = trial.suggest_int(config.name, low=config.low, high=config.high)
        elif config.type == "categorical":
            params[config.name] = trial.suggest_categorical(config.name, config.choices)
        else:
            logging.warning(f"Unknown type {config.type} for parameter {config.name}")

    return params

def get_default_lgbm_classifier_search_range_by_learning_rate(learning_rate: float) -> list[ParameterSearchRange]:
    min_n_estimators = min(1 / learning_rate * 7, 1000)

    return [
        ParameterSearchRange(
            name='n_estimators',
            type='int',
            low=min_n_estimators,
            high=min_n_estimators*6,
        ),
        ParameterSearchRange(
            name='num_leaves',
            type='int',
            low=10,
            high=100,
        ),
        ParameterSearchRange(
            name='max_depth',
            type='int',
            low=2,
            high=7,
        ),
        ParameterSearchRange(
            name='min_child_samples',
            type='int',
            low=2,
            high=200,
        ),
        ParameterSearchRange(
            name='reg_alpha',
            type='uniform',
            low=0,
            high=5,
        ),
    ]


def get_default_lgbm_regressor_search_range_by_learning_rate(learning_rate: float) -> list[ParameterSearchRange]:

    min_n_estimators = min(1/learning_rate*7, 1000)
    return [
        ParameterSearchRange(
            name='n_estimators',
            type='int',
            low=min_n_estimators,
            high=min_n_estimators * 7,
        ),
        ParameterSearchRange(
            name='num_leaves',
            type='int',
            low=10,
            high=100,
        ),
        ParameterSearchRange(
            name='max_depth',
            type='int',
            low=2,
            high=14,
        ),
        ParameterSearchRange(
            name='min_child_samples',
            type='int',
            low=2,
            high=200,
        ),
        ParameterSearchRange(
            name='reg_alpha',
            type='uniform',
            low=0,
            high=5,
        ),
    ]


def get_default_team_rating_search_range() -> list[ParameterSearchRange]:
    return [
        ParameterSearchRange(
            name='confidence_weight',
            type='uniform',
            low=0.7,
            high=0.95
        ),
        ParameterSearchRange(
            name='confidence_days_ago_multiplier',
            type='uniform',
            low=0.02,
            high=.12,
        ),
        ParameterSearchRange(
            name='confidence_max_days',
            type='uniform',
            low=40,
            high=150,
        ),
        ParameterSearchRange(
            name='confidence_max_sum',
            type='uniform',
            low=60,
            high=300,
        ),
        ParameterSearchRange(
            name='confidence_value_denom',
            type='uniform',
            low=50,
            high=350
        ),
        ParameterSearchRange(
            name='rating_change_multiplier',
            type='uniform',
            low=30,
            high=100
        ),
        ParameterSearchRange(
            name='min_rating_change_multiplier_ratio',
            type='uniform',
            low=0.02,
            high=0.2,
        )
    ]
