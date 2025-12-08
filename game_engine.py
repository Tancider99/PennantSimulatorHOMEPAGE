# -*- coding: utf-8 -*-
"""
NPB試合シミュレーションエンジン (修正版)
"""
import random
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum

from at_bat_engine import (
    AtBatSimulator, AtBatResult, AtBatContext, DefenseData,
    get_at_bat_simulator
)
from models import Position, Player # モデルインポート

# ========================================
# 列挙型
# ========================================

class GamePhase(Enum):
    NOT_STARTED = "開始前"
    IN_PROGRESS = "試合中"
    COMPLETED = "終了"

class InningHalf(Enum):
    TOP = "表"
    BOTTOM = "裏"

class BaseRunner:
    def __init__(self, player_idx: int = -1, speed: int = 50, baserunning: int = 50):
        self.player_idx = player_idx
        self.speed = speed
        self.baserunning = baserunning # 走塁技術を追加

    def is_occupied(self) -> bool:
        return self.player_idx >= 0

    def clear(self):
        self.player_idx = -1
        self.speed = 50
        self.baserunning = 50

# ========================================
# データクラス
# ========================================

@dataclass
class GameState:
    inning: int = 1
    half: InningHalf = InningHalf.TOP
    outs: int = 0
    runners: List[BaseRunner] = field(default_factory=lambda: [BaseRunner(), BaseRunner(), BaseRunner()])
    home_score: int = 0
    away_score: int = 0
    phase: GamePhase = GamePhase.NOT_STARTED
    home_batter_idx: int = 0
    away_batter_idx: int = 0
    home_pitcher_idx: int = -1
    away_pitcher_idx: int = -1
    home_pitch_count: int = 0
    away_pitch_count: int = 0

    def get_batting_team(self) -> str:
        return "away" if self.half == InningHalf.TOP else "home"

    def get_pitching_team(self) -> str:
        return "home" if self.half == InningHalf.TOP else "away"
        
    def clear_bases(self):
        for runner in self.runners:
            runner.clear()

@dataclass
class PlayerGameStats:
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
    innings_pitched: float = 0.0
    pitch_count: int = 0
    hits_allowed: int = 0
    runs_allowed: int = 0
    earned_runs: int = 0
    walks_allowed: int = 0
    strikeouts_pitched: int = 0
    home_runs_allowed: int = 0

@dataclass
class InningScore:
    inning: int
    half: InningHalf
    runs: int
    hits: int
    errors: int = 0

# ========================================
# 試合エンジン
# ========================================

class GameEngine:
    def __init__(self, home_team, away_team, use_dh: bool = True):
        self.home_team = home_team
        self.away_team = away_team
        self.use_dh = use_dh
        self.state = GameState()
        self.at_bat_sim = get_at_bat_simulator()
        self.home_player_stats: Dict[int, PlayerGameStats] = {}
        self.away_player_stats: Dict[int, PlayerGameStats] = {}
        self.inning_scores: List[InningScore] = []
        self.play_log: List[str] = []
        self.max_innings = 9
        self.max_extra_innings = 12
        self._init_game()

    def _init_game(self):
        if self.home_team.starting_pitcher_idx >= 0:
            self.state.home_pitcher_idx = self.home_team.starting_pitcher_idx
        else:
            self.state.home_pitcher_idx = 0
            
        if self.away_team.starting_pitcher_idx >= 0:
            self.state.away_pitcher_idx = self.away_team.starting_pitcher_idx
        else:
            self.state.away_pitcher_idx = 0

    def get_current_batter(self):
        if self.state.half == InningHalf.TOP:
            team = self.away_team
            idx = self.state.away_batter_idx
        else:
            team = self.home_team
            idx = self.state.home_batter_idx
            
        lineup_idx = idx % 9
        player_idx = team.current_lineup[lineup_idx] if team.current_lineup else lineup_idx
        return team.players[player_idx], player_idx

    def get_current_pitcher(self):
        if self.state.half == InningHalf.TOP:
            team = self.home_team
            idx = self.state.home_pitcher_idx
        else:
            team = self.away_team
            idx = self.state.away_pitcher_idx
        return team.players[idx], idx

    def get_defense_data(self) -> DefenseData:
        """守備データを作成 (新 stats 対応)"""
        if self.state.half == InningHalf.TOP:
            team = self.home_team
        else:
            team = self.away_team

        ranges = {}
        arms = {}
        errors = {}
        catcher_lead = 50
        turn_dp = 50
        
        for player in team.players:
            # 守備適正(defense_ranges)をすべて反映
            if hasattr(player.stats, 'defense_ranges'):
                for pos, val in player.stats.defense_ranges.items():
                    if val > ranges.get(pos, 0):
                        ranges[pos] = val
                        arms[pos] = getattr(player.stats, 'arm', 50)
                        errors[pos] = getattr(player.stats, 'error', 50)
            
            # 個別スキル
            if player.position == Position.CATCHER:
                catcher_lead = getattr(player.stats, 'catcher_lead', 50)
            
            if player.position in [Position.SECOND, Position.SHORTSTOP]:
                turn_dp = max(turn_dp, getattr(player.stats, 'turn_dp', 50))

        return DefenseData(ranges, arms, errors, catcher_lead, turn_dp)

    def simulate_at_bat(self) -> Tuple[AtBatResult, int, Dict]:
        batter, batter_idx = self.get_current_batter()
        pitcher, pitcher_idx = self.get_current_pitcher()

        context = AtBatContext(
            outs=self.state.outs,
            runners=[r.is_occupied() for r in self.state.runners],
            inning=self.state.inning,
            is_top=(self.state.half == InningHalf.TOP),
            score_diff=self._get_score_diff()
        )

        defense = self.get_defense_data()
        
        # 投手の持ち球
        pitch_list = ["ストレート"]
        if hasattr(pitcher.stats, 'pitches'):
            pitch_list.extend(pitcher.stats.pitches.keys())

        result, data = self.at_bat_sim.simulate_at_bat(
            batter.stats, pitcher.stats, defense, context, pitch_list
        )
        
        rbis = self._process_at_bat_result(result, batter, batter_idx, defense)
        self._add_play_log(batter, result, rbis)
        
        return result, rbis, data

    def _process_at_bat_result(self, result: AtBatResult, batter, batter_idx, defense: DefenseData) -> int:
        """結果処理 (走塁判定に baserunning と arm を使用)"""
        rbis = 0
        
        stats = batter.stats
        speed = getattr(stats, 'speed', 50)
        baserunning = getattr(stats, 'baserunning', 50)
        
        if result == AtBatResult.WALK or result == AtBatResult.HIT_BY_PITCH:
            rbis = self._advance_runners_forced(batter_idx, speed, baserunning)
        elif result == AtBatResult.HOME_RUN:
            rbis = self._process_home_run(batter_idx)
        elif result == AtBatResult.SINGLE:
            # 外野手の肩 vs 走塁
            outfield_arm = defense.get_arm(Position.OUTFIELD) # 簡易的に外野代表
            rbis = self._advance_runners_single(batter_idx, speed, baserunning, outfield_arm)
        elif result == AtBatResult.DOUBLE:
            outfield_arm = defense.get_arm(Position.OUTFIELD)
            rbis = self._advance_runners_double(batter_idx, speed, baserunning, outfield_arm)
        elif result == AtBatResult.TRIPLE:
            rbis = self._process_triple(batter_idx, speed, baserunning)
        elif result == AtBatResult.GROUNDOUT:
            self.state.outs += 1
            rbis = self._advance_runners_groundout()
        elif result == AtBatResult.FLYOUT:
            self.state.outs += 1
            outfield_arm = defense.get_arm(Position.OUTFIELD)
            rbis = self._check_sacrifice_fly(baserunning, outfield_arm)
        elif result == AtBatResult.DOUBLE_PLAY:
            self.state.outs += 2
            rbis = 0 # 併殺で得点は稀
            self.state.runners[0].clear()
            self.state.runners[1].clear() # 2塁ランナーが進むケースもあるが簡易化
        elif result == AtBatResult.STRIKEOUT:
            self.state.outs += 1
        elif result == AtBatResult.ERROR:
            rbis = self._advance_runners_single(batter_idx, speed, baserunning, 40) # 弱い肩扱い

        self._advance_batting_order()
        return rbis

    def _advance_runners_single(self, batter_idx, speed, baserunning, arm) -> int:
        rbis = 0
        # 3塁 -> 生還
        if self.state.runners[2].is_occupied():
            rbis += 1
            self.state.runners[2].clear()
            
        # 2塁 -> 生還判定 (Baserunning vs Arm)
        if self.state.runners[1].is_occupied():
            runner = self.state.runners[1]
            chance = 0.5 + (runner.baserunning - arm) * 0.01 + (runner.speed - 50) * 0.005
            if random.random() < chance:
                rbis += 1
                self.state.runners[1].clear()
            else:
                self.state.runners[2] = self.state.runners[1]
                self.state.runners[1].clear()
                
        # 1塁 -> 3塁判定
        if self.state.runners[0].is_occupied():
            runner = self.state.runners[0]
            chance = 0.3 + (runner.baserunning - arm) * 0.01
            if random.random() < chance:
                self.state.runners[2] = self.state.runners[0]
                self.state.runners[0].clear()
            else:
                self.state.runners[1] = self.state.runners[0]
                self.state.runners[0].clear()
                
        self.state.runners[0] = BaseRunner(batter_idx, speed, baserunning)
        return rbis

    def _advance_runners_double(self, batter_idx, speed, baserunning, arm) -> int:
        rbis = 0
        if self.state.runners[2].is_occupied(): rbis += 1; self.state.runners[2].clear()
        if self.state.runners[1].is_occupied(): rbis += 1; self.state.runners[1].clear()
        
        # 1塁 -> 生還判定
        if self.state.runners[0].is_occupied():
            runner = self.state.runners[0]
            chance = 0.4 + (runner.baserunning - arm) * 0.01
            if random.random() < chance:
                rbis += 1
                self.state.runners[0].clear()
            else:
                self.state.runners[2] = self.state.runners[0]
                self.state.runners[0].clear()
                
        self.state.runners[1] = BaseRunner(batter_idx, speed, baserunning)
        return rbis

    def _check_sacrifice_fly(self, baserunning, arm) -> int:
        if self.state.runners[2].is_occupied() and self.state.outs < 3:
            runner = self.state.runners[2]
            # 犠飛成功率
            chance = 0.7 + (runner.baserunning - arm) * 0.01 + (runner.speed - 50) * 0.005
            if random.random() < chance:
                self.state.runners[2].clear()
                return 1
        return 0

    def _advance_runners_forced(self, batter_idx, speed, baserunning) -> int:
        # 四死球（押し出し処理）
        rbis = 0
        if self.state.runners[0].is_occupied():
            if self.state.runners[1].is_occupied():
                if self.state.runners[2].is_occupied():
                    rbis = 1 # 押し出し
                self.state.runners[2] = self.state.runners[1]
            self.state.runners[1] = self.state.runners[0]
        self.state.runners[0] = BaseRunner(batter_idx, speed, baserunning)
        return rbis

    def _process_home_run(self, batter_idx):
        rbis = 1
        for r in self.state.runners:
            if r.is_occupied(): rbis += 1
        self.state.clear_bases()
        return rbis

    def _process_triple(self, batter_idx, speed, baserunning):
        rbis = 0
        for r in self.state.runners:
            if r.is_occupied(): rbis += 1
        self.state.clear_bases()
        self.state.runners[2] = BaseRunner(batter_idx, speed, baserunning)
        return rbis

    def _advance_runners_groundout(self):
        # 進塁打判定など (簡易)
        rbis = 0
        if self.state.runners[2].is_occupied() and self.state.outs < 3:
            # 3塁ランナー生還 (ギャンブル要素なしの簡易版)
            rbis += 1
            self.state.runners[2].clear()
        
        if self.state.runners[1].is_occupied():
            self.state.runners[2] = self.state.runners[1]
            self.state.runners[1].clear()
            
        if self.state.runners[0].is_occupied() and self.state.outs < 3:
            self.state.runners[1] = self.state.runners[0]
            self.state.runners[0].clear()
        return rbis

    def _get_score_diff(self):
        if self.state.half == InningHalf.TOP:
            return self.state.away_score - self.state.home_score
        return self.state.home_score - self.state.away_score

    def _advance_batting_order(self):
        if self.state.half == InningHalf.TOP:
            self.state.away_batter_idx = (self.state.away_batter_idx + 1) % 9
        else:
            self.state.home_batter_idx = (self.state.home_batter_idx + 1) % 9

    def _add_play_log(self, batter, result, rbis):
        self.play_log.append(f"{batter.name}: {result.value} ({rbis}点)")

    def simulate_half_inning(self) -> Tuple[int, int]:
        runs = 0
        hits = 0
        self.state.outs = 0
        self.state.clear_bases()

        while self.state.outs < 3:
            result, rbis, data = self.simulate_at_bat()
            runs += rbis
            if result in [AtBatResult.SINGLE, AtBatResult.DOUBLE, AtBatResult.TRIPLE,
                         AtBatResult.HOME_RUN, AtBatResult.INFIELD_HIT]:
                hits += 1
            
            if (self.state.half == InningHalf.BOTTOM and
                self.state.inning >= self.max_innings and
                self.state.home_score > self.state.away_score):
                break
        return runs, hits

    def simulate_inning(self) -> Dict:
        inning_data = {
            'inning': self.state.inning,
            'top': {'runs': 0, 'hits': 0},
            'bottom': {'runs': 0, 'hits': 0}
        }
        self.state.half = InningHalf.TOP
        runs, hits = self.simulate_half_inning()
        self.state.away_score += runs
        inning_data['top']['runs'] = runs
        inning_data['top']['hits'] = hits
        self.inning_scores.append(InningScore(self.state.inning, InningHalf.TOP, runs, hits))

        if (self.state.inning >= self.max_innings and self.state.home_score > self.state.away_score):
            inning_data['bottom'] = None
            return inning_data

        self.state.half = InningHalf.BOTTOM
        runs, hits = self.simulate_half_inning()
        self.state.home_score += runs
        inning_data['bottom']['runs'] = runs
        inning_data['bottom']['hits'] = hits
        self.inning_scores.append(InningScore(self.state.inning, InningHalf.BOTTOM, runs, hits))
        return inning_data

    def simulate_game(self) -> Dict:
        self.state.phase = GamePhase.IN_PROGRESS
        for inning in range(1, self.max_innings + 1):
            self.state.inning = inning
            self.simulate_inning()
            
        while (self.state.home_score == self.state.away_score and self.state.inning < self.max_extra_innings):
            self.state.inning += 1
            self.simulate_inning()
            
        self.state.phase = GamePhase.COMPLETED
        return self._create_game_result()

    def _create_game_result(self) -> Dict:
        # 結果データ作成 (省略)
        return {
            'home_team': self.home_team.name,
            'away_team': self.away_team.name,
            'home_score': self.state.home_score,
            'away_score': self.state.away_score,
            'play_log': self.play_log
        }