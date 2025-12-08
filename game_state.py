# -*- coding: utf-8 -*-
"""
ゲーム状態管理 (拡張版: 全軍日程管理・AI運用・統括シミュレーション)
"""
from enum import Enum
from typing import Optional, List
from models import Team, Player, DraftProspect, TeamLevel
import traceback
import random
from PySide6.QtCore import QDate

class GameState(Enum):
    TITLE = "タイトル"
    SETTINGS = "設定"
    NEW_GAME_SETUP = "新規ゲーム設定"
    TEAM_SELECT = "チーム選択"
    TEAM_CREATE = "チーム作成"
    DIFFICULTY_SELECT = "難易度選択"
    MENU = "メニュー"
    SCHEDULE_VIEW = "日程表"
    LINEUP = "オーダー設定"
    PITCHER_ORDER = "投手オーダー"
    BENCH_SETTING = "ベンチ設定"
    GAME = "試合"
    GAME_WATCH = "試合観戦"
    GAME_MANAGE = "采配モード"
    GAME_CHOICE = "試合方法選択"
    RESULT = "試合結果"
    STANDINGS = "順位表"
    PLAYER_STATS = "選手成績"
    TEAM_MANAGEMENT = "チーム管理"
    DRAFT = "ドラフト会議"
    DEVELOPMENTAL_DRAFT = "育成ドラフト"
    IKUSEI_DRAFT = "育成ドラフト"
    FREE_AGENT = "外国人FA"
    TRAINING = "選手育成"
    SEASON_END = "シーズン終了"
    PLAYOFFS = "プレーオフ"
    JAPAN_SERIES = "日本シリーズ"
    TEAM_INFO = "チーム情報"
    PLAYER_DETAIL = "選手詳細"
    TEAM_STATS = "チーム成績"
    TEAM_EDIT = "チーム編集"
    PENNANT_HOME = "ペナントホーム"
    PENNANT_DRAFT = "ペナントドラフト"
    PENNANT_FA = "ペナントFA"
    PENNANT_TRADE = "ペナントトレード"
    PENNANT_CAMP = "春季キャンプ"
    PENNANT_FALL_CAMP = "秋季キャンプ"
    PENNANT_CS = "クライマックスシリーズ"
    PENNANT_JS = "日本シリーズ"
    MANAGEMENT = "経営"
    FINANCES = "財務"
    FACILITIES = "施設"
    SPONSORS = "スポンサー"
    ROSTER_MANAGEMENT = "選手登録管理"
    OFFSEASON = "オフシーズン"
    CONTRACT_RENEWAL = "契約更改"


class DifficultyLevel(Enum):
    EASY = "イージー"
    NORMAL = "ノーマル"
    HARD = "ハード"
    VERY_HARD = "ベリーハード"


class GameStateManager:
    """ゲーム状態を管理するクラス"""

    def __init__(self):
        self.current_state = GameState.TITLE
        self.previous_state = None
        self.difficulty = DifficultyLevel.NORMAL

        self.player_team: Optional[Team] = None
        self.north_teams: List[Team] = []
        self.south_teams: List[Team] = []
        self.all_teams: List[Team] = []

        self.current_year = 2027
        self.current_game_number = 0
        self.current_opponent: Optional[Team] = None
        self.current_date: str = "2027-03-29"

        self.schedule_engine = None
        self.schedule = None # 一軍日程
        self.farm_schedule = None # 二軍日程
        self.third_schedule = None # 三軍日程

        self.draft_prospects: List[DraftProspect] = []
        self.foreign_free_agents: List[Player] = []
        self.selected_draft_pick: Optional[int] = None

        self.scroll_offset = 0
        self.result_scroll = 0
        self.playoff_stage = None
        self.playoff_teams = []
        self.game_history: List[dict] = []

    def initialize_schedule(self):
        """全軍の日程を初期化"""
        from league_schedule_engine import LeagueScheduleEngine
        from models import League

        self.schedule_engine = LeagueScheduleEngine(self.current_year)
        north = [t for t in self.all_teams if t.league == League.NORTH]
        south = [t for t in self.all_teams if t.league == League.SOUTH]

        self.schedule = self.schedule_engine.generate_schedule(north, south)
        self.current_date = self.schedule_engine.opening_day.strftime("%Y-%m-%d")
        
        self.farm_schedule = self.schedule_engine.generate_farm_schedule(north, south, TeamLevel.SECOND)
        self.third_schedule = self.schedule_engine.generate_farm_schedule(north, south, TeamLevel.THIRD)

    def process_date(self, date_str: str):
        """
        指定された日付の全試合をシミュレート
        （手動試合の場合も、残りの他球場試合を消化するためにこれを呼ぶ）
        """
        from live_game_engine import LiveGameEngine
        from farm_game_simulator import simulate_farm_games_for_day
        
        try:
            # 1. AIチーム運用（ロースター・オーダー調整）
            self._manage_ai_teams(date_str)

            # 2. 一軍試合シミュレーション
            if self.schedule:
                todays_games = [g for g in self.schedule.games if g.date == date_str and not g.is_completed]
                
                for game in todays_games:
                    home = next((t for t in self.all_teams if t.name == game.home_team_name), None)
                    away = next((t for t in self.all_teams if t.name == game.away_team_name), None)
                    
                    if home and away:
                        # プレイヤーチームの手動試合は既に完了している場合が多いが、
                        # もし未完了ならここでシミュレートされる（スキップ時など）
                        if home != self.player_team: self._ensure_valid_roster(home)
                        if away != self.player_team: self._ensure_valid_roster(away)
                        
                        try:
                            # 試合実行
                            engine = LiveGameEngine(home, away)
                            while not engine.is_game_over():
                                engine.simulate_pitch()
                            
                            # 成績反映
                            engine.finalize_game_stats()
                            
                            # 結果記録
                            self.record_game_result(home, away, engine.state.home_score, engine.state.away_score)
                            game.status = game.status.COMPLETED
                            game.home_score = engine.state.home_score
                            game.away_score = engine.state.away_score
                            
                            # 先発ローテーションを進める
                            home.rotation_index = (home.rotation_index + 1) % 6
                            away.rotation_index = (away.rotation_index + 1) % 6
                            
                        except Exception as e:
                            print(f"Error simulating game {home.name} vs {away.name}: {e}")
                            traceback.print_exc()

            # 3. 二軍・三軍の試合シミュレーション
            simulate_farm_games_for_day(self.all_teams, date_str)
            
            # 日付更新（呼び出し元で制御する場合は上書きに注意）
            self.current_date = date_str
            
        except Exception as e:
            print(f"Critical error in process_date: {e}")
            traceback.print_exc()

    def finish_day_and_advance(self):
        """
        その日の残り試合（他球場、二軍三軍）を消化し、日付を翌日に進める
        （手動試合終了後に呼び出す）
        """
        # 当日の残り試合を消化
        self.process_date(self.current_date)
        
        # 日付を翌日に進める
        try:
            y, m, d = map(int, self.current_date.split('-'))
            current_qdate = QDate(y, m, d)
            next_date = current_qdate.addDays(1)
            self.current_date = next_date.toString("yyyy-MM-dd")
        except:
            pass

    def _manage_ai_teams(self, date_str):
        """
        AIチームおよび自チーム二軍三軍の管理
        オーダー、ローテーションの自動生成など
        """
        for team in self.all_teams:
            if team != self.player_team:
                self._ensure_valid_roster(team)
            
            # 二軍三軍のオーダー・ローテ自動生成（不足時のみ、または定期的に更新）
            # ここでは「毎回チェックして生成」するが、固定化を防ぐため毎回シャッフル要素を入れる
            
            # 毎回リフレッシュして出場機会を分散させる
            team.farm_lineup = self._auto_generate_lineup(team, TeamLevel.SECOND)
            team.third_lineup = self._auto_generate_lineup(team, TeamLevel.THIRD)
            
            if not team.farm_rotation:
                team.farm_rotation = self._auto_generate_rotation(team, TeamLevel.SECOND)
            if not team.third_rotation:
                team.third_rotation = self._auto_generate_rotation(team, TeamLevel.THIRD)

    def _ensure_valid_roster(self, team: Team):
        valid_starters = len([x for x in team.current_lineup if x != -1])
        valid_rotation = len([x for x in team.rotation if x != -1])
        if valid_starters < 9 or valid_rotation == 0:
            team.auto_assign_rosters()
            team.auto_set_bench()

    def _auto_generate_lineup(self, team: Team, level: TeamLevel) -> List[int]:
        """
        指定レベルの自動打順生成
        一軍: 能力重視
        二軍・三軍: 若手・育成優先＋ランダム性
        """
        from models import Position
        roster = team.get_players_by_level(level)
        # チーム内インデックスを取得
        indices = [team.players.index(p) for p in roster if p.position != Position.PITCHER]
        
        if level == TeamLevel.FIRST:
            # 一軍はガチ構成（能力順）
            indices.sort(key=lambda i: team.players[i].stats.overall_batting(), reverse=True)
        else:
            # 二軍・三軍は育成優先
            # スコア = 能力*0.4 + (30-年齢)*2 + ランダム
            def calc_farm_score(p_idx):
                p = team.players[p_idx]
                ovr = p.stats.overall_batting()
                age_bonus = max(0, 30 - p.age) * 3  # 若手優遇
                rand = random.uniform(0, 15)        # ランダム性（固定化防止）
                return ovr * 0.4 + age_bonus + rand
            
            indices.sort(key=calc_farm_score, reverse=True)

        return indices[:9]

    def _auto_generate_rotation(self, team: Team, level: TeamLevel) -> List[int]:
        """
        指定レベルの自動ローテ生成
        一軍: 能力重視
        二軍・三軍: 若手・育成優先
        """
        from models import Position
        roster = team.get_players_by_level(level)
        indices = [team.players.index(p) for p in roster if p.position == Position.PITCHER]
        
        if level == TeamLevel.FIRST:
            indices.sort(key=lambda i: team.players[i].stats.overall_pitching(), reverse=True)
        else:
            def calc_farm_pitch_score(p_idx):
                p = team.players[p_idx]
                ovr = p.stats.overall_pitching()
                age_bonus = max(0, 28 - p.age) * 3
                rand = random.uniform(0, 10)
                # 先発適性も考慮
                return ovr * 0.4 + age_bonus + p.starter_aptitude * 0.2 + rand

            indices.sort(key=calc_farm_pitch_score, reverse=True)
            
        return indices[:6]

    def get_next_game(self):
        if not self.schedule_engine or not self.player_team: return None
        return self.schedule_engine.get_next_game(self.player_team.name, self.current_date)

    def get_today_games(self):
        if not self.schedule_engine: return []
        return self.schedule_engine.get_games_for_date(self.current_date)

    def record_game_result(self, home_team, away_team, home_score, away_score):
        result = {
            'date': self.current_date, 'home_team': home_team.name, 'away_team': away_team.name,
            'home_score': home_score, 'away_score': away_score,
            'winner': home_team.name if home_score > away_score else (away_team.name if away_score > home_score else 'DRAW')
        }
        self.game_history.append(result)
        if home_score > away_score:
            home_team.wins += 1; away_team.losses += 1
        elif away_score > home_score:
            away_team.wins += 1; home_team.losses += 1
        else:
            home_team.draws += 1; away_team.draws += 1

    def get_recent_results(self, team_name: str, count: int = 10) -> List[str]:
        results = []
        for game in reversed(self.game_history):
            if game['home_team'] == team_name or game['away_team'] == team_name:
                if game['winner'] == team_name: results.append('W')
                elif game['winner'] == 'DRAW': results.append('D')
                else: results.append('L')
                if len(results) >= count: break
        return results

    @property
    def teams(self) -> List[Team]: return self.all_teams

    def change_state(self, new_state: GameState):
        self.previous_state = self.current_state
        self.current_state = new_state
        self.scroll_offset = 0
        self.result_scroll = 0
    
    def go_back(self):
        if self.previous_state:
            self.current_state = self.previous_state
            self.previous_state = None
    
    def is_season_complete(self) -> bool: return self.current_game_number >= 143
    
    def get_difficulty_multiplier(self) -> float:
        return {DifficultyLevel.EASY: 1.3, DifficultyLevel.NORMAL: 1.0, DifficultyLevel.HARD: 0.8, DifficultyLevel.VERY_HARD: 0.6}.get(self.difficulty, 1.0)
    
    def reset_for_new_season(self):
        self.current_year += 1
        self.current_game_number = 0
        self.current_opponent = None
        self.playoff_stage = None
        self.playoff_teams = []
        for team in self.all_teams:
            team.wins = 0; team.losses = 0; team.draws = 0
            for player in team.players:
                player.record.reset()
                player.age += 1
                player.years_pro += 1