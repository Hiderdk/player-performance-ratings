from dataclasses import dataclass
from typing import Dict, List, Optional
from dataclasses_json import DataClassJsonMixin


@dataclass
class ColumnNames:
    team_id: str
    match_id: str
    start_date: str
    player_id: str
    performance: str = "performance"
    league: str = None
    participation_weight: str = None
    projected_participation_weight: str = None
    team_players_percentage_playing_time: str = None
    rating_update_id: str = None

    def __post_init__(self):
        if self.rating_update_id is None:
            self.rating_update_id = self.match_id

        if self.projected_participation_weight is None:
            self.projected_participation_weight = self.participation_weight


@dataclass
class StartRatingParameters:
    start_league_ratings: Optional[dict[str, float]] = None
    league_quantile: float = 0.2
    team_rating_subtract: float = 80
    team_weight: float = 0.2


@dataclass
class MatchPerformance:
    performance_value: float
    participation_weight: float
    projected_participation_weight: float
    ratio: Dict[str, float]


@dataclass
class PlayerRating(DataClassJsonMixin):
    id: str
    rating_value: float
    name: Optional[str] = None
    games_played: int = 0
    last_match_day_number: int = None
    certain_ratio: float = 0
    certain_sum: float = 0
    prev_rating_changes: List[float] = None


@dataclass
class Team:
    id: str
    player_ids: list[str]
    last_match_day_number: int
    name: Optional[str] = None


@dataclass
class TeamRating(DataClassJsonMixin):
    id: str
    name: str
    rating_value: float
    players: list[PlayerRating]
    games_played: int = 0
    last_match_day_number: int = None


@dataclass
class PreMatchPlayerRating:
    id: str
    rating_value: float
    games_played: int
    projected_rating_value: float
    certain_ratio: float
    league: str
    match_performance: MatchPerformance



@dataclass
class PreMatchTeamRating:
    id: str
    players: list[PreMatchPlayerRating]
    rating_value: float
    league: str
    projected_rating_value: float


@dataclass
class PreMatchRating:
    id: str
    teams: list[PreMatchTeamRating]
    day_number: int

@dataclass
class PlayerRatingChange:
    id: str
    day_number: int
    league: str
    participation_weight: float
    predicted_performance: float
    performance: float
    pre_match_rating_value: float
    rating_change_value: float


@dataclass
class TeamRatingChange:
    id: str
    players: list[PlayerRatingChange]
    predicted_performance: float
    performance: float
    pre_match_rating_value: float
    rating_change_value: float
    league: str

@dataclass
class PostMatchTeamRatingChange:
    id: str
    players: list[PlayerRatingChange]
    rating_value: float
    predicted_performance: float


@dataclass
class PostMatchRatingChange:
    id: str
    teams: list[PostMatchTeamRatingChange]


@dataclass
class MatchRating:
    id: str
    pre_match_rating: PreMatchRating
    post_match_rating: PostMatchRatingChange


@dataclass
class MatchRatings:
    pre_match_team_rating_values: list[float]
    pre_match_player_rating_values: list[float]
    pre_match_opponent_rating_values: list[float]
    player_rating_changes: list[float]
    player_leagues: list[str]
    team_opponent_leagues: list[str]
    match_ids: list[str]


@dataclass
class MatchPlayer:
    id: str
    performance: MatchPerformance
    league: Optional[str] = None


@dataclass
class MatchTeam:
    id: str
    players: list[MatchPlayer]
    league: str = None


@dataclass
class Match:
    id: str
    update_id: str
    teams: List[MatchTeam]
    day_number: int
    league: str = None
