# -*- coding: utf-8 -*-
"""
チーム生成ユーティリティ
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
    # ==============================
    # 投手 (28人)
    for _ in range(8):
        p = create_random_player(Position.PITCHER, PitchType.STARTER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        # 一軍/二軍の振り分け
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(14):
        p = create_random_player(Position.PITCHER, PitchType.RELIEVER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(6):
        p = create_random_player(Position.PITCHER, PitchType.CLOSER, PlayerStatus.ACTIVE, number)
        p.is_developmental = False
        _add_sub_positions_pitcher(p)
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    
    # 野手 (42人)
    for _ in range(4):
        p = create_random_player(Position.CATCHER, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_catcher(p)
        p.fix_main_position() # 守備範囲再チェック
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(5):
        p = create_random_player(Position.FIRST, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_infielder(p, Position.FIRST)
        p.fix_main_position() # 守備範囲再チェック
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(6):
        p = create_random_player(Position.SECOND, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_infielder(p, Position.SECOND)
        p.fix_main_position() # 守備範囲再チェック
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(5):
        p = create_random_player(Position.THIRD, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_infielder(p, Position.THIRD)
        p.fix_main_position() # 守備範囲再チェック
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(6):
        p = create_random_player(Position.SHORTSTOP, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_infielder(p, Position.SHORTSTOP)
        p.fix_main_position() # 守備範囲再チェック
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    for _ in range(16):
        p = create_random_player(Position.OUTFIELD, status=PlayerStatus.ACTIVE, number=number)
        p.is_developmental = False
        _add_sub_positions_outfielder(p)
        p.fix_main_position() # 守備範囲再チェック
        p.team_level = TeamLevel.FIRST if player_count < first_team_limit else TeamLevel.SECOND
        player_count += 1
        team.players.append(p)
        number += 1
    
    # ==============================
    # 育成選手 (30人) - 背番号は3桁
    # ==============================
    dev_number = 101
    
    # 育成投手 (12人)
    for _ in range(12):
        p = create_random_player(
            Position.PITCHER, 
            random.choice(list(PitchType)), 
            PlayerStatus.FARM, 
            dev_number
        )
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD  # 育成選手は三軍
        _add_sub_positions_pitcher(p)
        # 育成選手は能力を少し下げる
        _adjust_developmental_stats(p)
        team.players.append(p)
        dev_number += 1
    
    # 育成野手 (18人)
    positions = [Position.CATCHER, Position.FIRST, Position.SECOND, Position.THIRD, 
                Position.SHORTSTOP, Position.OUTFIELD, Position.OUTFIELD, Position.OUTFIELD]
    for _ in range(18):
        pos = random.choice(positions)
        p = create_random_player(pos, status=PlayerStatus.FARM, number=dev_number)
        p.is_developmental = True
        p.team_level = TeamLevel.THIRD  # 育成選手は三軍
        if pos == Position.CATCHER:
            _add_sub_positions_catcher(p)
        elif pos == Position.OUTFIELD:
            _add_sub_positions_outfielder(p)
        else:
            _add_sub_positions_infielder(p, pos)
        _adjust_developmental_stats(p)
        
        # 最後に守備範囲再チェック
        p.fix_main_position()
        
        team.players.append(p)
        dev_number += 1
    
    return team


def _add_sub_positions_pitcher(player):
    """投手のサブポジション（基本なし）"""
    pass


def _add_sub_positions_catcher(player):
    """捕手のサブポジション"""
    if random.random() < 0.3:
        player.add_sub_position(Position.FIRST, random.uniform(0.5, 0.7))
    if random.random() < 0.1:
        player.add_sub_position(Position.THIRD, random.uniform(0.4, 0.6))


def _add_sub_positions_infielder(player, main_pos: Position):
    """内野手のサブポジション"""
    # 二遊間はお互い守りやすい
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
        if random.random() < 0.2:
            player.add_sub_position(Position.OUTFIELD, random.uniform(0.5, 0.7))


def _add_sub_positions_outfielder(player):
    """外野手のサブポジション"""
    # 外野手は外野全ポジション可能（外野手同士のサブポジは不要、同一ポジション扱い）
    # 一塁や三塁を守れる選手もいる
    if random.random() < 0.25:
        player.add_sub_position(Position.FIRST, random.uniform(0.5, 0.75))
    if random.random() < 0.1:
        player.add_sub_position(Position.THIRD, random.uniform(0.4, 0.6))


def _adjust_developmental_stats(player):
    """育成選手の能力調整（やや低め）- OOTP Stats対応"""
    stats = player.stats
    factor = random.uniform(0.7, 0.9)
    
    # 打撃
    stats.contact = max(1, int(stats.contact * factor))
    stats.gap = max(1, int(stats.gap * factor))
    stats.power = max(1, int(stats.power * factor))
    stats.eye = max(1, int(stats.eye * factor))
    stats.avoid_k = max(1, int(stats.avoid_k * factor))
    
    # 走塁
    stats.speed = max(1, int(stats.speed * factor))
    stats.steal = max(1, int(stats.steal * factor))
    stats.baserunning = max(1, int(stats.baserunning * factor))
    
    # 守備 (統合された項目)
    stats.arm = max(1, int(stats.arm * factor))
    stats.error = max(1, int(stats.error * factor))
    stats.catcher_lead = max(1, int(stats.catcher_lead * factor))
    stats.turn_dp = max(1, int(stats.turn_dp * factor))

    # 守備範囲 (保持している全ポジションを調整)
    for pos_key in stats.defense_ranges:
        original = stats.defense_ranges[pos_key]
        stats.defense_ranges[pos_key] = max(1, int(original * factor))
    
    # 投手
    if player.position == Position.PITCHER:
        # 球速は少し落とす (例: 145km/h -> 138km/h)
        stats.velocity = max(120, int(stats.velocity * 0.95))
        
        stats.stuff = max(1, int(stats.stuff * factor))
        stats.movement = max(1, int(stats.movement * factor))
        stats.control = max(1, int(stats.control * factor))
        stats.stamina = max(1, int(stats.stamina * factor))


def load_or_create_teams(north_team_names: list, south_team_names: list) -> tuple:
    """固定選手データを読み込み、なければ新規生成して保存（球団別ファイル）"""
    from player_data_manager import player_data_manager
    
    all_team_names = north_team_names + south_team_names
    
    # 全球団のデータがあれば読み込み
    if player_data_manager.has_all_team_data(all_team_names):
        north_teams = []
        south_teams = []
        
        for team_name in north_team_names:
            team = player_data_manager.load_team(team_name)
            if team:
                north_teams.append(team)
        
        for team_name in south_team_names:
            team = player_data_manager.load_team(team_name)
            if team:
                south_teams.append(team)
        
            # 全チームが正しく読み込めたか確認
            if len(north_teams) == len(north_team_names) and len(south_teams) == len(south_team_names):
                print("固定選手データを使用します（球団別ファイル）")
                return north_teams, south_teams
        
        # 新規生成
        print("新規選手データを生成します")
        north_teams = []
        south_teams = []
        
        for team_name in north_team_names:
            team = create_team(team_name, League.NORTH)
            north_teams.append(team)
            player_data_manager.save_team(team)  # 個別保存
        
        for team_name in south_team_names:
            team = create_team(team_name, League.SOUTH)
            south_teams.append(team)
            player_data_manager.save_team(team)  # 個別保存
        
        return north_teams, south_teams
    
    
    def regenerate_and_save_teams(north_team_names: list, south_team_names: list) -> tuple:
        """選手データを新規生成して保存（既存データを上書き・球団別ファイル）"""
        from player_data_manager import player_data_manager
        
        print("選手データを再生成します")
        north_teams = []
        south_teams = []
        
        for team_name in north_team_names:
            team = create_team(team_name, League.NORTH)
            north_teams.append(team)
            player_data_manager.save_team(team)  # 個別保存
        
        for team_name in south_team_names:
            team = create_team(team_name, League.SOUTH)
            south_teams.append(team)
            player_data_manager.save_team(team)  # 個別保存
        
        return north_teams, south_teams