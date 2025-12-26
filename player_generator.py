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

    types = ["高校", "学園", "実業", "工業", "学院"]
    return random.choice(prefs) + random.choice(types)

def _assign_pitcher_aptitudes(player: Player, role_hint: Optional[PitchType] = None):
    """
    投手の適正（先発・中継・抑え）を設定する
    要件:
    - 4段階評価 (4:◎, 3:〇, 2:△, 1:×)
    - 先発◎(4): 約60%
    - 中継ぎ◎(4): 約60%
    - 抑え◎(4): 約20%
    
    また、役割に応じてスタミナ/回復力を調整:
    - 先発: スタミナ高め、回復力普通
    - 中継ぎ: スタミナ低め、回復力高め
    - 抑え: スタミナ低め、回復力高め
    """
    if player.position != Position.PITCHER:
        return

    def get_sub_aptitude() -> int:
        """サブ適正値を決定（確率は少し高めに設定）"""
        roll = random.random()
        if roll < 0.50: return 1  # 50%で適性なし
        if roll < 0.80: return 2  # 30%で△
        if roll < 0.95: return 3  # 15%で〇
        return 4                  # 5%で◎

    # メイン役割を決定 (hintがあればそれを使う、なければ確率)
    main_role = role_hint
    if main_role is None:
        roll = random.random()
        if roll < 0.50:
            main_role = PitchType.STARTER
        elif roll < 0.90:
            main_role = PitchType.RELIEVER
        else:
            main_role = PitchType.CLOSER

    # メイン役割の適性は◎(4)、それ以外は確率で設定
    # player.pitch_type は設定しない (役割要素を排除)
    if main_role == PitchType.STARTER:
        player.starter_aptitude = 4
        player.middle_aptitude = get_sub_aptitude()
        player.closer_aptitude = get_sub_aptitude()
        # 先発: スタミナ高め (+15〜25)、回復力普通
        player.stats.stamina = min(99, player.stats.stamina + random.randint(15, 25))
    elif main_role == PitchType.RELIEVER:
        player.starter_aptitude = get_sub_aptitude()
        player.middle_aptitude = 4
        player.closer_aptitude = get_sub_aptitude()
        # 中継ぎ: スタミナ低め (-10〜-5)、回復力高め (+15〜25)
        player.stats.stamina = max(1, player.stats.stamina - random.randint(5, 10))
        player.stats.recovery = min(99, player.stats.recovery + random.randint(15, 25))
    else: # CLOSER
        player.starter_aptitude = get_sub_aptitude()
        player.middle_aptitude = get_sub_aptitude()
        player.closer_aptitude = 4
        # 抑え: スタミナ低め (-10〜-5)、回復力高め (+15〜25)
        player.stats.stamina = max(1, player.stats.stamina - random.randint(5, 10))
        player.stats.recovery = min(99, player.stats.recovery + random.randint(15, 25))

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
        stats.velocity = random.randint(140, 160)

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

        # 変化球生成 (詳細パラメータ付き: stuff/control/movement)
        balls = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カットボール", "シンカー", "ツーシーム"]
        num_pitches = random.randint(3, 6)
        selected_balls = random.sample(balls, num_pitches)
        
        # 基準となる平均値を設定
        base_stuff = get_stat(50)
        base_control = get_stat(50)
        base_movement = get_stat(50)
        
        stats.pitches = {}
        for ball in selected_balls:
            # 各球種ごとに±10の揺らぎを持たせる
            p_stuff = get_stat(base_stuff, 10)
            p_control = get_stat(base_control, 10)
            p_move = get_stat(base_movement, 10) if ball not in ["ストレート", "Straight"] else get_stat(40, 10)
            
            stats.pitches[ball] = {
                "stuff": p_stuff,
                "control": p_control,
                "movement": p_move
            }
            
        if "ストレート" not in stats.pitches:
            stats.pitches["ストレート"] = {
                "stuff": get_stat(base_stuff, 10),
                "control": get_stat(base_control, 10),
                "movement": get_stat(40, 10)
            }

        # --- 投手の打撃能力 (弱めに生成: 1-20, 弾道 1) ---
        stats.trajectory = 1
        stats.contact = random.randint(1, 20)
        stats.gap = random.randint(1, 20)
        stats.power = random.randint(1, 20)
        stats.eye = random.randint(1, 20)
        stats.avoid_k = random.randint(1, 20)
        
        # 投手の走力・肩・守備は野手と同じ基準で生成する
        stats.speed = get_stat(50)
        stats.steal = get_stat(50)
        stats.baserunning = get_stat(50)
        
        # Arm/Defense for Pitcher is typically good (already get_stat(50))
        # So we just update speed to match fielders.


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

        # --- 野手の投手能力 (弱めに生成: 1-10, 球速120km/h) ---
        stats.velocity = 120
        stats.control = random.randint(1, 10)
        stats.stamina = random.randint(1, 10)
        stats.breaking = random.randint(1, 10)
        stats.stuff = random.randint(1, 10)
        stats.movement = random.randint(1, 10)
        stats.stability = random.randint(1, 10)
        
        # 野手用ストレート球種を生成
        stats.pitches = {
            "ストレート": {
                "stuff": random.randint(1, 10),
                "control": random.randint(1, 10),
                "movement": random.randint(1, 10)
            }
        }

    stats.durability = get_stat(50)
    stats.recovery = get_stat(50)
    stats.work_ethic = get_stat(50)
    stats.intelligence = get_stat(50)
    stats.mental = get_stat(50)

    # Decide Throwing Hand
    # Catchers and Infielders (2B, SS, 3B) must throw Right
    force_right_throw = position in [Position.CATCHER, Position.SECOND, Position.SHORTSTOP, Position.THIRD]
    
    if force_right_throw:
        player_throws = "右"
    else:
        # General Population: ~72% Right, ~28% Left
        if random.random() < 0.72:
            player_throws = "右"
        else:
            player_throws = "左"

    # Decide Batting Hand based on Throwing Hand
    rand_bat = random.random()
    if player_throws == "右":
        # Right Throw: ~70% Right, ~20% Left, ~10% Switch
        if rand_bat < 0.70: player_bats = "右"
        elif rand_bat < 0.90: player_bats = "左"
        else: player_bats = "両"
    else:
        # Left Throw: ~5% Right, ~85% Left, ~10% Switch
        if rand_bat < 0.05: player_bats = "右"
        elif rand_bat < 0.90: player_bats = "左"
        else: player_bats = "両"
    
    # 総合力を選手詳細画面と同じ計算で取得（1-999スケール）
    if position == Position.PITCHER:
        total_ability = stats.overall_pitching()
    else:
        total_ability = stats.overall_batting(position)

    # 年俸計算: 超大幅格差（チーム年俸50〜120億円目標）
    # 総合力130-180: 240万～500万 (育成・新人最低レベル)
    # 総合力180-250: 500万～2000万 (控え・若手)
    # 総合力250-320: 2000万～1億 (中堅)
    # 総合力320-400: 1億～5億 (レギュラー級)
    # 総合力400+: 5億～15億 (スター選手)
    # base_salary は万円単位で計算
    
    if total_ability >= 400:
        # エース・主砲クラス (400+): 5億〜15億
        excess = min(total_ability - 400, 250)
        ratio = excess / 250
        base_salary = 50000 + (ratio ** 1.3) * 100000  # 5億〜15億
        randomness = random.uniform(0.9, 1.1)
    elif total_ability >= 320:
        # レギュラークラス (320-400): 1億〜5億
        excess = total_ability - 320
        ratio = excess / 80
        base_salary = 10000 + (ratio ** 1.2) * 40000  # 1億〜5億
        randomness = random.uniform(0.85, 1.15)
    elif total_ability >= 250:
        # 中堅 (250-320): 2000万～1億
        excess = total_ability - 250
        ratio = excess / 70
        base_salary = 1000 + (ratio ** 1.1) * 9000  # 1000万〜1億
        randomness = random.uniform(0.85, 1.15)
    elif total_ability >= 180:
        # 控え・若手 (180-250): 500万～2000万
        excess = total_ability - 180
        ratio = excess / 70
        base_salary = 500 + ratio * 500  # 500万〜1000万
        randomness = random.uniform(0.8, 1.2)
    else:
        # 育成・新人 (1-180): 240万～500万
        ratio = total_ability / 180
        base_salary = 240 + ratio * 260  # 240万〜500万
        randomness = random.uniform(0.8, 1.2)
    
    # 年齢係数（若手は低く、ベテランは高く）
    if age <= 22:
        # 新人・若手割引: 18歳=0.4, 22歳=0.7
        age_factor = 0.4 + (age - 18) * 0.075
        base_salary = int(base_salary * age_factor)
    elif age >= 26:
        # ベテラン割増: 26歳=1.0, 30歳=1.4, 35歳=1.95
        age_factor = 1.0 + (age - 26) * 0.11
        base_salary = int(base_salary * age_factor)
    
    # 外国人ボーナス: 2.5〜5.0倍高い
    if is_foreign:
        foreign_bonus = random.uniform(2.5, 5.0)
        base_salary = int(base_salary * foreign_bonus)
    
    salary = int(base_salary * randomness) * 10000  # 万円を円に変換
    salary = max(2400000, min(1500000000, salary))  # 240万～15億円にクランプ

    # Generate potential based on age (younger = higher potential)
    # Base potential decreases with age: ~75 at 18, ~50 at 28, ~30 at 38
    age_factor = max(0, 40 - age) / 22.0  # 0.0-1.0 scale (higher for young)
    base_potential = int(30 + 45 * age_factor)  # Range: 30-75 based on age
    potential = max(1, min(99, int(random.gauss(base_potential, 12))))

    player = Player(
        name=name, position=position, pitch_type=None, stats=stats,
        age=age, status=status, uniform_number=number, is_foreign=is_foreign, salary=salary,
        bats=player_bats, throws=player_throws, potential=potential
    )
    
    if position == Position.PITCHER:
        _assign_pitcher_aptitudes(player, role_hint=pitch_type)

    return player

def create_draft_prospect(position: Position, pitch_type: Optional[PitchType] = None, base_potential: int = 5) -> DraftProspect:
    # 1. 年齢と出身区分の決定
    roll = random.random()
    if roll < 0.40: origin = "高校"; age = random.randint(17, 18); target_total = 180
    elif roll < 0.66: origin = "大学"; age = random.randint(21, 22); target_total = 220
    elif roll < 0.80: origin = "社会人"; age = random.randint(23, 26); target_total = 240
    else: origin = "独立リーグ"; age = random.randint(19, 26); age_factor = (age - 19) / 7.0; target_total = 190 + int(50 * age_factor)

    # 投手は総合力を少し上げる (+15)
    pitcher_boost = 15 if position == Position.PITCHER else 0
    target_total += random.randint(-15, 15) + pitcher_boost 
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
        
        # 変化球 (詳細パラメータ: stuff/control/movement)
        balls = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", "カットボール", "シンカー", "ツーシーム"]
        num_pitches = random.randint(2, 5)
        selected_balls = random.sample(balls, num_pitches)
        
        # 基準値
        base_stuff = stats.stuff  # すでに設定済み
        base_control = stats.control  # すでに設定済み
        
        stats.pitches = {}
        for ball in selected_balls:
            p_stuff = get_stat_gauss(base_stuff)
            p_control = get_stat_gauss(base_control)
            p_move = get_stat_gauss(50) if ball not in ["ストレート", "Straight"] else get_stat_gauss(40)
            
            stats.pitches[ball] = {
                "stuff": p_stuff,
                "control": p_control,
                "movement": p_move
            }
            
        if "ストレート" not in stats.pitches:
            stats.pitches["ストレート"] = {
                "stuff": get_stat_gauss(base_stuff),
                "control": get_stat_gauss(base_control),
                "movement": get_stat_gauss(40)
            }
            
        # --- Draft: Pitcher Batting Stats (Weak 1-20, Traj 1) ---
        stats.trajectory = 1
        stats.contact = random.randint(1, 20)
        stats.gap = random.randint(1, 20)
        stats.power = random.randint(1, 20)
        stats.eye = random.randint(1, 20)
        stats.avoid_k = random.randint(1, 20)
        
        stats.speed = get_stat_gauss(50, 15)
        stats.steal = get_stat_gauss(50, 15)
        stats.baserunning = get_stat_gauss(50, 15)
        
        stats.set_defense_range(Position.PITCHER, get_stat_gauss(50, 15))
        stats.error = get_stat_gauss(50, 15)

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
        
        # --- Draft: Fielder Pitching Stats (Weak 1-10, Vel 120) ---
        stats.velocity = 120
        stats.control = random.randint(1, 10)
        stats.stuff = random.randint(1, 10)
        stats.stamina = random.randint(1, 10)
        stats.breaking = random.randint(1, 10)
        stats.movement = random.randint(1, 10)
        stats.stability = random.randint(1, 10)
        
        # ドラフト野手用ストレート球種
        stats.pitches = {
            "ストレート": {
                "stuff": random.randint(1, 10),
                "control": random.randint(1, 10),
                "movement": random.randint(1, 10)
            }
        }

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

    # pitch_type要素を生成しないため None を渡す
    prospect = DraftProspect(name, position, None, stats, age, origin, potential)
    
    # ドラフト候補の適正も設定（DraftProspectがPlayerを継承していない場合、別途考慮が必要だが、
    # ここではPlayerオブジェクトに変換された後に設定されることが多い。
    # しかしDraftProspect自体もaptitudeを持つべきなら修正が必要。
    # ひとまずDraftProspectはPlayerではないのでここでは設定できないが、
    # 実際に入団する際にPlayerオブジェクトになるタイミングで設定されるべき。
    # もしDraftProspectにフィールドがあれば設定する。
    # 確認: DraftProspectはmodels.pyにあるが、aptitudeフィールドがあるか不明。
    # なければPlayer変換時に設定するロジックが必要。
    # 修正: 今回はPlayer生成時に必ず呼ばれる create_random_player 等を修正したが、
    # DraftProspect -> Player変換時 (draft_logic.py?) も確認が必要。
    # いったんここはスキップし、Player生成時のみとする。
    return prospect

def create_foreign_free_agent(position: Position, pitch_type: Optional[PitchType] = None) -> Player:
    """
    外国人選手生成ロジック (2層システム: 育成可能/支配下専用)
    総合力を先に決めてから逆算で能力を生成
    
    - 育成可能助っ人: 18〜25歳、総合力150〜300、年俸3〜15百万
    - 支配下専用助っ人: 26〜35歳、総合力330〜450、年俸30百万〜
    """
    
    def overall_to_normalized(overall: int, pos_adj: int = 0) -> float:
        """総合力から正規化能力値(1-99スケール)を逆算"""
        rating = overall - pos_adj
        
        if rating <= 250:
            # 130-250 → normalized 1-50
            normalized = ((rating - 130) / 120) * 50
        elif rating <= 450:
            # 250-450 → normalized 50-70
            normalized = ((rating - 250) / 200) * 20 + 50
        else:
            # 450-999 → normalized 70-99 (べき乗逆算)
            excess_ratio = (rating - 450) / 549
            normalized = (excess_ratio ** (1/1.5)) * 29 + 70
        
        return max(1, min(99, normalized))
    
    def get_stat_gauss(mu, sigma=15):
        val = int(random.gauss(mu, sigma))
        return max(1, min(99, val))
    
    # 年齢層と総合力目標を決定 (50% 若手育成候補、50% 即戦力)
    if random.random() < 0.5:
        # 若手育成候補 (developmental eligible) - 総合力200〜320
        age = random.randint(20, 27)
        base_overall = 200 + (age - 20) * 15  # 200 ~ 305
        target_overall = int(random.gauss(base_overall, 25))
        target_overall = max(200, min(320, target_overall))  # 下限200, 上限320
        is_developmental_candidate = True
    else:
        # 即戦力 (main roster only) - 高能力層 総合力320〜500
        age = random.randint(26, 35)
        if age <= 30:
            base_overall = 340 + (age - 26) * 25  # 340 ~ 440
        else:
            base_overall = 440 + (age - 30) * 10   # 440 ~ 490
        target_overall = int(random.gauss(base_overall, 30))
        target_overall = max(320, min(500, target_overall))  # 下限320, 上限500
        is_developmental_candidate = False
    
    name = generate_foreign_name()
    stats = PlayerStats()
    
    if position == Position.PITCHER:
        # 投手: ポジション調整なし
        target_normalized = overall_to_normalized(target_overall, 0)
        
        # 投手の主要能力: stuff(3.5), control(3.5), movement(2.5), vel(1.5), stamina(2.0)
        # 合計重み9.5 + 3.5 = 13.0 (主要)
        # 全体重み15.5なので、残り2.5は共通能力
        
        # 主要能力を目標に合わせて生成
        stuff = get_stat_gauss(target_normalized, 12)
        control = get_stat_gauss(target_normalized - 5, 12)  # 制球はやや低め
        movement = get_stat_gauss(target_normalized, 10)
        stamina = get_stat_gauss(target_normalized, 10)
        
        # 調整: 重み付き平均が target_normalized に近づくように補正
        # weighted = (stuff*3.5 + control*3.5 + movement*2.5 + vel_rating*1.5 + stamina*2.0) / 13.0
        vel_rating = get_stat_gauss(target_normalized + 5, 12)  # 速球派傾向
        
        weighted_sum = stuff*3.5 + control*3.5 + movement*2.5 + vel_rating*1.5 + stamina*2.0
        current_normalized = weighted_sum / 13.0
        
        # 補正係数
        if current_normalized > 0:
            correction = target_normalized / current_normalized
            stuff = max(1, min(99, int(stuff * correction)))
            control = max(1, min(99, int(control * correction)))
            movement = max(1, min(99, int(movement * correction)))
            stamina = max(1, min(99, int(stamina * correction)))
        
        stats.stuff = stuff
        stats.control = control
        stats.movement = movement
        stats.stamina = stamina
        
        # 球速: vel_rating から逆算 (rating = (kmh - 130) * 2 + 30)
        stats.velocity = max(130, min(165, int((vel_rating - 30) / 2 + 130)))
        
        # その他能力
        stats.stability = get_stat_gauss(target_normalized, 15)
        stats.vs_pinch = get_stat_gauss(target_normalized, 15)
        stats.hold_runners = get_stat_gauss(target_normalized - 5, 15)
        stats.gb_tendency = get_stat_gauss(50, 20)
        stats.set_defense_range(Position.PITCHER, get_stat_gauss(45, 15))
        stats.arm = get_stat_gauss(55, 15)
        stats.error = get_stat_gauss(45, 15)
        
        # 変化球
        balls = ["ストレート", "スライダー", "カーブ", "チェンジアップ", "ツーシーム", "カットボール", "SFF", "ナックルカーブ"]
        num_pitches = random.randint(2, 4)
        selected_balls = random.sample(balls, num_pitches)
        
        stats.pitches = {}
        for ball in selected_balls:
            p_stuff = get_stat_gauss(stats.stuff, 12)
            p_control = get_stat_gauss(stats.control, 12)
            p_move = get_stat_gauss(55, 12) if ball not in ["ストレート", "Straight"] else get_stat_gauss(40, 10)
            stats.pitches[ball] = {"stuff": p_stuff, "control": p_control, "movement": p_move}
            
        if "ストレート" not in stats.pitches:
            stats.pitches["ストレート"] = {
                "stuff": get_stat_gauss(stats.stuff, 12),
                "control": get_stat_gauss(stats.control, 12),
                "movement": get_stat_gauss(40, 10)
            }

        # 投手の打撃 (弱い)
        stats.trajectory = 1
        stats.contact = random.randint(1, 20)
        stats.gap = random.randint(1, 20)
        stats.power = random.randint(1, 20)
        stats.eye = random.randint(1, 20)
        stats.avoid_k = random.randint(1, 20)
        stats.speed = get_stat_gauss(50, 15)
        stats.steal = get_stat_gauss(50, 15)
        stats.baserunning = get_stat_gauss(50, 15)

    else:
        # 野手: ポジション調整を考慮
        pos_adj = 0
        if position == Position.CATCHER: pos_adj = 15
        elif position == Position.SHORTSTOP: pos_adj = 10
        elif position == Position.SECOND: pos_adj = 5
        elif position == Position.CENTER: pos_adj = 5
        elif position == Position.THIRD: pos_adj = -5
        elif position == Position.RIGHT: pos_adj = -5
        elif position == Position.LEFT: pos_adj = -10
        elif position == Position.FIRST: pos_adj = -10
        elif position == Position.DH: pos_adj = -20
        
        target_normalized = overall_to_normalized(target_overall, pos_adj)
        
        # 野手の主要能力: contact(3.5), power(3.0), speed(1.5), fielding(3.0), arm(1.5)
        # 外国人は特にパワー重視
        contact = get_stat_gauss(target_normalized - 2, 12)
        power = get_stat_gauss(target_normalized + 10, 12)  # パワー特化
        speed = get_stat_gauss(target_normalized, 12)
        arm = get_stat_gauss(target_normalized + 5, 12)
        fielding = get_stat_gauss(target_normalized - 5, 12)  # 守備はやや粗め
        
        # 重み付き平均で補正
        weighted_sum = contact*3.5 + power*3.0 + speed*1.5 + fielding*3.0 + arm*1.5
        current_normalized = weighted_sum / 12.5
        
        if current_normalized > 0:
            correction = target_normalized / current_normalized
            contact = max(1, min(99, int(contact * correction)))
            power = max(1, min(99, int(power * correction)))
            speed = max(1, min(99, int(speed * correction)))
            arm = max(1, min(99, int(arm * correction)))
            fielding = max(1, min(99, int(fielding * correction)))
        
        stats.contact = contact
        stats.power = power
        stats.speed = speed
        stats.arm = arm
        stats.set_defense_range(position, fielding)

        stats.gap = stats.power 
        stats.eye = get_stat_gauss(target_normalized - 5, 15)
        stats.avoid_k = get_stat_gauss(target_normalized - 8, 15)  # 外国人は三振多め
        stats.error = get_stat_gauss(target_normalized - 5, 15)
        stats.steal = get_stat_gauss(target_normalized, 15)
        stats.baserunning = get_stat_gauss(target_normalized, 15)
        stats.bunt_sac = get_stat_gauss(30, 15)
        stats.bunt_hit = get_stat_gauss(30, 15)
        stats.vs_left_batter = get_stat_gauss(target_normalized, 15)
        stats.chance = get_stat_gauss(target_normalized, 15)
        stats.turn_dp = get_stat_gauss(45, 15)
        stats.catcher_lead = get_stat_gauss(target_normalized, 15) if position == Position.CATCHER else get_stat_gauss(30, 15)
        
        # 弾道 (パワーに応じて)
        if stats.power > 75: stats.trajectory = 4
        elif stats.power > 60: stats.trajectory = 3
        else: stats.trajectory = 2
        
        # 野手の投球能力 (弱い)
        stats.velocity = 120
        stats.control = random.randint(1, 10)
        stats.stuff = random.randint(1, 10)
        stats.stamina = random.randint(1, 10)
        stats.breaking = random.randint(1, 10)
        stats.movement = random.randint(1, 10)
        stats.stability = random.randint(1, 10)
        
        stats.pitches = {
            "ストレート": {
                "stuff": random.randint(1, 10),
                "control": random.randint(1, 10),
                "movement": random.randint(1, 10)
            }
        }

    # 共通メンタル・回復など (全選手)
    stats.durability = get_stat_gauss(65, 15) # 外国人は体が強い傾向
    stats.recovery = get_stat_gauss(55, 15)
    stats.work_ethic = get_stat_gauss(50, 20)
    stats.mental = get_stat_gauss(50, 15)
    stats.intelligence = get_stat_gauss(45, 15)
    
    # 投手追加能力
    if position == Position.PITCHER:
        stats.hold_runners = get_stat_gauss(50, 15)
        stats.gb_tendency = get_stat_gauss(50, 20)
        stats.vs_pinch = get_stat_gauss(50, 15)
        stats.stability = get_stat_gauss(50, 15)
        stats.vs_left_pitcher = get_stat_gauss(50, 15)
    
    if random.random() < 0.75: player_throws = "右"
    else: player_throws = "左"
    
    if random.random() < 0.65: player_bats = "右"
    elif random.random() < 0.85: player_bats = "左"
    else: player_bats = "両"

    # 総合力を計算（選手詳細画面と同じ）
    if position == Position.PITCHER:
        total_ability = stats.overall_pitching()
    else:
        total_ability = stats.overall_batting(position)
    
    # 即戦力外国人年俸システム（超格差）
    # 層1: 総合力400-500 → 年俸5億〜30億（エース・主砲級）
    # 層2: 総合力320-400 → 年俸1億〜5億（レギュラー級）
    # 層3: 総合力200-320 → 年俸1000万〜1億（育成可）
    
    if total_ability >= 400:
        # エリート外国人 (400-500): 5億～30億
        is_developmental_candidate = False
        excess = min(total_ability - 400, 100)
        ratio = excess / 100
        base_salary_man = 50000 + (ratio ** 1.3) * 250000  # 5億〜30億
        
        # 若さプレミアム
        if age <= 30:
            youth_factor = 1.0 + (30 - age) * 0.08
        else:
            youth_factor = max(0.7, 1.0 - (age - 30) * 0.06)
        base_salary_man = int(base_salary_man * youth_factor)
    elif total_ability >= 320:
        # 高能力外国人 (320-400): 1億～5億
        is_developmental_candidate = False
        excess = total_ability - 320
        ratio = excess / 80
        base_salary_man = 10000 + (ratio ** 1.2) * 40000  # 1億〜5億
        
        # 若さプレミアム
        if age <= 30:
            youth_factor = 1.0 + (30 - age) * 0.06
        else:
            youth_factor = max(0.75, 1.0 - (age - 30) * 0.05)
        base_salary_man = int(base_salary_man * youth_factor)
    else:
        # 育成可能外国人 (200-320): 1000万～1億
        is_developmental_candidate = True
        ratio = max(0, (total_ability - 200) / 120)
        base_salary_man = 1000 + (ratio ** 1.1) * 9000  # 1000万～1億
        base_salary_man = max(1000, min(10000, base_salary_man))
    
    annual_salary = int(base_salary_man) * 10000
    annual_salary = max(10000000, min(3000000000, annual_salary))  # 1000万～30億円にクランプ
    
    # 契約金 (Contract Bonus): 年俸の30%〜60%（若いほど高い）
    bonus_base_ratio = 0.3 + (35 - age) * 0.015  # 35歳=0.3, 26歳=0.435
    bonus_ratio = random.uniform(bonus_base_ratio * 0.9, bonus_base_ratio * 1.1)
    contract_bonus = int(annual_salary * bonus_ratio)

    # pitch_typeは生成しない
    player = Player(
        name=name, position=position, pitch_type=None, stats=stats,
        age=age, status=PlayerStatus.ACTIVE, uniform_number=0, is_foreign=True, 
        salary=annual_salary, contract_bonus=contract_bonus,
        bats=player_bats, throws=player_throws
    )
    
    # 育成候補フラグを追加属性として設定
    player.is_developmental_candidate = is_developmental_candidate
    
    if position == Position.PITCHER:
        _assign_pitcher_aptitudes(player, role_hint=pitch_type)
    
    return player