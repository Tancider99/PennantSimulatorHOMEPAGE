# -*- coding: utf-8 -*-
"""
セイバーメトリクス計算・統計処理エンジン (修正版: wRC+完全整合化・環境補正制限撤廃・ROE修正・リーグwOBA基準値修正)
"""
from models import Team, Player, Position, TeamLevel, PlayerRecord
from typing import List, Dict

class LeagueStatsCalculator:
    """リーグ全体の統計と係数を計算する（レベル別）"""

    def __init__(self, teams: List[Team]):
        self.teams = teams
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
        self.park_factor = 1.0 

    def _create_empty_totals(self):
        return {
            "PA": 0, "AB": 0, "H": 0, "1B": 0, "2B": 0, "3B": 0, "HR": 0,
            "BB": 0, "IBB": 0, "HBP": 0, "SF": 0, "SH": 0, 
            "R": 0,   # 打者の得点合計
            "RA": 0,  # 投手の失点合計
            "IP": 0.0, "K": 0,
            "TB": 0, "FB": 0, "ROE": 0
        }

    def calculate_all(self):
        """全レベルの計算を実行"""
        self._aggregate_league_totals()
        for level in [TeamLevel.FIRST, TeamLevel.SECOND, TeamLevel.THIRD]:
            self._calculate_coefficients(level)
            self._calculate_player_advanced_stats(level)
        self._aggregate_team_stats()

    def _aggregate_league_totals(self):
        """全チーム・全レベルの合計値を集計"""
        for team in self.teams:
            for player in team.players:
                self._add_to_totals(player.record, TeamLevel.FIRST)
                self._add_to_totals(player.record_farm, TeamLevel.SECOND)
                self._add_to_totals(player.record_third, TeamLevel.THIRD)

    def _add_to_totals(self, r: PlayerRecord, level: TeamLevel):
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
        t["RA"] += r.runs_allowed
        t["IP"] += r.innings_pitched
        t["K"] += r.strikeouts
        t["TB"] += r.total_bases
        t["FB"] += r.fly_balls
        t["ROE"] += r.reach_on_error

    def _calculate_coefficients(self, level: TeamLevel):
        """リーグ成績から係数を算出 (環境連動型Linear Weights・制限撤廃)"""
        t = self.league_totals[level]
        c = {}
        
        # --- 1. 基礎データの準備 ---
        league_runs = max(t["R"], t["RA"])
        league_pa = t["PA"] if t["PA"] > 0 else 1
        
        # リーグR/PA (得点環境)
        lg_r_pa = league_runs / league_pa if league_pa > 0 else 0.12
        c["league_r_pa"] = lg_r_pa

        # --- 2. Run Values (得点価値) の算出 ---
        base_r_pa = 0.116
        env_factor = lg_r_pa / base_r_pa if base_r_pa > 0 else 1.0
        if env_factor < 0.01: env_factor = 0.01

        run_values = {
            "uBB": 0.33 * env_factor,
            "HBP": 0.36 * env_factor,
            "1B": 0.48 * env_factor,
            "2B": 0.79 * env_factor,
            "3B": 1.08 * env_factor,
            "HR": 1.42 * env_factor,
            "ROE": 0.48 * env_factor
        }
        
        if t["IP"] > 0:
            r_per_out = league_runs / (t["IP"] * 3)
        else:
            outs = max(1, t["AB"] - t["H"] + t["SF"])
            r_per_out = league_runs / outs if outs > 0 else 0.157

        # --- 3. wOBA係数 (Raw) の算出 ---
        value_not_out = r_per_out

        raw_weights = {
            "uBB": run_values["uBB"] + value_not_out,
            "HBP": run_values["HBP"] + value_not_out,
            "1B": run_values["1B"] + value_not_out,
            "2B": run_values["2B"] + value_not_out,
            "3B": run_values["3B"] + value_not_out,
            "HR": run_values["HR"] + value_not_out,
            "ROE": run_values["ROE"] + value_not_out
        }

        # --- 4. wOBA Scale の算出 ---
        # リーグwOBA(Raw)を計算
        lg_woba_raw = self._calc_league_woba_val(t, raw_weights)

        # リーグOBPを計算
        denom_woba = t["AB"] + t["BB"] - t["IBB"] + t["SF"] + t["HBP"]
        lg_oba = (t["H"] + t["BB"] + t["HBP"]) / denom_woba if denom_woba > 0 else 0.320

        # スケール係数
        if lg_woba_raw > 0:
            woba_scale = lg_oba / lg_woba_raw
        else:
            woba_scale = 1.25

        # --- 5. 最終的な係数の決定 ---
        final_woba_weights = {k: v * woba_scale for k, v in raw_weights.items()}
        
        c["woba_weights"] = final_woba_weights
        c["woba_scale"] = woba_scale
        
        # リーグwOBA
        c["league_woba"] = lg_woba_raw * woba_scale 

        # --- FIP Constant ---
        # FIP定数 = リーグ全体の失点率 - リーグFIP生値
        # FIP = (13×HR + 3×(BB-IBB+HBP) - 2×K) / IP + 定数
        if t["IP"] > 0:
            league_era = (league_runs * 9) / t["IP"]
            ubb = max(0, t["BB"] - t["IBB"])  # 故意四球を除外
            fip_raw = (13 * t["HR"] + 3 * (ubb + t["HBP"]) - 2 * t["K"]) / t["IP"]
            c["fip_constant"] = league_era - fip_raw
            c["league_fip"] = league_era 
        else:
            c["fip_constant"] = 3.10
            c["league_fip"] = 4.00
            
        if t["FB"] > 0:
            c["league_hr_fb"] = t["HR"] / t["FB"]
        else:
            c["league_hr_fb"] = 0.10 

        c["runs_per_win"] = 10.0
        
        self.coefficients[level] = c

    def _calc_league_woba_val(self, t, w):
        denom = t["AB"] + t["BB"] - t["IBB"] + t["HBP"] + t["SF"]
        if denom <= 0: return 0.0
        
        uBB = max(0, t["BB"] - t["IBB"])
        val = (w["uBB"] * uBB + 
               w["HBP"] * t["HBP"] + 
               w["ROE"] * t["ROE"] +
               w["1B"] * t["1B"] + 
               w["2B"] * t["2B"] + 
               w["3B"] * t["3B"] + 
               w["HR"] * t["HR"])
        return val / denom

    def _calculate_player_advanced_stats(self, level: TeamLevel):
        """指定レベルの全選手の指標を更新"""
        c = self.coefficients[level]
        for team in self.teams:
            team_pf = team.stadium.pf_runs if team.stadium else 1.0
            for player in team.players:
                record = player.get_record_by_level(level)
                self._update_single_record(player, record, c, team_pf)

    def _update_single_record(self, player: Player, r: PlayerRecord, c: dict, team_pf: float):
        """個人の成績を更新する"""
        if r.plate_appearances == 0 and r.innings_pitched == 0:
            return

        w = c["woba_weights"]
        lg_woba = c["league_woba"]
        lg_r_pa = c["league_r_pa"]
        woba_scale = c["woba_scale"]
        fip_const = c["fip_constant"]
        rpw = c["runs_per_win"]

        # PF算出
        if r.plate_appearances > 0:
            personal_pf_batter = r.sum_pf_runs / r.plate_appearances
        else:
            personal_pf_batter = 1.0
            
        tbf_approx = r.hits_allowed + r.walks_allowed + r.hit_batters + r.strikeouts_pitched + (r.innings_pitched * 3)
        if tbf_approx > 0:
            personal_pf_pitcher = r.sum_pf_runs / tbf_approx 
        else:
            personal_pf_pitcher = 1.0
            
        if personal_pf_batter == 0: personal_pf_batter = 1.0
        if personal_pf_pitcher == 0: personal_pf_pitcher = 1.0

        # --- Batting Stats ---
        if r.plate_appearances > 0:
            # wOBA Calculation
            denominator = r.at_bats + r.walks - r.intentional_walks + r.hit_by_pitch + r.sacrifice_flies
            if denominator > 0:
                uBB = max(0, r.walks - r.intentional_walks)
                numerator = (w["uBB"] * uBB + 
                             w["HBP"] * r.hit_by_pitch + 
                             w["ROE"] * r.reach_on_error +
                             w["1B"] * r.singles + 
                             w["2B"] * r.doubles + 
                             w["3B"] * r.triples + 
                             w["HR"] * r.home_runs)
                r.woba_val = numerator / denominator
            else:
                r.woba_val = 0.0

            # --- wRAA Calculation (Unadjusted) ---
            divisor = woba_scale if woba_scale > 0 else 1.25
            wraa = ((r.woba_val - lg_woba) / divisor) * r.plate_appearances
            r.wraa_val = wraa

            # --- Park Adjustment ---
            games_ratio = r.home_games / r.games if r.games > 0 else 0.5
            pf_correction_coefficient = games_ratio * team_pf + (1.0 - games_ratio) * ((6.0 - team_pf) / 5.0)
            
            # パーク補正値（打者有利ならマイナス）
            pf_correction_value = (1.0 - pf_correction_coefficient) * lg_r_pa * r.plate_appearances
            
            # 補正後wRAA (Batting Runs)
            adjusted_wraa = wraa + pf_correction_value
            
            # --- wRC Calculation (Fix: Raw wRAA) ---
            # wRCはパーク補正を含まない、純粋な創出得点数
            r.wrc_val = wraa + (lg_r_pa * r.plate_appearances)

            # --- wRC+ Calculation (Fix: Use Park Adjusted wRAA) ---
            # wRC+はパーク補正を含めた創出得点をリーグ平均と比較する
            park_adjusted_wrc = adjusted_wraa + (lg_r_pa * r.plate_appearances)
            
            if lg_r_pa > 0:
                league_expected_runs = lg_r_pa * r.plate_appearances
                if league_expected_runs > 0.0001:
                    r.wrc_plus_val = 100 * park_adjusted_wrc / league_expected_runs
                else:
                    r.wrc_plus_val = 100.0
            else:
                r.wrc_plus_val = 100.0
                
            # RC (Runs Created) Calculation
            val_A = r.hits + r.walks + r.hit_by_pitch - r.caught_stealing - r.grounded_into_dp
            val_B = r.total_bases + 0.26 * (r.walks - r.intentional_walks + r.hit_by_pitch) + 0.52 * (r.sacrifice_hits + r.sacrifice_flies + r.stolen_bases)
            val_C = r.at_bats + r.walks + r.hit_by_pitch + r.sacrifice_hits + r.sacrifice_flies
            
            if val_C > 0:
                r.rc_val = (val_A * val_B) / val_C
            else:
                r.rc_val = 0.0
                
            # RC/27
            outs = r.at_bats - r.hits + r.caught_stealing + r.sacrifice_hits + r.sacrifice_flies + r.grounded_into_dp
            if outs > 0:
                r.rc27_val = r.rc_val / (outs / 27.0)
            else:
                r.rc27_val = 0.0
            
        # --- Pitching Stats ---
        if r.innings_pitched > 0:
            # FIP = (13×HR + 3×(BB-IBB+HBP) - 2×K) / IP + 定数
            ubb = max(0, r.walks_allowed - r.intentional_walks_allowed)
            fip_val = (13 * r.home_runs_allowed + 3 * (ubb + r.hit_batters) - 2 * r.strikeouts_pitched) / r.innings_pitched
            r.fip_val = fip_val + fip_const
            
            # xFIP = (13×(lg_HR/FB×FB) + 3×(BB-IBB+HBP) - 2×K) / IP + 定数
            lg_hr_fb = c.get("league_hr_fb", 0.10)
            expected_hr = r.fly_balls * lg_hr_fb
            xfip_val = (13 * expected_hr + 3 * (ubb + r.hit_batters) - 2 * r.strikeouts_pitched) / r.innings_pitched
            r.xfip_val = xfip_val + fip_const

        # --- Defensive Stats ---
        r.drs_val = r.def_drs_raw
        r.uzr_val = r.def_drs_raw * 0.9

        # --- WAR Calculation ---
        if player.position.value != "投手":
            # Batting Runs (Park Adjusted)
            batting_runs = adjusted_wraa if r.plate_appearances > 0 else 0
            
            # wSB (Weighted Stolen Base Runs)
            wsb = (r.stolen_bases * 0.2) - (r.caught_stealing * 0.4)
            r.wsb_val = wsb
            
            # UBR (Ultimate Base Running)
            if not hasattr(r, 'ubr_val'): r.ubr_val = 0.0 
            
            bsr = wsb + r.ubr_val
            fielding_runs = r.uzr_val
            
            # Positional Adjustment
            pos_val_map = {
                "捕手": 18.1, "遊撃手": 10.3, "二塁手": 3.4, "三塁手": -4.8, "中堅手": 4.2,
                "左翼手": -12.0, "右翼手": -5.0,"一塁手": -14.1, "DH": -15.1
            }
            pos_base = pos_val_map.get(player.position.value, 0)
            
            # ★修正: 守備位置補正を守備イニングベースに変更（DH以外）
            if player.position == Position.DH:
                 pos_adj = pos_base * (r.plate_appearances / 600.0)
            else:
                 if r.defensive_innings > 0:
                     # 162試合 * 9回 = 1458イニング基準
                     pos_adj = pos_base * (r.defensive_innings / 1458.0)
                 else:
                     pos_adj = pos_base * (r.plate_appearances / 600.0)

            # Replacement Runs
            # User request: Raise Batter WAR. Increasing replacement level constant increases WAR (as it's runs above replacement).
            rep_runs = 25.0 * (r.plate_appearances / 600.0)
            
            total_runs = batting_runs + bsr + fielding_runs + pos_adj + rep_runs
            r.war_val = total_runs / rpw
            
        else:
            if r.innings_pitched > 0:
                lg_fip = c.get("league_fip", 4.00)
                
                games_ratio_p = r.home_games_pitched / r.games_pitched if r.games_pitched > 0 else 0.5
                pf_factor_p = games_ratio_p * team_pf + (1.0 - games_ratio_p) * ((6.0 - team_pf) / 5.0)
                
                if pf_factor_p > 0:
                    adjusted_fip = r.fip_val / pf_factor_p
                else:
                    adjusted_fip = r.fip_val

                ra9_diff = lg_fip - adjusted_fip
                runs_saved = ra9_diff * (r.innings_pitched / 9.0)
                
                # User request: Lower Pitcher WAR. Lowering rep_runs reduces the "free value" given to all pitchers.
                rep_runs_per_9 = 0.80
                rep_runs = rep_runs_per_9 * (r.innings_pitched / 9.0)
                
                r.war_val = (runs_saved + rep_runs) / rpw


    def _aggregate_team_stats(self):
        """チームごとの詳細成績を集計してTeamオブジェクトに格納（レベル別）"""
        target_attrs = {
            TeamLevel.FIRST: 'stats_total',
            TeamLevel.SECOND: 'stats_total_farm',
            TeamLevel.THIRD: 'stats_total_third'
        }
        
        for team in self.teams:
            for level, attr_name in target_attrs.items():
                if not hasattr(team, attr_name):
                    continue # Should adhere to model definition
                
                t = getattr(team, attr_name)
                t.reset()
                
                # 集計
                for p in team.players:
                    r = p.get_record_by_level(level)
                    t.merge_from(r)
                
                # 再計算（WAR, FIP, wOBAなど）
                # WAR summation
                t.war_val = sum(p.get_record_by_level(level).war_val for p in team.players)
                
                # Coefficients for this level
                c = self.coefficients.get(level, {})
                if not c: continue # Skip if no games played at this level
                
                if t.innings_pitched > 0:
                    # FIP & xFIP
                    fip_const = c.get("fip_constant", 3.10)
                    ubb = max(0, t.walks_allowed - t.intentional_walks_allowed)
                    
                    fip_val = (13 * t.home_runs_allowed + 3 * (ubb + t.hit_batters) - 2 * t.strikeouts_pitched) / t.innings_pitched
                    t.fip_val = fip_val + fip_const
                    
                    lg_hr_fb = c.get("league_hr_fb", 0.10)
                    expected_hr = t.fly_balls * lg_hr_fb
                    xfip_val = (13 * expected_hr + 3 * (ubb + t.hit_batters) - 2 * t.strikeouts_pitched) / t.innings_pitched
                    t.xfip_val = xfip_val + fip_const
                
                if t.plate_appearances > 0:
                    # wOBA
                    w = c.get("woba_weights", {})
                    denom = t.at_bats + t.walks - t.intentional_walks + t.hit_by_pitch + t.sacrifice_flies
                    if denom > 0:
                        uBB = max(0, t.walks - t.intentional_walks)
                        num = (w.get("uBB",0) * uBB + 
                               w.get("HBP",0) * t.hit_by_pitch + 
                               w.get("ROE",0) * t.reach_on_error +
                               w.get("1B",0) * t.singles + 
                               w.get("2B",0) * t.doubles + 
                               w.get("3B",0) * t.triples + 
                               w.get("HR",0) * t.home_runs)
                        t.woba_val = num / denom
                    
                    # wRC, wRAA, wRC+
                    lg_woba = c.get("league_woba", 0.300)
                    woba_scale = c.get("woba_scale", 1.20)
                    lg_r_pa = c.get("league_r_pa", 0.12)
                    
                    divisor = woba_scale if woba_scale > 0 else 1.25
                    wraa = ((t.woba_val - lg_woba) / divisor) * t.plate_appearances
                    t.wraa_val = wraa
                    
                    # Team wRC+
                    t.wrc_val = wraa + (lg_r_pa * t.plate_appearances)
                    if lg_r_pa * t.plate_appearances > 0:
                        t.wrc_plus_val = 100 * t.wrc_val / (lg_r_pa * t.plate_appearances)
                
                # UZR, DRS summation
                t.drs_val = sum(p.get_record_by_level(level).drs_val for p in team.players)
                t.uzr_val = sum(p.get_record_by_level(level).uzr_val for p in team.players)


def update_league_stats(all_teams: List[Team]):
    """外部から呼び出すためのヘルパー関数"""
    calc = LeagueStatsCalculator(all_teams)
    calc.calculate_all()