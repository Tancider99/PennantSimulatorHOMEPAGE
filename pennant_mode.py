# -*- coding: utf-8 -*-
"""
ペナントモード - パワプロ風複数年ペナントシステム
複数年プレイ、賞金システム、ドラフト、トレード、FA等を実装
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import random
import math

from models import (
    Player, Team, Position, PitchType, PlayerStatus, League,
    PlayerStats, DraftProspect
)


class PennantPhase(Enum):
    """ペナントのフェーズ"""
    SPRING_CAMP = "春季キャンプ"
    REGULAR_SEASON = "レギュラーシーズン"
    INTERLEAGUE = "交流戦"
    ALL_STAR = "オールスター"
    POST_SEASON = "ポストシーズン"
    CLIMAX_SERIES = "クライマックスシリーズ"
    JAPAN_SERIES = "日本シリーズ"
    OFF_SEASON = "オフシーズン"
    DRAFT = "ドラフト会議"
    FA_PERIOD = "FA期間"
    CONTRACT = "契約更改"


class DraftCategory(Enum):
    """ドラフト選手カテゴリ"""
    HIGH_SCHOOL = "高校生"
    COLLEGE = "大学生"
    CORPORATE = "社会人"
    INDEPENDENT = "独立リーグ"


class InjuryType(Enum):
    """怪我の種類"""
    ARM = "肩・肘"
    LEG = "足・膝"
    BACK = "腰"
    GENERAL = "全身疲労"


@dataclass
class DraftPlayer:
    """ドラフト候補選手"""
    name: str
    position: Position
    category: DraftCategory
    overall: int
    potential: int
    age: int
    school: str = ""
    traits: List[str] = field(default_factory=list)
    scouting_accuracy: float = 0.8  # スカウト精度
    scouting_rank: int = 1  # スカウト順位
    is_reincarnation: bool = False  # 転生選手フラグ
    pitch_type: Optional[PitchType] = None  # 投手の球種
    
    @property
    def potential_grade(self) -> str:
        """ポテンシャルをグレード表示"""
        if self.potential >= 9:
            return "S"
        elif self.potential >= 7:
            return "A"
        elif self.potential >= 5:
            return "B"
        elif self.potential >= 3:
            return "C"
        else:
            return "D"
    
    def to_player(self, team_name: str) -> Player:
        """実際のPlayerオブジェクトに変換"""
        # ポテンシャルに基づいて初期能力を調整
        actual_overall = max(30, min(99, self.overall + random.randint(-10, 10)))
        
        player = Player(
            name=self.name,
            position=self.position,
            team=team_name,
            age=self.age,
            overall=actual_overall,
            potential=self.potential,
            salary=300,  # 初年度年俸
            contract_years=4,  # 新人は4年契約
        )
        return player


@dataclass
class Coach:
    """コーチ情報"""
    name: str
    role: str  # "監督", "投手コーチ", "打撃コーチ", "守備コーチ"
    ability: int  # 1-100
    specialty: str = ""  # 得意分野
    
    def get_training_bonus(self, skill_type: str) -> float:
        """トレーニングボーナス係数"""
        base = self.ability / 100
        if skill_type == self.specialty:
            return base * 1.5
        return base


@dataclass
class Slogan:
    """チームスローガン"""
    text: str
    effect_type: str  # "morale", "offense", "defense", "pitching"
    effect_value: float = 1.1  # 効果倍率


@dataclass
class Injury:
    """怪我情報"""
    injury_type: InjuryType
    severity: int  # 1-10（重症度）
    days_remaining: int
    player_name: str = ""
    
    def heal_day(self) -> bool:
        """1日回復、完治したらTrue"""
        self.days_remaining -= 1
        return self.days_remaining <= 0


@dataclass
class SeasonAward:
    """シーズン表彰"""
    award_name: str
    player_name: str
    team_name: str
    value: float = 0.0


@dataclass
class FAPlayer:
    """FA宣言選手"""
    player: Player
    original_team: str
    rank: str  # "A", "B", "C"
    demands: Dict[str, any] = field(default_factory=dict)
    interested_teams: List[str] = field(default_factory=list)
    
    @property
    def requires_compensation(self) -> bool:
        return self.rank in ["A", "B"]


@dataclass
class TradeOffer:
    """トレードオファー"""
    offering_team: str
    receiving_team: str
    players_offered: List[Player]
    players_requested: List[Player]
    cash_offered: float = 0.0
    status: str = "pending"


@dataclass
class SpringCampState:
    """春季キャンプの状態（モダン版）"""
    current_day: int = 1
    total_days: int = 28
    
    # キャンプフェーズ (4週間制)
    phase: str = "week1"  # week1, week2, week3, week4
    
    # トレーニング配分（各0-100%、合計100%）
    batting_focus: int = 25
    pitching_focus: int = 25
    fielding_focus: int = 25
    conditioning_focus: int = 25
    
    # キャンプ地情報
    camp_location: str = "沖縄"
    weather: str = "晴れ"
    temperature: int = 20
    
    # 一軍・二軍メンバー
    first_team_players: List = field(default_factory=list)
    second_team_players: List = field(default_factory=list)
    
    # チーム状態
    team_morale: int = 50  # 0-100
    team_fatigue: int = 0  # 0-100
    
    # 選手個別の疲労度
    player_fatigue: Dict = field(default_factory=dict)  # {player_id: fatigue_value}
    
    # 休息・特別トレーニング
    rest_focus: int = 0  # 休息配分（0-100）
    physical_focus: int = 0  # フィジカル配分
    special_training: str = ""  # 特別トレーニング種類
    
    # 実績
    intrasquad_games: int = 0  # 紅白戦回数
    practice_games: int = 0   # オープン戦回数
    practice_wins: int = 0    # オープン戦勝利数
    
    # 成長記録
    growth_results: Dict = field(default_factory=dict)  # {player_name: [growth_events]}
    new_abilities: List = field(default_factory=list)   # 習得した特殊能力
    new_skills: List = field(default_factory=list)      # 新規スキル習得記録
    injuries: List = field(default_factory=list)        # 怪我一覧
    
    # 注目選手
    mvp_candidate: str = ""
    best_rookie: str = ""
    
    # 累計ステータス
    total_batting_growth: int = 0
    total_pitching_growth: int = 0
    total_fielding_growth: int = 0
    
    # 追加：MVP獲得回数
    mvp_counts: Dict = field(default_factory=dict)  # {player_name: count}
    
    # キャンプ目標
    goals: Dict = field(default_factory=lambda: {
        "intrasquad": {"target": 3, "current": 0},  # 紅白戦3回
        "practice": {"target": 5, "current": 0},    # オープン戦5回
        "growth": {"target": 10, "current": 0}      # 成長10回
    })
    
    @property
    def week(self) -> int:
        """現在の週（1-4）"""
        return min(4, (self.current_day - 1) // 7 + 1)
    
    @property
    def day_in_week(self) -> int:
        """週内の日（1-7）"""
        return ((self.current_day - 1) % 7) + 1
    
    def get_phase_name(self) -> str:
        phases = {
            "week1": "第1週 - 基礎トレーニング",
            "week2": "第2週 - 強化練習",
            "week3": "第3週 - 実戦練習",
            "week4": "第4週 - 仕上げ"
        }
        return phases.get(self.phase, "キャンプ")
    
    def advance_day(self) -> Dict:
        """1日進める"""
        result = {"day": self.current_day, "events": []}
        
        self.current_day += 1
        
        # フェーズ更新
        week = self.week
        self.phase = f"week{week}"
        
        # 天気変動
        self.weather = random.choices(
            ["晴れ", "曇り", "雨"],
            weights=[60, 30, 10]
        )[0]
        
        # 気温変動
        self.temperature = max(15, min(28, self.temperature + random.randint(-2, 2)))
        
        # 疲労回復（休養配分に応じて）
        recovery = max(5, 100 - self.conditioning_focus) // 10
        self.team_fatigue = max(0, self.team_fatigue - recovery)
        
        return result


@dataclass
class TeamFinances:
    """チーム財政状況"""
    budget: float = 50.0
    payroll: float = 30.0
    revenue: float = 40.0
    expenses: float = 35.0
    cash: float = 10.0
    
    @property
    def balance(self) -> float:
        return self.revenue - self.expenses - self.payroll
    
    @property
    def payroll_space(self) -> float:
        return max(0, self.budget - self.payroll)


class PennantManager:
    """ペナントモード管理クラス（強化版）"""
    
    def __init__(self, teams: List[Team] = None, start_year: int = 2027, max_years: int = 30):
        self.teams = teams or []
        self.current_year = start_year
        self.max_years = max_years
        self.current_phase = PennantPhase.SPRING_CAMP
        self.player_team_name: str = ""
        
        self.season_records: Dict[int, Dict] = {}
        self.awards_history: List[SeasonAward] = []
        
        self.draft_pool: List[DraftPlayer] = []
        self.draft_order: List[str] = []
        self.draft_results: Dict[int, List] = {}
        
        self.fa_players: List[FAPlayer] = []
        self.fa_history: Dict[int, List] = {}
        
        self.trade_offers: List[TradeOffer] = []
        self.trade_history: List[TradeOffer] = []
        
        self.team_finances: Dict[str, TeamFinances] = {}
        if self.teams:
            for team in self.teams:
                self.team_finances[team.name] = TeamFinances()
        
        self.injuries: Dict[int, Injury] = {}
        self.fatigue: Dict[int, float] = {}
        
        self.spring_camp_state: Optional[SpringCampState] = None
    
    def initialize_pennant(self, all_teams: List[Team], player_team: Team):
        """ペナントを初期化（後から設定する場合用）"""
        self.teams = all_teams
        self.player_team_name = player_team.name if player_team else ""
        
        # チーム財政を初期化
        self.team_finances = {}
        for team in self.teams:
            self.team_finances[team.name] = TeamFinances()
    
    def advance_phase(self):
        """次のフェーズに進む"""
        phase_order = [
            PennantPhase.SPRING_CAMP,
            PennantPhase.REGULAR_SEASON,
            PennantPhase.INTERLEAGUE,
            PennantPhase.ALL_STAR,
            PennantPhase.POST_SEASON,
            PennantPhase.CLIMAX_SERIES,
            PennantPhase.JAPAN_SERIES,
            PennantPhase.OFF_SEASON,
            PennantPhase.DRAFT,
            PennantPhase.FA_PERIOD,
            PennantPhase.CONTRACT,
        ]
        
        current_idx = phase_order.index(self.current_phase)
        next_idx = (current_idx + 1) % len(phase_order)
        
        if next_idx == 0:
            self.current_year += 1
        
        self.current_phase = phase_order[next_idx]
        return self.current_phase
    
    def generate_draft_pool(self, count: int = 60) -> List[DraftPlayer]:
        """ドラフト候補を生成"""
        from player_generator import generate_japanese_name, generate_high_school_name
        
        self.draft_pool = []
        
        categories = [
            (DraftCategory.HIGH_SCHOOL, 0.3, 18),
            (DraftCategory.COLLEGE, 0.35, 22),
            (DraftCategory.CORPORATE, 0.25, 24),
            (DraftCategory.INDEPENDENT, 0.1, 23),
        ]
        
        # 転生選手名（稀に出現）
        reincarnation_names = ["田中 将大", "大谷 翔平", "ダルビッシュ 有", "松坂 大輔", "イチロー", "松井 秀喜"]
        
        for category, ratio, base_age in categories:
            cat_count = int(count * ratio)
            for _ in range(cat_count):
                # ランダムにポジション決定
                is_pitcher = random.random() < 0.4
                if is_pitcher:
                    position = Position.PITCHER
                    pitch_type = random.choice([PitchType.OVERHAND, PitchType.SIDEARM, PitchType.UNDERHAND])
                else:
                    position = random.choice([Position.CATCHER, Position.FIRST, Position.SECOND,
                                             Position.SHORT, Position.THIRD, Position.LEFT,
                                             Position.CENTER, Position.RIGHT])
                    pitch_type = None
                
                # ポテンシャル決定（カテゴリで差をつける）
                if category == DraftCategory.HIGH_SCHOOL:
                    potential = random.randint(3, 10)  # 高校生は振れ幅大
                elif category == DraftCategory.COLLEGE:
                    potential = random.randint(4, 9)   # 大学生は安定
                elif category == DraftCategory.CORPORATE:
                    potential = random.randint(3, 7)   # 社会人は即戦力
                else:
                    potential = random.randint(2, 8)   # 独立リーグ
                
                # 総合力決定
                overall = max(30, min(85, 40 + potential * 4 + random.randint(-10, 10)))
                
                # 転生選手チェック（1%の確率）
                is_reincarnation = random.random() < 0.01
                if is_reincarnation:
                    name = random.choice(reincarnation_names)
                    potential = random.randint(8, 10)
                    overall = max(70, overall + 15)
                else:
                    name = generate_japanese_name()
                
                # 学校名
                if category == DraftCategory.HIGH_SCHOOL:
                    school = generate_high_school_name()
                elif category == DraftCategory.COLLEGE:
                    school = random.choice(["東京大学", "早稲田大学", "慶應義塾大学", "明治大学", "法政大学", 
                                           "立教大学", "中央大学", "青山学院大学", "日本大学", "東洋大学"])
                elif category == DraftCategory.CORPORATE:
                    school = random.choice(["JR東日本", "トヨタ自動車", "Honda", "パナソニック", "NTT東日本",
                                           "日本生命", "ENEOS", "三菱重工", "JFE", "日本通運"])
                else:
                    school = random.choice(["四国IL", "BCリーグ", "ルートインBCL", "九州アジアリーグ"])
                
                prospect = DraftPlayer(
                    name=name,
                    position=position,
                    category=category,
                    overall=overall,
                    potential=potential,
                    age=base_age + random.randint(0, 1),
                    school=school,
                    pitch_type=pitch_type,
                    is_reincarnation=is_reincarnation
                )
                self.draft_pool.append(prospect)
        
        # スカウトランキングを設定
        self.draft_pool.sort(key=lambda x: x.potential + x.overall / 20, reverse=True)
        for i, prospect in enumerate(self.draft_pool):
            prospect.scouting_rank = i + 1
        
        return self.draft_pool
    
    def set_draft_order(self, reverse_standings: bool = True):
        """ドラフト指名順を設定"""
        team_records = [(t.name, t.wins, t.losses) for t in self.teams]
        
        if reverse_standings:
            team_records.sort(key=lambda x: x[1] / max(1, x[1] + x[2]))
        else:
            team_records.sort(key=lambda x: x[1] / max(1, x[1] + x[2]), reverse=True)
        
        self.draft_order = [t[0] for t in team_records]
    
    def execute_draft_pick(self, team_name: str, prospect: DraftPlayer) -> Player:
        """ドラフト指名を実行"""
        # ポテンシャルベースでステータスを生成
        stats = PlayerStats()
        base_min = max(3, prospect.potential - 2)
        base_max = min(15, prospect.potential + 4)
        
        if prospect.position == Position.PITCHER:
            stats.speed = random.randint(base_min, base_max)
            stats.control = random.randint(base_min, base_max)
            stats.stamina = random.randint(base_min, base_max)
            stats.breaking = random.randint(base_min, base_max)
            stats.mental = random.randint(base_min, base_max)
        else:
            stats.contact = random.randint(base_min, base_max)
            stats.power = random.randint(base_min, base_max)
            stats.run = random.randint(base_min, base_max)
            stats.arm = random.randint(base_min - 1, base_max)
            stats.fielding = random.randint(base_min, base_max)
            stats.mental = random.randint(base_min, base_max)
        
        player = Player(
            name=prospect.name,
            position=prospect.position,
            pitch_type=prospect.pitch_type,
            age=prospect.age,
            stats=stats
        )
        player.years_pro = 0
        player.draft_round = 1
        
        if prospect in self.draft_pool:
            self.draft_pool.remove(prospect)
        
        if self.current_year not in self.draft_results:
            self.draft_results[self.current_year] = []
        self.draft_results[self.current_year].append({
            "team": team_name,
            "player": player.name,
            "position": player.position.value,
            "potential": prospect.potential
        })
        
        return player
    
    def check_fa_eligibility(self, player: Player) -> bool:
        return player.years_pro >= 8
    
    def process_fa_declaration(self, player: Player, team: Team) -> Optional[FAPlayer]:
        if not self.check_fa_eligibility(player):
            return None
        
        overall = player.stats.overall_batting() if player.position != Position.PITCHER else player.stats.overall_pitching()
        
        if overall >= 70:
            rank = "A"
        elif overall >= 60:
            rank = "B"
        else:
            rank = "C"
        
        fa_player = FAPlayer(
            player=player,
            original_team=team.name,
            rank=rank
        )
        
        self.fa_players.append(fa_player)
        return fa_player
    
    def sign_fa_player(self, fa_player: FAPlayer, new_team: Team, contract_years: int, salary: int):
        player = fa_player.player
        player.salary = salary
        player.contract_years = contract_years
        
        new_team.players.append(player)
        
        if fa_player in self.fa_players:
            self.fa_players.remove(fa_player)
        
        if self.current_year not in self.fa_history:
            self.fa_history[self.current_year] = []
        self.fa_history[self.current_year].append({
            "player": player.name,
            "from": fa_player.original_team,
            "to": new_team.name,
            "salary": salary
        })
    
    def create_trade_offer(self, offering_team: str, receiving_team: str,
                           players_offered: List[Player], players_requested: List[Player],
                           cash: float = 0.0) -> TradeOffer:
        offer = TradeOffer(
            offering_team=offering_team,
            receiving_team=receiving_team,
            players_offered=players_offered,
            players_requested=players_requested,
            cash_offered=cash
        )
        self.trade_offers.append(offer)
        return offer
    
    def evaluate_trade(self, offer: TradeOffer) -> float:
        offered_value = sum(self._calculate_player_value(p) for p in offer.players_offered)
        offered_value += offer.cash_offered * 5
        requested_value = sum(self._calculate_player_value(p) for p in offer.players_requested)
        return offered_value - requested_value
    
    def _calculate_player_value(self, player: Player) -> float:
        base_value = player.stats.overall_batting() if player.position != Position.PITCHER else player.stats.overall_pitching()
        age_factor = max(0.5, 1.0 - (player.age - 27) * 0.05)
        potential = player.growth.potential if player.growth else 5
        potential_factor = potential / 7.0
        return base_value * age_factor * potential_factor
    
    def accept_trade(self, offer: TradeOffer):
        offer.status = "accepted"
        self.trade_history.append(offer)
    
    def reject_trade(self, offer: TradeOffer):
        offer.status = "rejected"
    
    # ========================================
    # 春季キャンプ（モダン版）
    # ========================================
    def start_spring_camp(self, total_days: int = 28, team: Team = None) -> SpringCampState:
        """春季キャンプを開始"""
        self.spring_camp_state = SpringCampState(total_days=total_days)
        camp = self.spring_camp_state
        
        # キャンプ地を設定（チーム別）
        camp_locations = {
            "読売ジャイアンツ": ("宮崎", 18),
            "阪神タイガース": ("沖縄", 22),
            "中日ドラゴンズ": ("沖縄", 21),
            "横浜DeNAベイスターズ": ("沖縄", 23),
            "広島東洋カープ": ("沖縄", 22),
            "東京ヤクルトスワローズ": ("沖縄", 21),
            "福岡ソフトバンクホークス": ("宮崎", 19),
            "オリックス・バファローズ": ("宮崎", 18),
            "千葉ロッテマリーンズ": ("沖縄", 22),
            "埼玉西武ライオンズ": ("宮崎", 17),
            "東北楽天ゴールデンイーグルス": ("沖縄", 23),
            "北海道日本ハムファイターズ": ("沖縄", 24),
        }
        
        if team and team.name in camp_locations:
            camp.camp_location, camp.temperature = camp_locations[team.name]
        else:
            camp.camp_location = random.choice(["沖縄", "宮崎", "高知"])
            camp.temperature = random.randint(18, 24)
        
        # 一軍・二軍を振り分け
        if team:
            from models import Position as Pos
            pitchers = sorted([p for p in team.players if p.position == Pos.PITCHER],
                            key=lambda x: x.stats.overall_pitching(), reverse=True)
            batters = sorted([p for p in team.players if p.position != Pos.PITCHER],
                           key=lambda x: x.stats.overall_batting(), reverse=True)
            
            # 一軍: 投手10名 + 野手15名
            camp.first_team_players = [p.name for p in pitchers[:10] + batters[:15]]
            camp.second_team_players = [p.name for p in pitchers[10:] + batters[15:]]
            
            # 注目ルーキーを選出
            rookies = [p for p in team.players if p.years_pro <= 1]
            if rookies:
                best_rookie = max(rookies, key=lambda x: x.growth.potential if x.growth else 5)
                camp.best_rookie = best_rookie.name
        
        return camp
    
    def set_camp_training(self, batting: int, pitching: int, fielding: int, conditioning: int):
        """キャンプのトレーニング配分を設定（合計100%）"""
        if not self.spring_camp_state:
            return
        
        total = batting + pitching + fielding + conditioning
        if total > 0:
            # 正規化して100%に
            self.spring_camp_state.batting_focus = int(100 * batting / total)
            self.spring_camp_state.pitching_focus = int(100 * pitching / total)
            self.spring_camp_state.fielding_focus = int(100 * fielding / total)
            self.spring_camp_state.conditioning_focus = int(100 * conditioning / total)
    
    def advance_camp_day(self, team: Team) -> Dict[str, any]:
        """キャンプを1日進める"""
        if not self.spring_camp_state:
            return {}
        
        camp = self.spring_camp_state
        results = {
            "day": camp.current_day,
            "week": camp.week,
            "phase_name": camp.get_phase_name(),
            "growth": [],
            "events": [],
            "injuries": [],
        }
        
        # 週ごとのボーナス（後半ほど成長しやすい）
        week_bonus = {1: 0.8, 2: 1.0, 3: 1.2, 4: 1.0}
        mult = week_bonus.get(camp.week, 1.0)
        
        # 天気による補正
        weather_mult = {"晴れ": 1.1, "曇り": 1.0, "雨": 0.8}
        mult *= weather_mult.get(camp.weather, 1.0)
        
        # 各選手の成長処理
        for player in team.players:
            growth = self._process_player_camp_training(player, camp, mult)
            if growth:
                results["growth"].append(growth)
                
                # 累計成長を記録
                if player.position == Position.PITCHER:
                    camp.total_pitching_growth += growth.get("total", 0)
                else:
                    camp.total_batting_growth += growth.get("total", 0)
                    camp.total_fielding_growth += growth.get("fielding", 0)
        
        # 疲労蓄積
        fatigue_increase = (100 - camp.conditioning_focus) // 20
        camp.team_fatigue = min(100, camp.team_fatigue + fatigue_increase)
        
        # 怪我判定（疲労が高いほど危険）
        injury_chance = 0.01 + (camp.team_fatigue / 1000)
        if random.random() < injury_chance:
            injured_player = random.choice(team.players)
            injury_days = random.randint(3, 14)
            camp.injuries.append({
                "player": injured_player.name,
                "days": injury_days,
                "type": random.choice(["筋肉痛", "捻挫", "打撲"])
            })
            results["injuries"].append(injured_player.name)
        
        # 士気変動
        if camp.team_fatigue > 70:
            camp.team_morale = max(0, camp.team_morale - 3)
        elif camp.team_fatigue < 30:
            camp.team_morale = min(100, camp.team_morale + 2)
        
        # 日を進める
        camp.advance_day()
        
        return results
    
    def _process_player_camp_training(self, player: Player, camp: SpringCampState, mult: float) -> Dict:
        """選手のキャンプトレーニング処理"""
        result = {"player": player.name, "changes": [], "total": 0}
        
        # 疲労ペナルティ
        fatigue_mult = max(0.5, 1.0 - camp.team_fatigue / 200)
        mult *= fatigue_mult
        
        # ポテンシャルボーナス
        potential = player.growth.potential if player.growth else 5
        potential_mult = 0.8 + (potential * 0.04)
        mult *= potential_mult
        
        if player.position == Position.PITCHER:
            # 投手の成長
            if random.random() < 0.15 * mult * (camp.pitching_focus / 25):
                stat_choice = random.choice(["speed", "control", "stamina", "breaking"])
                old_val = getattr(player.stats, stat_choice)
                new_val = min(20, old_val + 1)
                setattr(player.stats, stat_choice, new_val)
                result["changes"].append(f"{stat_choice}+1")
                result["total"] += 1
        else:
            # 野手の成長
            if random.random() < 0.12 * mult * (camp.batting_focus / 25):
                stat_choice = random.choice(["contact", "power", "run"])
                old_val = getattr(player.stats, stat_choice)
                new_val = min(20, old_val + 1)
                setattr(player.stats, stat_choice, new_val)
                result["changes"].append(f"{stat_choice}+1")
                result["total"] += 1
            
            if random.random() < 0.10 * mult * (camp.fielding_focus / 25):
                stat_choice = random.choice(["fielding", "arm"])
                old_val = getattr(player.stats, stat_choice)
                new_val = min(20, old_val + 1)
                setattr(player.stats, stat_choice, new_val)
                result["changes"].append(f"{stat_choice}+1")
                result["fielding"] = 1
        
        return result if result["changes"] else None
    
    def run_intrasquad_game(self, team: Team) -> Dict:
        """紅白戦を実施"""
        if not self.spring_camp_state:
            return {}
        
        camp = self.spring_camp_state
        camp.intrasquad_games += 1
        
        # 結果をシミュレート
        team1_score = random.randint(0, 8)
        team2_score = random.randint(0, 8)
        
        # MVPを選出
        mvp = random.choice(team.players)
        
        # 士気上昇
        camp.team_morale = min(100, camp.team_morale + 3)
        
        return {
            "team1_score": team1_score,
            "team2_score": team2_score,
            "mvp": mvp.name,
            "total_games": camp.intrasquad_games
        }
    
    def run_practice_game(self, team: Team, opponent: str = "他球団") -> Dict:
        """オープン戦を実施"""
        if not self.spring_camp_state:
            return {}
        
        camp = self.spring_camp_state
        camp.practice_games += 1
        
        # 結果をシミュレート
        our_score = random.randint(0, 10)
        their_score = random.randint(0, 10)
        won = our_score > their_score
        
        if won:
            camp.practice_wins += 1
            camp.team_morale = min(100, camp.team_morale + 5)
        else:
            camp.team_morale = max(0, camp.team_morale - 2)
        
        return {
            "opponent": opponent,
            "our_score": our_score,
            "their_score": their_score,
            "won": won,
            "record": f"{camp.practice_wins}勝{camp.practice_games - camp.practice_wins}敗"
        }
    
    def auto_complete_camp(self, team: Team) -> Dict:
        """キャンプを自動で完了"""
        results = {
            "days_completed": 0,
            "total_growth": [],
            "injuries": [],
            "final_morale": 0,
            "practice_record": ""
        }
        
        while self.spring_camp_state and self.spring_camp_state.current_day <= self.spring_camp_state.total_days:
            day_result = self.advance_camp_day(team)
            results["days_completed"] += 1
            results["total_growth"].extend(day_result.get("growth", []))
            results["injuries"].extend(day_result.get("injuries", []))
            
            # 週末に紅白戦
            if self.spring_camp_state.day_in_week == 7:
                self.run_intrasquad_game(team)
            
            # 4週目はオープン戦
            if self.spring_camp_state.week == 4 and self.spring_camp_state.day_in_week in [2, 4, 6]:
                self.run_practice_game(team)
        
        if self.spring_camp_state:
            results["final_morale"] = self.spring_camp_state.team_morale
            results["practice_record"] = f"{self.spring_camp_state.practice_wins}勝{self.spring_camp_state.practice_games - self.spring_camp_state.practice_wins}敗"
        
        return results

    # ========================================
    # 怪我管理
    # ========================================
    def check_injury(self, player: Player) -> Optional[Injury]:
        
        return camp
    
    def _generate_camp_schedule(self, total_days: int) -> List[Dict]:
        """キャンプスケジュールを生成"""
        schedule = []
        for day in range(1, total_days + 1):
            if day <= 7:
                # 第1クール: 基礎練習中心
                event = random.choice(["基礎練習", "体力測定", "フォームチェック", "走り込み"])
            elif day <= 14:
                # 第2クール: 実戦練習
                event = random.choice(["紅白戦", "シート打撃", "投内連携", "サイン確認"])
            elif day <= 21:
                # 第3クール: 仕上げ
                event = random.choice(["実戦形式", "紅白戦", "調整", "ミーティング"])
            else:
                # 第4クール: オープン戦
                event = random.choice(["オープン戦", "調整", "休養日", "移動日"])
            
            schedule.append({
                "day": day,
                "phase": "early" if day <= 7 else "middle" if day <= 14 else "late" if day <= 21 else "game",
                "main_event": event,
                "completed": False
            })
        return schedule
    
    def set_camp_training_menu(self, batting: int = 3, pitching: int = 3,
                                fielding: int = 3, physical: int = 3,
                                rest: int = 3, mental: int = 3):
        """キャンプのトレーニングメニュー配分を設定"""
        if self.spring_camp_state:
            self.spring_camp_state.batting_focus = max(1, min(5, batting))
            self.spring_camp_state.pitching_focus = max(1, min(5, pitching))
            self.spring_camp_state.fielding_focus = max(1, min(5, fielding))
            self.spring_camp_state.physical_focus = max(1, min(5, physical))
            self.spring_camp_state.rest_focus = max(1, min(5, rest))
            self.spring_camp_state.mental_focus = max(1, min(5, mental))
    
    def set_special_training(self, training_type: str):
        """特別トレーニングを設定"""
        valid_types = ["batting_cage", "bullpen", "video_study", "weight", "running", "yoga", ""]
        if self.spring_camp_state and training_type in valid_types:
            self.spring_camp_state.special_training = training_type
    
    def advance_camp_day(self, team: Team) -> Dict[str, any]:
        """キャンプを1日進める（強化版）"""
        if not self.spring_camp_state:
            return {}
        
        camp = self.spring_camp_state
        results = {
            "day": camp.current_day,
            "phase": camp.phase,
            "phase_name": camp.get_phase_name(),
            "growth": {},
            "events": [],
            "injuries": [],
            "condition_changes": [],
            "special_training_result": None,
            "skill_acquired": [],
            "daily_highlight": None,
        }
        
        phase_bonus = {"early": 0.8, "middle": 1.0, "late": 1.2, "game": 1.0}
        phase_mult = phase_bonus.get(camp.phase, 1.0)
        
        growth_count = 0
        for player in team.players:
            player_results = self._process_player_camp_day_v2(player, camp, phase_mult)
            
            if player_results.get("growth"):
                results["growth"][player.name] = player_results["growth"]
                growth_count += len(player_results["growth"])
            if player_results.get("event"):
                results["events"].append((player.name, player_results["event"]))
            if player_results.get("injury"):
                results["injuries"].append((player.name, player_results["injury"]))
            if player_results.get("condition"):
                results["condition_changes"].append((player.name, player_results["condition"]))
            if player_results.get("new_skill"):
                results["skill_acquired"].append((player.name, player_results["new_skill"]))
                camp.new_skills.append((player.name, player_results["new_skill"]))
        
        if camp.special_training:
            results["special_training_result"] = self._process_special_training(team, camp)
        
        if results["growth"]:
            best_player = max(results["growth"].items(),
                            key=lambda x: sum(x[1].values()) if x[1] else 0)
            results["daily_highlight"] = f"{best_player[0]}が大きく成長！"
        elif results["events"]:
            results["daily_highlight"] = results["events"][0][1]
        
        for name, growth in results["growth"].items():
            if name not in camp.growth_results:
                camp.growth_results[name] = {}
            for stat, value in growth.items():
                camp.growth_results[name][stat] = camp.growth_results[name].get(stat, 0) + value
        
        camp.injuries.extend(results["injuries"])
        camp.advance_day()
        
        return results
    
    def _process_player_camp_day_v2(self, player: Player, camp: SpringCampState, phase_mult: float) -> Dict:
        """選手の1日のキャンプ処理（強化版）"""
        results = {"growth": {}, "event": None, "injury": None, "condition": None, "new_skill": None}
        
        player_id = id(player)
        fatigue = camp.player_fatigue.get(player_id, 0)
        
        rest_recovery = camp.rest_focus * 8 + (5 if camp.special_training == "yoga" else 0)
        fatigue = max(0, fatigue - rest_recovery)
        
        training_intensity = (camp.batting_focus + camp.pitching_focus +
                            camp.fielding_focus + camp.physical_focus)
        training_fatigue = training_intensity * 2.5
        if camp.special_training in ["weight", "running"]:
            training_fatigue *= 1.3
        fatigue = min(100, fatigue + training_fatigue)
        camp.player_fatigue[player_id] = fatigue
        
        base_injury_risk = 0.003
        fatigue_risk = (fatigue / 100) ** 2 * 0.03
        injury_risk = base_injury_risk + fatigue_risk
        
        if player.age <= 23:
            injury_risk *= 0.7
        elif player.age >= 34:
            injury_risk *= 1.5
        
        if random.random() < injury_risk:
            injury = self.check_injury(player)
            if injury:
                results["injury"] = injury
                return results
        
        is_pitcher = player.position == Position.PITCHER
        
        base_growth_chance = 0.12 + (camp.physical_focus * 0.015) + (camp.mental_focus * 0.01)
        
        potential = player.growth.potential if player.growth else 5
        growth_modifier = 1.0 + (potential - 5) * 0.15
        
        if player.age <= 22:
            growth_modifier *= 1.4
        elif player.age <= 25:
            growth_modifier *= 1.2
        elif player.age >= 33:
            growth_modifier *= 0.6
        elif player.age >= 30:
            growth_modifier *= 0.8
        
        growth_modifier *= phase_mult
        
        if is_pitcher:
            self._process_pitcher_growth(player, camp, base_growth_chance, growth_modifier, results)
        else:
            self._process_batter_growth(player, camp, base_growth_chance, growth_modifier, results)
        
        skill_chance = 0.008 + (camp.mental_focus * 0.002)
        if random.random() < skill_chance:
            new_skill = self._try_acquire_skill(player, is_pitcher)
            if new_skill:
                results["new_skill"] = new_skill
        
        if random.random() < 0.05:
            event = self._generate_camp_event_v2(player, is_pitcher, camp.phase)
            if event:
                results["event"] = event
        
        return results
    
    def _process_pitcher_growth(self, player: Player, camp: SpringCampState,
                                base_chance: float, modifier: float, results: Dict):
        """投手の成長処理"""
        if random.random() < base_chance * (camp.physical_focus / 3) * modifier:
            growth_value = random.choices([1, 2, 3], weights=[60, 35, 5])[0]
            self._apply_stat_growth(player, "speed", growth_value)
            results["growth"]["球速"] = growth_value
        
        if random.random() < base_chance * (camp.pitching_focus / 3) * modifier:
            growth_value = random.choices([1, 2, 3], weights=[55, 40, 5])[0]
            self._apply_stat_growth(player, "control", growth_value)
            results["growth"]["制球"] = growth_value
        
        if random.random() < base_chance * ((camp.physical_focus + camp.pitching_focus) / 6) * modifier:
            growth_value = random.choices([1, 2, 3], weights=[50, 40, 10])[0]
            self._apply_stat_growth(player, "stamina", growth_value)
            results["growth"]["スタミナ"] = growth_value
        
        if random.random() < base_chance * (camp.pitching_focus / 3) * modifier:
            growth_value = random.choices([1, 2], weights=[70, 30])[0]
            self._apply_stat_growth(player, "breaking", growth_value)
            results["growth"]["変化球"] = growth_value
        
        if random.random() < base_chance * (camp.mental_focus / 3) * modifier * 0.5:
            growth_value = random.randint(1, 2)
            self._apply_stat_growth(player, "mental", growth_value)
            results["growth"]["メンタル"] = growth_value
    
    def _process_batter_growth(self, player: Player, camp: SpringCampState,
                               base_chance: float, modifier: float, results: Dict):
        """野手の成長処理"""
        if random.random() < base_chance * (camp.batting_focus / 3) * modifier:
            growth_value = random.choices([1, 2, 3], weights=[55, 40, 5])[0]
            self._apply_stat_growth(player, "contact", growth_value)
            results["growth"]["ミート"] = growth_value
        
        if random.random() < base_chance * ((camp.batting_focus + camp.physical_focus) / 6) * modifier:
            growth_value = random.choices([1, 2, 3], weights=[60, 35, 5])[0]
            self._apply_stat_growth(player, "power", growth_value)
            results["growth"]["パワー"] = growth_value
        
        if random.random() < base_chance * (camp.physical_focus / 3) * modifier:
            growth_value = random.choices([1, 2], weights=[65, 35])[0]
            self._apply_stat_growth(player, "run", growth_value)
            results["growth"]["走力"] = growth_value
        
        if random.random() < base_chance * (camp.fielding_focus / 3) * modifier:
            growth_value = random.choices([1, 2, 3], weights=[50, 40, 10])[0]
            self._apply_stat_growth(player, "fielding", growth_value)
            results["growth"]["守備"] = growth_value
        
        if random.random() < base_chance * (camp.fielding_focus / 3) * modifier * 0.7:
            growth_value = random.randint(1, 2)
            self._apply_stat_growth(player, "arm", growth_value)
            results["growth"]["肩力"] = growth_value
        
        if random.random() < base_chance * (camp.mental_focus / 3) * modifier * 0.5:
            growth_value = random.randint(1, 2)
            self._apply_stat_growth(player, "mental", growth_value)
            results["growth"]["メンタル"] = growth_value
    
    def _apply_stat_growth(self, player: Player, stat: str, value: int):
        """能力値を成長させる"""
        current = getattr(player.stats, stat, 50)
        new_value = min(99, current + value)
        setattr(player.stats, stat, new_value)
    
    def _try_acquire_skill(self, player: Player, is_pitcher: bool) -> Optional[str]:
        """特殊能力獲得を試みる"""
        pitcher_skills = [
            "打たれ強さ", "クイック○", "牽制○", "緩急○", "重い球",
            "キレ○", "低め○", "内角○", "奪三振", "対ピンチ○"
        ]
        batter_skills = [
            "チャンス○", "対左投手○", "送球○", "走塁○", "内野安打○",
            "粘り打ち", "逆方向", "プルヒッター", "流し打ち", "バント○"
        ]
        skills = pitcher_skills if is_pitcher else batter_skills
        return random.choice(skills)
    
    def _process_special_training(self, team: Team, camp: SpringCampState) -> Dict:
        """特別トレーニングの効果を処理"""
        training_effects = {
            "batting_cage": {"stat": "contact", "bonus": 0.3, "desc": "打撃ケージ練習で集中強化"},
            "bullpen": {"stat": "control", "bonus": 0.3, "desc": "ブルペン投球で制球力アップ"},
            "video_study": {"stat": "mental", "bonus": 0.4, "desc": "映像分析でメンタル強化"},
            "weight": {"stat": "power", "bonus": 0.35, "desc": "ウエイトトレーニングでパワーアップ"},
            "running": {"stat": "run", "bonus": 0.35, "desc": "走り込みで足腰強化"},
            "yoga": {"stat": "stamina", "bonus": 0.2, "desc": "ヨガで柔軟性アップ・疲労回復"},
        }
        
        effect = training_effects.get(camp.special_training)
        if not effect:
            return {}
        
        affected_players = random.sample(team.players, min(3, len(team.players)))
        result = {"training": camp.special_training, "desc": effect["desc"], "affected": []}
        
        for player in affected_players:
            if random.random() < effect["bonus"]:
                stat = effect["stat"]
                growth = random.randint(1, 2)
                self._apply_stat_growth(player, stat, growth)
                result["affected"].append(f"{player.name}: {stat}+{growth}")
        
        return result
    
    def _generate_camp_event_v2(self, player: Player, is_pitcher: bool, phase: str) -> Optional[str]:
        """キャンプイベントを生成（フェーズ別）"""
        early_events = [
            "基礎練習に真剣に取り組んでいる",
            "体づくりに励んでいる",
            "コーチと熱心に話し合っている",
            "筋トレで汗を流している",
        ]
        middle_events_pitcher = [
            "新球種の習得に挑戦中！",
            "フォーム改造に取り組む",
            "制球力が安定してきた",
            "球速アップの兆し！",
            "変化球のキレが増した",
            "コーチに絶賛されている",
        ]
        middle_events_batter = [
            "打撃フォームを改良中",
            "パワーヒッティング練習中",
            "選球眼が良くなってきた",
            "足が速くなった",
            "守備の動きが機敏になった",
            "スイングスピードが上がった",
        ]
        late_events = [
            "仕上がりは順調",
            "開幕に向けて調整中",
            "実戦で好結果を残している",
            "レギュラー獲りに意欲",
            "首脳陣の評価が上がっている",
        ]
        
        if phase == "early":
            return random.choice(early_events)
        elif phase == "middle":
            return random.choice(middle_events_pitcher if is_pitcher else middle_events_batter)
        else:
            return random.choice(late_events)
    
    def execute_intrasquad_game(self, team: Team) -> Dict:
        """紅白戦を実行"""
        if not self.spring_camp_state:
            return {}
        
        results = {
            "type": "紅白戦",
            "mvp": None,
            "highlights": [],
            "evaluations": {}
        }
        
        mvp = random.choice(team.players)
        results["mvp"] = mvp.name
        
        if mvp.name not in self.spring_camp_state.mvp_counts:
            self.spring_camp_state.mvp_counts[mvp.name] = 0
        self.spring_camp_state.mvp_counts[mvp.name] += 1
        
        for player in team.players[:12]:
            score = random.randint(1, 5)
            evaluation = ["×", "△", "○", "◎", "☆"][score - 1]
            results["evaluations"][player.name] = evaluation
            
            if score >= 4:
                stat = random.choice(["contact", "power", "speed", "control"])
                self._apply_stat_growth(player, stat, 1)
        
        self.spring_camp_state.intrasquad_games += 1
        self.spring_camp_state.goals["intrasquad"]["current"] += 1
        
        return results
    
    def execute_practice_game(self, team: Team) -> Dict:
        """オープン戦を実行"""
        if not self.spring_camp_state:
            return {}
        
        results = {
            "type": "オープン戦",
            "score": (random.randint(0, 8), random.randint(0, 8)),
            "win": False,
            "highlights": [],
            "evaluations": {}
        }
        
        results["win"] = results["score"][0] > results["score"][1]
        
        for player in team.players[:15]:
            score = random.randint(1, 5)
            evaluation = ["×", "△", "○", "◎", "☆"][score - 1]
            results["evaluations"][player.name] = evaluation
            
            if random.random() < 0.3:
                is_pitcher = player.position == Position.PITCHER
                stat = random.choice(["control", "stamina"] if is_pitcher else ["contact", "power"])
                self._apply_stat_growth(player, stat, 1)
        
        self.spring_camp_state.practice_games += 1
        
        return results
    
    def end_spring_camp(self) -> Dict:
        """春季キャンプ終了処理"""
        if not self.spring_camp_state:
            return {}
        
        camp = self.spring_camp_state
        
        # MVPランキングを計算（成長量から）
        mvp_ranking = []
        if camp.growth_results:
            for name, growth in camp.growth_results.items():
                total_growth = sum(growth.values()) if growth else 0
                mvp_ranking.append((name, total_growth))
            mvp_ranking.sort(key=lambda x: x[1], reverse=True)
        
        summary = {
            "total_days": camp.total_days,
            "growth_results": camp.growth_results,
            "new_skills": camp.new_skills,
            "injuries": camp.injuries,
            "intrasquad_games": camp.intrasquad_games,
            "practice_games": camp.practice_games,
            "goals_achieved": [],  # 新構造ではgoalsなし
            "mvp_ranking": mvp_ranking[:3],
            "total_batting_growth": camp.total_batting_growth,
            "total_pitching_growth": camp.total_pitching_growth,
            "total_fielding_growth": camp.total_fielding_growth,
        }
        
        self.spring_camp_state = None
        return summary
    
    def process_spring_camp(self, team: Team, training_menu: Dict) -> Dict:
        """キャンプ1日分を処理"""
        if training_menu:
            self.set_camp_training_menu(
                batting=training_menu.get("batting", 3),
                pitching=training_menu.get("pitching", 3),
                fielding=training_menu.get("fielding", 3),
                physical=training_menu.get("physical", 3),
                rest=training_menu.get("rest", 3),
                mental=training_menu.get("mental", 3)
            )
        
        return self.advance_camp_day(team)
    
    # ========================================
    # 怪我管理
    # ========================================
    def check_injury(self, player: Player) -> Optional[Injury]:
        """怪我チェック"""
        is_pitcher = player.position == Position.PITCHER
        
        if is_pitcher:
            injury_type = random.choices(
                [InjuryType.ARM, InjuryType.LEG, InjuryType.BACK, InjuryType.GENERAL],
                weights=[50, 20, 20, 10]
            )[0]
        else:
            injury_type = random.choices(
                [InjuryType.ARM, InjuryType.LEG, InjuryType.BACK, InjuryType.GENERAL],
                weights=[15, 45, 25, 15]
            )[0]
        
        severity = random.randint(1, 10)
        days = severity * random.randint(3, 7)
        
        injury = Injury(
            injury_type=injury_type,
            severity=severity,
            days_remaining=days,
            player_name=player.name
        )
        
        self.injuries[id(player)] = injury
        return injury
    
    def heal_injuries(self):
        """怪我回復処理（1日）"""
        healed = []
        for player_id, injury in list(self.injuries.items()):
            if injury.heal_day():
                healed.append(injury.player_name)
                del self.injuries[player_id]
        return healed
    
    # ========================================
    # シーズン処理
    # ========================================
    def start_new_season(self):
        """新シーズン開始"""
        self.current_year += 1
        self.current_phase = PennantPhase.SPRING_CAMP
        
        for team in self.teams:
            for player in team.players:
                player.age += 1
                player.years_pro += 1
        
        self.fa_players.clear()
        self.trade_offers.clear()
        self.draft_pool.clear()
    
    def calculate_season_awards(self) -> List[SeasonAward]:
        """シーズン表彰を計算"""
        awards = []
        
        all_batters = []
        all_pitchers = []
        
        for team in self.teams:
            for player in team.players:
                if player.position == Position.PITCHER:
                    all_pitchers.append((player, team.name))
                else:
                    all_batters.append((player, team.name))
        
        if all_batters:
            best_avg = max(all_batters, key=lambda x: x[0].record.batting_average)
            awards.append(SeasonAward(
                award_name="首位打者",
                player_name=best_avg[0].name,
                team_name=best_avg[1],
                value=best_avg[0].record.batting_average
            ))
        
        if all_batters:
            best_hr = max(all_batters, key=lambda x: x[0].record.home_runs)
            awards.append(SeasonAward(
                award_name="本塁打王",
                player_name=best_hr[0].name,
                team_name=best_hr[1],
                value=best_hr[0].record.home_runs
            ))
        
        if all_pitchers:
            best_era = min(all_pitchers, key=lambda x: x[0].record.era if x[0].record.innings_pitched > 100 else 99)
            awards.append(SeasonAward(
                award_name="最優秀防御率",
                player_name=best_era[0].name,
                team_name=best_era[1],
                value=best_era[0].record.era
            ))
        
        self.awards_history.extend(awards)
        return awards

    # ========================================
    # 疲労管理
    # ========================================
    def add_fatigue(self, player: Player, amount: int):
        """選手の疲労を追加"""
        player_id = id(player)
        current = self.fatigue.get(player_id, 0)
        self.fatigue[player_id] = min(100, current + amount)
    
    def reduce_fatigue(self, player: Player, amount: int):
        """選手の疲労を回復"""
        player_id = id(player)
        current = self.fatigue.get(player_id, 0)
        self.fatigue[player_id] = max(0, current - amount)
    
    def get_fatigue(self, player: Player) -> int:
        """選手の疲労度を取得"""
        return self.fatigue.get(id(player), 0)
    
    def process_daily_fatigue_recovery(self):
        """毎日の疲労自然回復"""
        for player_id in list(self.fatigue.keys()):
            self.fatigue[player_id] = max(0, self.fatigue[player_id] - 5)
    
    def get_player_condition(self, player: Player) -> str:
        """選手のコンディションを取得"""
        fatigue = self.get_fatigue(player)
        if fatigue <= 20:
            return "絶好調"
        elif fatigue <= 40:
            return "好調"
        elif fatigue <= 60:
            return "普通"
        elif fatigue <= 80:
            return "不調"
        else:
            return "絶不調"
