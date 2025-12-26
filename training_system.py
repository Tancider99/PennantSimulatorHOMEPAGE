# -*- coding: utf-8 -*-
"""
Training System - 練習システム
選手の練習メニュー適用と能力成長を管理
"""
import random
from typing import Optional, Dict, Any
from models import (
    Player, PlayerType, TrainingMenu, Position,
    PLAYER_TYPE_GROWTH_MODIFIERS
)


# 可能な球種リスト
PITCH_TYPES = [
    "ストレート", "ツーシーム", "カットボール",
    "スライダー", "カーブ", "フォーク", "チェンジアップ", "シンカー",
    "シュート", "ナックル", "SFF", "Vスライダー", "スラーブ"
]

def learn_new_pitch(player: Player) -> Optional[str]:
    """新球種を習得する（ランダム選択）"""
    if player.position != Position.PITCHER:
        return None
        
    current_pitches = list(player.stats.pitches.keys())
    
    # ストレートは除外して候補作成
    candidates = [p for p in PITCH_TYPES if p not in current_pitches and p not in ["ストレート", "Straight"]]
    
    if not candidates:
        return None
        
    new_pitch = random.choice(candidates)
    
    # Add new pitch with random base stats (1-30)
    player.stats.pitches[new_pitch] = {
        "stuff": random.randint(1, 30),
        "control": random.randint(1, 30),
        "movement": random.randint(1, 30)
    }
    
    return new_pitch


def get_available_pitches(player: Player) -> list:
    """習得可能な球種リストを取得"""
    if player.position != Position.PITCHER:
        return []
    
    # Max 10 pitches
    if len(player.stats.pitches) >= 10:
        return []
    
    current_pitches = list(player.stats.pitches.keys())
    # ストレートは除外
    return [p for p in PITCH_TYPES if p not in current_pitches and p not in ["ストレート", "Straight"]]


def learn_specific_pitch(player: Player, pitch_name: str) -> bool:
    """指定した球種を習得"""
    if player.position != Position.PITCHER:
        return False
    
    # Max 10 pitches
    if len(player.stats.pitches) >= 10:
        return False
    
    if pitch_name in player.stats.pitches:
        return False  # Already has this pitch
    
    if pitch_name not in PITCH_TYPES:
        return False  # Invalid pitch type
    
    # Add new pitch with random base stats (1-30)
    player.stats.pitches[pitch_name] = {
        "stuff": random.randint(1, 30),
        "control": random.randint(1, 30),
        "movement": random.randint(1, 30)
    }
    
    return True

# 練習メニューと対応する能力の対応表
TRAINING_STAT_MAP = {
    TrainingMenu.CONTACT: "contact",
    TrainingMenu.GAP: "gap",
    TrainingMenu.POWER: "power",
    TrainingMenu.EYE: "eye",
    TrainingMenu.AVOID_K: "avoid_k",
    TrainingMenu.SPEED: "speed",
    TrainingMenu.STEAL: "steal",
    TrainingMenu.BASERUNNING: "baserunning",
    TrainingMenu.ARM: "arm",
    TrainingMenu.FIELDING: "error",  # 守備範囲は別処理
    TrainingMenu.ERROR: "error",
    TrainingMenu.BUNT: "bunt_sac",
    TrainingMenu.CHANCE: "chance",
    TrainingMenu.VS_LEFT: "vs_left_batter",
    TrainingMenu.VELOCITY: "velocity",
    TrainingMenu.CONTROL: "control",      # 全球種のcontrolを上昇
    TrainingMenu.STUFF: "stuff",          # 全球種のstuffを上昇
    TrainingMenu.MOVEMENT: "movement",    # 全球種のmovementを上昇
    TrainingMenu.STAMINA: "stamina",
    TrainingMenu.HOLD_RUNNERS: "hold_runners",
    TrainingMenu.VS_PINCH: "vs_pinch",
    TrainingMenu.STABILITY: "stability",
    TrainingMenu.DURABILITY: "durability",
    TrainingMenu.RECOVERY: "recovery",
    TrainingMenu.MENTAL: "mental",
    TrainingMenu.INTELLIGENCE: "intelligence",
    TrainingMenu.TRAJECTORY: "trajectory",
    TrainingMenu.CATCHER_LEAD: "catcher_lead",
    TrainingMenu.TURN_DP: "turn_dp",
    TrainingMenu.NEW_PITCH: "new_pitch_progress", # Add mapping
    TrainingMenu.REST: None,  # 休養は能力上昇なし
}

# 表示用名称マップ
STAT_DISPLAY_NAMES = {
    "contact": "ミート",
    "gap": "ミート", # パワープロスタイルではギャップはミートに統合的扱い
    "power": "パワー",
    "eye": "選球眼",
    "avoid_k": "三振回避",
    "speed": "走力",
    "steal": "盗塁",
    "baserunning": "走塁",
    "arm": "肩力",
    "fielding": "守備力", # Fixed
    "error": "捕球",
    "bunt_sac": "バント",
    "chance": "チャンス",
    "vs_left_batter": "対左投手",
    "trajectory": "弾道",
    "velocity": "球速",
    "control": "制球",
    "stuff": "球威",
    "movement": "変化球",
    "stamina": "スタミナ",
    "hold_runners": "クイック",
    "vs_pinch": "対ピンチ",
    "stability": "安定感",
    "durability": "ケガしにくさ",
    "recovery": "回復",
    "mental": "打たれ強さ",
    "intelligence": "野球脳",
    "vs_left_pitcher": "対左打者",
    "catcher_lead": "リード",
    "turn_dp": "併殺処理",
    "new_pitch_progress": "新球種",
}


def get_growth_modifier(player: Player, stat_name: str) -> float:
    """選手タイプに基づく成長倍率を取得
    
    Returns:
        1.5 for strong stats, 0.5 for weak stats, 1.0 otherwise
    """
    if not player.player_type:
        return 1.0
    
    modifiers = PLAYER_TYPE_GROWTH_MODIFIERS.get(player.player_type, {})
    strong = modifiers.get("strong", [])
    weak = modifiers.get("weak", [])
    
    if stat_name in strong:
        return 1.5
    elif stat_name in weak:
        return 0.5
    return 1.0


def get_coach_bonus(player: Player, stat_name: str, team=None) -> float:
    """
    コーチ能力に基づく練習効率ボーナスを計算
    
    Args:
        player: 対象選手
        stat_name: 練習対象の能力名
        team: チームオブジェクト (None の場合はボーナスなし)
    
    Returns:
        1.0 + bonus (例: 1.15 = +15%)
    """
    if not team or not hasattr(team, 'staff') or not team.staff:
        return 1.0
    
    from models import StaffRole, TeamLevel
    
    player_level = getattr(player, 'team_level', TeamLevel.FIRST)
    if player_level is None:
        player_level = TeamLevel.FIRST
    
    # コーチの種類と担当能力のマッピング
    COACH_STAT_MAP = {
        StaffRole.BATTING_COACH: [
            "contact", "gap", "power", "eye", "avoid_k", "chance", 
            "vs_left_batter", "vs_left_pitcher", "bunt_sac", "trajectory"
        ],
        StaffRole.PITCHING_COACH: [
            "velocity", "control", "stuff", "movement", "stamina", 
            "vs_pinch", "stability", "hold_runners"
        ],
        StaffRole.INFIELD_COACH: [
            "fielding", "error", "arm", "turn_dp", "baserunning", "speed"
        ],
        StaffRole.OUTFIELD_COACH: [
            "fielding", "error", "arm", "baserunning", "speed"
        ],
        StaffRole.BATTERY_COACH: [
            "catcher_lead", "arm", "blocking"
        ],
        StaffRole.BULLPEN_COACH: [
            "stamina", "vs_pinch", "mental", "recovery"
        ]
    }
    
    # 適切なコーチを探す
    best_coach_ability = 50  # デフォルト
    
    for staff in team.staff:
        if not staff.is_coach:
            continue
        if staff.team_level != player_level:
            continue
        
        # このコーチが担当する能力か確認
        coach_stats = COACH_STAT_MAP.get(staff.role, [])
        if stat_name in coach_stats:
            if staff.ability > best_coach_ability:
                best_coach_ability = staff.ability
    
    # ボーナス計算: ability 50 = 1.0, ability 80 = 1.15, ability 99 = 1.245
    bonus = 1.0 + (best_coach_ability - 50) * 0.005
    return bonus


def apply_training(player: Player, days: int = 1, team=None) -> Dict[str, Any]:
    """選手に練習を適用して能力を成長させる
    
    Args:
        player: 対象の選手
        days: 練習日数（デフォルト1日）
        team: チームオブジェクト（コーチボーナス計算用）
    
    Returns:
        成長結果の辞書 {stat_name: (old_value, new_value, change)}
    """
    result = {
        "player_name": player.name,
        "training_menu": player.training_menu.value if player.training_menu else "なし",
        "changes": {}
    }
    
    # 休養の場合は疲労回復のみ
    if player.training_menu == TrainingMenu.REST:
        old_fatigue = player.fatigue
        recovery_amount = 10 + int(player.stats.recovery * 0.2)
        player.fatigue = max(0, player.fatigue - recovery_amount * days)
        result["changes"]["fatigue"] = (old_fatigue, player.fatigue, player.fatigue - old_fatigue)
        return result
    
    # Natural recovery for non-REST menus (e.g. benched players training should recover slowly)
    current_fatigue = getattr(player, 'fatigue', 0)
    if current_fatigue > 0:
        rec_stat = getattr(player.stats, 'recovery', 50)
        # Recover 8-15 per day naturally even when training (must exceed training fatigue of 2-5)
        natural_rec = 8 + int((rec_stat - 50) * 0.15) * days
        if natural_rec < 3: natural_rec = 3 * days
        player.fatigue = max(0, current_fatigue - natural_rec)
    
    # Auto-training (お任せ): Select a random appropriate training menu
    # Use local variable to not modify player's training_menu setting
    active_menu = player.training_menu
    if not active_menu:
        if player.position == Position.PITCHER:
            auto_menus = [
                TrainingMenu.VELOCITY, TrainingMenu.CONTROL, TrainingMenu.STUFF, 
                TrainingMenu.MOVEMENT, TrainingMenu.STAMINA, TrainingMenu.HOLD_RUNNERS
            ]
        else:
            auto_menus = [
                TrainingMenu.CONTACT, TrainingMenu.POWER, TrainingMenu.EYE,
                TrainingMenu.SPEED, TrainingMenu.ARM, TrainingMenu.FIELDING
            ]
        active_menu = random.choice(auto_menus)
    
    # 対応する能力名を取得
    stat_name = TRAINING_STAT_MAP.get(active_menu)
    
    # 特殊マッピング: 対左はポジションで分岐
    if active_menu == TrainingMenu.VS_LEFT and player.position == Position.PITCHER:
        stat_name = "vs_left_pitcher"
        
    if not stat_name:
        return result
    
    # Get current stat value
    old_value = getattr(player.stats, stat_name, 50)
    
    # Special handling for max stats
    max_value = 99
    if stat_name == "velocity":
        max_value = 165
    elif stat_name == "trajectory":
        max_value = 4
    
    # Can't train stats already at max
    if old_value >= max_value:
        return result
    
    # Calculate XP gain (base: 1-3% per day)
    base_xp_gain = random.uniform(1.0, 3.0) * days
    
    # 練習態度補正: work_ethic (1-99) で 0.5x〜1.5x
    work_ethic = getattr(player.stats, 'work_ethic', 50)
    work_ethic_mult = 0.5 + (work_ethic / 100)
    
    # 年齢補正: 若いほど伸びやすい
    age_mult = 1.0
    if player.age <= 22:
        age_mult = 1.2
    elif player.age <= 25:
        age_mult = 1.0
    elif player.age <= 30:
        age_mult = 0.8
    else:
        age_mult = 0.5
    
    # 選手タイプ補正
    type_mult = get_growth_modifier(player, stat_name)
    
    # 潜在能力補正: potential (1-99) で 0.5x〜2.0x
    potential = getattr(player, 'potential', 50)
    potential_mult = 0.5 + (potential / 66.0)
    
    # XP required increases with current stat level
    # At low stats: 100% XP needed. At 90+: 500% XP needed
    stat_difficulty_mult = 1.0 + (old_value / 25.0)  # 1x at 0, 2x at 25, 3x at 50, 4x at 75, 4.96x at 99
    
    # 弾道は超高コスト
    if stat_name == "trajectory":
        stat_difficulty_mult *= 10.0
    
    # コーチボーナス
    coach_bonus = get_coach_bonus(player, stat_name, team)
    
    # Final XP gain
    xp_gain = base_xp_gain * work_ethic_mult * age_mult * type_mult * potential_mult * coach_bonus / stat_difficulty_mult
    
    # Initialize training_xp dict if needed
    if not hasattr(player, 'training_xp') or player.training_xp is None:
        player.training_xp = {}
    
    # Special handling for new pitch progress (uses existing system)
    if active_menu == TrainingMenu.NEW_PITCH:
        old_val = getattr(player.stats, "new_pitch_progress", 0)
        growth = random.uniform(0.5, 1.0) * work_ethic_mult * days
        new_val = min(100, old_val + growth)
        setattr(player.stats, "new_pitch_progress", new_val)
        result["changes"]["new_pitch_progress"] = (old_val, new_val, growth)
        
        if new_val >= 100 and old_val < 100:
            pitch_learned = learn_new_pitch(player)
            if pitch_learned: result["new_pitch_learned"] = pitch_learned
            setattr(player.stats, "new_pitch_progress", 0)
        
        return result
    
    # Update XP for the stat
    current_xp = player.training_xp.get(stat_name, 0.0)
    new_xp = current_xp + xp_gain
    
    # Check if XP hit 100% -> increase stat by 1
    stat_increased = False
    while new_xp >= 100.0 and int(old_value) < max_value:
        new_xp -= 100.0
        old_value = int(old_value) + 1
        stat_increased = True
        
        # Re-check max
        if old_value >= max_value:
            new_xp = 0.0
            break
    
    player.training_xp[stat_name] = max(0.0, min(99.99, new_xp))
    
    if stat_increased:
        setattr(player.stats, stat_name, int(old_value))
        actual_old = getattr(player.stats, stat_name, 50) - 1  # approximation
        result["changes"][stat_name] = (actual_old, int(old_value), 1)
    
    # Record XP progress in result
    result["xp_progress"] = {stat_name: player.training_xp[stat_name]}
    
    # 疲労増加は削除（ユーザー要望により練習では疲労しない）
    # Training no longer adds fatigue per user request
    
    return result


def apply_team_training(players: list, days: int = 1, team=None) -> list:
    """チーム全体に練習を適用
    
    Args:
        players: 選手リスト
        days: 練習日数
        team: チームオブジェクト（コーチボーナス計算用、投資設定参照用）
    
    Returns:
        各選手の成長結果リスト
    """
    # 投資設定から練習効果倍率を取得
    training_effectiveness = 1.0
    if team and hasattr(team, 'investment_settings') and team.investment_settings:
        training_effectiveness = team.investment_settings.get_training_effectiveness()
    
    # 練習日数を倍率で調整（効果的な日数として扱う）
    effective_days = days * training_effectiveness
    
    results = []
    for player in players:
        # Apply training to all players - apply_training handles auto mode (None)
        result = apply_training(player, effective_days, team)
        results.append(result)
    return results


def assign_default_player_type(player: Player):
    """選手タイプが未設定の場合、能力値から推定して設定"""
    if player.player_type:
        return
    
    if player.position == Position.PITCHER:
        # 投手タイプ判定
        velocity = getattr(player.stats, 'velocity', 145)
        control = getattr(player.stats, 'control', 50)
        movement = getattr(player.stats, 'movement', 50)
        
        if velocity >= 148:
            player.player_type = PlayerType.POWER_PITCHER
        elif control >= 60:
            player.player_type = PlayerType.FINESSE
        elif movement >= 60:
            player.player_type = PlayerType.JUNK
        else:
            player.player_type = PlayerType.POWER_PITCHER
    else:
        # 野手タイプ判定
        power = getattr(player.stats, 'power', 50)
        contact = getattr(player.stats, 'contact', 50)
        speed = getattr(player.stats, 'speed', 50)
        error = getattr(player.stats, 'error', 50)
        
        # 最も高い能力から判定
        max_stat = max(power, contact, speed, error)
        
        if max_stat == power and power >= 60:
            player.player_type = PlayerType.POWER
        elif max_stat == contact and contact >= 60:
            player.player_type = PlayerType.CONTACT
        elif max_stat == speed and speed >= 60:
            player.player_type = PlayerType.SPEED
        elif max_stat == error and error >= 60:
            player.player_type = PlayerType.DEFENSE
        else:
            player.player_type = PlayerType.BALANCED


def get_recommended_training(player: Player) -> list:
    """選手に推奨する練習メニューを取得"""
    if not player.player_type:
        assign_default_player_type(player)
    
    recommendations = []
    
    if player.position == Position.PITCHER:
        # 投手用推奨
        if player.player_type == PlayerType.POWER_PITCHER:
            recommendations = [TrainingMenu.VELOCITY, TrainingMenu.STUFF, TrainingMenu.STAMINA]
        elif player.player_type == PlayerType.FINESSE:
            recommendations = [TrainingMenu.CONTROL, TrainingMenu.MOVEMENT, TrainingMenu.STABILITY]
        elif player.player_type == PlayerType.JUNK:
            recommendations = [TrainingMenu.MOVEMENT, TrainingMenu.CONTROL, TrainingMenu.STABILITY]
        else:
            recommendations = [TrainingMenu.CONTROL, TrainingMenu.STAMINA, TrainingMenu.STUFF]
    else:
        # 野手用推奨
        if player.player_type == PlayerType.POWER:
            recommendations = [TrainingMenu.POWER, TrainingMenu.ARM, TrainingMenu.CONTACT]
        elif player.player_type == PlayerType.CONTACT:
            recommendations = [TrainingMenu.CONTACT, TrainingMenu.GAP, TrainingMenu.EYE]
        elif player.player_type == PlayerType.SPEED:
            recommendations = [TrainingMenu.SPEED, TrainingMenu.STEAL, TrainingMenu.BASERUNNING]
        elif player.player_type == PlayerType.DEFENSE:
            recommendations = [TrainingMenu.FIELDING, TrainingMenu.ERROR, TrainingMenu.ARM]
        else:
            recommendations = [TrainingMenu.CONTACT, TrainingMenu.POWER, TrainingMenu.SPEED]
    
    return recommendations


def resolve_auto_training(player: Player) -> TrainingMenu:
    """自動練習（お任せ）の場合のメニュー決定 logic"""
    # 1. 怪我/疲労チェック
    if player.is_injured:
        return TrainingMenu.RECOVERY
    if player.fatigue >= 80:
        return TrainingMenu.RECOVERY
        
    # 2. 推奨メニューからランダム or 弱点補強
    recs = get_recommended_training(player)
    if recs:
        return random.choice(recs)
        
    # fallback
    return TrainingMenu.STAMINA if player.position == Position.PITCHER else TrainingMenu.CONTACT

