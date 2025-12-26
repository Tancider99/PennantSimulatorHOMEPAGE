# -*- coding: utf-8 -*-
"""
チーム生成ユーティリティ (修正版: 外野3ポジション対応)
固定選手データがある場合は読み込み、なければ新規生成
"""
from models import Team, Position, PitchType, PlayerStatus, League, TeamLevel
from player_generator import create_random_player
import random


def create_team(team_name: str, league: League) -> Team:
    """チームを生成（支配下67〜70人＋育成30〜35人）- NPB風設定を適用"""
    from team_data_manager import get_team_config
    from models import Stadium, TeamFinance, FanBase
    
    # NPB風設定を取得
    config = get_team_config(team_name)
    
    # 球場を作成
    stadium_cfg = config.get("stadium", {})
    stadium = Stadium(
        name=stadium_cfg.get("name", f"{team_name}スタジアム"),
        capacity=stadium_cfg.get("capacity", 35000),
        is_dome=stadium_cfg.get("is_dome", False),
        pf_hr=stadium_cfg.get("pf_hr", 1.0),
        pf_runs=stadium_cfg.get("pf_runs", 1.0),
        pf_1b=stadium_cfg.get("pf_1b", 1.0),
        pf_2b=stadium_cfg.get("pf_2b", 1.0),
        pf_3b=stadium_cfg.get("pf_3b", 1.0),
        pf_so=stadium_cfg.get("pf_so", 1.0),
        pf_bb=stadium_cfg.get("pf_bb", 1.0)
    )
    
    # ファン層データを設定
    fans_cfg = config.get("fans", {})
    fan_base = FanBase(
        light_fans=fans_cfg.get("light", 300000),
        middle_fans=fans_cfg.get("middle", 150000),
        core_fans=fans_cfg.get("core", 50000)
    )
    
    # チームを作成（NPB風設定を適用）
    team = Team(
        name=team_name,
        league=league,
        stadium=stadium,
        color=config.get("color"),
        abbr=config.get("abbr")
    )
    
    # 財務データを設定（ファン層を含む）
    team.finance = TeamFinance(fan_base=fan_base)

    
    number = 1
    player_count = 0  # 支配下選手のカウント
    first_team_limit = 31  # 一軍上限
    
    # ==============================
    # 支配下日本人選手 (64人)
    # 外国人3〜6人を追加して67〜70人になる
    # ==============================
    
    # 投手 (25人) - 5:4:1 比率 (12:10:3)
    for _ in range(12):
        p = create_random_player(Position.PITCHER, PitchType.STARTER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        p.team_level = TeamLevel.SECOND # Default to Farm
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(10):
        p = create_random_player(Position.PITCHER, PitchType.RELIEVER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        p.team_level = TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(3):
        p = create_random_player(Position.PITCHER, PitchType.CLOSER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        p.team_level = TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    
    # 野手 (39人)
    # 捕手 (4)
    for _ in range(4):
        p = create_random_player(Position.CATCHER, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_catcher(p)
        p.fix_main_position()
        p.team_level = TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    
    # 内野手 (19)
    for pos, count in [(Position.FIRST, 4), (Position.SECOND, 5), (Position.THIRD, 5), (Position.SHORTSTOP, 5)]:
        for _ in range(count):
            p = create_random_player(pos, status=PlayerStatus.ACTIVE, number=number)
            p.is_developmental = False
            _add_sub_positions_infielder(p, pos)
            p.fix_main_position()
            p.team_level = TeamLevel.SECOND
            player_count += 1
            team.players.append(p)
            number += 1
            
    # 外野手 (16)
    for pos, count in [(Position.LEFT, 5), (Position.CENTER, 6), (Position.RIGHT, 5)]:
        for _ in range(count):
            p = create_random_player(pos, status=PlayerStatus.ACTIVE, number=number)
            p.is_developmental = False
            _add_sub_positions_outfielder(p)
            p.fix_main_position()
            p.team_level = TeamLevel.SECOND
            player_count += 1
            team.players.append(p)
            number += 1
            
    # ==============================
    # 1軍昇格ロジック (Best Selection)
    # ==============================
    # 支配下選手の中からベストメンバーを選出
    majors = [p for p in team.players if not p.is_developmental]
    m_pitchers = [p for p in majors if p.position.value == "投手"]
    m_batters = [p for p in majors if p.position.value != "投手"]
    
    # 能力順にソート (降順)
    m_pitchers.sort(key=lambda x: x.stats.overall_pitching(), reverse=True)
    m_batters.sort(key=lambda x: x.stats.overall_batting(), reverse=True)
    
    # 上位15人を1軍へ
    for i in range(min(15, len(m_pitchers))):
        m_pitchers[i].team_level = TeamLevel.FIRST
        
    # 上位16人を1軍へ
    for i in range(min(16, len(m_batters))):
        m_batters[i].team_level = TeamLevel.FIRST
    
    # ==============================
    # 支配下外国人選手 (3〜6人、27〜35歳)
    # ==============================
    num_foreign_major = random.randint(3, 6)
    foreign_number = 90  # 外国人は90番台
    foreign_positions = [Position.PITCHER, Position.FIRST, Position.LEFT, Position.RIGHT, Position.CENTER]
    
    for _ in range(num_foreign_major):
        pos = random.choice(foreign_positions)
        pitch_type = None
        if pos == Position.PITCHER:
            pitch_type = random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER])
        
        p = create_random_player(
            pos, pitch_type, PlayerStatus.ACTIVE, foreign_number,
            is_foreign=True, age=random.randint(27, 35)
        )
        p.is_developmental = False
        p.team_level = TeamLevel.SECOND  # 2軍スタート
        
        if pos == Position.PITCHER:
            _add_sub_positions_pitcher(p)
        elif pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            _add_sub_positions_outfielder(p)
        else:
            _add_sub_positions_infielder(p, pos)
            
        p.fix_main_position()
        team.players.append(p)
        foreign_number += 1
    
    # ==============================
    # 育成選手 (30人) - 背番号は3桁、年齢18〜25歳
    # ==============================
    dev_number = 101
    
    # 育成投手 (12人、日本人)
    for _ in range(12):
        p = create_random_player(
            Position.PITCHER, 
            None, # 自動決定（5:4:1）
            PlayerStatus.FARM, 
            dev_number,
            is_foreign=False,
            age=random.randint(18, 25)
        )
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD
        _add_sub_positions_pitcher(p)
        _adjust_developmental_stats(p)
        # 育成選手の年俸: 2〜10百万
        p.salary = random.randint(2, 10) * 1000000
        team.players.append(p)
        dev_number += 1
    
    # 育成野手 (18人、日本人)
    positions = [
        Position.CATCHER, Position.FIRST, Position.SECOND, Position.THIRD, Position.SHORTSTOP,
        Position.LEFT, Position.CENTER, Position.RIGHT, Position.LEFT
    ]
    for _ in range(18):
        pos = random.choice(positions)
        p = create_random_player(
            pos, status=PlayerStatus.FARM, number=dev_number,
            is_foreign=False, age=random.randint(18, 25)
        )
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD
        
        if pos == Position.CATCHER:
            _add_sub_positions_catcher(p)
        elif pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            _add_sub_positions_outfielder(p)
        else:
            _add_sub_positions_infielder(p, pos)
            
        _adjust_developmental_stats(p)
        # 育成選手の年俸: 2〜10百万
        p.salary = random.randint(2, 10) * 1000000
        p.fix_main_position()
        team.players.append(p)
        dev_number += 1
    
    # ==============================
    # 育成外国人選手 (0〜5人、18〜25歳)
    # ==============================
    num_foreign_dev = random.randint(0, 5)
    for _ in range(num_foreign_dev):
        pos = random.choice(foreign_positions)
        pitch_type = None
        if pos == Position.PITCHER:
            pitch_type = random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER])
        
        p = create_random_player(
            pos, pitch_type, PlayerStatus.FARM, dev_number,
            is_foreign=True, age=random.randint(18, 25)
        )
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD
        
        if pos == Position.PITCHER:
            _add_sub_positions_pitcher(p)
        elif pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            _add_sub_positions_outfielder(p)
        else:
            _add_sub_positions_infielder(p, pos)
            
        _adjust_developmental_stats(p)
        # 育成外国人の年俸: 2〜10百万
        p.salary = random.randint(2, 10) * 1000000
        p.fix_main_position()
        team.players.append(p)
        dev_number += 1
    
    # ==============================
    # チームの年俸調整: ファン数に応じた倍率を適用
    # 477万ファン(阪神級) = 1.3倍 → 約80億円
    # 350万ファン(巨人級) = 1.15倍 → 約65億円
    # 200万ファン(中位) = 1.0倍 → 約50億円
    # 142万ファン(ヤクルト級) = 0.7倍 → 約35億円
    # ==============================
    total_fans = fan_base.total_fans
    if total_fans >= 4000000:
        salary_mult = 1.3
    elif total_fans >= 3000000:
        salary_mult = 1.0 + (total_fans - 3000000) / 3333333  # 3M→1.0, 4M→1.3
    elif total_fans >= 2000000:
        salary_mult = 0.85 + (total_fans - 2000000) / 6666667  # 2M→0.85, 3M→1.0
    elif total_fans >= 1500000:
        salary_mult = 0.7 + (total_fans - 1500000) / 3333333  # 1.5M→0.7, 2M→0.85
    else:
        salary_mult = 0.6 + total_fans / 2500000 * 0.1  # 0→0.6, 1.5M→0.66
    
    # 全選手の年俸に倍率を適用
    for p in team.players:
        if hasattr(p, 'salary') and p.salary:
            p.salary = int(p.salary * salary_mult)
            p.salary = max(2400000, min(1500000000, p.salary))  # 再クランプ
    
    return team


def _add_sub_positions_pitcher(player):
    pass


def _add_sub_positions_catcher(player):
    if random.random() < 0.3:
        player.add_sub_position(Position.FIRST, random.uniform(0.5, 0.7))
    if random.random() < 0.1:
        player.add_sub_position(Position.THIRD, random.uniform(0.4, 0.6))


def _add_sub_positions_infielder(player, main_pos: Position):
    if main_pos == Position.SECOND:
        if random.random() < 0.6:
            player.add_sub_position(Position.SHORTSTOP, random.uniform(0.6, 0.85))
        if random.random() < 0.3:
            player.add_sub_position(Position.THIRD, random.uniform(0.5, 0.7))
    elif main_pos == Position.SHORTSTOP:
        if random.random() < 0.6:
            player.add_sub_position(Position.SECOND, random.uniform(0.6, 0.85))
        if random.random() < 0.5:
            player.add_sub_position(Position.THIRD, random.uniform(0.6, 0.8))
    elif main_pos == Position.THIRD:
        if random.random() < 0.4:
            player.add_sub_position(Position.FIRST, random.uniform(0.6, 0.8))
        if random.random() < 0.3:
            player.add_sub_position(Position.SHORTSTOP, random.uniform(0.5, 0.7))
    elif main_pos == Position.FIRST:
        if random.random() < 0.2:
            player.add_sub_position(Position.THIRD, random.uniform(0.5, 0.7))
        # 修正: OUTFIELD -> LEFT/RIGHT
        if random.random() < 0.2:
            sub_of = random.choice([Position.LEFT, Position.RIGHT])
            player.add_sub_position(sub_of, random.uniform(0.5, 0.7))


def _add_sub_positions_outfielder(player):
    """外野手のサブポジション（外野内での融通）"""
    main_pos = player.position
    
    # センターは両翼も守れる確率が高い
    if main_pos == Position.CENTER:
        player.add_sub_position(Position.LEFT, random.uniform(0.8, 0.95))
        player.add_sub_position(Position.RIGHT, random.uniform(0.8, 0.95))
    # レフトはライト、ライトはレフトを守れる
    elif main_pos == Position.LEFT:
        player.add_sub_position(Position.RIGHT, random.uniform(0.7, 0.9))
        if random.random() < 0.3: # センターは足が必要なので確率低め
            player.add_sub_position(Position.CENTER, random.uniform(0.5, 0.7))
    elif main_pos == Position.RIGHT:
        player.add_sub_position(Position.LEFT, random.uniform(0.7, 0.9))
        if random.random() < 0.3:
            player.add_sub_position(Position.CENTER, random.uniform(0.5, 0.7))

    # 一塁や三塁を守れる選手もいる
    if random.random() < 0.25:
        player.add_sub_position(Position.FIRST, random.uniform(0.5, 0.75))
    if random.random() < 0.1:
        player.add_sub_position(Position.THIRD, random.uniform(0.4, 0.6))


def _adjust_developmental_stats(player):
    """育成選手の能力調整"""
    stats = player.stats
    factor = random.uniform(0.7, 0.9)
    
    stats.contact = max(1, int(stats.contact * factor))
    stats.gap = max(1, int(stats.gap * factor))
    stats.power = max(1, int(stats.power * factor))
    stats.eye = max(1, int(stats.eye * factor))
    stats.avoid_k = max(1, int(stats.avoid_k * factor))
    
    stats.speed = max(1, int(stats.speed * factor))
    stats.steal = max(1, int(stats.steal * factor))
    stats.baserunning = max(1, int(stats.baserunning * factor))
    
    stats.arm = max(1, int(stats.arm * factor))
    stats.error = max(1, int(stats.error * factor))
    stats.catcher_lead = max(1, int(stats.catcher_lead * factor))
    stats.turn_dp = max(1, int(stats.turn_dp * factor))

    for pos_key in stats.defense_ranges:
        original = stats.defense_ranges[pos_key]
        stats.defense_ranges[pos_key] = max(1, int(original * factor))
    
    if player.position == Position.PITCHER:
        stats.velocity = max(120, int(stats.velocity * 0.95))
        stats.stuff = max(1, int(stats.stuff * factor))
        stats.movement = max(1, int(stats.movement * factor))
        stats.control = max(1, int(stats.control * factor))
        stats.stamina = max(1, int(stats.stamina * factor))


def load_or_create_teams(north_team_names: list, south_team_names: list) -> tuple:
    """
    チームデータを読み込みまたは新規生成
    
    Priority:
    1. team_dataディレクトリの既存ファイルからチームを読み込む (編集されたチーム名も対応)
    2. 不足分のみ新規生成
    """
    from player_data_manager import player_data_manager
    from team_data_manager import team_data_manager
    import os
    import json
    
    north_teams = []
    south_teams = []
    
    # team_dataディレクトリから既存チームを読み込む
    team_data_dir = team_data_manager.DATA_DIR
    existing_teams = {}
    
    # Get league info from TEAM_CONFIGS for fallback
    from team_data_manager import TEAM_CONFIGS
    south_team_default = set(south_team_names)
    
    if os.path.exists(team_data_dir):
        for filename in os.listdir(team_data_dir):
            if filename.endswith("_team.json"):
                team_filepath = os.path.join(team_data_dir, filename)
                try:
                    with open(team_filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # ファイル内の球団名を使用（編集後の名前）
                    team_name = data.get("球団名", filename.replace("_team.json", "").replace("_", " "))
                    
                    # リーグを決定: ファイル内 → TEAM_CONFIGS → ファイル名から推測
                    league = data.get("リーグ")
                    if not league:
                        # ファイル名からオリジナル名を取得
                        file_base_name = filename.replace("_team.json", "").replace("_", " ")
                        # TEAM_CONFIGSから検索
                        if file_base_name in south_team_default:
                            league = "South League"
                        else:
                            league = "North League"
                    
                    # ファイルから直接チームを作成
                    team = team_data_manager.dict_to_team(data)
                    
                    # 計算したリーグを設定（ファイルにリーグ情報がない場合の対応）
                    if team:
                        league_enum = League.SOUTH if "South" in league else League.NORTH
                        team.league = league_enum
                        # 選手データを読み込み - ファイル名ベースで探す
                        # (ファイルはリネームされているので、チーム名からパスを生成)
                        player_filepath = player_data_manager._get_team_filepath(team_name)
                        
                        # ファイル名ベースでも試す
                        if not os.path.exists(player_filepath):
                            file_based_name = filename.replace("_team.json", "").replace("_", " ")
                            player_filepath = player_data_manager._get_team_filepath(file_based_name)
                        
                        if os.path.exists(player_filepath):
                            with open(player_filepath, 'r', encoding='utf-8') as f:
                                player_data = json.load(f)
                            player_data_manager.load_players_to_team(team, player_data)
                            existing_teams[team_name] = (team, league)
                            print(f"  チームデータを読み込みました: {team_name}")
                        else:
                            # 選手データがなければ新規生成
                            print(f"  選手データがありません、新規生成: {team_name}")
                            league_enum = League.NORTH if "North" in league else League.SOUTH
                            team = create_team(team_name, league_enum)
                            player_data_manager.save_team(team)
                            existing_teams[team_name] = (team, league)
                except Exception as e:
                    print(f"  チームデータ読み込みエラー: {filename} - {e}")
                    import traceback
                    traceback.print_exc()
    
    # 既存チームをリーグ別に振り分け
    for team_name, (team, league) in existing_teams.items():
        if "North" in league:
            north_teams.append(team)
        else:
            south_teams.append(team)
    
    # 12チーム揃っていれば完了（チーム名に関係なく）
    if len(north_teams) >= 6 and len(south_teams) >= 6:
        print(f"既存のチームデータを使用します (North: {len(north_teams)}, South: {len(south_teams)})")
        return north_teams[:6], south_teams[:6]
    
    # 不足分を新規生成 (チーム数が足りない場合のみ)
    print(f"チーム不足のため新規生成 (North: {len(north_teams)}/6, South: {len(south_teams)}/6)")
    
    # 既存のファイル名も除外リストに追加（リネームされていないファイルの重複防止）
    existing_file_names = set()
    if os.path.exists(team_data_dir):
        for filename in os.listdir(team_data_dir):
            if filename.endswith("_team.json"):
                existing_file_names.add(filename.replace("_team.json", "").replace("_", " "))
    
    for team_name in north_team_names:
        if len(north_teams) >= 6:
            break
        # 既存のファイル名とも一致しない場合のみ生成
        if team_name not in existing_file_names:
            print(f"  新規チーム生成: {team_name}")
            team = create_team(team_name, League.NORTH)
            north_teams.append(team)
            team_data_manager.save_team(team)
            player_data_manager.save_team(team)
    
    for team_name in south_team_names:
        if len(south_teams) >= 6:
            break
        # 既存のファイル名とも一致しない場合のみ生成
        if team_name not in existing_file_names:
            print(f"  新規チーム生成: {team_name}")
            team = create_team(team_name, League.SOUTH)
            south_teams.append(team)
            team_data_manager.save_team(team)
            player_data_manager.save_team(team)
    
    return north_teams, south_teams