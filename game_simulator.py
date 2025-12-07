# -*- coding: utf-8 -*-
"""
試合シミュレーター（打球物理演算版 - 成績反映機能付き）
"""
import random
import math
from typing import Tuple, List, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from models import Team, Player, PitchType, TeamLevel, PlayerRecord

# ========================================
# 打球物理計算モジュール
# ========================================
@dataclass
class BattedBall:
    """打球データ"""
    exit_velocity: float    # 打球速度 (km/h)
    launch_angle: float     # 打球角度 (度)
    spray_angle: float      # 打球方向 (度)
    hang_time: float = 0.0
    distance: float = 0.0
    
    def __post_init__(self):
        # 簡易飛距離計算
        v0 = self.exit_velocity / 3.6
        angle_rad = math.radians(self.launch_angle)
        g = 9.8
        drag = 0.35 # 空気抵抗係数
        
        vx = v0 * math.cos(angle_rad)
        vy = v0 * math.sin(angle_rad)
        
        if self.launch_angle > 0:
            t_flight = (2 * vy / g) * (1 - drag * 0.3)
            self.hang_time = max(0.5, t_flight)
            self.distance = vx * self.hang_time * (1 - drag)
        else:
            self.hang_time = 0.3 + abs(self.launch_angle) / 30
            self.distance = vx * self.hang_time * 0.7


class BattedBallCalculator:
    """打球物理計算クラス"""
    
    @staticmethod
    def calculate_batted_ball(batter_stats, pitcher_stats) -> BattedBall:
        """打球データを計算 (OOTP Stats対応)"""
        contact = batter_stats.contact
        power = batter_stats.power
        velocity = pitcher_stats.velocity
        movement = pitcher_stats.movement
        
        # ===== 打球速度 (km/h) =====
        base_velocity = 95
        power_bonus = (power - 40) * 0.9
        pitch_vel_factor = (velocity - 130) * 0.4
        sweet_spot = random.gauss(0, 18)
        
        exit_velocity = base_velocity + power_bonus + pitch_vel_factor + sweet_spot
        if movement > 60:
            exit_velocity -= (movement - 50) * 0.3
            
        exit_velocity = max(70, min(180, exit_velocity))
        
        # ===== 打球角度 (度) =====
        target_angle = 12 + (power - 50) * 0.15
        control_effect = (100 - contact) * 0.2
        angle_deviation = random.gauss(0, 15 + control_effect)
        
        launch_angle = target_angle + angle_deviation
        launch_angle = max(-20, min(65, launch_angle))
        
        # ===== 打球方向 (度) =====
        spray_angle = random.gauss(0, 25)
        if contact >= 70: spray_angle *= 0.85
        spray_angle = max(-45, min(45, spray_angle))
        
        return BattedBall(exit_velocity, launch_angle, spray_angle)
    
    @staticmethod
    def judge_result(ball: BattedBall) -> Tuple[str, str]:
        ev = ball.exit_velocity
        la = ball.launch_angle
        dist = ball.distance
        
        # HR判定
        fence_dist = 115.0 
        if 20 <= la <= 45 and dist >= fence_dist:
            return "home_run", f"HR {dist:.0f}m"
            
        # フライ
        if la >= 15:
            if dist >= 75: # 外野
                catch_chance = 0.85 - (dist - 75)/60
                if random.random() > catch_chance:
                    if dist >= 105: return "triple", "三塁打"
                    if dist >= 90: return "double", "二塁打"
                    return "single", "ヒット"
                return "flyout", "外野フライ"
            return "flyout", "内野フライ"
            
        # ライナー
        elif 5 <= la < 15:
            if ev >= 145:
                if random.random() > 0.6: return "single", "ヒット"
                return "lineout", "ライナーアウト"
            if random.random() > 0.7: return "single", "ヒット"
            return "lineout", "ライナーアウト"
            
        # ゴロ
        else:
            if ev >= 140:
                if random.random() < 0.35: return "single", "強襲ヒット"
            return "groundout", "ゴロアウト"

    @staticmethod
    def simulate_swing(batter_stats, pitcher_stats) -> Tuple[str, Optional[BattedBall], str]:
        """スイング結果シミュレーション"""
        eye = batter_stats.eye
        avoid_k = batter_stats.avoid_k
        
        control = pitcher_stats.control
        stuff = pitcher_stats.stuff
        
        # ストライク判定
        strike_prob = 0.45 + (control - 50) * 0.003 - (eye - 50) * 0.002
        is_strike = random.random() < strike_prob
        
        if is_strike:
            swing_prob = 0.7
            if random.random() < swing_prob:
                # コンタクト判定
                contact_prob = 0.80 + (avoid_k - 50)*0.004 - (stuff - 50)*0.005
                contact_prob = max(0.4, min(0.95, contact_prob))
                
                if random.random() < contact_prob:
                    # インプレー
                    ball = BattedBallCalculator.calculate_batted_ball(batter_stats, pitcher_stats)
                    res, desc = BattedBallCalculator.judge_result(ball)
                    return res, ball, desc
                else:
                    return "swing_miss", None, "空振り"
            else:
                return "called_strike", None, "見逃し"
        else:
            # ボール球
            chase_prob = 0.30 - (eye - 50) * 0.005
            chase_prob = max(0.05, min(0.5, chase_prob))
            
            if random.random() < chase_prob:
                if random.random() < 0.6:
                    return "swing_miss", None, "空振り"
                else:
                    return "foul", None, "ファウル"
            else:
                return "ball", None, "ボール"


class TacticManager:
    @staticmethod
    def should_change_pitcher(pitcher: Player, game_state, team, stats) -> Tuple[bool, str]:
        stamina = pitcher.stats.stamina
        # スタミナ限界計算
        limit = 80 + (stamina - 50) * 0.8
        limit = max(50, min(130, limit))
        
        pitch_count = stats.get('pitch_count', 0)
        
        # 簡易ロジック: 限界を超えたら交代
        if pitch_count >= limit: return True, "スタミナ切れ"
        
        # 大量失点時
        runs_allowed = stats.get('runs', 0)
        if runs_allowed >= 5 and game_state['inning'] <= 5:
            return True, "炎上"
            
        return False, ""


class GameSimulator:
    def __init__(self, home_team: Team, away_team: Team, use_physics=True, fast_mode=False, use_new_engine=False):
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = 0
        self.away_score = 0
        self.inning = 1
        self.log = []
        self.fast_mode = fast_mode
        self.tactic_manager = TacticManager()
        
        # 投手成績管理用
        self.home_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'runs': 0, 'er': 0, 'so': 0, 'bb': 0, 'ip': 0.0}
        self.away_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'runs': 0, 'er': 0, 'so': 0, 'bb': 0, 'ip': 0.0}
        
        self.current_home_pitcher_idx = home_team.starting_pitcher_idx
        self.current_away_pitcher_idx = away_team.starting_pitcher_idx
        
        # 継投記録
        self.home_pitchers_used = [home_team.starting_pitcher_idx]
        self.away_pitchers_used = [away_team.starting_pitcher_idx]
        
        # 試合出場した選手ID（重複カウント防止用）
        self.participated_players = set()
        
        self.inning_scores_home = []
        self.inning_scores_away = []

    def _get_record(self, player: Player) -> PlayerRecord:
        """選手の所属軍に応じたレコードを取得"""
        if player.team_level == TeamLevel.SECOND:
            return player.record_farm
        elif player.team_level == TeamLevel.THIRD:
            return player.record_third
        else:
            return player.record

    def _mark_participation(self, player: Player, is_pitcher: bool):
        """試合出場を記録"""
        pid = id(player)
        if pid not in self.participated_players:
            self.participated_players.add(pid)
            record = self._get_record(player)
            if is_pitcher:
                record.games_pitched += 1
                if player == self.home_team.get_today_starter() or player == self.away_team.get_today_starter():
                    record.games_started += 1
            else:
                record.games += 1

    def _update_batter_stats(self, batter: Player, result: str, rbis: int, runs: int):
        """打者成績を更新"""
        self._mark_participation(batter, False)
        record = self._get_record(batter)
        
        record.plate_appearances += 1
        record.rbis += rbis
        # 得点は走者帰還時に別途加算されるべきだが、簡易的にここで処理
        # （厳密には生還した走者のrecord.runsを加算する必要がある）
        
        if result == "walk":
            record.walks += 1
        elif result == "hit_by_pitch": # 未実装だが枠として
            record.hit_by_pitch += 1
        elif result == "sacrifice_fly": # 未実装だが枠として
            record.sacrifice_flies += 1
        elif result == "sacrifice_hit": # 未実装だが枠として
            record.sacrifice_hits += 1
        elif result == "strikeout":
            record.at_bats += 1
            record.strikeouts += 1
        elif result == "home_run":
            record.at_bats += 1
            record.hits += 1
            record.home_runs += 1
            record.runs += 1 # 本塁打は自分も得点
            record.total_bases += 4
        elif result == "single":
            record.at_bats += 1
            record.hits += 1
            record.total_bases += 1
        elif result == "double":
            record.at_bats += 1
            record.hits += 1
            record.doubles += 1
            record.total_bases += 2
        elif result == "triple":
            record.at_bats += 1
            record.hits += 1
            record.triples += 1
            record.total_bases += 3
        elif result in ["out", "flyout", "groundout", "lineout"]:
            record.at_bats += 1
            # ゴロ/フライ等の内訳加算
            if "ground" in result: record.ground_balls += 1
            elif "fly" in result: record.fly_balls += 1
            elif "line" in result: record.line_drives += 1
    
    def _update_pitcher_stats(self, pitcher: Player, result: str, runs: int, er: int):
        """投手成績を更新（対戦ごと）"""
        self._mark_participation(pitcher, True)
        record = self._get_record(pitcher)
        
        # 投球数はsimulate_inningでまとめて加算しているが、本来はここでも良い
        
        if result == "walk":
            record.walks_allowed += 1
        elif result == "strikeout":
            record.strikeouts_pitched += 1
        elif result == "home_run":
            record.hits_allowed += 1
            record.home_runs_allowed += 1
        elif result in ["single", "double", "triple"]:
            record.hits_allowed += 1
            
        record.runs_allowed += runs
        record.earned_runs += er

    def simulate_at_bat(self, batter: Player, pitcher: Player) -> Tuple[str, int]:
        """1打席シミュレーション"""
        balls = 0
        strikes = 0
        
        while balls < 4 and strikes < 3:
            res, ball, desc = BattedBallCalculator.simulate_swing(batter.stats, pitcher.stats)
            
            if res == "ball": 
                balls += 1
            elif res in ["called_strike", "swing_miss"]: 
                strikes += 1
            elif res == "foul":
                if strikes < 2: strikes += 1
            else:
                # インプレー結果
                if res == "home_run": return "home_run", 1
                if res in ["single", "double", "triple"]: return res, 0
                return "out", 0 # flyout, groundout etc.
                
        if balls >= 4: return "walk", 0
        return "strikeout", 0
    
    def simulate_inning(self, batting_team: Team, pitching_team: Team, batter_idx: int):
        outs = 0
        runs_in_inning = 0
        runners = [False, False, False] # 1塁, 2塁, 3塁
        
        # 投手取得
        is_home_pitching = (pitching_team == self.home_team)
        p_idx = self.current_home_pitcher_idx if is_home_pitching else self.current_away_pitcher_idx
        pitcher = pitching_team.players[p_idx]
        p_stats = self.home_pitcher_stats if is_home_pitching else self.away_pitcher_stats
        
        # 投手交代判定（簡易）
        should_change, reason = self.tactic_manager.should_change_pitcher(pitcher, {'inning': self.inning}, pitching_team, p_stats)
        if should_change and len(pitching_team.bench_pitchers) > 0:
            # 交代処理（ランダムに次の投手）
            new_p_idx = random.choice(pitching_team.bench_pitchers)
            if is_home_pitching:
                self.current_home_pitcher_idx = new_p_idx
                self.home_pitchers_used.append(new_p_idx)
            else:
                self.current_away_pitcher_idx = new_p_idx
                self.away_pitchers_used.append(new_p_idx)
            pitcher = pitching_team.players[new_p_idx]
            if not self.fast_mode:
                self.log.append(f"  【投手交代】 {pitching_team.name}: {pitcher.name}")

        while outs < 3:
            # 打者取得
            b_idx = batting_team.current_lineup[batter_idx % 9]
            batter = batting_team.players[b_idx]
            
            # 打席結果
            res, _ = self.simulate_at_bat(batter, pitcher)
            
            # 投球数加算（簡易）
            pitches = random.randint(3, 6)
            p_stats['pitch_count'] += pitches
            self._get_record(pitcher).pitches_thrown += pitches
            
            # 成績反映用の変数
            rbis = 0
            runs_scored = 0
            earned_runs = 0
            
            if res == "out" or res == "strikeout":
                outs += 1
                self._update_batter_stats(batter, res, 0, 0)
                self._update_pitcher_stats(pitcher, res, 0, 0)
                
                if res != "strikeout":
                    # 進塁打の簡易判定（ランダム）
                    if runners[1] and outs < 3 and random.random() < 0.3:
                        runners[2] = True
                        runners[1] = False
                
                if not self.fast_mode:
                    self.log.append(f"  {batter.name}: {res}")
                    
            elif res == "walk":
                # 押し出し判定
                if all(runners):
                    runs_in_inning += 1
                    rbis += 1
                    runs_scored += 1
                    earned_runs += 1
                
                # 走者押し出し処理
                new_runners = [True, runners[0], False]
                if runners[0] and runners[1]: new_runners[2] = True
                elif runners[0] and not runners[1] and runners[2]: new_runners[2] = True # 1,3塁 -> 満塁
                elif all(runners): new_runners = [True, True, True]
                else:
                    if runners[0]: new_runners[1] = True
                    if runners[1]: new_runners[2] = True
                
                # 正確な押し出しロジックは複雑なので簡易化：
                # 満塁なら全員進む、それ以外は詰まっているところだけ進む
                if runners[0] and runners[1] and runners[2]:
                    runners = [True, True, True]
                elif runners[0] and runners[1]:
                    runners = [True, True, True]
                elif runners[0]:
                    runners = [True, True, runners[2]]
                else:
                    runners = [True, runners[1], runners[2]]

                self._update_batter_stats(batter, res, rbis, 0)
                self._update_pitcher_stats(pitcher, res, runs_scored, earned_runs)
                
                if not self.fast_mode:
                    self.log.append(f"  {batter.name}: 四球")
                    
            elif res == "home_run":
                score = 1 + sum(runners)
                runs_in_inning += score
                rbis += score
                runs_scored += score
                earned_runs += score
                
                # 走者の得点記録（簡易的に打者レコード更新時に考慮できないため、ここで走者のRunsを加算すべきだが、
                # 走者オブジェクトの追跡が複雑になるため、今回は打者のみ詳細に記録し、チーム得点を優先）
                # ※厳密にするなら lineup 上の選手IDからPlayerを取得して runs += 1 する
                
                runners = [False, False, False]
                self._update_batter_stats(batter, res, rbis, 1) # 本人は1得点
                self._update_pitcher_stats(pitcher, res, runs_scored, earned_runs)
                
                if not self.fast_mode:
                    self.log.append(f"  {batter.name}: ホームラン！ ({score}点)")
                    
            else: # Hit (Single, Double, Triple)
                hit_runs = 0
                # 走者生還ロジック（簡易）
                if res == "single":
                    if runners[2]: hit_runs += 1; runners[2] = False
                    if runners[1]: 
                        if random.random() < 0.6: hit_runs += 1; runners[1] = False
                        else: runners[2] = True; runners[1] = False
                    if runners[0]: runners[1] = True; runners[0] = False
                    runners[0] = True
                    
                elif res == "double":
                    if runners[2]: hit_runs += 1; runners[2] = False
                    if runners[1]: hit_runs += 1; runners[1] = False
                    if runners[0]: 
                        if random.random() < 0.4: hit_runs += 1; runners[0] = False
                        else: runners[2] = True; runners[0] = False
                    runners[1] = True
                    
                elif res == "triple":
                    hit_runs += sum(runners)
                    runners = [False, False, False]
                    runners[2] = True
                
                runs_in_inning += hit_runs
                rbis += hit_runs
                runs_scored += hit_runs
                earned_runs += hit_runs # エラーがない前提なので自責点
                
                self._update_batter_stats(batter, res, rbis, 1 if hit_runs > 0 else 0) # 自分がホームインしたわけではないが...
                # 正確には、自分がホームインしたかどうかは後続の打席で決まる。
                # ここでは「打者としての記録」にフォーカス。
                
                self._update_pitcher_stats(pitcher, res, runs_scored, earned_runs)

                if not self.fast_mode:
                    self.log.append(f"  {batter.name}: {res}")
            
            batter_idx += 1
        
        # イニング終了時、投手に投球回を加算
        # 1イニング完了 = 1.0 (内部的には1/3単位で管理していないため実数で加算)
        # 途中交代に対応するため、アウト数ベースで管理するのが理想だが、ここでは簡易的に
        self._get_record(pitcher).innings_pitched += 1.0
        p_stats['ip'] += 1.0
        
        return runs_in_inning, batter_idx

    def simulate_game(self):
        if not self.fast_mode:
            self.log = ["=== PLAY BALL ==="]
        else:
            self.log = []
            
        h_idx = 0
        a_idx = 0
        
        for i in range(9):
            self.inning = i + 1
            if not self.fast_mode:
                self.log.append(f"--- {i+1}回表 ---")
            
            r, a_idx = self.simulate_inning(self.away_team, self.home_team, a_idx)
            self.away_score += r
            self.inning_scores_away.append(r)
            
            # サヨナラ判定
            if i == 8 and self.home_score > self.away_score:
                self.inning_scores_home.append('X')
                break
                
            if not self.fast_mode:
                self.log.append(f"--- {i+1}回裏 ---")
            
            r, h_idx = self.simulate_inning(self.home_team, self.away_team, h_idx)
            self.home_score += r
            self.inning_scores_home.append(r)
            
            # 延長戦等のロジックは省略
            
        # 試合終了処理：勝敗・セーブ記録
        self._finalize_game_stats()
            
        return self.home_score, self.away_score

    def _finalize_game_stats(self):
        """試合終了後の投手成績確定（勝敗・セーブ）"""
        home_win = self.home_score > self.away_score
        draw = self.home_score == self.away_score
        
        if draw:
            return

        # 勝利チーム、敗戦チーム
        win_team = self.home_team if home_win else self.away_team
        lose_team = self.away_team if home_win else self.home_team
        
        win_pitchers = self.home_pitchers_used if home_win else self.away_pitchers_used
        lose_pitchers = self.away_pitchers_used if home_win else self.home_pitchers_used
        
        # 勝利投手：先発が5回以上リードを保って投げたか、救援がリードを奪ったか
        # 簡易ロジック: 
        # 1. 先発が5回以上投げているか確認（ここではイニングごとの登板記録がないため、最後に投げた投手を勝利とする簡易判定になってしまう）
        # より正確にするにはイニングごとのスコアと登板投手を紐付ける必要がある。
        # 今回は「最も長いイニングを投げた投手」または「先発」に勝ちをつける簡易実装にする。
        
        # 勝ち投手: 先発
        if len(win_pitchers) > 0:
            win_p = win_team.players[win_pitchers[0]]
            # 先発が5回以上投げたと仮定（GameSimulatorの構造上、厳密な回数は追跡していないため）
            # 常に先発に勝ちをつける（簡易）
            self._get_record(win_p).wins += 1
            
            # セーブ: 3点差以内で最後を投げた投手（先発以外）
            if len(win_pitchers) > 1:
                closer = win_team.players[win_pitchers[-1]]
                score_diff = abs(self.home_score - self.away_score)
                if score_diff <= 3:
                    self._get_record(closer).saves += 1
                else:
                    # ホールド（簡易: 最初と最後以外の中継ぎ）
                    for pid in win_pitchers[1:-1]:
                        self._get_record(win_team.players[pid]).holds += 1
        
        # 負け投手: 先発（簡易）
        if len(lose_pitchers) > 0:
            lose_p = lose_team.players[lose_pitchers[0]]
            self._get_record(lose_p).losses += 1