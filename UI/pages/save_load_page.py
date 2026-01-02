# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Save/Load Page
Angular Industrial Design matching Home Tab style
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QPushButton, QScrollArea, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

import os
import datetime

from UI.theme import get_theme
from UI.widgets.panels import ContentPanel


class SaveSlotCard(QFrame):
    """Angular save slot card matching home page industrial style"""
    load_requested = Signal(str)
    delete_requested = Signal(int)
    save_to_slot_requested = Signal(int)
    
    def __init__(self, slot_data: dict = None, slot_number: int = 1, 
                 allow_save: bool = True, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.slot_data = slot_data
        self.slot_number = slot_number
        self.filepath = slot_data.get("filepath") if slot_data else None
        self.allow_save = allow_save
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Angular design - no rounded corners
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left accent bar
        accent_color = self.theme.primary if self.slot_data else self.theme.bg_input
        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet(f"background: {accent_color}; border-radius: 0px;")
        layout.addWidget(accent)
        
        # Main content
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(16)
        
        # Slot number
        slot_label = QLabel(f"{self.slot_number:02d}")
        slot_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 800;
            color: {self.theme.primary if self.slot_data else self.theme.text_muted};
            font-family: 'Consolas', 'Monaco', monospace;
            min-width: 50px;
        """)
        content_layout.addWidget(slot_label)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        if self.slot_data:
            # Team name
            team_name = self.slot_data.get("team_name", "Unknown")
            team_label = QLabel(team_name)
            team_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: 700;
                color: {self.theme.text_primary};
                letter-spacing: 1px;
            """)
            info_layout.addWidget(team_label)
            
            # Details
            year = self.slot_data.get("year", 2027)
            date = self.slot_data.get("date", "")
            wins = self.slot_data.get("wins", 0)
            losses = self.slot_data.get("losses", 0)
            game_num = self.slot_data.get("game_number", 0)
            
            if self.slot_data.get("is_offseason"):
                detail_text = f"{year} OFFSEASON"
            else:
                detail_text = f"{year} | {date} | {wins}W-{losses}L | GAME {game_num}"
            
            detail_label = QLabel(detail_text)
            detail_label.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_secondary};
                letter-spacing: 1px;
            """)
            info_layout.addWidget(detail_label)
            
            # Modified time
            modified = self.slot_data.get("modified")
            if modified:
                mod_time = datetime.datetime.fromtimestamp(modified)
                time_label = QLabel(f"SAVED: {mod_time.strftime('%Y/%m/%d %H:%M')}")
                time_label.setStyleSheet(f"""
                    font-size: 9px;
                    color: {self.theme.text_muted};
                    letter-spacing: 1px;
                """)
                info_layout.addWidget(time_label)
        else:
            empty_label = QLabel("EMPTY SLOT")
            empty_label.setStyleSheet(f"""
                font-size: 14px;
                color: {self.theme.text_muted};
                letter-spacing: 2px;
            """)
            info_layout.addWidget(empty_label)
        
        content_layout.addLayout(info_layout, stretch=1)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        if self.slot_data:
            # Load button - WHITE background, BLACK text
            load_btn = QPushButton("LOAD")
            load_btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    color: black;
                    border: none;
                    border-radius: 0px;
                    padding: 10px 24px;
                    font-weight: 700;
                    font-size: 12px;
                    letter-spacing: 2px;
                }}
                QPushButton:hover {{
                    background: #e0e0e0;
                }}
            """)
            load_btn.clicked.connect(lambda: self.load_requested.emit(self.filepath))
            btn_layout.addWidget(load_btn)
            
            # Save/Overwrite button (only if save allowed)
            if self.allow_save:
                save_btn = QPushButton("SAVE")
                save_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.theme.bg_input};
                        color: {self.theme.text_secondary};
                        border: none;
                        border-radius: 0px;
                        padding: 10px 20px;
                        font-size: 11px;
                        letter-spacing: 1px;
                    }}
                    QPushButton:hover {{
                        background: {self.theme.success};
                        color: white;
                    }}
                """)
                save_btn.clicked.connect(lambda: self.save_to_slot_requested.emit(self.slot_number))
                btn_layout.addWidget(save_btn)
            
            # Delete button
            delete_btn = QPushButton("DELETE")
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {self.theme.text_muted};
                    border: 1px solid {self.theme.border};
                    border-radius: 0px;
                    padding: 8px 16px;
                    font-size: 10px;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background: {self.theme.danger};
                    color: white;
                    border-color: {self.theme.danger};
                }}
            """)
            delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.slot_number))
            btn_layout.addWidget(delete_btn)
        else:
            # Save to empty slot button (only if save allowed)
            if self.allow_save:
                save_btn = QPushButton("SAVE HERE")
                save_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.theme.success};
                        color: white;
                        border: none;
                        border-radius: 0px;
                        padding: 10px 24px;
                        font-weight: 700;
                        font-size: 12px;
                        letter-spacing: 2px;
                    }}
                    QPushButton:hover {{
                        background: {self.theme.success_light};
                    }}
                """)
                save_btn.clicked.connect(lambda: self.save_to_slot_requested.emit(self.slot_number))
                btn_layout.addWidget(save_btn)
        
        content_layout.addLayout(btn_layout)
        layout.addWidget(content)


class AutoSaveSlotCard(QFrame):
    """Autosave slot card - load only, no save/delete"""
    load_requested = Signal(str)
    
    def __init__(self, slot_data: dict = None, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.slot_data = slot_data
        self.filepath = slot_data.get("filepath") if slot_data else None
        self._setup_ui()
    
    def _setup_ui(self):
        # Angular design with distinct accent color for autosave
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left accent bar - Orange for autosave
        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet("background: #ff9800; border-radius: 0px;")
        layout.addWidget(accent)
        
        # Main content
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(16)
        
        # Slot label - "AUTO" instead of number
        slot_label = QLabel("AUTO")
        slot_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 800;
            color: #ff9800;
            font-family: 'Consolas', 'Monaco', monospace;
            min-width: 50px;
        """)
        content_layout.addWidget(slot_label)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        if self.slot_data:
            # Team name
            team_name = self.slot_data.get("team_name", "Unknown")
            team_label = QLabel(team_name)
            team_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: 700;
                color: {self.theme.text_primary};
                letter-spacing: 1px;
            """)
            info_layout.addWidget(team_label)
            
            # Details
            year = self.slot_data.get("year", 2027)
            date = self.slot_data.get("date", "")
            wins = self.slot_data.get("wins", 0)
            losses = self.slot_data.get("losses", 0)
            game_num = self.slot_data.get("game_number", 0)
            
            if self.slot_data.get("is_offseason"):
                detail_text = f"{year} OFFSEASON"
            else:
                detail_text = f"{year} | {date} | {wins}W-{losses}L | GAME {game_num}"
            
            detail_label = QLabel(detail_text)
            detail_label.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_secondary};
                letter-spacing: 1px;
            """)
            info_layout.addWidget(detail_label)
            
            # Modified time with "AUTOSAVE" label
            modified = self.slot_data.get("modified")
            if modified:
                mod_time = datetime.datetime.fromtimestamp(modified)
                time_label = QLabel(f"AUTOSAVED: {mod_time.strftime('%Y/%m/%d %H:%M')}")
                time_label.setStyleSheet(f"""
                    font-size: 9px;
                    color: #ff9800;
                    letter-spacing: 1px;
                """)
                info_layout.addWidget(time_label)
        else:
            empty_label = QLabel("NO AUTOSAVE DATA")
            empty_label.setStyleSheet(f"""
                font-size: 14px;
                color: {self.theme.text_muted};
                letter-spacing: 2px;
            """)
            info_layout.addWidget(empty_label)
        
        content_layout.addLayout(info_layout, stretch=1)
        
        # Buttons - LOAD only
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        if self.slot_data:
            # Load button - Orange accent to match autosave theme
            load_btn = QPushButton("LOAD")
            load_btn.setStyleSheet("""
                QPushButton {
                    background: #ff9800;
                    color: white;
                    border: none;
                    border-radius: 0px;
                    padding: 10px 24px;
                    font-weight: 700;
                    font-size: 12px;
                    letter-spacing: 2px;
                }
                QPushButton:hover {
                    background: #ffb74d;
                }
            """)
            load_btn.clicked.connect(lambda: self.load_requested.emit(self.filepath))
            btn_layout.addWidget(load_btn)
        
        content_layout.addLayout(btn_layout)
        layout.addWidget(content)

class SaveLoadPage(ContentPanel):
    """Save/Load page with angular industrial design"""
    
    save_requested = Signal()
    load_completed = Signal()
    back_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.save_dir = "saves"
        self.allow_save = True  # Title screen sets this to False
        self._setup_ui()
    
    def _setup_ui(self):
        # Header - Angular style
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(0)
        
        # Back button (hidden by default, only visible from title screen)
        self.back_btn = QPushButton("← BACK")
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
                padding: 10px 20px;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_card_hover};
                color: {self.theme.text_primary};
            }}
        """)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setVisible(False)  # Hidden by default
        header_layout.addWidget(self.back_btn)
        
        header_layout.addSpacing(20)
        
        # Title (no accent bar)
        title = QLabel("SAVE / LOAD")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 800;
            color: {self.theme.text_primary};
            letter-spacing: 4px;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Current game info
        self.current_info = QLabel("NO GAME LOADED")
        self.current_info.setStyleSheet(f"""
            font-size: 11px;
            color: {self.theme.text_muted};
            letter-spacing: 1px;
        """)
        header_layout.addWidget(self.current_info)
        
        self.add_widget(header)
        
        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {self.theme.border};")
        self.add_widget(sep)
        
        # Slots container with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 0px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.slots_widget = QWidget()
        self.slots_layout = QVBoxLayout(self.slots_widget)
        self.slots_layout.setSpacing(2)
        self.slots_layout.setContentsMargins(20, 16, 20, 24)
        
        scroll.setWidget(self.slots_widget)
        self.add_widget(scroll)
    
    def set_game_state(self, game_state):
        """Set game state reference"""
        self.game_state = game_state
        self._update_current_info()
        self._refresh_slots()
    
    def set_mode(self, allow_save: bool = True, show_back: bool = False):
        """Set page mode (title screen = load only, no save)"""
        self.allow_save = allow_save
        self.back_btn.setVisible(show_back)
        self._refresh_slots()
    
    def _update_current_info(self):
        """Update current game info display"""
        if self.game_state and self.game_state.player_team:
            info = self.game_state.get_save_info()
            team = info.get("team_name", "---")
            year = info.get("year", 2027)
            date = info.get("date", "")
            text = f"CURRENT: {team} | {year} | {date}"
            self.current_info.setText(text)
            self.current_info.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_secondary};
                letter-spacing: 1px;
            """)
        else:
            self.current_info.setText("NO GAME LOADED")
            self.current_info.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_muted};
                letter-spacing: 1px;
            """)
    
    def _refresh_slots(self):
        """Refresh save slot display"""
        # Clear existing
        while self.slots_layout.count():
            item = self.slots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get save slots
        from game_state import GameStateManager
        slots = GameStateManager.get_save_slots(self.save_dir)
        
        # Create slot map
        slot_map = {}
        for slot in slots:
            filename = slot.get("filename", "")
            try:
                if filename.startswith("slot_"):
                    num = int(filename.split("_")[1].split(".")[0])
                    slot_map[num] = slot
            except:
                pass
        
        # Display Autosave slot (slot 0) at top
        autosave_data = slot_map.get(0)
        autosave_card = AutoSaveSlotCard(autosave_data)
        autosave_card.load_requested.connect(self._on_load)
        self.slots_layout.addWidget(autosave_card)
        
        # Display 10 regular slots
        for i in range(1, 11):
            slot_data = slot_map.get(i)
            card = SaveSlotCard(slot_data, i, allow_save=self.allow_save)
            card.load_requested.connect(self._on_load)
            card.delete_requested.connect(self._on_delete)
            card.save_to_slot_requested.connect(self._on_save_to_slot)
            self.slots_layout.addWidget(card)
        
        self.slots_layout.addStretch()
    
    def _save_to_slot(self, slot_number: int, auto: bool = False):
        """Save to specific slot - used for autosave (slot 0)"""
        if not self.game_state:
            return False
        
        filepath = os.path.join(self.save_dir, f"slot_{slot_number:02d}.psav")
        return self.game_state.save_to_file(filepath)
    
    def _on_save_to_slot(self, slot_number: int):
        """Handle save to specific slot"""
        if not self.game_state:
            self.window().show_notification("エラー", "セーブするゲームデータがありません。", type="error")
            return
        
        if not self.allow_save:
            return
        
        # Check if slot has data (overwrite warning)
        from game_state import GameStateManager
        slots = GameStateManager.get_save_slots(self.save_dir)
        slot_exists = any(
            s.get("filename", "").startswith(f"slot_{slot_number:02d}")
            for s in slots
        )
        
        if slot_exists:
            result = QMessageBox.question(
                self, "上書き確認",
                f"スロット {slot_number} を上書きしますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return
        
        # Save
        filepath = os.path.join(self.save_dir, f"slot_{slot_number:02d}.psav")
        if self.game_state.save_to_file(filepath):
            self.window().show_notification("保存完了", f"スロット {slot_number} に保存しました。", type="success")
            self._refresh_slots()
        else:
            self.window().show_notification("エラー", "保存に失敗しました。", type="error")
    
    def _on_load(self, filepath: str):
        """Handle load request"""
        if not filepath:
            return
        
        result = QMessageBox.question(
            self, "ロード確認",
            "このデータをロードしますか？\n現在の進行状況は失われます。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        # Create new game state if needed
        if not self.game_state:
            from game_state import GameStateManager
            self.game_state = GameStateManager()
        
        if self.game_state.load_from_file(filepath):
            self.window().show_notification("ロード完了", "ゲームをロードしました。", type="success")
            self._update_current_info()
            self.load_completed.emit()
        else:
            self.window().show_notification("エラー", "ロードに失敗しました。", type="error")
    
    def _on_delete(self, slot_number: int):
        """Handle delete request"""
        if not slot_number: # Assuming 0 is not a valid slot for this context, or handle it
            return
        
        result = QMessageBox.question(
            self, "削除確認",
            f"スロット {slot_number} のデータを削除しますか？\nこの操作は取り消せません。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result == QMessageBox.Yes:

            
            # Simple delete
            try:
                slot_int = int(slot_number)
                filepath = os.path.join(self.save_dir, f"slot_{slot_int:02d}.psav")
                
                deleted = False
                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted = True
                
                # Also remove DB file from Hybrid Save
                db_path = filepath + ".db"
                if os.path.exists(db_path):
                    try: 
                        os.remove(db_path)
                        deleted = True
                    except: pass

                if deleted:
                    self.window().show_notification("削除完了", f"スロット {slot_number} を削除しました。", type="success")
                    self._refresh_slots()
                else:
                    self.window().show_notification("エラー", "削除するデータが見つかりませんでした。", type="warning")

            except Exception as e:
                self.window().show_notification("エラー", f"削除に失敗しました: {e}", type="error")
    
    def showEvent(self, event):
        """Refresh slots when page is shown"""
        super().showEvent(event)
        self._refresh_slots()
        self._update_current_info()
