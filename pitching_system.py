# -*- coding: utf-8 -*-
"""
投手起用管理システム (NPB準拠版)
- 6人ローテーション
- 勝ちパターン/同点/ビハインドのリリーフ戦略
- スタミナ・球数・失点に基づく交代判断
"""
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass

if TYPE_CHECKING:
    from models import Team, Player, Position
    from live_game_engine import GameState


class PitcherRole(Enum):
    """投手の役割"""
    STARTER = "先発"
    CLOSER = "抑え"
    SETUP_A = "セットアップA"  # 8回担当
    SETUP_B = "セットアップB"  # 7回担当
    MIDDLE = "中継ぎ"
    LONG = "ロング"
    SPECIALIST = "ワンポイント"


@dataclass
class PitchingContext:
    """投手交代判断に必要な情報をまとめたコンテキスト"""
    inning: int
    outs: int
    score_diff: int  # 正=リード、負=ビハインド
    is_close: bool  # abs(score_diff) <= 3
    is_blowout: bool  # abs(score_diff) >= 5
    current_stamina: float  # 0-100
    pitch_count: int
    runs_allowed: int  # 現投手の失点
    ip_pitched: float  # 現投手の投球回
    runner_on_base: bool
    runner_in_scoring_position: bool
    next_batter_hand: str  # "左" or "右"


class PitchingDirector:
    """
    投手起用を統括するディレクター
    チームごとにインスタンス化し、試合中の投手交代を管理する
    """
    
    # --- 定数 (調整可能なしきい値) ---
    # 先発用（スタミナは球数ベース: 先発70-170球）
    STARTER_STAMINA_CRITICAL = 0  # 球切れで強制交代
    STARTER_PITCH_COUNT_LIMIT = 130  # 球数上限
    STARTER_EARLY_HOOK_RUNS = 6  # 3回以内でこれ以上失点したら降板
    STARTER_BLOWUP_RUNS = 8  # どの回でもこれ以上失点したら降板
    STARTER_QS_STAMINA_ALLOW = 5  # QSペースなら残り5球でも続投
    STARTER_NORMAL_STAMINA_MIN = 10  # 通常時は残り10球で交代検討
    STARTER_LATE_INNING_THRESHOLD = 7  # 終盤とみなす回
    STARTER_LATE_PITCH_COUNT = 115  # 終盤接戦での球数しきい値
    STARTER_CRISIS_STAMINA = 15  # ピンチ時は残り15球で交代
    STARTER_MAX_INNINGS = 9.0  # 先発の最大イニング数
    
    # リリーフ用
    RELIEVER_STAMINA_MIN = 15  # 球数15球未満は交代
    RELIEVER_PITCH_COUNT_LIMIT = 25  # 25球で交代検討
    RELIEVER_ONE_INNING_LIMIT = 0.9  # 基本的に1イニング未満で交代
    RELIEVER_BLOWUP_RUNS = 2  # リリーフが2失点したら要交代
    LONG_RELIEVER_MAX_INNINGS = 3.0  # ロングリリーフの最大イニング数
    
    def __init__(self, team: 'Team', team_level: 'TeamLevel' = None):
        from models import TeamLevel
        self.team = team
        self.team_level = team_level or TeamLevel.FIRST
        self._cached_rotation_pitchers: List['Player'] = []
        self._update_rotation_cache()
        
    def _get_roster_indices(self) -> list:
        """チームレベルに応じたロスターインデックスを返す"""
        from models import TeamLevel
        if self.team_level == TeamLevel.SECOND:
            return self.team.farm_roster
        elif self.team_level == TeamLevel.THIRD:
            return self.team.third_roster
        else:
            return self.team.active_roster
        
    def _update_rotation_cache(self):
        """ローテーション投手のキャッシュを更新"""
        from models import Position, TeamLevel
        self._cached_rotation_pitchers = []
        
        # Use level-appropriate rotation
        if self.team_level == TeamLevel.SECOND:
            rotation = self.team.farm_rotation
        elif self.team_level == TeamLevel.THIRD:
            rotation = self.team.third_rotation
        else:
            rotation = self.team.rotation
        
        if not rotation:
            return
        
        for idx in rotation:
            if 0 <= idx < len(self.team.players):
                p = self.team.players[idx]
                if p.position == Position.PITCHER:
                    self._cached_rotation_pitchers.append(p)
    
    def is_starter(self, pitcher: 'Player') -> bool:
        """選手がローテーション投手かどうか"""
        # First check: Is the pitcher in the rotation cache?
        if pitcher in self._cached_rotation_pitchers:
            return True
        
        # Fallback: Check if this pitcher has starter aptitude (works across all levels)
        if hasattr(pitcher, 'stats') and hasattr(pitcher.stats, 'aptitude_starter'):
            return pitcher.stats.aptitude_starter >= 3  # ◎(4) or 〇(3)
        
        return False
    
    def get_pitcher_role(self, pitcher: 'Player') -> PitcherRole:
        """選手の役割を取得"""
        # ローテーション
        if self.is_starter(pitcher):
            return PitcherRole.STARTER
        
        # クローザー
        if self.team.closers:
            closer_idx = self.team.closers[0]
            if 0 <= closer_idx < len(self.team.players):
                if self.team.players[closer_idx] == pitcher:
                    return PitcherRole.CLOSER
        
        # セットアップ
        if self.team.setup_pitchers:
            for i, idx in enumerate(self.team.setup_pitchers):
                if 0 <= idx < len(self.team.players):
                    if self.team.players[idx] == pitcher:
                        return PitcherRole.SETUP_A if i == 0 else PitcherRole.SETUP_B
        
        # ワンポイント (左投げで対左強い)
        if pitcher.throws == "左":
            vs_left = getattr(pitcher.stats, 'vs_left_batter', 50)
            if vs_left >= 65:
                return PitcherRole.SPECIALIST
        
        # ロング (スタミナ高い)
        if hasattr(pitcher, 'stats') and pitcher.stats.stamina >= 60:
            return PitcherRole.LONG
        
        return PitcherRole.MIDDLE
    
    def check_pitcher_change(self, ctx: PitchingContext, current_pitcher: 'Player', 
                             used_pitchers: List['Player'], next_batter: 'Player', is_all_star: bool = False) -> Optional['Player']:
        """
        投手交代が必要かチェックし、必要なら交代投手を返す
        
        Args:
            ctx: 現在の試合状況
            current_pitcher: 現在の投手
            used_pitchers: すでに登板した投手リスト
            next_batter: 次の打者
            is_all_star: オールスターゲームかどうか (特別ルール適用)
            
        Returns:
            交代する投手、交代不要ならNone
        """
        # All-Star Special Rules - MANDATORY rotation based on IP
        if is_all_star:
            # First pitcher in the game (starter) gets EXACTLY 2 IP max
            # All subsequent pitchers (relievers) get EXACTLY 1 IP max
            is_first_pitcher = (len(used_pitchers) == 0) or (len(used_pitchers) == 1 and current_pitcher in used_pitchers)
            
            if is_first_pitcher:
                # First pitcher: Change after completing 2 innings (6 outs)
                if ctx.ip_pitched >= 2.0:
                    reliever = self._select_reliever(ctx, used_pitchers, next_batter)
                    if reliever:
                        return reliever
            else:
                # Subsequent pitchers: Change after completing 1 inning (3 outs)
                if ctx.ip_pitched >= 1.0:
                    reliever = self._select_reliever(ctx, used_pitchers, next_batter)
                    if reliever:
                        return reliever
        
        # 怪我チェック
        if current_pitcher.is_injured:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # Determine role - check if this is the game's starter first
        is_game_starter = len(used_pitchers) > 0 and used_pitchers[0] == current_pitcher
        
        if is_game_starter:
            # If this pitcher was the first to pitch in this game, treat as starter
            role = PitcherRole.STARTER
        else:
            role = self.get_pitcher_role(current_pitcher)
        
        # 先発ロジック
        if role == PitcherRole.STARTER:
            replacement = self._check_starter_change(ctx, current_pitcher, used_pitchers, next_batter)
            if replacement:
                return replacement
        else:
            # リリーフロジック
            replacement = self._check_reliever_change(ctx, current_pitcher, role, used_pitchers, next_batter)
            if replacement:
                return replacement
        
        # 対左ワンポイント起用チェック
        if ctx.inning >= 7 and ctx.is_close and ctx.score_diff > 0:
            if next_batter.bats == "左" and current_pitcher.throws == "右":
                if role not in [PitcherRole.CLOSER, PitcherRole.SETUP_A]:
                    specialist = self._find_reliever_by_role(PitcherRole.SPECIALIST, used_pitchers)
                    if specialist:
                        return specialist
        
        return None
    
    def _check_starter_change(self, ctx: PitchingContext, pitcher: 'Player',
                              used_pitchers: List['Player'], next_batter: 'Player') -> Optional['Player']:
        """先発の交代判断"""
        
        # (A) 絶対条件 - 即交代
        if ctx.current_stamina < self.STARTER_STAMINA_CRITICAL:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        if ctx.pitch_count > self.STARTER_PITCH_COUNT_LIMIT:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # 先発の9イニング制限
        if ctx.ip_pitched >= self.STARTER_MAX_INNINGS:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (B) 早期KO (序盤大量失点)
        if ctx.inning <= 3 and ctx.runs_allowed >= self.STARTER_EARLY_HOOK_RUNS:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # 大炎上
        if ctx.runs_allowed >= self.STARTER_BLOWUP_RUNS:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (C) イニング開始時のチェック
        if ctx.outs == 0:
            # QSペース (6回以上、3失点以下) なら続投しやすい
            is_qs_pace = ctx.inning >= 6 and ctx.runs_allowed <= 3
            stamina_threshold = self.STARTER_QS_STAMINA_ALLOW if is_qs_pace else self.STARTER_NORMAL_STAMINA_MIN
            
            if ctx.current_stamina < stamina_threshold:
                return self._select_reliever(ctx, used_pitchers, next_batter)
            
            # 終盤接戦では早めにブルペンへ
            if ctx.inning >= self.STARTER_LATE_INNING_THRESHOLD and ctx.is_close:
                if ctx.pitch_count > self.STARTER_LATE_PITCH_COUNT or ctx.current_stamina < 30:
                    return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (D) ピンチ時の判断 (6回以降、接戦、走者あり)
        if ctx.inning >= 6 and ctx.is_close and ctx.runner_on_base:
            if ctx.current_stamina < self.STARTER_CRISIS_STAMINA:
                return self._select_reliever(ctx, used_pitchers, next_batter)
            if ctx.runs_allowed >= 5:
                return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (E) 9回守護神投入ロジック (完投防止) - より厳格に
        # 3点差以内のリード時、9回に入ったらスタミナが十分残っていなければ交代
        # スタミナ50未満 または 球数100球以上 ならクローザーへ (厳格化)
        if ctx.inning >= 9 and ctx.score_diff > 0 and ctx.score_diff <= 3:
            if ctx.current_stamina < 50 or ctx.pitch_count >= 100:
                return self._select_reliever(ctx, used_pitchers, next_batter)

        return None
    
    def _check_reliever_change(self, ctx: PitchingContext, pitcher: 'Player', 
                               role: PitcherRole, used_pitchers: List['Player'], 
                               next_batter: 'Player') -> Optional['Player']:
        """リリーフの交代判断"""
        
        # (A) クローザー特例 - セーブ機会は最後まで
        is_save_situation = (
            ctx.score_diff > 0 and ctx.score_diff <= 3 and ctx.inning >= 9
        ) or (
            ctx.score_diff > 0 and ctx.score_diff <= 4 and ctx.runner_on_base and ctx.inning >= 9
        )
        
        if role == PitcherRole.CLOSER and is_save_situation:
            # クローザーはセーブ機会では粘る (スタミナが壊滅的でない限り)
            if ctx.current_stamina >= 5:
                return None
        
        # (B) 全リリーフの3イニング上限（クローザーのセーブ機会を除く）
        if ctx.ip_pitched >= self.LONG_RELIEVER_MAX_INNINGS:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (C) スタミナ・球数限界
        if ctx.current_stamina < self.RELIEVER_STAMINA_MIN:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        if ctx.pitch_count > self.RELIEVER_PITCH_COUNT_LIMIT:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (D) イニングまたぎ防止 (新イニング開始時 = 3アウト取った直後)
        if ctx.outs == 0 and ctx.ip_pitched > 0:
            # 例外: クローザー9回以降のみ続投
            if role == PitcherRole.CLOSER and ctx.inning >= 9:
                pass  # 続投OK
            elif role == PitcherRole.LONG:
                # ロングリリーフは続投OK（3イニング上限は上で既にチェック済み）
                pass
            else:
                # 通常の中継ぎ/セットアップは新イニングで必ず交代
                return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (E) イニング途中でも制限（ロング以外）
        if role != PitcherRole.LONG and ctx.ip_pitched >= self.RELIEVER_ONE_INNING_LIMIT:
            if role == PitcherRole.CLOSER and is_save_situation:
                pass  # クローザーのみ続投
            else:
                return self._select_reliever(ctx, used_pitchers, next_batter)
        
        # (F) 炎上中
        if ctx.runs_allowed >= self.RELIEVER_BLOWUP_RUNS:
            return self._select_reliever(ctx, used_pitchers, next_batter)
        
        return None
    
    def _select_reliever(self, ctx: PitchingContext, used_pitchers: List['Player'], 
                         next_batter: 'Player') -> Optional['Player']:
        """状況に応じた最適なリリーフを選択"""
        
        # 役割の優先順位を決定
        target_roles = self._get_target_roles(ctx)
        
        # 対左ワンポイント (接戦で左打者)
        if ctx.is_close and next_batter.bats == "左":
            specialist = self._find_reliever_by_role(PitcherRole.SPECIALIST, used_pitchers)
            if specialist:
                return specialist
        
        # 優先順位に従って探す
        for role in target_roles:
            reliever = self._find_reliever_by_role(role, used_pitchers)
            if reliever:
                return reliever
        
        # フォールバック: 使える人なら誰でも
        all_available = self._get_all_available_relievers(used_pitchers)
        if all_available:
            # 接戦なら能力順、大差なら温存のため能力低い順
            if ctx.is_close and ctx.score_diff > 0:
                all_available.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
            else:
                all_available.sort(key=lambda p: p.stats.overall_pitching())
            return all_available[0]
        
        return None
    
    def _get_target_roles(self, ctx: PitchingContext) -> List[PitcherRole]:
        """状況に応じた目標役割リストを返す
        
        勝ちパターン投手 (CLOSER/SETUP_A) は3点差以内のリード時のみ使用
        それ以外はMIDDLE/LONGを優先して勝ちパターン温存
        """
        is_winning = ctx.score_diff > 0
        is_hold_situation = is_winning and 1 <= ctx.score_diff <= 3  # ホールドシチュエーション: 1-3点リード
        
        # (A) 勝ちパターン (ホールドシチュエーション: 1-3点リード)
        if is_hold_situation:
            if ctx.inning >= 9:
                return [PitcherRole.CLOSER, PitcherRole.SETUP_A]
            elif ctx.inning == 8:
                return [PitcherRole.SETUP_A, PitcherRole.SETUP_B, PitcherRole.MIDDLE]
            elif ctx.inning == 7:
                return [PitcherRole.SETUP_B, PitcherRole.MIDDLE]
            else:
                return [PitcherRole.MIDDLE, PitcherRole.LONG]
        
        # (B) 4点差以上のリード - 勝ちパターン温存
        if is_winning and ctx.score_diff >= 4:
            return [PitcherRole.LONG, PitcherRole.MIDDLE]
        
        # (C) 同点
        if ctx.score_diff == 0:
            if ctx.inning >= 8:
                return [PitcherRole.SETUP_A, PitcherRole.SETUP_B, PitcherRole.CLOSER]
            else:
                return [PitcherRole.MIDDLE, PitcherRole.SETUP_B]
        
        # (D) ビハインド接戦
        if not is_winning and ctx.is_close:
            return [PitcherRole.MIDDLE, PitcherRole.LONG]
        
        # (E) 大差ビハインド
        return [PitcherRole.LONG, PitcherRole.MIDDLE]
    
    def _find_reliever_by_role(self, target_role: PitcherRole, 
                               used_pitchers: List['Player']) -> Optional['Player']:
        """特定の役割のリリーバーを探す"""
        from models import Position, TeamLevel
        
        # ファーム試合ではクローザー/セットアップをスキップ（一軍用のため）
        if self.team_level == TeamLevel.FIRST:
            # まず明示的なアサインをチェック
            if target_role == PitcherRole.CLOSER:
                if self.team.closers:
                    idx = self.team.closers[0]
                    if 0 <= idx < len(self.team.players):
                        p = self.team.players[idx]
                        if self._is_available(p, used_pitchers):
                            return p
            
            elif target_role == PitcherRole.SETUP_A:
                if self.team.setup_pitchers:
                    idx = self.team.setup_pitchers[0]
                    if 0 <= idx < len(self.team.players):
                        p = self.team.players[idx]
                        if self._is_available(p, used_pitchers):
                            return p
            
            elif target_role == PitcherRole.SETUP_B:
                if len(self.team.setup_pitchers) > 1:
                    for idx in self.team.setup_pitchers[1:]:
                        if 0 <= idx < len(self.team.players):
                            p = self.team.players[idx]
                            if self._is_available(p, used_pitchers):
                                return p
                        
        # 汎用検索 - チームレベルに応じたロスターを使用
        candidates = []
        roster_indices = self._get_roster_indices()
        for idx in roster_indices:
            if not (0 <= idx < len(self.team.players)):
                continue
            p = self.team.players[idx]
            
            # ローテ投手は除外
            if self.is_starter(p):
                continue
            
            if p.position.value != "投手":
                continue
            if not self._is_available(p, used_pitchers):
                continue
            
            role = self.get_pitcher_role(p)
            if role == target_role:
                candidates.append(p)
        
        if candidates:
            # スタミナと能力でソート
            candidates.sort(key=lambda x: (x.current_stamina, x.stats.overall_pitching()), reverse=True)
            return candidates[0]
        
        return None
    
    def _get_all_available_relievers(self, used_pitchers: List['Player']) -> List['Player']:
        """使用可能な全リリーバーを取得"""
        from models import Position
        
        available = []
        
        # チームレベルに応じたロスターを使用
        roster_indices = self._get_roster_indices()
        if not roster_indices or len(roster_indices) == 0:
            # Fallback: search all players by index
            roster_indices = range(len(self.team.players))
        
        for idx in roster_indices:
            if not (0 <= idx < len(self.team.players)):
                continue
            p = self.team.players[idx]
            
            if p.position.value != "投手":
                continue
            if not self._is_available(p, used_pitchers):
                continue
            # ローテ投手は除外 (for normal games, but for All-Star we may include)
            # For All-Star: don't exclude rotation pitchers since they should also be available
            if "ALL-" not in self.team.name and self.is_starter(p):
                continue
            
            available.append(p)
        
        return available
    
    def _is_available(self, pitcher: 'Player', used_pitchers: List['Player']) -> bool:
        """投手が使用可能か"""
        if pitcher.is_injured:
            return False
        if pitcher in used_pitchers:
            return False
        if pitcher.current_stamina < 20:
            return False
        # 既に今日出場した選手は出場不可（複数軍出場防止）
        if getattr(pitcher, 'has_played_today', False):
            return False
        
        # 連投防止: 中継ぎは連投をほぼさせない
        # 先発適性がない投手 = 中継ぎ
        apt_starter = getattr(pitcher.stats, 'aptitude_starter', 1)
        is_reliever = apt_starter < 3
        
        if is_reliever:
            consecutive_days = getattr(pitcher, 'consecutive_days', 0)
            fatigue = getattr(pitcher, 'fatigue', 0)
            
            # 2連投以上は原則使用不可
            if consecutive_days >= 2:
                return False
            
            # 1連投でも疲労度が高い場合は使用不可（閾値を厳しく）
            if consecutive_days >= 1 and fatigue >= 30:
                return False
            
            # スタミナが低い場合も連投禁止
            if consecutive_days >= 1 and pitcher.current_stamina < 40:
                return False
        
        return True


def create_pitching_context(state: 'GameState', current_pitcher: 'Player', 
                            current_pitcher_ip: float, is_defending_home: bool) -> PitchingContext:
    """GameStateからPitchingContextを生成するヘルパー"""
    # スタミナはPlayer.current_staminaを使用（球数ベース）
    current_stamina = current_pitcher.current_stamina
    
    if is_defending_home:
        # ホームチームが守備中 (表の攻撃中)
        pitch_count = state.home_pitch_count
        runs_allowed = state.home_current_pitcher_runs
        score_diff = state.home_score - state.away_score
    else:
        # アウェイチームが守備中 (裏の攻撃中)
        pitch_count = state.away_pitch_count
        runs_allowed = state.away_current_pitcher_runs
        score_diff = state.away_score - state.home_score
    
    return PitchingContext(
        inning=state.inning,
        outs=state.outs,
        score_diff=score_diff,
        is_close=abs(score_diff) <= 3,
        is_blowout=abs(score_diff) >= 5,
        current_stamina=current_stamina,
        pitch_count=pitch_count,
        runs_allowed=runs_allowed,
        ip_pitched=current_pitcher_ip,
        runner_on_base=(state.runner_1b is not None or state.runner_2b is not None or state.runner_3b is not None),
        runner_in_scoring_position=(state.runner_2b is not None or state.runner_3b is not None),
        next_batter_hand="右"  # Will be updated by caller
    )
