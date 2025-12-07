# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Player Stats Detail Page
超詳細なセイバーメトリクス統計を表示する画面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QBrush

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from models import Player, PlayerRecord, TeamLevel, CareerStats


class StatsCard(QFrame):
    """統計カード"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        self.layout.addWidget(title_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(4)
        self.layout.addLayout(self.content_layout)

    def add_stat_row(self, label: str, value: str, highlight: bool = False):
        """統計行を追加"""
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_muted};
            border: none;
            background: transparent;
        """)
        row.addWidget(lbl)

        val = QLabel(value)
        color = self.theme.accent_blue if highlight else self.theme.text_primary
        val.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {color};
            font-family: 'Consolas', monospace;
            border: none;
            background: transparent;
        """)
        val.setAlignment(Qt.AlignRight)
        row.addWidget(val)

        self.content_layout.addLayout(row)


class PlayerStatsDetailPage(QWidget):
    """選手詳細統計ページ"""
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_player = None
        self.current_year = 2027
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.theme.bg_dark};
                border: none;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(20)

        self.placeholder = QLabel("選手を選択してください")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"""
            font-size: 18px;
            color: {self.theme.text_muted};
        """)
        self.content_layout.addWidget(self.placeholder)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        # Back button
        back_btn = QPushButton("← 戻る")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_card_hover};
                color: {self.theme.text_primary};
            }}
        """)
        back_btn.clicked.connect(self._on_back)
        toolbar.add_widget(back_btn)

        toolbar.add_separator()

        # Title
        self.title_label = QLabel("詳細統計")
        self.title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {self.theme.text_primary};
        """)
        toolbar.add_widget(self.title_label)

        toolbar.add_stretch()

        # Year selector
        year_label = QLabel("年度:")
        year_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        toolbar.add_widget(year_label)

        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(100)
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        toolbar.add_widget(self.year_combo)

        # Level selector
        level_label = QLabel("軍:")
        level_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        toolbar.add_widget(level_label)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["一軍", "二軍", "三軍", "通算"])
        self.level_combo.currentIndexChanged.connect(self._on_level_changed)
        toolbar.add_widget(self.level_combo)

        return toolbar

    def set_player(self, player: Player, current_year: int = 2027):
        """表示する選手を設定"""
        self.current_player = player
        self.current_year = current_year

        if not player:
            self.placeholder.show()
            self.title_label.setText("詳細統計")
            return

        self.placeholder.hide()
        self.title_label.setText(f"{player.name} - 詳細統計")

        # Year combo更新
        self._update_year_combo()

        # 表示更新
        self._update_display()

    def _update_year_combo(self):
        """年度コンボボックスを更新"""
        self.year_combo.blockSignals(True)
        self.year_combo.clear()

        if self.current_player and self.current_player.career_stats:
            years = sorted(self.current_player.career_stats.season_stats.keys(), reverse=True)
            for year in years:
                self.year_combo.addItem(f"{year}年", year)

        # 現在年を追加（成績がなくても）
        if self.year_combo.count() == 0 or self.current_year not in [
            self.year_combo.itemData(i) for i in range(self.year_combo.count())
        ]:
            self.year_combo.insertItem(0, f"{self.current_year}年", self.current_year)

        self.year_combo.blockSignals(False)

    def _on_year_changed(self, index):
        self._update_display()

    def _on_level_changed(self, index):
        self._update_display()

    def _update_display(self):
        """表示を更新"""
        # Clear existing content
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_player:
            return

        player = self.current_player
        year = self.year_combo.currentData() if self.year_combo.currentData() else self.current_year
        level_text = self.level_combo.currentText()

        # レコードを取得
        record = self._get_record(player, year, level_text)

        is_pitcher = player.position.value == "投手"

        # ヘッダー
        header = self._create_header(player, year, level_text)
        self.content_layout.addWidget(header)

        # タブウィジェット
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_secondary};
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background-color: {self.theme.primary};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self.theme.bg_card_hover};
            }}
        """)

        if is_pitcher:
            tabs.addTab(self._create_pitcher_basic_tab(record), "基本成績")
            tabs.addTab(self._create_pitcher_advanced_tab(record), "セイバー指標")
            tabs.addTab(self._create_pitcher_detail_tab(record), "詳細データ")
        else:
            tabs.addTab(self._create_batter_basic_tab(record), "基本成績")
            tabs.addTab(self._create_batter_advanced_tab(record), "セイバー指標")
            tabs.addTab(self._create_batter_detail_tab(record), "詳細データ")

        # 年度別一覧
        tabs.addTab(self._create_career_table(player, is_pitcher), "年度別成績")

        self.content_layout.addWidget(tabs)
        self.content_layout.addStretch()

    def _get_record(self, player: Player, year: int, level_text: str) -> PlayerRecord:
        """指定条件のレコードを取得"""
        if level_text == "通算":
            return player.career_stats.career_total

        level_map = {"一軍": TeamLevel.FIRST, "二軍": TeamLevel.SECOND, "三軍": TeamLevel.THIRD}
        level = level_map.get(level_text, TeamLevel.FIRST)

        # 現在年の場合は現在のレコードを使用
        if year == self.current_year:
            return player.get_record_by_level(level)

        # 過去年の場合はcareer_statsから取得
        season = player.career_stats.get_season(year, level)
        if season:
            return season.record
        return PlayerRecord()

    def _create_header(self, player: Player, year: int, level: str) -> QFrame:
        """ヘッダー作成"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-left: 4px solid {self.theme.primary};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)

        # 選手名
        name_label = QLabel(f"{player.name}")
        name_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 800;
            color: {self.theme.text_primary};
            border: none;
            background: transparent;
        """)
        layout.addWidget(name_label)

        # 背番号
        num_label = QLabel(f"#{player.uniform_number}")
        num_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 800;
            color: {self.theme.text_muted};
            font-family: 'Consolas', monospace;
            margin-left: 12px;
            border: none;
            background: transparent;
        """)
        layout.addWidget(num_label)

        layout.addStretch()

        # 年度・軍
        info_label = QLabel(f"{year}年 {level}")
        info_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.accent_blue};
            border: none;
            background: transparent;
        """)
        layout.addWidget(info_label)

        return frame

    def _create_batter_basic_tab(self, record: PlayerRecord) -> QWidget:
        """打者基本成績タブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # 基本成績
        grid = QGridLayout()
        grid.setSpacing(16)

        basic_card = StatsCard("基本成績")
        basic_card.add_stat_row("試合", str(record.games))
        basic_card.add_stat_row("打席", str(record.plate_appearances))
        basic_card.add_stat_row("打数", str(record.at_bats))
        basic_card.add_stat_row("安打", str(record.hits))
        basic_card.add_stat_row("二塁打", str(record.doubles))
        basic_card.add_stat_row("三塁打", str(record.triples))
        basic_card.add_stat_row("本塁打", str(record.home_runs), highlight=True)
        grid.addWidget(basic_card, 0, 0)

        scoring_card = StatsCard("得点・打点")
        scoring_card.add_stat_row("打点", str(record.rbis), highlight=True)
        scoring_card.add_stat_row("得点", str(record.runs))
        scoring_card.add_stat_row("四球", str(record.walks))
        scoring_card.add_stat_row("死球", str(record.hit_by_pitch))
        scoring_card.add_stat_row("三振", str(record.strikeouts))
        scoring_card.add_stat_row("犠打", str(record.sacrifice_hits))
        scoring_card.add_stat_row("犠飛", str(record.sacrifice_flies))
        grid.addWidget(scoring_card, 0, 1)

        running_card = StatsCard("走塁")
        running_card.add_stat_row("盗塁", str(record.stolen_bases), highlight=True)
        running_card.add_stat_row("盗塁死", str(record.caught_stealing))
        sb_rate = record.sb_rate * 100
        running_card.add_stat_row("盗塁成功率", f"{sb_rate:.1f}%")
        running_card.add_stat_row("併殺打", str(record.grounded_into_dp))
        grid.addWidget(running_card, 0, 2)

        rate_card = StatsCard("率")
        avg = record.batting_average
        rate_card.add_stat_row("打率", f".{int(avg * 1000):03d}" if record.at_bats > 0 else "---", highlight=True)
        rate_card.add_stat_row("出塁率", f".{int(record.obp * 1000):03d}" if record.plate_appearances > 0 else "---")
        rate_card.add_stat_row("長打率", f".{int(record.slg * 1000):03d}" if record.at_bats > 0 else "---")
        rate_card.add_stat_row("OPS", f".{int(record.ops * 1000):03d}" if record.plate_appearances > 0 else "---", highlight=True)
        grid.addWidget(rate_card, 1, 0)

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def _create_batter_advanced_tab(self, record: PlayerRecord) -> QWidget:
        """打者セイバーメトリクスタブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)

        # 打撃価値
        value_card = StatsCard("打撃価値指標")
        value_card.add_stat_row("wOBA", f".{int(record.woba * 1000):03d}" if record.plate_appearances > 0 else "---", highlight=True)
        value_card.add_stat_row("wRAA", f"{record.wraa:.1f}")
        value_card.add_stat_row("RC", f"{record.rc:.1f}")
        value_card.add_stat_row("RC/27", f"{record.rc27:.2f}" if record.rc27 > 0 else "---", highlight=True)
        grid.addWidget(value_card, 0, 0)

        # 長打力
        power_card = StatsCard("長打力指標")
        power_card.add_stat_row("ISO", f".{int(record.iso * 1000):03d}" if record.at_bats > 0 else "---", highlight=True)
        power_card.add_stat_row("AB/HR", f"{record.ab_per_hr:.1f}" if record.home_runs > 0 else "---")
        power_card.add_stat_row("長打率", f".{int(record.slg * 1000):03d}" if record.at_bats > 0 else "---")
        tb = record.singles + record.doubles * 2 + record.triples * 3 + record.home_runs * 4
        power_card.add_stat_row("塁打", str(tb))
        grid.addWidget(power_card, 0, 1)

        # 選球眼
        eye_card = StatsCard("選球眼指標")
        eye_card.add_stat_row("BB%", f"{record.bb_rate * 100:.1f}%")
        eye_card.add_stat_row("K%", f"{record.k_rate * 100:.1f}%")
        eye_card.add_stat_row("BB/K", f"{record.bb_k_ratio:.2f}" if record.strikeouts > 0 else "---", highlight=True)
        eye_card.add_stat_row("P/PA", f"{(record.plate_appearances * 4.1):.1f}" if record.plate_appearances > 0 else "---")  # 仮
        grid.addWidget(eye_card, 0, 2)

        # 運・分析
        luck_card = StatsCard("運・打球分析")
        luck_card.add_stat_row("BABIP", f".{int(record.babip * 1000):03d}" if record.at_bats > 0 else "---", highlight=True)
        if record.balls_in_play > 0:
            gb_pct = record.ground_balls / record.balls_in_play * 100
            fb_pct = record.fly_balls / record.balls_in_play * 100
            ld_pct = record.line_drives / record.balls_in_play * 100
        else:
            gb_pct = fb_pct = ld_pct = 0
        luck_card.add_stat_row("GB%", f"{gb_pct:.1f}%")
        luck_card.add_stat_row("FB%", f"{fb_pct:.1f}%")
        luck_card.add_stat_row("LD%", f"{ld_pct:.1f}%")
        grid.addWidget(luck_card, 1, 0)

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def _create_batter_detail_tab(self, record: PlayerRecord) -> QWidget:
        """打者詳細データタブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)

        # 打球データ
        ball_card = StatsCard("打球データ")
        ball_card.add_stat_row("ゴロ", str(record.ground_balls))
        ball_card.add_stat_row("フライ", str(record.fly_balls))
        ball_card.add_stat_row("ライナー", str(record.line_drives))
        ball_card.add_stat_row("ポップフライ", str(record.popups))
        ball_card.add_stat_row("強打球", str(record.hard_hit_balls), highlight=True)
        grid.addWidget(ball_card, 0, 0)

        # 詳細カウント
        count_card = StatsCard("詳細カウント")
        count_card.add_stat_row("故意四球", str(record.intentional_walks))
        count_card.add_stat_row("死球", str(record.hit_by_pitch))
        count_card.add_stat_row("敬遠除く四球", str(record.walks - record.intentional_walks))
        count_card.add_stat_row("インプレー", str(record.balls_in_play))
        grid.addWidget(count_card, 0, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def _create_pitcher_basic_tab(self, record: PlayerRecord) -> QWidget:
        """投手基本成績タブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)

        basic_card = StatsCard("基本成績")
        basic_card.add_stat_row("登板", str(record.games_pitched))
        basic_card.add_stat_row("先発", str(record.games_started))
        basic_card.add_stat_row("勝利", str(record.wins), highlight=True)
        basic_card.add_stat_row("敗戦", str(record.losses))
        basic_card.add_stat_row("セーブ", str(record.saves), highlight=True)
        basic_card.add_stat_row("ホールド", str(record.holds))
        basic_card.add_stat_row("勝率", f".{int(record.winning_percentage * 1000):03d}" if (record.wins + record.losses) > 0 else "---")
        grid.addWidget(basic_card, 0, 0)

        innings_card = StatsCard("投球")
        innings_card.add_stat_row("投球回", f"{record.innings_pitched:.1f}")
        innings_card.add_stat_row("被安打", str(record.hits_allowed))
        innings_card.add_stat_row("被本塁打", str(record.home_runs_allowed))
        innings_card.add_stat_row("与四球", str(record.walks_allowed))
        innings_card.add_stat_row("奪三振", str(record.strikeouts_pitched), highlight=True)
        innings_card.add_stat_row("与死球", str(record.hit_batters))
        grid.addWidget(innings_card, 0, 1)

        runs_card = StatsCard("失点")
        runs_card.add_stat_row("失点", str(record.runs_allowed))
        runs_card.add_stat_row("自責点", str(record.earned_runs))
        runs_card.add_stat_row("防御率", f"{record.era:.2f}" if record.innings_pitched > 0 else "---", highlight=True)
        runs_card.add_stat_row("暴投", str(record.wild_pitches))
        runs_card.add_stat_row("ボーク", str(record.balks))
        grid.addWidget(runs_card, 0, 2)

        quality_card = StatsCard("品質")
        quality_card.add_stat_row("QS", str(record.quality_starts))
        quality_card.add_stat_row("完投", str(record.complete_games))
        quality_card.add_stat_row("完封", str(record.shutouts), highlight=True)
        quality_card.add_stat_row("ブロウン", str(record.blown_saves))
        grid.addWidget(quality_card, 1, 0)

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def _create_pitcher_advanced_tab(self, record: PlayerRecord) -> QWidget:
        """投手セイバーメトリクスタブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)

        # FIP系
        fip_card = StatsCard("守備非依存指標")
        fip_card.add_stat_row("FIP", f"{record.fip:.2f}" if record.innings_pitched > 0 else "---", highlight=True)
        fip_card.add_stat_row("xFIP", f"{record.xfip:.2f}" if record.innings_pitched > 0 else "---")
        fip_card.add_stat_row("SIERA", f"{record.siera:.2f}" if record.innings_pitched > 0 else "---")
        fip_card.add_stat_row("ERA-FIP", f"{(record.era - record.fip):.2f}" if record.innings_pitched > 0 else "---")
        grid.addWidget(fip_card, 0, 0)

        # 奪三振・四球
        k_bb_card = StatsCard("奪三振・四球")
        k_bb_card.add_stat_row("K/9", f"{record.k_per_9:.2f}" if record.innings_pitched > 0 else "---", highlight=True)
        k_bb_card.add_stat_row("BB/9", f"{record.bb_per_9:.2f}" if record.innings_pitched > 0 else "---")
        k_bb_card.add_stat_row("K/BB", f"{record.k_bb_ratio:.2f}" if record.walks_allowed > 0 else "---", highlight=True)
        k_bb_card.add_stat_row("K%", f"{record.k_rate_pitched * 100:.1f}%")
        k_bb_card.add_stat_row("BB%", f"{record.bb_rate_pitched * 100:.1f}%")
        grid.addWidget(k_bb_card, 0, 1)

        # 被打
        hit_card = StatsCard("被打指標")
        hit_card.add_stat_row("WHIP", f"{record.whip:.2f}" if record.innings_pitched > 0 else "---", highlight=True)
        hit_card.add_stat_row("H/9", f"{record.h_per_9:.2f}" if record.innings_pitched > 0 else "---")
        hit_card.add_stat_row("HR/9", f"{record.hr_per_9:.2f}" if record.innings_pitched > 0 else "---")
        hit_card.add_stat_row("被BABIP", f".{int(record.babip_against * 1000):03d}" if record.innings_pitched > 0 else "---")
        grid.addWidget(hit_card, 0, 2)

        # 打球・LOB
        ball_card = StatsCard("打球・残塁")
        ball_card.add_stat_row("GB%", f"{record.gb_rate * 100:.1f}%" if record.ground_outs + record.fly_outs > 0 else "---")
        ball_card.add_stat_row("FB%", f"{record.fb_rate * 100:.1f}%" if record.ground_outs + record.fly_outs > 0 else "---")
        ball_card.add_stat_row("LOB%", f"{record.lob_rate * 100:.1f}%" if record.hits_allowed > 0 else "---", highlight=True)
        grid.addWidget(ball_card, 1, 0)

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def _create_pitcher_detail_tab(self, record: PlayerRecord) -> QWidget:
        """投手詳細データタブ"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(16)

        pitch_card = StatsCard("投球データ")
        pitch_card.add_stat_row("投球数", str(record.pitches_thrown))
        pitch_card.add_stat_row("ストライク", str(record.strikes_thrown))
        pitch_card.add_stat_row("ボール", str(record.balls_thrown))
        pitch_card.add_stat_row("ストライク率", f"{record.strike_percentage * 100:.1f}%" if record.pitches_thrown > 0 else "---", highlight=True)
        pitch_card.add_stat_row("初球ストライク", str(record.first_pitch_strikes))
        pitch_card.add_stat_row("投球数/イニング", f"{record.pitches_per_inning:.1f}" if record.innings_pitched > 0 else "---")
        grid.addWidget(pitch_card, 0, 0)

        out_card = StatsCard("アウト内訳")
        out_card.add_stat_row("ゴロアウト", str(record.ground_outs))
        out_card.add_stat_row("フライアウト", str(record.fly_outs))
        out_card.add_stat_row("故意四球", str(record.intentional_walks_allowed))
        grid.addWidget(out_card, 0, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return widget

    def _create_career_table(self, player: Player, is_pitcher: bool) -> QWidget:
        """年度別成績テーブル"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        table = QTableWidget()

        if is_pitcher:
            headers = ["年度", "軍", "登板", "勝", "敗", "S", "H", "投球回", "防御率", "奪三振",
                      "WHIP", "K/9", "BB/9", "FIP"]
        else:
            headers = ["年度", "軍", "試合", "打率", "本塁", "打点", "安打", "OPS",
                      "wOBA", "BB%", "K%", "ISO", "BABIP"]

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # データ収集
        all_seasons = player.career_stats.get_all_seasons()
        # 現在シーズンも追加
        current_records = [
            (self.current_year, "一軍", player.record),
            (self.current_year, "二軍", player.record_farm),
            (self.current_year, "三軍", player.record_third),
        ]

        rows_data = []
        for year, level, record in current_records:
            if record.games > 0 or record.games_pitched > 0:
                rows_data.append((year, level, record))

        for year, level, season in all_seasons:
            if year != self.current_year:  # 現在年は上で追加済み
                rows_data.append((year, level, season.record))

        # 年度降順でソート
        rows_data.sort(key=lambda x: (x[0], x[1]), reverse=True)

        table.setRowCount(len(rows_data))

        for row, (year, level, record) in enumerate(rows_data):
            if is_pitcher:
                values = [
                    str(year),
                    level,
                    str(record.games_pitched),
                    str(record.wins),
                    str(record.losses),
                    str(record.saves),
                    str(record.holds),
                    f"{record.innings_pitched:.1f}",
                    f"{record.era:.2f}" if record.innings_pitched > 0 else "-",
                    str(record.strikeouts_pitched),
                    f"{record.whip:.2f}" if record.innings_pitched > 0 else "-",
                    f"{record.k_per_9:.2f}" if record.innings_pitched > 0 else "-",
                    f"{record.bb_per_9:.2f}" if record.innings_pitched > 0 else "-",
                    f"{record.fip:.2f}" if record.innings_pitched > 0 else "-",
                ]
            else:
                avg = record.batting_average
                values = [
                    str(year),
                    level,
                    str(record.games),
                    f".{int(avg * 1000):03d}" if record.at_bats > 0 else "-",
                    str(record.home_runs),
                    str(record.rbis),
                    str(record.hits),
                    f".{int(record.ops * 1000):03d}" if record.plate_appearances > 0 else "-",
                    f".{int(record.woba * 1000):03d}" if record.plate_appearances > 0 else "-",
                    f"{record.bb_rate * 100:.1f}%",
                    f"{record.k_rate * 100:.1f}%",
                    f".{int(record.iso * 1000):03d}" if record.at_bats > 0 else "-",
                    f".{int(record.babip * 1000):03d}" if record.at_bats > 0 else "-",
                ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col, item)

        # スタイル
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                gridline-color: {self.theme.border_muted};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.text_secondary};
                font-weight: 700;
                font-size: 11px;
                padding: 10px 6px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(table)
        return widget

    def _on_back(self):
        self.back_requested.emit()
