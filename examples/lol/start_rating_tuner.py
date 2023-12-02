from examples.utils import load_data
from player_performance_ratings.data_structures import ColumnNames
from player_performance_ratings.predictor.match_predictor import MatchPredictor
from player_performance_ratings.predictor.estimators.classifier import SKLearnClassifierWrapper
from player_performance_ratings.ratings.enums import RatingColumnNames
from player_performance_ratings import TeamRatingGenerator
from player_performance_ratings import RatingGenerator
from player_performance_ratings import StartRatingTuner
from player_performance_ratings import ParameterSearchRange
from player_performance_ratings import StartLeagueRatingOptimizer

df = load_data()

df = df.sort_values(by=['date', 'gameid', 'teamname', "playername"])
df = (
    df.loc[lambda x: x.position != 'team']
    .assign(team_count=df.groupby('gameid')['teamname'].transform('nunique'))
    .loc[lambda x: x.team_count == 2]
)

column_names = ColumnNames(
    team_id='teamname',
    match_id='gameid',
    start_date="date",
    player_id="playername",
    performance="result",
    league='league'
)
team_rating_generator = TeamRatingGenerator(
    player_rating_generator=TeamRatingGenerator())
rating_generator = RatingGenerator()
predictor = SKLearnClassifierWrapper(features=[RatingColumnNames.RATING_DIFFERENCE], target='result',
                                     granularity=[column_names.match_id, column_names.team_id])

match_predictor = MatchPredictor(
    rating_generator=rating_generator,
    column_names=column_names,
    predictor=predictor,
)
start_rating_search_range = [
    ParameterSearchRange(
        name='team_weight',
        type='uniform',
        low=0.12,
        high=.4,
    ),
    ParameterSearchRange(
        name='league_quantile',
        type='uniform',
        low=0.12,
        high=.4,
    ),
    ParameterSearchRange(
        name='min_count_for_percentiles',
        type='uniform',
        low=20,
        high=100,
    )
]

start_rating_optimizer = StartLeagueRatingOptimizer(column_names=column_names, match_predictor=match_predictor,
                                                    max_iterations=1)

start_rating_tuner = StartRatingTuner(column_names=column_names,
                                      match_predictor=match_predictor,
                                      n_trials=1,
                                      search_ranges=start_rating_search_range,
                                      start_rating_optimizer=start_rating_optimizer
                                      )
start_rating_tuner.tune(df=df)
