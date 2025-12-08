# -*- coding: utf-8 -*-
"""
日程作成エンジン（完全再現版）
"""
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
import datetime
from collections import defaultdict

from models import Team, League, Schedule, ScheduledGame, GameStatus


class LeagueScheduleEngine:
    """リーグ日程作成エンジン"""

    # 基本設定
    GAMES_PER_SEASON = 143
    INTRA_LEAGUE_GAMES = 25  # 同一リーグ対戦数（5チーム×25試合=125試合）
    INTERLEAGUE_GAMES = 18   # 交流戦（6チーム×3試合=18試合）

    def __init__(self, year: int = 2027):
        self.year = year

        # カレンダー設定
        self.opening_day = datetime.date(year, 3, 29)
        self.interleague_start = datetime.date(year, 5, 30)
        self.interleague_end = datetime.date(year, 6, 16)
        self.allstar_start = datetime.date(year, 7, 19)
        self.allstar_end = datetime.date(year, 7, 22)
        self.season_end = datetime.date(year, 10, 6)

        self.schedule = Schedule()
        self.north_teams = []
        self.south_teams = []

    def generate_schedule(self, north_teams: List[Team],
                         south_teams: List[Team]) -> Schedule:
        """日程を生成"""
        self.north_teams = [t.name for t in north_teams]
        self.south_teams = [t.name for t in south_teams]
        self.all_teams = self.north_teams + self.south_teams

        self.schedule = Schedule()

        # 1. 全試合リストを生成
        all_games = self.generate_all_games()

        # 2. 試合を日程に配置
        self._assign_games_to_dates(all_games)

        return self.schedule

    def generate_all_games(self) -> List[Tuple[str, str, bool]]:
        """全試合を生成（ホーム, アウェイ, 交流戦フラグ）"""
        games = []

        # リーグ内対戦（25試合×5対戦=125試合/チーム）
        for teams in [self.north_teams, self.south_teams]:
            for i, team1 in enumerate(teams):
                for j, team2 in enumerate(teams):
                    if i >= j:
                        continue
                    # 25試合：ホーム12-13試合ずつ
                    home1 = 13 if (i + j) % 2 == 0 else 12
                    home2 = 25 - home1
                    for _ in range(home1):
                        games.append((team1, team2, False))
                    for _ in range(home2):
                        games.append((team2, team1, False))

        # 交流戦（3試合×6対戦=18試合/チーム）
        for n_team in self.north_teams:
            for s_team in self.south_teams:
                # 偶数年：セ主催2試合、パ主催1試合
                if self.year % 2 == 0:
                    games.append((n_team, s_team, True))
                    games.append((n_team, s_team, True))
                    games.append((s_team, n_team, True))
                else:
                    games.append((s_team, n_team, True))
                    games.append((s_team, n_team, True))
                    games.append((n_team, s_team, True))

        return games

    def _assign_games_to_dates(self, all_games: List[Tuple[str, str, bool]]):
        """試合を日程に配置"""
        random.shuffle(all_games)

        game_number = 1

        # ゲーム日リストを作成
        game_dates = []
        d = self.opening_day
        while d <= self.season_end:
            # 月曜は休み
            if d.weekday() != 0:
                # オールスター期間は休み
                if not (self.allstar_start <= d <= self.allstar_end):
                    game_dates.append(d)
            d += datetime.timedelta(days=1)

        # 全試合を日程に配置
        game_number = self._place_games(all_games, game_dates, game_number)

        # 日付順にソート
        self.schedule.games.sort(key=lambda g: (g.date, g.game_number))

        # 試合番号を振り直し
        for i, game in enumerate(self.schedule.games):
            game.game_number = i + 1

    def _place_games(self, games: List[Tuple[str, str, bool]],
                    dates: List[datetime.date], start_number: int) -> int:
        """試合を日程に配置"""
        game_number = start_number
        remaining = list(games)

        for date in dates:
            if not remaining:
                break

            date_str = date.strftime("%Y-%m-%d")
            teams_today: Set[str] = set()
            games_today = 0

            # この日に最大6試合（全12チームが試合）
            idx = 0
            while games_today < 6 and idx < len(remaining):
                home, away, _ = remaining[idx]

                if home not in teams_today and away not in teams_today:
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    teams_today.add(home)
                    teams_today.add(away)
                    game_number += 1
                    games_today += 1
                    remaining.pop(idx)
                else:
                    idx += 1

        # 残りの試合があれば追加の日程に配置
        max_iterations = 50
        iteration = 0
        while remaining and iteration < max_iterations:
            iteration += 1
            placed_any = False

            for date in dates:
                if not remaining:
                    break

                date_str = date.strftime("%Y-%m-%d")
                existing = [g for g in self.schedule.games if g.date == date_str]

                if len(existing) >= 6:
                    continue

                teams_today = set()
                for g in existing:
                    teams_today.add(g.home_team_name)
                    teams_today.add(g.away_team_name)

                idx = 0
                while idx < len(remaining) and len(existing) < 6:
                    home, away, _ = remaining[idx]
                    if home not in teams_today and away not in teams_today:
                        self.schedule.games.append(ScheduledGame(
                            game_number=game_number,
                            date=date_str,
                            home_team_name=home,
                            away_team_name=away
                        ))
                        teams_today.add(home)
                        teams_today.add(away)
                        game_number += 1
                        remaining.pop(idx)
                        existing.append(None)
                        placed_any = True
                    else:
                        idx += 1

            if not placed_any:
                break

        return game_number

    def get_team_schedule(self, team_name: str) -> List[ScheduledGame]:
        """チームの全日程を取得"""
        return [g for g in self.schedule.games
                if g.home_team_name == team_name or g.away_team_name == team_name]

    def get_next_game(self, team_name: str,
                      after_date: str = None) -> Optional[ScheduledGame]:
        """チームの次の試合を取得"""
        for game in self.schedule.games:
            if game.status != GameStatus.SCHEDULED:
                continue
            if after_date and game.date <= after_date:
                continue
            if game.home_team_name == team_name or game.away_team_name == team_name:
                return game
        return None

    def get_games_for_date(self, date_str: str) -> List[ScheduledGame]:
        """指定日の全試合を取得"""
        return [g for g in self.schedule.games if g.date == date_str]

    def is_interleague_period(self, date_str: str) -> bool:
        """交流戦期間かどうか"""
        try:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return self.interleague_start <= d <= self.interleague_end
        except:
            return False

    def get_schedule_stats(self) -> Dict:
        """日程統計を取得"""
        stats = {
            "total_games": len(self.schedule.games),
            "teams": {}
        }

        for team in self.all_teams:
            team_games = self.get_team_schedule(team)
            home = len([g for g in team_games if g.home_team_name == team])
            away = len([g for g in team_games if g.away_team_name == team])

            stats["teams"][team] = {
                "total": len(team_games),
                "home": home,
                "away": away
            }

        return stats

def create_league_schedule(year: int, north_teams: List[Team],
                       south_teams: List[Team]) -> Schedule:
    """リーグ日程を作成するヘルパー関数"""
    engine = LeagueScheduleEngine(year)
    return engine.generate_schedule(north_teams, south_teams)
