# -*- coding: utf-8 -*-
"""
選手生成ユーティリティ（球種別能力値対応・外国人生成修正版）
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
    """ランダムな選手を生成（通常用）"""
    name = generate_foreign_name() if is_foreign else generate_japanese_name()
    if age is None:
        age = random.randint(18, 38) if not is_foreign else random.randint(22, 35)

    stats = PlayerStats()

    def get_stat(mu=50, sigma=15, min_val=1, max_val=99):
        val = int(random.gauss(mu, sigma))
        return max(min_val, min(max_val, val))

    if position == Position.PITCHER:
        # --- 投手能力 ---
        stats.velocity = int(random.gauss(145, 7))
        stats.velocity = max(120, min(170, stats.velocity))

        stats.stuff = get_stat(50)
        stats.movement = get_stat(50)
        stats.control = get_stat(50)
        stats.stamina = get_stat(50)
        stats.hold_runners = get_stat(50)
        stats.gb_tendency = get_stat(50, 20, 1, 99)
        
        stats.vs_left_pitcher = get_stat(50)
        stats.vs_pinch = get_stat(50)
        stats.stability = get_stat(50)

        stats.set_defense_range(Position.PITCHER, get_stat(50))
        stats.arm = get_stat(50)
        stats.error = get_stat(50)
        stats.turn_dp = get_stat(50)

        stats.contact = get_stat(15, 7, 1, 40)
        stats.gap = get_stat(15, 7, 1, 40)
        stats.power = get_stat(15, 7, 1, 40)
        stats.eye = get_stat(15, 7, 1, 40)
        stats.avoid_k = get_stat(15, 7, 1, 40)
        stats.trajectory = random.randint(1, 2)

        stats.speed = get_stat(20, 7, 1, 60)
        stats.steal = get_stat(10, 5, 1, 40)
        stats.baserunning = get_stat(15, 7, 1, 60)

        # 変化球生成 (詳細パラメータ付き)
        balls = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カットボール", "シンカー", "ツーシーム"]
        num_pitches = random.randint(3, 6)
        selected_balls = random.sample(balls, num_pitches)
        
        stats.pitches = {}
        for ball in selected_balls:
            qual = get_stat(50)
            # 全体のstuff/movementを基準に±10の揺らぎを持たせる
            p_stuff = get_stat(stats.stuff, 10)
            p_move = get_stat(stats.movement, 10)
            
            stats.pitches[ball] = {
                "quality": qual,
                "stuff": p_stuff,
                "movement": p_move
            }
            
        if "ストレート" not in stats.pitches:
            stats.pitches["ストレート"] = {
                "quality": get_stat(stats.stuff, 10),
                "stuff": stats.stuff,
                "movement": get_stat(40, 10) # ストレートの変化量は控えめ
            }

    else:
        # --- 野手能力 ---
        stats.contact = get_stat(50)
        stats.gap = get_stat(50)
        stats.power = get_stat(50)
        stats.eye = get_stat(50)
        stats.avoid_k = get_stat(50)
        
        if stats.power > 70: stats.trajectory = random.choice([3, 4, 4])
        elif stats.power > 50: stats.trajectory = random.choice([2, 3, 3])
        else: stats.trajectory = random.choice([1, 2, 2])
        
        stats.vs_left_batter = get_stat(50)
        stats.chance = get_stat(50)

        stats.speed = get_stat(50)
        stats.steal = get_stat(50)
        stats.baserunning = get_stat(50)

        stats.bunt_sac = get_stat(50)
        stats.bunt_hit = get_stat(50)

        stats.arm = get_stat(50)
        stats.error = get_stat(50)
        stats.turn_dp = get_stat(50)

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
        elif position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            stats.set_defense_range(position, get_stat(50))

        stats.velocity = 130
        stats.control = 50
        stats.stuff = 50
        stats.movement = 50
        stats.stamina = 50

    stats.durability = get_stat(50)
    stats.recovery = get_stat(50)
    stats.work_ethic = get_stat(50)
    stats.intelligence = get_stat(50)
    stats.mental = get_stat(50)

    if random.random() < 0.7: player_throws = "右"
    else: player_throws = "左"
    
    if random.random() < 0.6: player_bats = "右"
    elif random.random() < 0.85: player_bats = "左"
    else: player_bats = "両"
    
    if position == Position.PITCHER:
        rating = stats.overall_pitching()
    else:
        rating = stats.overall_batting(position)

    base = 500
    salary = int(base * (rating ** 1.5) / 100) * 10000

    player = Player(
        name=name, position=position, pitch_type=pitch_type, stats=stats,
        age=age, status=status, uniform_number=number, is_foreign=is_foreign, salary=salary,
        bats=player_bats, throws=player_throws
    )

    return player

def create_draft_prospect(position: Position, pitch_type: Optional[PitchType] = None, base_potential: int = 5) -> DraftProspect:
    # 1. 年齢と出身区分の決定
    roll = random.random()
    if roll < 0.40: origin = "高校"; age = random.randint(17, 18); target_total = 180
    elif roll < 0.66: origin = "大学"; age = random.randint(21, 22); target_total = 220
    elif roll < 0.80: origin = "社会人"; age = random.randint(23, 26); target_total = 240
    else: origin = "独立リーグ"; age = random.randint(19, 26); age_factor = (age - 19) / 7.0; target_total = 190 + int(50 * age_factor)

    target_total += random.randint(-15, 15) 
    stats = PlayerStats()
    name = generate_japanese_name()

    def get_stat_gauss(mu, sigma=10):
        val = int(random.gauss(mu, sigma))
        return max(1, min(99, val))

    if position == Position.PITCHER:
        avg = target_total / 3
        v1 = random.gauss(avg, 10); v2 = random.gauss(avg, 10); v3 = random.gauss(avg, 10)
        current_sum = v1 + v2 + v3
        ratio = target_total / current_sum if current_sum > 0 else 1
        
        stats.stuff = max(1, min(99, int(v1 * ratio)))
        stats.control = max(1, min(99, int(v2 * ratio)))
        stats.stamina = max(1, min(99, int(v3 * ratio)))
        
        stats.velocity = int(random.gauss(140 + (target_total - 180)/4, 5)) 
        stats.velocity = max(125, min(165, stats.velocity))
        
        stats.movement = get_stat_gauss(50, 15)
        stats.vs_left_pitcher = get_stat_gauss(50, 15)
        stats.vs_pinch = get_stat_gauss(50, 15)
        stats.stability = get_stat_gauss(50, 15)
        stats.set_defense_range(Position.PITCHER, get_stat_gauss(50, 15))
        stats.arm = get_stat_gauss(50, 15)
        stats.error = get_stat_gauss(50, 15)
        stats.turn_dp = get_stat_gauss(50, 15)
        
        # 変化球 (詳細パラメータ)
        balls = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カットボール", "シンカー", "ツーシーム"]
        num_pitches = random.randint(2, 5)
        selected_balls = random.sample(balls, num_pitches)
        
        stats.pitches = {}
        for ball in selected_balls:
            base_val = int(random.gauss(stats.stuff, 10))
            stats.pitches[ball] = {
                "quality": get_stat_gauss(base_val),
                "stuff": get_stat_gauss(stats.stuff),
                "movement": get_stat_gauss(stats.movement)
            }
            
        if "ストレート" not in stats.pitches:
            stats.pitches["ストレート"] = {
                "quality": stats.stuff,
                "stuff": stats.stuff,
                "movement": get_stat_gauss(40)
            }

    else:
        avg = target_total / 5
        v1 = random.gauss(avg, 12); v2 = random.gauss(avg, 12); v3 = random.gauss(avg, 12)
        v4 = random.gauss(avg, 12); v5 = random.gauss(avg, 12)
        
        current_sum = v1 + v2 + v3 + v4 + v5
        ratio = target_total / current_sum if current_sum > 0 else 1
        
        stats.contact = max(1, min(99, int(v1 * ratio)))
        stats.power = max(1, min(99, int(v2 * ratio)))
        stats.speed = max(1, min(99, int(v3 * ratio)))
        stats.arm = max(1, min(99, int(v4 * ratio)))
        def_val = max(1, min(99, int(v5 * ratio)))
        
        if position == Position.CATCHER:
            stats.catcher_lead = get_stat_gauss(50, 10)
            stats.set_defense_range(Position.CATCHER, def_val)
        elif position == Position.FIRST: stats.set_defense_range(Position.FIRST, def_val)
        elif position == Position.SECOND: stats.set_defense_range(Position.SECOND, def_val)
        elif position == Position.THIRD: stats.set_defense_range(Position.THIRD, def_val)
        elif position == Position.SHORTSTOP: stats.set_defense_range(Position.SHORTSTOP, def_val)
        elif position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            stats.set_defense_range(position, def_val)
            
        stats.gap = stats.power 
        stats.eye = get_stat_gauss(50, 15)
        stats.avoid_k = stats.contact 
        stats.error = get_stat_gauss(50, 15)
        
        stats.velocity = 130
        stats.control = 50
        stats.stuff = 50

    stats.durability = get_stat_gauss(50, 15)
    stats.recovery = get_stat_gauss(50, 15)
    stats.work_ethic = get_stat_gauss(50, 15)
    stats.intelligence = get_stat_gauss(50, 15)
    stats.mental = get_stat_gauss(50, 15)

    pot_bonus = 0
    if origin == "高校": pot_bonus = random.randint(10, 30)
    elif origin == "大学": pot_bonus = random.randint(5, 20)
    elif origin == "独立リーグ": pot_bonus = random.randint(5, 25)
    else: pot_bonus = random.randint(0, 15)
    
    potential = int((target_total / (3 if position == Position.PITCHER else 5)) + pot_bonus)
    potential = max(1, min(99, potential))

    return DraftProspect(name, position, pitch_type, stats, age, origin, potential)

def create_foreign_free_agent(position: Position, pitch_type: Optional[PitchType] = None) -> Player:
    """
    外国人選手生成ロジック (球種別能力対応・能力底上げ・年齢相関強化・年俸適正化)
    """
    age = random.randint(18, 35)
    name = generate_foreign_name()
    
    # 修正: 年齢が高いほど能力が高くなる傾向を強化 (衰えではなく全盛期として扱う)
    # ベースターゲット値を全体的に引き上げ
    if age < 23:
        base_target = 200 + (age - 18) * 10  # 200 ~ 250 (若手有望株)
    elif age <= 30:
        base_target = 250 + (age - 23) * 6   # 250 ~ 292 (全盛期)
    else:
        # 30歳以上は実績あるベテランとして高めに設定 (以前は減衰していた)
        base_target = 292 + (age - 30) * 4   # 292 ~ 312 (超大物)

    # 分散を持たせて「当たり外れ」を演出
    target_total = int(random.gauss(base_target, 35))
    target_total = max(180, min(420, target_total)) # 下限180, 上限420 (Sランク級も出るように)

    stats = PlayerStats()
    
    def get_stat_gauss(mu, sigma=15):
        val = int(random.gauss(mu, sigma))
        return max(1, min(99, val))

    if position == Position.PITCHER:
        # 投手: 球威重視の傾向
        avg = target_total / 3
        v1 = random.gauss(avg + 8, 15) # 球威強め
        v2 = random.gauss(avg - 5, 15) # 制球はバラつく
        v3 = random.gauss(avg, 15)     # スタミナ
        
        current_sum = v1 + v2 + v3
        ratio = target_total / current_sum if current_sum > 0 else 1
        
        stats.stuff = max(1, min(99, int(v1 * ratio)))
        stats.control = max(1, min(99, int(v2 * ratio)))
        stats.stamina = max(1, min(99, int(v3 * ratio)))
        
        # 球速は速め (140~165km/h)
        stats.velocity = int(random.gauss(152 + (target_total - 200)/6, 5))
        stats.velocity = max(135, min(168, stats.velocity))
        
        # その他能力
        stats.movement = get_stat_gauss(55, 15)
        stats.set_defense_range(Position.PITCHER, get_stat_gauss(45, 15))
        stats.arm = get_stat_gauss(55, 15)
        stats.error = get_stat_gauss(45, 15)
        
        # 変化球 (球種別詳細パラメータ設定)
        balls = ["ストレート", "スライダー", "カーブ", "チェンジアップ", "ツーシーム", "カットボール", "SFF", "ナックルカーブ"]
        num_pitches = random.randint(2, 4)
        selected_balls = random.sample(balls, num_pitches)
        
        stats.pitches = {}
        for ball in selected_balls:
            # 変化球の精度などは全体のstuff/movementを基準に決定
            qual = get_stat_gauss(stats.stuff, 12)
            p_stuff = get_stat_gauss(stats.stuff, 12)
            p_move = get_stat_gauss(stats.movement, 12)
            
            stats.pitches[ball] = {
                "quality": qual,
                "stuff": p_stuff,
                "movement": p_move
            }
            
        if "ストレート" not in stats.pitches:
            stats.pitches["ストレート"] = {
                "quality": stats.stuff,
                "stuff": stats.stuff,
                "movement": get_stat_gauss(40, 10)
            }

    else:
        # 野手: パワー重視の傾向
        avg = target_total / 5
        
        v1 = random.gauss(avg - 2, 15)  # ミート
        v2 = random.gauss(avg + 12, 15) # パワー特化
        v3 = random.gauss(avg, 15)      # 走力
        v4 = random.gauss(avg + 5, 15)  # 肩強め
        v5 = random.gauss(avg - 5, 15)  # 守備粗め
        
        current_sum = v1 + v2 + v3 + v4 + v5
        ratio = target_total / current_sum if current_sum > 0 else 1
        
        stats.contact = max(1, min(99, int(v1 * ratio)))
        stats.power = max(1, min(99, int(v2 * ratio)))
        stats.speed = max(1, min(99, int(v3 * ratio)))
        stats.arm = max(1, min(99, int(v4 * ratio)))
        def_val = max(1, min(99, int(v5 * ratio)))
        
        # 守備位置適性
        if position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            stats.set_defense_range(position, def_val)
        elif position == Position.FIRST:
            stats.set_defense_range(position, def_val)
        else:
            stats.set_defense_range(position, def_val)

        stats.gap = stats.power 
        stats.eye = get_stat_gauss(48, 15)
        stats.avoid_k = get_stat_gauss(42, 15) 
        stats.error = get_stat_gauss(45, 15)
        
        # 弾道 (パワーに応じて高めに)
        if stats.power > 75: stats.trajectory = 4
        elif stats.power > 60: stats.trajectory = 3
        else: stats.trajectory = 2
        
        stats.velocity = 130
        stats.control = 50
        stats.stuff = 50

    # 共通メンタル・回復など
    stats.durability = get_stat_gauss(65, 15) # 外国人は体が強い傾向
    stats.recovery = get_stat_gauss(55, 15)
    stats.work_ethic = get_stat_gauss(50, 20)
    
    if random.random() < 0.75: player_throws = "右"
    else: player_throws = "左"
    
    if random.random() < 0.65: player_bats = "右"
    elif random.random() < 0.85: player_bats = "左"
    else: player_bats = "両"

    # 修正: 年俸・契約金計算ロジック
    # 能力(target_total)に応じて指数関数的に増加させる
    # 基準: Rating 200 -> 5,000万, 300 -> 2億5000万, 400 -> 6億
    
    base_salary_min = 5000 # 5000万
    if target_total <= 200:
        salary_man = base_salary_min
    else:
        # 200を超えた分について上乗せ
        excess = target_total - 200
        # 係数を調整して高騰させる
        # excess=100 (total=300) -> 100 * 200 = 20000 (2億) + 5000 = 2.5億
        # excess=200 (total=400) -> 200 * 300 = 60000 (6億) + 5000 = 6.5億
        multiplier = 200 + (excess * 1.5) # 能力が高いほど単価も上がる
        salary_man = base_salary_min + (excess * multiplier)
    
    annual_salary = int(salary_man) * 10000
    
    # 契約金 (Contract Bonus): 年俸の30%〜50%程度
    bonus_ratio = random.uniform(0.3, 0.5)
    contract_bonus = int(annual_salary * bonus_ratio)

    player = Player(
        name=name, position=position, pitch_type=pitch_type, stats=stats,
        age=age, status=PlayerStatus.ACTIVE, uniform_number=0, is_foreign=True, 
        salary=annual_salary, contract_bonus=contract_bonus, # 契約金を設定
        bats=player_bats, throws=player_throws
    )
    
    return player