# -*- coding: utf-8 -*-
"""
セーブデータ管理モジュール
ゲームの状態を保存・読み込み
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import asdict
import pickle


class SaveManager:
    """セーブデータの管理クラス"""
    
    SAVE_DIR = "saves"
    SAVE_EXTENSION = ".sav"
    MAX_SAVE_SLOTS = 10
    
    def __init__(self):
        """初期化"""
        self._ensure_save_directory()
    
    def _ensure_save_directory(self):
        """セーブディレクトリを作成"""
        if not os.path.exists(self.SAVE_DIR):
            os.makedirs(self.SAVE_DIR)
    
    def get_save_slots(self) -> List[Dict[str, Any]]:
        """利用可能なセーブスロットを取得
        
        Returns:
            セーブスロット情報のリスト
        """
        slots = []
        for i in range(1, self.MAX_SAVE_SLOTS + 1):
            slot_info = self._get_slot_info(i)
            slots.append(slot_info)
        return slots
    
    def _get_slot_info(self, slot_num: int) -> Dict[str, Any]:
        """スロット情報を取得"""
        filepath = self._get_save_path(slot_num)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
                
                return {
                    "slot": slot_num,
                    "exists": True,
                    "team_name": data.get("team_name", "不明"),
                    "year": data.get("year", 2025),
                    "month": data.get("month", 1),
                    "day": data.get("day", 1),
                    "wins": data.get("wins", 0),
                    "losses": data.get("losses", 0),
                    "save_date": data.get("save_date", "不明"),
                    "game_mode": data.get("game_mode", "pennant")
                }
            except Exception as e:
                print(f"セーブデータ読み込みエラー (スロット{slot_num}): {e}")
                return {"slot": slot_num, "exists": False, "error": str(e)}
        
        return {"slot": slot_num, "exists": False}
    
    def _get_save_path(self, slot_num: int) -> str:
        """セーブファイルのパスを取得"""
        return os.path.join(self.SAVE_DIR, f"save_{slot_num}{self.SAVE_EXTENSION}")
    
    def save_game(self, slot_num: int, game_data: Dict[str, Any]) -> bool:
        """ゲームを保存
        
        Args:
            slot_num: スロット番号 (1-10)
            game_data: 保存するゲームデータ
        
        Returns:
            成功したかどうか
        """
        if not 1 <= slot_num <= self.MAX_SAVE_SLOTS:
            print(f"無効なスロット番号: {slot_num}")
            return False
        
        try:
            # セーブ日時を追加
            game_data["save_date"] = datetime.now().strftime("%Y/%m/%d %H:%M")
            
            filepath = self._get_save_path(slot_num)
            with open(filepath, 'wb') as f:
                pickle.dump(game_data, f)
            
            print(f"セーブ完了: スロット{slot_num}")
            return True
        
        except Exception as e:
            print(f"セーブエラー: {e}")
            return False
    
    def load_game(self, slot_num: int) -> Optional[Dict[str, Any]]:
        """ゲームを読み込み
        
        Args:
            slot_num: スロット番号 (1-10)
        
        Returns:
            ゲームデータ または None
        """
        if not 1 <= slot_num <= self.MAX_SAVE_SLOTS:
            print(f"無効なスロット番号: {slot_num}")
            return None
        
        filepath = self._get_save_path(slot_num)
        
        if not os.path.exists(filepath):
            print(f"セーブデータが見つかりません: スロット{slot_num}")
            return None
        
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)

            # マイグレーション: 古いセーブ（能力値が1-20スケールのもの）を検出して1-99スケールへ変換
            try:
                self._migrate_stat_scales(data)
            except Exception as me:
                print(f"セーブマイグレーションでエラー: {me}")

            print(f"ロード完了: スロット{slot_num}")
            return data
        
        except Exception as e:
            print(f"ロードエラー: {e}")
            return None
    
    def delete_save(self, slot_num: int) -> bool:
        """セーブデータを削除
        
        Args:
            slot_num: スロット番号 (1-10)
        
        Returns:
            成功したかどうか
        """
        if not 1 <= slot_num <= self.MAX_SAVE_SLOTS:
            return False
        
        filepath = self._get_save_path(slot_num)
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"削除完了: スロット{slot_num}")
                return True
            except Exception as e:
                print(f"削除エラー: {e}")
                return False
        
        return False

    def _migrate_stat_scales(self, data: Any):
        """Loaded pickle data may contain Player / PlayerStats objects saved with
        older 1-20 scales. Detect PlayerStats objects and rescale integer stat
        attributes from 1-20 -> 1-99 if necessary.
        """
        try:
            from models import Player, PlayerStats
        except Exception:
            return

        STAT_KEYS = [
            'contact', 'power', 'run', 'arm', 'fielding', 'catching',
            'speed', 'control', 'stamina', 'breaking', 'mental', 'clutch',
            'consistency', 'vs_left', 'pinch_hit', 'stealing', 'baserunning'
        ]

        def scale_value(v: int) -> int:
            if not isinstance(v, int):
                return v
            if v <= 0:
                return v
            # treat values <= 20 as old-scale and rescale to 1-99
            if v <= 20:
                return max(1, min(99, int(round(v * 99.0 / 20.0))))
            return v

        def visit(obj):
            # If it's a PlayerStats instance, scale its stat attributes
            if isinstance(obj, PlayerStats):
                for k in STAT_KEYS:
                    if hasattr(obj, k):
                        try:
                            cur = getattr(obj, k)
                            newv = scale_value(cur)
                            if newv != cur:
                                setattr(obj, k, newv)
                        except Exception:
                            continue

            # If it's a Player, visit its stats attribute
            if isinstance(obj, Player):
                if hasattr(obj, 'stats') and isinstance(obj.stats, PlayerStats):
                    visit(obj.stats)

            # If it's a dict or list, recurse
            if isinstance(obj, dict):
                # If dict looks like a serialized stats block, scale numeric stat entries
                for key in list(obj.keys()):
                    try:
                        if key in STAT_KEYS and isinstance(obj[key], int):
                            obj[key] = scale_value(obj[key])
                        else:
                            visit(obj[key])
                    except Exception:
                        # ignore errors and continue recursion
                        continue
            elif isinstance(obj, (list, tuple, set)):
                for v in obj:
                    visit(v)

        visit(data)
    
    def export_to_json(self, slot_num: int, export_path: str) -> bool:
        """セーブデータをJSONとしてエクスポート（デバッグ用）"""
        data = self.load_game(slot_num)
        if not data:
            return False
        
        try:
            # pickleデータをJSON互換形式に変換
            json_data = self._convert_to_json_compatible(data)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
            return True
        except Exception as e:
            print(f"エクスポートエラー: {e}")
            return False
    
    def _convert_to_json_compatible(self, data: Any) -> Any:
        """データをJSON互換形式に変換"""
        if isinstance(data, dict):
            return {k: self._convert_to_json_compatible(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_to_json_compatible(item) for item in data]
        elif hasattr(data, '__dict__'):
            return self._convert_to_json_compatible(data.__dict__)
        else:
            return data


def create_save_data(game) -> Dict[str, Any]:
    """Gameインスタンスからセーブデータを作成

    Args:
        game: Gameインスタンス

    Returns:
        セーブデータの辞書
    """
    from models import Team, Player
    
    save_data = {
        # 基本情報
        "game_mode": game.state_manager.current_state.name if hasattr(game, 'state_manager') else "MAIN_MENU",
        "year": getattr(game, 'current_year', 2025),
        "month": getattr(game, 'current_month', 1),
        "day": getattr(game, 'current_day', 1),
        
        # チーム情報
        "teams": [],
        "player_team_name": None,
    }
    
    # プレイヤーチーム
    if hasattr(game, 'state_manager') and game.state_manager.player_team:
        player_team = game.state_manager.player_team
        save_data["player_team_name"] = player_team.name
        save_data["team_name"] = player_team.name
        save_data["wins"] = player_team.wins
        save_data["losses"] = player_team.losses
    
    # 全チームデータ
    if hasattr(game, 'state_manager') and hasattr(game.state_manager, 'all_teams') and game.state_manager.all_teams:
        for team in game.state_manager.all_teams:
            team_data = _serialize_team(team)
            save_data["teams"].append(team_data)
    
    # ペナントモード固有のデータ
    if hasattr(game, 'pennant_manager') and game.pennant_manager:
        pm = game.pennant_manager
        save_data["pennant"] = {
            "current_year": getattr(pm, 'current_year', 2025),
            "current_month": getattr(pm, 'current_month', 1),
            "current_day": getattr(pm, 'current_day', 1),
            "phase": getattr(pm, 'current_phase', 'regular_season'),
            "schedule_index": getattr(pm, 'current_schedule_index', 0),
            "team_finances": getattr(pm, 'team_finances', {}),
        }
    
    # スケジュールマネージャー
    if hasattr(game, 'schedule_manager') and game.schedule_manager:
        sm = game.schedule_manager
        save_data["schedule"] = {
            "current_year": getattr(sm, 'current_year', 2025),
            "schedule": getattr(sm, 'schedule', []),
            "completed_games": getattr(sm, 'completed_games', []),
        }
    
    return save_data


def _serialize_team(team) -> Dict[str, Any]:
    """チームをシリアライズ"""
    return {
        "name": team.name,
        "league": team.league,
        "wins": team.wins,
        "losses": team.losses,
        "draws": team.draws,
        "budget": team.budget,
        "players": [_serialize_player(p) for p in team.players],
        "current_lineup": team.current_lineup,
        "starting_pitcher_idx": team.starting_pitcher_idx,
        "position_assignments": dict(team.position_assignments) if team.position_assignments else {},
        # 投手陣設定
        "rotation": getattr(team, 'rotation', []),
        "rotation_index": getattr(team, 'rotation_index', 0),
        "setup_pitchers": getattr(team, 'setup_pitchers', []),
        "closer_idx": getattr(team, 'closer_idx', -1),
        # ベンチ設定
        "bench_batters": getattr(team, 'bench_batters', []),
        "bench_pitchers": getattr(team, 'bench_pitchers', []),
        "active_roster": getattr(team, 'active_roster', []),
    }


def _serialize_player(player) -> Dict[str, Any]:
    """選手をシリアライズ"""
    data = {
        "name": player.name,
        "uniform_number": player.uniform_number,
        "position": player.position.value,
        "pitch_type": player.pitch_type.value if player.pitch_type else None,
        "age": player.age,
        "years_pro": player.years_pro,
        "salary": player.salary,
        "is_developmental": player.is_developmental,
        "team_level": getattr(player, 'team_level', None).value if getattr(player, 'team_level', None) else None,
        "stats": _serialize_stats(player.stats),
        "record": _serialize_record(player.record),
    }
    
    # 成長データ
    if hasattr(player, 'growth') and player.growth:
        data["growth"] = {
            "potential": player.growth.potential,
            "peak_age": getattr(player.growth, 'peak_age', 28),
            "growth_rate": getattr(player.growth, 'growth_rate', 1.0),
            "decline_rate": getattr(player.growth, 'decline_rate', 1.0),
        }
    
    # 特殊能力（PlayerAbilitiesオブジェクトまたはリスト/セット）
    if hasattr(player, 'special_abilities') and player.special_abilities:
        abilities = player.special_abilities
        if hasattr(abilities, '__iter__') and not hasattr(abilities, 'keys'):
            # リストやセットの場合
            data["special_abilities"] = list(abilities)
        elif hasattr(abilities, '__dict__'):
            # PlayerAbilitiesオブジェクトの場合は属性を辞書として保存
            data["special_abilities"] = {k: v for k, v in abilities.__dict__.items() if not k.startswith('_')}
        else:
            data["special_abilities"] = []
    
    return data


def _serialize_stats(stats) -> Dict[str, Any]:
    """能力値をシリアライズ"""
    return {
        "contact": getattr(stats, 'contact', 50),
        "power": getattr(stats, 'power', 50),
        "speed": getattr(stats, 'speed', 50),
        "fielding": getattr(stats, 'fielding', 50),
        "arm": getattr(stats, 'arm', 50),
        "eye": getattr(stats, 'eye', 50),
        "run": getattr(stats, 'run', 50),
        "stamina": getattr(stats, 'stamina', 50),
        "control": getattr(stats, 'control', 50),
        "breaking": getattr(stats, 'breaking', 50),
    }


def _serialize_record(record) -> Dict[str, Any]:
    """成績をシリアライズ"""
    return {
        "at_bats": getattr(record, 'at_bats', 0),
        "hits": getattr(record, 'hits', 0),
        "home_runs": getattr(record, 'home_runs', 0),
        "rbis": getattr(record, 'rbis', 0),
        "runs": getattr(record, 'runs', 0),
        "walks": getattr(record, 'walks', 0),
        "strikeouts": getattr(record, 'strikeouts', 0),
        "doubles": getattr(record, 'doubles', 0),
        "triples": getattr(record, 'triples', 0),
        "stolen_bases": getattr(record, 'stolen_bases', 0),
        "innings_pitched": getattr(record, 'innings_pitched', 0),
        "earned_runs": getattr(record, 'earned_runs', 0),
        "wins": getattr(record, 'wins', 0),
        "losses": getattr(record, 'losses', 0),
        "saves": getattr(record, 'saves', 0),
        "holds": getattr(record, 'holds', 0),
        "strikeouts_pitched": getattr(record, 'strikeouts_pitched', 0),
        "walks_allowed": getattr(record, 'walks_allowed', 0),
        "hits_allowed": getattr(record, 'hits_allowed', 0),
        "games_pitched": getattr(record, 'games_pitched', 0),
    }


def load_save_data(game, save_data: Dict[str, Any]) -> bool:
    """セーブデータからゲーム状態を復元

    Args:
        game: Gameインスタンス
        save_data: セーブデータ

    Returns:
        成功したかどうか
    """
    from models import Team, Player, Position, PitchType, PlayerStats, PlayerRecord
    from player_development import PlayerGrowth
    
    try:
        # チームを復元
        teams = []
        for team_data in save_data.get("teams", []):
            team = _deserialize_team(team_data)
            teams.append(team)
        
        if teams:
            game.state_manager.all_teams = teams
            # リーグ別にも分類
            game.state_manager.north_teams = [t for t in teams if hasattr(t, 'league') and t.league.value == "North League"]
            game.state_manager.south_teams = [t for t in teams if hasattr(t, 'league') and t.league.value == "South League"]
        
        # プレイヤーチームを設定
        player_team_name = save_data.get("player_team_name")
        if player_team_name and teams:
            for team in teams:
                if team.name == player_team_name:
                    game.state_manager.player_team = team
                    break
        
        # ペナントマネージャーを復元
        pennant_data = save_data.get("pennant", {})
        if pennant_data and hasattr(game, 'pennant_manager') and game.pennant_manager:
            pm = game.pennant_manager
            pm.current_year = pennant_data.get("current_year", 2025)
            pm.current_month = pennant_data.get("current_month", 1)
            pm.current_day = pennant_data.get("current_day", 1)
            pm.current_phase = pennant_data.get("phase", "regular_season")
            pm.current_schedule_index = pennant_data.get("schedule_index", 0)
            if "team_finances" in pennant_data:
                pm.team_finances = pennant_data["team_finances"]
        
        # スケジュールマネージャーを復元
        schedule_data = save_data.get("schedule", {})
        if schedule_data and hasattr(game, 'schedule_manager') and game.schedule_manager:
            sm = game.schedule_manager
            sm.current_year = schedule_data.get("current_year", 2025)
            if "schedule" in schedule_data:
                sm.schedule = schedule_data["schedule"]
            if "completed_games" in schedule_data:
                sm.completed_games = schedule_data["completed_games"]
        
        # 年月日
        game.current_year = save_data.get("year", 2025)
        game.current_month = save_data.get("month", 1)
        game.current_day = save_data.get("day", 1)
        
        return True
    
    except Exception as e:
        print(f"データ復元エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def _deserialize_team(data: Dict[str, Any]):
    """チームをデシリアライズ"""
    from models import Team
    
    team = Team(
        name=data["name"],
        league=data.get("league", "North League")
    )
    team.wins = data.get("wins", 0)
    team.losses = data.get("losses", 0)
    team.draws = data.get("draws", 0)
    team.budget = data.get("budget", 50)
    team.current_lineup = data.get("current_lineup", [])
    team.starting_pitcher_idx = data.get("starting_pitcher_idx", -1)
    team.position_assignments = data.get("position_assignments", {})
    
    # 投手陣設定を復元
    team.rotation = data.get("rotation", [])
    team.rotation_index = data.get("rotation_index", 0)
    team.setup_pitchers = data.get("setup_pitchers", [])
    team.closer_idx = data.get("closer_idx", -1)
    
    # ベンチ設定を復元
    team.bench_batters = data.get("bench_batters", [])
    team.bench_pitchers = data.get("bench_pitchers", [])
    team.active_roster = data.get("active_roster", [])
    
    # 選手を復元
    team.players = []
    for player_data in data.get("players", []):
        player = _deserialize_player(player_data)
        team.players.append(player)
    
    return team


def _deserialize_player(data: Dict[str, Any]):
    """選手をデシリアライズ"""
    from models import Player, Position, PitchType, PlayerStats, PlayerRecord
    from player_development import PlayerGrowth
    
    # ポジション
    position = Position(data.get("position", "野手"))
    
    # 投手タイプ
    pitch_type = None
    if data.get("pitch_type"):
        try:
            pitch_type = PitchType(data["pitch_type"])
        except:
            pass
    
    # 能力値
    stats_data = data.get("stats", {})
    stats = PlayerStats(
        contact=stats_data.get("contact", 50),
        power=stats_data.get("power", 50),
        speed=stats_data.get("speed", 50),
        fielding=stats_data.get("fielding", 50),
        arm=stats_data.get("arm", 50),
        eye=stats_data.get("eye", 50),
        run=stats_data.get("run", 50),
        stamina=stats_data.get("stamina", 50),
        control=stats_data.get("control", 50),
        breaking=stats_data.get("breaking", 50),
    )
    
    # 成績
    record_data = data.get("record", {})
    record = PlayerRecord(
        at_bats=record_data.get("at_bats", 0),
        hits=record_data.get("hits", 0),
        home_runs=record_data.get("home_runs", 0),
        rbis=record_data.get("rbis", 0),
        runs=record_data.get("runs", 0),
        walks=record_data.get("walks", 0),
        strikeouts=record_data.get("strikeouts", 0),
        doubles=record_data.get("doubles", 0),
        triples=record_data.get("triples", 0),
        stolen_bases=record_data.get("stolen_bases", 0),
        innings_pitched=record_data.get("innings_pitched", 0),
        earned_runs=record_data.get("earned_runs", 0),
        wins=record_data.get("wins", 0),
        losses=record_data.get("losses", 0),
        saves=record_data.get("saves", 0),
        holds=record_data.get("holds", 0),
        strikeouts_pitched=record_data.get("strikeouts_pitched", 0),
        walks_allowed=record_data.get("walks_allowed", 0),
        hits_allowed=record_data.get("hits_allowed", 0),
        games_pitched=record_data.get("games_pitched", 0),
    )
    
    player = Player(
        name=data["name"],
        uniform_number=data.get("uniform_number", 0),
        position=position,
        pitch_type=pitch_type,
        stats=stats,
        record=record,
        age=data.get("age", 20),
        years_pro=data.get("years_pro", 1),
        salary=data.get("salary", 1000),
        is_developmental=data.get("is_developmental", False),
    )
    
    # team_level を復元
    team_level_str = data.get("team_level")
    if team_level_str:
        from models import TeamLevel
        team_level_map = {
            "一軍": TeamLevel.FIRST,
            "二軍": TeamLevel.SECOND,
            "三軍": TeamLevel.THIRD,
        }
        player.team_level = team_level_map.get(team_level_str, None)
    
    # 成長データ
    growth_data = data.get("growth")
    if growth_data:
        player.growth = PlayerGrowth(
            potential=growth_data.get("potential", 5)
        )
        # 追加属性を設定
        player.growth.peak_age = growth_data.get("peak_age", 28)
        player.growth.growth_rate = growth_data.get("growth_rate", growth_data.get("development_speed", 1.0))
        player.growth.decline_rate = growth_data.get("decline_rate", 1.0)
    
    # 特殊能力
    if "special_abilities" in data:
        player.special_abilities = set(data["special_abilities"])
    
    return player


# グローバルインスタンス
save_manager = SaveManager()
