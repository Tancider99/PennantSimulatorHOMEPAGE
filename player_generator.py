# -*- coding: utf-8 -*-
"""
選手生成ユーティリティ（OOTPスタイル対応版）
"""
import random
from typing import Optional, List
from models import Player, PlayerStats, Position, PitchType, PlayerStatus, DraftProspect
from constants import JAPANESE_SURNAMES, JAPANESE_FIRSTNAMES, FOREIGN_SURNAMES, FOREIGN_FIRSTNAMES


def generate_japanese_name() -> str:
    return random.choice(JAPANESE_SURNAMES) + random.choice(JAPANESE_FIRSTNAMES)

def generate_foreign_name() -> str:
    return f"{random.choice(FOREIGN_FIRSTNAMES)} {random.choice(FOREIGN_SURNAMES)}"

def generate_high_school_name() -> str:
    prefs = ["北海", "東都", "なにわ", "西京", "南国"]
    types = ["高校", "学園", "実業", "工業", "学院"]
    return random.choice(prefs) + random.choice(types)

def create_random_player(position: Position,
                        pitch_type: Optional[PitchType] = None,
                        status: PlayerStatus = PlayerStatus.ACTIVE,
                        number: int = 0,
                        is_foreign: bool = False,
                        age: int = None) -> Player:
    """ランダムな選手を生成（OOTPスタイル対応版）

    能力値は1-99スケール（平均50）
    """
    name = generate_foreign_name() if is_foreign else generate_japanese_name()
    if age is None:
        age = random.randint(18, 38) if not is_foreign else random.randint(22, 35)

    stats = PlayerStats()

    # 能力値生成ヘルパー (正規分布、1-99スケール)
    def get_stat(mu=50, sigma=15, min_val=1, max_val=99):
        val = int(random.gauss(mu, sigma))
        return max(min_val, min(max_val, val))

    if position == Position.PITCHER:
          # --- 投手能力 ---
          # 球速: 平均145km/h, 標準偏差7km/h, 範囲120-170
                stats.velocity = int(random.gauss(145, 7))
                stats.velocity = max(120, min(170, stats.velocity))

                # 基本能力
                stats.stuff = get_stat(50)
                stats.movement = get_stat(50)
                stats.control = get_stat(50)
                stats.stamina = get_stat(50)
                stats.hold_runners = get_stat(50)
                stats.gb_tendency = get_stat(50, 20, 1, 99)
                
                # 新規追加能力
                stats.vs_left_pitcher = get_stat(50)
                stats.vs_pinch = get_stat(50)
                stats.stability = get_stat(50)

                # 守備 (投手)
                stats.set_defense_range(Position.PITCHER, get_stat(50))
                stats.arm = get_stat(50)
                stats.error = get_stat(50)
                stats.turn_dp = get_stat(50)

                # 打撃 (投手は低い)
                stats.contact = get_stat(15, 7, 1, 40)
                stats.gap = get_stat(15, 7, 1, 40)
                stats.power = get_stat(15, 7, 1, 40)
                stats.eye = get_stat(15, 7, 1, 40)
                stats.avoid_k = get_stat(15, 7, 1, 40)
                stats.trajectory = random.randint(1, 2) # 投手は低弾道

                # 走塁 (投手は低い)
                stats.speed = get_stat(20, 7, 1, 60)
                stats.steal = get_stat(10, 5, 1, 40)
                stats.baserunning = get_stat(15, 7, 1, 60)

                # 変化球
                balls = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カットボール", "シンカー", "ツーシーム"]
                num_pitches = random.randint(3, 6)
                selected_balls = random.sample(balls, num_pitches)
                stats.pitches = {ball: get_stat(50) for ball in selected_balls}
                if "ストレート" not in stats.pitches:
                        stats.pitches["ストレート"] = get_stat()

    else:
        # --- 野手能力 ---
        stats.contact = get_stat(50)
        stats.gap = get_stat(50)
        stats.power = get_stat(50)
        stats.eye = get_stat(50)
        stats.avoid_k = get_stat(50)
        
        # 弾道 (パワーがあるほど高くなりやすい)
        if stats.power > 70: stats.trajectory = random.choice([3, 4, 4])
        elif stats.power > 50: stats.trajectory = random.choice([2, 3, 3])
        else: stats.trajectory = random.choice([1, 2, 2])
        
        # 新規追加能力
        stats.vs_left_batter = get_stat(50)
        stats.chance = get_stat(50)

        stats.speed = get_stat(50)
        stats.steal = get_stat(50)
        stats.baserunning = get_stat(50)

        # バント
        stats.bunt_sac = get_stat(50)
        stats.bunt_hit = get_stat(50)

        # 守備 (共通)
        stats.arm = get_stat(50)
        stats.error = get_stat(50)
        stats.turn_dp = get_stat(50)

        # 守備 (ポジション別範囲 & 固有)
        if position == Position.CATCHER:
            stats.catcher_lead = get_stat(50)
            stats.set_defense_range(Position.CATCHER, get_stat(50))
        elif position == Position.FIRST:
            stats.set_defense_range(Position.FIRST, get_stat(50))
        elif position == Position.SECOND:
            stats.set_defense_range(Position.SECOND, get_stat(50))
        elif position == Position.THIRD:
            stats.set_defense_range(Position.THIRD, get_stat(50))
        elif position == Position.SHORTSTOP:
            stats.set_defense_range(Position.SHORTSTOP, get_stat(50))
        elif position == Position.OUTFIELD:
            stats.set_defense_range(Position.OUTFIELD, get_stat(50))

        # 投手能力 (野手)
        stats.velocity = 130
        stats.control = 50
        stats.stuff = 50
        stats.movement = 50
        stats.stamina = 50

    # 共通能力
    stats.durability = get_stat(50)
    stats.recovery = get_stat(50) # 新規
    stats.work_ethic = get_stat(50)
    stats.intelligence = get_stat(50)
    stats.mental = get_stat(50) # 新規

    # 年俸計算
    if position == Position.PITCHER:
        rating = stats.overall_pitching()
    else:
        # ポジションを渡して正確な評価を計算
        rating = stats.overall_batting(position)

    base = 500
    salary = int(base * (rating ** 1.5) / 100) * 10000

    player = Player(
        name=name, position=position, pitch_type=pitch_type, stats=stats,
        age=age, status=status, uniform_number=number, is_foreign=is_foreign, salary=salary
    )

    return player

def create_draft_prospect(position: Position, pitch_type: Optional[PitchType] = None, base_potential: int = 5) -> DraftProspect:
    player = create_random_player(position, pitch_type, age=18)
    return DraftProspect(player.name, position, pitch_type, player.stats, 18, "高校", base_potential)

def create_foreign_free_agent(position: Position, pitch_type: Optional[PitchType] = None) -> Player:
    return create_random_player(position, pitch_type, is_foreign=True, age=27)