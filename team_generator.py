# -*- coding: utf-8 -*-
"""
チーム生成ユーティリティ (修正版: 外野3ポジション対応)
固定選手データがある場合は読み込み、なければ新規生成
"""
from models import Team, Position, PitchType, PlayerStatus, League, TeamLevel
from player_generator import create_random_player
import random


def create_team(team_name: str, league: League) -> Team:
    """チームを生成（支配下70人＋育成30人）"""
    team = Team(name=team_name, league=league)
    number = 1
    player_count = 0  # 支配下選手のカウント
    first_team_limit = 31  # 一軍上限
    
    # ==============================
    # 支配下選手 (70人)
    # 1軍枠配分: 投手15人 / 野手16人
    # ==============================
    
    # 投手 (28人) - 5:4:1 比率 (14:11:3)
    for _ in range(14):
        p = create_random_player(Position.PITCHER, PitchType.STARTER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        p.team_level = TeamLevel.SECOND # Default to Farm
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(11):
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
    
    # 野手 (42人)
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
    
    # 内野手 (22)
    for pos, count in [(Position.FIRST, 5), (Position.SECOND, 6), (Position.THIRD, 5), (Position.SHORTSTOP, 6)]:
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
    # 育成選手 (30人) - 背番号は3桁
    # ==============================
    dev_number = 101
    
    # 育成投手 (12人)
    for _ in range(12):
        p = create_random_player(
            Position.PITCHER, 
            None, # 自動決定（5:4:1）
            PlayerStatus.FARM, 
            dev_number
        )
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD
        _add_sub_positions_pitcher(p)
        _adjust_developmental_stats(p)
        team.players.append(p)
        dev_number += 1
    
    # 育成野手 (18人)
    # ポジションリストを修正 (OUTFIELD -> LEFT, CENTER, RIGHT)
    positions = [
        Position.CATCHER, Position.FIRST, Position.SECOND, Position.THIRD, Position.SHORTSTOP,
        Position.LEFT, Position.CENTER, Position.RIGHT, Position.LEFT
    ]
    for _ in range(18):
        pos = random.choice(positions)
        p = create_random_player(pos, status=PlayerStatus.FARM, number=dev_number)
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD
        
        if pos == Position.CATCHER:
            _add_sub_positions_catcher(p)
        elif pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
            _add_sub_positions_outfielder(p)
        else:
            _add_sub_positions_infielder(p, pos)
            
        _adjust_developmental_stats(p)
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