# -*- coding: utf-8 -*-
"""
NPB試合シミュレーションエンジン

打席エンジン(at_bat_engine)を使用して、
完全な野球の試合をシミュレートする

NPB 2023年実績ベース:
- 平均得点: 3.68点/試合
- 平均試合時間: 3時間12分
- 平均投球数: 143球/試合（先発90球、リリーフ53球）
"""
import random
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum

from at_bat_engine import (
    AtBatSimulator, AtBatResult, AtBatContext, DefenseData,
    get_at_bat_simulator
)


# ========================================
# 列挙型
# ========================================

class GamePhase(Enum):
    """試合フェーズ"""
    NOT_STARTED = "開始前"
    IN_PROGRESS = "試合中"
    COMPLETED = "終了"


class InningHalf(Enum):
    """イニングの表裏"""
    TOP = "表"
    BOTTOM = "裏"


class BaseRunner:
    """走者情報"""
    def __init__(self, player_idx: int = -1, speed: int = 50):
        self.player_idx = player_idx
        self.speed = speed

    def is_occupied(self) -> bool:
        return self.player_idx >= 0

    def clear(self):
        self.player_idx = -1
        self.speed = 50


# ========================================
# データクラス
# ========================================

@dataclass
class GameState:
    """試合状態"""
    inning: int = 1
    half: InningHalf = InningHalf.TOP
    outs: int = 0
    runners: List[BaseRunner] = field(default_factory=lambda: [BaseRunner(), BaseRunner(), BaseRunner()])
    home_score: int = 0
    away_score: int = 0
    phase: GamePhase = GamePhase.NOT_STARTED

    # 打順追跡
    home_batter_idx: int = 0  # 0-8
    away_batter_idx: int = 0

    # 投手追跡
    home_pitcher_idx: int = -1
    away_pitcher_idx: int = -1

    # 投球数
    home_pitch_count: int = 0
    away_pitch_count: int = 0

    def get_batting_team(self) -> str:
        """攻撃チームを取得"""
        return "away" if self.half == InningHalf.TOP else "home"

    def get_pitching_team(self) -> str:
        """守備チームを取得"""
        return "home" if self.half == InningHalf.TOP else "away"

    def get_runner_string(self) -> str:
        """走者状況を文字列で取得"""
        bases = []
        if self.runners[0].is_occupied():
            bases.append("1塁")
        if self.runners[1].is_occupied():
            bases.append("2塁")
        if self.runners[2].is_occupied():
            bases.append("3塁")
        return "・".join(bases) if bases else "無走者"

    def clear_bases(self):
        """塁を空にする"""
        for runner in self.runners:
            runner.clear()

    def count_runners(self) -> int:
        """走者数をカウント"""
        return sum(1 for r in self.runners if r.is_occupied())

    def is_scoring_position(self) -> bool:
        """得点圏に走者がいるか"""
        return self.runners[1].is_occupied() or self.runners[2].is_occupied()


@dataclass
class PlayerGameStats:
    """選手の試合成績"""
    # 打撃
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

    # 投球
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
    """イニングスコア"""
    inning: int
    half: InningHalf
    runs: int
    hits: int
    errors: int = 0


# ========================================
# 試合エンジン
# ========================================

class GameEngine:
    """試合シミュレーションエンジン"""

    def __init__(self, home_team, away_team, use_dh: bool = True):
        """
        Args:
            home_team: ホームチームのTeamオブジェクト
            away_team: アウェイチームのTeamオブジェクト
            use_dh: DH制を使用するか（パ・リーグはTrue）
        """
        self.home_team = home_team
        self.away_team = away_team
        self.use_dh = use_dh

        # 状態
        self.state = GameState()

        # シミュレーター
        self.at_bat_sim = get_at_bat_simulator()

        # 成績記録
        self.home_player_stats: Dict[int, PlayerGameStats] = {}
        self.away_player_stats: Dict[int, PlayerGameStats] = {}

        # イニングスコア
        self.inning_scores: List[InningScore] = []

        # ログ
        self.play_log: List[str] = []
        self.detailed_log: List[Dict] = []

        # 設定
        self.max_innings = 9
        self.max_extra_innings = 12

        # 初期化
        self._init_game()

    def _init_game(self):
        """試合初期化"""
        # 先発投手設定
        if self.home_team.starting_pitcher_idx >= 0:
            self.state.home_pitcher_idx = self.home_team.starting_pitcher_idx
        elif self.home_team.rotation:
            self.state.home_pitcher_idx = self.home_team.rotation[0]
        else:
            # 投手を探す
            from models import Position
            pitchers = [i for i, p in enumerate(self.home_team.players)
                       if p.position == Position.PITCHER]
            self.state.home_pitcher_idx = pitchers[0] if pitchers else 0

        if self.away_team.starting_pitcher_idx >= 0:
            self.state.away_pitcher_idx = self.away_team.starting_pitcher_idx
        elif self.away_team.rotation:
            self.state.away_pitcher_idx = self.away_team.rotation[0]
        else:
            from models import Position
            pitchers = [i for i, p in enumerate(self.away_team.players)
                       if p.position == Position.PITCHER]
            self.state.away_pitcher_idx = pitchers[0] if pitchers else 0

    def get_current_batter(self):
        """現在の打者を取得"""
        if self.state.half == InningHalf.TOP:
            team = self.away_team
            batter_order_idx = self.state.away_batter_idx % 9
        else:
            team = self.home_team
            batter_order_idx = self.state.home_batter_idx % 9

        if team.current_lineup and len(team.current_lineup) > batter_order_idx:
            player_idx = team.current_lineup[batter_order_idx]
            if 0 <= player_idx < len(team.players):
                return team.players[player_idx], player_idx

        # ラインナップがない場合
        return team.players[batter_order_idx] if batter_order_idx < len(team.players) else None, batter_order_idx

    def get_current_pitcher(self):
        """現在の投手を取得"""
        if self.state.half == InningHalf.TOP:
            team = self.home_team
            pitcher_idx = self.state.home_pitcher_idx
        else:
            team = self.away_team
            pitcher_idx = self.state.away_pitcher_idx

        if 0 <= pitcher_idx < len(team.players):
            return team.players[pitcher_idx], pitcher_idx
        return None, -1

    def get_defense_data(self) -> DefenseData:
        """守備データを作成"""
        if self.state.half == InningHalf.TOP:
            team = self.home_team
        else:
            team = self.away_team

        defense = DefenseData()

        # ラインナップから守備力を取得
        from models import Position

        for player in team.players:
            if player.position == Position.CATCHER:
                defense.catcher_fielding = player.stats.fielding
            elif player.position == Position.FIRST:
                defense.first_fielding = player.stats.fielding
            elif player.position == Position.SECOND:
                defense.second_fielding = player.stats.fielding
            elif player.position == Position.THIRD:
                defense.third_fielding = player.stats.fielding
            elif player.position == Position.SHORTSTOP:
                defense.short_fielding = player.stats.fielding
            elif player.position == Position.OUTFIELD:
                # 外野手は複数いるので平均化
                if defense.center_fielding == 50:
                    defense.center_fielding = player.stats.fielding
                    defense.center_speed = player.stats.run
                elif defense.left_fielding == 50:
                    defense.left_fielding = player.stats.fielding
                    defense.left_speed = player.stats.run
                elif defense.right_fielding == 50:
                    defense.right_fielding = player.stats.fielding
                    defense.right_speed = player.stats.run

        return defense

    def _get_player_stats(self, team: str, player_idx: int) -> PlayerGameStats:
        """選手の試合成績を取得（なければ作成）"""
        stats_dict = self.home_player_stats if team == "home" else self.away_player_stats
        if player_idx not in stats_dict:
            stats_dict[player_idx] = PlayerGameStats()
        return stats_dict[player_idx]

    def simulate_at_bat(self) -> Tuple[AtBatResult, int, Dict]:
        """1打席をシミュレート

        Returns:
            (打席結果, 打点, 詳細データ)
        """
        batter, batter_idx = self.get_current_batter()
        pitcher, pitcher_idx = self.get_current_pitcher()

        if batter is None or pitcher is None:
            return AtBatResult.GROUNDOUT, 0, {}

        # コンテキスト作成
        context = AtBatContext(
            balls=0,
            strikes=0,
            outs=self.state.outs,
            runners=[r.is_occupied() for r in self.state.runners],
            inning=self.state.inning,
            is_top=(self.state.half == InningHalf.TOP),
            score_diff=self._get_score_diff()
        )

        # 守備データ
        defense = self.get_defense_data()

        # 投手の持ち球
        pitch_list = ["ストレート"]
        if hasattr(pitcher.stats, 'breaking_balls') and pitcher.stats.breaking_balls:
            pitch_list.extend(pitcher.stats.breaking_balls)

        # 打席シミュレーション
        result, data = self.at_bat_sim.simulate_at_bat(
            batter.stats, pitcher.stats, defense, context, pitch_list
        )

        # 投球数記録
        pitch_count = data.get('pitch_count', 4)
        if self.state.half == InningHalf.TOP:
            self.state.home_pitch_count += pitch_count
        else:
            self.state.away_pitch_count += pitch_count

        # 結果処理
        rbis = self._process_at_bat_result(result, batter, batter_idx, pitcher, pitcher_idx)

        # ログ追加
        batting_team = "away" if self.state.half == InningHalf.TOP else "home"
        self._add_play_log(batter, result, rbis)

        return result, rbis, data

    def _process_at_bat_result(self, result: AtBatResult, batter, batter_idx: int,
                               pitcher, pitcher_idx: int) -> int:
        """打席結果を処理して打点を返す"""
        batting_team = self.state.get_batting_team()
        pitching_team = self.state.get_pitching_team()

        batter_stats = self._get_player_stats(batting_team, batter_idx)
        pitcher_stats = self._get_player_stats(pitching_team, pitcher_idx)

        rbis = 0

        # 打撃成績更新
        if result == AtBatResult.WALK:
            batter_stats.walks += 1
            pitcher_stats.walks_allowed += 1
            rbis = self._advance_runners_walk(batter_idx, batter)

        elif result == AtBatResult.STRIKEOUT:
            batter_stats.at_bats += 1
            batter_stats.strikeouts += 1
            pitcher_stats.strikeouts_pitched += 1
            self.state.outs += 1

        elif result == AtBatResult.HOME_RUN:
            batter_stats.at_bats += 1
            batter_stats.hits += 1
            batter_stats.home_runs += 1
            pitcher_stats.hits_allowed += 1
            pitcher_stats.home_runs_allowed += 1
            rbis = self._process_home_run(batter_idx, batter)
            batter_stats.rbis += rbis
            batter_stats.runs += 1

        elif result == AtBatResult.TRIPLE:
            batter_stats.at_bats += 1
            batter_stats.hits += 1
            batter_stats.triples += 1
            pitcher_stats.hits_allowed += 1
            rbis = self._advance_runners_triple(batter_idx, batter)
            batter_stats.rbis += rbis

        elif result == AtBatResult.DOUBLE:
            batter_stats.at_bats += 1
            batter_stats.hits += 1
            batter_stats.doubles += 1
            pitcher_stats.hits_allowed += 1
            rbis = self._advance_runners_double(batter_idx, batter)
            batter_stats.rbis += rbis

        elif result in [AtBatResult.SINGLE, AtBatResult.INFIELD_HIT]:
            batter_stats.at_bats += 1
            batter_stats.hits += 1
            pitcher_stats.hits_allowed += 1
            rbis = self._advance_runners_single(batter_idx, batter)
            batter_stats.rbis += rbis

        elif result == AtBatResult.GROUNDOUT:
            batter_stats.at_bats += 1
            # 併殺判定
            if self._check_double_play():
                self.state.outs += 2
                rbis = self._process_double_play()
            else:
                self.state.outs += 1
                rbis = self._advance_runners_groundout()

        elif result in [AtBatResult.FLYOUT, AtBatResult.LINEOUT, AtBatResult.POP_OUT]:
            batter_stats.at_bats += 1
            self.state.outs += 1
            # 犠牲フライ判定
            if result == AtBatResult.FLYOUT and self.state.outs < 3:
                rbis = self._check_sacrifice_fly()

        # 得点を加算
        if rbis > 0:
            if self.state.half == InningHalf.TOP:
                self.state.away_score += rbis
            else:
                self.state.home_score += rbis
            pitcher_stats.runs_allowed += rbis
            pitcher_stats.earned_runs += rbis

        # 打順を進める
        self._advance_batting_order()

        return rbis

    def _get_score_diff(self) -> int:
        """攻撃チームから見た点差"""
        if self.state.half == InningHalf.TOP:
            return self.state.away_score - self.state.home_score
        else:
            return self.state.home_score - self.state.away_score

    def _advance_batting_order(self):
        """打順を進める"""
        if self.state.half == InningHalf.TOP:
            self.state.away_batter_idx = (self.state.away_batter_idx + 1) % 9
        else:
            self.state.home_batter_idx = (self.state.home_batter_idx + 1) % 9

    def _process_home_run(self, batter_idx: int, batter) -> int:
        """本塁打の処理"""
        rbis = 1  # 打者自身
        for runner in self.state.runners:
            if runner.is_occupied():
                rbis += 1
        self.state.clear_bases()
        return rbis

    def _advance_runners_triple(self, batter_idx: int, batter) -> int:
        """三塁打時の走者進塁"""
        rbis = 0
        for runner in self.state.runners:
            if runner.is_occupied():
                rbis += 1
        self.state.clear_bases()
        self.state.runners[2] = BaseRunner(batter_idx, getattr(batter.stats, 'run', 50))
        return rbis

    def _advance_runners_double(self, batter_idx: int, batter) -> int:
        """二塁打時の走者進塁"""
        rbis = 0

        # 3塁走者は必ず生還
        if self.state.runners[2].is_occupied():
            rbis += 1

        # 2塁走者は必ず生還
        if self.state.runners[1].is_occupied():
            rbis += 1

        # 1塁走者は3塁へ（足が速ければ生還）
        if self.state.runners[0].is_occupied():
            if self.state.runners[0].speed >= 65 and random.random() < 0.4:
                rbis += 1
                self.state.runners[2].clear()
            else:
                self.state.runners[2] = self.state.runners[0]

        self.state.runners[0].clear()
        self.state.runners[1] = BaseRunner(batter_idx, getattr(batter.stats, 'run', 50))

        return rbis

    def _advance_runners_single(self, batter_idx: int, batter) -> int:
        """単打時の走者進塁"""
        rbis = 0

        # 3塁走者は必ず生還
        if self.state.runners[2].is_occupied():
            rbis += 1
            self.state.runners[2].clear()

        # 2塁走者は生還 or 3塁
        if self.state.runners[1].is_occupied():
            if self.state.runners[1].speed >= 55 and random.random() < 0.55:
                rbis += 1
            else:
                self.state.runners[2] = self.state.runners[1]
            self.state.runners[1].clear()

        # 1塁走者は2塁 or 3塁
        if self.state.runners[0].is_occupied():
            if self.state.runners[0].speed >= 70 and random.random() < 0.25:
                self.state.runners[2] = self.state.runners[0]
            else:
                self.state.runners[1] = self.state.runners[0]
            self.state.runners[0].clear()

        # 打者は1塁
        self.state.runners[0] = BaseRunner(batter_idx, getattr(batter.stats, 'run', 50))

        return rbis

    def _advance_runners_walk(self, batter_idx: int, batter) -> int:
        """四球時の走者進塁（押し出しあり）"""
        rbis = 0

        # 満塁なら押し出し
        if all(r.is_occupied() for r in self.state.runners):
            rbis = 1
            self.state.runners[2].clear()

        # 走者を押し出す
        if self.state.runners[0].is_occupied() and self.state.runners[1].is_occupied():
            self.state.runners[2] = self.state.runners[1]
        if self.state.runners[0].is_occupied():
            self.state.runners[1] = self.state.runners[0]

        self.state.runners[0] = BaseRunner(batter_idx, getattr(batter.stats, 'run', 50))

        return rbis

    def _advance_runners_groundout(self) -> int:
        """ゴロアウト時の走者進塁"""
        rbis = 0

        # 2アウト未満で3塁走者がいれば生還の可能性
        if self.state.outs < 3 and self.state.runners[2].is_occupied():
            if random.random() < 0.25:  # 25%で生還
                rbis += 1
                self.state.runners[2].clear()

        # 2塁走者は3塁へ
        if self.state.runners[1].is_occupied():
            self.state.runners[2] = self.state.runners[1]
            self.state.runners[1].clear()

        # 1塁走者は2塁へ（進塁打）
        if self.state.runners[0].is_occupied() and self.state.outs < 3:
            self.state.runners[1] = self.state.runners[0]
            self.state.runners[0].clear()

        return rbis

    def _check_double_play(self) -> bool:
        """併殺判定"""
        # 2アウト未満、1塁走者ありで併殺の可能性
        if self.state.outs < 2 and self.state.runners[0].is_occupied():
            return random.random() < 0.12  # 12%で併殺
        return False

    def _process_double_play(self) -> int:
        """併殺処理"""
        rbis = 0

        # 3塁走者は生還可能
        if self.state.runners[2].is_occupied():
            if random.random() < 0.3:
                rbis += 1
            self.state.runners[2].clear()

        # 1塁走者アウト
        self.state.runners[0].clear()

        # 2塁走者は3塁へ
        if self.state.runners[1].is_occupied():
            self.state.runners[2] = self.state.runners[1]
            self.state.runners[1].clear()

        return rbis

    def _check_sacrifice_fly(self) -> int:
        """犠牲フライ判定"""
        if self.state.runners[2].is_occupied():
            if random.random() < 0.65:  # 65%でタッチアップ成功
                self.state.runners[2].clear()
                return 1
        return 0

    def _add_play_log(self, batter, result: AtBatResult, rbis: int):
        """プレイログを追加"""
        log_entry = f"{batter.name}: {result.value}"
        if rbis > 0:
            log_entry += f" ({rbis}打点)"
        self.play_log.append(log_entry)

    def simulate_half_inning(self) -> Tuple[int, int]:
        """半イニングをシミュレート

        Returns:
            (得点, ヒット数)
        """
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

            # サヨナラ判定（9回裏以降、ホームがリード）
            if (self.state.half == InningHalf.BOTTOM and
                self.state.inning >= self.max_innings and
                self.state.home_score > self.state.away_score):
                break

        return runs, hits

    def simulate_inning(self) -> Dict:
        """1イニングをシミュレート"""
        inning_data = {
            'inning': self.state.inning,
            'top': {'runs': 0, 'hits': 0},
            'bottom': {'runs': 0, 'hits': 0}
        }

        # 表
        self.state.half = InningHalf.TOP
        runs, hits = self.simulate_half_inning()
        inning_data['top']['runs'] = runs
        inning_data['top']['hits'] = hits
        self.inning_scores.append(InningScore(self.state.inning, InningHalf.TOP, runs, hits))

        # 9回裏、ホームがリードしていれば終了
        if (self.state.inning >= self.max_innings and
            self.state.home_score > self.state.away_score):
            inning_data['bottom'] = None
            return inning_data

        # 裏
        self.state.half = InningHalf.BOTTOM
        runs, hits = self.simulate_half_inning()
        inning_data['bottom']['runs'] = runs
        inning_data['bottom']['hits'] = hits
        self.inning_scores.append(InningScore(self.state.inning, InningHalf.BOTTOM, runs, hits))

        return inning_data

    def should_change_pitcher(self) -> Tuple[bool, str]:
        """継投判定"""
        if self.state.half == InningHalf.TOP:
            pitch_count = self.state.home_pitch_count
            pitcher_idx = self.state.home_pitcher_idx
            team = self.home_team
        else:
            pitch_count = self.state.away_pitch_count
            pitcher_idx = self.state.away_pitcher_idx
            team = self.away_team

        if pitcher_idx < 0 or pitcher_idx >= len(team.players):
            return False, ""

        pitcher = team.players[pitcher_idx]
        stamina = getattr(pitcher.stats, 'stamina', 50)

        # 投球数上限（スタミナ50で100球）
        pitch_limit = 100 + (stamina - 50) * 0.6

        if pitch_count >= pitch_limit:
            return True, "球数制限"

        return False, ""

    def change_pitcher(self, new_pitcher_idx: int):
        """投手交代"""
        if self.state.half == InningHalf.TOP:
            self.state.home_pitcher_idx = new_pitcher_idx
            self.state.home_pitch_count = 0
        else:
            self.state.away_pitcher_idx = new_pitcher_idx
            self.state.away_pitch_count = 0

    def simulate_game(self) -> Dict:
        """試合全体をシミュレート

        Returns:
            試合結果データ
        """
        self.state.phase = GamePhase.IN_PROGRESS

        # 9イニング
        for inning in range(1, self.max_innings + 1):
            self.state.inning = inning
            inning_data = self.simulate_inning()

            # 継投チェック
            should_change, reason = self.should_change_pitcher()
            if should_change:
                # 中継ぎに交代（簡易処理）
                pass

        # 延長戦
        while (self.state.home_score == self.state.away_score and
               self.state.inning < self.max_extra_innings):
            self.state.inning += 1
            self.simulate_inning()

        self.state.phase = GamePhase.COMPLETED

        # 結果データ作成
        return self._create_game_result()

    def _create_game_result(self) -> Dict:
        """試合結果データを作成"""
        return {
            'home_team': self.home_team.name,
            'away_team': self.away_team.name,
            'home_score': self.state.home_score,
            'away_score': self.state.away_score,
            'innings': self.state.inning,
            'winner': self._get_winner(),
            'is_draw': self.state.home_score == self.state.away_score,
            'inning_scores': self._get_inning_scores_array(),
            'home_player_stats': self.home_player_stats,
            'away_player_stats': self.away_player_stats,
            'play_log': self.play_log
        }

    def _get_winner(self) -> Optional[str]:
        """勝利チームを取得"""
        if self.state.home_score > self.state.away_score:
            return self.home_team.name
        elif self.state.away_score > self.state.home_score:
            return self.away_team.name
        return None

    def _get_inning_scores_array(self) -> Dict:
        """イニングスコア配列を取得"""
        home_scores = []
        away_scores = []

        for score in self.inning_scores:
            if score.half == InningHalf.TOP:
                away_scores.append(score.runs)
            else:
                home_scores.append(score.runs)

        return {
            'home': home_scores,
            'away': away_scores
        }

    def update_team_records(self):
        """チーム成績を更新"""
        if self.state.home_score > self.state.away_score:
            self.home_team.wins += 1
            self.away_team.losses += 1
        elif self.state.away_score > self.state.home_score:
            self.away_team.wins += 1
            self.home_team.losses += 1
        else:
            self.home_team.draws += 1
            self.away_team.draws += 1

    def update_player_records(self):
        """選手の通算成績を更新"""
        # ホームチーム
        for player_idx, game_stats in self.home_player_stats.items():
            if 0 <= player_idx < len(self.home_team.players):
                player = self.home_team.players[player_idx]
                self._update_player_record(player, game_stats)

        # アウェイチーム
        for player_idx, game_stats in self.away_player_stats.items():
            if 0 <= player_idx < len(self.away_team.players):
                player = self.away_team.players[player_idx]
                self._update_player_record(player, game_stats)

    def _update_player_record(self, player, game_stats: PlayerGameStats):
        """選手の通算成績を更新"""
        record = player.record

        # 打撃成績
        record.at_bats += game_stats.at_bats
        record.hits += game_stats.hits
        record.doubles += game_stats.doubles
        record.triples += game_stats.triples
        record.home_runs += game_stats.home_runs
        record.rbis += game_stats.rbis
        record.runs += game_stats.runs
        record.walks += game_stats.walks
        record.strikeouts += game_stats.strikeouts

        # 投球成績
        record.innings_pitched += game_stats.innings_pitched
        record.hits_allowed += game_stats.hits_allowed
        record.earned_runs += game_stats.earned_runs
        record.walks_allowed += game_stats.walks_allowed
        record.strikeouts_pitched += game_stats.strikeouts_pitched


# ========================================
# 便利関数
# ========================================

def simulate_game(home_team, away_team, use_dh: bool = True,
                  update_records: bool = True) -> Dict:
    """試合をシミュレートする便利関数

    Args:
        home_team: ホームチーム
        away_team: アウェイチーム
        use_dh: DH制使用
        update_records: 成績を更新するか

    Returns:
        試合結果データ
    """
    engine = GameEngine(home_team, away_team, use_dh)
    result = engine.simulate_game()

    if update_records:
        engine.update_team_records()
        engine.update_player_records()

    return result


def simulate_game_quick(home_team, away_team) -> Tuple[int, int, str]:
    """高速試合シミュレーション（詳細なしでスコアのみ）

    NPB 2023年実績ベースの計算:
    - リーグ平均得点: 3.68点/試合
    - ホームアドバンテージ: +3.5%

    Returns:
        (home_score, away_score, winner_name)
    """
    # チーム打撃力
    def calc_batting(team):
        if team.current_lineup:
            batters = [team.players[i] for i in team.current_lineup
                      if 0 <= i < len(team.players)]
        else:
            from models import Position
            batters = [p for p in team.players if p.position != Position.PITCHER]

        if not batters:
            return 50

        total = sum(p.stats.contact * 0.4 + p.stats.power * 0.4 + p.stats.run * 0.2
                   for p in batters[:9])
        return total / min(9, len(batters))

    # チーム投手力
    def calc_pitching(team):
        if team.starting_pitcher_idx >= 0 and team.starting_pitcher_idx < len(team.players):
            starter = team.players[team.starting_pitcher_idx]
            return (starter.stats.control * 0.4 + starter.stats.breaking * 0.3 +
                   starter.stats.speed * 0.2 + starter.stats.stamina * 0.1)
        return 50

    home_bat = calc_batting(home_team)
    away_bat = calc_batting(away_team)
    home_pitch = calc_pitching(home_team)
    away_pitch = calc_pitching(away_team)

    # 期待得点
    base_runs = 3.68

    home_exp = base_runs * (1 + (home_bat - 50) * 0.015) * (1 - (away_pitch - 50) * 0.012)
    away_exp = base_runs * (1 + (away_bat - 50) * 0.015) * (1 - (home_pitch - 50) * 0.012)

    # ホームアドバンテージ
    home_exp *= 1.035

    # 得点生成
    home_score = max(0, int(home_exp + random.gauss(0, 2.2)))
    away_score = max(0, int(away_exp + random.gauss(0, 2.2)))

    home_score = min(home_score, 15)
    away_score = min(away_score, 15)

    # 引き分けの場合は延長
    if home_score == away_score:
        if random.random() < 0.70:
            if random.random() < 0.535:
                home_score += 1
            else:
                away_score += 1

    # 勝敗記録
    if home_score > away_score:
        winner = home_team.name
    elif away_score > home_score:
        winner = away_team.name
    else:
        winner = ""

    return home_score, away_score, winner


# ========================================
# テスト
# ========================================

if __name__ == "__main__":
    # テスト用にモックチームを作成
    print("試合エンジンテスト")

    # 実際のテストは models.py の Team を使用
    # from models import Team, Player, Position
    # team1 = Team(name="テストチーム1", league=League.CENTRAL)
    # team2 = Team(name="テストチーム2", league=League.CENTRAL)
    # result = simulate_game(team1, team2)
    # print(f"結果: {result['away_team']} {result['away_score']} - {result['home_score']} {result['home_team']}")
