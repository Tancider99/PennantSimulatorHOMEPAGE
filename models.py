# -*- coding: utf-8 -*-
"""
データモデル定義
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import datetime


class Position(Enum):
    PITCHER = "投手"
    CATCHER = "捕手"
    FIRST = "一塁手"
    SECOND = "二塁手"
    THIRD = "三塁手"
    SHORTSTOP = "遊撃手"
    OUTFIELD = "外野手"


class PitchType(Enum):
    STARTER = "先発"
    RELIEVER = "中継ぎ"
    CLOSER = "抑え"


class TeamLevel(Enum):
    FIRST = "一軍"
    SECOND = "二軍"
    THIRD = "三軍"


class PlayerStatus(Enum):
    ACTIVE = "支配下"
    FARM = "育成"


class League(Enum):
    CENTRAL = "セントラル"
    PACIFIC = "パシフィック"


class GameStatus(Enum):
    SCHEDULED = "未消化"
    IN_PROGRESS = "試合中"
    COMPLETED = "終了"


@dataclass
class GameResult:
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    date: str
    game_number: int


@dataclass
class ScheduledGame:
    game_number: int
    date: str
    home_team_name: str
    away_team_name: str
    status: GameStatus = GameStatus.SCHEDULED
    home_score: int = 0
    away_score: int = 0
    
    @property
    def is_completed(self) -> bool:
        return self.status == GameStatus.COMPLETED
    
    @property
    def month(self) -> int:
        try:
            return int(self.date.split('-')[1])
        except:
            return 0
    
    @property
    def day(self) -> int:
        try:
            return int(self.date.split('-')[2])
        except:
            return 0
            
    @property
    def year(self) -> int:
        try:
            return int(self.date.split('-')[0])
        except:
            return 0

    def get_winner(self) -> Optional[str]:
        if not self.is_completed:
            return None
        if self.home_score > self.away_score:
            return self.home_team_name
        elif self.away_score > self.home_score:
            return self.away_team_name
        return None  # 引き分け

    def is_draw(self) -> bool:
        return self.is_completed and self.home_score == self.away_score

    def to_result(self) -> GameResult:
        return GameResult(
            home_team_name=self.home_team_name,
            away_team_name=self.away_team_name,
            home_score=self.home_score,
            away_score=self.away_score,
            date=self.date,
            game_number=self.game_number
        )


@dataclass
class PlayerStats:
    """選手能力値（1-99スケール）

    基本能力値は1〜99の範囲（50が平均、90以上がSランク）
    """
    # ===== 打撃能力 (Batting Ratings) =====
    contact: int = 50          # コンタクト
    gap: int = 50              # ギャップパワー
    power: int = 50            # パワー
    eye: int = 50              # 選球眼
    avoid_k: int = 50          # 三振回避

    # ===== 走塁能力 (Running Ratings) =====
    speed: int = 50            # 走力
    steal: int = 50            # 盗塁
    baserunning: int = 50      # 走塁

    # ===== バント能力 =====
    bunt_sac: int = 50         # 送りバント
    bunt_hit: int = 50         # セーフティバント

    # ===== 守備能力 (Fielding Ratings) =====
    catcher_ability: int = 50  # 捕手リード
    catcher_arm: int = 50      # 捕手肩

    inf_range: int = 50        # 内野守備範囲
    inf_error: int = 50        # 内野捕球
    inf_arm: int = 50          # 内野肩
    turn_dp: int = 50          # 併殺処理

    of_range: int = 50         # 外野守備範囲
    of_error: int = 50         # 外野捕球
    of_arm: int = 50           # 外野肩

    # ===== 投球能力 (Pitching Ratings) =====
    stuff: int = 50            # 球威
    movement: int = 50         # 変化球/ムーブメント
    control: int = 50          # 制球

    # ===== 投手追加能力 =====
    velocity: int = 145        # 球速 (km/h)
    stamina: int = 50          # スタミナ
    hold_runners: int = 50     # クイック
    gb_tendency: int = 50      # ゴロ傾向

    # ===== その他能力 =====
    durability: int = 50       # 回復力・ケガ耐性
    work_ethic: int = 50       # 練習態度
    intelligence: int = 50     # 野球脳

    # ===== 投手専用 =====
    pitches: Dict[str, int] = field(default_factory=dict)  # 球種 {"ストレート": 60, ...}

    # ===== 互換性・エイリアス =====
    @property
    def run(self) -> int: return self.speed
    @property
    def arm(self) -> int:
        return max(self.inf_arm, self.of_arm, self.catcher_arm)
    @property
    def fielding(self) -> int:
        return max(self.inf_range, self.of_range, self.catcher_ability)
    @property
    def catching(self) -> int:
        return max(self.inf_error, self.of_error)
    @property
    def breaking(self) -> int: return self.stuff
    @property
    def bunt(self) -> int: return self.bunt_sac
    @property
    def mental(self) -> int: return self.intelligence
    @property
    def injury_res(self) -> int: return self.durability
    @property
    def recovery(self) -> int: return self.durability
    @property
    def trajectory(self) -> int: return min(4, max(1, self.power // 25 + 1)) # 1-99スケールに合わせて調整
    @property
    def chance(self) -> int: return self.intelligence
    @property
    def vs_left_batter(self) -> int: return self.contact
    @property
    def vs_left_pitcher(self) -> int: return self.stuff
    @property
    def vs_pinch(self) -> int: return self.intelligence
    @property
    def quick(self) -> int: return self.hold_runners
    @property
    def stability(self) -> int: return self.control
    @property
    def inf_dp(self) -> int: return self.turn_dp
    @property
    def catcher_ab(self) -> int: return self.catcher_ability
    @property
    def breaking_balls(self) -> List[str]: return list(self.pitches.keys()) if self.pitches else []

    # 互換性セッター
    @run.setter
    def run(self, value): self.speed = value
    @arm.setter
    def arm(self, value):
        self.inf_arm = value
        self.of_arm = value
        self.catcher_arm = value
    @fielding.setter
    def fielding(self, value):
        self.inf_range = value
        self.of_range = value
        self.catcher_ability = value
    @breaking.setter
    def breaking(self, value): self.stuff = value
    @bunt.setter
    def bunt(self, value): self.bunt_sac = value

    def to_star_rating(self, value: int) -> float:
        """能力値を★評価に変換 (0.5-5.0)"""
        return max(0.5, min(5.0, value / 20)) # 99/20 = ~5.0

    def overall_batting(self) -> float:
        """野手の総合値を計算 (1-99)"""
        batting = (self.contact * 2 + self.gap * 1.5 + self.power * 1.5 + self.eye + self.avoid_k) / 7
        running = (self.speed + self.steal + self.baserunning) / 3
        defense = (self.inf_range + self.of_range + self.catcher_ability) / 3
        return (batting * 0.5 + running * 0.2 + defense * 0.3)

    def overall_pitching(self) -> float:
        """投手の総合値を計算 (1-99)"""
        vel_rating = self.kmh_to_rating(self.velocity)
        return (self.stuff * 2 + self.movement * 1.5 + self.control * 2 + vel_rating + self.stamina * 0.5) / 7

    def speed_to_kmh(self) -> int:
        """球速をkm/hで返す"""
        return self.velocity

    @staticmethod
    def kmh_to_rating(kmh: int) -> int:
        """km/hを1-99評価値に変換"""
        # 130km/h -> 30, 145km/h -> 60, 160km/h -> 90
        # Formula: 30 + (kmh - 130) * 2
        val = (kmh - 130) * 2 + 30
        return int(max(1, min(99, val)))

    def get_rank(self, value: int) -> str:
        """能力値をランクに変換（1-99スケール）"""
        if value >= 90: return "S"
        elif value >= 80: return "A"
        elif value >= 70: return "B"
        elif value >= 60: return "C"
        elif value >= 50: return "D"
        elif value >= 40: return "E"
        elif value >= 30: return "F"
        else: return "G"

    def get_rank_color(self, value: int) -> str:
        """ランクに応じた色コード（1-99スケール）"""
        if value >= 90: return "#FFD700"  # Gold (S)
        elif value >= 80: return "#FF4500"  # Red-Orange (A)
        elif value >= 70: return "#FFA500"  # Orange (B)
        elif value >= 60: return "#FFFF00"  # Yellow (C)
        elif value >= 50: return "#32CD32"  # Lime Green (D)
        elif value >= 40: return "#1E90FF"  # Dodger Blue (E)
        elif value >= 30: return "#4682B4"  # Steel Blue (F)
        return "#808080"  # Gray (G)

    def get_star_display(self, value: int) -> str:
        """能力値を★表示に変換"""
        stars = self.to_star_rating(value)
        full = int(stars)
        half = 1 if stars - full >= 0.5 else 0
        return "★" * full + ("☆" if half else "")

    def get_breaking_balls_display(self) -> str:
        if not self.pitches: return "なし"
        return "、".join(self.pitches.keys())


@dataclass
class PlayerRecord:
    """選手成績（基本統計）"""
    # 打撃基本
    games: int = 0
    plate_appearances: int = 0
    at_bats: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    rbis: int = 0
    runs: int = 0
    walks: int = 0
    intentional_walks: int = 0
    hit_by_pitch: int = 0
    strikeouts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    sacrifice_hits: int = 0
    sacrifice_flies: int = 0
    grounded_into_dp: int = 0

    # 投手基本
    games_pitched: int = 0
    games_started: int = 0
    wins: int = 0
    losses: int = 0
    saves: int = 0
    holds: int = 0
    blown_saves: int = 0
    innings_pitched: float = 0.0
    earned_runs: int = 0
    hits_allowed: int = 0
    walks_allowed: int = 0
    intentional_walks_allowed: int = 0
    hit_batters: int = 0
    strikeouts_pitched: int = 0
    home_runs_allowed: int = 0
    runs_allowed: int = 0
    wild_pitches: int = 0
    balks: int = 0

    # 詳細打撃データ
    total_bases: int = 0
    ground_balls: int = 0
    fly_balls: int = 0
    line_drives: int = 0
    popups: int = 0
    hard_hit_balls: int = 0  # 強い打球
    balls_in_play: int = 0   # インプレー打球数

    # 詳細投球データ
    pitches_thrown: int = 0
    strikes_thrown: int = 0
    balls_thrown: int = 0
    first_pitch_strikes: int = 0
    ground_outs: int = 0
    fly_outs: int = 0
    quality_starts: int = 0
    complete_games: int = 0
    shutouts: int = 0

    # ===== 基本指標 =====
    @property
    def batting_average(self) -> float:
        """打率"""
        return self.hits / self.at_bats if self.at_bats > 0 else 0.0

    @property
    def era(self) -> float:
        """防御率"""
        return (self.earned_runs * 9) / self.innings_pitched if self.innings_pitched > 0 else 0.0

    @property
    def singles(self) -> int:
        """単打"""
        return self.hits - self.doubles - self.triples - self.home_runs

    # ===== セイバーメトリクス（打者） =====
    @property
    def obp(self) -> float:
        """出塁率 (On-Base Percentage)"""
        denominator = self.at_bats + self.walks + self.hit_by_pitch + self.sacrifice_flies
        if denominator == 0:
            return 0.0
        return (self.hits + self.walks + self.hit_by_pitch) / denominator

    @property
    def slg(self) -> float:
        """長打率 (Slugging Percentage)"""
        if self.at_bats == 0:
            return 0.0
        tb = self.singles + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)
        return tb / self.at_bats

    @property
    def ops(self) -> float:
        """OPS (On-base Plus Slugging)"""
        return self.obp + self.slg

    @property
    def iso(self) -> float:
        """ISO (Isolated Power) - 純粋長打力"""
        return self.slg - self.batting_average

    @property
    def babip(self) -> float:
        """BABIP (Batting Average on Balls In Play)"""
        denominator = self.at_bats - self.strikeouts - self.home_runs + self.sacrifice_flies
        if denominator <= 0:
            return 0.0
        return (self.hits - self.home_runs) / denominator

    @property
    def bb_rate(self) -> float:
        """BB% (Walk Rate)"""
        if self.plate_appearances == 0:
            return 0.0
        return self.walks / self.plate_appearances

    @property
    def k_rate(self) -> float:
        """K% (Strikeout Rate)"""
        if self.plate_appearances == 0:
            return 0.0
        return self.strikeouts / self.plate_appearances

    @property
    def bb_k_ratio(self) -> float:
        """BB/K (Walk to Strikeout Ratio)"""
        if self.strikeouts == 0:
            return self.walks if self.walks > 0 else 0.0
        return self.walks / self.strikeouts

    @property
    def ab_per_hr(self) -> float:
        """AB/HR (At Bats per Home Run)"""
        if self.home_runs == 0:
            return 0.0
        return self.at_bats / self.home_runs

    @property
    def sb_rate(self) -> float:
        """SB% (Stolen Base Success Rate)"""
        attempts = self.stolen_bases + self.caught_stealing
        if attempts == 0:
            return 0.0
        return self.stolen_bases / attempts

    @property
    def rc(self) -> float:
        """RC (Runs Created) - 得点創出"""
        a = self.hits + self.walks + self.hit_by_pitch
        b = self.singles + (1.5 * self.doubles) + (2 * self.triples) + (2.4 * self.home_runs)
        c = self.at_bats + self.walks + self.hit_by_pitch
        if c == 0:
            return 0.0
        return (a * b) / c

    @property
    def rc27(self) -> float:
        """RC/27 (Runs Created per 27 outs)"""
        outs = self.at_bats - self.hits + self.sacrifice_hits + self.sacrifice_flies + self.grounded_into_dp + self.caught_stealing
        if outs == 0:
            return 0.0
        return (self.rc / outs) * 27

    @property
    def woba(self) -> float:
        """wOBA (Weighted On-Base Average) - 簡易版"""
        # NPB用に調整した係数
        numerator = (0.69 * (self.walks - self.intentional_walks) +
                    0.72 * self.hit_by_pitch +
                    0.89 * self.singles +
                    1.27 * self.doubles +
                    1.62 * self.triples +
                    2.10 * self.home_runs)
        denominator = self.at_bats + self.walks - self.intentional_walks + self.sacrifice_flies + self.hit_by_pitch
        if denominator == 0:
            return 0.0
        return numerator / denominator

    @property
    def wraa(self) -> float:
        """wRAA (Weighted Runs Above Average)"""
        league_woba = 0.320  # リーグ平均wOBA（仮）
        woba_scale = 1.15
        pa = self.plate_appearances
        if pa == 0:
            return 0.0
        return ((self.woba - league_woba) / woba_scale) * pa

    # ===== セイバーメトリクス（投手） =====
    @property
    def whip(self) -> float:
        """WHIP (Walks + Hits per Inning Pitched)"""
        if self.innings_pitched == 0:
            return 0.0
        return (self.walks_allowed + self.hits_allowed) / self.innings_pitched

    @property
    def k_per_9(self) -> float:
        """K/9 (Strikeouts per 9 innings)"""
        if self.innings_pitched == 0:
            return 0.0
        return (self.strikeouts_pitched * 9) / self.innings_pitched

    @property
    def bb_per_9(self) -> float:
        """BB/9 (Walks per 9 innings)"""
        if self.innings_pitched == 0:
            return 0.0
        return (self.walks_allowed * 9) / self.innings_pitched

    @property
    def hr_per_9(self) -> float:
        """HR/9 (Home Runs per 9 innings)"""
        if self.innings_pitched == 0:
            return 0.0
        return (self.home_runs_allowed * 9) / self.innings_pitched

    @property
    def h_per_9(self) -> float:
        """H/9 (Hits per 9 innings)"""
        if self.innings_pitched == 0:
            return 0.0
        return (self.hits_allowed * 9) / self.innings_pitched

    @property
    def k_bb_ratio(self) -> float:
        """K/BB (Strikeout to Walk Ratio)"""
        if self.walks_allowed == 0:
            return self.strikeouts_pitched if self.strikeouts_pitched > 0 else 0.0
        return self.strikeouts_pitched / self.walks_allowed

    @property
    def k_rate_pitched(self) -> float:
        """K% (Pitcher Strikeout Rate)"""
        batters = self.hits_allowed + self.walks_allowed + self.hit_batters + int(self.innings_pitched * 3)
        if batters == 0:
            return 0.0
        return self.strikeouts_pitched / batters

    @property
    def bb_rate_pitched(self) -> float:
        """BB% (Pitcher Walk Rate)"""
        batters = self.hits_allowed + self.walks_allowed + self.hit_batters + int(self.innings_pitched * 3)
        if batters == 0:
            return 0.0
        return self.walks_allowed / batters

    @property
    def gb_rate(self) -> float:
        """GB% (Ground Ball Rate)"""
        total = self.ground_outs + self.fly_outs
        if total == 0:
            return 0.0
        return self.ground_outs / total

    @property
    def fb_rate(self) -> float:
        """FB% (Fly Ball Rate)"""
        total = self.ground_outs + self.fly_outs
        if total == 0:
            return 0.0
        return self.fly_outs / total

    @property
    def lob_rate(self) -> float:
        """LOB% (Left on Base Percentage) - 簡易版"""
        h_plus_bb = self.hits_allowed + self.walks_allowed + self.hit_batters
        if h_plus_bb == 0:
            return 0.0
        return max(0, (h_plus_bb - self.runs_allowed)) / h_plus_bb

    @property
    def fip(self) -> float:
        """FIP (Fielding Independent Pitching)"""
        if self.innings_pitched == 0:
            return 0.0
        constant = 3.10  # NPB用の定数
        return ((13 * self.home_runs_allowed + 3 * (self.walks_allowed + self.hit_batters) - 2 * self.strikeouts_pitched) / self.innings_pitched) + constant

    @property
    def xfip(self) -> float:
        """xFIP (Expected FIP)"""
        if self.innings_pitched == 0 or self.fly_outs == 0:
            return self.fip
        league_hr_fb_rate = 0.10  # リーグ平均HR/FB率（仮）
        expected_hr = self.fly_outs * league_hr_fb_rate
        constant = 3.10
        return ((13 * expected_hr + 3 * (self.walks_allowed + self.hit_batters) - 2 * self.strikeouts_pitched) / self.innings_pitched) + constant

    @property
    def siera(self) -> float:
        """SIERA (Skill-Interactive ERA) - 簡易版"""
        if self.innings_pitched == 0:
            return 0.0
        # 簡易計算
        k_rate = self.k_rate_pitched
        bb_rate = self.bb_rate_pitched
        gb_rate = self.gb_rate
        return 6.145 - 16.986 * k_rate + 11.434 * bb_rate - 1.858 * gb_rate + 3.10

    @property
    def winning_percentage(self) -> float:
        """勝率"""
        total = self.wins + self.losses
        if total == 0:
            return 0.0
        return self.wins / total

    @property
    def strike_percentage(self) -> float:
        """ストライク率"""
        if self.pitches_thrown == 0:
            return 0.0
        return self.strikes_thrown / self.pitches_thrown

    @property
    def pitches_per_inning(self) -> float:
        """イニングあたり投球数"""
        if self.innings_pitched == 0:
            return 0.0
        return self.pitches_thrown / self.innings_pitched

    @property
    def babip_against(self) -> float:
        """被BABIP"""
        denominator = self.hits_allowed + int(self.innings_pitched * 3) - self.strikeouts_pitched - self.home_runs_allowed
        if denominator <= 0:
            return 0.0
        return (self.hits_allowed - self.home_runs_allowed) / denominator

    def reset(self):
        """成績をリセット"""
        for field_name in self.__dataclass_fields__:
            if field_name not in ['games', 'games_pitched', 'games_started']:
                setattr(self, field_name, 0 if isinstance(getattr(self, field_name), int) else 0.0)

    def merge_from(self, other: 'PlayerRecord'):
        """他のレコードから成績を合算"""
        for field_name in self.__dataclass_fields__:
            current = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if isinstance(current, (int, float)):
                setattr(self, field_name, current + other_val)


@dataclass
class DetailedSeasonStats:
    """年度別・軍別の詳細成績"""
    year: int = 0
    team_level: TeamLevel = None  # 一軍、二軍、三軍
    record: PlayerRecord = field(default_factory=PlayerRecord)

    # 月別成績
    monthly_stats: Dict[int, PlayerRecord] = field(default_factory=dict)  # {月: PlayerRecord}

    # 対戦チーム別成績
    vs_team_stats: Dict[str, PlayerRecord] = field(default_factory=dict)  # {チーム名: PlayerRecord}

    # 左右別成績
    vs_left_stats: PlayerRecord = field(default_factory=PlayerRecord)
    vs_right_stats: PlayerRecord = field(default_factory=PlayerRecord)

    # 状況別成績
    risp_stats: PlayerRecord = field(default_factory=PlayerRecord)  # 得点圏
    close_game_stats: PlayerRecord = field(default_factory=PlayerRecord)  # 接戦時

    # ホーム/アウェイ別
    home_stats: PlayerRecord = field(default_factory=PlayerRecord)
    away_stats: PlayerRecord = field(default_factory=PlayerRecord)


@dataclass
class CareerStats:
    """選手の通算・年度別成績"""
    # 年度別成績 {年: {TeamLevel: DetailedSeasonStats}}
    season_stats: Dict[int, Dict[str, DetailedSeasonStats]] = field(default_factory=dict)

    # 通算成績（軍別）
    career_first: PlayerRecord = field(default_factory=PlayerRecord)   # 一軍通算
    career_second: PlayerRecord = field(default_factory=PlayerRecord)  # 二軍通算
    career_third: PlayerRecord = field(default_factory=PlayerRecord)   # 三軍通算
    career_total: PlayerRecord = field(default_factory=PlayerRecord)   # 全通算

    def add_season(self, year: int, team_level: TeamLevel, stats: DetailedSeasonStats):
        """シーズン成績を追加"""
        if year not in self.season_stats:
            self.season_stats[year] = {}
        self.season_stats[year][team_level.value if team_level else "一軍"] = stats

        # 通算に加算
        if team_level == TeamLevel.FIRST or team_level is None:
            self.career_first.merge_from(stats.record)
        elif team_level == TeamLevel.SECOND:
            self.career_second.merge_from(stats.record)
        elif team_level == TeamLevel.THIRD:
            self.career_third.merge_from(stats.record)
        self.career_total.merge_from(stats.record)

    def get_season(self, year: int, team_level: TeamLevel = None) -> Optional[DetailedSeasonStats]:
        """特定年度・軍の成績を取得"""
        if year not in self.season_stats:
            return None
        level_key = team_level.value if team_level else "一軍"
        return self.season_stats[year].get(level_key)

    def get_all_seasons(self) -> List[Tuple[int, str, DetailedSeasonStats]]:
        """全シーズン成績をリストで取得"""
        result = []
        for year in sorted(self.season_stats.keys()):
            for level, stats in self.season_stats[year].items():
                result.append((year, level, stats))
        return result


@dataclass
class Player:
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    stats: PlayerStats = field(default_factory=PlayerStats)
    record: PlayerRecord = field(default_factory=PlayerRecord)  # 現シーズン一軍成績
    age: int = 25
    status: PlayerStatus = PlayerStatus.ACTIVE
    uniform_number: int = 0
    is_foreign: bool = False
    salary: int = 10000000
    years_pro: int = 0
    draft_round: int = 0

    is_developmental: bool = False
    team_level: 'TeamLevel' = None

    sub_positions: List[Position] = field(default_factory=list)
    # サブポジション適性値（0.0〜1.0）
    sub_position_ratings: Dict[str, float] = field(default_factory=dict)

    starter_aptitude: int = 50
    middle_aptitude: int = 50
    closer_aptitude: int = 50

    special_abilities: Optional[object] = None
    player_status: Optional[object] = None
    growth: Optional[object] = None

    # ===== 軍別成績 =====
    record_farm: PlayerRecord = field(default_factory=PlayerRecord)    # 現シーズン二軍成績
    record_third: PlayerRecord = field(default_factory=PlayerRecord)   # 現シーズン三軍成績

    # ===== 通算・年度別成績 =====
    career_stats: CareerStats = field(default_factory=CareerStats)

    def __post_init__(self):
        """初期化後の処理"""
        if self.team_level is None:
            self.team_level = TeamLevel.FIRST

    def get_record_by_level(self, level: TeamLevel) -> PlayerRecord:
        """軍別の成績を取得"""
        if level == TeamLevel.FIRST:
            return self.record
        elif level == TeamLevel.SECOND:
            return self.record_farm
        elif level == TeamLevel.THIRD:
            return self.record_third
        return self.record

    def get_current_season_total(self) -> PlayerRecord:
        """現シーズンの全軍合算成績を取得"""
        total = PlayerRecord()
        total.merge_from(self.record)
        total.merge_from(self.record_farm)
        total.merge_from(self.record_third)
        return total

    def reset_season_records(self):
        """シーズン成績をリセット"""
        self.record = PlayerRecord()
        self.record_farm = PlayerRecord()
        self.record_third = PlayerRecord()

    def archive_season(self, year: int):
        """シーズン終了時に成績をアーカイブ"""
        # 一軍成績
        if self.record.games > 0 or self.record.games_pitched > 0:
            season_first = DetailedSeasonStats(
                year=year,
                team_level=TeamLevel.FIRST,
                record=self.record
            )
            self.career_stats.add_season(year, TeamLevel.FIRST, season_first)

        # 二軍成績
        if self.record_farm.games > 0 or self.record_farm.games_pitched > 0:
            season_second = DetailedSeasonStats(
                year=year,
                team_level=TeamLevel.SECOND,
                record=self.record_farm
            )
            self.career_stats.add_season(year, TeamLevel.SECOND, season_second)

        # 三軍成績
        if self.record_third.games > 0 or self.record_third.games_pitched > 0:
            season_third = DetailedSeasonStats(
                year=year,
                team_level=TeamLevel.THIRD,
                record=self.record_third
            )
            self.career_stats.add_season(year, TeamLevel.THIRD, season_third)

    def add_sub_position(self, pos: Position, rating: float = 0.7):
        """サブポジションを追加"""
        if pos != self.position and pos not in self.sub_positions:
            self.sub_positions.append(pos)
            self.sub_position_ratings[pos.value] = min(1.0, max(0.3, rating))

    def can_play_position(self, pos: Position) -> bool:
        """指定位置を守れるかどうか"""
        if self.position == pos:
            return True
        return pos in self.sub_positions
    
    def get_position_rating(self, pos: Position) -> float:
        """指定位置の適性値を取得（1.0が最高）"""
        if self.position == pos:
            return 1.0
        if pos in self.sub_positions:
            return self.sub_position_ratings.get(pos.value, 0.7)
        return 0.0

    @property
    def overall_rating(self) -> int:
        """総合評価 (1-999)"""
        # 能力値(1-99) を入力とし、平均250、最大999になるようにスケーリング
        # Formula: (rating / 99)^2 * 999
        # 50 -> 255
        # 99 -> 999
        if self.position == Position.PITCHER:
            val = self.stats.overall_pitching()
        else:
            val = self.stats.overall_batting()
            
        rating = (val / 99) ** 2 * 999
        return max(1, min(999, int(rating)))


@dataclass
class Team:
    name: str
    league: League
    players: List[Player] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    draws: int = 0
    current_lineup: List[int] = field(default_factory=list)
    starting_pitcher_idx: int = -1
    budget: int = 5000000000
    color: str = None
    abbr: str = None

    rotation: List[int] = field(default_factory=list)
    rotation_index: int = 0
    setup_pitchers: List[int] = field(default_factory=list)
    closer_idx: int = -1

    bench_batters: List[int] = field(default_factory=list)
    bench_pitchers: List[int] = field(default_factory=list)
    active_roster: List[int] = field(default_factory=list)  # 一軍登録選手（最大31人）
    farm_roster: List[int] = field(default_factory=list)    # 二軍選手
    third_roster: List[int] = field(default_factory=list)   # 三軍選手

    # 二軍・三軍のオーダー管理
    farm_lineup: List[int] = field(default_factory=list)         # 二軍打順
    farm_rotation: List[int] = field(default_factory=list)       # 二軍ローテ
    third_lineup: List[int] = field(default_factory=list)        # 三軍打順
    third_rotation: List[int] = field(default_factory=list)      # 三軍ローテ

    # 出場登録上限
    ACTIVE_ROSTER_LIMIT = 31
    FARM_ROSTER_LIMIT = 40   # 二軍上限
    THIRD_ROSTER_LIMIT = 30  # 三軍上限

    def get_today_starter(self) -> Optional[Player]:
        if not self.rotation: return None
        idx = self.rotation[self.rotation_index % len(self.rotation)]
        if 0 <= idx < len(self.players): return self.players[idx]
        return None

    def get_roster_players(self) -> List[Player]:
        """支配下選手を取得"""
        return [p for p in self.players if not p.is_developmental]

    def get_active_roster_players(self) -> List[Player]:
        """一軍登録選手を取得"""
        return [self.players[i] for i in self.active_roster if 0 <= i < len(self.players)]

    def get_farm_roster_players(self) -> List[Player]:
        """二軍選手を取得"""
        return [self.players[i] for i in self.farm_roster if 0 <= i < len(self.players)]

    def get_third_roster_players(self) -> List[Player]:
        """三軍選手を取得"""
        return [self.players[i] for i in self.third_roster if 0 <= i < len(self.players)]

    def get_players_by_level(self, level: TeamLevel) -> List[Player]:
        """軍別の選手を取得"""
        if level == TeamLevel.FIRST:
            return self.get_active_roster_players()
        elif level == TeamLevel.SECOND:
            return self.get_farm_roster_players()
        elif level == TeamLevel.THIRD:
            return self.get_third_roster_players()
        return []

    def get_active_roster_count(self) -> int:
        """一軍登録人数を取得"""
        return len(self.active_roster)

    def can_add_to_active_roster(self) -> bool:
        """一軍に追加可能かどうか"""
        return len(self.active_roster) < self.ACTIVE_ROSTER_LIMIT

    def add_to_active_roster(self, player_idx: int) -> bool:
        """一軍に選手を追加"""
        if not self.can_add_to_active_roster():
            return False
        if player_idx in self.active_roster:
            return False
        if player_idx in self.farm_roster:
            self.farm_roster.remove(player_idx)
        self.active_roster.append(player_idx)
        return True

    def remove_from_active_roster(self, player_idx: int, to_level: TeamLevel = TeamLevel.SECOND) -> bool:
        """一軍から選手を外す（二軍または三軍へ）"""
        if player_idx not in self.active_roster:
            return False
        self.active_roster.remove(player_idx)
        if to_level == TeamLevel.THIRD:
            if player_idx not in self.third_roster:
                self.third_roster.append(player_idx)
        else:
            if player_idx not in self.farm_roster:
                self.farm_roster.append(player_idx)
        # 選手のteam_levelも更新
        if 0 <= player_idx < len(self.players):
            self.players[player_idx].team_level = to_level
        return True

    def move_to_third_roster(self, player_idx: int) -> bool:
        """二軍から三軍へ移動"""
        if player_idx in self.farm_roster:
            self.farm_roster.remove(player_idx)
        elif player_idx in self.active_roster:
            self.active_roster.remove(player_idx)
        else:
            return False
        if player_idx not in self.third_roster:
            self.third_roster.append(player_idx)
        if 0 <= player_idx < len(self.players):
            self.players[player_idx].team_level = TeamLevel.THIRD
        return True

    def move_to_farm_roster(self, player_idx: int) -> bool:
        """一軍または三軍から二軍へ移動"""
        if player_idx in self.active_roster:
            self.active_roster.remove(player_idx)
        elif player_idx in self.third_roster:
            self.third_roster.remove(player_idx)
        else:
            return False
        if player_idx not in self.farm_roster:
            self.farm_roster.append(player_idx)
        if 0 <= player_idx < len(self.players):
            self.players[player_idx].team_level = TeamLevel.SECOND
        return True

    def auto_assign_rosters(self):
        """選手を自動で一軍・二軍・三軍に振り分け"""
        from models import Position as Pos

        # 選手を能力順にソート
        pitchers = [(i, p) for i, p in enumerate(self.players) if p.position == Pos.PITCHER]
        batters = [(i, p) for i, p in enumerate(self.players) if p.position != Pos.PITCHER]

        pitchers.sort(key=lambda x: x[1].stats.overall_pitching(), reverse=True)
        batters.sort(key=lambda x: x[1].stats.overall_batting(), reverse=True)

        # クリア
        self.active_roster = []
        self.farm_roster = []
        self.third_roster = []

        # 一軍: 投手12名 + 野手19名 = 31名
        first_pitchers = [idx for idx, _ in pitchers[:12]]
        first_batters = [idx for idx, _ in batters[:19]]
        self.active_roster = first_pitchers + first_batters

        # 二軍: 投手15名 + 野手25名 = 40名（残り）
        farm_pitchers = [idx for idx, _ in pitchers[12:27]]
        farm_batters = [idx for idx, _ in batters[19:44]]
        self.farm_roster = farm_pitchers + farm_batters

        # 三軍: 残り全員
        third_pitchers = [idx for idx, _ in pitchers[27:]]
        third_batters = [idx for idx, _ in batters[44:]]
        self.third_roster = third_pitchers + third_batters

        # 選手のteam_levelを更新
        for idx in self.active_roster:
            self.players[idx].team_level = TeamLevel.FIRST
        for idx in self.farm_roster:
            self.players[idx].team_level = TeamLevel.SECOND
        for idx in self.third_roster:
            self.players[idx].team_level = TeamLevel.THIRD

    def auto_set_bench(self):
        """ベンチメンバーを自動設定"""
        # スタメン・ローテ・中継ぎ・抑え以外の一軍メンバーをベンチに
        assigned = set(self.current_lineup + self.rotation + self.setup_pitchers)
        if self.closer_idx >= 0:
            assigned.add(self.closer_idx)

        self.bench_batters = []
        self.bench_pitchers = []

        for idx in self.active_roster:
            if idx not in assigned and 0 <= idx < len(self.players):
                p = self.players[idx]
                if p.position.value == "投手":
                    self.bench_pitchers.append(idx)
                else:
                    self.bench_batters.append(idx)

    def get_closer(self) -> Optional[Player]:
        if 0 <= self.closer_idx < len(self.players): return self.players[self.closer_idx]
        return None

    def get_setup_pitcher(self) -> Optional[Player]:
        if self.setup_pitchers:
            idx = self.setup_pitchers[0]
            if 0 <= idx < len(self.players): return self.players[idx]
        return None

    @property
    def winning_percentage(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

@dataclass
class DraftProspect:
    name: str
    position: Position
    pitch_type: Optional[PitchType]
    stats: PlayerStats
    age: int
    high_school: str
    potential: int
    is_developmental: bool = False

@dataclass
class Schedule:
    """シーズン日程"""
    games: List[ScheduledGame] = field(default_factory=list)
    current_game_index: int = 0
    
    def get_next_game(self, team_name: str) -> Optional[ScheduledGame]:
        """指定チームの次の試合を取得"""
        for i in range(self.current_game_index, len(self.games)):
            game = self.games[i]
            if game.status == GameStatus.SCHEDULED:
                if game.home_team_name == team_name or game.away_team_name == team_name:
                    return game
        return None
    
    def get_team_games(self, team_name: str, status: Optional[GameStatus] = None) -> List[ScheduledGame]:
        """指定チームの試合を取得"""
        games = [g for g in self.games if g.home_team_name == team_name or g.away_team_name == team_name]
        if status:
            games = [g for g in games if g.status == status]
        return games
    
    def complete_game(self, game: ScheduledGame, home_score: int, away_score: int):
        """試合を完了"""
        game.status = GameStatus.COMPLETED
        game.home_score = home_score
        game.away_score = away_score

TEAM_COLORS = {
    "Tokyo Bravers": "#FF6600",
    "Osaka Thunders": "#FFD700",
    "Nagoya Sparks": "#005BAC",
    "Hiroshima Phoenix": "#C20000",
    "Yokohama Mariners": "#0055B3",
    "Shinjuku Spirits": "#009944",
    "Fukuoka Phoenix": "#FFF200",
    "Saitama Bears": "#003366",
    "Sendai Flames": "#800000",
    "Chiba Mariners": "#222222",
    "Sapporo Fighters": "#0066B3",
    "Kobe Buffaloes": "#1B1B1B",
}

TEAM_ABBRS = {
    "Tokyo Bravers": "TB",
    "Osaka Thunders": "OT",
    "Nagoya Sparks": "NS",
    "Hiroshima Phoenix": "HP",
    "Yokohama Mariners": "YM",
    "Shinjuku Spirits": "SS",
    "Fukuoka Phoenix": "FP",
    "Saitama Bears": "SB",
    "Sendai Flames": "SF",
    "Chiba Mariners": "CM",
    "Sapporo Fighters": "SF",
    "Kobe Buffaloes": "KB",
}