# -*- coding: utf-8 -*-
"""
データモデル定義 (修正版: 外野3ポジション化・利き腕・詳細指標対応・Plate Discipline追加)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import datetime
import random


class Position(Enum):
    PITCHER = "投手"
    CATCHER = "捕手"
    FIRST = "一塁手"
    SECOND = "二塁手"
    THIRD = "三塁手"
    SHORTSTOP = "遊撃手"
    # 外野手を3ポジションに分割
    LEFT = "左翼手"
    CENTER = "中堅手"
    RIGHT = "右翼手"


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
    NORTH = "North League"
    SOUTH = "South League"


class GameStatus(Enum):
    SCHEDULED = "未消化"
    IN_PROGRESS = "試合中"
    COMPLETED = "終了"

class Hand(Enum):
    RIGHT = "右"
    LEFT = "左"
    BOTH = "両"

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
    """選手能力値（1-99スケール）"""
    # ===== 打撃能力 (Batting Ratings) =====
    contact: int = 50          # ミート
    gap: int = 50              # ギャップ（二・三塁打）
    power: int = 50            # パワー
    eye: int = 50              # 選球眼
    avoid_k: int = 50          # 三振回避
    trajectory: int = 2        # 弾道 (1:低 2:中 3:高 4:アーチ)

    # ===== 特殊打撃能力 =====
    vs_left_batter: int = 50   # 対左投手
    chance: int = 50           # チャンス

    # ===== 走塁能力 (Running Ratings) =====
    speed: int = 50            # 走力
    steal: int = 50            # 盗塁技術
    baserunning: int = 50      # 走塁技術

    # ===== バント能力 =====
    bunt_sac: int = 50         # 送りバント
    bunt_hit: int = 50         # セーフティバント

    # ===== 守備能力 (Fielding Ratings) =====
    arm: int = 50              # 肩力 (全ポジション共通)
    error: int = 50            # 捕球/エラー回避 (全ポジション共通)
    
    # 守備範囲 (Defense Range)
    # キー: "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "左翼手", "中堅手", "右翼手"
    # 以前の "外野手" キーも互換性のため維持推奨だが、基本は新キーを使用
    defense_ranges: Dict[str, int] = field(default_factory=dict)
    
    catcher_lead: int = 50     # 捕手リード
    turn_dp: int = 50          # 併殺処理

    # ===== 投球能力 (Pitching Ratings) =====
    stuff: int = 50            # 球威
    movement: int = 50         # 変化球/ムーブメント
    control: int = 50          # 制球

    # ===== 投手追加能力 =====
    velocity: int = 145        # 球速 (km/h)
    stamina: int = 50          # スタミナ
    hold_runners: int = 50     # クイック
    gb_tendency: int = 50      # ゴロ傾向
    
    vs_left_pitcher: int = 50  # 対左打者
    vs_pinch: int = 50         # 対ピンチ
    stability: int = 50        # 安定感

    # ===== 共通能力 =====
    durability: int = 50       # ケガしにくさ
    recovery: int = 50         # 回復力
    work_ethic: int = 50       # 練習態度
    intelligence: int = 50     # 野球脳
    mental: int = 50           # メンタル/打たれ強さ

    # ===== 投手専用 =====
    pitches: Dict[str, int] = field(default_factory=dict)  # 球種 {"ストレート": 60, ...}

    # ===== ヘルパーメソッド =====
    def get_defense_range(self, position: 'Position') -> int:
        val = self.defense_ranges.get(position.value, 0)
        # 互換性: 具体的な外野ポジションがない場合、汎用"外野手"の値を使う
        if val == 0 and position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            val = self.defense_ranges.get("外野手", 1)
        return max(1, val)

    def set_defense_range(self, position: 'Position', value: int):
        self.defense_ranges[position.value] = max(1, min(99, value))

    @property
    def effective_catcher_lead(self) -> int:
        if self.get_defense_range(Position.CATCHER) < 2:
            return 1
        return self.catcher_lead

    # ===== 互換性・エイリアス =====
    @property
    def run(self) -> int: return self.speed
    
    @property
    def fielding(self) -> int:
        max_range = max(self.defense_ranges.values()) if self.defense_ranges else 1
        return max_range

    @property
    def catching(self) -> int: return self.error
    @property
    def breaking(self) -> int: return self.stuff
    @property
    def bunt(self) -> int: return self.bunt_sac
    @property
    def injury_res(self) -> int: return self.durability
    @property
    def quick(self) -> int: return self.hold_runners
    @property
    def inf_dp(self) -> int: return self.turn_dp
    @property
    def catcher_ab(self) -> int: return self.effective_catcher_lead
    @property
    def breaking_balls(self) -> List[str]: return list(self.pitches.keys()) if self.pitches else []

    @run.setter
    def run(self, value): self.speed = value
    @breaking.setter
    def breaking(self, value): self.stuff = value
    @bunt.setter
    def bunt(self, value): self.bunt_sac = value
    
    @property
    def inf_arm(self) -> int: return self.arm
    @inf_arm.setter
    def inf_arm(self, value): self.arm = value
    
    @property
    def of_arm(self) -> int: return self.arm
    @of_arm.setter
    def of_arm(self, value): self.arm = value
    
    @property
    def catcher_arm(self) -> int: return self.arm
    @catcher_arm.setter
    def catcher_arm(self, value): self.arm = value
    
    @property
    def inf_error(self) -> int: return self.error
    @inf_error.setter
    def inf_error(self, value): self.error = value
    
    @property
    def of_error(self) -> int: return self.error
    @of_error.setter
    def of_error(self, value): self.error = value

    @property
    def catcher_ability(self) -> int: return self.catcher_lead
    @catcher_ability.setter
    def catcher_ability(self, value): self.catcher_lead = value

    def to_star_rating(self, value: int) -> float:
        return max(0.5, min(5.0, value / 20))

    def overall_batting(self, position: Optional[Position] = None) -> float:
        batting = (self.contact * 2 + self.gap * 1.5 + self.power * 1.5 + self.eye + self.avoid_k) / 7
        running = (self.speed + self.steal + self.baserunning) / 3
        
        if position:
            def_range = self.get_defense_range(position)
        else:
            def_range = max(self.defense_ranges.values()) if self.defense_ranges else 1
            
        defense = (def_range * 1.5 + self.error + self.arm) / 3.5
        
        if position == Position.CATCHER or (not position and self.get_defense_range(Position.CATCHER) > 40):
             defense = (defense * 3 + self.effective_catcher_lead) / 4

        return (batting * 0.5 + running * 0.2 + defense * 0.3)

    def overall_pitching(self) -> float:
        vel_rating = self.kmh_to_rating(self.velocity)
        return (self.stuff * 2 + self.movement * 1.5 + self.control * 2 + vel_rating + self.stamina * 0.5) / 7

    def speed_to_kmh(self) -> int:
        return self.velocity

    @staticmethod
    def kmh_to_rating(kmh: int) -> int:
        val = (kmh - 130) * 2 + 30
        return int(max(1, min(99, val)))

    def get_rank(self, value: int) -> str:
        if value >= 90: return "S"
        elif value >= 80: return "A"
        elif value >= 70: return "B"
        elif value >= 60: return "C"
        elif value >= 50: return "D"
        elif value >= 40: return "E"
        elif value >= 30: return "F"
        else: return "G"

    def get_rank_color(self, value: int) -> str:
        if value >= 90: return "#FFD700"
        elif value >= 80: return "#FF4500"
        elif value >= 70: return "#FFA500"
        elif value >= 60: return "#FFFF00"
        elif value >= 50: return "#32CD32"
        elif value >= 40: return "#1E90FF"
        elif value >= 30: return "#4682B4"
        return "#808080"

    def get_star_display(self, value: int) -> str:
        stars = self.to_star_rating(value)
        full = int(stars)
        half = 1 if stars - full >= 0.5 else 0
        return "★" * full + ("☆" if half else "")

    def get_breaking_balls_display(self) -> str:
        if not self.pitches: return "なし"
        return "、".join(self.pitches.keys())


@dataclass
class Stadium:
    """球場データとパークファクター"""
    name: str
    capacity: int = 30000
    
    # Park Factors (1.00 = League Average)
    pf_runs: float = 1.00    # 得点
    pf_hr: float = 1.00      # 本塁打
    pf_1b: float = 1.00      # 単打
    pf_2b: float = 1.00      # 二塁打
    pf_3b: float = 1.00      # 三塁打
    pf_so: float = 1.00      # 奪三振 (高いほど三振しやすい)
    pf_bb: float = 1.00      # 与四球 (高いほど四球が出やすい)

    def get_factor(self, item: str) -> float:
        return getattr(self, f"pf_{item.lower()}", 1.0)


@dataclass
class PlayerRecord:
    """選手成績（基本統計 + 高度な守備指標 + 計算済み指標）"""
    # Basic
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
    reach_on_error: int = 0
    strikeouts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    sacrifice_hits: int = 0
    sacrifice_flies: int = 0
    grounded_into_dp: int = 0
    home_games: int = 0          # 本拠地での出場試合数 (野手)
    home_games_pitched: int = 0  # 本拠地での登板試合数 (投手)

    # 経験したパークファクターの累積値
    sum_pf_runs: float = 0.0

    # Pitching Basic
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

    # Advanced Tracking
    total_bases: int = 0
    ground_balls: int = 0
    fly_balls: int = 0
    line_drives: int = 0
    popups: int = 0
    hard_hit_balls: int = 0
    
    # 打球質・方向詳細カウンター
    medium_hit_balls: int = 0
    soft_hit_balls: int = 0
    
    pull_balls: int = 0
    center_balls: int = 0
    oppo_balls: int = 0

    balls_in_play: int = 0

    # Plate Discipline / Pitch Tracking (New)
    pitches_seen: int = 0      # 打者用：見た投球数
    pitches_thrown: int = 0    # 投手用：投げた投球数
    strikes_thrown: int = 0
    balls_thrown: int = 0
    first_pitch_strikes: int = 0
    
    zone_pitches: int = 0      # ゾーン内投球数
    chase_pitches: int = 0     # ゾーン外投球数
    zone_swings: int = 0       # ゾーン内スイング数
    chase_swings: int = 0      # ゾーン外スイング数
    zone_contact: int = 0      # ゾーン内コンタクト数
    chase_contact: int = 0     # ゾーン外コンタクト数
    swings: int = 0            # 総スイング数
    whiffs: int = 0            # 空振り数 (Swinging Strikes)

    ground_outs: int = 0
    fly_outs: int = 0
    quality_starts: int = 0
    complete_games: int = 0
    shutouts: int = 0

    # --- Defensive Metrics (Source Data) ---
    def_opportunities: int = 0 
    def_plays_made: int = 0    
    def_difficulty_sum: float = 0.0 
    def_drs_raw: float = 0.0 

    # --- Computed Advanced Stats (Cached/Calculated by Stats Engine) ---
    woba_val: float = 0.0
    wrc_val: float = 0.0
    wrc_plus_val: float = 0.0
    war_val: float = 0.0
    fip_val: float = 0.0
    xfip_val: float = 0.0
    uzr_val: float = 0.0
    drs_val: float = 0.0
    
    wsb_val: float = 0.0
    ubr_val: float = 0.0
    
    # --- Basic Properties ---
    @property
    def batting_average(self) -> float:
        return self.hits / self.at_bats if self.at_bats > 0 else 0.0

    @property
    def era(self) -> float:
        return (self.earned_runs * 9) / self.innings_pitched if self.innings_pitched > 0 else 0.0

    @property
    def winning_percentage(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    @property
    def singles(self) -> int:
        return self.hits - self.doubles - self.triples - self.home_runs

    @property
    def obp(self) -> float:
        denominator = self.at_bats + self.walks + self.hit_by_pitch + self.sacrifice_flies
        if denominator == 0: return 0.0
        return (self.hits + self.walks + self.hit_by_pitch) / denominator

    @property
    def slg(self) -> float:
        if self.at_bats == 0: return 0.0
        tb = self.singles + (self.doubles * 2) + (self.triples * 3) + (self.home_runs * 4)
        return tb / self.at_bats

    @property
    def ops(self) -> float:
        return self.obp + self.slg

    # --- Plate Discipline Properties (New) ---
    @property
    def o_swing_pct(self) -> float:
        return self.chase_swings / self.chase_pitches if self.chase_pitches > 0 else 0.0
    
    @property
    def z_swing_pct(self) -> float:
        return self.zone_swings / self.zone_pitches if self.zone_pitches > 0 else 0.0
        
    @property
    def swing_pct(self) -> float:
        # 打者の場合pitches_seen、投手の場合pitches_thrownを分母にする
        total = self.pitches_seen if self.pitches_seen > 0 else self.pitches_thrown
        return self.swings / total if total > 0 else 0.0

    @property
    def o_contact_pct(self) -> float:
        return self.chase_contact / self.chase_swings if self.chase_swings > 0 else 0.0

    @property
    def z_contact_pct(self) -> float:
        return self.zone_contact / self.zone_swings if self.zone_swings > 0 else 0.0

    @property
    def contact_pct(self) -> float:
        return (self.zone_contact + self.chase_contact) / self.swings if self.swings > 0 else 0.0
        
    @property
    def whiff_pct(self) -> float:
        return self.whiffs / self.swings if self.swings > 0 else 0.0
        
    @property
    def swstr_pct(self) -> float:
        total = self.pitches_seen if self.pitches_seen > 0 else self.pitches_thrown
        return self.whiffs / total if total > 0 else 0.0

    # --- Sabermetrics Properties ---
    @property
    def k_pct(self) -> float:
        return self.strikeouts / self.plate_appearances if self.plate_appearances > 0 else 0.0

    @property
    def bb_pct(self) -> float:
        return self.walks / self.plate_appearances if self.plate_appearances > 0 else 0.0

    @property
    def hard_pct(self) -> float:
        bip = self.balls_in_play
        return self.hard_hit_balls / bip if bip > 0 else 0.0

    @property
    def mid_pct(self) -> float:
        bip = self.balls_in_play
        return self.medium_hit_balls / bip if bip > 0 else 0.0

    @property
    def soft_pct(self) -> float:
        bip = self.balls_in_play
        return self.soft_hit_balls / bip if bip > 0 else 0.0

    @property
    def gb_pct(self) -> float:
        bip = self.balls_in_play
        return self.ground_balls / bip if bip > 0 else 0.0

    @property
    def fb_pct(self) -> float:
        bip = self.balls_in_play
        return self.fly_balls / bip if bip > 0 else 0.0

    @property
    def ld_pct(self) -> float:
        bip = self.balls_in_play
        return self.line_drives / bip if bip > 0 else 0.0

    @property
    def iffb_pct(self) -> float:
        total_fb = self.fly_balls + self.popups
        return self.popups / total_fb if total_fb > 0 else 0.0

    @property
    def hr_fb(self) -> float:
        return self.home_runs / self.fly_balls if self.fly_balls > 0 else 0.0

    @property
    def pull_pct(self) -> float:
        total = self.pull_balls + self.center_balls + self.oppo_balls
        return self.pull_balls / total if total > 0 else 0.0

    @property
    def cent_pct(self) -> float:
        total = self.pull_balls + self.center_balls + self.oppo_balls
        return self.center_balls / total if total > 0 else 0.0

    @property
    def oppo_pct(self) -> float:
        total = self.pull_balls + self.center_balls + self.oppo_balls
        return self.oppo_balls / total if total > 0 else 0.0
    
    @property
    def wsb(self) -> float:
        return self.wsb_val
    
    @property
    def ubr(self) -> float:
        return self.ubr_val

    @property
    def iso(self) -> float:
        return self.slg - self.batting_average

    @property
    def babip(self) -> float:
        denominator = self.at_bats - self.strikeouts - self.home_runs + self.sacrifice_flies
        if denominator <= 0: return 0.0
        return (self.hits - self.home_runs) / denominator

    @property
    def woba(self) -> float:
        return self.woba_val

    @property
    def wrc(self) -> float:
        return self.wrc_val

    @property
    def wrc_plus(self) -> float:
        return self.wrc_plus_val

    @property
    def war(self) -> float:
        return self.war_val
        
    @property
    def fip(self) -> float:
        if self.fip_val == 0.0 and self.innings_pitched > 0:
             return (13 * self.home_runs_allowed + 3 * (self.walks_allowed + self.hit_batters) - 2 * self.strikeouts_pitched) / self.innings_pitched + 3.10
        return self.fip_val

    @property
    def xfip(self) -> float:
        if self.xfip_val == 0.0:
             return self.fip 
        return self.xfip_val

    @property
    def whip(self) -> float:
        if self.innings_pitched == 0: return 0.0
        return (self.walks_allowed + self.hits_allowed) / self.innings_pitched

    @property
    def k_per_9(self) -> float:
        if self.innings_pitched == 0: return 0.0
        return (self.strikeouts_pitched * 9) / self.innings_pitched

    @property
    def bb_per_9(self) -> float:
        if self.innings_pitched == 0: return 0.0
        return (self.walks_allowed * 9) / self.innings_pitched
    
    @property
    def k_bb_ratio(self) -> float:
        if self.walks_allowed == 0: return float(self.strikeouts_pitched)
        return self.strikeouts_pitched / self.walks_allowed

    @property
    def hr_per_9(self) -> float:
        if self.innings_pitched == 0: return 0.0
        return (self.home_runs_allowed * 9) / self.innings_pitched
        
    @property
    def h_per_9(self) -> float:
        if self.innings_pitched == 0: return 0.0
        return (self.hits_allowed * 9) / self.innings_pitched

    @property
    def k_rate_pitched(self) -> float:
        total_batters = self.hits_allowed + self.walks_allowed + self.hit_batters + self.strikeouts_pitched + self.ground_outs + self.fly_outs 
        if total_batters == 0: return 0.0
        return self.strikeouts_pitched / total_batters

    @property
    def bb_rate_pitched(self) -> float:
        total_batters = self.hits_allowed + self.walks_allowed + self.hit_batters + self.strikeouts_pitched + self.ground_outs + self.fly_outs
        if total_batters == 0: return 0.0
        return self.walks_allowed / total_batters
        
    @property
    def bb_rate(self) -> float:
        if self.plate_appearances == 0: return 0.0
        return self.walks / self.plate_appearances

    @property
    def k_rate(self) -> float:
        if self.plate_appearances == 0: return 0.0
        return self.strikeouts / self.plate_appearances
        
    @property
    def sb_rate(self) -> float:
        attempts = self.stolen_bases + self.caught_stealing
        if attempts == 0: return 0.0
        return self.stolen_bases / attempts

    @property
    def lob_rate(self) -> float:
        num = (self.hits_allowed + self.walks_allowed + self.hit_batters) - self.runs_allowed
        denom = (self.hits_allowed + self.walks_allowed + self.hit_batters) - (1.4 * self.home_runs_allowed)
        if denom <= 0: return 0.72
        return num / denom

    @property
    def uzr(self) -> float:
        return self.uzr_val
    
    @property
    def drs(self) -> float:
        return self.drs_val

    def reset(self):
        for field_name in self.__dataclass_fields__:
            if field_name not in ['games', 'games_pitched', 'games_started']:
                setattr(self, field_name, 0 if isinstance(getattr(self, field_name), int) else 0.0)

    def merge_from(self, other: 'PlayerRecord'):
        for field_name in self.__dataclass_fields__:
            current = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if isinstance(current, (int, float)):
                setattr(self, field_name, current + other_val)


@dataclass
class DetailedSeasonStats:
    year: int = 0
    team_level: TeamLevel = None
    record: PlayerRecord = field(default_factory=PlayerRecord)
    monthly_stats: Dict[int, PlayerRecord] = field(default_factory=dict)
    vs_team_stats: Dict[str, PlayerRecord] = field(default_factory=dict)
    vs_left_stats: PlayerRecord = field(default_factory=PlayerRecord)
    vs_right_stats: PlayerRecord = field(default_factory=PlayerRecord)
    risp_stats: PlayerRecord = field(default_factory=PlayerRecord)
    close_game_stats: PlayerRecord = field(default_factory=PlayerRecord)
    home_stats: PlayerRecord = field(default_factory=PlayerRecord)
    away_stats: PlayerRecord = field(default_factory=PlayerRecord)


@dataclass
class CareerStats:
    season_stats: Dict[int, Dict[str, DetailedSeasonStats]] = field(default_factory=dict)
    career_first: PlayerRecord = field(default_factory=PlayerRecord)
    career_second: PlayerRecord = field(default_factory=PlayerRecord)
    career_third: PlayerRecord = field(default_factory=PlayerRecord)
    career_total: PlayerRecord = field(default_factory=PlayerRecord)

    def add_season(self, year: int, team_level: TeamLevel, stats: DetailedSeasonStats):
        if year not in self.season_stats:
            self.season_stats[year] = {}
        self.season_stats[year][team_level.value if team_level else "一軍"] = stats

        if team_level == TeamLevel.FIRST or team_level is None:
            self.career_first.merge_from(stats.record)
        elif team_level == TeamLevel.SECOND:
            self.career_second.merge_from(stats.record)
        elif team_level == TeamLevel.THIRD:
            self.career_third.merge_from(stats.record)
        self.career_total.merge_from(stats.record)

    def get_season(self, year: int, team_level: TeamLevel = None) -> Optional[DetailedSeasonStats]:
        if year not in self.season_stats:
            return None
        level_key = team_level.value if team_level else "一軍"
        return self.season_stats[year].get(level_key)

    def get_all_seasons(self) -> List[Tuple[int, str, DetailedSeasonStats]]:
        result = []
        for year in sorted(self.season_stats.keys()):
            for level, stats in self.season_stats[year].items():
                result.append((year, level, stats))
        return result


@dataclass(eq=False)
class Player:
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    stats: PlayerStats = field(default_factory=PlayerStats)
    record: PlayerRecord = field(default_factory=PlayerRecord)
    age: int = 25
    status: PlayerStatus = PlayerStatus.ACTIVE
    uniform_number: int = 0
    is_foreign: bool = False
    salary: int = 10000000
    years_pro: int = 0
    draft_round: int = 0

    is_developmental: bool = False
    team_level: 'TeamLevel' = None

    starter_aptitude: int = 50
    middle_aptitude: int = 50
    closer_aptitude: int = 50

    special_abilities: Optional[object] = None
    player_status: Optional[object] = None
    growth: Optional[object] = None

    record_farm: PlayerRecord = field(default_factory=PlayerRecord)
    record_third: PlayerRecord = field(default_factory=PlayerRecord)

    career_stats: CareerStats = field(default_factory=CareerStats)
    
    condition: int = 5
    
    days_rest: int = 6  # 登板間隔 (中n日)
    
    bats: str = "右"
    throws: str = "右"

    def __post_init__(self):
        if self.team_level is None:
            self.team_level = TeamLevel.FIRST

    def get_record_by_level(self, level: TeamLevel) -> PlayerRecord:
        if level == TeamLevel.FIRST: return self.record
        elif level == TeamLevel.SECOND: return self.record_farm
        elif level == TeamLevel.THIRD: return self.record_third
        return self.record

    def get_current_season_total(self) -> PlayerRecord:
        total = PlayerRecord()
        total.merge_from(self.record)
        total.merge_from(self.record_farm)
        total.merge_from(self.record_third)
        return total

    def reset_season_records(self):
        self.record = PlayerRecord()
        self.record_farm = PlayerRecord()
        self.record_third = PlayerRecord()

    def archive_season(self, year: int):
        if self.record.games > 0 or self.record.games_pitched > 0:
            season_first = DetailedSeasonStats(year=year, team_level=TeamLevel.FIRST, record=self.record)
            self.career_stats.add_season(year, TeamLevel.FIRST, season_first)

        if self.record_farm.games > 0 or self.record_farm.games_pitched > 0:
            season_second = DetailedSeasonStats(year=year, team_level=TeamLevel.SECOND, record=self.record_farm)
            self.career_stats.add_season(year, TeamLevel.SECOND, season_second)

        if self.record_third.games > 0 or self.record_third.games_pitched > 0:
            season_third = DetailedSeasonStats(year=year, team_level=TeamLevel.THIRD, record=self.record_third)
            self.career_stats.add_season(year, TeamLevel.THIRD, season_third)

    def add_sub_position(self, pos: Position, rating: int = 50):
        if isinstance(rating, float) and rating <= 1.0:
            rating = int(rating * 99)
        self.stats.set_defense_range(pos, rating)

    def can_play_position(self, pos: Position) -> bool:
        if self.position == pos: return True
        return self.stats.get_defense_range(pos) >= 2
    
    def get_position_rating(self, pos: Position) -> float:
        if self.position == pos: return 1.0
        val = self.stats.get_defense_range(pos)
        if val < 2: return 0.0
        return val / 99.0

    def fix_main_position(self):
        if self.position == Position.PITCHER: return
        best_pos = self.position
        max_val = self.stats.get_defense_range(self.position)
        for pos_name, val in self.stats.defense_ranges.items():
            if pos_name == Position.PITCHER.value: continue
            current_pos_enum = None
            for p in Position:
                if p.value == pos_name:
                    current_pos_enum = p
                    break
            if current_pos_enum and val > max_val:
                max_val = val
                best_pos = current_pos_enum
        if best_pos != self.position:
            self.position = best_pos
            
    def update_condition(self):
        change = random.choices([-1, 0, 1], weights=[0.25, 0.5, 0.25])[0]
        self.condition = max(1, min(9, self.condition + change))

    @property
    def overall_rating(self) -> int:
        if self.position == Position.PITCHER:
            val = self.stats.overall_pitching()
        else:
            val = self.stats.overall_batting(self.position)
        rating = (val / 99) ** 2 * 999
        return max(1, min(999, int(rating)))


@dataclass(eq=False)
class Team:
    name: str
    league: League
    stadium: Optional[Stadium] = None
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
    
    closers: List[int] = field(default_factory=list)

    bench_batters: List[int] = field(default_factory=list)
    bench_pitchers: List[int] = field(default_factory=list)
    active_roster: List[int] = field(default_factory=list)
    farm_roster: List[int] = field(default_factory=list)
    third_roster: List[int] = field(default_factory=list)

    farm_lineup: List[int] = field(default_factory=list)
    farm_rotation: List[int] = field(default_factory=list)
    third_lineup: List[int] = field(default_factory=list)
    third_rotation: List[int] = field(default_factory=list)

    ACTIVE_ROSTER_LIMIT = 31
    FARM_ROSTER_LIMIT = 40
    THIRD_ROSTER_LIMIT = 30
    
    @property
    def closer_idx(self) -> int:
        return self.closers[0] if self.closers else -1
    
    @closer_idx.setter
    def closer_idx(self, val: int):
        if val == -1:
            self.closers = []
        else:
            if not self.closers:
                self.closers = [val]
            else:
                self.closers[0] = val

    def get_today_starter(self) -> Optional[Player]:
        if not self.rotation: return None
        
        candidates = []
        for idx in self.rotation:
            if 0 <= idx < len(self.players):
                candidates.append(self.players[idx])
        
        if not candidates: return None

        best_candidate = None
        
        for p in candidates:
            if p.days_rest >= 5:
                best_candidate = p
                break
        
        if not best_candidate:
            for p in candidates:
                if p.days_rest >= 4:
                    best_candidate = p
                    break
        
        if not best_candidate:
            best_candidate = max(candidates, key=lambda p: p.days_rest)

        return best_candidate

    def auto_assign_pitching_roles(self, level: TeamLevel = TeamLevel.FIRST):
        """指定レベルの投手陣を先発・中継ぎ・抑えに最適配分する"""
        roster_players = self.get_players_by_level(level)
        pitchers = [p for p in roster_players if p.position == Position.PITCHER]
        if not pitchers: return

        pitcher_indices = [self.players.index(p) for p in pitchers]
        
        def starter_score(p: Player):
            rating = p.stats.overall_pitching()
            stamina = p.stats.stamina
            aptitude = p.starter_aptitude
            return rating * 0.4 + stamina * 0.3 + aptitude * 0.3

        def reliever_score(p: Player):
            rating = p.stats.overall_pitching()
            velocity = p.stats.velocity
            aptitude = max(p.middle_aptitude, p.closer_aptitude)
            return rating * 0.4 + (velocity - 130) * 0.5 + aptitude * 0.3

        pitchers.sort(key=starter_score, reverse=True)
        starters = pitchers[:6]
        starter_indices = [self.players.index(p) for p in starters]

        remaining_pitchers = pitchers[6:]
        
        remaining_pitchers.sort(key=reliever_score, reverse=True)
        closer = []
        closer_idx = []
        if remaining_pitchers:
            closer = [remaining_pitchers[0]]
            closer_idx = [self.players.index(remaining_pitchers[0])]
            remaining_pitchers = remaining_pitchers[1:]

        setups = remaining_pitchers[:2]
        setup_indices = [self.players.index(p) for p in setups]
        
        others = remaining_pitchers[2:]
        other_indices = [self.players.index(p) for p in others]

        if level == TeamLevel.FIRST:
            self.rotation = starter_indices
            self.closers = closer_idx
            self.setup_pitchers = setup_indices
            self.bench_pitchers = other_indices
        elif level == TeamLevel.SECOND:
            self.farm_rotation = starter_indices
        elif level == TeamLevel.THIRD:
            self.third_rotation = starter_indices

    def get_roster_players(self) -> List[Player]:
        return [p for p in self.players if not p.is_developmental]

    def get_active_roster_players(self) -> List[Player]:
        return [self.players[i] for i in self.active_roster if 0 <= i < len(self.players)]

    def get_farm_roster_players(self) -> List[Player]:
        return [self.players[i] for i in self.farm_roster if 0 <= i < len(self.players)]

    def get_third_roster_players(self) -> List[Player]:
        return [self.players[i] for i in self.third_roster if 0 <= i < len(self.players)]

    def get_players_by_level(self, level: TeamLevel) -> List[Player]:
        if level == TeamLevel.FIRST: return self.get_active_roster_players()
        elif level == TeamLevel.SECOND: return self.get_farm_roster_players()
        elif level == TeamLevel.THIRD: return self.get_third_roster_players()
        return []

    def get_active_roster_count(self) -> int:
        return len(self.active_roster)

    def can_add_to_active_roster(self) -> bool:
        return len(self.active_roster) < self.ACTIVE_ROSTER_LIMIT

    def add_to_active_roster(self, player_idx: int) -> bool:
        if not self.can_add_to_active_roster(): return False
        if player_idx in self.active_roster: return False
        if player_idx in self.farm_roster: self.farm_roster.remove(player_idx)
        self.active_roster.append(player_idx)
        return True

    def remove_from_active_roster(self, player_idx: int, to_level: TeamLevel = TeamLevel.SECOND) -> bool:
        if player_idx not in self.active_roster: return False
        self.active_roster.remove(player_idx)
        if to_level == TeamLevel.THIRD:
            if player_idx not in self.third_roster: self.third_roster.append(player_idx)
        else:
            if player_idx not in self.farm_roster: self.farm_roster.append(player_idx)
        if 0 <= player_idx < len(self.players):
            self.players[player_idx].team_level = to_level
        return True

    def move_to_third_roster(self, player_idx: int) -> bool:
        if player_idx in self.farm_roster: self.farm_roster.remove(player_idx)
        elif player_idx in self.active_roster: self.active_roster.remove(player_idx)
        else: return False
        if player_idx not in self.third_roster: self.third_roster.append(player_idx)
        if 0 <= player_idx < len(self.players):
            self.players[player_idx].team_level = TeamLevel.THIRD
        return True

    def move_to_farm_roster(self, player_idx: int) -> bool:
        if player_idx in self.active_roster: self.active_roster.remove(player_idx)
        elif player_idx in self.third_roster: self.third_roster.remove(player_idx)
        else: return False
        if player_idx not in self.farm_roster: self.farm_roster.append(player_idx)
        if 0 <= player_idx < len(self.players):
            self.players[player_idx].team_level = TeamLevel.SECOND
        return True

    def auto_assign_rosters(self):
        from models import Position as Pos
        pitchers = [(i, p) for i, p in enumerate(self.players) if p.position == Pos.PITCHER]
        batters = [(i, p) for i, p in enumerate(self.players) if p.position != Pos.PITCHER]
        pitchers.sort(key=lambda x: x[1].stats.overall_pitching(), reverse=True)
        batters.sort(key=lambda x: x[1].stats.overall_batting(), reverse=True)
        self.active_roster = []
        self.farm_roster = []
        self.third_roster = []
        first_pitchers = [idx for idx, _ in pitchers[:12]]
        first_batters = [idx for idx, _ in batters[:19]]
        self.active_roster = first_pitchers + first_batters
        farm_pitchers = [idx for idx, _ in pitchers[12:27]]
        farm_batters = [idx for idx, _ in batters[19:44]]
        self.farm_roster = farm_pitchers + farm_batters
        third_pitchers = [idx for idx, _ in pitchers[27:]]
        third_batters = [idx for idx, _ in batters[44:]]
        self.third_roster = third_pitchers + third_batters
        for idx in self.active_roster: self.players[idx].team_level = TeamLevel.FIRST
        for idx in self.farm_roster: self.players[idx].team_level = TeamLevel.SECOND
        for idx in self.third_roster: self.players[idx].team_level = TeamLevel.THIRD

    def auto_set_bench(self):
        self.auto_assign_pitching_roles(TeamLevel.FIRST)
        
        assigned = set(self.current_lineup)
        self.bench_batters = []
        
        for idx in self.active_roster:
            if idx not in assigned and 0 <= idx < len(self.players):
                p = self.players[idx]
                if p.position.value != "投手":
                    self.bench_batters.append(idx)

    def get_closer(self) -> Optional[Player]:
        if self.closers and 0 <= self.closers[0] < len(self.players):
            return self.players[self.closers[0]]
        return None

    def get_setup_pitcher(self) -> Optional[Player]:
        if self.setup_pitchers:
            for idx in self.setup_pitchers:
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
    games: List[ScheduledGame] = field(default_factory=list)
    current_game_index: int = 0
    
    def get_next_game(self, team_name: str) -> Optional[ScheduledGame]:
        for i in range(self.current_game_index, len(self.games)):
            game = self.games[i]
            if game.status == GameStatus.SCHEDULED:
                if game.home_team_name == team_name or game.away_team_name == team_name:
                    return game
        return None
    
    def get_team_games(self, team_name: str, status: Optional[GameStatus] = None) -> List[ScheduledGame]:
        games = [g for g in self.games if g.home_team_name == team_name or g.away_team_name == team_name]
        if status:
            games = [g for g in games if g.status == status]
        return games
    
    def complete_game(self, game: ScheduledGame, home_score: int, away_score: int):
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

def generate_best_lineup(team: Team, roster_players: List[Player]) -> List[int]:
    """
    指定された選手リストから、守備位置を考慮した最適オーダー(9人)を生成して返す。
    外野手をLeft/Center/Rightに最適配分する。
    """
    
    # 優先順位: 捕手 -> 遊撃 -> 二塁 -> 中堅 -> 三塁 -> 右翼 -> 左翼 -> 一塁
    def_priority = [
        (Position.CATCHER, "捕手", 1.5),
        (Position.SHORTSTOP, "遊撃手", 1.4),
        (Position.SECOND, "二塁手", 1.3),
        (Position.CENTER, "中堅手", 1.3), 
        (Position.THIRD, "三塁手", 1.0),
        (Position.RIGHT, "右翼手", 1.1),
        (Position.LEFT, "左翼手", 0.9),
        (Position.FIRST, "一塁手", 0.8)
    ]
    
    candidates = {}
    for p in roster_players:
        if p.position == Position.PITCHER: continue
        try:
            original_idx = team.players.index(p)
            candidates[original_idx] = p
        except ValueError:
            continue

    selected_starters = {} # position_name -> player_idx
    used_indices = set()
    
    def calculate_score(player, pos_name, weight):
        # defense_ranges から適正を取得
        # 外野ポジションの場合は、個別の適正がなければ汎用"外野手"の値を見る
        aptitude = player.stats.get_defense_range(getattr(Position, pos_name_enum_key))
        if aptitude < 20: return -1
        
        bat_score = (player.stats.contact * 1.0 + player.stats.power * 1.2 + 
                     player.stats.speed * 0.5 + player.stats.eye * 0.5)
        
        # 守備スコア補正: 中堅は走力、右翼は肩力を重視
        def_bonus = 0
        if pos_name == "中堅手": def_bonus = player.stats.speed * 0.5
        if pos_name == "右翼手": def_bonus = player.stats.arm * 0.5
        
        def_score = (aptitude * 1.5 + player.stats.error * 0.5 + player.stats.arm * 0.5 + def_bonus)
        
        return bat_score + (def_score * weight)

    for pos_enum, pos_name, weight in def_priority:
        # pos_enumに対応するキー名を取得 (例: CENTER -> "CENTER")
        pos_name_enum_key = pos_enum.name
        
        best_idx = -1
        best_score = -1.0
        
        for idx, p in candidates.items():
            if idx in used_indices: continue
            
            score = calculate_score(p, pos_name, weight)
            if score > best_score:
                best_score = score
                best_idx = idx
        
        if best_idx != -1:
            selected_starters[pos_name] = best_idx
            used_indices.add(best_idx)
    
    dh_best_idx = -1
    dh_best_score = -1
    for idx, p in candidates.items():
        if idx in used_indices: continue
        score = p.stats.overall_batting()
        if score > dh_best_score:
            dh_best_score = score
            dh_best_idx = idx
            
    if dh_best_idx != -1:
        selected_starters["DH"] = dh_best_idx
        used_indices.add(dh_best_idx)

    lineup_candidates = []
    # 辞書順ではなく、一般的な打順構成のためのスタメンリストを作成
    # ポジションマップからリストへ
    for pos, idx in selected_starters.items():
        lineup_candidates.append(idx)
        
    lineup_candidates.sort(key=lambda i: team.players[i].stats.overall_batting(), reverse=True)
    
    # 人数が足りない場合の補充
    if len(lineup_candidates) < 9:
        remaining = [i for i in candidates.keys() if i not in used_indices]
        remaining.sort(key=lambda i: team.players[i].stats.overall_batting(), reverse=True)
        lineup_candidates.extend(remaining[:9 - len(lineup_candidates)])
    
    return lineup_candidates[:9]