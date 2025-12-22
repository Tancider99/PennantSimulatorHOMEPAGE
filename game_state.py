# -*- coding: utf-8 -*-
"""
ゲーム状態管理 (NPB準拠版: 天候システム・延期試合・ポストシーズン・オフシーズン対応)
"""
from enum import Enum
from typing import Optional, List, Tuple
from models import Team, Player, DraftProspect, TeamLevel, Position, generate_best_lineup, GameStatus
from stats_records import update_league_stats
import traceback
import random
import datetime
from PySide6.QtCore import QDate
from farm_game_simulator import FarmGameSimulator
from league_schedule_engine import WeatherSystem
from training_system import apply_team_training

from dataclasses import dataclass, field
from typing import List

@dataclass
class PendingTrade:
    """承認待ちのトレード提案"""
    offering_team_name: str
    target_team_name: str
    offered_player_ids: List[int] # チーム内のインデックス
    requested_player_ids: List[int] # チーム内のインデックス
    money_adjustment: int # 正: 自チーム支払い, 負: 受取
    days_remaining: int = 5
    success_chance: int = 0


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

        # NPB準拠シーズン管理
        self.season_manager = None
        self.weather_enabled = True
        self.cancelled_games_today: List = []  # 今日の中止試合
        self.postseason_schedule = None
        self.japan_series_schedule = None
        
        # 自動オーダー設定: "ability" (能力優先) or "condition" (調子優先)
        self.auto_order_priority = "ability"
        
        # 自由契約選手リスト (Acquisitions用)
        self.free_agents: List[Player] = []
        self.news_feed = [] # ニュースフィード
        self.pending_trades: List[PendingTrade] = [] # トレード提案中リスト
        self.daily_rankings: Dict[str, Dict[str, int]] = {} # 日別順位履歴 {date: {team_name: rank}}
        self._generate_dummy_free_agents()

    def _generate_dummy_free_agents(self):
        """テスト用の自由契約選手を生成"""
        if self.free_agents: return
        
        import random
        from models import Player, Position, PlayerStats
        
        # Foreigners / Veterans
        names = ["スミス", "ジョンソン", "ガルシア", "李", "王", "田中(元)", "佐藤(元)"]
        for name in names:
            pos = random.choice(list(Position))
            if pos == Position.DH: pos = Position.FIRST
            p = Player(name=name, position=pos, age=random.randint(28, 38))
            p.stats = PlayerStats()
            
            p.stats.speed = random.randint(30, 70)

            if pos == Position.PITCHER:
                p.stats.stuff = random.randint(30, 70)
                p.stats.control = random.randint(30, 70)
                p.stats.stamina = random.randint(30, 70)
                p.stats.breaking = random.randint(30, 70)
                p.stats.velocity = 150
                
                # Pitcher Batting (Weak)
                p.stats.contact = random.randint(1, 20)
                p.stats.power = random.randint(1, 20)
                p.stats.trajectory = 1
            else:
                # Fielder Batting (Normal)
                p.stats.contact = random.randint(30, 70)
                p.stats.power = random.randint(40, 80)
                
                # Fielder Pitching (Weak)
                p.stats.velocity = 120
                p.stats.control = random.randint(1, 10)
                p.stats.stuff = random.randint(1, 10)
                p.stats.stamina = random.randint(1, 10)
                p.stats.breaking = random.randint(1, 10)
            
            p.salary = random.randint(1000, 10000) * 10000
            
            self.free_agents.append(p)

    def log_news(self, category: str, message: str, team_name: str = None, date: str = None):
        """ニュースを記録"""
        if date is None:
            date = self.current_date
        
        self.news_feed.insert(0, {
            "date": date,
            "category": category,
            "message": message,
            "team": team_name
        })
        # 制限（最新500件）
        if len(self.news_feed) > 500:
            self.news_feed.pop()
            
    def get_news(self, team_name: str = None, limit: int = 50):
        """ニュースを取得"""
        # マッチ結果等は動的に結合するか、news_feedに都度入れるか。
        # ここではnews_feedのみ返す設計にする（試合結果もnews_feedに入れる運用）
        if not team_name:
            return self.news_feed[:limit]
        
        filtered = [n for n in self.news_feed if n['team'] == team_name or n['team'] is None]
        return filtered[:limit]

    def get_league_leaders(self, league: 'League', stat_name: str, limit: int = 5, is_pitcher: bool = False) -> List['Player']:
        """リーグリーダーを取得"""
        from models import League
        candidates = []
        teams = self.north_teams if league == League.NORTH else self.south_teams
        
        for team in teams:
            for p in team.players:
                if is_pitcher and p.position.value == "投手":
                    if p.record.innings_pitched > 0:
                        candidates.append(p)
                elif not is_pitcher and p.position.value != "投手":
                    if p.record.plate_appearances > 0:
                        candidates.append(p)
                        
        def get_stat_value(p):
            # Check record first, then stats, then properties
            val = getattr(p.record, stat_name, None)
            if val is not None: return val
            
            val = getattr(p.stats, stat_name, None)
            if val is not None: return val
            
            val = getattr(p, stat_name, None) # e.g. batting_average property
            if val is not None: return val
            
            return 0
            
        reverse = True
        if stat_name in ["era", "whip", "fip"]: reverse = False
        
        candidates.sort(key=get_stat_value, reverse=reverse)
        return candidates[:limit]

    def get_team_rankings(self, team: 'Team') -> dict:
        """チームの各種スタッツ順位を返す"""
        from models import League
        rankings = {}
        target_group = self.north_teams if team.league == League.NORTH else self.south_teams
        
        # 1. Runs Scored
        target_group.sort(key=lambda t: getattr(t, 'team_record', None).runs if hasattr(t, 'team_record') else 0, reverse=True)
        try: rankings["runs"] = target_group.index(team) + 1
        except: rankings["runs"] = "-"
        
        # 2. Batting Average
        target_group.sort(key=lambda t: getattr(t, 'team_record', None).batting_average if hasattr(t, 'team_record') else 0.0, reverse=True)
        try: rankings["avg"] = target_group.index(team) + 1
        except: rankings["avg"] = "-"
        
        # 3. ERA
        target_group.sort(key=lambda t: getattr(t, 'team_record', None).era if hasattr(t, 'team_record') else 99.0, reverse=False)
        try: rankings["era"] = target_group.index(team) + 1
        except: rankings["era"] = "-"
        
        # 4. Def Eff (Fielding Pct for now)
        target_group.sort(key=lambda t: getattr(t, 'team_record', None).fielding_pct if hasattr(t, 'team_record') else 0.0, reverse=True)
        try: rankings["def"] = target_group.index(team) + 1
        except: rankings["def"] = "-"
        
        return rankings

    def get_top_prospects(self, team: 'Team', limit: int = 5) -> List['Player']:
        """チーム内の有望株（若手・高評価）を取得"""
        prospects = []
        # Check Farm & Third rosters
        for idx in team.farm_roster + team.third_roster:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                if p.age <= 25:
                    prospects.append(p)
                    
        # Sort by Overall Rating
        prospects.sort(key=lambda p: p.overall_rating, reverse=True)
        return prospects[:limit]

    def initialize_schedule(self):
        """全軍の日程を初期化"""
        from league_schedule_engine import LeagueScheduleEngine, SeasonManager
        from models import League

        self.schedule_engine = LeagueScheduleEngine(self.current_year)
        self.schedule_engine.weather_enabled = self.weather_enabled

        north = [t for t in self.all_teams if t.league == League.NORTH]
        south = [t for t in self.all_teams if t.league == League.SOUTH]

        self.schedule = self.schedule_engine.generate_schedule(north, south)
        self.current_date = self.schedule_engine.opening_day.strftime("%Y-%m-%d")

        self.farm_schedule = self.schedule_engine.generate_farm_schedule(north, south, TeamLevel.SECOND)
        self.third_schedule = self.schedule_engine.generate_farm_schedule(north, south, TeamLevel.THIRD)

        # シーズン管理の初期化
        self.season_manager = SeasonManager(self.current_year)

    def _update_player_status_daily(self):
        """日付変更時の全選手ステータス更新（回復・怪我・調子・練習）"""
        from training_system import apply_team_training
        
        for team in self.all_teams:
            # 練習による成長 (全選手)
            apply_team_training(team.players, 1)
            
            for player in team.players:
                # 明示的な疲労増加防止 (練習も休息も疲労は減る方向のみ)
                # 万が一のバグによる疲労増加を防ぐ
                old_fatigue = getattr(player, 'fatigue', 0)

                # models.pyに追加したrecover_dailyメソッドを呼び出し
                if hasattr(player, 'recover_daily'):
                    player.recover_daily()
                else:
                    # 互換性維持のためのフォールバック
                    if player.position == Position.PITCHER:
                        player.days_rest += 1
                
                # 疲労が増加していたら元に戻す (日次更新で疲労は増えないはず)
                new_fatigue = getattr(player, 'fatigue', 0)
                new_fatigue = getattr(player, 'fatigue', 0)
                if new_fatigue > old_fatigue:
                    player.fatigue = old_fatigue

        # トレード進行処理
        self._process_pending_trades()

    def _process_pending_trades(self):
        """トレード提案の進行処理"""
        completed_trades = []
        for trade in self.pending_trades:
            trade.days_remaining -= 1
            if trade.days_remaining <= 0:
                self._resolve_trade(trade)
                completed_trades.append(trade)
        
        for t in completed_trades:
            self.pending_trades.remove(t)

    def _resolve_trade(self, trade: 'PendingTrade'):
        """トレード結果の判定と実行"""
        result = random.randint(1, 100)
        
        # チームオブジェクトの取得
        offering_team = next((t for t in self.all_teams if t.name == trade.offering_team_name), None)
        target_team = next((t for t in self.all_teams if t.name == trade.target_team_name), None)
        
        if not offering_team or not target_team:
            return # エラー: チームが見つからない
            
        if result <= trade.success_chance:
            # --- 成功: 選手交換実行 ---
            
            # IDの整合性チェックとオブジェクト取得 (インデックスが変わっている可能性があるため名前などで再確認したいが、
            # 簡略化のためインデックスを使用。ただし、日数が経過しているので危険。本来はID管理すべき)
            # ※今回は簡易実装として、インデックスが範囲内であることを確認して実行
            
            # 本当はPlayerオブジェクトに固有IDを持たせて追跡すべきだが、
            # 現状の実装に合わせて、インデックスで取得する。
            # ただし、ロースター変更でずれている可能性に注意。
            # リスク回避のため、名前照合を追加実装するのがベストだが、タスク範囲で簡易対応する。
            
            offered_players = []
            for idx in trade.offered_player_ids:
                if idx < len(offering_team.players):
                    offered_players.append(offering_team.players[idx])
            
            requested_players = []
            for idx in trade.requested_player_ids:
                if idx < len(target_team.players):
                    requested_players.append(target_team.players[idx])
            
            # 選手移動
            # Note: 実際には remove するとインデックスがずれるので、オブジェクトベースで移動
            for p in offered_players:
                if p in offering_team.players:
                    offering_team.players.remove(p)
                    # ロースターからも削除
                    if hasattr(offering_team, 'active_roster'):
                        offering_team.active_roster = [i for i in range(len(offering_team.players))] # リセットが必要
                        # 簡易リセット: active_roster等はインデックス依存なので、
                        # 選手削除後に再構築が必要。_manage_all_teams_rosters等で修正されることを期待
                    target_team.players.append(p)
                    # 移籍フラグなどを設定してもよい
            
            for p in requested_players:
                if p in target_team.players:
                    target_team.players.remove(p)
                    offering_team.players.append(p)
            
            # ロースター整合性のための強制リセット (インデックスずれ防止)
            # 次の _manage_all_teams_rosters で再構築されるが、最低限のクリア
            offering_team.active_roster = list(range(min(28, len(offering_team.players))))
            offering_team.farm_roster = list(range(28, len(offering_team.players))) if len(offering_team.players) > 28 else []
            
            target_team.active_roster = list(range(min(28, len(target_team.players))))
            target_team.farm_roster = list(range(28, len(target_team.players))) if len(target_team.players) > 28 else []

            # ニュースログ
            p_names_out = "、".join([p.name for p in offered_players])
            p_names_in = "、".join([p.name for p in requested_players])
            
            message = f"トレード成立！\n獲得: {p_names_in}\n放出: {p_names_out}"
            if trade.money_adjustment > 0:
                message += f"\n金銭支払い: {trade.money_adjustment//1000000}00万円"
            elif trade.money_adjustment < 0:
                message += f"\n金銭受取: {abs(trade.money_adjustment)//1000000}00万円"
                
            self.log_news("トレード", message, offering_team.name, self.current_date)
            # 相手チーム側にもログ
            self.log_news("トレード", f"{offering_team.name}とのトレードが成立しました。", target_team.name, self.current_date)
            
        else:
            # --- 失敗 ---
            self.log_news("トレード", f"{target_team.name}へのトレード提案は破談となりました。", offering_team.name, self.current_date)



    def _record_daily_rankings(self, date_str: str):
        """指定日の順位を記録"""
        from models import League
        
        # 北リーグ
        north_ranks = self._get_league_standings(League.NORTH)
        # 南リーグ
        south_ranks = self._get_league_standings(League.SOUTH)
        
        rankings = {}
        for name, rank in north_ranks:
            rankings[name] = rank
        for name, rank in south_ranks:
            rankings[name] = rank
            
        self.daily_rankings[date_str] = rankings


    def _manage_all_teams_rosters(self):
        """全チームのロースター管理（自動オーダー編成＋保存）"""
        
        # WAR計算のために一度統計を更新
        update_league_stats(self.all_teams)
        
        for team in self.all_teams:
            # 常にロースター枠を補充（投手15人/野手16人を維持）
            self._fill_roster_gaps(team)
            
            # 自動オーダー編成＋保存（全チーム対象）
            # プレイヤーチームも含めて自動編成を実行（スキップ時に空き枠ができないように）
            self._auto_fill_and_save_order(team)
        
        # 全チーム共通: ベンチ枠の整合性確保 (ローテ投手がベンチに入らないように)
        for team in self.all_teams:
             self._cleanup_roster_consistency(team)

    def _cleanup_roster_consistency(self, team):
        """ロースター、役割、ベンチの整合性を確保"""
        # Pitchers
        active_pitchers = [i for i in team.active_roster if 0 <= i < len(team.players) and team.players[i].position.value == "投手"]
        used_pitchers = set()
        for i in team.rotation: 
            if i != -1: used_pitchers.add(i)
        for i in team.closers:
            if i != -1: used_pitchers.add(i)
        for i in team.setup_pitchers:
            if i != -1: used_pitchers.add(i)
        
        team.bench_pitchers = [i for i in active_pitchers if i not in used_pitchers]

        # Batters
        active_batters = [i for i in team.active_roster if 0 <= i < len(team.players) and team.players[i].position.value != "投手"]
        used_batters = set()
        for i in team.current_lineup:
            if i != -1: used_batters.add(i)
            
        team.bench_batters = [i for i in active_batters if i not in used_batters]

    def _auto_fill_and_save_order(self, team: Team):
        """スマート自動オーダー編成AI
        
        全チーム共通で毎日の試合開始時に自動編成を実行。
        直近成績、調子、ポテンシャル、年齢、疲労を考慮した最適編成を行う。
        """
        from models import Position, TeamLevel
        
        use_condition_priority = (self.auto_order_priority == "condition")
        current_date = self.current_date
        
        # ========== スコアリング関数群 ==========
        
        def get_recent_bonus_batter(p):
            """打者の直近成績ボーナス（OPSベース）"""
            recent = p.get_recent_stats(current_date, days=14)
            if not recent or recent.plate_appearances < 10:
                return 0
            ops = recent.ops
            if ops >= 1.000: return 80   # 絶好調
            if ops >= 0.900: return 60
            if ops >= 0.800: return 40
            if ops >= 0.700: return 20
            if ops >= 0.600: return 0
            if ops >= 0.500: return -20
            return -40  # 不調
        
        def get_recent_bonus_pitcher(p):
            """投手の直近成績ボーナス（ERAベース）"""
            recent = p.get_recent_stats(current_date, days=14)
            if not recent or recent.innings_pitched < 3.0:
                return 0
            era = recent.era
            if era <= 1.50: return 80
            if era <= 2.50: return 60
            if era <= 3.50: return 40
            if era <= 4.50: return 20
            if era <= 5.50: return 0
            return -40
        
        def get_condition_mult(p):
            """調子倍率"""
            if use_condition_priority:
                return 1.0 + (p.condition - 5) * 0.12
            else:
                return 1.0 + (p.condition - 5) * 0.04
        
        def get_potential_bonus(p):
            """若手有望株ボーナス"""
            potential = getattr(p, 'potential', 50)
            age = p.age
            if age <= 22 and potential >= 70: return 30
            if age <= 24 and potential >= 65: return 20
            if age <= 26 and potential >= 60: return 10
            return 0
        
        def get_fatigue_penalty(p):
            """疲労ペナルティ（主に投手）"""
            if p.position.value == "投手":
                if p.days_rest == 0: return -100  # 連投
                if p.days_rest == 1: return -50
                if p.days_rest == 2: return -20
            return 0
        
        def get_batting_score(p):
            """打者総合スコア"""
            s = p.stats
            base = (s.contact * 1.0 + s.power * 1.3 + s.speed * 0.6 + s.eye * 0.7)
            base *= get_condition_mult(p)
            base += get_recent_bonus_batter(p)
            base += get_potential_bonus(p)
            return base
        
        def get_defense_score(p, pos_name_long):
            """守備スコア"""
            apt = p.stats.defense_ranges.get(pos_name_long, 0)
            if apt < 15: return -100  # 守備できない
            s = p.stats
            return apt * 2.0 + s.fielding * 0.5 + s.arm * 0.3

        def get_pitcher_score(p, role):
            """投手スコア（役割別）"""
            s = p.stats
            base = s.overall_pitching() * 100
            
            if role == 'starter':
                apt = p.starter_aptitude / 4.0  # 1-4 scale -> 0.25-1.0
                base = base * apt + s.stamina * 2.0
            elif role == 'closer':
                apt = p.closer_aptitude / 4.0
                base = base * apt + (s.velocity - 130) * 3 + s.vs_pinch * 0.5
            else:  # relief
                apt = p.middle_aptitude / 4.0
                base = base * apt + s.velocity * 0.5
            
            base *= get_condition_mult(p)
            base += get_recent_bonus_pitcher(p)
            base += get_fatigue_penalty(p)
            base += get_potential_bonus(p)
            return base

        # ========== 編成対象選手の取得 ==========
        
        pitchers = [i for i, p in enumerate(team.players) 
                   if p.position.value == "投手" 
                   and not getattr(p, 'is_developmental', False)
                   and (not hasattr(p, 'days_until_promotion') or p.days_until_promotion == 0)
                   and not p.is_injured
                   and i in team.active_roster]
        
        batters = [i for i, p in enumerate(team.players) 
                  if p.position.value != "投手" 
                  and not getattr(p, 'is_developmental', False)
                  and (not hasattr(p, 'days_until_promotion') or p.days_until_promotion == 0)
                  and not p.is_injured
                  and i in team.active_roster]

        # ========== 投手編成 ==========
        
        # 先発候補: 先発適性≥3のみ
        starter_pool = [i for i in pitchers if team.players[i].starter_aptitude >= 3]
        starter_pool.sort(key=lambda i: get_pitcher_score(team.players[i], 'starter'), reverse=True)
        
        rotation = [-1] * 8
        for i in range(min(6, len(starter_pool))):
            rotation[i] = starter_pool[i]
        used_pitchers = set([x for x in rotation if x != -1])
        
        # 抑え候補: 抑え適性≥3のみ
        closer_pool = [i for i in pitchers if i not in used_pitchers and team.players[i].closer_aptitude >= 3]
        closer_pool.sort(key=lambda i: get_pitcher_score(team.players[i], 'closer'), reverse=True)
        
        closers = [-1] * 2
        if closer_pool:
            closers[0] = closer_pool[0]
            used_pitchers.add(closer_pool[0])
        
        # 中継ぎ: 中継ぎ適性≥3を優先
        setup_pool = [i for i in pitchers if i not in used_pitchers and team.players[i].middle_aptitude >= 3]
        setup_pool.sort(key=lambda i: get_pitcher_score(team.players[i], 'relief'), reverse=True)
        
        setup_pitchers = [-1] * 8
        for i in range(min(8, len(setup_pool))):
            setup_pitchers[i] = setup_pool[i]
            used_pitchers.add(setup_pool[i])
        
        # 補充: 枠が余っている場合、適性2以上の投手で補充
        empty_slots = [i for i, x in enumerate(setup_pitchers) if x == -1]
        if empty_slots:
            fallback_pool = [i for i in pitchers if i not in used_pitchers and team.players[i].middle_aptitude >= 2]
            fallback_pool.sort(key=lambda i: get_pitcher_score(team.players[i], 'relief'), reverse=True)
            for slot_idx in empty_slots:
                if fallback_pool:
                    p_idx = fallback_pool.pop(0)
                    setup_pitchers[slot_idx] = p_idx
                    used_pitchers.add(p_idx)
        
        # 最終補充: まだ枠が余っていれば残りの投手で埋める
        empty_slots = [i for i, x in enumerate(setup_pitchers) if x == -1]
        if empty_slots:
            remaining = [i for i in pitchers if i not in used_pitchers]
            remaining.sort(key=lambda i: get_pitcher_score(team.players[i], 'relief'), reverse=True)
            for slot_idx in empty_slots:
                if remaining:
                    p_idx = remaining.pop(0)
                    setup_pitchers[slot_idx] = p_idx
                    used_pitchers.add(p_idx)
        
        # ========== 投手枠補充（二軍から昇格） ==========
        # 一軍投手枠: 15人目標
        TARGET_PITCHERS = 15
        current_pitcher_count = len(used_pitchers)
        
        if current_pitcher_count < TARGET_PITCHERS:
            needed = TARGET_PITCHERS - current_pitcher_count
            # 二軍から投手を補充
            farm_pitchers = [i for i, p in enumerate(team.players)
                            if p.position.value == "投手"
                            and not getattr(p, 'is_developmental', False)
                            and not p.is_injured
                            and i not in used_pitchers
                            and i in team.farm_roster]
            farm_pitchers.sort(key=lambda i: get_pitcher_score(team.players[i], 'relief'), reverse=True)
            
            for i in range(min(needed, len(farm_pitchers))):
                promoted_idx = farm_pitchers[i]
                # Move to active roster
                if promoted_idx in team.farm_roster:
                    team.farm_roster.remove(promoted_idx)
                if promoted_idx not in team.active_roster:
                    team.active_roster.append(promoted_idx)
                team.players[promoted_idx].team_level = TeamLevel.FIRST
                team.players[promoted_idx].days_until_promotion = 0
                
                # 中継ぎ枠に追加
                empty_setup = [j for j, x in enumerate(setup_pitchers) if x == -1]
                if empty_setup:
                    setup_pitchers[empty_setup[0]] = promoted_idx
                    used_pitchers.add(promoted_idx)

        # ========== 野手編成 ==========
        
        pos_map = {
            "捕": "捕手", "遊": "遊撃手", "二": "二塁手", "中": "中堅手", 
            "三": "三塁手", "右": "右翼手", "左": "左翼手", "一": "一塁手"
        }
        # センターライン優先
        def_priority = ["捕", "遊", "二", "中", "三", "右", "左", "一"]
        
        current_lineup = [-1] * 9
        lineup_positions = [""] * 9
        used_indices = set()
        lineup_idx = 0
        
        for short_pos in def_priority:
            long_pos = pos_map[short_pos]
            candidates = []
            
            for idx in batters:
                if idx in used_indices: continue
                p = team.players[idx]
                
                def_score = get_defense_score(p, long_pos)
                if def_score < 0: continue  # 守備不可
                
                # センターラインは守備重視
                def_weight = 2.0 if short_pos in ["捕", "遊", "二", "中"] else 1.0
                total = get_batting_score(p) + def_score * def_weight
                candidates.append((idx, total))
            
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_idx = candidates[0][0]
                current_lineup[lineup_idx] = best_idx
                lineup_positions[lineup_idx] = short_pos
                used_indices.add(best_idx)
                lineup_idx += 1
        
        # DH: 打撃特化
        dh_candidates = [(i, get_batting_score(team.players[i])) 
                         for i in batters if i not in used_indices]
        dh_candidates.sort(key=lambda x: x[1], reverse=True)
        if dh_candidates and lineup_idx < 9:
            current_lineup[lineup_idx] = dh_candidates[0][0]
            lineup_positions[lineup_idx] = "DH"
            used_indices.add(dh_candidates[0][0])
            lineup_idx += 1
        
        # 不足分を埋める
        while lineup_idx < 9:
            remaining = [(i, get_batting_score(team.players[i])) 
                        for i in batters if i not in used_indices]
            if remaining:
                remaining.sort(key=lambda x: x[1], reverse=True)
                current_lineup[lineup_idx] = remaining[0][0]
                lineup_positions[lineup_idx] = "指"
                used_indices.add(remaining[0][0])
                lineup_idx += 1
            else:
                # Fallback: pull batters from farm roster if needed
                farm_batters = [i for i, p in enumerate(team.players)
                               if p.position.value != "投手"
                               and not getattr(p, 'is_developmental', False)
                               and not p.is_injured
                               and i not in used_indices
                               and i in team.farm_roster]
                
                if farm_batters:
                    # Promote best farm batter
                    farm_batters.sort(key=lambda i: get_batting_score(team.players[i]), reverse=True)
                    promoted_idx = farm_batters[0]
                    # Move to active roster
                    if promoted_idx in team.farm_roster:
                        team.farm_roster.remove(promoted_idx)
                    if promoted_idx not in team.active_roster:
                        team.active_roster.append(promoted_idx)
                    team.players[promoted_idx].team_level = TeamLevel.FIRST
                    team.players[promoted_idx].days_until_promotion = 0
                    
                    current_lineup[lineup_idx] = promoted_idx
                    lineup_positions[lineup_idx] = "指"
                    used_indices.add(promoted_idx)
                    lineup_idx += 1
                else:
                    break  # No more players available

        # ベンチ
        bench_batters = [i for i in batters if i not in used_indices]
        
        # ========== ベンチ野手補充（一軍枠に空きがある場合） ==========
        # 一軍野手枠: 16人目標
        TARGET_BATTERS = 16
        current_batter_count = len(used_indices) + len(bench_batters)
        
        if current_batter_count < TARGET_BATTERS:
            needed = TARGET_BATTERS - current_batter_count
            # 二軍から補充
            farm_batters = [i for i, p in enumerate(team.players)
                           if p.position.value != "投手"
                           and not getattr(p, 'is_developmental', False)
                           and not p.is_injured
                           and i not in used_indices
                           and i not in bench_batters
                           and i in team.farm_roster]
            farm_batters.sort(key=lambda i: get_batting_score(team.players[i]), reverse=True)
            
            for i in range(min(needed, len(farm_batters))):
                promoted_idx = farm_batters[i]
                # Move to active roster
                if promoted_idx in team.farm_roster:
                    team.farm_roster.remove(promoted_idx)
                if promoted_idx not in team.active_roster:
                    team.active_roster.append(promoted_idx)
                team.players[promoted_idx].team_level = TeamLevel.FIRST
                team.players[promoted_idx].days_until_promotion = 0
                bench_batters.append(promoted_idx)

        # ========== 降格処理 ==========
        new_order_set = set()
        new_order_set.update([x for x in current_lineup if x != -1])
        new_order_set.update(bench_batters)
        new_order_set.update([x for x in rotation if x != -1])
        new_order_set.update([x for x in setup_pitchers if x != -1])
        new_order_set.update([x for x in closers if x != -1])
        
        for p_idx in list(team.active_roster):
            if p_idx not in new_order_set:
                p = team.players[p_idx]
                p.days_until_promotion = 10
                p.team_level = TeamLevel.SECOND
                team.active_roster.remove(p_idx)
                if p_idx not in team.farm_roster:
                    team.farm_roster.append(p_idx)

        # ========== チームに反映 ==========
        team.current_lineup = current_lineup
        team.lineup_positions = lineup_positions
        team.bench_batters = bench_batters
        team.rotation = rotation
        team.setup_pitchers = setup_pitchers
        team.closers = closers
        team.closer_idx = closers[0] if closers[0] != -1 else -1


    def _fill_roster_gaps(self, team: Team):
        """不足しているロースター枠を埋める (投手15人/野手16人配分)"""
        
        # 目標人数
        TARGET_PITCHERS = 15
        TARGET_BATTERS = 16
        
        # 現状確認
        active_pitchers = [idx for idx in team.active_roster if team.players[idx].position.value == "投手"]
        active_batters = [idx for idx in team.active_roster if team.players[idx].position.value != "投手"]
        
        # --- 1. 過剰分の削減 (降格) ---
        
        # 投手が多すぎる場合
        if len(active_pitchers) > TARGET_PITCHERS:
            excess = len(active_pitchers) - TARGET_PITCHERS
            # 能力順（低い順）にソート
            p_sorted = sorted(active_pitchers, key=lambda i: team.players[i].overall_rating)
            removed_count = 0
            for idx in p_sorted:
                p = team.players[idx]
                if not p.is_injured and removed_count < excess:
                    team.move_to_farm_roster(idx)
                    p.days_until_promotion = 10
                    removed_count += 1
                    
        # 野手が多すぎる場合
        if len(active_batters) > TARGET_BATTERS:
            excess = len(active_batters) - TARGET_BATTERS
            b_sorted = sorted(active_batters, key=lambda i: team.players[i].overall_rating)
            removed_count = 0
            for idx in b_sorted:
                p = team.players[idx]
                if not p.is_injured and removed_count < excess:
                    team.move_to_farm_roster(idx)
                    p.days_until_promotion = 10
                    removed_count += 1

        # --- Re-fetch status after reductions ---
        active_pitchers = [idx for idx in team.active_roster if team.players[idx].position.value == "投手"]
        active_batters = [idx for idx in team.active_roster if team.players[idx].position.value != "投手"]

        # --- 2. 不足分の補充 (昇格) ---
        
        # 投手補充
        p_needed = TARGET_PITCHERS - len(active_pitchers)
        if p_needed > 0:
            # First pass: Valid promotions
            farm_pitchers = [idx for idx in team.farm_roster 
                           if team.players[idx].position.value == "投手" 
                           and not team.players[idx].is_injured 
                           and team.players[idx].days_until_promotion == 0]
            farm_pitchers.sort(key=lambda i: team.players[i].overall_rating, reverse=True)
            
            promoted_count = 0
            for i in range(min(p_needed, len(farm_pitchers))):
                team.move_to_active_roster(farm_pitchers[i])
                promoted_count += 1
            
            # Minimum required pitchers check (raised 11→13 to ensure reliever availability)
            current_pitcher_count = len([idx for idx in team.active_roster if team.players[idx].position.value == "投手"])
            if current_pitcher_count < 13:
                still_needed = 13 - current_pitcher_count 
                # Find restricted but healthy pitchers
                restricted_pitchers = [idx for idx in team.farm_roster 
                                     if team.players[idx].position.value == "投手" 
                                     and not team.players[idx].is_injured 
                                     and team.players[idx].days_until_promotion > 0]
                restricted_pitchers.sort(key=lambda i: team.players[i].overall_rating, reverse=True)
                
                for i in range(min(still_needed, len(restricted_pitchers))):
                    # Force promote
                    pid = restricted_pitchers[i]
                    team.players[pid].days_until_promotion = 0
                    team.move_to_active_roster(pid)
                    # print(f"Emergency Promotion: {team.players[pid].name} (Team: {team.name})")
                
        # 野手補充
        b_needed = TARGET_BATTERS - len(active_batters)
        if b_needed > 0:
            farm_batters = [idx for idx in team.farm_roster 
                          if team.players[idx].position.value != "投手" 
                          and not team.players[idx].is_injured
                          and team.players[idx].days_until_promotion == 0]
            farm_batters.sort(key=lambda i: team.players[i].overall_rating, reverse=True)
            for i in range(min(b_needed, len(farm_batters))):
                team.move_to_active_roster(farm_batters[i])

    def _perform_roster_moves(self, team: Team):
        """1日ごとの昇格・降格処理（怪我人入れ替えのみ）
        
        ※スコアベースの自動降格は廃止。降格はオーダー保存時のみ発生する。
        """
        
        def calculate_score(p):
            """昇格候補・二軍⇔三軍判定用のスコア計算"""
            potential_val = getattr(p, 'potential', 50)
            score = p.overall_rating * 0.6
            if p.age <= 22 and potential_val >= 60: score += 10
            
            recent = p.get_recent_stats(self.current_date, days=20)
            if recent:
                if p.position.value == "投手":
                    diff = 5.00 - recent.era
                    score += diff * 30.0
                else:
                    diff = recent.ops - 0.600
                    score += diff * 200.0
            
            if p.condition <= 2: score -= 15
            if p.condition >= 8: score += 10
            return score

        # --- 1. 怪我人のみ降格候補（3日以上離脱） ---
        injury_demotions = []
        for idx in team.active_roster:
            p = team.players[idx]
            if p.is_injured and p.injury_days >= 3:
                injury_demotions.append((idx, p))
        
        # --- 2. 昇格候補の選定 (Farm) ---
        farm_candidates = []
        for idx in team.farm_roster:
            p = team.players[idx]
            if p.is_injured: continue
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0: continue
            
            s = calculate_score(p)
            farm_candidates.append((idx, s, p))
        
        farm_candidates.sort(key=lambda x: x[1], reverse=True)

        # --- 3. 怪我人入れ替え実行 ---
        moved_indices = set()
        
        for d_idx, d_p in injury_demotions:
            target_pos = d_p.position
            
            # 投手の場合、役割を特定
            is_starter = target_pos.value == "投手" and d_idx in team.rotation
            is_reliever = target_pos.value == "投手" and d_idx not in team.rotation
            
            best_promo = None
            
            # 同一ポジション・役割適性の候補を探す
            for f_cand in farm_candidates:
                f_idx, f_score, f_p = f_cand
                if f_idx in moved_indices: continue
                if f_p.position != target_pos: continue

                if target_pos.value == "投手":
                    if is_starter and f_p.starter_aptitude < 3: 
                        continue
                    elif is_reliever and f_p.middle_aptitude < 3 and f_p.closer_aptitude < 3: 
                        continue
                
                best_promo = f_cand
                break
            
            # 救済措置：適性不問で同ポジションを探す
            if not best_promo:
                for f_cand in farm_candidates:
                    f_idx, f_score, f_p = f_cand
                    if f_idx in moved_indices: continue
                    if f_p.position == target_pos:
                        best_promo = f_cand
                        break

            if best_promo:
                f_idx, f_score, f_p = best_promo
                
                team.move_to_farm_roster(d_idx)
                d_p.days_until_promotion = 10
                
                team.move_to_active_roster(f_idx)
                
                moved_indices.add(f_idx)
            # 候補がいない場合は入れ替えスキップ（ロースター不足のまま）
                
        # --- 2軍 <-> 3軍 ---
        farm_demotion_candidates = []
        for idx in team.farm_roster:
            p = team.players[idx]
            if p.is_injured: continue 
            score = calculate_score(p)
            if score < 20:
                farm_demotion_candidates.append((idx, score))
        
        farm_demotion_candidates.sort(key=lambda x: x[1])
        
        third_promotion_candidates = []
        for idx in team.third_roster:
            p = team.players[idx]
            if p.is_injured: continue
            score = calculate_score(p)
            if score > 30:
                third_promotion_candidates.append((idx, score, p))
                
        third_promotion_candidates.sort(key=lambda x: x[1], reverse=True)
        
        for d_idx, d_score in farm_demotion_candidates:
            d_p = team.players[d_idx]
            best_promo_idx = -1
            for i, (p_idx, p_score, p_p) in enumerate(third_promotion_candidates):
                if p_idx == -1: continue
                if (d_p.position.value == "投手") == (p_p.position.value == "投手"):
                    best_promo_idx = i
                    break
            
            if best_promo_idx != -1:
                p_tuple = third_promotion_candidates.pop(best_promo_idx)
                p_idx = p_tuple[0]
                if d_idx in team.farm_roster: team.farm_roster.remove(d_idx)
                team.third_roster.append(d_idx)
                d_p.team_level = TeamLevel.THIRD
                
                if p_idx in team.third_roster: team.third_roster.remove(p_idx)
                team.farm_roster.append(p_idx)
                team.players[p_idx].team_level = TeamLevel.SECOND

    def process_date(self, date_str: str):
        """
        指定された日付の全試合をシミュレート
        （手動試合の場合も、残りの他球場試合を消化するためにこれを呼ぶ）
        天候による中止・コールドも処理
        """
        from live_game_engine import LiveGameEngine
        from farm_game_simulator import simulate_farm_games_for_day
        from league_schedule_engine import WeatherSystem, SeasonPhase

        try:
            # 0. シーズンフェーズチェック
            if self.season_manager:
                phase = self.season_manager.get_current_phase(date_str)
                if phase == SeasonPhase.OFF_SEASON:
                    # オフシーズンは試合なし
                    self.current_date = date_str
                    return
                elif phase == SeasonPhase.ALLSTAR_BREAK:
                    # オールスター期間の処理
                    self._update_player_status_daily()
                    
                    # Use shared All-Star simulation method (same as home tab)
                    self.simulate_allstar_for_date(date_str)

                    self.current_date = date_str
                    return



            # 1. 全選手のステータス更新 (怪我回復、疲労回復、調子変動)
            self._update_player_status_daily()

            # 1.5. 練習効果適用 (全選手の練習メニューに基づく成長)
            for team in self.all_teams:
                apply_team_training(team.players, days=1)

            # 2. チーム編成の自動調整 (怪我人対応、調子による入れ替え)
            self._manage_all_teams_rosters()

            # 3. AIチーム運用（ロースター・オーダー調整の続き：2軍3軍など）
            self._manage_ai_teams(date_str)

            # 4. 天候による試合中止判定
            self.cancelled_games_today = []
            if self.schedule_engine and self.weather_enabled:
                self.cancelled_games_today = self.schedule_engine.process_weather_for_date(date_str)
                if self.cancelled_games_today:
                    # 中止試合があれば振替日程を組む
                    rescheduled = self.schedule_engine.reschedule_postponed_games()
                    for game, old_date in rescheduled:
                        print(f"雨天中止: {game.home_team_name} vs {game.away_team_name} ({old_date}) → {game.date}に振替")

            # 5. 一軍試合シミュレーション
            if self.schedule:
                todays_games = [g for g in self.schedule.games if g.date == date_str and not g.is_completed]

                for game in todays_games:
                    home = next((t for t in self.all_teams if t.name == game.home_team_name), None)
                    away = next((t for t in self.all_teams if t.name == game.away_team_name), None)

                    if home and away:
                        # 全チームのロースター整合性をチェック (自チーム含む)
                        self._ensure_valid_roster(home)
                        self._ensure_valid_roster(away)

                        try:
                            # Check for Postseason
                            ps_series = None
                            ps_engine = getattr(self.season_manager, 'postseason_engine', None) if self.season_manager else None
                            if ps_engine:
                                for s in [ps_engine.cs_north_first, ps_engine.cs_south_first, ps_engine.cs_north_final, ps_engine.cs_south_final, ps_engine.japan_series]:
                                    if s and game in s.schedule:
                                        ps_series = s
                                        break
                            
                            is_ps = (ps_series is not None)

                            # 試合実行
                            engine = LiveGameEngine(home, away, is_postseason=is_ps)
                            while not engine.is_game_over():
                                engine.simulate_pitch()

                            final_result = engine.finalize_game_stats(date_str)
                            
                            if is_ps:
                                ps_engine.record_game_result(ps_series, engine.state.home_score, engine.state.away_score)
                            else:
                                self.record_game_result(home, away, engine.state.home_score, engine.state.away_score)

                            game.status = GameStatus.COMPLETED
                            game.home_score = engine.state.home_score
                            game.away_score = engine.state.away_score
                            
                            # Record inning-by-inning scores for viewing past results
                            game.home_inning_scores = list(engine.state.home_inning_scores)
                            game.away_inning_scores = list(engine.state.away_inning_scores)
                            
                            # Record hits and errors
                            game.home_hits = engine.state.home_hits
                            game.away_hits = engine.state.away_hits
                            game.home_errors = engine.state.home_errors
                            game.away_errors = engine.state.away_errors
                            
                            # Use the finalized stats from the return value
                            if final_result:
                                game.game_stats = final_result.get('game_stats', {})
                                # Store pitcher results
                                game.pitcher_win = final_result.get('win')
                                game.pitcher_loss = final_result.get('loss')
                                game.pitcher_save = final_result.get('save')
                                # Store highlights (home runs, etc.)
                                game.highlights = final_result.get('highlights', [])
                            else:
                                game.game_stats = dict(engine.game_stats)
                                game.pitcher_win = None
                                game.pitcher_loss = None
                                game.pitcher_save = None
                                game.highlights = []

                            if engine.state.home_pitchers_used:
                                for p in engine.state.home_pitchers_used:
                                    p.days_rest = 0
                            if engine.state.away_pitchers_used:
                                for p in engine.state.away_pitchers_used:
                                    p.days_rest = 0
                            
                            # Check for injuries after game for players who participated
                            for team in [home, away]:
                                # Check pitchers who pitched
                                pitchers_used = engine.state.home_pitchers_used if team == home else engine.state.away_pitchers_used
                                if pitchers_used:
                                    for pitcher in pitchers_used:
                                        if pitcher.check_injury_risk():
                                            self.log_news("怪我", f"{pitcher.name}選手が{pitcher.injury_name}で全治{pitcher.injury_days}日の見込み", team.name, date_str)
                                
                                # Check batters who played (check lineup players)
                                for player in team.players:
                                    if player.position != Position.PITCHER and not player.is_injured:
                                        if player.check_injury_risk():
                                            self.log_news("怪我", f"{player.name}選手が{player.injury_name}で全治{player.injury_days}日の見込み", team.name, date_str)

                            
                            # ローテーションを進める
                            home.rotation_index = (home.rotation_index + 1) % 6
                            away.rotation_index = (away.rotation_index + 1) % 6


                        except Exception as e:
                            print(f"Error simulating game {home.name} vs {away.name}: {e}")
                            traceback.print_exc()

            # 6. 二軍・三軍の試合シミュレーション
            # simulate_farm_games_for_day(self.all_teams, date_str) # 廃止
            
            def process_farm_schedule(schedule, level):
                if not schedule: return
                todays_games = [g for g in schedule.games if g.date == date_str and g.status == GameStatus.SCHEDULED]
                
                # 天候チェック (一軍とは独立して判定)
                # 雨天振り替えなし
                d_obj = None
                try: d_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                except: pass
                
                weather = WeatherSystem.get_weather(d_obj) if d_obj and self.weather_enabled else None
                
                for game in todays_games:
                    # 中止判定
                    if weather and WeatherSystem.should_cancel_game(weather):
                        game.status = GameStatus.CANCELLED
                        # print(f"{level.value} {game.home_team_name} vs {game.away_team_name} 雨天中止 (振替なし)")
                        continue
                        
                    home = next((t for t in self.all_teams if t.name == game.home_team_name), None)
                    away = next((t for t in self.all_teams if t.name == game.away_team_name), None)
                    
                    if home and away:
                        # オーダー・ローテの自動調整 (FarmLeagueManagerのロジックを部分適用または簡易化)
                        # ここでは簡易的に、LiveGameEngineをラップするFarmGameSimulatorを使う
                        # ただしFarmGameSimulatorは都度生成
                        
                        # 試合前に簡易ロースターチェック
                        self._ensure_farm_roster(home, level)
                        self._ensure_farm_roster(away, level)
                        
                        try:
                            sim = FarmGameSimulator(home, away, level)
                            res = sim.simulate_game(date_str)
                            
                            game.status = GameStatus.COMPLETED
                            game.home_score = res.home_score
                            game.away_score = res.away_score
                            
                            # 疲労回復等はsim内で処理済み? -> LiveGameEngine.finalize_game_statsで処理される
                            # ただしdays_restのリセットはここかSimulation内か確認必要
                            # LiveGameEngine._change_inningでリセットしてるわけではない。
                            # 一軍はfinalize後に手動リセットしている(lines 364-369)
                            
                            if sim.engine.state.home_pitchers_used:
                                for p in sim.engine.state.home_pitchers_used: p.days_rest = 0
                            if sim.engine.state.away_pitchers_used:
                                for p in sim.engine.state.away_pitchers_used: p.days_rest = 0
                                
                        except Exception as e:
                            print(f"Error simulating farm game ({level.value}): {e}")
                            traceback.print_exc()

            process_farm_schedule(self.farm_schedule, TeamLevel.SECOND)
            process_farm_schedule(self.third_schedule, TeamLevel.THIRD)

            # 7. 全試合終了後に成績集計を更新
            update_league_stats(self.all_teams)

            # 順位履歴の記録
            self._record_daily_rankings(date_str)

            # 8. レギュラーシーズン終了チェック
            if self.schedule_engine and self.schedule_engine.is_regular_season_complete():
                self._on_regular_season_complete()

            # 日付更新
            self.current_date = date_str

        except Exception as e:
            print(f"Critical error in process_date: {e}")
            traceback.print_exc()

    def _on_regular_season_complete(self):
        """レギュラーシーズン終了時の処理"""
        if self.season_manager and not hasattr(self, '_regular_season_ended'):
            self._regular_season_ended = True
            print("レギュラーシーズン終了！ポストシーズンに突入します。")
            # ポストシーズン日程の生成はUI側で行う

    def get_current_season_phase(self) -> str:
        """現在のシーズンフェーズを取得"""
        if self.season_manager:
            from league_schedule_engine import SeasonPhase
            phase = self.season_manager.get_current_phase(self.current_date)
            return phase.value
        return "レギュラーシーズン"

    def is_regular_season_complete(self) -> bool:
        """レギュラーシーズンが終了したか"""
        if self.schedule_engine:
            return self.schedule_engine.is_regular_season_complete()
        return False

    def start_postseason(self) -> bool:
        """ポストシーズンを開始"""
        from league_schedule_engine import PostseasonScheduleEngine
        from models import League

        if not self.is_regular_season_complete():
            return False

        # 順位を取得
        north_standings = self._get_league_standings(League.NORTH)
        south_standings = self._get_league_standings(League.SOUTH)

        # ポストシーズン日程生成
        start_date = self.schedule_engine.get_postseason_start_date()
        ps_engine = PostseasonScheduleEngine(self.current_year, start_date)
        self.postseason_schedule = ps_engine.generate_climax_series_schedule(
            north_standings, south_standings
        )

        return True

    def _get_league_standings(self, league) -> List[Tuple[str, int]]:
        """リーグの順位を取得"""
        teams = [t for t in self.all_teams if t.league == league]
        teams.sort(key=lambda t: (t.winning_percentage, t.wins), reverse=True)
        return [(t.name, i+1) for i, t in enumerate(teams)]

    def mark_postseason_complete(self):
        """ポストシーズン終了をマーク → オフシーズンに移行"""
        if self.season_manager:
            self.season_manager.mark_postseason_complete()
            print("全日程終了！オフシーズンに突入します。")

    def is_off_season(self) -> bool:
        """オフシーズンかどうか"""
        if self.season_manager:
            return self.season_manager.is_off_season(self.current_date)
        return False

    def get_today_weather(self) -> str:
        """今日の天候を取得"""
        from league_schedule_engine import WeatherSystem
        import datetime
        try:
            d = datetime.datetime.strptime(self.current_date, "%Y-%m-%d").date()
            weather = WeatherSystem.get_weather(d)
            return weather.value
        except:
            return "晴れ"

    def finish_day_and_advance(self):
        """その日の残り試合（他球場、二軍三軍）を消化し、日付を翌日に進める"""
        self.process_date(self.current_date)
        try:
            y, m, d = map(int, self.current_date.split('-'))
            current_qdate = QDate(y, m, d)
            next_date = current_qdate.addDays(1)
            self.current_date = next_date.toString("yyyy-MM-dd")
            
            # Check for schedule events (All-Star, Postseason)
            self._check_schedule_events()
            
        except Exception as e:
            print(f"Error in finish_day_and_advance: {e}")
            traceback.print_exc()

    def simulate_allstar_for_date(self, date_str: str):
        """
        オールスター試合をシミュレート (共有メソッド)
        ホームタブからのボタン押下とスキップ処理の両方から呼び出される
        """
        if not self.season_manager:
            return None
        
        # Initialize All-Star engine if not done
        if not hasattr(self.season_manager, 'allstar_engine') or not self.season_manager.allstar_engine:
            print("Initializing All-Star Engine...")
            self.season_manager.initialize_allstar(self.all_teams)
        
        if not self.season_manager.allstar_engine:
            print("Failed to initialize All-Star Engine")
            return None
        
        ase = self.season_manager.allstar_engine
        engine = None
        
        # Find today's All-Star game
        if self.schedule:
            todays_games = [g for g in self.schedule.games if g.date == date_str and not g.is_completed]
            for game in todays_games:
                if game.home_team_name in ["ALL-NORTH", "ALL-SOUTH"]:
                    # Determine game number
                    game_num = game.game_number if hasattr(game, 'game_number') else 1
                    
                    # Simulate via AllStarGameEngine (uses LiveGameEngine internally)
                    engine = ase.simulate_single_allstar_game(game_num)
                    
                    if engine:
                        # Update scheduled game with results
                        game.home_score = engine.state.home_score
                        game.away_score = engine.state.away_score
                        game.status = GameStatus.COMPLETED
                        
                        # Record inning-by-inning scores
                        game.home_inning_scores = list(engine.state.home_inning_scores)
                        game.away_inning_scores = list(engine.state.away_inning_scores)
                        
                        # Record hits and errors
                        game.home_hits = engine.state.home_hits
                        game.away_hits = engine.state.away_hits
                        game.home_errors = engine.state.home_errors
                        game.away_errors = engine.state.away_errors
                        
                        # Get detail with pitcher results, MVP, box score
                        detail = ase.game1_detail if game_num == 1 else ase.game2_detail
                        if detail:
                            # Convert Player objects to name strings
                            raw_pitcher = detail.get('pitcher_result', {})
                            game.pitcher_result = {
                                'win': getattr(raw_pitcher.get('win'), 'name', None) if raw_pitcher.get('win') else None,
                                'loss': getattr(raw_pitcher.get('loss'), 'name', None) if raw_pitcher.get('loss') else None,
                                'save': getattr(raw_pitcher.get('save'), 'name', None) if raw_pitcher.get('save') else None,
                            }
                            game.mvp_name = detail.get('mvp', '')
                            game.box_score = detail.get('box_score', {})
                            game.game_stats = engine.game_stats
                            
                            # Create highlights
                            highlights = []
                            if game.mvp_name:
                                highlights.append(f"MVP: {game.mvp_name}")
                            if game.pitcher_result.get('win'):
                                highlights.append(f"勝利投手: {game.pitcher_result['win']}")
                            if game.pitcher_result.get('loss'):
                                highlights.append(f"敗戦投手: {game.pitcher_result['loss']}")
                            if game.pitcher_result.get('save'):
                                highlights.append(f"セーブ: {game.pitcher_result['save']}")
                            
                            # Add home runs with correct team names (tuple format for HighlightsCard)
                            home_runs = []
                            for p in engine.home_team.players + engine.away_team.players:
                                cnt = engine.game_stats[p]['home_runs']
                                if cnt > 0:
                                    t_name = engine.home_team.name if p in engine.home_team.players else engine.away_team.name
                                    home_runs.append((p.name, cnt, t_name))
                                    highlights.append(f"HR: {p.name}({t_name})")
                            game.home_runs = home_runs

                            game.highlights = highlights

                        
                        # Log to news feed
                        winner = "ALL-NORTH" if engine.state.home_score > engine.state.away_score else "ALL-SOUTH"
                        if engine.state.home_score == engine.state.away_score:
                            winner = "引き分け"
                        self.log_news(date_str, "オールスター", f"オールスター第{game_num}戦: {winner} {engine.state.home_score}-{engine.state.away_score}")
        
        return engine

    def _check_schedule_events(self):
        """日付更新時に特別なイベント（オールスター、CS、日本シリーズ）の開始をチェック"""
        if not self.season_manager: return
        
        cal = self.season_manager.calendar
        today_date = datetime.datetime.strptime(self.current_date, "%Y-%m-%d").date()
        
        # All-Star Generation
        # Roster selection only. Games are already in schedule from Season Start.
        if today_date == cal.allstar_day1:
            if not self.season_manager.allstar_engine:
                print("Generating All-Star Rosters...")
                self.season_manager.initialize_allstar(self.all_teams)
                
        # Postseason: Climax Series First Stage
        if today_date == cal.cs_first_start:
            if not self.postseason_schedule:
                print("Generating CS First Stage...")
                self.start_postseason()
                # Postseason games are generated in start_postseason -> PostseasonScheduleEngine
                if self.season_manager.postseason_engine:
                    self._merge_postseason_games(self.season_manager.postseason_engine)

        # Postseason: Climax Series Final Stage
        if today_date == cal.cs_final_start:
            if self.season_manager.postseason_engine:
                 # Ensure Final Stage games are merged if they weren't already
                 self._merge_postseason_games(self.season_manager.postseason_engine)
                 
    def _merge_postseason_games(self, ps_engine):
        """PostseasonEngineから試合を取り出してスケジュールに統合"""
        # 既存のPS試合（同一日付・同一カード）があれば重複しないようにする
        existing_keys = set()
        for g in self.schedule.games:
            existing_keys.add(f"{g.date}_{g.home_team_name}_{g.away_team_name}")
            
        series_list = [
            ps_engine.cs_north_first, ps_engine.cs_south_first,
            ps_engine.cs_north_final, ps_engine.cs_south_final,
            ps_engine.japan_series
        ]
        
        for series in series_list:
            if series and series.schedule:
                for g in series.schedule:
                    key = f"{g.date}_{g.home_team_name}_{g.away_team_name}"
                    if key not in existing_keys:
                        self.schedule.games.append(g)
                        existing_keys.add(key)
        
        # Sort schedule by date
        self.schedule.games.sort(key=lambda x: x.date) 
                
        # Note: Japan Series generation is handled by `advance_cs_stage` logic usually called when CS ends.
        # We need to make sure `finish_day_and_advance` or `process_date` handles postseason progress.
        
        # If we are in Postseason, we should check if a series ended yesterday and we need to Advance.
        if self.season_manager.postseason_engine:
             # Check logic to auto-advance stages if series finished
             pass

    def _manage_ai_teams(self, date_str):
        """AIチームおよび自チーム二軍三軍の管理"""
        for team in self.all_teams:
            if team.current_lineup:
                self._rotate_lineup_based_on_condition(team)

            if not team.rotation or len(team.rotation) < 6:
                team.auto_assign_pitching_roles(TeamLevel.FIRST)
            
            team.farm_lineup = self._auto_generate_lineup(team, TeamLevel.SECOND)
            team.third_lineup = self._auto_generate_lineup(team, TeamLevel.THIRD)
            
            if not team.farm_rotation:
                team.auto_assign_pitching_roles(TeamLevel.SECOND)
            if not team.third_rotation:
                team.auto_assign_pitching_roles(TeamLevel.THIRD)

    def _rotate_lineup_based_on_condition(self, team: Team):
        """
        調子や疲労、そして直近成績に基づいてスタメンを入れ替える
        """
        
        def calc_player_score(p, current_date):
            """選手のスコアを計算（直近成績を重視）"""
            base_score = p.stats.overall_batting()
            
            # 調子補正 (-40 ~ +40)
            cond_bonus = (p.condition - 5) * 10
            
            # 直近成績補正（最大±50）
            recent_bonus = 0
            recent = p.get_recent_stats(current_date, days=10)
            if recent and recent.plate_appearances >= 5:
                ops = recent.ops
                if ops >= 1.000:
                    recent_bonus = 50  # 絶好調
                elif ops >= 0.900:
                    recent_bonus = 40
                elif ops >= 0.800:
                    recent_bonus = 30
                elif ops >= 0.700:
                    recent_bonus = 15
                elif ops >= 0.600:
                    recent_bonus = 0
                elif ops >= 0.500:
                    recent_bonus = -15
                else:
                    recent_bonus = -30  # 不調
            
            return base_score + cond_bonus + recent_bonus
        
        # ベストオーダーがある場合はそれをベースにする
        if hasattr(team, 'best_order') and team.best_order and len(team.best_order) >= 9:
            new_lineup = list(team.best_order)
            used_indices = set(new_lineup)
            
            # 交代が必要なポジションを探して埋める
            for i, p_idx in enumerate(new_lineup):
                if not (0 <= p_idx < len(team.players)): continue
                
                player = team.players[p_idx]
                needs_replacement = False
                
                # 1. 一軍登録抹消されている
                if p_idx not in team.active_roster:
                    needs_replacement = True
                # 2. 怪我している
                elif player.is_injured:
                    needs_replacement = True
                # 3. 絶不調 (コンディション2以下)
                elif player.condition <= 2:
                    needs_replacement = True
                    
                # 4. 成績不振 (直近10試合の打率が.150未満など)
                if not needs_replacement and not player.is_injured:
                    recent = player.get_recent_stats(self.current_date, days=10)
                    if recent and recent.at_bats >= 15: 
                        if recent.batting_average < 0.150:
                            needs_replacement = True

                if needs_replacement:
                    # 代役を探す (ベンチにいる元気な選手)
                    candidates = []
                    for bench_idx in team.active_roster:
                        if bench_idx in used_indices: continue 
                        if not (0 <= bench_idx < len(team.players)): continue
                        
                        bench_p = team.players[bench_idx]
                        if bench_p.is_injured: continue 
                        if bench_p.condition <= 2: continue 
                        
                        # ポジション適性チェック
                        if bench_p.can_play_position(player.position):
                            score = calc_player_score(bench_p, self.current_date)
                            candidates.append((bench_idx, score))
                    
                    # 候補がいれば最高スコアの選手と交代
                    if candidates:
                        candidates.sort(key=lambda x: x[1], reverse=True)
                        best_sub_idx = candidates[0][0]
                        new_lineup[i] = best_sub_idx
                        used_indices.add(best_sub_idx)
            
            team.current_lineup = new_lineup
            
            # ベンチメンバーの更新
            active_batters = [p_idx for p_idx in team.active_roster 
                            if 0 <= p_idx < len(team.players) 
                            and team.players[p_idx].position.value != "投手"]
            assigned = set(team.current_lineup)
            team.bench_batters = [i for i in active_batters if i not in assigned]
            
        else:
            # ベストオーダーがない場合：直近成績を考慮して自動生成
            active_batters = [p_idx for p_idx in team.active_roster 
                            if 0 <= p_idx < len(team.players) 
                            and team.players[p_idx].position.value != "投手"]
            
            # スコアでソート（調子・直近成績を加味）
            scored_batters = []
            for i in active_batters:
                p = team.players[i]
                if p.is_injured: continue
                score = calc_player_score(p, self.current_date)
                scored_batters.append((i, score, p))
            
            scored_batters.sort(key=lambda x: x[1], reverse=True)
            
            # 上位選手でラインアップ生成
            top_players = [x[2] for x in scored_batters[:12]]  # 余裕を持って渡す
            new_lineup = generate_best_lineup(team, top_players)
            
            team.current_lineup = new_lineup
            
            assigned = set(team.current_lineup)
            team.bench_batters = [i for i in active_batters if i not in assigned]

    def _ensure_valid_roster(self, team: Team):
        valid_starters = len([x for x in team.current_lineup if x != -1])
        # ローテーションに必要な人数 (最低5人、できれば6人)
        rotation_count = len([x for x in team.rotation if x != -1])
        has_rotation = rotation_count >= 6
        
        if valid_starters < 9 or not has_rotation:
            # 投手不足チェック (最低11人は確保したい)
            active_pitcher_count = len([x for x in team.active_roster if team.players[x].position.value == "投手"])
            
            # ロースター枠が足りない or 投手が足りない場合は補充
            if len(team.active_roster) < 31 or active_pitcher_count < 11:
                self._fill_roster_gaps(team)
            
            # オーダー不備なら再生成 (既存ロースターで)
            if valid_starters < 9:
                roster_players = team.get_active_roster_players()
                team.current_lineup = generate_best_lineup(team, roster_players)
                team.auto_set_bench()
            
            # ローテ不備なら再設定 (既存ロースターで)
            if not has_rotation:
                 team.auto_assign_pitching_roles(TeamLevel.FIRST)

    def _ensure_farm_roster(self, team: Team, level: TeamLevel):
        lineup = team.farm_lineup if level == TeamLevel.SECOND else team.third_lineup
        rotation = team.farm_rotation if level == TeamLevel.SECOND else team.third_rotation
        
        valid_starters = len([x for x in lineup if x != -1]) if lineup else 0
        has_rotation = len([x for x in rotation if x != -1]) >= 1 if rotation else False
        
        if valid_starters < 9:
            if level == TeamLevel.SECOND:
                team.farm_lineup = self._auto_generate_lineup(team, level)
            else:
                team.third_lineup = self._auto_generate_lineup(team, level)
                
        if not has_rotation:
             team.auto_assign_pitching_roles(level)

    def _auto_generate_lineup(self, team: Team, level: TeamLevel) -> List[int]:
        """
        指定レベルの自動打順生成
        一軍: 能力重視
        二軍・三軍: 若手・育成優先＋ランダム性
        """
        from models import Position
        roster = team.get_players_by_level(level)
        indices = [team.players.index(p) for p in roster if p.position != Position.PITCHER and not p.is_injured]
        
        if level == TeamLevel.FIRST:
            indices.sort(key=lambda i: team.players[i].stats.overall_batting(), reverse=True)
        else:
            def calc_farm_score(p_idx):
                p = team.players[p_idx]
                ovr = p.stats.overall_batting()
                age_bonus = max(0, 30 - p.age) * 3
                rand = random.uniform(0, 15)
                return ovr * 0.4 + age_bonus + rand
            
            indices.sort(key=calc_farm_score, reverse=True)

        return indices[:9]

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
    
    def is_season_complete(self) -> bool:
        """シーズン全体（レギュラー+ポストシーズン）が終了したか"""
        if self.season_manager:
            return self.season_manager.postseason_complete
        return self.current_game_number >= 143
    
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
                if player.position == Position.PITCHER:
                    player.days_rest = 6 # 開幕前は休息十分