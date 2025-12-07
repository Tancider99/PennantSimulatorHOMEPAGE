# -*- coding: utf-8 -*-
"""
ゲーム状態管理
"""
from enum import Enum
from typing import Optional, List
from models import Team, Player, DraftProspect


class GameState(Enum):
    """ゲーム状態の列挙型"""
    TITLE = "タイトル"
    SETTINGS = "設定"
    NEW_GAME_SETUP = "新規ゲーム設定"  # ゲーム開始時の詳細設定画面
    TEAM_SELECT = "チーム選択"
    TEAM_CREATE = "チーム作成"  # 新規チーム作成画面
    DIFFICULTY_SELECT = "難易度選択"
    MENU = "メニュー"
    SCHEDULE_VIEW = "日程表"
    LINEUP = "オーダー設定"
    PITCHER_ORDER = "投手オーダー"  # 投手起用設定画面
    BENCH_SETTING = "ベンチ設定"  # ベンチ入りメンバー設定
    GAME = "試合"
    GAME_WATCH = "試合観戦"  # 一球速報風の試合観戦モード
    GAME_MANAGE = "采配モード"  # 采配モード：自分のチームを操作
    GAME_CHOICE = "試合方法選択"  # 観戦か結果スキップか選択
    RESULT = "試合結果"
    STANDINGS = "順位表"
    PLAYER_STATS = "選手成績"
    TEAM_MANAGEMENT = "チーム管理"
    DRAFT = "ドラフト会議"
    DEVELOPMENTAL_DRAFT = "育成ドラフト"  # 追加：育成ドラフト
    IKUSEI_DRAFT = "育成ドラフト"  # 別名（互換性用）
    FREE_AGENT = "外国人FA"
    TRAINING = "選手育成"
    SEASON_END = "シーズン終了"
    PLAYOFFS = "プレーオフ"
    JAPAN_SERIES = "日本シリーズ"
    # 新規追加
    TEAM_INFO = "チーム情報"
    PLAYER_DETAIL = "選手詳細"
    TEAM_STATS = "チーム成績"
    TEAM_EDIT = "チーム編集"  # チーム名編集用
    # ペナントモード
    PENNANT_HOME = "ペナントホーム"
    PENNANT_DRAFT = "ペナントドラフト"
    PENNANT_FA = "ペナントFA"
    PENNANT_TRADE = "ペナントトレード"
    PENNANT_CAMP = "春季キャンプ"
    PENNANT_FALL_CAMP = "秋季キャンプ"  # 秋季キャンプ（総合力が低い選手のみ参加）
    PENNANT_CS = "クライマックスシリーズ"
    PENNANT_JS = "日本シリーズ"
    # 経営システム
    MANAGEMENT = "経営"
    FINANCES = "財務"
    FACILITIES = "施設"
    SPONSORS = "スポンサー"
    # 選手管理
    ROSTER_MANAGEMENT = "選手登録管理"
    OFFSEASON = "オフシーズン"
    CONTRACT_RENEWAL = "契約更改"


class DifficultyLevel(Enum):
    """難易度レベル"""
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

        # ゲーム進行データ
        self.player_team: Optional[Team] = None
        self.central_teams: List[Team] = []
        self.pacific_teams: List[Team] = []
        self.all_teams: List[Team] = []

        self.current_year = 2027
        self.current_game_number = 0
        self.current_opponent: Optional[Team] = None
        self.current_date: str = "2027-03-29"  # 開幕日

        # NPB日程エンジン
        self.schedule_engine = None
        self.schedule = None

        # ドラフト・FA関連
        self.draft_prospects: List[DraftProspect] = []
        self.foreign_free_agents: List[Player] = []
        self.selected_draft_pick: Optional[int] = None

        # UI関連
        self.scroll_offset = 0
        self.result_scroll = 0

        # プレーオフ進行状況
        self.playoff_stage = None  # None, "CLIMAX_FIRST", "CLIMAX_FINAL", "JAPAN_SERIES"
        self.playoff_teams = []

        # 試合結果履歴
        self.game_history: List[dict] = []

    def initialize_schedule(self):
        """NPB日程を初期化"""
        from npb_schedule_engine import NPBScheduleEngine
        from models import League

        self.schedule_engine = NPBScheduleEngine(self.current_year)

        # チームをリーグ別に分類
        central = [t for t in self.all_teams if t.league == League.CENTRAL]
        pacific = [t for t in self.all_teams if t.league == League.PACIFIC]

        self.schedule = self.schedule_engine.generate_schedule(central, pacific)
        self.current_date = self.schedule_engine.opening_day.strftime("%Y-%m-%d")

    def get_next_game(self):
        """プレイヤーチームの次の試合を取得"""
        if not self.schedule_engine or not self.player_team:
            return None
        return self.schedule_engine.get_next_game(self.player_team.name, self.current_date)

    def get_today_games(self):
        """今日の全試合を取得"""
        if not self.schedule_engine:
            return []
        return self.schedule_engine.get_games_for_date(self.current_date)

    def record_game_result(self, home_team, away_team, home_score, away_score):
        """試合結果を記録"""
        result = {
            'date': self.current_date,
            'home_team': home_team.name,
            'away_team': away_team.name,
            'home_score': home_score,
            'away_score': away_score,
            'winner': home_team.name if home_score > away_score else (away_team.name if away_score > home_score else 'DRAW')
        }
        self.game_history.append(result)

        # チーム成績更新
        if home_score > away_score:
            home_team.wins += 1
            away_team.losses += 1
        elif away_score > home_score:
            away_team.wins += 1
            home_team.losses += 1
        else:
            home_team.draws += 1
            away_team.draws += 1

    def get_recent_results(self, team_name: str, count: int = 10) -> List[str]:
        """チームの最近の勝敗を取得 ('W', 'L', 'D')"""
        results = []
        for game in reversed(self.game_history):
            if game['home_team'] == team_name or game['away_team'] == team_name:
                if game['winner'] == team_name:
                    results.append('W')
                elif game['winner'] == 'DRAW':
                    results.append('D')
                else:
                    results.append('L')
                if len(results) >= count:
                    break
        return results

    @property
    def teams(self) -> List[Team]:
        """Alias for all_teams for compatibility"""
        return self.all_teams

    def change_state(self, new_state: GameState):
        """状態を変更"""
        self.previous_state = self.current_state
        self.current_state = new_state
        self.scroll_offset = 0
        self.result_scroll = 0
    
    def go_back(self):
        """前の状態に戻る"""
        if self.previous_state:
            self.current_state = self.previous_state
            self.previous_state = None
    
    def is_season_complete(self) -> bool:
        """シーズンが完了したかチェック"""
        # 143試合制
        return self.current_game_number >= 143
    
    def get_difficulty_multiplier(self) -> float:
        """難易度に応じた補正値を取得"""
        multipliers = {
            DifficultyLevel.EASY: 1.3,
            DifficultyLevel.NORMAL: 1.0,
            DifficultyLevel.HARD: 0.8,
            DifficultyLevel.VERY_HARD: 0.6
        }
        return multipliers.get(self.difficulty, 1.0)
    
    def reset_for_new_season(self):
        """新シーズンのためにリセット"""
        self.current_year += 1
        self.current_game_number = 0
        self.current_opponent = None
        self.playoff_stage = None
        self.playoff_teams = []
        
        # 全チームの成績をリセット
        for team in self.all_teams:
            team.wins = 0
            team.losses = 0
            team.draws = 0
            
            # 選手の成績をリセット
            for player in team.players:
                player.record.at_bats = 0
                player.record.hits = 0
                player.record.doubles = 0
                player.record.triples = 0
                player.record.home_runs = 0
                player.record.rbis = 0
                player.record.runs = 0
                player.record.walks = 0
                player.record.strikeouts = 0
                player.record.stolen_bases = 0
                player.record.games_pitched = 0
                player.record.wins = 0
                player.record.losses = 0
                player.record.saves = 0
                player.record.innings_pitched = 0.0
                player.record.earned_runs = 0
                player.record.hits_allowed = 0
                player.record.walks_allowed = 0
                player.record.strikeouts_pitched = 0
                
                # 選手の年齢を1増やす
                player.age += 1
                player.years_pro += 1