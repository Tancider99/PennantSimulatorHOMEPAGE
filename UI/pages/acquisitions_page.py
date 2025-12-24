# -*- coding: utf-8 -*-
"""
Acquisitions Page
Manage Free Agent signings and Developmental Player promotions
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QTableWidget, QHeaderView, 
    QMessageBox, QAbstractItemView, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont, QIcon

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from UI.widgets.tables import PlayerTable, SortableTableWidgetItem, RatingDelegate
from models import Player, Position, TeamLevel

class AcquisitionsTable(PlayerTable):
    """Custom PlayerTable for Acquisitions with Salary and Action columns"""
    
    action_requested = Signal(object)

    def __init__(self, parent=None, action_label="Action", btn_color=None):
        self.action_label = action_label
        self.btn_color = btn_color
        super().__init__(parent)
        
        # Increase row height to prevent button cutoff
        self.table.verticalHeader().setDefaultSectionSize(40)
        
        # Override the inner table style to remove hover effect strictly
        self.table.setStyleSheet(self.table.styleSheet() + """
            QTableWidget::item:hover {
                background-color: transparent;
                border: none;
            }
            QTableWidget::item:selected:hover {
                background-color: #ffffff;
                color: #000000;
            }
        """)

    def set_players(self, players: list, mode: str = "all"):
        """Override to ignore mode and always use combined view"""
        super().set_players(players, "all")

    def _refresh_columns(self, mode: str = "all"):
        """Set up table columns - Combined View"""
        self.table.clear()
        
        # Clear delegates
        for i in range(self.table.columnCount()):
            self.table.setItemDelegateForColumn(i, None)

        # Combined Headers
        # Info: #, Name, Pos, Age
        # Pitch: Vel, Con, Stm, Brk
        # Bat: Con, Pow, Run, Arm, Fld
        # Stats: ERA, W, L, S, AVG, HR, RBI, OPS
        # Salary, Action
        
        # Note: Pitcher Control(コ) and Batter Contact(ミ)?
        # Let's use clear headers.
        
        headers = [
            "#", "名前", "Pos", "年齢", "総合",
            "球速", "コ", "ス", "変",     # Pitching Abilities
            "ミ", "パ", "走", "肩", "守", # Batting/Fielding Abilities
            "防御率", "勝", # Reduced Pitching Stats
            "打率", "HR",   # Reduced Batting Stats
            "年俸", "操作"
        ]
        
        # Widths
        w_idx = 40
        w_name = 177 
        w_pos = 50
        w_age = 40
        w_total = 65 
        w_abi = 40 
        w_stat = 75 
        w_sal = 100 
        w_act = 120 
        
        widths = [
            w_idx, w_name, w_pos, w_age, w_total,
            60, w_abi, w_abi, w_abi,       # Vel, Con, Stm, Brk
            w_abi, w_abi, w_abi, w_abi, w_abi, # Con, Pow, Run, Arm, Fld
            w_stat, 50,    # ERA, W
            w_stat, 50,    # AVG, HR
            w_sal, w_act
        ]

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Custom Row Height removed (Default)

        # Set widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed) # All fixed
        
        # Apply specific widths
        for i, width in enumerate(widths):
            header.resizeSection(i, width)
        
        header.setStretchLastSection(False)

        # Set delegates for Ability columns
        # Indices: 
        # Total: 4 (String with color)
        # Pitch: 5 (Vel-raw), 6, 7, 8
        # Bat: 9, 10, 11, 12, 13
        rating_cols = [6, 7, 8, 9, 10, 11, 12, 13]
        
        for col in rating_cols:
            self.table.setItemDelegateForColumn(col, self.rating_delegate)

        # Set StarDelegate for Total column (Index 4)
        self.table.setItemDelegateForColumn(4, self.star_delegate)

        # Refresh data
        self._populate_table(mode)

    def _set_player_row(self, row, player, mode):
        """Set row data - Combined"""
        stats = player.stats
        record = player.record
        
        # Salary (億万形式で表示)
        salary_yen = player.salary
        man = salary_yen // 10000
        if man >= 10000:
            oku = man // 10000
            remainder = man % 10000
            salary_text = f"{oku}億{remainder}万" if remainder > 0 else f"{oku}億"
        else:
            salary_text = f"{man}万"
        salary_val = player.salary
        
        # Determine Role
        is_pitcher = player.position.value == "投手"

        # --- Abilities ---
        # No more forced "1". Use generated values.
        
        # Pitching
        vel_val = getattr(stats, 'velocity', 0)
        vel_text = f"{vel_val}km" if vel_val > 0 else "---"
        ctrl = getattr(stats, 'control', 1)
        stm = getattr(stats, 'stamina', 1)
        brk = getattr(stats, 'breaking', 1) 
            
        # Batting
        cont = getattr(stats, 'contact', 1)
        pow_ = getattr(stats, 'power', 1)
        run = getattr(stats, 'run', 1)
        arm = getattr(stats, 'arm', 1)
        fld = getattr(stats, 'fielding', 1)

        # --- Stats (Reduced) ---
        # Pitching
        if record.innings_pitched > 0 or is_pitcher:
            era_text = f"{record.era:.2f}" if record.innings_pitched > 0 else "-.--"
            wins = str(record.wins)
        else:
            era_text = "---"
            wins = "-"

        # Batting
        if record.at_bats > 0 or not is_pitcher:
             avg_text = f".{int(record.batting_average * 1000):03d}" if record.at_bats > 0 else "---"
             hr = str(record.home_runs)
        else:
             avg_text = "---"
             hr = "-"

        # --- Total Rating (Stars) ---
        # Calculate rating
        if is_pitcher:
            total_rating = stats.overall_pitching()
        else:
            total_rating = stats.overall_batting(player.position)
            
        stars_text = f"★ {total_rating}"

        data = [
            str(player.uniform_number),
            player.name,
            player.position.value[:2],
            str(player.age),
            stars_text, # Total
            # Pitching
            vel_text, ctrl, stm, brk,
            # Batting
            cont, pow_, run, arm, fld,
            # P Stats
            era_text, wins,
            # B Stats
            avg_text, hr,
            # Salary/Action
            salary_text,
            ""
        ]
        
        rating_cols = [6, 7, 8, 9, 10, 11, 12, 13]

        for col, value in enumerate(data):
            if col == len(data) - 1:
                # Action Column
                btn = QPushButton(self.action_label)
                if self.btn_color:
                    btn.setStyleSheet(f"background-color: {self.btn_color}; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
                else:
                    btn.setStyleSheet(f"background-color: #666; color: white; border-radius: 4px; padding: 4px;")
                
                btn.clicked.connect(lambda checked=False, p=player: self.action_requested.emit(p))
                self.table.setCellWidget(row, col, btn)
                continue

            item = SortableTableWidgetItem()
            if col in rating_cols:
                item.setData(Qt.UserRole, value)
                item.setData(Qt.DisplayRole, "") 
            else:
                item.setText(str(value))
                if "km" in str(value): # Vel
                     item.setData(Qt.UserRole, vel_val)
                elif "万" in str(value): # Salary (億万 format)
                     item.setData(Qt.UserRole, salary_val)
                elif "★" in str(value): # Total Stars
                     # Order Style: Gold Text
                     item.setForeground(QColor("#FFD700"))
                     item.setData(Qt.UserRole, total_rating)
                     item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            
            item.setTextAlignment(Qt.AlignCenter if col != 1 else Qt.AlignLeft | Qt.AlignVCenter)
            
            if col == 0:
                item.setData(Qt.UserRole, player)

            self.table.setItem(row, col, item)


class AcquisitionsPage(QWidget):
    """Acquisitions and Roster Management Page"""
    
    player_detail_requested = Signal(object)
    MAX_SHIHAIKA = 70

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._get_tab_style())
        
        self.release_tab = self._create_release_tab()
        self.tabs.addTab(self.release_tab, "自由契約 (戦力外通告)")
        
        self.promotion_tab = self._create_promotion_tab()
        self.tabs.addTab(self.promotion_tab, "支配下登録 (育成昇格)")
        
        layout.addWidget(self.tabs)

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        self.team_info_label = QLabel("チーム情報: --")
        self.team_info_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 14px; margin-left: 12px;")
        toolbar.add_widget(self.team_info_label)
        
        toolbar.add_stretch()
        
        # Reload button
        refresh_btn = QPushButton("更新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 4px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {self.theme.bg_hover}; }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        toolbar.add_widget(refresh_btn)

        return toolbar

    def _get_tab_style(self):
        return f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_secondary};
                padding: 8px 24px;
                border-bottom: 2px solid {self.theme.border};
                font-weight: bold;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {self.theme.primary};
                border-bottom: 2px solid {self.theme.primary};
                background: {self.theme.bg_input};
            }}
        """

    def _create_release_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        lbl = QLabel("自由契約にする選手を選択してください (解雇)")
        lbl.setStyleSheet(f"color: {self.theme.text_muted}; margin-bottom: 8px;")
        layout.addWidget(lbl)
        
        # Table
        self.release_table = AcquisitionsTable(action_label="自由契約", btn_color=self.theme.danger)
        self.release_table.action_requested.connect(self._release_player)
        self.release_table.player_double_clicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.release_table)
        
        return widget

    def _create_promotion_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        lbl = QLabel("支配下登録する育成選手を選択してください")
        lbl.setStyleSheet(f"color: {self.theme.text_muted}; margin-bottom: 8px;")
        layout.addWidget(lbl)
        
        # Table
        self.promo_table = AcquisitionsTable(action_label="支配下登録", btn_color=self.theme.accent_blue)
        self.promo_table.action_requested.connect(self._promote_player)
        self.promo_table.player_double_clicked.connect(self._on_table_double_clicked)
        layout.addWidget(self.promo_table)
        
        return widget

    def set_game_state(self, game_state):
        self.game_state = game_state
        if game_state:
            self.current_team = game_state.player_team
        self.refresh()

    def refresh(self):
        if not self.game_state: return
        self._update_info()
        self._refresh_release_list()
        self._refresh_promotion_list()

    def _update_info(self):
        if not self.current_team:
            self.team_info_label.setText("チーム未選択")
            return
            
        shihaika_count = len([p for p in self.current_team.players if not p.is_developmental])
        limit = self.MAX_SHIHAIKA
        color = self.theme.success if shihaika_count < limit else self.theme.danger
        
        self.team_info_label.setText(f"{self.current_team.name} | 支配下登録: <span style='color:{color}'>{shihaika_count}</span>/{limit}人")

    def _refresh_release_list(self):
        if not self.current_team: return
        
        # Registered players for release (exclude developmental? Or include?)
        # Conventionally, "Free Contract" applies to everyone, but separate tab handles dev promotion.
        # Let's show only Registered players here, as Development ones can be released too 
        # but maybe user wants to see them separately.
        # Since I have exact "Promotion" tab, I will keep "Release" for Registered.
        # Actually, let's include ALL players who CAN be released.
        # But if I show developmental players in "Release" tab, it overlaps with "Promotion" tab conceptually (listing players).
        # Let's stick to Registered Players in Release Tab.
        
        registered_players = [p for p in self.current_team.players if not p.is_developmental]
        # Keep same order (or let table sort)
        self.release_table.set_players(registered_players)

    def _refresh_promotion_list(self):
        if not self.current_team: return
        
        dev_players = [p for p in self.current_team.players if p.is_developmental]
        self.promo_table.set_players(dev_players)

    def _on_table_double_clicked(self, player):
        if player:
            self.player_detail_requested.emit(player)

    def _release_player(self, player: Player):
        """Release player to free agency"""
        if not self.current_team: return
        
        reply = QMessageBox.warning(self, "自由契約確認", 
            f"{player.name}選手を自由契約にしますか？\n"
            "チームから削除され、他球団が獲得できるようになります。\n"
            "（元に戻すことはできません）",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            try:
                if player not in self.current_team.players:
                    return
                    
                idx = self.current_team.players.index(player)
                
                # Remove from all specific rosters
                self.current_team.active_roster = [i for i in self.current_team.active_roster if i != idx]
                self.current_team.farm_roster = [i for i in self.current_team.farm_roster if i != idx]
                self.current_team.third_roster = [i for i in self.current_team.third_roster if i != idx]
                
                # Decrement indices
                self._decrement_indices(self.current_team.active_roster, idx)
                self._decrement_indices(self.current_team.farm_roster, idx)
                self._decrement_indices(self.current_team.third_roster, idx)
                
                self._decrement_indices(self.current_team.rotation, idx)
                self._decrement_indices(self.current_team.setup_pitchers, idx)
                self._decrement_indices(self.current_team.closers, idx)
                self._decrement_indices(self.current_team.current_lineup, idx)
                self._decrement_indices(self.current_team.farm_lineup, idx)
                self._decrement_indices(self.current_team.farm_rotation, idx)

                # Remove player
                self.current_team.players.pop(idx)
                
                # Add to free agents
                if self.game_state:
                    self.game_state.free_agents.append(player)
                    player.team_level = None
                
                QMessageBox.information(self, "自由契約", f"{player.name}を自由契約にしました。")
                self.refresh()
                
            except ValueError:
                QMessageBox.warning(self, "エラー", "選手の削除に失敗しました。")

    def _decrement_indices(self, idx_list: list, removed_idx: int):
        """Helper to shift indices after removal"""
        for i in range(len(idx_list)):
            if idx_list[i] > removed_idx:
                idx_list[i] -= 1

    def _promote_player(self, player: Player):
        if not self.current_team: return
        
        shihaika_count = len([p for p in self.current_team.players if not p.is_developmental])
        if shihaika_count >= self.MAX_SHIHAIKA:
             QMessageBox.warning(self, "登録枠超過", f"支配下登録枠({self.MAX_SHIHAIKA}人)が一杯です。")
             return

        reply = QMessageBox.question(self, "登録確認", 
            f"{player.name}選手を支配下登録しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            player.is_developmental = False
            
            # 背番号変更 (0-99の空き番号)
            import random
            used = set(p.uniform_number for p in self.current_team.players)
            candidates = [n for n in range(0, 100) if n not in used]
            if candidates:
                player.uniform_number = random.choice(candidates)
            
            # ニュースログ
            if self.game_state:
                self.game_state.log_news("TRANSACTION", f"{player.name}選手を支配下登録しました（背番号:{player.uniform_number}）", self.current_team.name)

            QMessageBox.information(self, "登録完了", f"{player.name}を支配下登録しました。\n新背番号: {player.uniform_number}")
            self.refresh()

