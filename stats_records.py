# -*- coding: utf-8 -*-
"""
セイバーメトリクス計算・統計処理エンジン (修正版: 変数参照エラー修正・レベル別対応)
"""
from models import Team, Player, Position, TeamLevel, PlayerRecord
from typing import List, Dict

class LeagueStatsCalculator:
    """リーグ全体の統計と係数を計算する（レベル別）"""

    def __init__(self, teams: List[Team]):
        self.teams = teams
        # レベルごとの集計データを保持
        self.league_totals = {
            TeamLevel.FIRST: self._create_empty_totals(),
            TeamLevel.SECOND: self._create_empty_totals(),
            TeamLevel.THIRD: self._create_empty_totals()
        }
        self.coefficients = {
            TeamLevel.FIRST: {},
            TeamLevel.SECOND: {},
            TeamLevel.THIRD: {}
        }
        self.park_factor = 1.0 # 簡易的に1.0

    def _create_empty_totals(self):
        return {
            "PA": 0, "AB": 0, "H": 0, "1B": 0, "2B": 0, "3B": 0, "HR": 0,
            "BB": 0, "IBB": 0, "HBP": 0, "SF": 0, "SH": 0, "R": 0, "IP": 0.0, "K": 0,
            "TB": 0, "FB": 0 # Fly Balls
        }

    def calculate_all(self):
        """全レベルの計算を実行"""
        # 1. 集計
        self._aggregate_league_totals()
        
        # 2. 係数計算 & 適用
        for level in [TeamLevel.FIRST, TeamLevel.SECOND, TeamLevel.THIRD]:
            self._calculate_coefficients(level)
            self._calculate_player_advanced_stats(level)

    def _aggregate_league_totals(self):
        """全チーム・全レベルの合計値を集計"""
        for team in self.teams:
            for player in team.players:
                # 各レベルのレコードを集計
                self._add_to_totals(player.record, TeamLevel.FIRST)
                self._add_to_totals(player.record_farm, TeamLevel.SECOND)
                self._add_to_totals(player.record_third, TeamLevel.THIRD)

    def _add_to_totals(self, r: PlayerRecord, level: TeamLevel):
        """レコードを該当レベルの合計に加算"""
        t = self.league_totals[level]
        if r.plate_appearances == 0 and r.innings_pitched == 0:
            return

        t["PA"] += r.plate_appearances
        t["AB"] += r.at_bats
        t["H"] += r.hits
        t["1B"] += r.singles
        t["2B"] += r.doubles
        t["3B"] += r.triples
        t["HR"] += r.home_runs
        t["BB"] += r.walks
        t["IBB"] += r.intentional_walks
        t["HBP"] += r.hit_by_pitch
        t["SF"] += r.sacrifice_flies
        t["SH"] += r.sacrifice_hits
        t["R"] += r.runs
        t["IP"] += r.innings_pitched
        t["K"] += r.strikeouts
        t["TB"] += r.total_bases
        t["FB"] += r.fly_balls

    def _calculate_coefficients(self, level: TeamLevel):
        """リーグ成績から係数を算出 (レベル別)"""
        t = self.league_totals[level]
        c = {}
        
        # --- wOBA Weights (Guts法簡易版 + リーグ補正) ---
        # リーグ出塁率
        denom_oba = t["AB"] + t["BB"] + t["HBP"] + t["SF"]
        if denom_oba > 0:
            league_oba = (t["H"] + t["BB"] + t["HBP"]) / denom_oba
        else:
            league_oba = 0.320

        # Run per Out (R / Outs)
        if t["IP"] > 0:
            outs = t["IP"] * 3
        else:
            outs = max(1, t["AB"] - t["H"])

        if outs <= 0: r_per_out = 0.15
        else: r_per_out = t["R"] / outs

        # 係数スケーリング (MLB平均 0.18 R/Out を基準)
        scale = r_per_out / 0.18 if r_per_out > 0 else 1.0
        
        c["woba_weights"] = {
            "uBB": 0.69 * scale,
            "HBP": 0.72 * scale,
            "1B": 0.89 * scale,
            "2B": 1.27 * scale,
            "3B": 1.62 * scale,
            "HR": 2.10 * scale
        }
        
        c["woba_scale"] = 1.20 # 一般的なスケール定数
        c["league_woba"] = self._calc_league_woba_val(t, c["woba_weights"])
        c["league_r_pa"] = t["R"] / t["PA"] if t["PA"] > 0 else 0.12

        # --- FIP Constant ---
        if t["IP"] > 0:
            league_era = (t["R"] * 9) / t["IP"]
            fip_raw = (13 * t["HR"] + 3 * (t["BB"] + t["HBP"]) - 2 * t["K"]) / t["IP"]
            c["fip_constant"] = league_era - fip_raw
            c["league_fip"] = league_era # League FIP = League ERA by definition
        else:
            c["fip_constant"] = 3.10
            c["league_fip"] = 4.00
            
        # --- League HR/FB ---
        if t["FB"] > 0:
            c["league_hr_fb"] = t["HR"] / t["FB"]
        else:
            c["league_hr_fb"] = 0.10 # Default 10%

        c["runs_per_win"] = 10.0 # 簡易値
        
        self.coefficients[level] = c

    def _calc_league_woba_val(self, t, w):
        if t["PA"] == 0: return 0.320
        # uBB = BB - IBB
        uBB = max(0, t["BB"] - t["IBB"])
        val = (w["uBB"] * uBB + w["HBP"] * t["HBP"] + w["1B"] * t["1B"] + 
               w["2B"] * t["2B"] + w["3B"] * t["3B"] + w["HR"] * t["HR"])
        return val / t["PA"]

    def _calculate_player_advanced_stats(self, level: TeamLevel):
        """指定レベルの全選手の指標を更新"""
        c = self.coefficients[level]
        
        for team in self.teams:
            for player in team.players:
                # 該当レベルのレコードを取得
                record = player.get_record_by_level(level)
                self._update_single_record(player, record, c)

    def _update_single_record(self, player: Player, r: PlayerRecord, c: dict):
        if r.plate_appearances == 0 and r.innings_pitched == 0:
            return

        w = c["woba_weights"]
        lg_woba = c["league_woba"]
        lg_r_pa = c["league_r_pa"]
        woba_scale = c["woba_scale"]
        fip_const = c["fip_constant"]
        rpw = c["runs_per_win"]

        # --- Batting Stats ---
        if r.plate_appearances > 0:
            # wOBA
            uBB = max(0, r.walks - r.intentional_walks)
            numerator = (w["uBB"] * uBB + w["HBP"] * r.hit_by_pitch + 
                         w["1B"] * r.singles + w["2B"] * r.doubles + 
                         w["3B"] * r.triples + w["HR"] * r.home_runs)
            r.woba_val = numerator / r.plate_appearances

            # wRAA (Weighted Runs Above Average)
            wraa = ((r.woba_val - lg_woba) / woba_scale) * r.plate_appearances
            
            # wRC (Weighted Runs Created)
            # wRC = wRAA + (League R/PA * PA)
            r.wrc_val = wraa + (lg_r_pa * r.plate_appearances)
            
            # wRC+ (Weighted Runs Created Plus)
            # Simplified: (wRC/PA) / lgR/PA * 100
            if lg_r_pa > 0:
                r.wrc_plus_val = (r.wrc_val / r.plate_appearances) / lg_r_pa * 100
            else:
                r.wrc_plus_val = 100.0
            
        # --- Pitching Stats ---
        if r.innings_pitched > 0:
            # FIP
            fip_val = (13 * r.home_runs_allowed + 3 * (r.walks_allowed + r.hit_batters) - 2 * r.strikeouts_pitched) / r.innings_pitched
            r.fip_val = fip_val + fip_const
            
            # xFIP
            # League HR/FB Rate
            lg_hr_fb = c.get("league_hr_fb", 0.10)
            expected_hr = r.fly_balls * lg_hr_fb
            xfip_val = (13 * expected_hr + 3 * (r.walks_allowed + r.hit_batters) - 2 * r.strikeouts_pitched) / r.innings_pitched
            r.xfip_val = xfip_val + fip_const

        # --- Defensive Stats (Simplified) ---
        r.drs_val = r.def_drs_raw
        r.uzr_val = r.def_drs_raw * 0.9

        # --- WAR Calculation (Comprehensive) ---
        if player.position.value != "投手":
            # 野手WAR
            # 1. Batting Runs (wRAA)
            batting_runs = ((r.woba_val - lg_woba) / woba_scale) * r.plate_appearances if r.plate_appearances > 0 else 0
            
            # 2. Baserunning Runs
            bsr = (r.stolen_bases * 0.2) - (r.caught_stealing * 0.4)
            
            # 3. Fielding Runs
            fielding_runs = r.uzr_val
            
            # 4. Positional Adjustment
            pos_val_map = {
                "捕手": 12.5, "遊撃手": 7.5, "二塁手": 2.5, "三塁手": 2.5, "外野手": -2.5,
                "一塁手": -12.5, "DH": -17.5
            }
            pos_base = pos_val_map.get(player.position.value, 0)
            pos_adj = pos_base * (r.plate_appearances / 600.0)
            
            # 5. Replacement Level
            rep_runs = 20.0 * (r.plate_appearances / 600.0)
            
            total_runs = batting_runs + bsr + fielding_runs + pos_adj + rep_runs
            r.war_val = total_runs / rpw
            
        else:
            # 投手WAR (FIP Base)
            if r.innings_pitched > 0:
                lg_fip = c.get("league_fip", 4.00)
                
                ra9_diff = lg_fip - r.fip_val
                runs_saved = ra9_diff * (r.innings_pitched / 9.0)
                
                # Replacement Level for Pitchers:
                # Typically defined as winning % .294, or about 2.00 runs/9 worse than avg
                # Here we use a run-based replacement level constant scaled by IP
                rep_runs_per_9 = 2.06 # Approx runs difference between avg and replacement
                rep_runs = rep_runs_per_9 * (r.innings_pitched / 9.0)
                
                r.war_val = (runs_saved + rep_runs) / rpw


def update_league_stats(all_teams: List[Team]):
    """外部から呼び出すためのヘルパー関数"""
    calc = LeagueStatsCalculator(all_teams)
    calc.calculate_all()