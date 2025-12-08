# filename: tancider99/pennantsimulator/PennantSimulator-74e5e1ba92308cf746a532be9f08c61e03fdf900/player_data_manager.py
# -*- coding: utf-8 -*-
"""
固定選手データ管理モジュール
選手データを球団ごとのJSONファイルに保存・読み込み
ファイルを直接編集して選手の名前・能力・背番号などを変更可能
"""
import json
import os
from typing import Dict, List, Any, Optional
from models import (
    Team, Player, PlayerStats, Position, PitchType, 
    PlayerStatus, League, TeamLevel, PlayerRecord
)


class PlayerDataManager:
    """選手データの保存・読み込み管理クラス（球団別ファイル）"""
    
    # スクリプトのディレクトリを基準にデータディレクトリを設定
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(_SCRIPT_DIR, "player_data")
    
    def __init__(self):
        """初期化"""
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """データディレクトリを作成"""
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)
            print(f"データディレクトリを作成しました: {self.DATA_DIR}")
    
    def _get_team_filepath(self, team_name: str) -> str:
        """チームごとのファイルパスを取得"""
        # ファイル名に使えない文字を置換
        safe_name = team_name.replace(" ", "_").replace("/", "_")
        return os.path.join(self.DATA_DIR, f"{safe_name}.json")
    
    def player_to_dict(self, player: Player) -> Dict[str, Any]:
        """PlayerオブジェクトをDict形式に変換（編集しやすい形式・投手/野手別）"""
        from models import Position
        
        is_pitcher = player.position == Position.PITCHER
        
        base_data = {
            "名前": player.name,
            "背番号": player.uniform_number,
            "年齢": player.age,
            "ポジション": player.position.value,
            "外国人": player.is_foreign,
            "年俸": player.salary,
            "プロ年数": player.years_pro,
            "ドラフト順位": player.draft_round,
            "育成選手": player.is_developmental,
            "チームレベル": player.team_level.value if player.team_level else None,
        }
        
        # 共通能力
        base_data["共通能力"] = {
            "ケガしにくさ": player.stats.durability,
            "回復": player.stats.recovery,
            "練習態度": player.stats.work_ethic,
            "野球脳": player.stats.intelligence,
            "メンタル": player.stats.mental
        }
        
        if is_pitcher:
            # 投手の場合
            base_data["球種"] = player.pitch_type.value if player.pitch_type else None
            base_data["先発適性"] = player.starter_aptitude
            base_data["中継ぎ適性"] = player.middle_aptitude
            base_data["抑え適性"] = player.closer_aptitude
            
            # 守備範囲は投手も持つ
            defense_ranges = {}
            if hasattr(player.stats, 'defense_ranges'):
                defense_ranges = player.stats.defense_ranges

            base_data["能力値"] = {
                "球速": player.stats.velocity,
                "コントロール": player.stats.control,
                "スタミナ": player.stats.stamina,
                "変化球": player.stats.stuff,
                "ムーブメント": player.stats.movement,
                "持ち球": player.stats.pitches,
                "対左打者": player.stats.vs_left_pitcher,
                "対ピンチ": player.stats.vs_pinch,
                "安定感": player.stats.stability,
                "ゴロ傾向": player.stats.gb_tendency,
                "クイック": player.stats.hold_runners,
                "守備適正": defense_ranges,
                "肩力": player.stats.arm,
                "捕球": player.stats.error,
                "守備": player.stats.turn_dp, 
            }
        else:
            # 野手の場合
            # サブポジションはdefense_rangesから算出（表示用）
            sub_positions_list = []
            if hasattr(player.stats, 'defense_ranges'):
                 for pos_name, rating in player.stats.defense_ranges.items():
                    if pos_name != player.position.value and rating >= 2:
                        sub_positions_list.append(pos_name)

            base_data["サブポジション"] = sub_positions_list
            
            base_data["能力値"] = {
                "ミート": player.stats.contact,
                "パワー": player.stats.power,
                "走力": player.stats.speed,
                "盗塁": player.stats.steal,
                "走塁": player.stats.baserunning,
                "肩力": player.stats.arm,
                "守備": player.stats.turn_dp, # 併殺処理
                "捕球": player.stats.error,
                "ギャップ": player.stats.gap,
                "選球眼": player.stats.eye,
                "三振回避": player.stats.avoid_k,
                "弾道": player.stats.trajectory,
                "対左投手": player.stats.vs_left_batter,
                "チャンス": player.stats.chance,
                "バント": player.stats.bunt_sac,
                "セーフティ": player.stats.bunt_hit,
                "守備適正": player.stats.defense_ranges,
                "捕手リード": player.stats.catcher_lead
            }
        
        return base_data
    
    def _get_value(self, data: Dict[str, Any], jp_key: str, en_key: str, default):
        """日本語キーと英語キーの両方をチェックして値を取得"""
        if jp_key in data and data[jp_key] is not None:
            return data[jp_key]
        if en_key in data and data[en_key] is not None:
            return data[en_key]
        return default
    
    def dict_to_player(self, data: Dict[str, Any]) -> Player:
        """Dict形式からPlayerオブジェクトを復元（日本語キー対応）"""
        name = self._get_value(data, "名前", "name", "選手")
        uniform_number = self._get_value(data, "背番号", "uniform_number", 0)
        age = self._get_value(data, "年齢", "age", 25)
        position_value = self._get_value(data, "ポジション", "position", "右翼手")
        pitch_type_value = self._get_value(data, "球種", "pitch_type", None)
        is_foreign = self._get_value(data, "外国人", "is_foreign", False)
        salary = self._get_value(data, "年俸", "salary", 10000000)
        years_pro = self._get_value(data, "プロ年数", "years_pro", 0)
        draft_round = self._get_value(data, "ドラフト順位", "draft_round", 0)
        is_developmental = self._get_value(data, "育成選手", "is_developmental", False)
        team_level_value = self._get_value(data, "チームレベル", "team_level", None)
        starter_aptitude = self._get_value(data, "先発適性", "starter_aptitude", 50)
        middle_aptitude = self._get_value(data, "中継ぎ適性", "middle_aptitude", 50)
        closer_aptitude = self._get_value(data, "抑え適性", "closer_aptitude", 50)
        
        # Position変換
        position = None
        for p in Position:
            if p.value == position_value:
                position = p
                break
        if position is None:
            position = Position.OUTFIELDER_RIGHT if hasattr(Position, 'OUTFIELDER_RIGHT') else Position.OUTFIELD
        
        # PitchType変換
        pitch_type = None
        if pitch_type_value:
            for pt in PitchType:
                if pt.value == pitch_type_value:
                    pitch_type = pt
                    break
        
        # TeamLevel変換
        team_level = None
        if team_level_value:
            for tl in TeamLevel:
                if tl.value == team_level_value:
                    team_level = tl
                    break
        
        # PlayerStats復元（日本語キー対応）
        stats_data = self._get_value(data, "能力値", "stats", {})
        common_data = self._get_value(data, "共通能力", "common", {})
        
        def get_stat(jp_key: str, en_key: str, default):
            """statsからの値取得"""
            if jp_key in stats_data and stats_data[jp_key] is not None:
                return stats_data[jp_key]
            if en_key in stats_data and stats_data[en_key] is not None:
                return stats_data[en_key]
            return default
            
        def get_common(jp_key: str, en_key: str, default):
            """共通能力からの値取得"""
            # common_dataにあればそこから、なければstats_dataから（互換性）
            if jp_key in common_data: return common_data[jp_key]
            if en_key in common_data: return common_data[en_key]
            return get_stat(jp_key, en_key, default)
        
        # 旧形式のデータを読み込んで変数に格納
        run_val = get_stat("走力", "run", 50)
        arm_val = get_stat("肩力", "arm", 50)
        fielding_val = get_stat("守備", "fielding", 50)
        catching_val = get_stat("捕球", "catching", 50)
        breaking_val = get_stat("変化球", "breaking", 50)
        catcher_lead_val = get_stat("捕手リード", "catcher_lead", fielding_val)
        
        # 持ち球の処理（リストか辞書か判別）
        pitches_data = get_stat("持ち球", "breaking_balls", {})
        pitches_dict = {}
        if isinstance(pitches_data, list):
            for p_name in pitches_data:
                pitches_dict[p_name] = breaking_val
        elif isinstance(pitches_data, dict):
            pitches_dict = pitches_data

        # 守備適正(defense_ranges)の構築
        defense_ranges = get_stat("守備適正", "defense_ranges", {})
        
        if not defense_ranges:
            defense_ranges = {}
            # メインポジションを設定
            defense_ranges[position.value] = fielding_val
            
            # サブポジションを設定
            sub_positions_data = self._get_value(data, "サブポジション", "sub_positions", [])
            sub_position_ratings = self._get_value(data, "サブポジション評価", "sub_position_ratings", {})
            
            for sp_value in sub_positions_data:
                rating = sub_position_ratings.get(sp_value)
                if rating is None:
                    rating = int(fielding_val * 0.7)
                elif isinstance(rating, float) and rating <= 1.0:
                    rating = int(rating * 99)
                defense_ranges[sp_value] = max(1, int(rating))

        # PlayerStatsの生成
        stats = PlayerStats(
            # 打撃
            contact = get_stat("ミート", "contact", 50),
            gap = get_stat("ギャップ", "gap", 50),
            power = get_stat("パワー", "power", 50),
            eye = get_stat("選球眼", "eye", 50),
            avoid_k = get_stat("三振回避", "avoid_k", 50),
            trajectory = get_stat("弾道", "trajectory", 2),
            vs_left_batter = get_stat("対左投手", "vs_left_batter", 50),
            chance = get_stat("チャンス", "chance", 50),
            
            # 走塁
            speed = run_val,
            steal = get_stat("盗塁", "stealing", 50),
            baserunning = get_stat("走塁", "baserunning", 50),
            
            # バント
            bunt_sac = get_stat("バント", "bunt_sac", 50),
            bunt_hit = get_stat("セーフティ", "bunt_hit", 50),
            
            # 守備
            arm = arm_val,
            error = catching_val,
            defense_ranges = defense_ranges,
            catcher_lead = catcher_lead_val,
            turn_dp = fielding_val, 
            
            # 投手
            stuff = breaking_val,
            movement = get_stat("ムーブメント", "movement", 50),
            control = get_stat("コントロール", "control", 50),
            velocity = get_stat("球速", "speed", 145),
            stamina = get_stat("スタミナ", "stamina", 50),
            hold_runners = get_stat("クイック", "hold_runners", 50),
            gb_tendency = get_stat("ゴロ傾向", "gb_tendency", 50),
            vs_left_pitcher = get_stat("対左打者", "vs_left_pitcher", 50),
            vs_pinch = get_stat("対ピンチ", "vs_pinch", 50),
            stability = get_stat("安定感", "stability", 50),
            
            # 共通
            durability = get_common("ケガしにくさ", "durability", 50),
            recovery = get_common("回復", "recovery", 50),
            work_ethic = get_common("練習態度", "work_ethic", 50),
            intelligence = get_common("野球脳", "intelligence", 50),
            mental = get_common("メンタル", "mental", 50),
            
            pitches = pitches_dict
        )
        
        player = Player(
            name=name,
            position=position,
            pitch_type=pitch_type,
            stats=stats,
            age=age,
            status=PlayerStatus.FARM if is_developmental else PlayerStatus.ACTIVE,
            uniform_number=uniform_number,
            is_foreign=is_foreign,
            salary=salary,
            years_pro=years_pro,
            draft_round=draft_round,
            is_developmental=is_developmental,
            team_level=team_level,
            starter_aptitude=starter_aptitude,
            middle_aptitude=middle_aptitude,
            closer_aptitude=closer_aptitude
        )
        
        return player
    
    def team_to_dict(self, team: Team) -> Dict[str, Any]:
        """TeamオブジェクトをDict形式に変換（球団別ファイル用）"""
        return {
            "球団名": team.name,
            "リーグ": team.league.value,
            "予算": team.budget,
            "選手一覧": [self.player_to_dict(p) for p in team.players]
        }
    
    def dict_to_team(self, data: Dict[str, Any]) -> Team:
        """Dict形式からTeamオブジェクトを復元（日本語キー対応）"""
        name = data.get("球団名") or data.get("name", "チーム")
        league_value = data.get("リーグ") or data.get("league", "North League")
        budget = data.get("予算") or data.get("budget", 5000000000)
        players_data = data.get("選手一覧") or data.get("players", [])
        
        # League変換
        league = None
        for lg in League:
            if lg.value == league_value:
                league = lg
                break
        if league is None:
            league = League.NORTH
        
        team = Team(
            name=name,
            league=league,
            budget=budget
        )
        
        # 選手を復元
        for player_data in players_data:
            player = self.dict_to_player(player_data)
            team.players.append(player)
        
        return team
    
    def save_team(self, team: Team) -> bool:
        """球団データを個別ファイルに保存
        
        Args:
            team: 保存するチーム
        
        Returns:
            成功したかどうか
        """
        try:
            filepath = self._get_team_filepath(team.name)
            
            data = {
                "説明": "このファイルを編集して選手の能力値・名前・背番号などを変更できます",
                "能力値の範囲": "1～99（50が平均）", # メッセージ修正
                "バージョン": "2.2",
                **self.team_to_dict(team)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"球団データを保存しました: {filepath}")
            return True
        
        except Exception as e:
            print(f"球団データ保存エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_team(self, team_name: str) -> Optional[Team]:
        """球団データを個別ファイルから読み込み
        
        Args:
            team_name: チーム名
        
        Returns:
            チームオブジェクト（失敗時はNone）
        """
        try:
            filepath = self._get_team_filepath(team_name)
            
            if not os.path.exists(filepath):
                print(f"球団データファイルが見つかりません: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            team = self.dict_to_team(data)
            print(f"球団データを読み込みました: {filepath}")
            return team
        
        except Exception as e:
            print(f"球団データ読み込みエラー: {e}")
            return None
    
    def save_all_teams(self, teams: List[Team]) -> bool:
        """全チームの選手データを個別ファイルに保存
        
        Args:
            teams: 保存するチームリスト
        
        Returns:
            成功したかどうか
        """
        success = True
        for team in teams:
            if not self.save_team(team):
                success = False
        return success
    
    def load_all_teams(self, team_names: List[str]) -> Optional[List[Team]]:
        """全チームの選手データを個別ファイルから読み込み
        
        Args:
            team_names: 読み込むチーム名のリスト
        
        Returns:
            チームリスト（失敗時はNone）
        """
        teams = []
        for team_name in team_names:
            team = self.load_team(team_name)
            if team:
                teams.append(team)
        
        return teams if teams else None
    
    def has_team_data(self, team_name: str) -> bool:
        """球団の保存済みデータが存在するかチェック"""
        filepath = self._get_team_filepath(team_name)
        return os.path.exists(filepath)
    
    def has_all_team_data(self, team_names: List[str]) -> bool:
        """全球団の保存済みデータが存在するかチェック"""
        return all(self.has_team_data(name) for name in team_names)
    
    def get_all_team_files(self) -> List[str]:
        """データディレクトリにある全球団ファイルのリストを取得"""
        if not os.path.exists(self.DATA_DIR):
            return []
        
        files = []
        for filename in os.listdir(self.DATA_DIR):
            if filename.endswith('.json'):
                files.append(filename)
        return files


# グローバルインスタンス
player_data_manager = PlayerDataManager()