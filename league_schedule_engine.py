# -*- coding: utf-8 -*-
"""
日程作成エンジン（NPB完全準拠版）
- 一軍143試合（3連戦カード制）、二軍120試合、三軍100試合
- リーグ戦は同一リーグのみ対戦
- 交流戦（6月）は他リーグのみ対戦 + 予備日3日
- オールスター（7月下旬）本格実装
- 天候システム（雨天中止・コールド）
- 延期試合の振替
- ポストシーズン（CS・日本シリーズ）本格実装
"""
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
import datetime
from enum import Enum
from models import Team, League, Schedule, ScheduledGame, GameStatus, TeamLevel, Player, Position


class WeatherCondition(Enum):
    CLEAR = "晴れ"
    CLOUDY = "曇り"
    LIGHT_RAIN = "小雨"
    RAIN = "雨"
    HEAVY_RAIN = "大雨"


class GameCancellationReason(Enum):
    NONE = ""
    RAIN = "雨天中止"
    RAIN_COLD = "雨天コールド"


@dataclass
class SeriesCard:
    """3連戦カード"""
    home_team: str
    away_team: str
    games: int = 3  # 通常3試合
    is_interleague: bool = False


@dataclass
class SeasonCalendar:
    """シーズンカレンダー設定"""
    year: int
    opening_day: datetime.date
    interleague_start: datetime.date
    interleague_end: datetime.date
    interleague_reserve_end: datetime.date
    allstar_day1: datetime.date
    allstar_day2: datetime.date
    regular_season_end: datetime.date
    max_season_end: datetime.date
    cs_first_start: datetime.date
    cs_final_start: datetime.date
    japan_series_start: datetime.date

    @classmethod
    def create(cls, year: int) -> 'SeasonCalendar':
        """NPB準拠のカレンダーを生成"""
        # 開幕日: 3月最終週の金曜日（月曜日を避ける）
        base_opening = datetime.date(year, 3, 29)
        # 金曜日(weekday=4)になるよう調整
        days_until_friday = (4 - base_opening.weekday()) % 7
        if days_until_friday == 0 and base_opening.weekday() != 4:
            days_until_friday = 7  # すでに過ぎている場合は次週
        opening_day = datetime.date(year, 3, 25) + datetime.timedelta(days=(4 - datetime.date(year, 3, 25).weekday()) % 7)
        
        # 交流戦開始は火曜日に設定（5月最終週の火曜日）
        il_start_base = datetime.date(year, 5, 27)
        # 火曜日(weekday=1)になるよう調整
        days_until_tuesday = (1 - il_start_base.weekday()) % 7
        interleague_start = il_start_base + datetime.timedelta(days=days_until_tuesday)

        # 交流戦構造: 火-日(6日) + 月休 + 火-日(6日) + 月休 + 火-日(6日) = 20日間
        # その後、予備日4日間
        interleague_end = interleague_start + datetime.timedelta(days=19)  # 20日目（3週目の日曜）
        interleague_reserve_end = interleague_end + datetime.timedelta(days=4)  # 予備日4日間

        return cls(
            year=year,
            opening_day=opening_day,
            interleague_start=interleague_start,  # 火曜日開始
            interleague_end=interleague_end,  # 3週目の日曜日
            interleague_reserve_end=interleague_reserve_end,  # 予備日終了
            allstar_day1=datetime.date(year, 7, 23),
            allstar_day2=datetime.date(year, 7, 24),
            regular_season_end=datetime.date(year, 9, 28),
            max_season_end=datetime.date(year, 10, 7),
            cs_first_start=datetime.date(year, 10, 12),
            cs_final_start=datetime.date(year, 10, 16),
            japan_series_start=datetime.date(year, 10, 26),
        )


class WeatherSystem:
    """天候シミュレーションシステム"""

    # 雨天確率を現実的な値に調整（NPBの実際の中止率は年間5-10試合程度）
    MONTHLY_RAIN_PROBABILITY = {
        3: 0.15, 4: 0.18, 5: 0.20, 6: 0.30,  # 梅雨時期でも控えめに
        7: 0.20, 8: 0.15, 9: 0.20, 10: 0.15,
    }

    @classmethod
    def get_weather(cls, date: datetime.date) -> WeatherCondition:
        rain_prob = cls.MONTHLY_RAIN_PROBABILITY.get(date.month, 0.15)
        roll = random.random()
        if roll < rain_prob * 0.2:  # 大雨は稀（雨の20%）
            return WeatherCondition.HEAVY_RAIN
        elif roll < rain_prob * 0.5:  # 雨（雨の30%）
            return WeatherCondition.RAIN
        elif roll < rain_prob:  # 小雨（雨の50%）
            return WeatherCondition.LIGHT_RAIN
        elif roll < rain_prob + 0.25:
            return WeatherCondition.CLOUDY
        return WeatherCondition.CLEAR

    @classmethod
    def should_cancel_game(cls, weather: WeatherCondition) -> bool:
        """試合中止判定（ドーム球場を考慮して確率を下げる）"""
        if weather == WeatherCondition.HEAVY_RAIN:
            return random.random() < 0.6  # 大雨でも40%はドームで開催
        elif weather == WeatherCondition.RAIN:
            return random.random() < 0.3  # 雨でも70%は開催
        elif weather == WeatherCondition.LIGHT_RAIN:
            return random.random() < 0.05  # 小雨はほぼ開催
        return False

    @classmethod
    def should_call_game(cls, weather: WeatherCondition, inning: int) -> bool:
        """試合途中のコールド判定"""
        if inning < 5:
            return False
        if weather == WeatherCondition.HEAVY_RAIN:
            return random.random() < 0.5
        elif weather == WeatherCondition.RAIN:
            return random.random() < 0.2
        return False


class LeagueScheduleEngine:
    """NPB準拠リーグ日程作成エンジン（3連戦カード制）"""

    GAMES_PER_SEASON = 143
    LEAGUE_GAMES_PER_OPPONENT = 25  # 同一リーグ: 5チーム × 25試合 = 125試合
    INTERLEAGUE_GAMES_PER_OPPONENT = 3  # 交流戦: 6チーム × 3試合 = 18試合

    def __init__(self, year: int = 2027):
        self.year = year
        self.calendar = SeasonCalendar.create(year)
        self.schedule = Schedule()
        self.north_teams: List[str] = []
        self.south_teams: List[str] = []
        self.all_teams: List[str] = []
        self.postponed_games: List[ScheduledGame] = []
        self.weather_enabled = True

    @property
    def opening_day(self) -> datetime.date:
        return self.calendar.opening_day

    def generate_schedule(self, north_teams: List[Team], south_teams: List[Team]) -> Schedule:
        """一軍日程を生成（NPB準拠・3連戦カード制）"""
        self.north_teams = [t.name for t in north_teams]
        self.south_teams = [t.name for t in south_teams]
        self.all_teams = self.north_teams + self.south_teams

        self.schedule = Schedule()
        self.postponed_games = []

        # 1. リーグ内カード（3連戦）を生成
        north_cards = self._generate_league_cards(self.north_teams)
        south_cards = self._generate_league_cards(self.south_teams)

        # 2. 交流戦カード（3連戦）を生成
        interleague_cards = self._generate_interleague_cards()

        # 3. 日程に配置
        self._assign_cards_to_calendar(north_cards, south_cards, interleague_cards)

        # 4. オールスターゲームをスケジュールに追加（初期は未定）
        # Game 1
        as_game1 = ScheduledGame(
            game_number=1,
            date=self.calendar.allstar_day1.strftime("%Y-%m-%d"),
            home_team_name="ALL-NORTH",
            away_team_name="ALL-SOUTH",
            status=GameStatus.SCHEDULED
        )
        self.schedule.games.append(as_game1)

        # Game 2
        as_game2 = ScheduledGame(
            game_number=2,
            date=self.calendar.allstar_day2.strftime("%Y-%m-%d"),
            home_team_name="ALL-SOUTH",
            away_team_name="ALL-NORTH",
            status=GameStatus.SCHEDULED
        )
        self.schedule.games.append(as_game2)
        
        # Sort by date to be safe
        self.schedule.games.sort(key=lambda x: x.date)

        return self.schedule

    def _generate_league_cards(self, teams: List[str]) -> List[SeriesCard]:
        """リーグ内3連戦カードを生成（各対戦25試合）

        各チームペア25試合の内訳:
        - 8つの3連戦カード = 24試合
        - 1つの1試合カード = 1試合
        合計: 25試合

        ホーム・アウェイ配分:
        - team1ホーム: 4カード(12試合) + 調整1試合 = 13試合 or 12試合
        - team2ホーム: 4カード(12試合) = 12試合 or 13試合
        """
        cards = []

        for i, team1 in enumerate(teams):
            for j, team2 in enumerate(teams):
                if i >= j:
                    continue

                # team1がホームの3連戦カード × 4
                for _ in range(4):
                    cards.append(SeriesCard(home_team=team1, away_team=team2, games=3))

                # team2がホームの3連戦カード × 4
                for _ in range(4):
                    cards.append(SeriesCard(home_team=team2, away_team=team1, games=3))

                # 調整用1試合（ペアのインデックスで交互にホームを決定）
                if (i + j) % 2 == 0:
                    cards.append(SeriesCard(home_team=team1, away_team=team2, games=1))
                else:
                    cards.append(SeriesCard(home_team=team2, away_team=team1, games=1))

        return cards

    def _generate_interleague_cards(self) -> List[SeriesCard]:
        """交流戦3連戦カードを生成（NPB方式: 2年1サイクルでホーム・ビジター入替）

        NPB方式:
        - 各リーグ6チームを2グループに分割（A: 0,1,2番目、B: 3,4,5番目）
        - 偶数年: 北チームはAグループ南とホーム、Bグループ南とビジター
        - 奇数年: 北チームはAグループ南とビジター、Bグループ南とホーム
        - 4年ごとにグループ組み合わせがローテーション
        """
        cards = []

        # 南リーグを2グループに分割（年によってローテーション）
        cycle = (self.year // 4) % 3  # 4年ごとにグループ変更、3パターン
        if cycle == 0:
            south_group_a = self.south_teams[0:3]  # インデックス 0,1,2
            south_group_b = self.south_teams[3:6]  # インデックス 3,4,5
        elif cycle == 1:
            south_group_a = [self.south_teams[0], self.south_teams[2], self.south_teams[4]]
            south_group_b = [self.south_teams[1], self.south_teams[3], self.south_teams[5]]
        else:
            south_group_a = [self.south_teams[0], self.south_teams[3], self.south_teams[4]]
            south_group_b = [self.south_teams[1], self.south_teams[2], self.south_teams[5]]

        # 2年1サイクルでホーム・ビジター入替
        is_even_year = self.year % 2 == 0

        for n_team in self.north_teams:
            # グループAの南チームとの対戦
            for s_team in south_group_a:
                if is_even_year:
                    # 偶数年: 北チームホーム
                    cards.append(SeriesCard(home_team=n_team, away_team=s_team, games=3, is_interleague=True))
                else:
                    # 奇数年: 南チームホーム
                    cards.append(SeriesCard(home_team=s_team, away_team=n_team, games=3, is_interleague=True))

            # グループBの南チームとの対戦
            for s_team in south_group_b:
                if is_even_year:
                    # 偶数年: 南チームホーム
                    cards.append(SeriesCard(home_team=s_team, away_team=n_team, games=3, is_interleague=True))
                else:
                    # 奇数年: 北チームホーム
                    cards.append(SeriesCard(home_team=n_team, away_team=s_team, games=3, is_interleague=True))

        return cards

    def _assign_cards_to_calendar(self, north_cards: List[SeriesCard],
                                   south_cards: List[SeriesCard],
                                   interleague_cards: List[SeriesCard]):
        """カードを日程に配置 - 日別均等配分＋連戦継続優先方式"""

        # 必要な試合数を計算
        required_games: Dict[Tuple[str, str], int] = {}

        for card in north_cards + south_cards:
            key = tuple(sorted([card.home_team, card.away_team]))
            required_games[key] = required_games.get(key, 0) + card.games

        for card in interleague_cards:
            key = tuple(sorted([card.home_team, card.away_team]))
            required_games[key] = required_games.get(key, 0) + card.games

        # 日程を分類
        pre_il_dates = []
        il_dates = []
        post_il_dates = []

        d = self.calendar.opening_day
        while d <= self.calendar.regular_season_end:
            if d.weekday() == 0:
                d += datetime.timedelta(days=1)
                continue

            allstar_rest_start = self.calendar.allstar_day1 - datetime.timedelta(days=1)
            allstar_rest_end = self.calendar.allstar_day2 + datetime.timedelta(days=1)
            if allstar_rest_start <= d <= allstar_rest_end:
                d += datetime.timedelta(days=1)
                continue

            if d < self.calendar.interleague_start:
                pre_il_dates.append(d)
            elif self.calendar.interleague_start <= d <= self.calendar.interleague_end:
                il_dates.append(d)
            elif d > self.calendar.interleague_reserve_end:
                post_il_dates.append(d)

            d += datetime.timedelta(days=1)

        all_league_dates = pre_il_dates + post_il_dates
        all_dates = pre_il_dates + il_dates + post_il_dates

        # 実施済み試合数を追跡
        scheduled_games: Dict[Tuple[str, str], int] = {key: 0 for key in required_games}

        # ホーム・アウェイのバランスを追跡
        home_games: Dict[str, Dict[str, int]] = {}
        for team in self.north_teams + self.south_teams:
            home_games[team] = {}

        # 連戦追跡（各チームが前日にどのチームと対戦したか）
        yesterday_opponent: Dict[str, Tuple[str, int]] = {}  # team -> (opponent, consecutive_days)
        # 連戦中のホームチーム追跡（3連戦中は同じ球場で開催）
        series_home: Dict[Tuple[str, str], str] = {}  # (t1, t2) sorted -> home_team

        # 交流戦グループ分け（NPB方式）
        cycle = (self.year // 4) % 3
        if cycle == 0:
            south_group_a = set(self.south_teams[0:3])
            south_group_b = set(self.south_teams[3:6])
        elif cycle == 1:
            south_group_a = {self.south_teams[0], self.south_teams[2], self.south_teams[4]}
            south_group_b = {self.south_teams[1], self.south_teams[3], self.south_teams[5]}
        else:
            south_group_a = {self.south_teams[0], self.south_teams[3], self.south_teams[4]}
            south_group_b = {self.south_teams[1], self.south_teams[2], self.south_teams[5]}

        is_even_year = self.year % 2 == 0

        def get_home_team(t1: str, t2: str, is_interleague: bool = False) -> str:
            key = tuple(sorted([t1, t2]))
            # 連戦継続中は同じホームを維持
            if key in series_home:
                return series_home[key]
            # 交流戦の場合、グループと年によってホームを決定
            if is_interleague:
                n_team = t1 if t1 in self.north_teams else t2
                s_team = t2 if t1 in self.north_teams else t1
                # グループAの南チームとの対戦
                if s_team in south_group_a:
                    return n_team if is_even_year else s_team
                # グループBの南チームとの対戦
                else:
                    return s_team if is_even_year else n_team
            # 通常はバランスで決定
            h1 = home_games.get(t1, {}).get(t2, 0)
            h2 = home_games.get(t2, {}).get(t1, 0)
            return t1 if h1 <= h2 else t2

        def add_game_for_pair(t1: str, t2: str, date: datetime.date, is_il: bool = False):
            key = tuple(sorted([t1, t2]))
            home = get_home_team(t1, t2, is_il)
            away = t2 if home == t1 else t1

            date_str = date.strftime("%Y-%m-%d")
            self.schedule.games.append(ScheduledGame(
                game_number=len(self.schedule.games) + 1,
                date=date_str,
                home_team_name=home,
                away_team_name=away
            ))

            scheduled_games[key] += 1
            if home not in home_games:
                home_games[home] = {}
            home_games[home][away] = home_games[home].get(away, 0) + 1

            # 連戦開始時にホームを記録
            if key not in series_home:
                series_home[key] = home

        def needs_more_games(t1: str, t2: str) -> bool:
            key = tuple(sorted([t1, t2]))
            return scheduled_games.get(key, 0) < required_games.get(key, 0)

        def remaining_games(t1: str, t2: str) -> int:
            key = tuple(sorted([t1, t2]))
            return required_games.get(key, 0) - scheduled_games.get(key, 0)

        def is_interleague(t1: str, t2: str) -> bool:
            return (t1 in self.north_teams) != (t2 in self.north_teams)

        # 日付ごとのチーム使用状況
        date_team_usage: Dict[str, Set[str]] = {
            d.strftime("%Y-%m-%d"): set() for d in all_dates
        }

        # === メインスケジューリング: 日別に6試合ずつ配置 ===
        def schedule_date(date: datetime.date, valid_pairs: List[Tuple[str, str]], is_interleague: bool = False):
            """指定日に最大6試合を配置（連戦継続を優先、残り試合数で確実に優先）"""
            date_str = date.strftime("%Y-%m-%d")
            teams_used: Set[str] = set()
            games_today = 0

            # 優先度でソート: (連戦継続可能, 残り試合数)
            def pair_priority(pair):
                t1, t2 = pair
                if t1 in teams_used or t2 in teams_used:
                    return (-1, -1, -1, 0)  # 使用済み

                remaining = remaining_games(t1, t2)
                if remaining <= 0:
                    return (-1, -1, -1, 0)  # 試合不要

                # 連戦継続ボーナス（前日同じ相手と対戦していて、3連戦未満なら優先）
                series_bonus = 0
                if t1 in yesterday_opponent:
                    opp, days = yesterday_opponent[t1]
                    if opp == t2 and days < 3:
                        series_bonus = 1000  # 高い優先度

                # 残り試合数が多いペアを優先（確実性のため）
                return (series_bonus, remaining, -hash((t1, t2)) % 1000, 0)

            # 6試合分を配置
            while games_today < 6:
                # 利用可能なペアを優先度順に取得
                available = [(p, pair_priority(p)) for p in valid_pairs
                             if p[0] not in teams_used and p[1] not in teams_used]
                available = [(p, pri) for p, pri in available if pri[0] >= 0]

                if not available:
                    break

                available.sort(key=lambda x: x[1], reverse=True)
                best_pair, _ = available[0]
                t1, t2 = best_pair

                if not needs_more_games(t1, t2):
                    # このペアはもう試合不要、次を探す
                    valid_pairs = [p for p in valid_pairs if p != best_pair]
                    continue

                add_game_for_pair(t1, t2, date, is_interleague)
                teams_used.add(t1)
                teams_used.add(t2)
                date_team_usage[date_str].add(t1)
                date_team_usage[date_str].add(t2)
                games_today += 1

            return teams_used

        # リーグ戦ペア
        north_pairs = [(self.north_teams[i], self.north_teams[j])
                       for i in range(len(self.north_teams))
                       for j in range(i + 1, len(self.north_teams))]
        south_pairs = [(self.south_teams[i], self.south_teams[j])
                       for i in range(len(self.south_teams))
                       for j in range(i + 1, len(self.south_teams))]
        league_pairs = north_pairs + south_pairs

        # 交流戦ペア
        il_pairs = [(n, s) for n in self.north_teams for s in self.south_teams]

        # === 交流戦を先にスケジュール（ラウンドロビン方式）===
        # 構造: 3週間 × 6日/週 = 18日
        # 各週で各チームは2つのシリーズ（3連戦×2）をプレイ
        # 36ペア × 3試合 = 108試合
        il_dates_sorted = sorted(il_dates)

        # 週ごとに分割（月曜を除いた6日ブロック）
        weeks = []
        current_week = []
        for date in il_dates_sorted:
            if date.weekday() == 0:  # 月曜はスキップ
                continue
            current_week.append(date)
            if len(current_week) == 6:
                weeks.append(current_week)
                current_week = []
        if current_week:  # 残りがあれば追加
            weeks.append(current_week)

        # 各北チームと南チームの対戦スケジュールを作成
        # 各週で各チームは2チームと3連戦（計6試合）
        # 3週間で6チームと1回ずつ対戦（計18試合）

        # ラウンドロビン: 各週でどの北チームがどの南チームと対戦するか決定
        # Week 1: North[i] vs South[i], South[(i+1)%6]
        # Week 2: North[i] vs South[(i+2)%6], South[(i+3)%6]
        # Week 3: North[i] vs South[(i+4)%6], South[(i+5)%6]
        week_matchups = []
        for week_idx in range(3):
            matchups = []  # (north_idx, south_idx) のリスト
            for n_idx in range(6):
                # 各週で2つの南チームと対戦
                s_idx1 = (n_idx + week_idx * 2) % 6
                s_idx2 = (n_idx + week_idx * 2 + 1) % 6
                matchups.append((n_idx, s_idx1))
                matchups.append((n_idx, s_idx2))
            week_matchups.append(matchups)

        # 週ごとにスケジュール
        for week_idx, week_dates in enumerate(weeks):
            if week_idx >= 3:
                break  # 3週間分のみ

            matchups = week_matchups[week_idx]

            # この週の各日の対戦を決定
            # 3日目までと4日目以降で異なるシリーズを配置

            # 前半3日（シリーズA）: 各北チームの1つ目の対戦
            series_a = [(n_idx, s_idx) for n_idx, s_idx in matchups[::2]]  # 偶数インデックス
            # 後半3日（シリーズB）: 各北チームの2つ目の対戦
            series_b = [(n_idx, s_idx) for n_idx, s_idx in matchups[1::2]]  # 奇数インデックス

            for day_offset, date in enumerate(week_dates):
                date_str = date.strftime("%Y-%m-%d")

                # 前半3日か後半3日かでシリーズを選択
                if day_offset < 3:
                    day_series = series_a
                else:
                    day_series = series_b

                for n_idx, s_idx in day_series:
                    n_team = self.north_teams[n_idx]
                    s_team = self.south_teams[s_idx]

                    add_game_for_pair(n_team, s_team, date, True)
                    date_team_usage[date_str].add(n_team)
                    date_team_usage[date_str].add(s_team)

        # === リーグ戦を日付順に処理 ===
        prev_date = None
        for date in sorted(all_league_dates):
            # 前日からの連戦情報を更新
            if prev_date is not None:
                day_gap = (date - prev_date).days
                if day_gap <= 2:  # 月曜スキップ考慮
                    # 連戦を継続
                    new_yesterday = {}
                    pairs_to_clear = []  # 3連戦終了したペア
                    for game in self.schedule.games:
                        if game.date == prev_date.strftime("%Y-%m-%d"):
                            t1, t2 = game.home_team_name, game.away_team_name
                            key = tuple(sorted([t1, t2]))
                            prev_days_1 = yesterday_opponent.get(t1, (None, 0))[1] if yesterday_opponent.get(t1, (None, 0))[0] == t2 else 0
                            prev_days_2 = yesterday_opponent.get(t2, (None, 0))[1] if yesterday_opponent.get(t2, (None, 0))[0] == t1 else 0
                            new_days = prev_days_1 + 1
                            new_yesterday[t1] = (t2, new_days)
                            new_yesterday[t2] = (t1, new_days)
                            # 3連戦終了したらseries_homeをクリア
                            if new_days >= 3:
                                pairs_to_clear.append(key)
                    yesterday_opponent.clear()
                    yesterday_opponent.update(new_yesterday)
                    for key in pairs_to_clear:
                        series_home.pop(key, None)
                else:
                    # 日程が離れたら全連戦リセット
                    yesterday_opponent.clear()
                    series_home.clear()

            schedule_date(date, league_pairs.copy(), False)
            prev_date = date

        # === 補完パス: 不足分を埋める（最大30パス）===
        for pass_num in range(30):
            any_added = False
            total_remaining = sum(remaining_games(p[0], p[1]) for p in league_pairs + il_pairs)

            if total_remaining == 0:
                break

            for date in sorted(all_dates):
                date_str = date.strftime("%Y-%m-%d")
                teams_used = date_team_usage[date_str].copy()

                if len(teams_used) >= 12:
                    continue

                # 交流戦期間かどうかで使用するペアを決定
                is_il = self.calendar.interleague_start <= date <= self.calendar.interleague_end
                if is_il:
                    valid_pairs = il_pairs
                else:
                    valid_pairs = league_pairs

                # 残り試合数が多いペアを優先
                pairs_with_need = []
                for pair in valid_pairs:
                    t1, t2 = pair
                    if t1 in teams_used or t2 in teams_used:
                        continue
                    rem = remaining_games(t1, t2)
                    if rem > 0:
                        pairs_with_need.append((rem, pair))

                if not pairs_with_need:
                    continue

                pairs_with_need.sort(reverse=True)

                for _, pair in pairs_with_need:
                    if len(teams_used) >= 12:
                        break
                    t1, t2 = pair
                    if t1 in teams_used or t2 in teams_used:
                        continue

                    add_game_for_pair(t1, t2, date, is_il)
                    date_team_usage[date_str].add(t1)
                    date_team_usage[date_str].add(t2)
                    teams_used.add(t1)
                    teams_used.add(t2)
                    any_added = True

            if not any_added:
                break

        # ソートして番号振り直し
        self.schedule.games.sort(key=lambda g: (g.date, g.game_number))
        for i, game in enumerate(self.schedule.games):
            game.game_number = i + 1

    # ========================================
    # 天候・振替システム
    # ========================================

    def process_weather_for_date(self, date_str: str) -> List[ScheduledGame]:
        if not self.weather_enabled:
            return []

        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return []

        cancelled_games = []
        weather = WeatherSystem.get_weather(date)

        games_today = [g for g in self.schedule.games if g.date == date_str and g.status == GameStatus.SCHEDULED]

        for game in games_today:
            if WeatherSystem.should_cancel_game(weather):
                game.status = GameStatus.CANCELLED
                self.postponed_games.append(game)
                cancelled_games.append(game)

        return cancelled_games

    def reschedule_postponed_games(self) -> List[Tuple[ScheduledGame, str]]:
        rescheduled = []

        for game in self.postponed_games[:]:
            new_date = self._find_makeup_date(game)
            if new_date:
                game.status = GameStatus.SCHEDULED
                old_date = game.date
                game.date = new_date.strftime("%Y-%m-%d")
                self.postponed_games.remove(game)
                rescheduled.append((game, old_date))

        return rescheduled

    def _find_makeup_date(self, game: ScheduledGame) -> Optional[datetime.date]:
        """延期試合の振替日を探す

        ルール:
        - 交流戦: 交流戦予備日（interleague_end + 1 ～ interleague_reserve_end）に振替
        - リーグ戦: 元の日付以降の9月～で空きを探す
        - 元の日付より前には振替しない
        """
        try:
            original_date = datetime.datetime.strptime(game.date, "%Y-%m-%d").date()
        except:
            return None

        # 交流戦かどうか判定
        is_interleague = (game.home_team_name in self.north_teams) != (game.away_team_name in self.north_teams)

        if is_interleague:
            # 交流戦は予備日に振替
            d = self.calendar.interleague_end + datetime.timedelta(days=1)
            while d <= self.calendar.interleague_reserve_end:
                if d.weekday() != 0:  # 月曜以外
                    if self._can_schedule_on_date(d, game.home_team_name, game.away_team_name):
                        return d
                d += datetime.timedelta(days=1)
            # 予備日に空きがない場合は9月以降で探す
            september_start = datetime.date(self.year, 9, 1)
            d = september_start
            while d <= self.calendar.regular_season_end:
                if d.weekday() != 0:
                    if self._can_schedule_on_date(d, game.home_team_name, game.away_team_name):
                        return d
                d += datetime.timedelta(days=1)
        else:
            # リーグ戦: 元の日付以降の9月～で探す
            september_start = datetime.date(self.year, 9, 1)
            # 元の日付と9月1日の遅い方から開始
            search_start = max(original_date + datetime.timedelta(days=1), september_start)

            d = search_start
            while d <= self.calendar.regular_season_end:
                if d.weekday() != 0:  # 月曜以外
                    if self._can_schedule_on_date(d, game.home_team_name, game.away_team_name):
                        return d
                d += datetime.timedelta(days=1)

        # シーズン終了後〜CS前で探す（元の日付以降のみ）
        d = max(self.calendar.regular_season_end + datetime.timedelta(days=1),
                original_date + datetime.timedelta(days=1))
        max_search = d + datetime.timedelta(days=30)
        while d < max_search:
            if d.weekday() != 0:
                if self._can_schedule_on_date(d, game.home_team_name, game.away_team_name):
                    return d
            d += datetime.timedelta(days=1)

        return None

    def _can_schedule_on_date(self, date: datetime.date, home: str, away: str) -> bool:
        date_str = date.strftime("%Y-%m-%d")
        games_on_date = [g for g in self.schedule.games if g.date == date_str]

        if len(games_on_date) >= 6:
            return False

        for g in games_on_date:
            if g.home_team_name in [home, away] or g.away_team_name in [home, away]:
                return False

        return True

    def is_regular_season_complete(self) -> bool:
        scheduled_games = [g for g in self.schedule.games if g.status == GameStatus.SCHEDULED]
        return len(scheduled_games) == 0 and len(self.postponed_games) == 0

    def get_last_regular_season_game_date(self) -> datetime.date:
        """全ての正規シーズン試合の最終日を取得"""
        if not self.schedule.games:
            return self.calendar.regular_season_end

        last_date = self.calendar.regular_season_end
        for game in self.schedule.games:
            try:
                game_date = datetime.datetime.strptime(game.date, "%Y-%m-%d").date()
                if game_date > last_date:
                    last_date = game_date
            except:
                continue
        return last_date

    def get_postseason_start_date(self) -> datetime.date:
        """CSの開始日を計算（最後の試合の1週間後）"""
        last_game = self.get_last_regular_season_game_date()
        # 最後の試合から1週間後
        cs_start = last_game + datetime.timedelta(days=7)
        # 元の予定より早い場合は元の予定を使用
        return max(cs_start, self.calendar.cs_first_start)

    # ========================================
    # 二軍・三軍日程生成
    # ========================================

    def generate_farm_schedule(self, north_teams: List[Team], south_teams: List[Team], level: TeamLevel) -> Schedule:
        n_names = [t.name for t in north_teams]
        s_names = [t.name for t in south_teams]
        all_names = n_names + s_names
        n_teams = len(all_names)

        schedule = Schedule()
        games = []

        special_pairings = set()
        for i in range(0, n_teams, 2):
            if i + 1 < n_teams:
                special_pairings.add((i, i + 1))

        if level == TeamLevel.SECOND:
            base_games = 11
            special_games = 10
        else:
            base_games = 9
            special_games = 10

        for i, t1 in enumerate(all_names):
            for j, t2 in enumerate(all_names):
                if i >= j:
                    continue

                is_special = (i, j) in special_pairings or (j, i) in special_pairings
                count = special_games if is_special else base_games

                home_games = count // 2
                away_games = count - home_games

                if (i + j) % 2 == 0:
                    home_games, away_games = away_games, home_games

                for _ in range(home_games):
                    games.append((t1, t2, False))
                for _ in range(away_games):
                    games.append((t2, t1, False))

        self._assign_games_to_dates_scattered(schedule, games, level)
        return schedule

    def _assign_games_to_dates_scattered(self, schedule_obj: Schedule, all_games: List[Tuple[str, str, bool]], level: TeamLevel):
        random.shuffle(all_games)
        valid_dates = self._get_farm_valid_dates(level)

        date_schedule_map = {d: set() for d in valid_dates}
        scheduled_games_list = []
        game_number = 1

        for home, away, _ in all_games:
            found_date = None

            for _ in range(50):
                d = random.choice(valid_dates)
                teams_on_date = date_schedule_map[d]
                if home not in teams_on_date and away not in teams_on_date:
                    found_date = d
                    break

            if found_date is None:
                for d in valid_dates:
                    teams_on_date = date_schedule_map[d]
                    if home not in teams_on_date and away not in teams_on_date:
                        found_date = d
                        break

            if found_date:
                date_str = found_date.strftime("%Y-%m-%d")
                scheduled_games_list.append(ScheduledGame(
                    game_number=game_number, date=date_str,
                    home_team_name=home, away_team_name=away
                ))
                date_schedule_map[found_date].add(home)
                date_schedule_map[found_date].add(away)
                game_number += 1

        schedule_obj.games = scheduled_games_list
        schedule_obj.games.sort(key=lambda g: (g.date, g.game_number))
        for i, game in enumerate(schedule_obj.games):
            game.game_number = i + 1

    def _get_farm_valid_dates(self, level: TeamLevel) -> List[datetime.date]:
        valid_dates = []
        d = self.calendar.opening_day

        while d <= self.calendar.regular_season_end:
            if d.weekday() != 0:
                valid_dates.append(d)
            d += datetime.timedelta(days=1)

        return valid_dates

    # ========================================
    # ユーティリティ
    # ========================================

    def get_team_schedule(self, team_name: str) -> List[ScheduledGame]:
        return [g for g in self.schedule.games
                if g.home_team_name == team_name or g.away_team_name == team_name]

    def get_next_game(self, team_name: str, after_date: str = None) -> Optional[ScheduledGame]:
        for game in self.schedule.games:
            if game.status != GameStatus.SCHEDULED:
                continue
            if after_date and game.date <= after_date:
                continue
            if game.home_team_name == team_name or game.away_team_name == team_name:
                return game
        return None

    def get_games_for_date(self, date_str: str) -> List[ScheduledGame]:
        return [g for g in self.schedule.games if g.date == date_str]

    def is_interleague_period(self, date_str: str) -> bool:
        try:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return self.calendar.interleague_start <= d <= self.calendar.interleague_end
        except:
            return False

    def is_allstar_break(self, date_str: str) -> bool:
        try:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            allstar_rest_start = self.calendar.allstar_day1 - datetime.timedelta(days=1)
            allstar_rest_end = self.calendar.allstar_day2 + datetime.timedelta(days=1)
            return allstar_rest_start <= d <= allstar_rest_end
        except:
            return False

    def get_schedule_stats(self) -> Dict:
        stats = {"total_games": len(self.schedule.games), "teams": {}}
        for team in self.all_teams:
            team_games = self.get_team_schedule(team)
            home = len([g for g in team_games if g.home_team_name == team])
            away = len([g for g in team_games if g.away_team_name == team])
            stats["teams"][team] = {"total": len(team_games), "home": home, "away": away}
        return stats


# ========================================
# オールスターゲームエンジン
# ========================================

@dataclass
class AllStarSelection:
    """オールスター選出選手"""
    player: Player
    team_name: str
    position: Position
    votes: int = 0
    is_starter: bool = False


class AllStarGameEngine:
    """オールスターゲーム管理"""

    def __init__(self, year: int, all_teams: List[Team]):
        self.year = year
        self.all_teams = all_teams
        self.north_roster: List[AllStarSelection] = []
        self.south_roster: List[AllStarSelection] = []
        self.game1_result: Optional[Tuple[int, int]] = None
        self.game2_result: Optional[Tuple[int, int]] = None
        self.game1_detail: Optional[dict] = None
        self.game2_detail: Optional[dict] = None

    def select_allstar_players(self) -> Tuple[List[AllStarSelection], List[AllStarSelection]]:
        """オールスター選手を選出（成績ベース）"""
        from models import League

        north_teams = [t for t in self.all_teams if t.league == League.NORTH]
        south_teams = [t for t in self.all_teams if t.league == League.SOUTH]

        self.north_roster = self._select_league_roster(north_teams)
        self.south_roster = self._select_league_roster(south_teams)

        return self.north_roster, self.south_roster

    def _select_league_roster(self, teams: List[Team]) -> List[AllStarSelection]:
        """リーグのオールスターロースターを選出（28名）"""
        roster = []

        # 各ポジション最低1名 + 成績上位者
        all_players = []
        for team in teams:
            for player in team.players:
                if player.team_level == TeamLevel.FIRST and not player.is_injured:
                    all_players.append((player, team.name))

        # 投手（12名）
        # 投手選出 (先発6名、救援6名)
        pitchers = [(p, t) for p, t in all_players if p.position == Position.PITCHER]
        
        # 先発候補 (先発適性あり)
        starters_cand = [x for x in pitchers if x[0].starter_aptitude >= 3]
        starters_cand.sort(key=lambda x: (x[0].record.wins, -x[0].record.era), reverse=True)
        
        # 救援候補 (抑え/中継ぎ適性あり)
        relievers_cand = [x for x in pitchers if x[0].closer_aptitude >= 3 or x[0].middle_aptitude >= 3]
        relievers_cand.sort(key=lambda x: (x[0].record.saves, x[0].record.holds, -x[0].record.era), reverse=True)
        
        # 重複排除用
        selected_pids = set()
        
        # 先発6名
        for i, (p, t) in enumerate(starters_cand[:6]):
            if p in selected_pids: continue
            roster.append(AllStarSelection(
                player=p, team_name=t, position=p.position,
                votes=1000 - i * 50, is_starter=(i < 3) # Top 3 start
            ))
            selected_pids.add(p)
            
        # 救援6名 -> 7名
        count_r = 0
        for i, (p, t) in enumerate(relievers_cand):
            if count_r >= 7: break
            if p in selected_pids: continue
            roster.append(AllStarSelection(
                player=p, team_name=t, position=p.position,
                votes=800 - i * 50, is_starter=False
            ))
            selected_pids.add(p)
            count_r += 1

        # 捕手（3名）
        catchers = [(p, t) for p, t in all_players if p.position == Position.CATCHER]
        catchers.sort(key=lambda x: x[0].record.ops, reverse=True)
        for i, (p, t) in enumerate(catchers[:3]):
            roster.append(AllStarSelection(
                player=p, team_name=t, position=p.position,
                votes=800 - i * 50, is_starter=(i == 0)
            ))

        # 内野手（7名 -> 9名）
        infielders = [(p, t) for p, t in all_players if p.position in [
            Position.FIRST, Position.SECOND, Position.THIRD, Position.SHORTSTOP
        ]]
        infielders.sort(key=lambda x: x[0].record.ops, reverse=True)
        for i, (p, t) in enumerate(infielders[:9]):
            roster.append(AllStarSelection(
                player=p, team_name=t, position=p.position,
                votes=900 - i * 40, is_starter=(i < 4)
            ))

        # 外野手（6名）
        outfielders = [(p, t) for p, t in all_players if p.position in [
            Position.LEFT, Position.CENTER, Position.RIGHT
        ]]
        outfielders.sort(key=lambda x: x[0].record.ops, reverse=True)
        for i, (p, t) in enumerate(outfielders[:6]):
            roster.append(AllStarSelection(
                player=p, team_name=t, position=p.position,
                votes=850 - i * 40, is_starter=(i < 3)
            ))

        return roster

    def simulate_single_allstar_game(self, game_number: int):
        """指定された試合番号(1 or 2)のみシミュレート (LiveGameEngine使用)"""
        from live_game_engine import LiveGameEngine
        
        # チームオブジェクト作成
        team_n, team_s = self.create_team_objects()
        
        target_engine = None
        
        if game_number == 1:
            # Game 1: North (Home) vs South (Away)
            eng1 = LiveGameEngine(team_n, team_s, is_all_star=True)
            while not eng1.is_game_over():
                eng1.simulate_pitch(manual_strategy="AUTO")
            
            # Capture metadata (Win/Loss/Save)
            meta = eng1.finalize_game_stats()
            self.game1_result = (eng1.state.home_score, eng1.state.away_score)
            
            # 詳細データの作成
            mvp1 = self._determine_mvp(eng1)
            self.game1_detail = {
                'north_innings': self._get_inning_scores(eng1, True), # Home=North
                'south_innings': self._get_inning_scores(eng1, False),
                'mvp': mvp1,
                'box_score': self._create_box_score(eng1),
                'engine': eng1,
                'pitcher_result': {
                    'win': meta.get('win'),
                    'loss': meta.get('loss'),
                    'save': meta.get('save')
                }
            }
            target_engine = eng1
            
        elif game_number == 2:
            # Game 2: South (Home) vs North (Away)
            eng2 = LiveGameEngine(team_s, team_n, is_all_star=True)
            while not eng2.is_game_over():
                eng2.simulate_pitch(manual_strategy="AUTO")
                
            meta = eng2.finalize_game_stats()
            self.game2_result = (eng2.state.home_score, eng2.state.away_score) # Home=South
            
            mvp2 = self._determine_mvp(eng2)
            self.game2_detail = {
                'north_innings': self._get_inning_scores(eng2, False), # Away=North
                'south_innings': self._get_inning_scores(eng2, True),  # Home=South
                'mvp': mvp2,
                'box_score': self._create_box_score(eng2),
                'engine': eng2,
                'pitcher_result': {
                    'win': meta.get('win'),
                    'loss': meta.get('loss'),
                    'save': meta.get('save')
                }
            }
            target_engine = eng2

        return target_engine

    def _get_inning_scores(self, engine, is_home):
        scores = engine.state.home_inning_scores if is_home else engine.state.away_inning_scores
        # Ensure at least 9 innings
        res = scores[:]
        while len(res) < 9:
            res.append(0)
        return res

    def _determine_mvp(self, engine):
        home_win = engine.state.home_score > engine.state.away_score
        win_team = engine.home_team if home_win else engine.away_team
        
        candidates = [p for p in win_team.players if engine.game_stats[p]['rbis'] > 0 or engine.game_stats[p]['earned_runs'] == 0] 
        if not candidates: candidates = win_team.players
        
        import random
        mvp_p = random.choice(candidates)
        return f"{mvp_p.name} ({win_team.name})"

    def _create_box_score(self, engine):
        # Convert engine.game_stats to dict usable by UI
        # But UI Logic (BoxScoreCard) re-extracts from game_stats object.
        # So we just pass game_stats raw or wrapped.
        return engine.game_stats # returning raw defaultdict is safest implementation for now

    def get_winner(self) -> str:
        """オールスター勝利リーグを取得"""
        if not self.game1_result or not self.game2_result:
            return "未定"

        north_wins = 0
        south_wins = 0

        if self.game1_result[0] > self.game1_result[1]:
            north_wins += 1
        elif self.game1_result[1] > self.game1_result[0]:
            south_wins += 1

        if self.game2_result[0] > self.game2_result[1]:
            north_wins += 1
        elif self.game2_result[1] > self.game2_result[0]:
            south_wins += 1

        if north_wins > south_wins:
            return "North League"
        elif south_wins > north_wins:
            return "South League"
    def create_team_objects(self) -> Tuple[object, object]:
        """オールスター対戦用のチームオブジェクト（一時的）を作成"""
        from models import Team, League, Position, TeamLevel

        def build_team(name, league, roster: List[AllStarSelection]):
            team = Team(name, league)
            team.color = "#FFD700"  # All-Star Gold
            
            # 分類
            pitchers_sel = [x for x in roster if x.position == Position.PITCHER]
            fielders_sel = [x for x in roster if x.position != Position.PITCHER]
            
            # 選手を追加 (オリジナルを変更しないように注意が必要だが、
            # LiveGameEngineがPlayerオブジェクトをキーにする場合、参照を維持する)
            # ここではシンプルにリストに追加し、インデックスで管理する
            
            # 1. 投手を追加
            for sel in pitchers_sel:
                team.players.append(sel.player)
            
            # 2. 野手を追加
            offset = len(team.players)
            for sel in fielders_sel:
                team.players.append(sel.player)
                
            # スタメン設定 (野手から選出)
            # is_starterフラグがある選手を優先、足りなければ適当に
            starters = [x for x in fielders_sel if x.is_starter]
            if len(starters) < 9:
                # 足りない場合は補充
                others = [x for x in fielders_sel if not x.is_starter]
                starters.extend(others[:9-len(starters)])
            
            # 打順決定 (OPS順)
            starters.sort(key=lambda x: x.player.record.ops, reverse=True)
            
            # ポジション重複の解消は簡易的 (本来は厳密にやるべきだが)
            # 単純に roster の position を使う
            used_pos = set()
            lineup = [-1] * 9  # 1-9番
            
            # ラインアップ配列は [1番のindex, 2番の実体index...]
            # スタメン選手の team.players におけるインデックスを特定する必要がある
            
            current_lineup_indices = [-1] * 9
            
            for i, sel in enumerate(starters[:9]):
                # team.players内のインデックスを探す
                pidx = -1
                for idx, p in enumerate(team.players):
                    if p == sel.player:
                        pidx = idx
                        break
                current_lineup_indices[i] = pidx
                
                # ポジション割り当て (データ上)
                # LiveGameEngineは team.lineup_positions を使う場合があるか確認
                pass

            team.current_lineup = current_lineup_indices
            
            # 投手設定
            team.rotation = []
            team.bullpen = []
            for i, sel in enumerate(pitchers_sel):
                pidx = -1
                for idx, p in enumerate(team.players):
                    if p == sel.player:
                        pidx = idx
                        break
                
                if i < 3: team.rotation.append(pidx)
                else: team.bullpen.append(pidx)
                
            # lineup_positions (リスト) の作成
            # team.current_lineup に対応する守備位置
            team.lineup_positions = []
            for idx in team.current_lineup:
                if idx != -1:
                    p = team.players[idx]
                    team.lineup_positions.append(p.position.value)
                else:
                    team.lineup_positions.append("DH")
            
            return team

        t_north = build_team("ALL-NORTH", League.NORTH, self.north_roster)
        t_south = build_team("ALL-SOUTH", League.SOUTH, self.south_roster)
        
        return t_north, t_south


# ========================================
# ポストシーズン（CS・日本シリーズ）エンジン
# ========================================

class PostseasonStage(Enum):
    CS_FIRST = "CSファーストステージ"
    CS_FINAL = "CSファイナルステージ"
    JAPAN_SERIES = "日本シリーズ"


@dataclass
class PostseasonSeries:
    """ポストシーズンシリーズ"""
    stage: PostseasonStage
    league: str  # "north", "south", or "japan_series"
    team1: str  # 上位チーム（ホームアドバンテージ）
    team2: str
    team1_wins: int = 0
    team2_wins: int = 0
    games_played: int = 0
    max_games: int = 3  # CSファースト=3, CSファイナル=6, 日本S=7
    team1_advantage: int = 0  # CSファイナルで1位チームに1勝アドバンテージ
    winner: Optional[str] = None
    schedule: List[ScheduledGame] = field(default_factory=list)


class PostseasonEngine:
    """ポストシーズン管理エンジン"""

    def __init__(self, year: int, calendar: SeasonCalendar):
        self.year = year
        self.calendar = calendar
        self.cs_north_first: Optional[PostseasonSeries] = None
        self.cs_south_first: Optional[PostseasonSeries] = None
        self.cs_north_final: Optional[PostseasonSeries] = None
        self.cs_south_final: Optional[PostseasonSeries] = None
        self.japan_series: Optional[PostseasonSeries] = None
        self.current_stage: Optional[PostseasonStage] = None

    def initialize_climax_series(self, north_standings: List[Tuple[str, int]],
                                   south_standings: List[Tuple[str, int]]):
        """クライマックスシリーズを初期化"""

        # CSファーストステージ（2位 vs 3位、2勝先勝、2位ホーム）
        if len(north_standings) >= 3:
            self.cs_north_first = PostseasonSeries(
                stage=PostseasonStage.CS_FIRST,
                league="north",
                team1=north_standings[1][0],  # 2位
                team2=north_standings[2][0],  # 3位
                max_games=3
            )
            self._generate_series_schedule(self.cs_north_first, self.calendar.cs_first_start)

        if len(south_standings) >= 3:
            self.cs_south_first = PostseasonSeries(
                stage=PostseasonStage.CS_FIRST,
                league="south",
                team1=south_standings[1][0],
                team2=south_standings[2][0],
                max_games=3
            )
            self._generate_series_schedule(self.cs_south_first, self.calendar.cs_first_start)

        # CSファイナルステージ（1位 vs ファースト勝者、4勝先勝、1位に1勝アドバンテージ）
        if len(north_standings) >= 1:
            self.cs_north_final = PostseasonSeries(
                stage=PostseasonStage.CS_FINAL,
                league="north",
                team1=north_standings[0][0],  # 1位
                team2="ファースト勝者",  # プレースホルダー
                max_games=6,
                team1_advantage=1  # 1勝アドバンテージ
            )

        if len(south_standings) >= 1:
            self.cs_south_final = PostseasonSeries(
                stage=PostseasonStage.CS_FINAL,
                league="south",
                team1=south_standings[0][0],
                team2="ファースト勝者",
                max_games=6,
                team1_advantage=1
            )

        self.current_stage = PostseasonStage.CS_FIRST

    def _generate_series_schedule(self, series: PostseasonSeries, start_date: datetime.date):
        """シリーズの日程を生成"""
        series.schedule = []
        current_date = start_date

        for i in range(series.max_games):
            date_str = current_date.strftime("%Y-%m-%d")

            # ホーム・アウェイの決定
            if series.stage == PostseasonStage.JAPAN_SERIES:
                # 2-3-2方式
                if i < 2 or i >= 5:
                    home = series.team1
                    away = series.team2
                else:
                    home = series.team2
                    away = series.team1
            else:
                # CS: 上位チームが全試合ホーム
                home = series.team1
                away = series.team2

            series.schedule.append(ScheduledGame(
                game_number=i + 1, date=date_str,
                home_team_name=home, away_team_name=away
            ))

            current_date += datetime.timedelta(days=1)

            # 日本シリーズ移動日
            if series.stage == PostseasonStage.JAPAN_SERIES and (i == 1 or i == 4):
                current_date += datetime.timedelta(days=1)

    def record_game_result(self, series: PostseasonSeries, team1_score: int, team2_score: int):
        """試合結果を記録"""
        series.games_played += 1

        if team1_score > team2_score:
            series.team1_wins += 1
        else:
            series.team2_wins += 1

        # 勝敗判定
        wins_needed = (series.max_games // 2) + 1
        if series.stage == PostseasonStage.CS_FINAL:
            wins_needed = 4  # アドバンテージ込みで4勝必要

        total_team1_wins = series.team1_wins + series.team1_advantage

        if total_team1_wins >= wins_needed:
            series.winner = series.team1
        elif series.team2_wins >= wins_needed:
            series.winner = series.team2

    def advance_to_cs_final(self):
        """CSファイナルに進出"""
        if self.cs_north_first and self.cs_north_first.winner:
            self.cs_north_final.team2 = self.cs_north_first.winner
            self._generate_series_schedule(self.cs_north_final, self.calendar.cs_final_start)

        if self.cs_south_first and self.cs_south_first.winner:
            self.cs_south_final.team2 = self.cs_south_first.winner
            self._generate_series_schedule(self.cs_south_final, self.calendar.cs_final_start)

        self.current_stage = PostseasonStage.CS_FINAL

    def initialize_japan_series(self):
        """日本シリーズを初期化"""
        if not self.cs_north_final or not self.cs_south_final:
            return

        north_champion = self.cs_north_final.winner
        south_champion = self.cs_south_final.winner

        if not north_champion or not south_champion:
            return

        # 年によってホームアドバンテージを交互
        if self.year % 2 == 0:
            team1 = south_champion
            team2 = north_champion
        else:
            team1 = north_champion
            team2 = south_champion

        self.japan_series = PostseasonSeries(
            stage=PostseasonStage.JAPAN_SERIES,
            league="japan_series",
            team1=team1,
            team2=team2,
            max_games=7
        )
        self._generate_series_schedule(self.japan_series, self.calendar.japan_series_start)
        self.current_stage = PostseasonStage.JAPAN_SERIES

    def is_postseason_complete(self) -> bool:
        """ポストシーズンが完了したか"""
        return self.japan_series is not None and self.japan_series.winner is not None

    def get_japan_champion(self) -> Optional[str]:
        """日本一チームを取得"""
        if self.japan_series:
            return self.japan_series.winner
        return None


# ========================================
# シーズン状態管理
# ========================================

class SeasonPhase(Enum):
    PRE_SEASON = "プレシーズン"
    REGULAR_SEASON = "レギュラーシーズン"
    INTERLEAGUE = "交流戦"
    ALLSTAR_BREAK = "オールスター"
    CLIMAX_SERIES = "クライマックスシリーズ"
    JAPAN_SERIES = "日本シリーズ"
    OFF_SEASON = "オフシーズン"


class SeasonManager:
    """シーズン全体の状態管理"""

    def __init__(self, year: int):
        self.year = year
        self.calendar = SeasonCalendar.create(year)
        self.phase = SeasonPhase.PRE_SEASON
        self.postseason_complete = False
        self.allstar_engine: Optional[AllStarGameEngine] = None
        self.postseason_engine: Optional[PostseasonEngine] = None

    def get_current_phase(self, date_str: str) -> SeasonPhase:
        try:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return SeasonPhase.REGULAR_SEASON

        if d < self.calendar.opening_day:
            return SeasonPhase.PRE_SEASON

        allstar_rest_start = self.calendar.allstar_day1 - datetime.timedelta(days=1)
        allstar_rest_end = self.calendar.allstar_day2 + datetime.timedelta(days=1)
        if allstar_rest_start <= d <= allstar_rest_end:
            return SeasonPhase.ALLSTAR_BREAK

        if self.calendar.interleague_start <= d <= self.calendar.interleague_reserve_end:
            return SeasonPhase.INTERLEAGUE

        if d <= self.calendar.max_season_end:
            return SeasonPhase.REGULAR_SEASON

        if d >= self.calendar.cs_first_start:
            if self.postseason_complete:
                return SeasonPhase.OFF_SEASON
            if self.postseason_engine:
                if self.postseason_engine.current_stage == PostseasonStage.JAPAN_SERIES:
                    return SeasonPhase.JAPAN_SERIES
            return SeasonPhase.CLIMAX_SERIES

        return SeasonPhase.REGULAR_SEASON

    def is_off_season(self, date_str: str) -> bool:
        return self.get_current_phase(date_str) == SeasonPhase.OFF_SEASON

    def mark_postseason_complete(self):
        self.postseason_complete = True
        self.phase = SeasonPhase.OFF_SEASON

    def initialize_allstar(self, all_teams: List[Team]):
        """オールスターを初期化"""
        self.allstar_engine = AllStarGameEngine(self.year, all_teams)
        self.allstar_engine.select_allstar_players()

    def initialize_postseason(self, north_standings: List[Tuple[str, int]],
                               south_standings: List[Tuple[str, int]]):
        """ポストシーズンを初期化"""
        self.postseason_engine = PostseasonEngine(self.year, self.calendar)
        self.postseason_engine.initialize_climax_series(north_standings, south_standings)


def create_league_schedule(year: int, north_teams: List[Team], south_teams: List[Team]) -> Schedule:
    engine = LeagueScheduleEngine(year)
    return engine.generate_schedule(north_teams, south_teams)
