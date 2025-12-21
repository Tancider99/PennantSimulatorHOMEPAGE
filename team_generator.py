# -*- coding: utf-8 -*-
"""
チーム生成ユーティリティ (修正版: 外野3ポジション対応)
固定選手データがある場合は読み込み、なければ新規生成
"""
from models import Team, Position, PitchType, PlayerStatus, League, TeamLevel
from player_generator import create_random_player
import random


def create_team(team_name: str, league: League) -> Team:
    """チームを生成（支配下67〜70人＋育成30〜35人）"""
    team = Team(name=team_name, league=league)
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
    from player_data_manager import player_data_manager
    all_team_names = north_team_names + south_team_names
    
    if player_data_manager.has_all_team_data(all_team_names):
        north_teams = []
        south_teams = []
        for team_name in north_team_names:
            team = player_data_manager.load_team(team_name)
            if team: north_teams.append(team)
        for team_name in south_team_names:
            team = player_data_manager.load_team(team_name)
            if team: south_teams.append(team)
        if len(north_teams) == len(north_team_names) and len(south_teams) == len(south_team_names):
            print("固定選手データを使用します（球団別ファイル）")
            return north_teams, south_teams
        
    print("新規選手データを生成します")
    north_teams = []
    south_teams = []
    
    for team_name in north_team_names:
        team = create_team(team_name, League.NORTH)
        north_teams.append(team)
        player_data_manager.save_team(team)
    
    for team_name in south_team_names:
        team = create_team(team_name, League.SOUTH)
        south_teams.append(team)
        player_data_manager.save_team(team)
    
    return north_teams, south_teams