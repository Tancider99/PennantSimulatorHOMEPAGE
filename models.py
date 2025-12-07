# NPBチームカラー・略称定義
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
# -*- coding: utf-8 -*-
"""
データモデル定義
"""
from dataclasses import dataclass, field
from typing import List, Optional
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
    """一軍/二軍/三軍"""
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
    """試合結果"""
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    date: str
    game_number: int


@dataclass
class ScheduledGame:
    """予定試合"""
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
        """月を取得"""
        try:
            return int(self.date.split('-')[1])
        except:
            return 0
    
    @property
    def day(self) -> int:
        """日を取得"""
        try:
            return int(self.date.split('-')[2])
        except:
            return 0
    
    @property
    def year(self) -> int:
        """年を取得"""
        try:
            return int(self.date.split('-')[0])
        except:
            return 0
    
    def get_winner(self) -> Optional[str]:
        """勝者チーム名を取得"""
        if not self.is_completed:
            return None
        if self.home_score > self.away_score:
            return self.home_team_name
        elif self.away_score > self.home_score:
            return self.away_team_name
        return None  # 引き分け
    
    def is_draw(self) -> bool:
        """引き分けかどうか"""
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
    """選手能力値（パワプロ風 S/A/B/C/D/E/F/G ランク対応）
    
    基本能力値は1〜99の範囲
    表示時はランクに変換（S=90+, A=80-89, B=70-79, C=60-69, D=50-59, E=40-49, F=30-39, G=1-29）
    50が平均的なプロ選手レベル
    """
    # ===== 野手基本能力 =====
    contact: int = 50      # ミート（打率への影響）
    power: int = 50        # パワー（長打力）
    run: int = 50          # 走力（盗塁、走塁）
    arm: int = 50          # 肩力（送球速度）
    fielding: int = 50     # 守備力（捕球、反応）
    catching: int = 50     # 捕球（エラー率）
    
    # ===== 投手基本能力 =====
    speed: int = 50        # 球速
    control: int = 50      # コントロール
    stamina: int = 50      # スタミナ
    breaking: int = 50     # 変化球キレ
    
    # ===== 特殊能力関連 =====
    mental: int = 50       # メンタル強さ
    clutch: int = 50       # チャンス（チャンス時の強さ）
    consistency: int = 50  # 安定感
    vs_left: int = 50      # 対左投手/打者
    pinch_hit: int = 50    # 代打適性
    stealing: int = 50     # 盗塁技術
    baserunning: int = 50  # 走塁センス
    
    # ===== 投手専用 =====
    breaking_balls: List[str] = field(default_factory=list)  # 持ち球リスト
    best_pitch: str = ""   # 決め球
    pitch_repertoire: dict = field(default_factory=dict)  # 球種別変化量 {"スライダー": 4, ...}
    
    # ===== 弾道（野手用、1-4） =====
    trajectory: int = 2    # 1=グラウンダー, 2=ライナー, 3=普通, 4=フライ
    
    def overall_batting(self) -> float:
        """野手の総合値を計算（1-99スケール）"""
        # 能力値は既に1-99スケール
        return (self.contact * 2 + self.power * 1.5 + self.run + self.clutch * 0.5) / 5.0
    
    def overall_pitching(self) -> float:
        """投手の総合値を計算（1-99スケール）"""
        return (self.speed * 1.5 + self.control * 2 + self.stamina + self.breaking * 1.5 + self.mental * 0.5) / 6.5
    
    def speed_to_kmh(self) -> int:
        """球速能力値(1-99)をkm/h表示に変換
        
        1 → 130km/h (最低)
        50 → 145km/h (平均的プロ投手)
        99 → 165km/h (最高)
        
        計算式: 130 + (speed - 1) * 35 / 98
        """
        return int(130 + (self.speed - 1) * 35 / 98)
    
    @staticmethod
    def kmh_to_speed(kmh: int) -> int:
        """km/h表示を球速能力値(1-99)に変換"""
        return max(1, min(99, int((kmh - 130) * 98 / 35 + 1)))
    
    def to_100_scale(self, value: int) -> int:
        """能力値を1-99スケールに正規化（互換性のため保持）"""
        return max(1, min(99, value))
    
    def get_rank(self, value: int) -> str:
        """能力値をパワプロ風ランクに変換（1-100スケール対応）"""
        # 100スケール用のランク分け
        if value >= 90: return "S"
        elif value >= 80: return "A"
        elif value >= 70: return "B"
        elif value >= 60: return "C"
        elif value >= 50: return "D"
        elif value >= 40: return "E"
        elif value >= 30: return "F"
        else: return "G"
    
    def get_rank_color(self, value: int) -> tuple:
        """ランクに応じた色を返す (R, G, B) - パワプロ風カラー"""
        rank = self.get_rank(value)
        colors = {
            "S": (255, 50, 50),    # 赤（パワプロS）
            "A": (255, 140, 0),    # オレンジ（パワプロA）
            "B": (255, 215, 0),    # 金色（パワプロB）
            "C": (255, 255, 100),  # 黄色（パワプロC）
            "D": (100, 255, 100),  # 緑（パワプロD）
            "E": (100, 200, 255),  # 水色（パワプロE）
            "F": (180, 180, 180),  # グレー（パワプロF）
            "G": (120, 120, 120),  # 暗いグレー（パワプロG）
        }
        return colors.get(rank, (255, 255, 255))
    
    def get_grade(self, value: int) -> str:
        """互換性のためのエイリアス"""
        return self.get_rank(value)
    
    def get_trajectory_name(self) -> str:
        """弾道の名前を返す"""
        names = {1: "グラウンダー", 2: "ライナー", 3: "普通", 4: "フライ"}
        return names.get(self.trajectory, "普通")
    
    def get_breaking_balls_display(self) -> str:
        """変化球リストを表示用文字列に"""
        if not self.breaking_balls:
            return "なし"
        return "、".join(self.breaking_balls)
    
    def get_pitch_repertoire_display(self) -> str:
        """球種と変化量を表示用文字列に"""
        if not self.pitch_repertoire:
            return self.get_breaking_balls_display()
        return ", ".join([f"{k}({v})" for k, v in self.pitch_repertoire.items()])


@dataclass
class PlayerRecord:
    """選手成績"""
    # 打撃成績
    at_bats: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    rbis: int = 0
    runs: int = 0
    walks: int = 0
    strikeouts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    sacrifice_hits: int = 0
    sacrifice_flies: int = 0
    grounded_into_dp: int = 0
    
    # 投球成績
    games_pitched: int = 0
    wins: int = 0
    losses: int = 0
    saves: int = 0
    innings_pitched: float = 0.0
    earned_runs: int = 0
    runs_allowed: int = 0
    hits_allowed: int = 0
    walks_allowed: int = 0
    strikeouts_pitched: int = 0
    home_runs_allowed: int = 0
    
    @property
    def batting_average(self) -> float:
        return self.hits / self.at_bats if self.at_bats > 0 else 0.0
    
    @property
    def era(self) -> float:
        return (self.earned_runs * 9) / self.innings_pitched if self.innings_pitched > 0 else 0.0


@dataclass
class Player:
    """選手クラス"""
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    stats: PlayerStats = field(default_factory=PlayerStats)
    record: PlayerRecord = field(default_factory=PlayerRecord)
    age: int = 25
    status: PlayerStatus = PlayerStatus.ACTIVE
    uniform_number: int = 0
    is_foreign: bool = False
    salary: int = 10000000  # 年俸（円）
    years_pro: int = 0
    draft_round: int = 0  # 0はドラフト外
    
    # 育成選手フラグ（True=育成契約、False=支配下登録）
    is_developmental: bool = False
    # 一軍/二軍/三軍
    team_level: 'TeamLevel' = None  # Noneの場合は自動判定
    # サブポジション（適性がある守備位置リスト）
    sub_positions: List[Position] = field(default_factory=list)
    # サブポジション適性値（0.0〜1.0、1.0で本職と同等）
    sub_position_ratings: dict = field(default_factory=dict)
    
    # 投手適性値（0-100）：先発・中継ぎ・抑えの適性
    starter_aptitude: int = 50    # 先発適性
    middle_aptitude: int = 50     # 中継ぎ適性
    closer_aptitude: int = 50     # 抑え適性
    
    # 追加: 育成システム用
    special_abilities: Optional['PlayerAbilities'] = None
    player_status: Optional['PlayerStatusData'] = None
    growth: Optional['PlayerGrowth'] = None
    
    def __post_init__(self):
        """初期化後の処理"""
        if self.special_abilities is None:
            from special_abilities import PlayerAbilities
            self.special_abilities = PlayerAbilities()
        
        if self.player_status is None:
            from player_development import PlayerStatus as PlayerStatusData
            self.player_status = PlayerStatusData()
        
        if self.growth is None:
            from player_development import PlayerGrowth
            potential = 5 + (self.stats.overall_batting() if self.position != Position.PITCHER else self.stats.overall_pitching()) // 2
            self.growth = PlayerGrowth(int(min(10, max(1, potential))))
    
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
    
    def add_sub_position(self, pos: Position, rating: float = 0.7):
        """サブポジションを追加"""
        if pos != self.position and pos not in self.sub_positions:
            self.sub_positions.append(pos)
            self.sub_position_ratings[pos.value] = min(1.0, max(0.3, rating))
    
    def get_preferred_pitcher_role(self) -> Optional[PitchType]:
        """最も適性が高い投手役割を取得"""
        if self.position != Position.PITCHER:
            return None
        
        aptitudes = {
            PitchType.STARTER: self.starter_aptitude,
            PitchType.RELIEVER: self.middle_aptitude,
            PitchType.CLOSER: self.closer_aptitude
        }
        return max(aptitudes, key=aptitudes.get)
    
    def get_aptitude_for_role(self, role: PitchType) -> int:
        """指定された役割の適性値を取得"""
        if role == PitchType.STARTER:
            return self.starter_aptitude
        elif role == PitchType.RELIEVER:
            return self.middle_aptitude
        elif role == PitchType.CLOSER:
            return self.closer_aptitude
        return 50

    @property
    def overall_rating(self) -> int:
        """総合力を計算（1-999）
        
        野手：ミート、パワー、走力、守備、肩力、捕球を重み付け
        投手：球速、制球、スタミナ、変化球、適性を重み付け
        年齢補正：若い選手は将来性で加算、ベテランは経験値で加算
        能力値は1-99スケール
        """
        if self.position == Position.PITCHER:
            # 投手の総合力（能力値1-99スケール）
            base = (
                self.stats.speed * 1.0 +
                self.stats.control * 1.0 +
                self.stats.stamina * 0.6 +
                self.stats.breaking * 0.8 +
                self.stats.mental * 0.4
            )  # max: 99*3.8 = 376.2
            
            # 適性ボーナス
            max_apt = max(self.starter_aptitude, self.middle_aptitude, self.closer_aptitude)
            apt_bonus = max_apt * 0.4  # max: 40
            
            total = base + apt_bonus  # max: ~416
        else:
            # 野手の総合力（能力値1-99スケール）
            base = (
                self.stats.contact * 1.0 +
                self.stats.power * 1.0 +
                self.stats.run * 0.6 +
                self.stats.fielding * 0.6 +
                self.stats.arm * 0.4 +
                self.stats.catching * 0.4
            )  # max: 99*4.0 = 396
            
            # メンタル・チャンスボーナス
            mental_bonus = (self.stats.clutch + self.stats.mental) * 0.4  # max: 79.2
            
            total = base + mental_bonus  # max: ~475
        
        # 年齢補正：年齢が高いほどやや有利になる方向に調整（経験値を重視）
        # 基本的に25歳を基準にし、年齢1につき約+2のボーナスを与える（例: 35歳で+20）。
        # ただし極端な値はクリップして安定させる。
        age_bonus = int((self.age - 25) * 2)
        age_bonus = max(-30, min(60, age_bonus))
        
        # 育成選手は減算
        dev_penalty = -50 if self.is_developmental else 0
        
        # 最終計算：内部合計をそのまま総合値として扱うことで、平均が扱いやすい領域に収まるようにする。
        # （内部合計の典型値が約250になるように能力分布を設計しているため、ここでの値が平均250前後になります）
        rating = int(total + age_bonus + dev_penalty)
        return max(1, min(999, rating))


@dataclass
class DraftProspect:
    """ドラフト候補選手"""
    name: str
    position: Position
    pitch_type: Optional[PitchType]
    stats: PlayerStats
    age: int
    high_school: str
    potential: int  # ポテンシャル（1-10）
    is_developmental: bool = False  # True=育成ドラフト候補
    
    
@dataclass
class Team:
    """チームクラス"""
    name: str
    league: League
    players: List[Player] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    draws: int = 0
    current_lineup: List[int] = field(default_factory=list)
    starting_pitcher_idx: int = -1
    budget: int = 5000000000  # 予算（円）
    color: str = None
    abbr: str = None

    def __post_init__(self):
        # ...existing code...
        # チームカラー・略称自動セット
        if not self.color:
            self.color = TEAM_COLORS.get(self.name, "#888888")
        if not self.abbr:
            self.abbr = TEAM_ABBRS.get(self.name, self.name[:2].upper())
    
    # 投手ローテーション・継投設定
    rotation: List[int] = field(default_factory=list)  # 先発ローテーション（6人）のインデックス
    rotation_index: int = 0  # 現在のローテーション位置
    setup_pitchers: List[int] = field(default_factory=list)  # 中継ぎ投手（3人程度）
    closer_idx: int = -1  # 抑え投手
    
    # NPB式ベンチ入りメンバー管理（一軍登録）
    bench_batters: List[int] = field(default_factory=list)  # ベンチ野手（5人程度）
    bench_pitchers: List[int] = field(default_factory=list)  # ベンチ投手（中継ぎ・抑え）
    active_roster: List[int] = field(default_factory=list)  # 一軍登録選手（最大31人）
    farm_roster: List[int] = field(default_factory=list)  # 二軍（ファーム）選手
    
    # NPBルール定数
    MAX_ACTIVE_ROSTER: int = 31  # 一軍登録上限
    MAX_BENCH_BATTERS: int = 5  # ベンチ野手上限
    MAX_BENCH_PITCHERS: int = 8  # ベンチ投手上限（中継ぎ＋抑え）
    MAX_GAME_ENTRY: int = 26  # 試合出場登録上限（スタメン9人＋ベンチ17人）
    
    # 支配下登録上限・育成上限
    MAX_ROSTER_SIZE: int = 70  # 支配下登録上限
    MAX_DEVELOPMENTAL_SIZE: int = 30  # 育成選手上限
    
    def get_today_starter(self) -> Optional[Player]:
        """今日の先発投手を取得"""
        if not self.rotation:
            return None
        idx = self.rotation[self.rotation_index % len(self.rotation)]
        if 0 <= idx < len(self.players):
            return self.players[idx]
        return None
    
    def advance_rotation(self):
        """ローテーションを1つ進める"""
        if self.rotation:
            self.rotation_index = (self.rotation_index + 1) % len(self.rotation)
    
    def set_rotation(self, pitcher_indices: List[int]):
        """先発ローテーションを設定（最大6人）"""
        self.rotation = pitcher_indices[:6]
        self.rotation_index = 0
        if self.rotation:
            self.starting_pitcher_idx = self.rotation[0]
    
    def get_setup_pitcher(self, situation: str = "normal") -> Optional[Player]:
        """状況に応じた中継ぎを取得"""
        if not self.setup_pitchers:
            return None
        # 最もスタミナが残っている投手を選択
        available = []
        for idx in self.setup_pitchers:
            if 0 <= idx < len(self.players):
                p = self.players[idx]
                fatigue = getattr(p.player_status, 'fatigue', 0) if p.player_status else 0
                available.append((idx, fatigue))
        if available:
            # 疲労が少ない投手を優先
            available.sort(key=lambda x: x[1])
            return self.players[available[0][0]]
        return None
    
    def get_closer(self) -> Optional[Player]:
        """抑え投手を取得"""
        if 0 <= self.closer_idx < len(self.players):
            return self.players[self.closer_idx]
        return None
    
    def auto_set_pitching_staff(self):
        """投手陣を自動設定"""
        pitchers = self.get_active_pitchers()
        starters = [p for p in pitchers if p.pitch_type == PitchType.STARTER]
        relievers = [p for p in pitchers if p.pitch_type == PitchType.RELIEVER]
        closers = [p for p in pitchers if p.pitch_type == PitchType.CLOSER]
        
        # 先発ローテーション（最大6人）
        starters.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
        self.rotation = [self.players.index(p) for p in starters[:6]]
        if self.rotation:
            self.starting_pitcher_idx = self.rotation[0]
        
        # 中継ぎ（3-4人）
        relievers.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
        self.setup_pitchers = [self.players.index(p) for p in relievers[:4]]
        
        # 抑え（1人）
        if closers:
            closers.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
            self.closer_idx = self.players.index(closers[0])
        elif relievers:
            # 抑えがいなければ中継ぎのトップを抑えに
            self.closer_idx = self.players.index(relievers[0])
    
    def auto_set_bench(self):
        """ベンチ入りメンバーを自動設定（NPB式）"""
        # 一軍登録をまず設定
        roster_players = self.get_roster_players()
        
        # 野手のベンチ入り
        batters = [p for p in roster_players if p.position != Position.PITCHER]
        batters.sort(key=lambda p: p.stats.overall_batting(), reverse=True)
        
        # スタメン9人以外をベンチに
        starting_idxs = set(self.current_lineup) if self.current_lineup else set()
        bench_batter_candidates = [p for p in batters if self.players.index(p) not in starting_idxs]
        self.bench_batters = [self.players.index(p) for p in bench_batter_candidates[:self.MAX_BENCH_BATTERS]]
        
        # 投手のベンチ入り（先発除く）
        pitchers = [p for p in roster_players if p.position == Position.PITCHER]
        starter_idxs = set(self.rotation) if self.rotation else set()
        bench_pitcher_candidates = [p for p in pitchers if self.players.index(p) not in starter_idxs]
        bench_pitcher_candidates.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
        self.bench_pitchers = [self.players.index(p) for p in bench_pitcher_candidates[:self.MAX_BENCH_PITCHERS]]
        
        # 一軍登録メンバーを更新
        self._update_active_roster()
    
    def _update_active_roster(self):
        """一軍登録メンバーを更新"""
        active = set()
        # スタメン野手
        if self.current_lineup:
            active.update(idx for idx in self.current_lineup if idx is not None and idx >= 0)
        # ベンチ野手
        active.update(idx for idx in self.bench_batters if idx >= 0)
        # 先発ローテーション
        active.update(idx for idx in self.rotation if idx >= 0)
        # 中継ぎ
        setup = getattr(self, 'setup_pitchers', []) or []
        active.update(idx for idx in setup if idx >= 0)
        # 抑え
        closer = getattr(self, 'closer', -1)
        if closer >= 0:
            active.add(closer)
        # ベンチ投手（互換性のため）
        active.update(idx for idx in self.bench_pitchers if idx >= 0)
        
        self.active_roster = list(active)[:self.MAX_ACTIVE_ROSTER]
    
    def is_on_active_roster(self, player_idx: int) -> bool:
        """一軍登録されているか"""
        return player_idx in self.active_roster
    
    def add_to_bench_batters(self, player_idx: int) -> bool:
        """野手をベンチに追加"""
        if len(self.bench_batters) >= self.MAX_BENCH_BATTERS:
            return False
        if player_idx not in self.bench_batters:
            self.bench_batters.append(player_idx)
            self._update_active_roster()
            return True
        return False
    
    def remove_from_bench_batters(self, player_idx: int) -> bool:
        """野手をベンチから外す"""
        if player_idx in self.bench_batters:
            self.bench_batters.remove(player_idx)
            self._update_active_roster()
            return True
        return False
    
    def add_to_bench_pitchers(self, player_idx: int) -> bool:
        """投手をベンチに追加"""
        if len(self.bench_pitchers) >= self.MAX_BENCH_PITCHERS:
            return False
        if player_idx not in self.bench_pitchers:
            self.bench_pitchers.append(player_idx)
            self._update_active_roster()
            return True
        return False
    
    def remove_from_bench_pitchers(self, player_idx: int) -> bool:
        """投手をベンチから外す"""
        if player_idx in self.bench_pitchers:
            self.bench_pitchers.remove(player_idx)
            self._update_active_roster()
            return True
        return False
    
    def get_game_entry_players(self) -> List[Player]:
        """試合出場登録選手を取得"""
        entry_idxs = []
        # スタメン
        if self.current_lineup:
            entry_idxs.extend(self.current_lineup)
        # ベンチ野手
        entry_idxs.extend(self.bench_batters)
        # 今日の先発
        if self.rotation and self.rotation_index < len(self.rotation):
            entry_idxs.append(self.rotation[self.rotation_index])
        # ベンチ投手
        entry_idxs.extend(self.bench_pitchers)
        
        unique_idxs = list(dict.fromkeys(entry_idxs))  # 重複排除
        return [self.players[i] for i in unique_idxs if 0 <= i < len(self.players)][:self.MAX_GAME_ENTRY]
    
    def get_available_bench_batters(self) -> List[Player]:
        """試合中に代打・代走可能な野手を取得"""
        return [self.players[i] for i in self.bench_batters if 0 <= i < len(self.players)]
    
    def get_available_relief_pitchers(self) -> List[Player]:
        """試合中に登板可能なリリーフ投手を取得"""
        return [self.players[i] for i in self.bench_pitchers if 0 <= i < len(self.players)]
    
    @property
    def winning_percentage(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0
    
    @property
    def win_rate(self) -> float:
        """勝率を取得（winning_percentageのエイリアス）"""
        return self.winning_percentage
    
    @property
    def games_played(self) -> int:
        """消化試合数を取得"""
        return self.wins + self.losses + self.draws
    
    def get_roster_players(self) -> List[Player]:
        """支配下登録選手を取得"""
        return [p for p in self.players if not p.is_developmental]
    
    def get_developmental_players(self) -> List[Player]:
        """育成選手を取得"""
        return [p for p in self.players if p.is_developmental]
    
    def get_roster_count(self) -> int:
        """支配下登録人数"""
        return len(self.get_roster_players())
    
    def get_developmental_count(self) -> int:
        """育成選手人数"""
        return len(self.get_developmental_players())
    
    def can_add_roster_player(self) -> bool:
        """支配下登録可能か"""
        return self.get_roster_count() < self.MAX_ROSTER_SIZE
    
    def can_add_developmental_player(self) -> bool:
        """育成選手追加可能か"""
        return self.get_developmental_count() < self.MAX_DEVELOPMENTAL_SIZE
    
    def promote_to_roster(self, player: Player) -> bool:
        """育成選手を支配下登録"""
        if not player.is_developmental:
            return False
        if not self.can_add_roster_player():
            return False
        player.is_developmental = False
        return True
    
    def demote_to_developmental(self, player: Player) -> bool:
        """支配下選手を育成契約に（通常シーズン中は不可）"""
        if player.is_developmental:
            return False
        if not self.can_add_developmental_player():
            return False
        player.is_developmental = True
        return True
    
    def get_active_batters(self) -> List[Player]:
        return [p for p in self.players if not p.is_developmental and p.position != Position.PITCHER]
    
    def get_active_pitchers(self, pitch_type: Optional[PitchType] = None) -> List[Player]:
        pitchers = [p for p in self.players if not p.is_developmental and p.position == Position.PITCHER]
        if pitch_type:
            pitchers = [p for p in pitchers if p.pitch_type == pitch_type]
        return pitchers
    
    def get_foreign_players(self) -> List[Player]:
        return [p for p in self.players if p.is_foreign and not p.is_developmental]
    
    def can_sign_foreign_player(self) -> bool:
        """外国人選手を獲得可能かチェック（NPBルール：支配下最大4人）"""
        return len(self.get_foreign_players()) < 4


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
