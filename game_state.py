# -*- coding: utf-8 -*-
"""
ゲーム状態管理 (拡張版: 全軍日程管理・AI運用・統括シミュレーション・完全版)
"""
from enum import Enum
from typing import Optional, List
from models import Team, Player, DraftProspect, TeamLevel, Position, generate_best_lineup
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

    def _update_player_status_daily(self):
        """日付変更時の全選手ステータス更新（回復・怪我・調子）"""
        for team in self.all_teams:
            for player in team.players:
                # models.pyに追加したrecover_dailyメソッドを呼び出し
                if hasattr(player, 'recover_daily'):
                    player.recover_daily()
                else:
                    # 互換性維持のためのフォールバック
                    if player.position == Position.PITCHER:
                        player.days_rest += 1

    def _manage_all_teams_rosters(self):
        """全チームのロースター管理（怪我・不調による入れ替え）"""
        for team in self.all_teams:
            # 入れ替え実行 (1軍⇔2軍)
            self._perform_roster_moves(team)
            
            # ロースター枠整理
            team.auto_assign_rosters()
            
            # オーダー生成
            if not team.current_lineup or len(team.current_lineup) < 9:
                team.current_lineup = generate_best_lineup(team, team.get_active_roster_players())
            
            # 投手起用設定
            team.auto_assign_pitching_roles(TeamLevel.FIRST)

    def _perform_roster_moves(self, team: Team):
        """
        怪我・調子・成績に基づく1軍・2軍入れ替えロジック
        """
        active_players = team.get_active_roster_players()
        farm_players = team.get_farm_roster_players()
        
        demote_candidates = []
        promote_candidates = []

        # --- 1. 降格候補の選定 ---
        for p in active_players:
            reason = None
            
            # (A) 怪我人は即降格
            if hasattr(p, 'is_injured') and p.is_injured:
                reason = "injury"
            
            # (B) 超絶不調 (調子1〜2) かつ 実績不足
            elif p.condition <= 2 and p.salary < 50000000: # 高年俸(主力)は我慢する傾向
                reason = "condition"
            
            # (C) 成績不振 (野手: 打率.150以下, 投手: 防御率6.00以上) ※試合数が少ないうちは除外
            elif p.position == Position.PITCHER:
                if p.record.innings_pitched > 10 and p.record.era > 6.00:
                    reason = "stats"
            else:
                if p.record.at_bats > 30 and p.record.batting_average < 0.180:
                    reason = "stats"
            
            if reason:
                demote_candidates.append((p, reason))

        # --- 2. 昇格候補の選定 ---
        # 調子が良い、または2軍で成績が良い選手
        for p in farm_players:
            score = 0
            # 怪我人は論外
            if hasattr(p, 'is_injured') and p.is_injured: continue
            
            # ★追加: 再昇格待機期間中の選手は除外
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0: continue

            # 調子ボーナス
            if p.condition >= 8: score += 50
            elif p.condition <= 3: score -= 50
            
            # 能力ボーナス
            score += p.overall_rating * 0.2
            
            if score > 60: # 一定基準を超えたら候補
                promote_candidates.append((p, score))
        
        # 候補をスコア順にソート
        promote_candidates.sort(key=lambda x: x[1], reverse=True)

        # --- 3. 入れ替え実行 ---
        # ポジションバランスを崩さないように入れ替える (投手⇔投手、野手⇔野手)
        
        pitchers_in_active = len([x for x in active_players if x.position == Position.PITCHER])
        
        for demote_p, reason in demote_candidates:
            # 1軍枠が空になるか、入れ替え候補がいる場合のみ実行
            
            target_pos_type = "PITCHER" if demote_p.position == Position.PITCHER else "FIELDER"
            
            # 交代相手を探す
            replacement = None
            for cand_p, score in promote_candidates:
                cand_pos_type = "PITCHER" if cand_p.position == Position.PITCHER else "FIELDER"
                
                # 同じタイプ(投手/野手)で入れ替え
                if target_pos_type == cand_pos_type:
                    replacement = cand_p
                    break
            
            # 投手の場合、1軍投手が少なすぎると困るので、補充必須
            if target_pos_type == "PITCHER" and pitchers_in_active <= 10 and not replacement:
                continue # 補充できないなら降格させない (怪我でもベンチに置くしかない)
            
            # 入れ替え実行
            try:
                p_idx = team.players.index(demote_p)
                team.remove_from_active_roster(p_idx, TeamLevel.SECOND)
                
                if replacement:
                    r_idx = team.players.index(replacement)
                    team.add_to_active_roster(r_idx)
                    promote_candidates.remove((replacement, score)) # 候補リストから削除
                    if target_pos_type == "PITCHER": pitchers_in_active += 1 
                    
                if target_pos_type == "PITCHER": pitchers_in_active -= 1
                
            except ValueError:
                pass

        # 枠が余っているなら埋める処理
        while team.get_active_roster_count() < 28 and promote_candidates:
            cand_p, score = promote_candidates.pop(0)
            try:
                r_idx = team.players.index(cand_p)
                team.add_to_active_roster(r_idx)
            except:
                pass

    def process_date(self, date_str: str):
        """
        指定された日付の全試合をシミュレート
        （手動試合の場合も、残りの他球場試合を消化するためにこれを呼ぶ）
        """
        from live_game_engine import LiveGameEngine
        from farm_game_simulator import simulate_farm_games_for_day
        
        try:
            # 0. 全選手のステータス更新 (怪我回復、疲労回復、調子変動)
            self._update_player_status_daily()

            # 1. チーム編成の自動調整 (怪我人対応、調子による入れ替え)
            self._manage_all_teams_rosters()

            # 2. AIチーム運用（ロースター・オーダー調整の続き：2軍3軍など）
            self._manage_ai_teams(date_str)

            # 3. 一軍試合シミュレーション
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
                            
                            # 登板した投手の休息日数をリセット (models.pyのrecover_dailyでも処理されるが念のため)
                            if engine.state.home_pitchers_used:
                                for p in engine.state.home_pitchers_used:
                                    p.days_rest = 0
                            if engine.state.away_pitchers_used:
                                for p in engine.state.away_pitchers_used:
                                    p.days_rest = 0
                            
                        except Exception as e:
                            print(f"Error simulating game {home.name} vs {away.name}: {e}")
                            traceback.print_exc()

            # 4. 二軍・三軍の試合シミュレーション
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
            # 1. ロースター整理 (怪我人・不調者の入れ替え) は _perform_roster_moves で実施済み
            
            # 2. スタメンのターンオーバー (疲労・調子による休養)
            if team.current_lineup:
                self._rotate_lineup_based_on_condition(team)

            # 3. 投手起用法の再設定
            if not team.rotation or len(team.rotation) < 6:
                team.auto_assign_pitching_roles(TeamLevel.FIRST)
            
            # 4. 二軍三軍のオーダー・ローテ自動生成
            team.farm_lineup = self._auto_generate_lineup(team, TeamLevel.SECOND)
            team.third_lineup = self._auto_generate_lineup(team, TeamLevel.THIRD)
            
            if not team.farm_rotation:
                team.auto_assign_pitching_roles(TeamLevel.SECOND)
            if not team.third_rotation:
                team.auto_assign_pitching_roles(TeamLevel.THIRD)

    def _rotate_lineup_based_on_condition(self, team: Team):
        """調子や疲労に基づいてスタメンを入れ替える（ベストオーダー優先）"""
        
        # ★追加: ベストオーダーがある場合はそれをベースにする
        if hasattr(team, 'best_order') and team.best_order and len(team.best_order) >= 9:
            # ベストオーダーのコピーを作成
            new_lineup = list(team.best_order)
            
            # 使用済み選手セット（ベンチメンバー選定用）
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
                    
                if needs_replacement:
                    # 代役を探す (ベンチにいる元気な選手)
                    # 同じポジションを守れる選手を優先
                    candidates = []
                    for bench_idx in team.active_roster:
                        if bench_idx in used_indices: continue # 既にオーダーに入っている選手は除外
                        if not (0 <= bench_idx < len(team.players)): continue
                        
                        bench_p = team.players[bench_idx]
                        if bench_p.is_injured: continue
                        if bench_p.condition <= 2: continue # 不調な選手は選ばない
                        
                        # ポジション適性チェック
                        if bench_p.can_play_position(player.position):
                            # スコア計算 (打撃 + 調子)
                            score = bench_p.stats.overall_batting() + (bench_p.condition - 5) * 10
                            candidates.append((bench_idx, score))
                    
                    # 候補がいれば最高スコアの選手と交代
                    if candidates:
                        candidates.sort(key=lambda x: x[1], reverse=True)
                        best_sub_idx = candidates[0][0]
                        new_lineup[i] = best_sub_idx
                        used_indices.add(best_sub_idx)
                        # 元の選手をusedから外す必要はない（どうせ使えないので）
            
            team.current_lineup = new_lineup
            
            # ベンチメンバーの更新
            active_batters = [p_idx for p_idx in team.active_roster 
                            if 0 <= p_idx < len(team.players) 
                            and team.players[p_idx].position.value != "投手"]
            assigned = set(team.current_lineup)
            team.bench_batters = [i for i in active_batters if i not in assigned]
            
        else:
            # 既存ロジック: ベストオーダーがない場合は毎回自動生成
            active_batters = [p_idx for p_idx in team.active_roster 
                            if 0 <= p_idx < len(team.players) 
                            and team.players[p_idx].position.value != "投手"]
            
            # スタメン再生成（調子重視）
            roster_players = [team.players[i] for i in active_batters]
            new_lineup = generate_best_lineup(team, roster_players)
            
            team.current_lineup = new_lineup
            
            assigned = set(team.current_lineup)
            team.bench_batters = [i for i in active_batters if i not in assigned]

    def _ensure_valid_roster(self, team: Team):
        valid_starters = len([x for x in team.current_lineup if x != -1])
        has_rotation = len([x for x in team.rotation if x != -1]) >= 1
        
        if valid_starters < 9 or not has_rotation:
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
                if player.position == Position.PITCHER:
                    player.days_rest = 6 # 開幕前は休息十分