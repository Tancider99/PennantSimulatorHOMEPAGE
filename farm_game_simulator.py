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
            
        # 成績反映 (修正: 引数なし)
        self.engine.finalize_game_stats()
        
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
        # 野手リスト（投手以外）
        candidates = [p for p in roster if p.position != Position.PITCHER]
        
        # 人数不足時は投手も含める（緊急措置）
        if len(candidates) < 9:
            candidates = roster
        
        # スコア計算関数（年齢ボーナス＋ランダム性）
        def get_score(p):
            # 基本能力 (0-100 scale * factor)
            ability = p.stats.overall_batting()
            
            # 年齢補正: 若いほど高スコア (28歳以下に強いボーナス)
            # 22歳以下はさらに優遇
            age_bonus = max(0, 28 - p.age) * 4.0
            if p.age <= 22: age_bonus += 10
            
            # ランダム性: 毎回大きく変動させることで固定化を防ぐ (0-40)
            # これにより能力が低くてもチャンスが回ってくる
            rand = random.uniform(0, 40)
            
            # 調子補正: 調子が良い選手を使う
            cond = (p.condition - 5) * 4.0
            
            return ability * 0.4 + age_bonus + rand + cond

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
        
        # 上位の選手を「本日のスタメン候補」としてピックアップ
        # 少し多めに候補を選び、その中からポジション最適化を行う
        candidate_count = min(len(scored_players), 13)
        if candidate_count < 9: candidate_count = len(scored_players)
        
        top_candidates = [x[1] for x in scored_players[:candidate_count]]
        
        # 万が一9人に満たない場合は全員リストに戻す
        if len(top_candidates) < 9:
            top_candidates = [x[1] for x in scored_players]
            
        # 選抜メンバーで最適なポジション配置を行う
        final_lineup = generate_best_lineup(team, top_candidates)
        
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