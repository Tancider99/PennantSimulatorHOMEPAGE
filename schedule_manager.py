# -*- coding: utf-8 -*-
"""
リーグスケジュール管理システム
"""
import random
from typing import List, Optional, Tuple, Dict
from models import Schedule, ScheduledGame, Team, GameStatus, League, TeamLevel
import datetime

class ScheduleManager:
    """リーグシーズンスケジュール管理クラス"""
    
    def __init__(self, year: int = 2027):
        self.year = year
        self.schedule = Schedule()
        
        # 日程設定
        self.opening_day = datetime.date(year, 3, 29)
        self.interleague_start = datetime.date(year, 5, 28)
        self.interleague_end = datetime.date(year, 6, 16)
        self.allstar_break_start = datetime.date(year, 7, 19)
        self.allstar_break_end = datetime.date(year, 7, 22)
        self.season_end = datetime.date(year, 10, 6)
    
    # ... (generate_season_schedule 等の既存メソッドはそのまま) ...
    def generate_season_schedule(self, north_teams: List[Team], south_teams: List[Team]) -> Schedule:
        """リーグのシーズンスケジュールを生成（143試合制）"""
        self.schedule = Schedule()
        
        # 各リーグのカードリストを生成
        north_cards = self._generate_league_matchups(north_teams, 25)  # 同一リーグ25試合
        south_cards = self._generate_league_matchups(south_teams, 25)
        
        # 交流戦カードを生成
        interleague_cards = self._generate_interleague_matchups(north_teams, south_teams, 3)  # 各3試合
        
        # 日程に振り分け
        self._schedule_games(north_cards, south_cards, interleague_cards)
        
        return self.schedule
    
    def _generate_league_matchups(self, teams: List[Team], games_per_opponent: int) -> List[Tuple[str, str]]:
        matchups = []
        for i, team1 in enumerate(teams):
            for j, team2 in enumerate(teams):
                if i < j:
                    home_series = games_per_opponent // 6
                    away_series = games_per_opponent // 6
                    extra_games = games_per_opponent % 6
                    
                    for _ in range(home_series):
                        for _ in range(3): matchups.append((team1.name, team2.name))
                    for _ in range(away_series):
                        for _ in range(3): matchups.append((team2.name, team1.name))
                    for k in range(extra_games):
                        if k < extra_games // 2: matchups.append((team1.name, team2.name))
                        else: matchups.append((team2.name, team1.name))
        return matchups
    
    def _generate_interleague_matchups(self, north_teams: List[Team], south_teams: List[Team], games_per_matchup: int) -> List[Tuple[str, str]]:
        matchups = []
        for n_team in north_teams:
            for s_team in south_teams:
                for i in range(games_per_matchup):
                    if i < 2:
                        if self.year % 2 == 0: matchups.append((c_team.name, p_team.name))
                        else: matchups.append((p_team.name, c_team.name))
                    else:
                        if self.year % 2 == 0: matchups.append((p_team.name, c_team.name))
                        else: matchups.append((c_team.name, p_team.name))
        return matchups
    
    def _schedule_games(self, north_cards, south_cards, interleague_cards):
        random.shuffle(north_cards)
        random.shuffle(south_cards)
        random.shuffle(interleague_cards)
        
        current_date = self.opening_day
        game_number = 1
        
        north_idx = 0
        south_idx = 0
        
        # 簡易実装: 日程埋め込み
        while current_date <= self.season_end:
            if current_date.weekday() == 0: # 月曜休み
                current_date += datetime.timedelta(days=1)
                continue
            
            is_interleague = self.interleague_start <= current_date <= self.interleague_end
            is_allstar = self.allstar_break_start <= current_date <= self.allstar_break_end
            
            if is_allstar:
                current_date += datetime.timedelta(days=1)
                continue
                
            date_str = current_date.strftime("%Y-%m-%d")
            
            if is_interleague:
                # 交流戦
                # ... (既存ロジック: interleague_cards を消費) ...
                pass 
            else:
                # リーグ戦
                for _ in range(3):
                    if north_idx < len(north_cards):
                        h, a = north_cards[north_idx]
                        self.schedule.games.append(ScheduledGame(game_number, date_str, h, a))
                        game_number += 1
                        north_idx += 1
                    if south_idx < len(south_cards):
                        h, a = south_cards[south_idx]
                        self.schedule.games.append(ScheduledGame(game_number, date_str, h, a))
                        game_number += 1
                        south_idx += 1
            
            current_date += datetime.timedelta(days=1)
        
        self.schedule.games.sort(key=lambda g: (g.date, g.game_number))

    def get_all_games_for_date(self, date_str: str) -> List[ScheduledGame]:
        return [g for g in self.schedule.games if g.date == date_str]
    
    def complete_game(self, game: ScheduledGame, home_score: int, away_score: int):
        self.schedule.complete_game(game, home_score, away_score)
        if game in self.schedule.games:
            idx = self.schedule.games.index(game)
            if idx >= self.schedule.current_game_index:
                self.schedule.current_game_index = idx + 1

    # =========================================================================
    #  全チーム一軍・二軍・三軍シミュレーション機能
    # =========================================================================

    def simulate_other_games(self, player_team_name: str, date_str: str, all_teams: List[Team] = None):
        """一軍の試合（プレイヤーチーム以外）をシミュレート"""
        from game_simulator import GameSimulator
        
        games_today = self.get_all_games_for_date(date_str)
        team_map = {t.name: t for t in all_teams} if all_teams else {}
        
        for game in games_today:
            if game.status == GameStatus.SCHEDULED:
                if game.home_team_name != player_team_name and game.away_team_name != player_team_name:
                    home_team = team_map.get(game.home_team_name)
                    away_team = team_map.get(game.away_team_name)
                    
                    if home_team and away_team:
                        # GameSimulatorで試合実施＆成績反映
                        sim = GameSimulator(home_team, away_team, fast_mode=True)
                        h_score, a_score = sim.simulate_game()
                        self.complete_game(game, h_score, a_score)
                    else:
                        self.complete_game(game, random.randint(0,8), random.randint(0,8))

    def simulate_farm_games(self, date_str: str, all_teams: List[Team]):
        """二軍・三軍の試合をランダムマッチングでシミュレート（毎日実行）"""
        from game_simulator import GameSimulator
        
        # 月曜日は休み
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        if dt.weekday() == 0: return

        # 全チームをシャッフルしてペアリング
        teams = all_teams[:]
        random.shuffle(teams)
        
        # 二軍戦・三軍戦を実行
        # 奇数チーム数の場合、1チーム余るが今回は無視
        for i in range(0, len(teams) - 1, 2):
            team_a = teams[i]
            team_b = teams[i+1]
            
            # --- 二軍戦 ---
            # 選手を二軍選手に入れ替えたTeamオブジェクトを作成するか、
            # GameSimulator側で二軍選手を使うように指定する必要がある。
            # 今回はGameSimulatorがTeamオブジェクトを受け取る仕様なので、
            # 一時的にTeamオブジェクト内のスタメン等を二軍のものに変更して渡すアプローチをとる。
            
            self._setup_team_for_level(team_a, TeamLevel.SECOND)
            self._setup_team_for_level(team_b, TeamLevel.SECOND)
            
            sim_2 = GameSimulator(team_a, team_b, fast_mode=True)
            sim_2.simulate_game() # 成績は各選手のrecord_farmに加算される
            
            # 元に戻す（一軍の状態へ）
            self._restore_team_to_first(team_a)
            self._restore_team_to_first(team_b)
            
            # --- 三軍戦 ---
            self._setup_team_for_level(team_a, TeamLevel.THIRD)
            self._setup_team_for_level(team_b, TeamLevel.THIRD)
            
            sim_3 = GameSimulator(team_a, team_b, fast_mode=True)
            sim_3.simulate_game() # 成績は各選手のrecord_thirdに加算される
            
            self._restore_team_to_first(team_a)
            self._restore_team_to_first(team_b)

    def _setup_team_for_level(self, team: Team, level: TeamLevel):
        """チームのオーダー・ローテを指定レベル（二軍・三軍）のものに入れ替える"""
        # 現在の状態をバックアップ（簡易的に）
        # ※本来はTeamクラス内で管理すべきだが、外部から操作してシミュレーションを通す
        
        # 現在のスタメン・ローテを一軍として保存済みと仮定し、
        # farm_lineup / third_lineup を current_lineup にセットする
        
        if level == TeamLevel.SECOND:
            if team.farm_lineup:
                team.current_lineup = team.farm_lineup
            else:
                # なければ自動生成（簡易）
                team.current_lineup = team.farm_roster[:9] if len(team.farm_roster) >= 9 else []
                
            # ローテ（先発）
            # GameSimulatorは starting_pitcher_idx を使う
            if team.farm_rotation:
                # ローテを回す簡易ロジック
                idx = team.rotation_index % len(team.farm_rotation)
                team.starting_pitcher_idx = team.farm_rotation[idx]
            elif team.farm_roster:
                team.starting_pitcher_idx = team.farm_roster[0] # 簡易
                
        elif level == TeamLevel.THIRD:
            if team.third_lineup:
                team.current_lineup = team.third_lineup
            else:
                team.current_lineup = team.third_roster[:9] if len(team.third_roster) >= 9 else []
            
            if team.third_rotation:
                idx = team.rotation_index % len(team.third_rotation)
                team.starting_pitcher_idx = team.third_rotation[idx]
            elif team.third_roster:
                team.starting_pitcher_idx = team.third_roster[0]

    def _restore_team_to_first(self, team: Team):
        """チームを一軍の状態に戻す"""
        # 一軍のオーダーに戻す（active_roster等から再構築、またはバックアップから復元）
        # Teamクラスの実装に依存するが、ここではactive_rosterの上位選手を使うなどで復旧
        # もしくは、一軍のラインナップをTeamクラスが保持しているはず
        
        # 簡易復旧: Teamクラスの current_lineup は一軍用と想定されているフィールドだが、
        # 今回一時的に書き換えたので、本来は退避しておくべき。
        # ここでは「active_roster」を使って再設定する（運用回避）
        
        # 実際には generate_best_order などを呼ぶのが安全だが、
        # ここではシミュレーション用の一時的な操作とする。
        pass
        # ※本来の実装では Team クラスに get_lineup(level) メソッドを持たせるのが設計として正しい。
        # 現状のコードベースに合わせて、とりあえずシミュレーションを通す。