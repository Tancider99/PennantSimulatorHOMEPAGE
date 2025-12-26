# -*- coding: utf-8 -*-
"""
チームデータ管理モジュール
球団情報（球団名、本拠地、パークファクターなど）をJSONファイルに保存・読み込み
ゲーム開始時のみファイルから読み込み、ゲーム中の変更はメモリに保持
"""
import json
import os
from typing import Dict, List, Any, Optional
from models import Team, League, Stadium


# NPB風チームデータ定義（球場・PF・色・略称）- 2024年PFデータ使用
# 現実のNPBファン数データを基にした初期ファン設定
# 参考: 阪神477万, 巨人354万, 日ハム249万, ソフトバンク201万, 広島196万, 総数2218万
# ライト層: 観客・視聴者層（増減大）、ミドル層: 熱心なファン、コア層: 会員・グッズ購入者
TEAM_CONFIGS = {
    # Northリーグ（セ・リーグ風）
    "Tokyo Bravers": {
        "abbr": "Tokyo",
        "color": "#FF6600",  # オレンジ
        "stadium": {
            "name": "首都ドーム",
            "capacity": 43500,
            "is_dome": True,
            "pf_hr": 1.155, "pf_runs": 1.026, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 0.80, "pf_so": 1.02, "pf_bb": 1.00
        },
        "fans": {"light": 2500000, "middle": 750000, "core": 290000}  # 巨人級：354万人
    },
    "Kobe Thunders": {
        "abbr": "Kobe",
        "color": "#B5A642",  # ゴールド
        "stadium": {
            "name": "甲陽スタジアム",
            "capacity": 47508,
            "is_dome": False,
            "pf_hr": 0.701, "pf_runs": 0.931, "pf_1b": 0.98, "pf_2b": 1.00, "pf_3b": 1.05, "pf_so": 1.03, "pf_bb": 0.98
        },
        "fans": {"light": 3400000, "middle": 1000000, "core": 370000}  # 阪神級：477万人（人気No.1）
    },
    "Yokohama Mariners": {
        "abbr": "Yokohama",
        "color": "#0055A5",  # 青
        "stadium": {
            "name": "港南スタジアム",
            "capacity": 33912,
            "is_dome": False,
            "pf_hr": 1.258, "pf_runs": 1.050, "pf_1b": 1.02, "pf_2b": 1.05, "pf_3b": 0.85, "pf_so": 0.95, "pf_bb": 1.02
        },
        "fans": {"light": 1200000, "middle": 360000, "core": 140000}  # DeNA級：170万人
    },
    "Nagoya Sparks": {
        "abbr": "Nagoya",
        "color": "#002569",  # 紺青
        "stadium": {
            "name": "中部ドーム",
            "capacity": 36627,
            "is_dome": True,
            "pf_hr": 0.814, "pf_runs": 0.927, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 0.90, "pf_so": 1.05, "pf_bb": 0.98
        },
        "fans": {"light": 1300000, "middle": 400000, "core": 150000}  # 中日級：185万人
    },
    "Hiroshima Phoenix": {
        "abbr": "Hiroshima",
        "color": "#E50012",  # 赤
        "stadium": {
            "name": "瀬戸内パーク",
            "capacity": 33000,
            "is_dome": False,
            "pf_hr": 0.936, "pf_runs": 0.970, "pf_1b": 1.00, "pf_2b": 1.05, "pf_3b": 1.10, "pf_so": 0.98, "pf_bb": 1.00
        },
        "fans": {"light": 1400000, "middle": 400000, "core": 160000}  # 広島級：196万人
    },
    "Shinjuku Spirits": {
        "abbr": "Shinjuku",
        "color": "#00479D",  # 青緑
        "stadium": {
            "name": "中央球場",
            "capacity": 30969,
            "is_dome": False,
            "pf_hr": 1.506, "pf_runs": 1.049, "pf_1b": 1.00, "pf_2b": 1.02, "pf_3b": 0.90, "pf_so": 0.95, "pf_bb": 1.02
        },
        "fans": {"light": 1000000, "middle": 300000, "core": 120000}  # ヤクルト級：142万人
    },
    # Southリーグ（パ・リーグ風）
    "Sapporo Fighters": {
        "abbr": "Sapporo",
        "color": "#004B98",  # 青
        "stadium": {
            "name": "北海道フィールド",
            "capacity": 35000,
            "is_dome": True,
            "pf_hr": 1.211, "pf_runs": 1.018, "pf_1b": 1.00, "pf_2b": 1.03, "pf_3b": 1.00, "pf_so": 1.00, "pf_bb": 1.00
        },
        "fans": {"light": 1750000, "middle": 530000, "core": 210000}  # 日ハム級：249万人
    },
    "Saitama Bears": {
        "abbr": "Saitama",
        "color": "#1E3A5F",  # 紺
        "stadium": {
            "name": "武蔵野ドーム",
            "capacity": 31552,
            "is_dome": True,
            "pf_hr": 0.900, "pf_runs": 0.963, "pf_1b": 1.00, "pf_2b": 1.00, "pf_3b": 0.95, "pf_so": 1.02, "pf_bb": 1.00
        },
        "fans": {"light": 1100000, "middle": 330000, "core": 130000}  # 西武級：156万人
    },
    "Chiba Mariners": {
        "abbr": "Chiba",
        "color": "#000000",  # 黒
        "stadium": {
            "name": "湾岸マリンパーク",
            "capacity": 33000,
            "is_dome": False,
            "pf_hr": 0.968, "pf_runs": 0.984, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 1.15, "pf_so": 1.03, "pf_bb": 0.98
        },
        "fans": {"light": 980000, "middle": 290000, "core": 110000}  # ロッテ級：138万人
    },
    "Fukuoka Phoenix": {
        "abbr": "Fukuoka",
        "color": "#FFE100",  # 黄
        "stadium": {
            "name": "九州ドーム",
            "capacity": 40178,
            "is_dome": True,
            "pf_hr": 1.099, "pf_runs": 0.995, "pf_1b": 0.98, "pf_2b": 0.98, "pf_3b": 0.90, "pf_so": 1.02, "pf_bb": 1.00
        },
        "fans": {"light": 1420000, "middle": 420000, "core": 170000}  # ソフトバンク級：201万人
    },
    "Sendai Flames": {
        "abbr": "Sendai",
        "color": "#C41E3A",  # 臙脂
        "stadium": {
            "name": "杜の都パーク",
            "capacity": 31272,
            "is_dome": False,
            "pf_hr": 0.957, "pf_runs": 0.985, "pf_1b": 1.00, "pf_2b": 1.02, "pf_3b": 1.05, "pf_so": 1.00, "pf_bb": 1.00
        },
        "fans": {"light": 1120000, "middle": 340000, "core": 130000}  # 楽天級：159万人
    },
    "Osaka Buffaloes": {
        "abbr": "Osaka",
        "color": "#BE0029",  # 赤紫
        "stadium": {
            "name": "関西ドーム",
            "capacity": 36154,
            "is_dome": True,
            "pf_hr": 0.941, "pf_runs": 0.966, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 0.85, "pf_so": 1.05, "pf_bb": 0.98
        },
        "fans": {"light": 1050000, "middle": 320000, "core": 125000}  # オリックス級：150万人
    }
}



def get_team_config(team_name: str) -> Dict[str, Any]:
    """チーム名からNPB風設定を取得（なければデフォルト生成）"""
    if team_name in TEAM_CONFIGS:
        return TEAM_CONFIGS[team_name]
    
    # デフォルト生成：地名部分を略称に
    parts = team_name.split(" ")
    abbr = parts[0] if parts else team_name[:4]
    
    return {
        "abbr": abbr,
        "color": "#333333",
        "stadium": {
            "name": f"{abbr}スタジアム",
            "capacity": 35000,
            "pf_hr": 1.0, "pf_runs": 1.0, "pf_1b": 1.0, "pf_2b": 1.0, "pf_3b": 1.0, "pf_so": 1.0, "pf_bb": 1.0
        },
        "fans": {"light": 400000, "middle": 200000, "core": 70000}  # デフォルト：中規模チーム
    }



class TeamDataManager:
    """チームデータの保存・読み込み管理クラス"""
    
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(_SCRIPT_DIR, "team_data")
    DEFAULT_DATA_DIR = os.path.join(_SCRIPT_DIR, "team_data_default")
    
    def __init__(self):
        """初期化"""
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """データディレクトリを作成"""
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)
            print(f"チームデータディレクトリを作成しました: {self.DATA_DIR}")
        if not os.path.exists(self.DEFAULT_DATA_DIR):
            os.makedirs(self.DEFAULT_DATA_DIR)
    
    def save_default_data(self):
        """現在のデータをデフォルトとして保存"""
        import shutil
        if os.path.exists(self.DATA_DIR):
            # Clear and copy current data to default
            if os.path.exists(self.DEFAULT_DATA_DIR):
                shutil.rmtree(self.DEFAULT_DATA_DIR)
            shutil.copytree(self.DATA_DIR, self.DEFAULT_DATA_DIR)
            print(f"デフォルトチームデータを保存しました: {self.DEFAULT_DATA_DIR}")
            return True
        return False
    
    def reset_to_default(self):
        """デフォルトデータに戻す"""
        import shutil
        if os.path.exists(self.DEFAULT_DATA_DIR) and os.listdir(self.DEFAULT_DATA_DIR):
            # Clear current and copy from default
            if os.path.exists(self.DATA_DIR):
                shutil.rmtree(self.DATA_DIR)
            shutil.copytree(self.DEFAULT_DATA_DIR, self.DATA_DIR)
            print(f"チームデータをデフォルトに戻しました")
            return True
        print(f"デフォルトデータがありません")
        return False
    
    def has_default_data(self):
        """デフォルトデータが存在するか確認"""
        return os.path.exists(self.DEFAULT_DATA_DIR) and len(os.listdir(self.DEFAULT_DATA_DIR)) > 0
    
    def _get_team_filepath(self, team_name: str) -> str:
        """チームデータのファイルパスを取得"""
        safe_name = team_name.replace(" ", "_").replace("/", "_")
        return os.path.join(self.DATA_DIR, f"{safe_name}_team.json")
    
    def team_to_dict(self, team: Team) -> Dict[str, Any]:
        """TeamオブジェクトをDict形式に変換（球団情報のみ、成績は含まない）"""
        data = {
            "球団名": team.name,
            "リーグ": team.league.value if team.league else "North League",
            "予算": team.budget,
            "色": getattr(team, 'color', None),
            "略称": getattr(team, 'abbr', None),
        }
        
        # 球場情報
        if team.stadium:
            data["球場"] = {
                "名前": team.stadium.name,
                "収容人数": team.stadium.capacity,
                "ドーム": getattr(team.stadium, 'is_dome', False),
                "パークファクター": {
                    "得点": getattr(team.stadium, 'pf_runs', 1.0),
                    "HR": getattr(team.stadium, 'pf_hr', 1.0),
                    "単打": getattr(team.stadium, 'pf_1b', 1.0),
                    "二塁打": getattr(team.stadium, 'pf_2b', 1.0),
                    "三塁打": getattr(team.stadium, 'pf_3b', 1.0),
                    "三振": getattr(team.stadium, 'pf_so', 1.0),
                    "四球": getattr(team.stadium, 'pf_bb', 1.0)
                }
            }
        else:
            data["球場"] = None
        
        # ファン層データを保存
        if hasattr(team, 'finance') and team.finance and team.finance.fan_base:
            fb = team.finance.fan_base
            data["ファン"] = {
                "ライト層": fb.light_fans,
                "ミドル層": fb.middle_fans,
                "コア層": fb.core_fans
            }
        
        # 成績は含まない（ゲームセーブで管理）
        return data

    
    def dict_to_team(self, data: Dict[str, Any]) -> Team:
        """Dict形式からTeamオブジェクトを復元（球団情報のみ）"""
        from models import FanBase, TeamFinance
        
        name = data.get("球団名") or data.get("name", "チーム")
        league_value = data.get("リーグ") or data.get("league", "North League")
        budget = data.get("予算") or data.get("budget", 5000000000)
        color = data.get("色") or data.get("color")
        abbr = data.get("略称") or data.get("abbr")
        
        # League変換
        league = None
        for lg in League:
            if lg.value == league_value:
                league = lg
                break
        if league is None:
            league = League.NORTH
        
        # 球場情報
        stadium = None
        stadium_data = data.get("球場")
        if stadium_data:
            pf_data = stadium_data.get("パークファクター", {})
            
            stadium = Stadium(
                name=stadium_data.get("名前", "本拠地球場"),
                capacity=stadium_data.get("収容人数", 40000),
                field_size=stadium_data.get("フィールド広さ", 3),
                is_dome=stadium_data.get("ドーム", False),
                pf_runs=pf_data.get("得点", 1.0),
                pf_hr=pf_data.get("HR", 1.0),
                pf_1b=pf_data.get("単打", 1.0),
                pf_2b=pf_data.get("二塁打", 1.0),
                pf_3b=pf_data.get("三塁打", 1.0),
                pf_so=pf_data.get("三振", 1.0),
                pf_bb=pf_data.get("四球", 1.0)
            )
        
        team = Team(
            name=name,
            league=league,
            budget=budget,
            stadium=stadium,
            color=color,
            abbr=abbr
        )
        
        # ファン層データを読み込み
        fan_data = data.get("ファン")
        if fan_data:
            fan_base = FanBase(
                light_fans=fan_data.get("ライト層", 300000),
                middle_fans=fan_data.get("ミドル層", 150000),
                core_fans=fan_data.get("コア層", 50000)
            )
            team.finance = TeamFinance(fan_base=fan_base)
        
        # 成績は0から開始（ゲームセーブから復元される）
        team.wins = 0
        team.losses = 0
        team.draws = 0
        
        return team
    
    def save_team(self, team: Team) -> bool:
        """チームデータをファイルに保存（初回生成時のみ使用）"""
        try:
            filepath = self._get_team_filepath(team.name)
            
            data = {
                "説明": "球団情報ファイル（球場・パークファクター・予算など）- ゲーム中は変更されません",
                "バージョン": "1.1",
                **self.team_to_dict(team)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"チームデータを保存しました: {filepath}")
            return True
        
        except Exception as e:
            print(f"チームデータ保存エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_team(self, team_name: str) -> Optional[Team]:
        """チームデータをファイルから読み込み"""
        try:
            filepath = self._get_team_filepath(team_name)
            
            if not os.path.exists(filepath):
                print(f"チームデータファイルが見つかりません: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            team = self.dict_to_team(data)
            print(f"チームデータを読み込みました: {filepath}")
            return team
        
        except Exception as e:
            print(f"チームデータ読み込みエラー: {e}")
            return None
    
    def save_all_teams(self, teams: List[Team]) -> bool:
        """全チームのデータを保存"""
        success = True
        for team in teams:
            if not self.save_team(team):
                success = False
        return success
    
    def load_all_teams(self, team_names: List[str]) -> Optional[List[Team]]:
        """全チームのデータを読み込み"""
        teams = []
        for team_name in team_names:
            team = self.load_team(team_name)
            if team:
                teams.append(team)
        return teams if teams else None
    
    def has_team_data(self, team_name: str) -> bool:
        """チームデータが存在するか確認"""
        filepath = self._get_team_filepath(team_name)
        return os.path.exists(filepath)
    
    def has_all_team_data(self, team_names: List[str]) -> bool:
        """全チームのデータが存在するか確認"""
        return all(self.has_team_data(name) for name in team_names)
    
    def get_all_teams_from_files(self) -> dict:
        """
        team_dataディレクトリ内のすべてのチームファイルからデータを読み込む
        Returns: {"north": [(name, data), ...], "south": [(name, data), ...], "all_data": {name: data}}
        """
        import json
        
        north_teams = []
        south_teams = []
        all_data = {}
        
        # デフォルトのSouthリーグチーム（ファイルにリーグがない場合のフォールバック）
        default_south = {"Fukuoka Phoenix", "Saitama Bears", "Sendai Flames", 
                        "Chiba Mariners", "Sapporo Fighters", "Osaka Buffaloes"}
        
        if os.path.exists(self.DATA_DIR):
            for filename in os.listdir(self.DATA_DIR):
                if filename.endswith("_team.json"):
                    filepath = os.path.join(self.DATA_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        team_name = data.get("球団名", filename.replace("_team.json", "").replace("_", " "))
                        
                        # リーグ判定
                        league = data.get("リーグ")
                        if not league:
                            file_base = filename.replace("_team.json", "").replace("_", " ")
                            league = "South League" if file_base in default_south else "North League"
                        
                        all_data[team_name] = data
                        if "South" in league:
                            south_teams.append((team_name, data))
                        else:
                            north_teams.append((team_name, data))
                    except Exception as e:
                        print(f"チームデータ読み込みエラー: {filename} - {e}")
        
        return {"north": north_teams, "south": south_teams, "all_data": all_data}


# グローバルインスタンス
team_data_manager = TeamDataManager()
