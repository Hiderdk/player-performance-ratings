from sklearn.preprocessing import StandardScaler


from examples.utils import load_data
from player_performance_ratings import ColumnNames
from player_performance_ratings import MatchPredictor
from player_performance_ratings import SKLearnClassifierWrapper
from player_performance_ratings import RatingColumnNames
from player_performance_ratings import PlayerRatingGenerator
from player_performance_ratings import TeamRatingGenerator
from player_performance_ratings import RatingGenerator
from player_performance_ratings import ParameterSearchRange
from player_performance_ratings import PlayerRatingTuner


from player_performance_ratings.transformers.common import SkLearnTransformerWrapper, MinMaxTransformer, ColumnsWeighter, ColumnWeight

column_names = ColumnNames(
    team_id='teamname',
    match_id='gameid',
    start_date="date",
    player_id="playername",
    performance='performance',
    league='league'
)
df = load_data()
df = df.sort_values(by=['date', 'gameid', 'teamname', "playername"])

df = (
    df.loc[lambda x: x.position != 'team']
    .assign(team_count=df.groupby('gameid')['teamname'].transform('nunique'))
    .loc[lambda x: x.team_count == 2]
)

search_ranges = [
    ParameterSearchRange(
        name='certain_weight',
        type='uniform',
        low=0.7,
        high=0.95
    ),
    ParameterSearchRange(
        name='certain_days_ago_multiplier',
        type='uniform',
        low=0.02,
        high=.12,
    ),
    ParameterSearchRange(
        name='max_days_ago',
        type='uniform',
        low=40,
        high=150,
    ),
    ParameterSearchRange(
        name='max_certain_sum',
        type='uniform',
        low=20,
        high=70,
    ),
    ParameterSearchRange(
        name='certain_value_denom',
        type='uniform',
        low=15,
        high=50
    ),
    ParameterSearchRange(
        name='reference_certain_sum_value',
        type='uniform',
        low=0.5,
        high=5
    ),
    ParameterSearchRange(
        name='rating_change_multiplier',
        type='uniform',
        low=40,
        high=240
    ),
]

features = ["result", "kills",
            "deaths", "assists", "damagetochampions"]
standard_scaler = SkLearnTransformerWrapper(transformer=StandardScaler(), features=features)

pre_transformers = [
    standard_scaler,
    MinMaxTransformer(features=features),
    ColumnsWeighter(
        weighted_column_name=column_names.performance, column_weights=[
            ColumnWeight(
                name='kills',
                weight=0.1,
            ),
            ColumnWeight(
                name='deaths',
                weight=0.1,
                is_negative=True,
            ),
            ColumnWeight(
                name='assists',
                weight=0.1,
            ),
            ColumnWeight(
                name='damagetochampions',
                weight=0.2,
            ),
            ColumnWeight(
                name='result',
                weight=0.5,
            ),
        ]
    ),
]

team_rating_generator = TeamRatingGenerator(
    player_rating_generator=PlayerRatingGenerator())
rating_generator = RatingGenerator()
predictor = SKLearnClassifierWrapper(features=[RatingColumnNames.RATING_DIFFERENCE], target='result')

match_predictor = MatchPredictor(
    rating_generator=rating_generator,
    column_names=column_names,
    predictor=predictor,
    pre_rating_transformers=pre_transformers,
)

tuner = PlayerRatingTuner(match_predictor=match_predictor,
                          search_ranges=search_ranges,
                          n_trials=100
                          )
tuner.tune(df=df)
