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
TEAM_CONFIGS = {
    # Northリーグ（セ・リーグ風）
    "Tokyo Bravers": {
        "abbr": "Tokyo",
        "color": "#FF6600",  # オレンジ
        "stadium": {
            "name": "首都ドーム",
            "capacity": 46000,
            # 東京ドーム 2024 PF: HR 1.155, Runs 1.026
            "pf_hr": 1.155, "pf_runs": 1.026, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 0.80, "pf_so": 1.02, "pf_bb": 1.00
        }
    },
    "Osaka Thunders": {
        "abbr": "Osaka",
        "color": "#BE0029",  # 赤紫
        "stadium": {
            "name": "関西ドーム",
            "capacity": 36146,
            # 京セラドーム 2024 PF: HR 0.941, Runs 0.966
            "pf_hr": 0.941, "pf_runs": 0.966, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 0.85, "pf_so": 1.05, "pf_bb": 0.98
        }
    },
    "Yokohama Mariners": {
        "abbr": "Yokohama",
        "color": "#0055A5",  # 青
        "stadium": {
            "name": "港スタジアム",
            "capacity": 34000,
            # 横浜スタジアム 2024 PF: HR 1.258, Runs 1.050
            "pf_hr": 1.258, "pf_runs": 1.050, "pf_1b": 1.02, "pf_2b": 1.05, "pf_3b": 0.85, "pf_so": 0.95, "pf_bb": 1.02
        }
    },
    "Nagoya Sparks": {
        "abbr": "Nagoya",
        "color": "#002569",  # 紺青
        "stadium": {
            "name": "中部ドーム",
            "capacity": 40500,
            # バンテリンドーム 2024 PF: HR 0.814, Runs 0.927
            "pf_hr": 0.814, "pf_runs": 0.927, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 0.90, "pf_so": 1.05, "pf_bb": 0.98
        }
    },
    "Hiroshima Phoenix": {
        "abbr": "Hiroshima",
        "color": "#E50012",  # 赤
        "stadium": {
            "name": "瀬戸内スタジアム",
            "capacity": 33000,
            # マツダスタジアム 2024 PF: HR 0.936, Runs 0.970
            "pf_hr": 0.936, "pf_runs": 0.970, "pf_1b": 1.00, "pf_2b": 1.05, "pf_3b": 1.10, "pf_so": 0.98, "pf_bb": 1.00
        }
    },
    "Shinjuku Spirits": {
        "abbr": "Shinjuku",
        "color": "#00479D",  # 青緑
        "stadium": {
            "name": "都心球場",
            "capacity": 31805,
            # 神宮球場 2024 PF: HR 1.506, Runs 1.049
            "pf_hr": 1.506, "pf_runs": 1.049, "pf_1b": 1.00, "pf_2b": 1.02, "pf_3b": 0.90, "pf_so": 0.95, "pf_bb": 1.02
        }
    },
    # Southリーグ（パ・リーグ風）
    "Sapporo Fighters": {
        "abbr": "Sapporo",
        "color": "#004B98",  # 青
        "stadium": {
            "name": "北海道フィールド",
            "capacity": 35000,
            # エスコンフィールド 2024 PF: HR 1.111, Runs 1.018
            "pf_hr": 1.211, "pf_runs": 1.018, "pf_1b": 1.00, "pf_2b": 1.03, "pf_3b": 1.00, "pf_so": 1.00, "pf_bb": 1.00
        }
    },
    "Saitama Bears": {
        "abbr": "Saitama",
        "color": "#1E3A5F",  # 紺
        "stadium": {
            "name": "武蔵野ドーム",
            "capacity": 33556,
            # ベルーナドーム 2024 PF: HR 0.900, Runs 0.963
            "pf_hr": 0.900, "pf_runs": 0.963, "pf_1b": 1.00, "pf_2b": 1.00, "pf_3b": 0.95, "pf_so": 1.02, "pf_bb": 1.00
        }
    },
    "Chiba Mariners": {
        "abbr": "Chiba",
        "color": "#000000",  # 黒
        "stadium": {
            "name": "湾岸マリンスタジアム",
            "capacity": 30118,
            # ZOZOマリン 2024 PF: HR 0.968, Runs 0.984
            "pf_hr": 0.968, "pf_runs": 0.984, "pf_1b": 0.98, "pf_2b": 0.95, "pf_3b": 1.15, "pf_so": 1.03, "pf_bb": 0.98
        }
    },
    "Fukuoka Phoenix": {
        "abbr": "Fukuoka",
        "color": "#FFE100",  # 黄
        "stadium": {
            "name": "九州ドーム",
            "capacity": 40178,
            # PayPayドーム 2024 PF: HR 0.999, Runs 0.995
            "pf_hr": 1.099, "pf_runs": 0.995, "pf_1b": 0.98, "pf_2b": 0.98, "pf_3b": 0.90, "pf_so": 1.02, "pf_bb": 1.00
        }
    },
    "Sendai Flames": {
        "abbr": "Sendai",
        "color": "#C41E3A",  # 臙脂
        "stadium": {
            "name": "杜の都パーク",
            "capacity": 30508,
            # 楽天モバイルパーク 2024 PF: HR 0.957, Runs 0.985
            "pf_hr": 0.957, "pf_runs": 0.985, "pf_1b": 1.00, "pf_2b": 1.02, "pf_3b": 1.05, "pf_so": 1.00, "pf_bb": 1.00
        }
    },
    "Kobe Buffaloes": {
        "abbr": "Kobe",
        "color": "#B5A642",  # ゴールド
        "stadium": {
            "name": "神戸フィールド",
            "capacity": 35000,
            # 甲子園 2024 PF: HR 0.701, Runs 0.931 (投手有利球場として設定)
            "pf_hr": 0.701, "pf_runs": 0.931, "pf_1b": 0.98, "pf_2b": 1.00, "pf_3b": 1.05, "pf_so": 1.03, "pf_bb": 0.98
        }
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
        }
    }


class TeamDataManager:
    """チームデータの保存・読み込み管理クラス"""
    
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(_SCRIPT_DIR, "team_data")
    
    def __init__(self):
        """初期化"""
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """データディレクトリを作成"""
        if not os.path.exists(self.DATA_DIR):
            os.makedirs(self.DATA_DIR)
            print(f"チームデータディレクトリを作成しました: {self.DATA_DIR}")
    
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
        
        # 成績は含まない（ゲームセーブで管理）
        return data
    
    def dict_to_team(self, data: Dict[str, Any]) -> Team:
        """Dict形式からTeamオブジェクトを復元（球団情報のみ）"""
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


# グローバルインスタンス
team_data_manager = TeamDataManager()
