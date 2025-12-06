# -*- coding: utf-8 -*-
"""
NPB準拠スケジュール管理システム
- 143試合制（同一リーグ25試合×5チーム=125試合、交流戦18試合）
- 3連戦を基本とし、月曜日休み
- オールスター休み（7月中旬）
- 交流戦期間（5月末〜6月中旬）
"""
import random
from typing import List, Optional, Tuple
from models import Schedule, ScheduledGame, Team, GameStatus, League
import datetime


class ScheduleManager:
    """NPB準拠シーズンスケジュール管理クラス"""
    
    def __init__(self, year: int = 2027):
        self.year = year
        self.schedule = Schedule()
        
        # NPB日程設定
        self.opening_day = datetime.date(year, 3, 29)  # 開幕日
        self.interleague_start = datetime.date(year, 5, 28)  # 交流戦開始
        self.interleague_end = datetime.date(year, 6, 16)  # 交流戦終了
        self.allstar_break_start = datetime.date(year, 7, 19)  # オールスター休み開始
        self.allstar_break_end = datetime.date(year, 7, 22)  # オールスター休み終了
        self.season_end = datetime.date(year, 10, 6)  # シーズン終了
    
    def generate_season_schedule(self, central_teams: List[Team], pacific_teams: List[Team]) -> Schedule:
        """NPB準拠のシーズンスケジュールを生成（143試合制）"""
        self.schedule = Schedule()
        
        # 各リーグのカードリストを生成
        central_cards = self._generate_league_matchups(central_teams, 25)  # 同一リーグ25試合
        pacific_cards = self._generate_league_matchups(pacific_teams, 25)
        
        # 交流戦カードを生成
        interleague_cards = self._generate_interleague_matchups(central_teams, pacific_teams, 3)  # 各3試合
        
        # 日程に振り分け
        self._schedule_games(central_cards, pacific_cards, interleague_cards)
        
        return self.schedule
    
    def _generate_league_matchups(self, teams: List[Team], games_per_opponent: int) -> List[Tuple[str, str]]:
        """リーグ内対戦カードを生成（3連戦単位）"""
        matchups = []
        
        for i, team1 in enumerate(teams):
            for j, team2 in enumerate(teams):
                if i < j:
                    # ホーム/アウェイ各チーム半分ずつ（端数は調整）
                    home_series = games_per_opponent // 6  # 3連戦の数
                    away_series = games_per_opponent // 6
                    extra_games = games_per_opponent % 6  # 余り試合
                    
                    # 3連戦でホームゲーム
                    for _ in range(home_series):
                        for _ in range(3):
                            matchups.append((team1.name, team2.name))
                    
                    # 3連戦でアウェイゲーム
                    for _ in range(away_series):
                        for _ in range(3):
                            matchups.append((team2.name, team1.name))
                    
                    # 余り試合を追加
                    for k in range(extra_games):
                        if k < extra_games // 2:
                            matchups.append((team1.name, team2.name))
                        else:
                            matchups.append((team2.name, team1.name))
        
        return matchups
    
    def _generate_interleague_matchups(self, central_teams: List[Team], pacific_teams: List[Team],
                                        games_per_matchup: int) -> List[Tuple[str, str]]:
        """交流戦カードを生成"""
        matchups = []
        
        for c_team in central_teams:
            for p_team in pacific_teams:
                # 3試合対戦（2試合ホーム、1試合アウェイを交互）
                for i in range(games_per_matchup):
                    if i < 2:
                        # 偶数年はセ主催2試合、奇数年はパ主催2試合
                        if self.year % 2 == 0:
                            matchups.append((c_team.name, p_team.name))
                        else:
                            matchups.append((p_team.name, c_team.name))
                    else:
                        if self.year % 2 == 0:
                            matchups.append((p_team.name, c_team.name))
                        else:
                            matchups.append((c_team.name, p_team.name))
        
        return matchups
    
    def _schedule_games(self, central_cards: List[Tuple[str, str]], 
                        pacific_cards: List[Tuple[str, str]],
                        interleague_cards: List[Tuple[str, str]]):
        """カードを日程に振り分け"""
        
        # 各リーグのカードをシャッフル
        random.shuffle(central_cards)
        random.shuffle(pacific_cards)
        random.shuffle(interleague_cards)
        
        current_date = self.opening_day
        game_number = 1
        
        # 開幕〜交流戦前（リーグ戦前半）
        central_idx = 0
        pacific_idx = 0
        
        while current_date < self.interleague_start:
            # 月曜日は休み
            if current_date.weekday() == 0:
                current_date += datetime.timedelta(days=1)
                continue
            
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 1日3試合（各リーグ3試合）
            for _ in range(3):
                if central_idx < len(central_cards):
                    home, away = central_cards[central_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    central_idx += 1
                
                if pacific_idx < len(pacific_cards):
                    home, away = pacific_cards[pacific_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    pacific_idx += 1
            
            current_date += datetime.timedelta(days=1)
        
        # 交流戦期間
        interleague_idx = 0
        while current_date <= self.interleague_end:
            if current_date.weekday() == 0:
                current_date += datetime.timedelta(days=1)
                continue
            
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 1日6試合（全12チームが対戦）
            for _ in range(6):
                if interleague_idx < len(interleague_cards):
                    home, away = interleague_cards[interleague_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    interleague_idx += 1
            
            current_date += datetime.timedelta(days=1)
        
        # 交流戦後〜オールスター前（リーグ戦後半前半）
        while current_date < self.allstar_break_start:
            if current_date.weekday() == 0:
                current_date += datetime.timedelta(days=1)
                continue
            
            date_str = current_date.strftime("%Y-%m-%d")
            
            for _ in range(3):
                if central_idx < len(central_cards):
                    home, away = central_cards[central_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    central_idx += 1
                
                if pacific_idx < len(pacific_cards):
                    home, away = pacific_cards[pacific_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    pacific_idx += 1
            
            current_date += datetime.timedelta(days=1)
        
        # オールスター休み（スキップ）
        current_date = self.allstar_break_end + datetime.timedelta(days=1)
        
        # オールスター後〜シーズン終了（リーグ戦後半）
        while current_date <= self.season_end:
            if current_date.weekday() == 0:
                current_date += datetime.timedelta(days=1)
                continue
            
            date_str = current_date.strftime("%Y-%m-%d")
            
            for _ in range(3):
                if central_idx < len(central_cards):
                    home, away = central_cards[central_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    central_idx += 1
                
                if pacific_idx < len(pacific_cards):
                    home, away = pacific_cards[pacific_idx]
                    self.schedule.games.append(ScheduledGame(
                        game_number=game_number,
                        date=date_str,
                        home_team_name=home,
                        away_team_name=away
                    ))
                    game_number += 1
                    pacific_idx += 1
            
            current_date += datetime.timedelta(days=1)
        
        # 残りの交流戦カード（あれば）
        while interleague_idx < len(interleague_cards):
            home, away = interleague_cards[interleague_idx]
            self.schedule.games.append(ScheduledGame(
                game_number=game_number,
                date=current_date.strftime("%Y-%m-%d"),
                home_team_name=home,
                away_team_name=away
            ))
            game_number += 1
            interleague_idx += 1
        
        # ゲームを日付順にソート
        self.schedule.games.sort(key=lambda g: (g.date, g.game_number))
    
    def get_next_game_for_team(self, team_name: str) -> Optional[ScheduledGame]:
        """指定チームの次の試合を取得"""
        return self.schedule.get_next_game(team_name)
    
    def get_team_schedule(self, team_name: str) -> List[ScheduledGame]:
        """指定チームの全試合スケジュール"""
        return self.schedule.get_team_games(team_name)
    
    def get_recent_results(self, team_name: str, count: int = 10) -> List[ScheduledGame]:
        """最近の試合結果を取得"""
        completed_games = self.schedule.get_team_games(team_name, GameStatus.COMPLETED)
        return completed_games[-count:]
    
    def complete_game(self, game: ScheduledGame, home_score: int, away_score: int):
        """試合を完了としてマーク"""
        self.schedule.complete_game(game, home_score, away_score)
        
        if game in self.schedule.games:
            current_idx = self.schedule.games.index(game)
            if current_idx >= self.schedule.current_game_index:
                self.schedule.current_game_index = current_idx + 1
    
    def get_all_games_for_date(self, date_str: str) -> List[ScheduledGame]:
        """特定日の全試合を取得"""
        return [g for g in self.schedule.games if g.date == date_str]
    
    def simulate_other_games(self, player_team_name: str, date_str: str):
        """プレイヤーチーム以外の試合を自動シミュレート"""
        from game_simulator import GameSimulator
        
        games_today = self.get_all_games_for_date(date_str)
        
        for game in games_today:
            if game.status == GameStatus.SCHEDULED:
                if game.home_team_name != player_team_name and game.away_team_name != player_team_name:
                    home_score = random.randint(0, 10)
                    away_score = random.randint(0, 10)
                    self.complete_game(game, home_score, away_score)
    
    def get_progress_percentage(self) -> float:
        """シーズン進行率を取得"""
        total_games = len(self.schedule.games)
        completed_games = len([g for g in self.schedule.games if g.status == GameStatus.COMPLETED])
        return (completed_games / total_games * 100) if total_games > 0 else 0.0
    
    def is_interleague_period(self, date_str: str) -> bool:
        """交流戦期間かどうか"""
        try:
            check_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return self.interleague_start <= check_date <= self.interleague_end
        except:
            return False
    
    def is_allstar_break(self, date_str: str) -> bool:
        """オールスター休みかどうか"""
        try:
            check_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return self.allstar_break_start <= check_date <= self.allstar_break_end
        except:
            return False
    
    def get_team_games_count(self, team_name: str) -> int:
        """チームの総試合数を取得"""
        return len(self.get_team_schedule(team_name))
    
    def get_team_completed_games_count(self, team_name: str) -> int:
        """チームの消化試合数を取得"""
        return len([g for g in self.get_team_schedule(team_name) if g.is_completed])
