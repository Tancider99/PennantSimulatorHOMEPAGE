# -*- coding: utf-8 -*-
"""
二軍・三軍試合シミュレーター (本格版: LiveGameEngine使用 + 守備適正考慮オーダー + 若手起用・固定防止)
"""
import random
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from models import Team, Player, Position, TeamLevel, generate_best_lineup
from live_game_engine import LiveGameEngine, GameState

@dataclass
class FarmGameResult:
    team_level: TeamLevel
    home_team_name: str
    away_team_name: str
    home_score: int
    away_score: int
    date: str

class FarmGameSimulator:
    """LiveGameEngineを使用した二軍・三軍試合シミュレーター"""

    def __init__(self, home_team: Team, away_team: Team, team_level: TeamLevel = TeamLevel.SECOND):
        self.home_team = home_team
        self.away_team = away_team
        self.team_level = team_level
        # 本格シミュレーションエンジンを使用
        self.engine = LiveGameEngine(home_team, away_team, team_level)

    def simulate_game(self, date: str = "") -> FarmGameResult:
        """1試合を完全にシミュレート"""
        
        # 試合実行
        while not self.engine.is_game_over():
            self.engine.simulate_pitch()
            
        # 成績反映
        self.engine.finalize_game_stats(date)
        
        return FarmGameResult(
            team_level=self.team_level,
            home_team_name=self.home_team.name,
            away_team_name=self.away_team.name,
            home_score=self.engine.state.home_score,
            away_score=self.engine.state.away_score,
            date=date
        )

class FarmLeagueManager:
    def __init__(self, teams: List[Team]):
        self.teams = teams

    def simulate_farm_games(self, date: str, exclude_team: Optional[str] = None) -> List[FarmGameResult]:
        results = []
        # 二軍戦
        results.extend(self._simulate_level_games(TeamLevel.SECOND, date, exclude_team))
        # 三軍戦
        results.extend(self._simulate_level_games(TeamLevel.THIRD, date, exclude_team))
        return results

    def _simulate_level_games(self, level: TeamLevel, date: str, exclude_team: str) -> List[FarmGameResult]:
        results = []
        # 全チーム対象 (exclude_teamがNoneなら自チームも含まれる)
        target_teams = [t for t in self.teams if t.name != exclude_team]
        random.shuffle(target_teams)

        for i in range(0, len(target_teams) - 1, 2):
            home = target_teams[i]
            away = target_teams[i+1]
            
            # 試合ごとにオーダーを再生成する（固定化防止・若手起用）
            self._update_lineup_for_game(home, level)
            self._update_lineup_for_game(away, level)
            
            # 投手ローテの確認（簡易的に先発がいない場合は設定）
            self._check_and_fix_rotation(home, level)
            self._check_and_fix_rotation(away, level)
            
            sim = FarmGameSimulator(home, away, level)
            res = sim.simulate_game(date)
            results.append(res)
        
        return results

    def _update_lineup_for_game(self, team: Team, level: TeamLevel):
        """
        試合ごとにオーダーを生成する
        年齢（若手優先）・能力・ランダム性を加味して出場選手を決定
        """
        roster = team.get_players_by_level(level)
        # 野手リスト（投手以外）- 怪我人を除く
        candidates = [p for p in roster if p.position != Position.PITCHER and not p.is_injured]
        
        # 人数不足時は投手も含める（緊急措置）
        if len(candidates) < 9:
            candidates = [p for p in roster if not p.is_injured]
        
        # スコア計算関数（年齢ボーナス＋ランダム性）
        def get_score(p):
            # 基本能力 (0-100 scale * factor)
            ability = p.stats.overall_batting()
            
            # 年齢補正: 若いほど高スコア (28歳以下に強いボーナス)
            # 22歳以下はさらに優遇
            age_bonus = max(0, 28 - p.age) * 4.0
            if p.age <= 22: age_bonus += 10
            
            # ランダム性: 毎回大きく変動させることで固定化を防ぐ (0-60に拡大)
            # これにより能力が低くてもチャンスが回ってくる確率を上げる
            rand = random.uniform(0, 60)
            
            # 調子補正: 調子が良い選手を使う
            cond = (p.condition - 5) * 4.0
            
            # 打席数が極端に少ない選手を優先する補正（0打席防止）
            rec = p.get_record_by_level(level)
            pa_bonus = 0
            if rec.plate_appearances < 5: pa_bonus = 80 # 強制的に出場させるレベルの補正
            elif rec.plate_appearances < 20: pa_bonus = 30
            
            return ability * 0.4 + age_bonus + rand + cond + pa_bonus

        # 評価値付きリスト作成
        scored_players = []
        for p in candidates:
            try:
                # チーム内のインデックスを取得
                idx = team.players.index(p)
                scored_players.append((idx, p, get_score(p)))
            except ValueError:
                continue
            
        # スコア順にソート（起用優先度順）
        scored_players.sort(key=lambda x: x[2], reverse=True)
        
        # スタメン候補として上位から選出
        # 確実に試合に出すため、generate_best_lineupに渡す人数を絞る
        # ただし、捕手が含まれていないとエラーや不整合の原因になるため、捕手を必ず1名は含める
        top_candidates_objects = []
        
        # まず捕手を確保
        catchers = [x for x in scored_players if x[1].position == Position.CATCHER]
        if catchers:
            top_candidates_objects.append(catchers[0][1])
            # 選んだ捕手をリストから除外して重複防止（後でセットにするので）
            scored_players.remove(catchers[0])
            
        # 残りの枠を埋める (合計11人程度渡して、generate_best_lineupに9人選ばせる)
        # 枠を絞ることで、スコア上位（＝出場させたい若手や0打席の選手）が確実に使われるようにする
        needed = 11 - len(top_candidates_objects)
        for x in scored_players[:needed]:
            top_candidates_objects.append(x[1])
            
        # 万が一9人に満たない場合は全員リストに戻す
        if len(top_candidates_objects) < 9:
            top_candidates_objects = [x[1] for x in scored_players]
            
        # 選抜メンバーで最適なポジション配置を行う
        # generate_best_lineupは渡されたリストの中から最適な9人を選ぶ
        final_lineup = generate_best_lineup(team, top_candidates_objects, ignore_restriction=True)
        
        # 生成したラインナップをセット
        if level == TeamLevel.SECOND:
            team.farm_lineup = final_lineup
        else:
            team.third_lineup = final_lineup

    def _check_and_fix_rotation(self, team: Team, level: TeamLevel):
        """指定レベルのローテーションが不備なら自動設定"""
        current_rotation = team.farm_rotation if level == TeamLevel.SECOND else team.third_rotation
        if not current_rotation:
            team.auto_assign_pitching_roles(level)

def simulate_farm_games_for_day(teams: List[Team], date: str, player_team_name: str = None):
    """その日の二軍・三軍戦をまとめてシミュレート"""
    manager = FarmLeagueManager(teams)
    manager.simulate_farm_games(date, exclude_team=None)