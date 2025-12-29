# -*- coding: utf-8 -*-
"""
データモデル定義 (修正版: 契約金フィールド追加)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any, Union
from enum import Enum
import datetime
import random
from datetime import datetime, timedelta

class Position(Enum):
    PITCHER = "投手"
    CATCHER = "捕手"
    FIRST = "一塁手"
    SECOND = "二塁手"
    THIRD = "三塁手"
    SHORTSTOP = "遊撃手"
    LEFT = "左翼手"
    CENTER = "中堅手"
    RIGHT = "右翼手"
    DH = "指名打者"


class PitchType(Enum):
    STARTER = "先発"
    RELIEVER = "中継ぎ"
    CLOSER = "抑え"

class PitcherRole(Enum):
    STARTER = "先発"
    SETUP_A = "勝利の方程式A" # 8回 (Primary Setup)
    SETUP_B = "勝利の方程式B" # 7回 (Secondary Setup)
    CLOSER = "守護神"      # 9回
    MIDDLE = "中継ぎ"      # 接戦/ビハインド
    LONG = "ロング"        # 敗戦処理/ロングリリーフ
    SPECIALIST = "ワンポイント" # 左キラーなど


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
    CANCELLED = "雨天中止"

class Hand(Enum):
    RIGHT = "右"
    LEFT = "左"
    BOTH = "両"


class PlayerType(Enum):
    """選手タイプ - 初期能力と成長傾向に影響"""
    # 野手タイプ
    POWER = "パワー型"      # パワー↑、スピード↓
    CONTACT = "巧打型"      # ミート↑、パワー↓
    SPEED = "俊足型"        # スピード↑、パワー↓
    DEFENSE = "守備型"      # 守備↑、パワー↓
    BALANCED = "万能型"     # 均等
    # 投手タイプ
    POWER_PITCHER = "本格派"  # 球速↑、制球↓
    FINESSE = "技巧派"       # 制球↑、球速↓
    JUNK = "軟投派"         # 変化球↑、球速↓


class TrainingMenu(Enum):
    """練習メニュー"""
    # 野手練習
    CONTACT = "ミート強化"
    GAP = "ギャップ強化"
    POWER = "パワー強化"
    EYE = "選球眼強化"
    AVOID_K = "三振回避強化"
    SPEED = "走力強化"
    STEAL = "盗塁強化"
    BASERUNNING = "走塁強化"
    ARM = "肩力強化"
    FIELDING = "守備強化"
    ERROR = "捕球強化"
    BUNT = "バント強化"
    CHANCE = "チャンス強化"
    VS_LEFT = "対左強化"
    # 投手練習
    VELOCITY = "球速強化"
    CONTROL = "制球強化"      # 全球種のcontrolを上昇
    STUFF = "球威強化"        # 全球種のstuffを上昇  
    MOVEMENT = "変化球強化"   # 全球種のmovementを上昇
    STAMINA = "スタミナ強化"
    HOLD_RUNNERS = "クイック強化"
    VS_PINCH = "対ピンチ強化"
    STABILITY = "安定感強化"
    # 共通
    DURABILITY = "耐久力強化"
    RECOVERY = "回復力強化"
    MENTAL = "メンタル強化"
    INTELLIGENCE = "野球脳強化"
    # 追加
    TRAJECTORY = "弾道強化"
    CATCHER_LEAD = "リード強化"
    TURN_DP = "併殺処理強化"
    NEW_PITCH = "新球種習得"
    REST = "休養"  # スタミナ回復優先


class StaffRole(Enum):
    """スタッフ役職"""
    MANAGER_FIRST = "一軍監督"
    MANAGER_SECOND = "二軍監督"
    MANAGER_THIRD = "三軍監督"
    PITCHING_COACH = "投手コーチ"
    BATTING_COACH = "打撃コーチ"
    INFIELD_COACH = "内野守備走塁コーチ"
    OUTFIELD_COACH = "外野守備走塁コーチ"
    BATTERY_COACH = "バッテリーコーチ"
    BULLPEN_COACH = "ブルペンコーチ"
    SCOUT_DOMESTIC = "国内スカウト"
    SCOUT_INTERNATIONAL = "海外スカウト"


@dataclass
class StaffMember:
    """チームスタッフ (監督・コーチ・スカウト)"""
    name: str
    role: StaffRole
    age: int = 45
    salary: int = 10000000  # 年俸
    ability: int = 50  # 総合能力 (1-99)
    specialty: str = ""  # 専門分野 (e.g., "パワー強化", "変化球指導")
    years_in_role: int = 0
    team_level: 'TeamLevel' = None  # 所属軍 (1軍/2軍/3軍), None for scouts
    
    # Scout-specific fields
    is_available: bool = True  # スカウト用: 派遣可能か
    current_mission_id: Optional[str] = None  # スカウト用: 調査対象ID
    
    # Candidate tracking
    source: str = "generated"  # "generated" or "retired_player"
    original_player_name: str = ""  # 元選手名 (引退選手の場合)
    
    def __post_init__(self):
        if self.team_level is None and not self.is_scout:
            self.team_level = TeamLevel.FIRST
    
    @property
    def is_coach(self) -> bool:
        return self.role in [StaffRole.PITCHING_COACH,
                            StaffRole.BATTING_COACH, StaffRole.INFIELD_COACH,
                            StaffRole.OUTFIELD_COACH, StaffRole.BATTERY_COACH,
                            StaffRole.BULLPEN_COACH]
    
    @property
    def is_scout(self) -> bool:
        return self.role in [StaffRole.SCOUT_DOMESTIC, StaffRole.SCOUT_INTERNATIONAL]
    
    @property
    def is_manager(self) -> bool:
        return self.role in [StaffRole.MANAGER_FIRST, StaffRole.MANAGER_SECOND, StaffRole.MANAGER_THIRD]
    
    @property
    def daily_progress(self) -> float:
        """1日あたりの調査進捗率 (%) - for scouts"""
        # 5%前後になるように調整 (ability 50で5%)
        return 2.0 + (self.ability * 0.06)


# 選手タイプ別の成長倍率定義
PLAYER_TYPE_GROWTH_MODIFIERS = {
    PlayerType.POWER: {
        "strong": ["power", "arm"],  # 1.5x
        "weak": ["speed", "steal", "baserunning"],  # 0.5x
    },
    PlayerType.CONTACT: {
        "strong": ["contact", "gap", "eye"],
        "weak": ["power"],
    },
    PlayerType.SPEED: {
        "strong": ["speed", "steal", "baserunning"],
        "weak": ["power", "arm"],
    },
    PlayerType.DEFENSE: {
        "strong": ["error", "arm", "fielding"],
        "weak": ["power", "contact"],
    },
    PlayerType.BALANCED: {
        "strong": [],
        "weak": [],
    },
    PlayerType.POWER_PITCHER: {
        "strong": ["velocity", "stuff"],
        "weak": ["control", "stability"],
    },
    PlayerType.FINESSE: {
        "strong": ["control", "movement", "stability"],
        "weak": ["velocity", "stuff"],
    },
    PlayerType.JUNK: {
        "strong": ["movement", "stability", "control"],
        "weak": ["velocity", "stuff"],
    },
}

@dataclass
class FanBase:
    """三層ファン構造"""
    light_fans: int = 300000      # ライト層（増減しやすい、収益低）
    middle_fans: int = 150000     # ミドル層（中程度）
    core_fans: int = 50000        # コア層（増減しにくい、収益高）
    
    @property
    def total_fans(self) -> int:
        return self.light_fans + self.middle_fans + self.core_fans
    
    def update_fans(self, settings: 'ManagementSettings', win_rate: float = 0.5):
        """経営設定と勝率に基づいてファン層を更新"""
        import random
        
        # ライト層: 放映権価格が安いほど増加（変動大）
        # broadcast_price: 1=最安(大増加), 5=最高(減少)
        light_mod = (3 - settings.broadcast_price) * 0.0008  # -0.16% ~ +0.16%
        light_mod += (win_rate - 0.5) * 0.004  # 勝率影響大
        light_mod += random.uniform(-0.003, 0.003)  # 変動大
        self.light_fans = max(10000, int(self.light_fans * (1 + light_mod)))
        
        # ミドル層: チケット価格が安いほど増加（変動中）
        middle_mod = (3 - settings.ticket_price) * 0.0005
        middle_mod += (win_rate - 0.5) * 0.002
        middle_mod += random.uniform(-0.0015, 0.0015)
        self.middle_fans = max(5000, int(self.middle_fans * (1 + middle_mod)))
        
        # コア層: グッズ価格が安いほど増加（変動小）
        core_mod = (3 - settings.merchandise_price) * 0.0003
        core_mod += (win_rate - 0.5) * 0.001
        core_mod += random.uniform(-0.0005, 0.0005)  # 変動小
        self.core_fans = max(1000, int(self.core_fans * (1 + core_mod)))


@dataclass
class ManagementSettings:
    """経営コマンド設定（5段階）"""
    # 放映権価格：1=最安（ライト層増加）, 5=最高（収益高）
    broadcast_price: int = 3
    
    # チケット価格：1=最安（ミドル層増加）, 5=最高（収益高）
    ticket_price: int = 3
    
    # グッズ価格：1=最安（コア層増加）, 5=最高（収益高）
    merchandise_price: int = 3
    
    def get_level_name(self, level: int) -> str:
        """レベルを日本語名で返す"""
        names = {1: "最安", 2: "安い", 3: "標準", 4: "高い", 5: "最高"}
        return names.get(level, "標準")


@dataclass
class InvestmentSettings:
    """投資コマンド設定（5段階）"""
    # 練習設備：1=最低, 5=最高（練習効果に影響）
    training_facility: int = 3
    
    # 医療設備：1=最低, 5=最高（怪我軽減に影響）
    medical_facility: int = 3
    
    def get_training_effectiveness(self) -> float:
        """練習効果倍率（0.7〜1.5倍）"""
        return 0.5 + self.training_facility * 0.2
    
    def get_injury_reduction(self) -> float:
        """怪我軽減率（0.15〜0.35）"""
        return 0.1 + self.medical_facility * 0.05
    
    def get_training_cost(self) -> int:
        """練習設備の年間維持費"""
        base_costs = {1: 50000000, 2: 100000000, 3: 200000000, 4: 400000000, 5: 800000000}
        return base_costs.get(self.training_facility, 200000000)
    
    def get_medical_cost(self) -> int:
        """医療設備の年間維持費"""
        base_costs = {1: 30000000, 2: 60000000, 3: 120000000, 4: 240000000, 5: 480000000}
        return base_costs.get(self.medical_facility, 120000000)


@dataclass
class TeamFinance:
    """チームの財務情報"""
    # ファン層
    fan_base: FanBase = field(default_factory=FanBase)
    
    # 収入項目 (今期累計、円単位)
    ticket_revenue: int = 0          # チケット収入
    broadcast_revenue: int = 0       # 放映権収入
    merchandise_revenue: int = 0     # グッズ収入
    sponsor_revenue: int = 0         # スポンサー収入
    other_revenue: int = 0           # その他収入
    
    # 支出項目
    player_salary_expense: int = 0   # 選手年俸
    staff_salary_expense: int = 0    # スタッフ年俸
    stadium_maintenance: int = 0     # 球場維持費（累計）
    facility_expense: int = 0        # 練習・医療設備維持費（累計）
    other_expense: int = 0           # その他支出（遠征費、雑費等）
    
    # 観客数記録
    season_attendance: int = 0       # 今期累計観客数
    last_game_attendance: int = 0    # 直近試合の観客数
    
    @property
    def total_income(self) -> int:
        return self.ticket_revenue + self.broadcast_revenue + self.merchandise_revenue + self.sponsor_revenue + self.other_revenue
    
    @property
    def total_expense(self) -> int:
        return self.player_salary_expense + self.staff_salary_expense + self.stadium_maintenance + self.facility_expense + self.other_expense
    
    @property
    def total_fans(self) -> int:
        return self.fan_base.total_fans
    
    def calculate_attendance(self, stadium_capacity: int, win_rate: float, opponent_popularity: float = 1.0) -> int:
        """試合の観客数を計算（最低80%動員率保証）"""
        import random
        
        # 最低動員率: 80%
        min_attendance = int(stadium_capacity * 0.80)
        
        # ファン数に基づく基本動員率: ファン数が多いほど満員に近づく
        # 100万ファン=85%, 300万ファン=95%, 500万ファン=100%
        fan_fill_rate = 0.80 + min(self.fan_base.total_fans / 5000000, 1.0) * 0.20
        base = stadium_capacity * fan_fill_rate
        
        # 勝率補正 (0.4で0.95倍、0.5で1.0倍、0.6で1.05倍)
        base *= (0.9 + win_rate * 0.2)
        
        # 対戦相手補正
        base *= opponent_popularity
        
        # ランダム変動 (±10%)
        base *= random.uniform(0.9, 1.1)
        
        # 最低動員率と収容人数の範囲内に収める
        attendance = max(min_attendance, min(int(base), stadium_capacity))
        self.last_game_attendance = attendance
        self.season_attendance += attendance
        return attendance
    
    def calculate_game_revenue(self, attendance: int, settings: 'ManagementSettings'):
        """試合ごとの収入を計算"""
        # チケット単価を減少: 1=2300円, 5=3500円
        ticket_unit_price = 2000 + settings.ticket_price * 300
        ticket_income = attendance * ticket_unit_price
        self.ticket_revenue += ticket_income
        return ticket_income
    
    def calculate_daily_revenue(self, settings: 'ManagementSettings'):
        """日次収入を計算（放映権、グッズ、スポンサー）"""
        fb = self.fan_base
        
        # 放映権収入: ファン数の影響を減らす（平方根で逓減）
        broadcast_base = 8000000 + settings.broadcast_price * 2000000  # 1000万〜1800万/日
        broadcast_mult = (fb.total_fans / 500000) ** 0.5  # 平方根で影響を緩やかに
        self.broadcast_revenue += int(broadcast_base * broadcast_mult)
        
        # グッズ収入: 層別に計算
        # コア層: 高収益、ミドル層: 中収益、ライト層: 低収益
        price_mult = 0.6 + settings.merchandise_price * 0.15  # 0.75〜1.35
        core_revenue = fb.core_fans * 3 * price_mult  # 1人3円/日
        middle_revenue = fb.middle_fans * 1 * price_mult
        light_revenue = fb.light_fans * 0.3 * price_mult
        self.merchandise_revenue += int(core_revenue + middle_revenue + light_revenue)
        
        # スポンサー収入: ファン数の影響を減らす（平方根で逓減）
        sponsor_mult = (fb.total_fans / 500000) ** 0.5  # 平方根で影響を緩やかに
        daily_sponsor = int(15000000 * sponsor_mult)  # 基本1500万円/日
        self.sponsor_revenue += daily_sponsor
    
    def calculate_daily_expense(self, stadium: 'Stadium', inv_settings: 'InvestmentSettings'):
        """日次支出を計算（球場維持費、設備維持費、その他）"""
        fb = self.fan_base
        
        # 球場維持費（日割）: 年間維持費 / 200
        if stadium:
            daily_stadium = stadium.maintenance_cost // 200
            self.stadium_maintenance += daily_stadium
        
        # 設備維持費（日割）
        if inv_settings:
            annual_facility = inv_settings.get_training_cost() + inv_settings.get_medical_cost()
            daily_facility = annual_facility // 200
            self.facility_expense += daily_facility
        
        # その他支出（遠征費、雑費等）: 約100億円/年
        # 基本2000万円/日 + ファン数に応じて大きく変動（ファン1人あたり10円/日）
        base_other = 20000000  # 2000万円/日 (年間約40億円の固定費)
        fan_based_other = int(fb.total_fans * 10)  # ファン1人あたり10円/日
        daily_other = base_other + fan_based_other
        self.other_expense += daily_other
    
    def host_event(self, event_cost: int):
        """イベント開催でファン増加"""
        boost = event_cost / 10000000  # 1000万円で基本ブースト
        self.fan_base.light_fans += int(self.fan_base.light_fans * boost * 0.05)
        self.fan_base.middle_fans += int(self.fan_base.middle_fans * boost * 0.02)
        self.fan_base.core_fans += int(self.fan_base.core_fans * boost * 0.01)
        self.other_expense += event_cost


@dataclass
class GameResult:
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    date: str
    game_number: int


@dataclass
class TeamRecord:
    wins: int = 0
    losses: int = 0
    draws: int = 0
    runs: int = 0
    batting_average: float = 0.0
    era: float = 0.0
    fielding_pct: float = 0.0



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
        return None 

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
    # ===== 打撃能力 =====
    contact: int = 50          # ミート
    gap: int = 50              # ギャップ
    power: int = 50            # パワー
    eye: int = 50              # 選球眼
    avoid_k: int = 50          # 三振回避
    trajectory: int = 2        # 弾道

    # ===== 特殊打撃能力 =====
    vs_left_batter: int = 50
    chance: int = 50

    # ===== 走塁能力 =====
    speed: int = 50            # 走力
    steal: int = 50            # 盗塁技術
    baserunning: int = 50      # 走塁技術

    # ===== バント能力 =====
    bunt_sac: int = 50
    bunt_hit: int = 50

    # ===== 守備能力 =====
    arm: int = 50              # 肩力
    error: int = 50            # 捕球/エラー回避
    
    # 守備範囲 (Defense Range)
    defense_ranges: Dict[str, int] = field(default_factory=dict)
    
    catcher_lead: int = 50     # 捕手リード
    turn_dp: int = 50          # 併殺処理

    # ===== 投球能力 ===== (Per-pitch managed in 'pitches')
    # stuff: int = 50            # 球威 (Removed global)
    # movement: int = 50         # 変化球 (Removed global)
    # control: int = 50          # 制球 (Removed global)

    # ===== 投手追加能力 =====
    velocity: int = 145        # 球速 (km/h)
    new_pitch_progress: int = 0 # 新球種習得進行度 (0-100)
    stamina: int = 50          # スタミナ
    hold_runners: int = 50     # クイック
    gb_tendency: int = 50      # ゴロ傾向
    
    vs_left_pitcher: int = 50
    vs_pinch: int = 50
    stability: int = 50

    # ===== 共通能力 =====
    durability: int = 50
    recovery: int = 50
    work_ethic: int = 50
    intelligence: int = 50
    mental: int = 50

    # ===== 投手専用 =====
    # 値は int (精度のみ) または dict (詳細: {quality, stuff, movement})
    pitches: Dict[str, Union[int, Dict[str, int]]] = field(default_factory=dict)

    # ===== ヘルパーメソッド =====
    def get_defense_range(self, position: 'Position') -> int:
        val = self.defense_ranges.get(position.value, 0)
        if val == 0 and position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            val = self.defense_ranges.get("外野手", 1)
        return max(1, val)

    def set_defense_range(self, position: 'Position', value: int):
        self.defense_ranges[position.value] = max(1, min(99, value))

    def get_pitch_quality(self, pitch_name: str) -> int:
        """後方互換性: qualityの代わりにstuffを返す"""
        data = self.pitches.get(pitch_name)
        if isinstance(data, dict): return data.get("stuff", data.get("quality", 50))
        return data if isinstance(data, int) else 0

    def get_pitch_stuff(self, pitch_name: str) -> int:
        data = self.pitches.get(pitch_name)
        if isinstance(data, dict) and "stuff" in data: return data["stuff"]
        return self.stuff # Uses property average

    def get_pitch_movement(self, pitch_name: str) -> int:
        data = self.pitches.get(pitch_name)
        if isinstance(data, dict) and "movement" in data: return data["movement"]
        return self.movement # Uses property average
    
    def get_pitch_control(self, pitch_name: str) -> int:
        data = self.pitches.get(pitch_name)
        if isinstance(data, dict) and "control" in data: return data["control"]
        return self.control # Uses property average

    @property
    def stuff(self) -> int:
        """全球種の球威の合計値 / 5 (99上限)"""
        if not self.pitches: return 50
        total = 0
        for p in self.pitches.values():
            if isinstance(p, dict):
                total += p.get("stuff", 50)
            elif isinstance(p, int):
                total += p
        return min(99, total // 5)

    @property
    def control(self) -> int:
        """全球種の制球の合計値 / 5 (99上限)"""
        if not self.pitches: return 50
        total = 0
        for p in self.pitches.values():
            if isinstance(p, dict):
                total += p.get("control", 50)
            elif isinstance(p, int):
                total += 50
        return min(99, total // 5)

    @property
    def movement(self) -> int:
        """全球種の変化量の合計値 / 5 (99上限)"""
        if not self.pitches: return 50
        total = 0
        for name, p in self.pitches.items():
            if name in ["ストレート", "Straight"]: continue  # Skip straight
            if isinstance(p, dict):
                total += p.get("movement", 50)
            elif isinstance(p, int):
                total += p
        return min(99, total // 5)
        
    @stuff.setter
    def stuff(self, val): pass # Ignored
    @control.setter
    def control(self, val): pass 
    @movement.setter
    def movement(self, val): pass

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
        return max(0.5, min(5.0, value / 100))

    def overall_batting(self, position: Optional[Position] = None) -> float:
        """
        野手の総合力を計算（WAR連動型、全能力使用）
        平均250、ボリュームゾーン230-270、1-999スケール
        
        重み付け（WAR貢献度に基づく）:
        - 打撃系: ミート(3.5), パワー(3.0), ギャップ(1.5), 選球眼(2.0), 三振回避(1.0)
        - 走塁系: 走力(1.5), 盗塁(0.8), 走塁(0.7)
        - 守備系: 守備範囲(3.0), 肩力(1.0), 捕球(1.5), 併殺処理(0.5)
        - 共通: 精神力(0.5), 対左打者(0.3), チャンス(0.3)
        """
        # 打撃系能力 (重み合計: 11.0)
        batting_raw = (
            self.contact * 3.5 +
            self.power * 3.0 +
            self.gap * 1.5 +
            self.eye * 2.0 +
            self.avoid_k * 1.0
        )
        
        # 走塁系能力 (重み合計: 3.0)
        running_raw = (
            self.speed * 1.5 +
            self.steal * 0.8 +
            self.baserunning * 0.7
        )
        
        # 守備系能力 (重み合計: 6.0)
        def_range = self.get_defense_range(position) if position else 50
        fielding_raw = (
            def_range * 3.0 +
            self.arm * 1.0 +
            self.error * 1.5 +
            self.turn_dp * 0.5
        )
        
        # 共通能力 (重み合計: 1.1)
        misc_raw = (
            self.mental * 0.5 +
            self.vs_left_batter * 0.3 +
            self.chance * 0.3
        )
        
        # 捕手ボーナス
        catcher_bonus = 0
        if position == Position.CATCHER:
            catcher_bonus = self.catcher_lead * 0.8
        
        # 重み付き合計 (合計重み約21.1)
        total_weighted = batting_raw + running_raw + fielding_raw + misc_raw + catcher_bonus
        total_weight = 21.1 + (0.8 if position == Position.CATCHER else 0)
        
        # 平均50の能力 → 合計約1055 → 正規化して50に
        normalized = total_weighted / total_weight
        
        # ポジション調整（WAR基準: 捕手+15, SS+10, 2B+5, CF+5, 3B/RF-5, LF/1B-10, DH-20）
        pos_adj = 0
        if position:
            if position == Position.CATCHER: pos_adj = 15
            elif position == Position.SHORTSTOP: pos_adj = 10
            elif position == Position.SECOND: pos_adj = 5
            elif position == Position.CENTER: pos_adj = 5
            elif position == Position.THIRD: pos_adj = -5
            elif position == Position.RIGHT: pos_adj = -5
            elif position == Position.LEFT: pos_adj = -10
            elif position == Position.FIRST: pos_adj = -10
            elif position == Position.DH: pos_adj = -20
        
        # スケール変換: 傾斜をかけた非線形スケール
        # 通常生成 (能力30-70) → 総合力130-450
        # 超一流 (能力99) → 総合力999
        # 
        # 線形部分: 能力50を基準に250、能力70で450相当
        # 曲線部分: 能力70以上は急激に上昇
        
        if normalized <= 50:
            # 能力50以下: 線形で130-250
            rating = (normalized / 50) * 120 + 130  # 1→130, 50→250
        elif normalized <= 70:
            # 能力50-70: 線形で250-450
            rating = ((normalized - 50) / 20) * 200 + 250  # 50→250, 70→450
        else:
            # 能力70以上: 曲線で450-999 (指数関数的に上昇)
            # normalized 70→450, 99→999
            excess = (normalized - 70) / 29  # 0 to 1
            rating = 450 + (excess ** 1.5) * 549  # 70→450, 99→999
        
        rating = rating + pos_adj
        return max(1, min(999, int(rating)))

    def overall_pitching(self) -> float:
        """
        投手の総合力を計算（WAR連動型、全能力使用）
        平均250、ボリュームゾーン230-270、1-999スケール
        
        重み付け（WAR貢献度に基づく）:
        - 球種系: 球威(3.5), 制球(3.5), 変化(2.5)
        - 球速系: 球速(1.5)
        - スタミナ系: スタミナ(2.0)
        - 共通: 安定感(1.0), 対ピンチ(0.5), 精神力(0.5), クイック(0.3), ゴロ傾向(0.2)
        """
        # 球速を能力値に変換 (130km=30, 145km=60, 160km=90)
        vel_rating = self.kmh_to_rating(self.velocity)
        
        # 球種系能力 (重み合計: 9.5)
        pitch_raw = (
            self.stuff * 3.5 +
            self.control * 3.5 +
            self.movement * 2.5
        )
        
        # 球速・スタミナ (重み合計: 3.5)
        physical_raw = (
            vel_rating * 1.5 +
            self.stamina * 2.0
        )
        
        # 共通能力 (重み合計: 2.5)
        misc_raw = (
            self.stability * 1.0 +
            self.vs_pinch * 0.5 +
            self.mental * 0.5 +
            self.hold_runners * 0.3 +
            self.gb_tendency * 0.2
        )
        
        # 重み付き合計 (合計重み15.5)
        total_weighted = pitch_raw + physical_raw + misc_raw
        total_weight = 15.5
        
        # 正規化
        normalized = total_weighted / total_weight
        
        # スケール変換: 傾斜をかけた非線形スケール
        # 通常生成 (能力30-70) → 総合力130-450
        # 超一流 (能力99) → 総合力999
        
        if normalized <= 50:
            rating = (normalized / 50) * 120 + 130
        elif normalized <= 70:
            rating = ((normalized - 50) / 20) * 200 + 250
        else:
            excess = (normalized - 70) / 29
            rating = 450 + (excess ** 1.5) * 549
        
        return max(1, min(999, int(rating)))

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
    name: str
    capacity: int = 30000           # 観客席数 (10000-100000)
    field_size: int = 3             # フィールド広さ (1-5: 狭い-広い)
    is_dome: bool = False           # ドーム球場かどうか
    pf_runs: float = 1.00
    pf_hr: float = 1.00
    pf_1b: float = 1.00
    pf_2b: float = 1.00
    pf_3b: float = 1.00
    pf_so: float = 1.00
    pf_bb: float = 1.00

    def get_factor(self, item: str) -> float:
        return getattr(self, f"pf_{item.lower()}", 1.0)
    
    @property
    def maintenance_cost(self) -> int:
        """年間維持費: 容量に比例、ドームは2倍"""
        base = self.capacity * 5000  # 1席あたり5000円/年
        if self.is_dome:
            return base * 2
        return base
    
    @property
    def attendance_bonus(self) -> float:
        """ドーム球場は観客が来やすい（+20%）"""
        return 1.2 if self.is_dome else 1.0


@dataclass
class PlayerRecord:
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
    home_games: int = 0
    home_games_pitched: int = 0

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
    batters_faced: int = 0

    # Advanced Tracking
    total_bases: int = 0
    ground_balls: int = 0
    fly_balls: int = 0
    line_drives: int = 0
    popups: int = 0
    hard_hit_balls: int = 0
    medium_hit_balls: int = 0
    soft_hit_balls: int = 0
    pull_balls: int = 0
    center_balls: int = 0
    oppo_balls: int = 0
    balls_in_play: int = 0

    pitches_seen: int = 0
    pitches_thrown: int = 0
    strikes_thrown: int = 0
    balls_thrown: int = 0
    first_pitch_strikes: int = 0
    
    zone_pitches: int = 0
    chase_pitches: int = 0
    zone_swings: int = 0
    chase_swings: int = 0
    zone_contact: int = 0
    chase_contact: int = 0
    swings: int = 0
    whiffs: int = 0

    ground_outs: int = 0
    fly_outs: int = 0
    quality_starts: int = 0
    complete_games: int = 0
    shutouts: int = 0

    # Defensive Metrics
    def_opportunities: int = 0 
    def_plays_made: int = 0    
    def_difficulty_sum: float = 0.0 
    def_drs_raw: float = 0.0 
    defensive_innings: float = 0.0
    
    uzr_rngr: float = 0.0
    uzr_errr: float = 0.0
    uzr_arm: float = 0.0
    uzr_dpr: float = 0.0
    uzr_rsb: float = 0.0
    uzr_rblk: float = 0.0

    # Computed Advanced Stats
    woba_val: float = 0.0
    wrc_val: float = 0.0
    wrc_plus_val: float = 0.0
    war_val: float = 0.0
    fip_val: float = 0.0
    xfip_val: float = 0.0
    drs_val: float = 0.0
    uzr_val: float = 0.0
    wsb_val: float = 0.0
    ubr_val: float = 0.0
    
    wraa_val: float = 0.0
    rc_val: float = 0.0
    rc27_val: float = 0.0
    
    # Properties
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

    # Plate Discipline Properties
    @property
    def o_swing_pct(self) -> float:
        return self.chase_swings / self.chase_pitches if self.chase_pitches > 0 else 0.0
    
    @property
    def z_swing_pct(self) -> float:
        return self.zone_swings / self.zone_pitches if self.zone_pitches > 0 else 0.0
        
    @property
    def swing_pct(self) -> float:
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

    # Sabermetrics Properties
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
        if self.balls_in_play > 0:
            return (self.hits - self.home_runs) / self.balls_in_play
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
        if self.xfip_val == 0.0: return self.fip 
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
        if self.batters_faced == 0: return 0.0
        return self.strikeouts_pitched / self.batters_faced

    @property
    def bb_rate_pitched(self) -> float:
        if self.batters_faced == 0: return 0.0
        return self.walks_allowed / self.batters_faced
    
    @property
    def pitcher_hr_fb(self) -> float:
        """投手の被本塁打/被フライ率"""
        if self.fly_balls == 0: return 0.0
        return self.home_runs_allowed / self.fly_balls
        
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
        return self.uzr_rngr + self.uzr_errr + self.uzr_dpr + self.uzr_arm + self.uzr_rsb + self.uzr_rblk
    
    @property
    def drs(self) -> float:
        return self.drs_val

    @property
    def uzr_1000(self) -> float:
        if self.defensive_innings <= 0: return 0.0
        return (self.uzr / self.defensive_innings) * 1000

    @property
    def uzr_1200(self) -> float:
        if self.defensive_innings <= 0: return 0.0
        return (self.uzr / self.defensive_innings) * 1200

    @property
    def wraa(self) -> float:
        return self.wraa_val

    @property
    def rc(self) -> float:
        return self.rc_val

    @property
    def rc27(self) -> float:
        return self.rc27_val

    @property
    def ab_per_hr(self) -> float:
        if self.home_runs == 0: return 0.0
        return self.at_bats / self.home_runs

    @property
    def bb_k_ratio(self) -> float:
        if self.strikeouts == 0: return float(self.walks)
        return self.walks / self.strikeouts
        
    @property
    def babip_against(self) -> float:
        if self.balls_in_play > 0:
            return (self.hits_allowed - self.home_runs_allowed) / self.balls_in_play
        denom = self.batters_faced - self.strikeouts_pitched - self.home_runs_allowed - self.walks_allowed - self.hit_batters
        if denom <= 0: return 0.0
        return (self.hits_allowed - self.home_runs_allowed) / denom

    @property
    def gb_rate(self) -> float:
        total = self.ground_balls + self.fly_balls + self.line_drives + self.popups
        if total == 0: return 0.0
        return self.ground_balls / total

    @property
    def fb_rate(self) -> float:
        total = self.ground_balls + self.fly_balls + self.line_drives + self.popups
        if total == 0: return 0.0
        return self.fly_balls / total
    
    @property
    def strike_percentage(self) -> float:
        if self.pitches_thrown == 0: return 0.0
        return self.strikes_thrown / self.pitches_thrown
    
    @property
    def pitches_per_inning(self) -> float:
        if self.innings_pitched == 0: return 0.0
        return self.pitches_thrown / self.innings_pitched
        
    @property
    def siera(self) -> float:
        return self.xfip

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
    contract_bonus: int = 0 # ★追加: 契約金
    years_pro: int = 0
    draft_round: int = 0

    injury_days: int = 0
    injury_name: str = ""

    is_developmental: bool = False
    team_level: 'TeamLevel' = None

    starter_aptitude: int = 50
    middle_aptitude: int = 50
    closer_aptitude: int = 50

    potential: int = 50 # 潜在能力

    # 選手タイプと練習
    player_type: Optional['PlayerType'] = None  # 選手タイプ
    training_menu: Optional['TrainingMenu'] = None  # 現在の練習メニュー
    training_xp: Dict[str, float] = field(default_factory=dict)  # XP per stat (0-100%)

    special_abilities: Optional[object] = None
    player_status: Optional[object] = None
    growth: Optional[object] = None

    record_farm: PlayerRecord = field(default_factory=PlayerRecord)
    record_third: PlayerRecord = field(default_factory=PlayerRecord)

    career_stats: CareerStats = field(default_factory=CareerStats)
    
    condition: int = 5
    
    days_rest: int = 6
    rotation_interval: int = 6 # 先発登板間隔 (中n日)
    
    bats: str = "右"
    throws: str = "右"
    
    recent_records: List[Tuple[str, PlayerRecord]] = field(default_factory=list)
    days_until_promotion: int = 0
    
    # スタミナは球数ベース（20〜120球）
    # 実際の最大値は calc_max_pitches() で計算
    current_stamina: int = 100  # 現在の残り球数
    
    # 疲労システム
    fatigue: int = 0  # 疲労度 (0-100, 100=限界)
    consecutive_days: int = 0  # 連投日数（投手用）
    
    # 当日出場フラグ (1日2試合出場防止用)
    has_played_today: bool = False

    def __post_init__(self):
        if self.team_level is None:
            self.team_level = TeamLevel.FIRST
        # 投手の場合、初期スタミナを最大値に設定
        if self.position == Position.PITCHER:
            self.current_stamina = self.calc_max_pitches()
    
    def calc_max_pitches(self, is_starting: bool = False) -> int:
        """最大投球可能数を計算
        
        中継ぎ時: 20〜70球 (20 + スタミナ×0.5)
        先発時: 70〜170球 (70 + スタミナ×1.0)
        """
        if is_starting:
            # 先発: 70〜170球
            return 70 + int(self.stats.stamina * 1.0)
        else:
            # 中継ぎ: 20〜70球
            return 20 + int(self.stats.stamina * 0.5)

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
        self.recent_records = []

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

    def add_game_record(self, date_str: str, record: PlayerRecord):
        new_rec = PlayerRecord()
        new_rec.merge_from(record) 
        self.recent_records.append((date_str, new_rec))
        if len(self.recent_records) > 30:  # 60→30に削減してセーブ高速化
            self.recent_records.pop(0)

    def get_recent_stats(self, current_date_str: str, days: int = 30) -> PlayerRecord:
        total = PlayerRecord()
        try:
            curr = datetime.strptime(current_date_str, "%Y-%m-%d")
            limit = curr - timedelta(days=days)
            for d_str, rec in reversed(self.recent_records):
                game_date = datetime.strptime(d_str, "%Y-%m-%d")
                if game_date < limit:
                    break
                total.merge_from(rec)
        except Exception:
            pass
        return total

    @property
    def is_injured(self) -> bool:
        return self.injury_days > 0

    def inflict_injury(self, days: int, name: str):
        self.injury_days = days
        self.injury_name = name
        self.condition = 1

    @property
    def overall_rating(self) -> int:
        if self.position == Position.PITCHER:
            val = self.stats.overall_pitching()
        else:
            val = self.stats.overall_batting(self.position)
        return int(val)

    def get_aptitude_symbol(self, value: int) -> str:
        """適性を◎、〇、△、ーで返す (1-4段階評価)"""
        if value >= 4: return "◎"
        if value == 3: return "〇" 
        if value == 2: return "△"
        return "ー"

    def add_game_fatigue(self, at_bats: int = 0, defensive_innings: float = 0.0, pitches_thrown: int = 0):
        if at_bats == 0 and defensive_innings == 0 and pitches_thrown == 0: return

        """試合中の疲労蓄積
        
        打者: 打席数×1 + 守備イニング×0.5
        投手: 投球数×0.3
        """
        if self.position == Position.PITCHER:
            # 投手は投球数ベース (疲労蓄積を大幅増: 1球=1疲労)
            base_fatigue = int(pitches_thrown * 1.0)
            
            # 先発かどうかの判定
            apt_starter = getattr(self.stats, 'aptitude_starter', 1)
            is_starter = apt_starter >= 3
            
            # 中継ぎの連投ペナルティ: 連投日数に応じて追加疲労
            consecutive = getattr(self, 'consecutive_days', 0)
            if not is_starter and consecutive >= 1:
                # 連投すると疲労が1.5倍～2倍に
                consecutive_mult = 1.0 + (consecutive * 0.25)  # 1連投=1.25x, 2連投=1.5x, 3連投=1.75x...
                consecutive_mult = min(consecutive_mult, 2.5)  # 上限2.5倍
                base_fatigue = int(base_fatigue * consecutive_mult)
            
            self.fatigue += base_fatigue
            if pitches_thrown > 0:
                self.consecutive_days += 1
        else:
            # 野手は打席+守備 (疲労蓄積を大幅増: 1打席=3, 1回=1)
            # 1試合(4打席+9回)で約21疲労蓄積 -> 回復(約15)を上回り、連戦で疲労する設定
            self.fatigue += (at_bats * 3) + int(defensive_innings * 1.0)
        
        self.fatigue = min(100, self.fatigue)

    def check_injury_risk(self, injury_reduction: float = 0.0) -> bool:
        """ケガリスクチェック（疲労と耐久力に基づく）
        
        Args:
            injury_reduction: 怪我軽減率 (0.0-0.35、医療設備投資から取得)
        
        Returns: True if player gets injured
        """
        import random
        
        # 基本リスク: 1プレイあたり0.00002 (0.002%) - 少し上昇
        base_risk = 0.00002
        
        # 疲労補正: 疲労度50で2倍、100で3倍
        fatigue_mult = 1.0 + (self.fatigue / 50)
        
        # 耐久力補正: 耐久50で1倍、100で0.5倍、1で2倍
        durability = getattr(self.stats, 'durability', 50)
        durability_mult = 100 / max(50, durability)
        
        # 医療設備による軽減 (0-35%軽減)
        medical_mult = 1.0 - injury_reduction
        
        final_risk = base_risk * fatigue_mult * durability_mult * medical_mult
        
        if random.random() < final_risk:
            # ケガ発生
            injury_days = random.randint(7, 60)
            injury_names = ["肉離れ", "捻挫", "打撲", "張り", "疲労骨折", "腱炎"]
            self.inflict_injury(injury_days, random.choice(injury_names))
            return True
        return False

    def recover_daily(self):
        """日次ステータス更新 (疲労回復・怪我回復・調子変動)"""
        import random 
        
        # 1. 怪我回復
        if self.is_injured:
            self.injury_days = max(0, self.injury_days - 1)
        
        # 2. 登録抹消期間カウントダウン
        if self.days_until_promotion > 0:
            self.days_until_promotion -= 1
            
        # 3. 調子変動 (ランダムウォーク)
        if random.random() < 0.2:
            change = random.choice([-1, 1])
            self.condition += change
            self.condition = max(1, min(9, self.condition))
            
        # 4. スタミナ & 休養日回復（投手のみ、球数ベース）
        if self.position.value == "投手": 
            self.days_rest += 1
            
            # 回復量計算（回復力と休養日数に基づく）
            recovery_stat = self.stats.recovery if hasattr(self.stats, 'recovery') else 50
            max_pitches = self.calc_max_pitches()
            
            # 完全回復に必要な日数: 回復力1=中6日、回復力99=中4日
            full_recovery_days = 6 - int(recovery_stat / 50)  # 4〜6日
            full_recovery_days = max(4, min(6, full_recovery_days))
            
            if self.days_rest >= full_recovery_days:
                # 完全回復
                self.current_stamina = max_pitches
            else:
                # 段階的回復（中0日でも少し回復）
                # 基本回復量: 回復力の影響を減らす (10球固定 + 回復力による微調整)
                base_recovery = 10 + int((recovery_stat - 50) * 0.1)  # 5-15球
                # 休養日数ボーナス: 1日あたり+4球固定（回復力の影響を削除）
                day_bonus = int(self.days_rest * 4)
                total_recovery = base_recovery + day_bonus
                self.current_stamina = min(max_pitches, self.current_stamina + total_recovery)
            
            # 連投日数リセット（休養した場合）
            if self.days_rest >= 1:
                self.consecutive_days = 0
        
        # 5. 疲労回復（先発と中継ぎを分離）
        recovery_stat = getattr(self.stats, 'recovery', 50)
        
        # 先発かどうかの判定 (aptitude_starter >= 3 = ◎ or 〇)
        is_starter = False
        if self.position == Position.PITCHER:
            apt_starter = getattr(self.stats, 'aptitude_starter', 1)
            is_starter = apt_starter >= 3
        
        if is_starter:
            # 先発投手: 回復力50で約16/日回復 (6日で約100回復 = ほぼ全回復)
            # 回復力の影響は0.08 (回復力1=約12/日, 回復力99=約20/日)
            fatigue_recovery = int(16 + (recovery_stat - 50) * 0.08)
        else:
            # 中継ぎ投手: 回復力50で約10/日回復
            # 回復力の影響は0.04 (回復力1=約8/日, 回復力99=約12/日)
            fatigue_recovery = int(10 + (recovery_stat - 50) * 0.04)
            
            # 連投ペナルティ: consecutive_days > 0 なら回復量を減少
            consecutive = getattr(self, 'consecutive_days', 0)
            if consecutive >= 3:
                fatigue_recovery = int(fatigue_recovery * 0.5)  # 3連投以上: 回復量半減
            elif consecutive >= 2:
                fatigue_recovery = int(fatigue_recovery * 0.7)  # 2連投: 回復量30%減
            elif consecutive >= 1:
                fatigue_recovery = int(fatigue_recovery * 0.9)  # 1連投: 回復量10%減
        
        self.fatigue = max(0, self.fatigue - fatigue_recovery)
        
        # 6. 当日出場フラグリセット
        self.has_played_today = False


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
    
    record_farm: 'TeamRecord' = field(default_factory=TeamRecord)
    record_third: 'TeamRecord' = field(default_factory=TeamRecord)
    team_record: 'TeamRecord' = field(default_factory=TeamRecord)
    
    # チーム合計成績 (詳細スタッツ表示用)
    stats_total: PlayerRecord = field(default_factory=PlayerRecord)
    stats_total_farm: PlayerRecord = field(default_factory=PlayerRecord)
    stats_total_third: PlayerRecord = field(default_factory=PlayerRecord)

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
    
    best_order: List[int] = field(default_factory=list)
    lineup_positions: List[str] = field(default_factory=lambda: ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"])
    
    # オーダーが初期化されているかどうか (False の場合、ユーザーが最初に保存するまで空のまま)
    order_initialized: bool = False
    
    # スタッフ (監督・コーチ・スカウト) - active staff list for training bonus
    staff: List['StaffMember'] = field(default_factory=list)
    # Staff slots (all role slots including empty ones)
    staff_slots: List[Optional['StaffMember']] = field(default_factory=list)
    
    # 財務情報
    finance: 'TeamFinance' = field(default_factory=TeamFinance)
    # 経営設定
    management_settings: 'ManagementSettings' = field(default_factory=ManagementSettings)
    # 投資設定
    investment_settings: 'InvestmentSettings' = field(default_factory=InvestmentSettings)

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

    def get_closer(self) -> Optional[Player]:
        if not self.closers: return None
        idx = self.closers[0]
        if 0 <= idx < len(self.players):
            return self.players[idx]
        return None

    def get_setup_pitcher(self) -> Optional[Player]:
        if not self.setup_pitchers: return None
        # Primary setup
        idx = self.setup_pitchers[0]
        if 0 <= idx < len(self.players):
            return self.players[idx]
        return None

    def get_today_starter(self, level: TeamLevel = TeamLevel.FIRST) -> Optional[Player]:
        # 1. ローテーション順序に従って、登板可能な(中3日以上)投手を探索
        # rotation_indexから順にチェックし、条件を満たす最初の投手を返す
        
        target_rotation = self.rotation
        target_roster = self.active_roster
        if level == TeamLevel.SECOND:
            target_rotation = self.farm_rotation
            target_roster = self.farm_roster
        elif level == TeamLevel.THIRD:
            target_rotation = self.third_rotation
            target_roster = self.third_roster
        
        # まずローテーション内の有効なインデックスをフィルタリング
        valid_rotation = [idx for idx in target_rotation if idx in target_roster and 0 <= idx < len(self.players)]
        
        if valid_rotation:
            try:
                n = len(valid_rotation)
                # rotation_indexが範囲外なら補正
                start_ptr = self.rotation_index % n
                
                for i in range(n):
                    # 現在のインデックスから i 個先を確認
                    idx_ptr = (start_ptr + i) % n
                    p_idx = valid_rotation[idx_ptr]
                    
                    p = self.players[p_idx]
                    # 条件: 怪我していない かつ 指定間隔以上 (スタミナ回復考慮)
                    # 2軍以下は間隔緩めでもOKとするならここで調整
                    required_rest = getattr(p, 'rotation_interval', 6)
                    if not p.is_injured and p.days_rest >= required_rest:
                        return p
            except Exception:
                pass
        
        # 2. ローテが機能していない場合、緊急措置として Roster 全体から探す
        # 条件: 投手、怪我なし、中3日以上
        candidates = []
        for idx in target_roster:
            if 0 <= idx < len(self.players):
                p = self.players[idx]
                required_rest = getattr(p, 'rotation_interval', 6)
                if p.position.value == "投手" and not p.is_injured and p.days_rest >= required_rest:
                    # スコア付け: 適性 > スタミナ > 能力
                    score = 0
                    if p.starter_aptitude >= 4: score += 1000
                    elif p.starter_aptitude == 3: score += 500
                    
                    score += p.current_stamina * 2
                    score += p.stats.overall_pitching()
                    
                    candidates.append((p, score))
                    
        if candidates:
            # ベストな候補を返す
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
            
        # 3. どうしようもない場合: 連投でもいいから一番マシな投手 (Ace Fallbackの前にここで粘る)
        desperate_candidates = []
        for idx in target_roster:
            if 0 <= idx < len(self.players):
                p = self.players[idx]
                if p.position.value == "投手" and not p.is_injured:
                    # 緊急登板でも、先発適性がある程度ある投手を優先
                    # 中継ぎ専任 (適性1) は避ける
                    if p.starter_aptitude >= 2:
                        desperate_candidates.append(p)
                    # どうしてもいない場合はスタミナがある投手 (ロングリリーフ等)
                    elif p.stats.stamina >= 50:
                        desperate_candidates.append(p)
                    
        if desperate_candidates:
            # スタミナ順(元気な順) -> 適性順 でソートしたいが、休養が一番大事
            # days_restが同じなら適性が高い方
            desperate_candidates.sort(key=lambda p: (p.days_rest, p.starter_aptitude), reverse=True)
            return desperate_candidates[0]
            
        # 本当に誰もいない(全員リリーフ専任で連投続き)なら、最後のリリーフ
        final_resort = []
        for idx in target_roster:
            if 0 <= idx < len(self.players):
                p = self.players[idx]
                if p.position.value == "投手" and not p.is_injured:
                    final_resort.append(p)
        if final_resort:
             return max(final_resort, key=lambda p: p.days_rest)
             
        return None

    def auto_assign_pitching_roles(self, level: TeamLevel = TeamLevel.FIRST):
        """
        投手の役割自動設定 (厳格な適性判断・1〜4段階評価版)
        - 先発: 先発適正◎(4)推奨、足りなければ〇(3)も可
        - 中継: 中継適正◎(4)推奨、足りなければ〇(3)も可
        - 抑え: 抑え適正◎(4)推奨、足りなければ〇(3)も可
        - 適正△(2)以下は原則その役割に就けない
        """
        roster_players = self.get_players_by_level(level)
        pitchers = [p for p in roster_players if p.position == Position.PITCHER]
        if not pitchers: return

        pitcher_indices = [self.players.index(p) for p in pitchers]
        
        # --- Helper for sorting ---
        def get_score(p: Player, mode: str):
            # 基本は能力順。適性はフィルタリングに使用済みだが、同値なら適性高い方が良い
            rating = p.stats.overall_pitching()
            if mode == "starter":
                stamina = p.stats.stamina
                return rating * 1.5 + stamina * 1.0 + (p.starter_aptitude * 100.0)
            else:
                velocity = p.stats.velocity
                # Relief aptitude: max of middle/closer? Use relevant one.
                # Caller context handles filtering, so here we use general relief attributes
                return rating * 1.5 + (velocity - 130) * 1.0

        # --- 1. Starters Determination ---
        # 優先度: 適正4 -> 適正3
        starters_s = [p for p in pitchers if p.starter_aptitude >= 4]
        starters_a = [p for p in pitchers if p.starter_aptitude == 3]
        
        starters_s.sort(key=lambda p: get_score(p, "starter"), reverse=True)
        starters_a.sort(key=lambda p: get_score(p, "starter"), reverse=True)
        
        # Combine list
        starter_candidates = starters_s + starters_a
        
        final_starters = starter_candidates[:6]
        
        # 不足時の救済措置 (適正2以下でも能力順で埋める場合)
        # ユーザー要望「それ以外の適性の選手はそのポジションに編成しない」
        # しかし先発6人必須のため、足りない場合は警告しつつ埋めるか、システム上必須なら埋めるしかない。
        # 現状の生成ロジックならS60%あるのでほぼ足りる。
        if len(final_starters) < 6:
            remaining = [p for p in pitchers if p not in final_starters]
            remaining.sort(key=lambda p: get_score(p, "starter"), reverse=True)
            needed = 6 - len(final_starters)
            final_starters.extend(remaining[:needed])
            
        starter_indices = [self.players.index(p) for p in final_starters]

        # --- 2. Relief / Closer Determination ---
        # Pool exclude confirmed starters
        pool = [p for p in pitchers if p not in final_starters]
        
        # Closer: Prefer Aptitude 4 -> 3
        # Strict filter: only >= 3 allowed
        closer_candidates = [p for p in pool if p.closer_aptitude >= 3]
        closer_candidates.sort(key=lambda p: get_score(p, "relief") + (p.closer_aptitude * 50), reverse=True)
        
        final_closer = None
        if closer_candidates:
            final_closer = closer_candidates[0]
        else:
            # Fallback if no valid closer found (rare): Pick best relief aptitude even if < 3?
            # User prohibits it. But we need a closer.
            # We pick best available middle aptitude as fallback
            pool.sort(key=lambda p: get_score(p, "relief") + (p.middle_aptitude * 10), reverse=True)
            if pool: final_closer = pool[0]
            
        closer_idx_list = []
        if final_closer:
            closer_idx_list = [self.players.index(final_closer)]
            pool = [p for p in pool if p != final_closer]

        # Setup / Middle
        # Filter valid middle pitchers (>= 3)
        middle_candidates = [p for p in pool if p.middle_aptitude >= 3]
        
        middle_candidates.sort(key=lambda p: get_score(p, "relief") + (p.middle_aptitude * 20), reverse=True)
        
        setups = middle_candidates[:4]
        others = middle_candidates[4:]

        
        # Invalid pitchers (aptitude <= 2) go to bench/others
        invalid_pool = [p for p in pool if p not in middle_candidates]
        others.extend(invalid_pool) # They sit in bullpen
        
        setup_indices = [self.players.index(p) for p in setups]
        other_indices = [self.players.index(p) for p in others]

        if level == TeamLevel.FIRST:
            self.rotation = starter_indices
            self.closers = closer_idx_list
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
            self.players[player_idx].days_until_promotion = 10
        return True

    def move_to_active_roster(self, player_idx: int) -> bool:
        if player_idx in self.farm_roster: self.farm_roster.remove(player_idx)
        elif player_idx in self.third_roster: self.third_roster.remove(player_idx)
        else: return False
        
        if player_idx not in self.active_roster: self.active_roster.append(player_idx)
        
        if 0 <= player_idx < len(self.players):
            p = self.players[player_idx]
            p.team_level = TeamLevel.FIRST
            
            # 育成選手なら支配下登録（背番号変更）
            if p.is_developmental:
                p.is_developmental = False
                
                # 空き番号を探す (0-99)
                used_numbers = set(pl.uniform_number for pl in self.players)
                import random
                candidates = [n for n in range(0, 100) if n not in used_numbers]
                if candidates:
                    p.uniform_number = random.choice(candidates)
                    
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
        
        # 登録抹消中（昇格不可）の選手を除外してランク付け
        # まず全員をリストアップ
        pitchers = [(i, p) for i, p in enumerate(self.players) if p.position == Pos.PITCHER]
        batters = [(i, p) for i, p in enumerate(self.players) if p.position != Pos.PITCHER]
        
        pitchers.sort(key=lambda x: x[1].stats.overall_pitching(), reverse=True)
        batters.sort(key=lambda x: x[1].stats.overall_batting(), reverse=True)
        
        self.active_roster = []
        self.farm_roster = []
        self.third_roster = []
        
        # 一軍候補 (昇格制限がない選手のみ)
        available_pitchers = [(i, p) for i, p in pitchers if not (hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0)]
        available_batters = [(i, p) for i, p in batters if not (hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0)]
        
        # 制限中の選手
        restricted_pitchers = [(i, p) for i, p in pitchers if (hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0)]
        restricted_batters = [(i, p) for i, p in batters if (hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0)]
        
        # 一軍枠を埋める
        # 投手13人, 野手18人 (計31人)
        # 投手: 先発6 + 中継ぎ6 + 抑え1 = 13人体制
        first_pitchers = [idx for idx, _ in available_pitchers[:13]]
        first_batters = [idx for idx, _ in available_batters[:18]]
        
        self.active_roster = first_pitchers + first_batters
        
        # 残りをプールに戻して再配分 (制限中の選手はここに含まれるべき)
        # availableの残り + restricted
        remaining_pitchers = available_pitchers[13:] + restricted_pitchers
        remaining_batters = available_batters[18:] + restricted_batters
        
        # 再ソート (能力順)
        remaining_pitchers.sort(key=lambda x: x[1].stats.overall_pitching(), reverse=True)
        remaining_batters.sort(key=lambda x: x[1].stats.overall_batting(), reverse=True)
        
        # 二軍 (投手15人, 野手25人 -> 40人枠)
        farm_pitchers = [idx for idx, _ in remaining_pitchers[:15]]
        farm_batters = [idx for idx, _ in remaining_batters[:25]]
        self.farm_roster = farm_pitchers + farm_batters
        
        # 三軍 (残り)
        third_pitchers = [idx for idx, _ in remaining_pitchers[15:]]
        third_batters = [idx for idx, _ in remaining_batters[25:]]
        self.third_roster = third_pitchers + third_batters
        
        # Assign players to rosters and set their team_level attribute
        # Enforce mutual exclusivity to prevent leakage
        active_set = set(self.active_roster)
        farm_set = set(self.farm_roster) - active_set
        third_set = set(self.third_roster) - active_set - farm_set
        
        self.active_roster = list(active_set)
        self.farm_roster = list(farm_set)
        self.third_roster = list(third_set)

        for idx in self.active_roster: self.players[idx].team_level = TeamLevel.FIRST
        for idx in self.farm_roster: self.players[idx].team_level = TeamLevel.SECOND
        for idx in self.third_roster: self.players[idx].team_level = TeamLevel.THIRD
        
        # 枠外の選手は自動的に3軍へ
        all_assigned = active_set | farm_set | third_set
        for i, p in enumerate(self.players):
             if i not in all_assigned and not p.is_developmental:
                 self.third_roster.append(i)
                 p.team_level = TeamLevel.THIRD

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

    def games_behind(self, leader_team: 'Team') -> float:
        """ゲーム差計算 = ((首位勝利 - 自軍勝利) + (自軍敗戦 - 首位敗戦)) / 2"""
        if self == leader_team: return 0.0
        return ((leader_team.wins - self.wins) + (self.losses - leader_team.losses)) / 2.0

@dataclass
class DraftProspect:
    name: str
    position: Position
    pitch_type: Optional[PitchType]
    stats: PlayerStats
    age: int
    origin: str  
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

def _load_team_colors_and_abbrs():
    """Load team colors and abbreviations from team_data files."""
    try:
        from team_data_manager import team_data_manager
        teams_info = team_data_manager.get_all_teams_from_files()
        colors = {}
        abbrs = {}
        for name, data in teams_info["all_data"].items():
            if data.get("色"):
                colors[name] = data["色"]
            if data.get("略称"):
                abbrs[name] = data["略称"]
        return colors, abbrs
    except:
        return {}, {}

# Load from data files with fallback to empty dicts
TEAM_COLORS, TEAM_ABBRS = _load_team_colors_and_abbrs()

def generate_best_lineup(team: Team, roster_players: List[Player], ignore_restriction: bool = False, current_date: str = None) -> List[int]:
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
        try:
            if p.is_injured: continue
            if not ignore_restriction:
                if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0: continue # 制限中の選手は除外
            original_idx = team.players.index(p)
            candidates[original_idx] = p
        except ValueError: continue

    selected_starters = {} 
    used_indices = set()
    
    def calculate_ops_penalty(player) -> float:
        """直近30日のOPSが.500未満の場合にペナルティを適用"""
        if not current_date:
            return 0.0
        try:
            recent = player.get_recent_stats(current_date, days=30)
            if recent and recent.plate_appearances >= 20:
                ops = recent.ops
                if ops < 0.600:
                    # OPSが.600未満なら評価を下げる
                    penalty = (0.600 - ops) * 300
                    return -penalty
        except:
            pass
        return 0.0
    
    def calculate_score(player, pos_name, weight):
        pos_enum_key = None
        for p_enum in Position:
            if p_enum.value == pos_name:
                pos_enum_key = p_enum.name; break
        aptitude = player.stats.get_defense_range(getattr(Position, pos_enum_key))
        if player.position == Position.PITCHER: aptitude = 1
        if aptitude < 1: return -999 
        bat_score = (player.stats.contact * 1.0 + player.stats.power * 1.2 + player.stats.speed * 0.5 + player.stats.eye * 0.5)
        condition_bonus = (player.condition - 5) * 5.0
        def_bonus = 0
        if pos_name == "中堅手": def_bonus = player.stats.speed * 0.5
        if pos_name == "右翼手": def_bonus = player.stats.arm * 0.5
        def_score = (aptitude * 1.5 + player.stats.error * 0.5 + player.stats.arm * 0.5 + def_bonus)
        
        # 直近30日OPSペナルティを適用
        ops_penalty = calculate_ops_penalty(player)
        
        # 疲労ペナルティ: 疲労度60以上で起用スコア減少
        fatigue = getattr(player, 'fatigue', 0)
        fatigue_penalty = max(0, (fatigue - 60) * 0.5) if fatigue > 60 else 0
        
        return bat_score + (def_score * weight) + condition_bonus + ops_penalty - fatigue_penalty

    for pos_enum, pos_name, weight in def_priority:
        best_idx = -1; best_score = -9999.0
        for idx, p in candidates.items():
            if idx in used_indices: continue
            score = calculate_score(p, pos_name, weight)
            if score > best_score: best_score = score; best_idx = idx
        if best_idx != -1: selected_starters[pos_name] = best_idx; used_indices.add(best_idx)
    
    dh_best_idx = -1; dh_best_score = -9999.0
    for idx, p in candidates.items():
        if idx in used_indices: continue
        if p.position == Position.PITCHER: continue
        fatigue = getattr(p, 'fatigue', 0)
        fatigue_pen = max(0, (fatigue - 60) * 0.5) if fatigue > 60 else 0
        score = p.stats.overall_batting() + (p.condition - 5) * 8.0 + calculate_ops_penalty(p) - fatigue_pen
        if score > dh_best_score: dh_best_score = score; dh_best_idx = idx
    if dh_best_idx != -1: selected_starters["DH"] = dh_best_idx; used_indices.add(dh_best_idx)

    lineup_candidates = []
    for pos, idx in selected_starters.items(): lineup_candidates.append(idx)
    
    def get_sort_score(i):
        p = team.players[i]
        fatigue = getattr(p, 'fatigue', 0)
        fatigue_pen = max(0, (fatigue - 60) * 0.5) if fatigue > 60 else 0
        return p.stats.overall_batting() + (p.condition - 5) * 10 + calculate_ops_penalty(p) - fatigue_pen
    
    lineup_candidates.sort(key=get_sort_score, reverse=True)
    if len(lineup_candidates) < 9:
        remaining = [i for i in candidates.keys() if i not in used_indices]
        remaining.sort(key=get_sort_score, reverse=True)
        lineup_candidates.extend(remaining[:9 - len(lineup_candidates)])
    
    return lineup_candidates[:9]