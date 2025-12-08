# -*- coding: utf-8 -*-
"""
二軍・三軍試合シミュレーター (本格版: LiveGameEngine使用)
"""
import random
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from models import Team, Player, Position, TeamLevel
from live_game_engine import LiveGameEngine, GameState

@dataclass
class FarmGameResult:
    team_level: TeamLevel
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    date: str

class FarmGameSimulator:
    """LiveGameEngineを使用した二軍・三軍試合シミュレーター"""

    def __init__(self, home_team: Team, away_team: Team, team_level: TeamLevel = TeamLevel.SECOND):
        self.home_team = home_team
        self.away_team = away_team
        self.team_level = team_level
        # 本格シミュレーションエンジンを使用
        self.engine = LiveGameEngine(home_team, away_team, team_level)

    def simulate_game(self, date: str = "") -> FarmGameResult:
        """1試合を完全にシミュレート"""
        
        # 試合実行
        while not self.engine.is_game_over():
            self.engine.simulate_pitch()
            
        # 成績反映 (LiveGameEngine内で finalize_game_stats を呼び出すことで正しいレコードに加算される)
        self.engine.finalize_game_stats()
        
        return FarmGameResult(
            team_level=self.team_level,
            home_team_name=self.home_team.name,
            away_team_name=self.away_team.name,
            home_score=self.engine.state.home_score,
            away_score=self.engine.state.away_score,
            date=date
        )

class FarmLeagueManager:
    def __init__(self, teams: List[Team]):
        self.teams = teams

    def simulate_farm_games(self, date: str, exclude_team: Optional[str] = None) -> List[FarmGameResult]:
        results = []
        # 二軍戦
        results.extend(self._simulate_level_games(TeamLevel.SECOND, date, exclude_team))
        # 三軍戦
        results.extend(self._simulate_level_games(TeamLevel.THIRD, date, exclude_team))
        return results

    def _simulate_level_games(self, level: TeamLevel, date: str, exclude_team: str) -> List[FarmGameResult]:
        results = []
        target_teams = [t for t in self.teams if t.name != exclude_team]
        random.shuffle(target_teams)

        for i in range(0, len(target_teams) - 1, 2):
            home = target_teams[i]
            away = target_teams[i+1]
            
            # オーダー自動生成 (念のため)
            self._check_and_fix_lineup(home, level)
            self._check_and_fix_lineup(away, level)
            
            sim = FarmGameSimulator(home, away, level)
            res = sim.simulate_game(date)
            results.append(res)
        
        return results

    def _check_and_fix_lineup(self, team: Team, level: TeamLevel):
        lineup = team.farm_lineup if level == TeamLevel.SECOND else team.third_lineup
        if not lineup or len(lineup) < 9:
            # 簡易生成
            roster = team.get_players_by_level(level)
            indices = [team.players.index(p) for p in roster if p.position != Position.PITCHER]
            indices.sort(key=lambda i: team.players[i].stats.overall_batting(), reverse=True)
            new_lineup = indices[:9]
            if level == TeamLevel.SECOND: team.farm_lineup = new_lineup
            else: team.third_lineup = new_lineup

def simulate_farm_games_for_day(teams: List[Team], date: str, player_team_name: str = None):
    """その日の二軍・三軍戦をまとめてシミュレート"""
    manager = FarmLeagueManager(teams)
    manager.simulate_farm_games(date, exclude_team=None)