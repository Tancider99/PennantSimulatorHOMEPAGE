# -*- coding: utf-8 -*-
"""
詳細な選手成績・記録システム
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json


class RecordType(Enum):
    """記録タイプ"""
    SINGLE_GAME = "試合記録"
    SEASON = "シーズン記録"
    CAREER = "通算記録"
    STREAK = "連続記録"


@dataclass
class SingleGameRecord:
    """単一試合の詳細記録"""
    game_number: int
    date: str
    opponent: str
    is_home: bool
    
    # 打撃
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
    
    # 投球
    innings_pitched: float = 0.0
    hits_allowed: int = 0
    runs_allowed: int = 0
    earned_runs: int = 0
    walks_allowed: int = 0
    strikeouts_pitched: int = 0
    home_runs_allowed: int = 0
    pitch_count: int = 0
    win: bool = False
    loss: bool = False
    save: bool = False
    hold: bool = False
    
    @property
    def batting_average(self) -> float:
        return self.hits / self.at_bats if self.at_bats > 0 else 0.0


@dataclass
class SeasonStats:
    """シーズン成績"""
    year: int
    team_name: str
    
    # 打撃成績
    games_played: int = 0
    at_bats: int = 0
    hits: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    rbis: int = 0
    runs: int = 0
    walks: int = 0
    hit_by_pitch: int = 0
    strikeouts: int = 0
    stolen_bases: int = 0
    caught_stealing: int = 0
    sacrifice_hits: int = 0
    sacrifice_flies: int = 0
    grounded_into_dp: int = 0
    
    # 投球成績
    games_pitched: int = 0
    games_started: int = 0
    complete_games: int = 0
    shutouts: int = 0
    wins: int = 0
    losses: int = 0
    saves: int = 0
    holds: int = 0
    innings_pitched: float = 0.0
    hits_allowed: int = 0
    runs_allowed: int = 0
    earned_runs: int = 0
    walks_allowed: int = 0
    strikeouts_pitched: int = 0
    home_runs_allowed: int = 0
    wild_pitches: int = 0
    balks: int = 0
    
    # 試合ごとの記録
    game_log: List[SingleGameRecord] = field(default_factory=list)
    
    # 各種率
    @property
    def batting_average(self) -> float:
        return self.hits / self.at_bats if self.at_bats > 0 else 0.0
    
    @property
    def on_base_percentage(self) -> float:
        pa = self.at_bats + self.walks + self.hit_by_pitch + self.sacrifice_flies
        if pa == 0:
            return 0.0
        return (self.hits + self.walks + self.hit_by_pitch) / pa
    
    @property
    def slugging_percentage(self) -> float:
        if self.at_bats == 0:
            return 0.0
        total_bases = (self.hits - self.doubles - self.triples - self.home_runs +
                      self.doubles * 2 + self.triples * 3 + self.home_runs * 4)
        return total_bases / self.at_bats
    
    @property
    def ops(self) -> float:
        return self.on_base_percentage + self.slugging_percentage
    
    @property
    def era(self) -> float:
        if self.innings_pitched == 0:
            return 0.0
        return (self.earned_runs * 9) / self.innings_pitched
    
    @property
    def whip(self) -> float:
        if self.innings_pitched == 0:
            return 0.0
        return (self.walks_allowed + self.hits_allowed) / self.innings_pitched
    
    @property
    def k_per_9(self) -> float:
        if self.innings_pitched == 0:
            return 0.0
        return (self.strikeouts_pitched * 9) / self.innings_pitched
    
    @property
    def bb_per_9(self) -> float:
        if self.innings_pitched == 0:
            return 0.0
        return (self.walks_allowed * 9) / self.innings_pitched
    
    @property
    def stolen_base_percentage(self) -> float:
        attempts = self.stolen_bases + self.caught_stealing
        if attempts == 0:
            return 0.0
        return self.stolen_bases / attempts
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "year": self.year,
            "team": self.team_name,
            "batting": {
                "games": self.games_played,
                "ab": self.at_bats,
                "h": self.hits,
                "2b": self.doubles,
                "3b": self.triples,
                "hr": self.home_runs,
                "rbi": self.rbis,
                "r": self.runs,
                "bb": self.walks,
                "so": self.strikeouts,
                "sb": self.stolen_bases,
                "avg": f"{self.batting_average:.3f}",
                "obp": f"{self.on_base_percentage:.3f}",
                "slg": f"{self.slugging_percentage:.3f}",
                "ops": f"{self.ops:.3f}"
            },
            "pitching": {
                "g": self.games_pitched,
                "gs": self.games_started,
                "w": self.wins,
                "l": self.losses,
                "sv": self.saves,
                "hld": self.holds,
                "ip": f"{self.innings_pitched:.1f}",
                "h": self.hits_allowed,
                "er": self.earned_runs,
                "bb": self.walks_allowed,
                "so": self.strikeouts_pitched,
                "era": f"{self.era:.2f}",
                "whip": f"{self.whip:.2f}"
            }
        }


@dataclass
class CareerStats:
    """通算成績"""
    player_name: str
    seasons: List[SeasonStats] = field(default_factory=list)
    
    def add_season(self, season: SeasonStats):
        self.seasons.append(season)
    
    @property
    def total_games(self) -> int:
        return sum(s.games_played for s in self.seasons)
    
    @property
    def total_at_bats(self) -> int:
        return sum(s.at_bats for s in self.seasons)
    
    @property
    def total_hits(self) -> int:
        return sum(s.hits for s in self.seasons)
    
    @property
    def total_home_runs(self) -> int:
        return sum(s.home_runs for s in self.seasons)
    
    @property
    def total_rbis(self) -> int:
        return sum(s.rbis for s in self.seasons)
    
    @property
    def total_wins(self) -> int:
        return sum(s.wins for s in self.seasons)
    
    @property
    def total_saves(self) -> int:
        return sum(s.saves for s in self.seasons)
    
    @property
    def total_strikeouts_pitched(self) -> int:
        return sum(s.strikeouts_pitched for s in self.seasons)
    
    @property
    def career_batting_average(self) -> float:
        total_ab = self.total_at_bats
        if total_ab == 0:
            return 0.0
        return self.total_hits / total_ab
    
    @property
    def career_era(self) -> float:
        total_ip = sum(s.innings_pitched for s in self.seasons)
        total_er = sum(s.earned_runs for s in self.seasons)
        if total_ip == 0:
            return 0.0
        return (total_er * 9) / total_ip


@dataclass
class HistoricalRecord:
    """歴代記録"""
    category: str
    record_type: RecordType
    value: float
    holder: str
    team: str
    year: int
    description: str = ""


class RecordBook:
    """記録帳"""
    
    def __init__(self):
        self.records: Dict[str, HistoricalRecord] = {}
        self._initialize_default_records()
    
    def _initialize_default_records(self):
        """デフォルトの歴代記録を初期化"""
        # シーズン打撃記録
        self.records["season_batting_avg"] = HistoricalRecord(
            "シーズン最高打率", RecordType.SEASON, 0.389,
            "イチロー", "オリックス", 2000, "2000年South League"
        )
        self.records["season_home_runs"] = HistoricalRecord(
            "シーズン最多本塁打", RecordType.SEASON, 60,
            "王貞治", "巨人", 1964, "世界記録を更新"
        )
        self.records["season_rbis"] = HistoricalRecord(
            "シーズン最多打点", RecordType.SEASON, 160,
            "小鶴誠", "松竹", 1950
        )
        self.records["season_hits"] = HistoricalRecord(
            "シーズン最多安打", RecordType.SEASON, 210,
            "西岡剛", "ロッテ", 2010
        )
        self.records["season_stolen_bases"] = HistoricalRecord(
            "シーズン最多盗塁", RecordType.SEASON, 106,
            "福本豊", "阪急", 1972, "世界記録"
        )
        
        # シーズン投手記録
        self.records["season_wins"] = HistoricalRecord(
            "シーズン最多勝", RecordType.SEASON, 42,
            "稲尾和久", "西鉄", 1961, "鉄腕"
        )
        self.records["season_saves"] = HistoricalRecord(
            "シーズン最多セーブ", RecordType.SEASON, 46,
            "岩瀬仁紀", "中日", 2005
        )
        self.records["season_era"] = HistoricalRecord(
            "シーズン最優秀防御率", RecordType.SEASON, 0.73,
            "藤本英雄", "巨人", 1943
        )
        self.records["season_strikeouts"] = HistoricalRecord(
            "シーズン最多奪三振", RecordType.SEASON, 401,
            "野茂英雄", "近鉄", 1990
        )
        
        # 通算記録
        self.records["career_home_runs"] = HistoricalRecord(
            "通算最多本塁打", RecordType.CAREER, 868,
            "王貞治", "巨人", 1980, "世界記録"
        )
        self.records["career_hits"] = HistoricalRecord(
            "通算最多安打", RecordType.CAREER, 3085,
            "張本勲", "日本ハム他", 1981
        )
        self.records["career_wins"] = HistoricalRecord(
            "通算最多勝", RecordType.CAREER, 400,
            "金田正一", "国鉄/巨人", 1969
        )
        self.records["career_saves"] = HistoricalRecord(
            "通算最多セーブ", RecordType.CAREER, 407,
            "岩瀬仁紀", "中日", 2018
        )
        self.records["career_strikeouts"] = HistoricalRecord(
            "通算最多奪三振", RecordType.CAREER, 4490,
            "金田正一", "国鉄/巨人", 1969
        )
    
    def check_new_record(self, category: str, value: float, 
                        holder: str, team: str, year: int) -> Optional[HistoricalRecord]:
        """新記録かチェック"""
        if category not in self.records:
            return None
        
        current_record = self.records[category]
        
        # カテゴリによって比較方法を変える
        is_new_record = False
        if category in ["season_era"]:  # 低い方が良い記録
            is_new_record = value < current_record.value
        else:  # 高い方が良い記録
            is_new_record = value > current_record.value
        
        if is_new_record:
            new_record = HistoricalRecord(
                category=current_record.category,
                record_type=current_record.record_type,
                value=value,
                holder=holder,
                team=team,
                year=year,
                description=f"前記録: {current_record.holder} ({current_record.value})"
            )
            self.records[category] = new_record
            return new_record
        
        return None
    
    def get_record(self, category: str) -> Optional[HistoricalRecord]:
        return self.records.get(category)
    
    def get_all_records(self) -> List[HistoricalRecord]:
        return list(self.records.values())


@dataclass
class Streak:
    """連続記録"""
    streak_type: str
    current_count: int
    record_count: int
    record_holder: str
    is_active: bool = True
    start_date: str = ""
    end_date: str = ""


class StreakTracker:
    """連続記録追跡"""
    
    def __init__(self):
        self.active_streaks: Dict[str, Streak] = {}
        self.historical_streaks: List[Streak] = []
        
        # 歴代記録
        self.records = {
            "hitting_streak": Streak("連続試合安打", 0, 33, "高橋慶彦"),
            "games_played": Streak("連続試合出場", 0, 2215, "衣笠祥雄"),
            "consecutive_wins": Streak("連勝", 0, 28, "田中将大"),
            "save_opportunities": Streak("連続セーブ成功", 0, 65, "藤川球児"),
            "scoreless_innings": Streak("連続無失点イニング", 0, 50.0, "藤本英雄"),
        }
    
    def update_hitting_streak(self, player_name: str, had_hit: bool):
        """打撃連続記録を更新"""
        key = f"hitting_streak_{player_name}"
        
        if key not in self.active_streaks:
            self.active_streaks[key] = Streak("連続試合安打", 0, 0, player_name)
        
        streak = self.active_streaks[key]
        
        if had_hit:
            streak.current_count += 1
            if streak.current_count > streak.record_count:
                streak.record_count = streak.current_count
        else:
            if streak.is_active and streak.current_count > 0:
                self.historical_streaks.append(
                    Streak(streak.streak_type, 0, streak.current_count, player_name, False)
                )
            streak.current_count = 0
    
    def check_record(self, streak_type: str, current: int) -> bool:
        """記録更新かチェック"""
        if streak_type in self.records:
            return current > self.records[streak_type].record_count
        return False
    
    def get_top_active_streaks(self, streak_type: str, count: int = 5) -> List[Streak]:
        """現在進行中の上位連続記録を取得"""
        relevant = [s for key, s in self.active_streaks.items() 
                   if streak_type in key and s.current_count > 0]
        relevant.sort(key=lambda s: s.current_count, reverse=True)
        return relevant[:count]


@dataclass
class MilestoneAchievement:
    """マイルストーン達成"""
    player_name: str
    milestone_type: str
    value: int
    date: str
    game_number: int
    description: str


class MilestoneTracker:
    """マイルストーン追跡"""
    
    BATTING_MILESTONES = [100, 500, 1000, 1500, 2000, 2500, 3000]  # 安打
    HOME_RUN_MILESTONES = [100, 200, 300, 400, 500]
    RBI_MILESTONES = [500, 1000, 1500, 2000]
    WIN_MILESTONES = [50, 100, 150, 200, 250]
    SAVE_MILESTONES = [100, 200, 300, 400]
    STRIKEOUT_MILESTONES = [500, 1000, 1500, 2000, 2500, 3000]
    
    def __init__(self):
        self.achievements: List[MilestoneAchievement] = []
        self.pending_milestones: Dict[str, int] = {}  # player -> next milestone
    
    def check_hitting_milestone(self, player_name: str, total_hits: int,
                                date: str, game_num: int) -> Optional[MilestoneAchievement]:
        """安打マイルストーンをチェック"""
        for milestone in self.BATTING_MILESTONES:
            if total_hits >= milestone:
                key = f"{player_name}_hits_{milestone}"
                if key not in [a.player_name + "_hits_" + str(a.value) for a in self.achievements]:
                    achievement = MilestoneAchievement(
                        player_name=player_name,
                        milestone_type="通算安打",
                        value=milestone,
                        date=date,
                        game_number=game_num,
                        description=f"{player_name}が通算{milestone}安打達成！"
                    )
                    self.achievements.append(achievement)
                    return achievement
        return None
    
    def check_home_run_milestone(self, player_name: str, total_hr: int,
                                 date: str, game_num: int) -> Optional[MilestoneAchievement]:
        """本塁打マイルストーンをチェック"""
        for milestone in self.HOME_RUN_MILESTONES:
            if total_hr >= milestone:
                key = f"{player_name}_hr_{milestone}"
                if key not in [a.player_name + "_hr_" + str(a.value) for a in self.achievements]:
                    achievement = MilestoneAchievement(
                        player_name=player_name,
                        milestone_type="通算本塁打",
                        value=milestone,
                        date=date,
                        game_number=game_num,
                        description=f"{player_name}が通算{milestone}本塁打達成！"
                    )
                    self.achievements.append(achievement)
                    return achievement
        return None
    
    def check_win_milestone(self, player_name: str, total_wins: int,
                           date: str, game_num: int) -> Optional[MilestoneAchievement]:
        """勝利マイルストーンをチェック"""
        for milestone in self.WIN_MILESTONES:
            if total_wins >= milestone:
                key = f"{player_name}_wins_{milestone}"
                existing_keys = [f"{a.player_name}_wins_{a.value}" for a in self.achievements 
                               if a.milestone_type == "通算勝利"]
                if key not in existing_keys:
                    achievement = MilestoneAchievement(
                        player_name=player_name,
                        milestone_type="通算勝利",
                        value=milestone,
                        date=date,
                        game_number=game_num,
                        description=f"{player_name}が通算{milestone}勝達成！"
                    )
                    self.achievements.append(achievement)
                    return achievement
        return None
    
    def get_recent_achievements(self, count: int = 10) -> List[MilestoneAchievement]:
        """最近のマイルストーン達成を取得"""
        return sorted(self.achievements, key=lambda a: a.game_number, reverse=True)[:count]


class StatsFormatter:
    """成績フォーマッター"""
    
    @staticmethod
    def format_batting_line(stats: SeasonStats) -> str:
        """打撃成績1行表示"""
        return (f"{stats.games_played}試合 打率.{int(stats.batting_average*1000):03d} "
                f"{stats.home_runs}本 {stats.rbis}打点 "
                f"OPS.{int(stats.ops*1000):03d}")
    
    @staticmethod
    def format_pitching_line(stats: SeasonStats) -> str:
        """投手成績1行表示"""
        return (f"{stats.games_pitched}試合 {stats.wins}勝{stats.losses}敗{stats.saves}S "
                f"防御率{stats.era:.2f} {stats.strikeouts_pitched}奪三振")
    
    @staticmethod
    def format_batting_detailed(stats: SeasonStats) -> List[str]:
        """打撃成績詳細表示"""
        lines = [
            f"試合: {stats.games_played}  打席: {stats.at_bats + stats.walks + stats.hit_by_pitch}",
            f"打数: {stats.at_bats}  安打: {stats.hits}  打率: .{int(stats.batting_average*1000):03d}",
            f"二塁打: {stats.doubles}  三塁打: {stats.triples}  本塁打: {stats.home_runs}",
            f"打点: {stats.rbis}  得点: {stats.runs}  盗塁: {stats.stolen_bases}",
            f"四球: {stats.walks}  三振: {stats.strikeouts}",
            f"出塁率: .{int(stats.on_base_percentage*1000):03d}  "
            f"長打率: .{int(stats.slugging_percentage*1000):03d}  "
            f"OPS: .{int(stats.ops*1000):03d}"
        ]
        return lines
    
    @staticmethod
    def format_pitching_detailed(stats: SeasonStats) -> List[str]:
        """投手成績詳細表示"""
        lines = [
            f"登板: {stats.games_pitched}  先発: {stats.games_started}  "
            f"完投: {stats.complete_games}  完封: {stats.shutouts}",
            f"勝利: {stats.wins}  敗戦: {stats.losses}  "
            f"セーブ: {stats.saves}  ホールド: {stats.holds}",
            f"投球回: {stats.innings_pitched:.1f}  被安打: {stats.hits_allowed}",
            f"自責点: {stats.earned_runs}  防御率: {stats.era:.2f}",
            f"奪三振: {stats.strikeouts_pitched}  与四球: {stats.walks_allowed}",
            f"WHIP: {stats.whip:.2f}  K/9: {stats.k_per_9:.2f}  BB/9: {stats.bb_per_9:.2f}"
        ]
        return lines
