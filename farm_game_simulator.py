# -*- coding: utf-8 -*-
"""
二軍・三軍試合シミュレーター
一軍の試合と同時に裏で計算され、成績に反映される
"""
import random
import math
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass, field
from models import Team, Player, Position, TeamLevel, PlayerRecord


@dataclass
class FarmGameResult:
    """二軍/三軍試合結果"""
    team_level: TeamLevel
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    date: str
    player_stats: Dict[str, Dict] = field(default_factory=dict)  # {player_name: {stat_type: value}}


class FarmGameSimulator:
    """二軍・三軍試合シミュレーター"""

    def __init__(self, home_team: Team, away_team: Team, team_level: TeamLevel = TeamLevel.SECOND):
        self.home_team = home_team
        self.away_team = away_team
        self.team_level = team_level
        self.home_score = 0
        self.away_score = 0
        self.player_stats: Dict[str, Dict] = {}  # 試合中の個人成績

    def get_roster(self, team: Team) -> List[int]:
        """軍に応じたロスターを取得"""
        if self.team_level == TeamLevel.SECOND:
            return team.farm_roster
        elif self.team_level == TeamLevel.THIRD:
            return team.third_roster
        return team.active_roster

    def get_lineup(self, team: Team) -> List[int]:
        """軍に応じた打順を取得（なければ自動生成）"""
        if self.team_level == TeamLevel.SECOND:
            if team.farm_lineup:
                return team.farm_lineup
        elif self.team_level == TeamLevel.THIRD:
            if team.third_lineup:
                return team.third_lineup

        # 自動生成
        roster = self.get_roster(team)
        batters = [idx for idx in roster if 0 <= idx < len(team.players)
                   and team.players[idx].position != Position.PITCHER]

        # 能力順にソート
        batters.sort(key=lambda idx: team.players[idx].stats.overall_batting(), reverse=True)
        return batters[:9] if len(batters) >= 9 else batters

    def get_rotation(self, team: Team) -> List[int]:
        """軍に応じたローテーションを取得（なければ自動生成）"""
        if self.team_level == TeamLevel.SECOND:
            if team.farm_rotation:
                return team.farm_rotation
        elif self.team_level == TeamLevel.THIRD:
            if team.third_rotation:
                return team.third_rotation

        # 自動生成
        roster = self.get_roster(team)
        pitchers = [idx for idx in roster if 0 <= idx < len(team.players)
                    and team.players[idx].position == Position.PITCHER]

        # 能力順にソート
        pitchers.sort(key=lambda idx: team.players[idx].stats.overall_pitching(), reverse=True)
        return pitchers[:6] if len(pitchers) >= 6 else pitchers

    def init_player_stats(self, player_name: str):
        """選手の試合統計を初期化"""
        if player_name not in self.player_stats:
            self.player_stats[player_name] = {
                'pa': 0, 'ab': 0, 'hits': 0, 'doubles': 0, 'triples': 0,
                'hr': 0, 'rbi': 0, 'runs': 0, 'bb': 0, 'k': 0, 'sb': 0,
                'ip': 0.0, 'er': 0, 'h_allowed': 0, 'bb_allowed': 0, 'k_pitched': 0,
                'ground_balls': 0, 'fly_balls': 0, 'line_drives': 0
            }

    def simulate_at_bat(self, batter: Player, pitcher: Player) -> Tuple[str, int, Dict]:
        """1打席をシミュレート"""
        self.init_player_stats(batter.name)
        self.init_player_stats(pitcher.name)

        batter_stats = batter.stats
        pitcher_stats = pitcher.stats

        # 打撃能力
        contact = batter_stats.contact
        power = batter_stats.power
        eye = batter_stats.eye
        avoid_k = batter_stats.avoid_k

        # 投手能力
        control = pitcher_stats.control
        stuff = pitcher_stats.stuff
        movement = pitcher_stats.movement

        # カウントシミュレーション（簡易版）
        balls = 0
        strikes = 0
        pitches = 0

        while balls < 4 and strikes < 3:
            pitches += 1

            # ストライク確率
            strike_prob = 0.45 + (control - 100) * 0.002 - (eye - 100) * 0.001
            is_strike = random.random() < strike_prob

            if is_strike:
                # スイング判定
                swing_prob = 0.7
                if random.random() < swing_prob:
                    # コンタクト判定
                    contact_prob = 0.75 + (avoid_k - 100) * 0.002 - (stuff - 100) * 0.003
                    contact_prob = max(0.35, min(0.92, contact_prob))

                    if random.random() < contact_prob:
                        # インプレー
                        result = self._determine_batted_ball_result(batter_stats, pitcher_stats)
                        return result
                    else:
                        strikes += 1
                else:
                    strikes += 1
            else:
                # ボール球
                chase_prob = 0.25 - (eye - 100) * 0.003
                chase_prob = max(0.05, min(0.4, chase_prob))

                if random.random() < chase_prob:
                    if random.random() < 0.5:
                        strikes += 1 if strikes < 2 else strikes  # ファウル
                    else:
                        strikes += 1  # 空振り
                else:
                    balls += 1

        if balls >= 4:
            self.player_stats[batter.name]['pa'] += 1
            self.player_stats[batter.name]['bb'] += 1
            self.player_stats[pitcher.name]['bb_allowed'] += 1
            return "walk", 0, {'type': 'walk'}

        # 三振
        self.player_stats[batter.name]['pa'] += 1
        self.player_stats[batter.name]['ab'] += 1
        self.player_stats[batter.name]['k'] += 1
        self.player_stats[pitcher.name]['k_pitched'] += 1
        return "strikeout", 0, {'type': 'strikeout'}

    def _determine_batted_ball_result(self, batter_stats, pitcher_stats) -> Tuple[str, int, Dict]:
        """打球結果を決定"""
        contact = batter_stats.contact
        power = batter_stats.power
        gap = batter_stats.gap
        speed = batter_stats.speed

        movement = pitcher_stats.movement
        stuff = pitcher_stats.stuff

        # 打球速度（簡易版）
        exit_velocity = 85 + (power - 100) * 0.4 + random.gauss(0, 12)
        exit_velocity -= (movement - 100) * 0.15
        exit_velocity = max(60, min(170, exit_velocity))

        # 打球角度
        launch_angle = 10 + (power - 100) * 0.1 + random.gauss(0, 18)
        launch_angle = max(-25, min(60, launch_angle))

        # 飛距離計算
        v0 = exit_velocity / 3.6
        angle_rad = math.radians(max(0, launch_angle))
        distance = (v0 ** 2) * math.sin(2 * angle_rad) / 9.8 * 0.8 if launch_angle > 0 else 20

        # 打球タイプ分類
        ball_type = 'ground_ball'
        if launch_angle >= 25:
            ball_type = 'fly_ball'
        elif 10 <= launch_angle < 25:
            ball_type = 'line_drive'

        # 結果判定
        result = "groundout"
        rbi = 0
        detail = {'type': 'out', 'ball_type': ball_type, 'distance': distance}

        # ホームラン判定
        if launch_angle >= 20 and launch_angle <= 45 and distance >= 105:
            result = "home_run"
            rbi = 1
            detail = {'type': 'home_run', 'distance': distance}
        # フライ
        elif launch_angle >= 15:
            catch_prob = 0.82 - (distance - 70) / 80
            if random.random() > catch_prob and distance >= 60:
                if distance >= 100:
                    result = "triple"
                    detail = {'type': 'triple'}
                elif distance >= 80:
                    result = "double"
                    detail = {'type': 'double'}
                else:
                    result = "single"
                    detail = {'type': 'single'}
            else:
                result = "flyout"
                detail = {'type': 'flyout', 'ball_type': 'fly_ball'}
        # ライナー
        elif 5 <= launch_angle < 15:
            hit_prob = 0.30 + (exit_velocity - 100) * 0.004 + (contact - 100) * 0.002
            if random.random() < hit_prob:
                result = "single"
                detail = {'type': 'single'}
            else:
                result = "lineout"
                detail = {'type': 'lineout', 'ball_type': 'line_drive'}
        # ゴロ
        else:
            hit_prob = 0.22 + (exit_velocity - 100) * 0.003 + (speed - 100) * 0.002
            if random.random() < hit_prob:
                result = "single"
                detail = {'type': 'single'}
            else:
                result = "groundout"
                detail = {'type': 'groundout', 'ball_type': 'ground_ball'}

        return result, rbi, detail

    def simulate_inning(self, batting_team: Team, pitching_team: Team, batter_idx: int) -> Tuple[int, int]:
        """1イニングをシミュレート"""
        outs = 0
        runs = 0
        runners = [False, False, False]

        lineup = self.get_lineup(batting_team)
        if len(lineup) < 9:
            return 0, batter_idx

        rotation = self.get_rotation(pitching_team)
        if not rotation:
            return 0, batter_idx

        pitcher_idx = rotation[0]  # 簡易：先発固定
        if pitcher_idx >= len(pitching_team.players):
            return 0, batter_idx
        pitcher = pitching_team.players[pitcher_idx]

        while outs < 3:
            b_idx = lineup[batter_idx % len(lineup)]
            if b_idx >= len(batting_team.players):
                batter_idx += 1
                continue
            batter = batting_team.players[b_idx]

            result, extra_rbi, detail = self.simulate_at_bat(batter, pitcher)

            if result in ["groundout", "flyout", "lineout", "strikeout"]:
                outs += 1
                # 打球タイプを記録
                if detail.get('ball_type') == 'ground_ball':
                    self.player_stats[batter.name]['ground_balls'] += 1
                elif detail.get('ball_type') == 'fly_ball':
                    self.player_stats[batter.name]['fly_balls'] += 1
                elif detail.get('ball_type') == 'line_drive':
                    self.player_stats[batter.name]['line_drives'] += 1
            elif result == "walk":
                if all(runners):
                    runs += 1
                runners = [True, runners[0], runners[1]]
            elif result == "home_run":
                score = 1 + sum(runners)
                runs += score
                runners = [False, False, False]
                self.player_stats[batter.name]['pa'] += 1
                self.player_stats[batter.name]['ab'] += 1
                self.player_stats[batter.name]['hits'] += 1
                self.player_stats[batter.name]['hr'] += 1
                self.player_stats[batter.name]['rbi'] += score
                self.player_stats[batter.name]['runs'] += 1
                self.player_stats[pitcher.name]['h_allowed'] += 1
            elif result in ["single", "double", "triple"]:
                self.player_stats[batter.name]['pa'] += 1
                self.player_stats[batter.name]['ab'] += 1
                self.player_stats[batter.name]['hits'] += 1

                # ランナー進塁（簡易版）
                rbi = sum(runners)
                if result == "single":
                    if runners[2]:
                        runs += 1
                        rbi = 1
                    runners = [True, runners[0], runners[1]]
                elif result == "double":
                    runs += sum(runners[1:])
                    rbi = sum(runners[1:])
                    runners = [False, True, runners[0]]
                    self.player_stats[batter.name]['doubles'] += 1
                elif result == "triple":
                    runs += sum(runners)
                    rbi = sum(runners)
                    runners = [False, False, True]
                    self.player_stats[batter.name]['triples'] += 1

                self.player_stats[batter.name]['rbi'] += rbi
                self.player_stats[pitcher.name]['h_allowed'] += 1

            batter_idx += 1

        return runs, batter_idx

    def simulate_game(self, date: str = "") -> FarmGameResult:
        """1試合をシミュレート"""
        self.home_score = 0
        self.away_score = 0
        self.player_stats = {}

        h_idx = 0
        a_idx = 0

        for inning in range(9):
            # 表（アウェイ攻撃）
            runs, a_idx = self.simulate_inning(self.away_team, self.home_team, a_idx)
            self.away_score += runs

            # 9回裏で勝っていたらスキップ
            if inning == 8 and self.home_score > self.away_score:
                break

            # 裏（ホーム攻撃）
            runs, h_idx = self.simulate_inning(self.home_team, self.away_team, h_idx)
            self.home_score += runs

        # 投手成績を計算（簡易版：9イニング投げたとする）
        self._finalize_pitcher_stats()

        return FarmGameResult(
            team_level=self.team_level,
            home_team_name=self.home_team.name,
            away_team_name=self.away_team.name,
            home_score=self.home_score,
            away_score=self.away_score,
            date=date,
            player_stats=self.player_stats.copy()
        )

    def _finalize_pitcher_stats(self):
        """投手成績を確定"""
        # ホーム先発投手
        home_rotation = self.get_rotation(self.home_team)
        if home_rotation:
            pitcher = self.home_team.players[home_rotation[0]]
            self.init_player_stats(pitcher.name)
            self.player_stats[pitcher.name]['ip'] = 9.0

        # アウェイ先発投手
        away_rotation = self.get_rotation(self.away_team)
        if away_rotation:
            pitcher = self.away_team.players[away_rotation[0]]
            self.init_player_stats(pitcher.name)
            self.player_stats[pitcher.name]['ip'] = 9.0


class FarmLeagueManager:
    """二軍・三軍リーグ管理"""

    def __init__(self, teams: List[Team]):
        self.teams = teams

    def simulate_farm_games(self, date: str, exclude_team: Optional[str] = None) -> List[FarmGameResult]:
        """二軍・三軍の試合を一括シミュレート"""
        results = []

        # 二軍戦
        farm_results = self._simulate_level_games(TeamLevel.SECOND, date, exclude_team)
        results.extend(farm_results)

        # 三軍戦
        third_results = self._simulate_level_games(TeamLevel.THIRD, date, exclude_team)
        results.extend(third_results)

        return results

    def _simulate_level_games(self, level: TeamLevel, date: str,
                               exclude_team: Optional[str] = None) -> List[FarmGameResult]:
        """特定レベルの試合をシミュレート"""
        results = []

        # チームをシャッフルしてマッチング
        available_teams = [t for t in self.teams if t.name != exclude_team]
        random.shuffle(available_teams)

        # ペアを作成
        for i in range(0, len(available_teams) - 1, 2):
            home = available_teams[i]
            away = available_teams[i + 1]

            sim = FarmGameSimulator(home, away, level)
            result = sim.simulate_game(date)
            results.append(result)

            # 成績を反映
            self._apply_game_stats(result)

        return results

    def _apply_game_stats(self, result: FarmGameResult):
        """試合成績を選手に反映"""
        for team in self.teams:
            for player in team.players:
                if player.name in result.player_stats:
                    stats = result.player_stats[player.name]
                    record = player.get_record_by_level(result.team_level)

                    # 打撃成績
                    record.plate_appearances += stats.get('pa', 0)
                    record.at_bats += stats.get('ab', 0)
                    record.hits += stats.get('hits', 0)
                    record.doubles += stats.get('doubles', 0)
                    record.triples += stats.get('triples', 0)
                    record.home_runs += stats.get('hr', 0)
                    record.rbis += stats.get('rbi', 0)
                    record.runs += stats.get('runs', 0)
                    record.walks += stats.get('bb', 0)
                    record.strikeouts += stats.get('k', 0)
                    record.stolen_bases += stats.get('sb', 0)
                    record.ground_balls += stats.get('ground_balls', 0)
                    record.fly_balls += stats.get('fly_balls', 0)
                    record.line_drives += stats.get('line_drives', 0)

                    # 投手成績
                    if stats.get('ip', 0) > 0:
                        record.games_pitched += 1
                        record.innings_pitched += stats.get('ip', 0)
                        record.hits_allowed += stats.get('h_allowed', 0)
                        record.walks_allowed += stats.get('bb_allowed', 0)
                        record.strikeouts_pitched += stats.get('k_pitched', 0)

                    # 出場試合数
                    if stats.get('pa', 0) > 0 or stats.get('ip', 0) > 0:
                        record.games += 1


def simulate_farm_games_for_day(teams: List[Team], date: str,
                                 player_team_name: str = None) -> List[FarmGameResult]:
    """その日の二軍・三軍戦をまとめてシミュレート"""
    manager = FarmLeagueManager(teams)
    # 自チームの一軍は別で試合をするので、二軍三軍は裏で計算
    results = manager.simulate_farm_games(date, exclude_team=None)
    return results
