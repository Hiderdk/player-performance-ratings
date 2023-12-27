import pandas as pd

from player_performance_ratings.transformation.pre_transformers import GroupByTransformer, DiminishingValueTransformer, \
    NetOverPredictedTransformer, SymmetricDistributionTransformer


def test_groupby_transformer():
    df = pd.DataFrame({
        'game_id': [1, 1, 1, 2, 2, 2],
        "performance": [0.2, 0.3, 0.4, 0.5, 0.6, 0.2],
        "player_id": [1, 2, 3, 1, 2, 3],
    })

    transformer = GroupByTransformer(
        features=['performance'],
        granularity=["player_id"]
    )

    expected_df = df.copy()
    expected_df[transformer.prefix + "performance"] = [0.35, 0.45, 0.3, 0.35, 0.45, 0.3]

    transformed_df = transformer.transform(df)
    pd.testing.assert_frame_equal(expected_df, transformed_df)


def test_diminshing_value_transformer():
    df = pd.DataFrame({
        "performance": [0.2, 0.2, 0.2, 0.2, 0.9],
        "player_id": [1, 2, 3, 1, 2],
    })

    transformer = DiminishingValueTransformer(features=['performance'])

    ori_df = df.copy()
    transformed_df = transformer.transform(df)

    assert transformed_df['performance'].iloc[4] < ori_df['performance'].iloc[4]
    assert transformed_df['performance'].iloc[0] == ori_df['performance'].iloc[0]


def test_reverse_diminshing_value_transformer():
    df = pd.DataFrame({
        "performance": [0.1, 0.8, 0.8, 0.8, 0.8],
        "player_id": [1, 2, 3, 1, 2],
    })

    transformer = DiminishingValueTransformer(features=['performance'], reverse=True)

    ori_df = df.copy()
    transformed_df = transformer.transform(df)

    assert transformed_df['performance'].iloc[0] > ori_df['performance'].iloc[0]
    assert transformed_df['performance'].iloc[3] == ori_df['performance'].iloc[3]


def test_net_over_predicted_transformer():
    df = pd.DataFrame({
        "performance": [0.1, 0.2, 0.5, 0.55, 0.6],
        "player_id": [1, 1, 2, 2, 3],
        "position": ["PG", "PG", "SG", "SG", "SG"]
    })

    transformer = NetOverPredictedTransformer(features=['performance'], granularity=['position'])
    expected_df = df.copy()
    expected_df[transformer.features_created[0]] = [-0.05, 0.05, -0.05, 0, 0.05]
    transformed_df = transformer.transform(df)

    pd.testing.assert_frame_equal(expected_df, transformed_df)


def test_symmetric_distribution_transformery():
    df = pd.DataFrame({
        "performance": [0.1, 0.2, 0.15, 0.2, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.5, 0.15, 0.45, 0.5],
        "player_id": [1, 1, 1, 2, 2, 3, 3, 3, 3, 2, 4, 3, 2, 2],
        "position": ["PG", "PG", "PG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG"]
    })

    transformer = SymmetricDistributionTransformer(features=["performance"],
                                                   max_iterations=40)
    transformed_df = transformer.transform(df)
    assert abs(df["performance"].skew())> transformer.skewness_allowed

    assert abs(transformed_df["performance"].skew()) < transformer.skewness_allowed


def test_symmetric_distribution_transformer_with_granularity():
    df = pd.DataFrame({
        "performance": [0.1, 0.2, 0.15, 0.2, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.5, 0.15, 0.45, 0.5],
        "player_id": [1, 1, 1, 2, 2, 3, 3, 3, 3, 2, 4, 3, 2, 2],
        "position": ["PG", "PG", "PG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG", "SG"]
    })

    transformer = SymmetricDistributionTransformer(features=["performance"], granularity=["position"],
                                                   max_iterations=40)
    transformed_df = transformer.transform(df)
    assert abs(df.loc[lambda x: x.position == 'SG']["performance"].skew()) > transformer.skewness_allowed
    assert abs(transformed_df.loc[lambda x: x.position == 'SG']["performance"].skew()) < transformer.skewness_allowed