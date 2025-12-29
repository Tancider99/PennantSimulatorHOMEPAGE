# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Edit Screen
Full-screen editor for team, player, and staff data
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QListWidget, QListWidgetItem, QStackedWidget,
    QGridLayout, QDoubleSpinBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QTextEdit,
    QInputDialog, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QPolygon
from PySide6.QtCore import QPoint

import os
import json
import shutil

from UI.theme import get_theme
from network_manager import network_manager
from UI.dialogs.preset_manager_dialog import PresetManagerDialog

class PresetPublishDialog(QDialog):
    """Dialog for publishing a preset"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プリセットの公開")
        self.setFixedWidth(400)
        self.theme = get_theme()
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary};")
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("プリセット名を入力")
        self.name_edit.setStyleSheet(f"background: {self.theme.bg_dark}; border: 1px solid {self.theme.border}; padding: 6px;")
        form_layout.addRow("プリセット名:", self.name_edit)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("説明を入力（任意）")
        self.desc_edit.setFixedHeight(100)
        self.desc_edit.setStyleSheet(f"background: {self.theme.bg_dark}; border: 1px solid {self.theme.border}; padding: 6px;")
        form_layout.addRow("説明:", self.desc_edit)
        
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("作成者名（任意）")
        self.author_edit.setStyleSheet(f"background: {self.theme.bg_dark}; border: 1px solid {self.theme.border}; padding: 6px;")
        form_layout.addRow("作成者:", self.author_edit)
        
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"background: {self.theme.bg_dark}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 8px 16px;")
        btn_layout.addWidget(cancel_btn)
        
        publish_btn = QPushButton("公開")
        publish_btn.clicked.connect(self.accept)
        publish_btn.setStyleSheet(f"background: {self.theme.primary}; color: #fff; border: none; padding: 8px 16px; font-weight: bold;")
        btn_layout.addWidget(publish_btn)
        
        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip() or "無名プリセット",
            "description": self.desc_edit.toPlainText().strip(),
            "author": self.author_edit.text().strip() or "Anonymous"
        }

class PresetLoadDialog(QDialog):
    """Dialog for confirming preset loading"""
    def __init__(self, metadata, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プリセットの読み込み確認")
        self.setFixedWidth(400)
        self.metadata = metadata
        self.theme = get_theme()
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary};")
        layout = QVBoxLayout(self)
        
        title_label = QLabel("以下のプリセットを読み込みますか？")
        title_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background: {self.theme.bg_dark}; border: 1px solid {self.theme.border}; border-radius: 4px;")
        info_layout = QVBoxLayout(info_frame)
        
        name_label = QLabel(f"名前: {self.metadata.get('name')}")
        name_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.theme.primary};")
        info_layout.addWidget(name_label)
        
        author_label = QLabel(f"作成者: {self.metadata.get('author')}")
        info_layout.addWidget(author_label)
        
        version_label = QLabel(f"バージョン: {self.metadata.get('version')}")
        info_layout.addWidget(version_label)
        
        desc = self.metadata.get('description')
        if desc:
            desc_label = QLabel(f"説明:\n{desc}")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"margin-top: 8px; color: {self.theme.text_secondary};")
            info_layout.addWidget(desc_label)
            
        layout.addWidget(info_frame)
        
        warn_label = QLabel("⚠️ 注意: 現在のデータはすべて上書きされます！")
        warn_label.setStyleSheet(f"color: {self.theme.error}; font-weight: bold; margin-top: 10px;")
        layout.addWidget(warn_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"background: {self.theme.bg_dark}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 8px 16px;")
        btn_layout.addWidget(cancel_btn)
        
        load_btn = QPushButton("読み込む")
        load_btn.clicked.connect(self.accept)
        load_btn.setStyleSheet(f"background: {self.theme.error}; color: #fff; border: none; padding: 8px 16px; font-weight: bold;")
        btn_layout.addWidget(load_btn)
        
        layout.addLayout(btn_layout)


class TriangleButton(QPushButton):
    """Triangle-shaped button for up/down controls"""
    def __init__(self, direction: str = "up", parent=None):
        super().__init__(parent)
        self.direction = direction  # "up" or "down"
        self.theme = get_theme()
        self.setFixedSize(36, 28)
        self.setCursor(Qt.PointingHandCursor)
        self._hovered = False
        self._pressed = False
        self.setStyleSheet("background: transparent; border: none;")
    
    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background (no hover effect - only pressed state changes color)
        if self._pressed:
            painter.fillRect(self.rect(), QColor(self.theme.primary_dark))
        else:
            painter.fillRect(self.rect(), QColor(self.theme.bg_card))
        
        # Draw triangle
        w, h = self.width(), self.height()
        cx = w // 2
        
        if self.direction == "up":
            # Up triangle: point at top
            triangle = QPolygon([
                QPoint(cx, 6),
                QPoint(cx - 10, h - 6),
                QPoint(cx + 10, h - 6)
            ])
        else:
            # Down triangle: point at bottom
            triangle = QPolygon([
                QPoint(cx, h - 6),
                QPoint(cx - 10, 6),
                QPoint(cx + 10, 6)
            ])
        
        painter.setBrush(QColor(self.theme.text_primary))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(triangle)


class TriangleSpinBox(QWidget):
    """Custom SpinBox with external triangle buttons"""
    valueChanged = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._value = 0
        self._min = 0
        self._max = 100
        self._step = 1
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Down button (left)
        self.down_btn = TriangleButton("down")
        self.down_btn.clicked.connect(self._decrement)
        layout.addWidget(self.down_btn)
        
        # Value display
        self.value_edit = QLineEdit()
        self.value_edit.setAlignment(Qt.AlignCenter)
        self.value_edit.setStyleSheet(f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 8px;
            font-size: 14px;
            font-weight: 600;
            min-width: 80px;
        """)
        self.value_edit.editingFinished.connect(self._on_edit_finished)
        layout.addWidget(self.value_edit)
        
        # Up button (right)
        self.up_btn = TriangleButton("up")
        self.up_btn.clicked.connect(self._increment)
        layout.addWidget(self.up_btn)
    
    def _increment(self):
        self.setValue(self._value + self._step)
    
    def _decrement(self):
        self.setValue(self._value - self._step)
    
    def _on_edit_finished(self):
        try:
            val = int(self.value_edit.text().replace(",", ""))
            self.setValue(val)
        except ValueError:
            self._update_display()
    
    def _update_display(self):
        self.value_edit.setText(f"{self._value:,}")
    
    def setValue(self, value: int):
        value = max(self._min, min(self._max, value))
        if value != self._value:
            self._value = value
            self._update_display()
            self.valueChanged.emit(self._value)
        elif self.value_edit.text() != f"{self._value:,}":
            self._update_display()
    
    def value(self) -> int:
        return self._value
    
    def setRange(self, min_val: int, max_val: int):
        self._min = min_val
        self._max = max_val
        self.setValue(self._value)
    
    def setSingleStep(self, step: int):
        self._step = step
    
    def setStyleSheet(self, style):
        # Only apply custom styling to value_edit if needed
        pass


class TriangleDoubleSpinBox(QWidget):
    """Custom DoubleSpinBox with external triangle buttons"""
    valueChanged = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._value = 0.0
        self._min = 0.0
        self._max = 100.0
        self._step = 0.01
        self._decimals = 2
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Down button (left)
        self.down_btn = TriangleButton("down")
        self.down_btn.clicked.connect(self._decrement)
        layout.addWidget(self.down_btn)
        
        # Value display
        self.value_edit = QLineEdit()
        self.value_edit.setAlignment(Qt.AlignCenter)
        self.value_edit.setStyleSheet(f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 8px;
            font-size: 14px;
            font-weight: 600;
            min-width: 60px;
        """)
        self.value_edit.editingFinished.connect(self._on_edit_finished)
        layout.addWidget(self.value_edit)
        
        # Up button (right)
        self.up_btn = TriangleButton("up")
        self.up_btn.clicked.connect(self._increment)
        layout.addWidget(self.up_btn)
    
    def _increment(self):
        self.setValue(self._value + self._step)
    
    def _decrement(self):
        self.setValue(self._value - self._step)
    
    def _on_edit_finished(self):
        try:
            val = float(self.value_edit.text())
            self.setValue(val)
        except ValueError:
            self._update_display()
    
    def _update_display(self):
        self.value_edit.setText(f"{self._value:.{self._decimals}f}")
    
    def setValue(self, value: float):
        value = round(max(self._min, min(self._max, value)), self._decimals)
        if abs(value - self._value) > 1e-9:
            self._value = value
            self._update_display()
            self.valueChanged.emit(self._value)
        elif self.value_edit.text() != f"{self._value:.{self._decimals}f}":
            self._update_display()
    
    def value(self) -> float:
        return self._value
    
    def setRange(self, min_val: float, max_val: float):
        self._min = min_val
        self._max = max_val
        self.setValue(self._value)
    
    def setSingleStep(self, step: float):
        self._step = step
    
    def setDecimals(self, decimals: int):
        self._decimals = decimals
        self._update_display()
    
    def setStyleSheet(self, style):
        # Only apply custom styling if needed
        pass


class SidebarButton(QPushButton):
    """Sidebar navigation button"""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._active = False
        self._update_style()
    
    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._update_style()
    
    def _update_style(self):
        theme = get_theme()
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: #ffffff;
                    color: #000000;
                    border: none;
                    padding: 12px 20px;
                    font-size: 13px;
                    font-weight: 600;
                    text-align: left;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {theme.text_muted};
                    border: none;
                    padding: 12px 20px;
                    font-size: 13px;
                    font-weight: 500;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {theme.bg_card};
                    color: {theme.text_primary};
                }}
            """)


class TeamEditorPanel(QWidget):
    """Team data editor panel"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_team = None
        self.team_data = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Team list (left)
        list_frame = QFrame()
        list_frame.setStyleSheet(f"background: {self.theme.bg_card};")
        list_frame.setFixedWidth(200)
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(8, 8, 8, 8)
        
        list_label = QLabel("チーム一覧")
        list_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary};")
        list_layout.addWidget(list_label)
        
        self.team_list = QListWidget()
        self.team_list.setStyleSheet(f"""
            QListWidget {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                border: none;
            }}
            QListWidget::item {{
                padding: 8px;
            }}
            QListWidget::item:selected {{
                background: {self.theme.primary};
            }}
        """)
        self.team_list.currentRowChanged.connect(self._on_team_selected)
        list_layout.addWidget(self.team_list)
        
        layout.addWidget(list_frame)
        
        # Editor panel (right)
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        editor_widget = QWidget()
        self.editor_layout = QVBoxLayout(editor_widget)
        self.editor_layout.setContentsMargins(16, 16, 16, 16)
        self.editor_layout.setSpacing(16)
        
        # Team name
        name_group = self._create_group("チーム情報")
        name_grid = QGridLayout()
        name_grid.setSpacing(8)
        
        name_grid.addWidget(QLabel("チーム名:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(self._input_style())
        name_grid.addWidget(self.name_edit, 0, 1)
        
        name_grid.addWidget(QLabel("略称:"), 1, 0)
        self.abbr_edit = QLineEdit()
        self.abbr_edit.setStyleSheet(self._input_style())
        name_grid.addWidget(self.abbr_edit, 1, 1)
        
        name_grid.addWidget(QLabel("カラー:"), 2, 0)
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#FF6600")
        self.color_edit.setStyleSheet(self._input_style())
        name_grid.addWidget(self.color_edit, 2, 1)
        
        name_group.layout().addLayout(name_grid)
        self.editor_layout.addWidget(name_group)
        
        # Stadium info
        stadium_group = self._create_group("球場情報")
        stadium_grid = QGridLayout()
        stadium_grid.setSpacing(8)
        
        stadium_grid.addWidget(QLabel("球場名:"), 0, 0)
        self.stadium_name = QLineEdit()
        self.stadium_name.setStyleSheet(self._input_style())
        stadium_grid.addWidget(self.stadium_name, 0, 1)
        
        stadium_grid.addWidget(QLabel("収容人数:"), 1, 0)
        self.capacity_spin = TriangleSpinBox()
        self.capacity_spin.setRange(10000, 100000)
        self.capacity_spin.setSingleStep(1000)
        stadium_grid.addWidget(self.capacity_spin, 1, 1)
        
        stadium_grid.addWidget(QLabel("ドーム:"), 2, 0)
        self.dome_check = QCheckBox("ドーム球場")
        self.dome_check.setStyleSheet(f"color: {self.theme.text_primary};")
        stadium_grid.addWidget(self.dome_check, 2, 1)
        
        stadium_group.layout().addLayout(stadium_grid)
        self.editor_layout.addWidget(stadium_group)
        
        # Park factors
        pf_group = self._create_group("パークファクター")
        pf_grid = QGridLayout()
        pf_grid.setSpacing(8)
        
        self.pf_spins = {}
        pf_labels = [("HR", "pf_hr"), ("得点", "pf_runs"), ("単打", "pf_1b"), 
                     ("二塁打", "pf_2b"), ("三塁打", "pf_3b"), ("三振", "pf_so"), ("四球", "pf_bb")]
        
        for i, (label, key) in enumerate(pf_labels):
            row, col = divmod(i, 4)
            pf_grid.addWidget(QLabel(f"{label}:"), row, col * 2)
            spin = TriangleDoubleSpinBox()
            spin.setRange(0.5, 2.0)
            spin.setSingleStep(0.01)
            spin.setDecimals(3)
            spin.setValue(1.0)
            pf_grid.addWidget(spin, row, col * 2 + 1)
            self.pf_spins[key] = spin
        
        pf_group.layout().addLayout(pf_grid)
        self.editor_layout.addWidget(pf_group)
        
        # Fan data (ファン層編集)
        fan_group = self._create_group("ファン層")
        fan_grid = QGridLayout()
        fan_grid.setSpacing(8)
        
        fan_grid.addWidget(QLabel("ライト層:"), 0, 0)
        self.light_fans_spin = TriangleSpinBox()
        self.light_fans_spin.setRange(10000, 5000000)
        self.light_fans_spin.setSingleStep(10000)
        self.light_fans_spin.setValue(300000)
        fan_grid.addWidget(self.light_fans_spin, 0, 1)
        
        fan_grid.addWidget(QLabel("ミドル層:"), 0, 2)
        self.middle_fans_spin = TriangleSpinBox()
        self.middle_fans_spin.setRange(5000, 2000000)
        self.middle_fans_spin.setSingleStep(5000)
        self.middle_fans_spin.setValue(150000)
        fan_grid.addWidget(self.middle_fans_spin, 0, 3)
        
        fan_grid.addWidget(QLabel("コア層:"), 1, 0)
        self.core_fans_spin = TriangleSpinBox()
        self.core_fans_spin.setRange(1000, 500000)
        self.core_fans_spin.setSingleStep(1000)
        self.core_fans_spin.setValue(50000)
        fan_grid.addWidget(self.core_fans_spin, 1, 1)
        
        # Total fans display
        self.total_fans_label = QLabel("総ファン数: 500,000人")
        self.total_fans_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {self.theme.text_secondary};")
        fan_grid.addWidget(self.total_fans_label, 1, 2, 1, 2)
        
        # Connect signals to update total
        self.light_fans_spin.valueChanged.connect(self._update_total_fans)
        self.middle_fans_spin.valueChanged.connect(self._update_total_fans)
        self.core_fans_spin.valueChanged.connect(self._update_total_fans)
        
        fan_group.layout().addLayout(fan_grid)
        self.editor_layout.addWidget(fan_group)
        
        self.editor_layout.addStretch()
        
        editor_scroll.setWidget(editor_widget)
        layout.addWidget(editor_scroll, 1)
    
    def _update_total_fans(self):
        """Update total fans display"""
        total = self.light_fans_spin.value() + self.middle_fans_spin.value() + self.core_fans_spin.value()
        self.total_fans_label.setText(f"総ファン数: {total:,}人")
    
    def _create_group(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        
        label = QLabel(title)
        label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.primary};")
        layout.addWidget(label)
        return frame
    
    def _input_style(self) -> str:
        return f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 6px;
        """
    
    def _spinbox_style(self) -> str:
        """Enhanced SpinBox style with larger, visible up/down buttons"""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 8px 12px;
                padding-right: 40px;
                font-size: 14px;
                font-weight: 600;
                min-height: 28px;
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 32px;
                height: 18px;
                border: none;
                border-left: 1px solid {self.theme.border};
                border-bottom: 1px solid {self.theme.border};
                background: {self.theme.bg_card};
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
                background: {self.theme.primary};
            }}
            QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
                background: {self.theme.primary_dark};
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 32px;
                height: 18px;
                border: none;
                border-left: 1px solid {self.theme.border};
                background: {self.theme.bg_card};
            }}
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {self.theme.primary};
            }}
            QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
                background: {self.theme.primary_dark};
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                width: 14px;
                height: 14px;
                border: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-bottom: 6px solid {self.theme.text_primary};
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                width: 14px;
                height: 14px;
                border: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 6px solid {self.theme.text_primary};
            }}
        """
    
    def load_teams(self):
        """Load team data from files"""
        from team_data_manager import TeamDataManager
        self.team_list.clear()
        self.team_data = {}
        
        data_dir = TeamDataManager.DATA_DIR
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.endswith("_team.json"):
                    team_name = filename.replace("_team.json", "").replace("_", " ")
                    filepath = os.path.join(data_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        self.team_data[team_name] = data
                        self.team_list.addItem(team_name)
                    except Exception:
                        pass
    
    def _on_team_selected(self, row: int):
        if row < 0:
            return
        
        team_name = self.team_list.item(row).text()
        self.current_team = team_name
        data = self.team_data.get(team_name, {})
        
        # Load basic info
        self.name_edit.setText(data.get("球団名", team_name))
        self.abbr_edit.setText(data.get("略称", ""))
        self.color_edit.setText(data.get("色", ""))
        
        # Load stadium info
        stadium = data.get("球場", {})
        if stadium:
            self.stadium_name.setText(stadium.get("名前", ""))
            self.capacity_spin.setValue(stadium.get("収容人数", 35000))
            self.dome_check.setChecked(stadium.get("ドーム", False))
            
            pf = stadium.get("パークファクター", {})
            pf_mapping = {"pf_hr": "HR", "pf_runs": "得点", "pf_1b": "単打",
                          "pf_2b": "二塁打", "pf_3b": "三塁打", "pf_so": "三振", "pf_bb": "四球"}
            for key, label in pf_mapping.items():
                if key in self.pf_spins:
                    self.pf_spins[key].setValue(pf.get(label, 1.0))
        
        # Load fan data
        fan_data = data.get("ファン", {})
        if fan_data:
            self.light_fans_spin.setValue(fan_data.get("ライト層", 300000))
            self.middle_fans_spin.setValue(fan_data.get("ミドル層", 150000))
            self.core_fans_spin.setValue(fan_data.get("コア層", 50000))
        else:
            # Try to get from TEAM_CONFIGS
            from team_data_manager import get_team_config
            config = get_team_config(team_name)
            fans = config.get("fans", {})
            self.light_fans_spin.setValue(fans.get("light", 300000))
            self.middle_fans_spin.setValue(fans.get("middle", 150000))
            self.core_fans_spin.setValue(fans.get("core", 50000))
        self._update_total_fans()
    
    def save_current_team(self):
        """Save current team data - preserves original fields"""
        if not self.current_team:
            return
        
        old_name = self.current_team
        new_name = self.name_edit.text().strip()
        
        # Start with original data to preserve fields like リーグ, 予算
        data = self.team_data.get(old_name, {}).copy()
        
        # Update editable fields
        data["球団名"] = new_name
        data["略称"] = self.abbr_edit.text()
        data["色"] = self.color_edit.text()
        
        # Ensure required fields exist
        if "リーグ" not in data:
            data["リーグ"] = "North League"  # Default
        if "予算" not in data:
            data["予算"] = 5000000000
        
        data["球場"] = {
            "名前": self.stadium_name.text(),
            "収容人数": self.capacity_spin.value(),
            "ドーム": self.dome_check.isChecked(),
            "パークファクター": {
                "HR": self.pf_spins["pf_hr"].value(),
                "得点": self.pf_spins["pf_runs"].value(),
                "単打": self.pf_spins["pf_1b"].value(),
                "二塁打": self.pf_spins["pf_2b"].value(),
                "三塁打": self.pf_spins["pf_3b"].value(),
                "三振": self.pf_spins["pf_so"].value(),
                "四球": self.pf_spins["pf_bb"].value()
            }
        }
        
        # Save fan data
        data["ファン"] = {
            "ライト層": self.light_fans_spin.value(),
            "ミドル層": self.middle_fans_spin.value(),
            "コア層": self.core_fans_spin.value()
        }
        
        # Save to file
        from team_data_manager import TeamDataManager
        data_dir = TeamDataManager.DATA_DIR
        
        # If name changed, rename related files first
        if old_name != new_name:
            self._rename_team_files(old_name, new_name)
        
        # Save updated team data
        safe_name = new_name.replace(" ", "_").replace("/", "_")
        filepath = os.path.join(data_dir, f"{safe_name}_team.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.team_data[new_name] = data
        if old_name != new_name and old_name in self.team_data:
            del self.team_data[old_name]
        
        self.current_team = new_name
        self.load_teams()
    
    def _rename_team_files(self, old_name: str, new_name: str):
        """Rename all team-related files and update team name inside them"""
        from team_data_manager import TeamDataManager
        from player_data_manager import PlayerDataManager
        
        old_safe = old_name.replace(" ", "_").replace("/", "_")
        new_safe = new_name.replace(" ", "_").replace("/", "_")
        
        # Rename team_data file
        old_team = os.path.join(TeamDataManager.DATA_DIR, f"{old_safe}_team.json")
        new_team = os.path.join(TeamDataManager.DATA_DIR, f"{new_safe}_team.json")
        if os.path.exists(old_team):
            os.rename(old_team, new_team)
        
        # Rename player_data file and update team name inside
        old_player = os.path.join(PlayerDataManager.DATA_DIR, f"{old_safe}_player.json")
        new_player = os.path.join(PlayerDataManager.DATA_DIR, f"{new_safe}_player.json")
        if os.path.exists(old_player):
            # Update team name inside file
            try:
                with open(old_player, 'r', encoding='utf-8') as f:
                    player_data = json.load(f)
                if "球団名" in player_data:
                    player_data["球団名"] = new_name
                with open(old_player, 'w', encoding='utf-8') as f:
                    json.dump(player_data, f, ensure_ascii=False, indent=2)
            except:
                pass
            os.rename(old_player, new_player)
        
        # Rename staff_data file and update team name inside
        from UI.pages.staff_page import get_staff_data_path
        old_staff = get_staff_data_path(old_name)
        new_staff = get_staff_data_path(new_name)
        if os.path.exists(old_staff):
            try:
                with open(old_staff, 'r', encoding='utf-8') as f:
                    staff_data = json.load(f)
                if "team_name" in staff_data:
                    staff_data["team_name"] = new_name
                with open(old_staff, 'w', encoding='utf-8') as f:
                    json.dump(staff_data, f, ensure_ascii=False, indent=2)
            except:
                pass
            os.rename(old_staff, new_staff)


class PlayerEditorPanel(QWidget):
    """Player data editor panel"""
    
    # Player count limits (支配下選手)
    MIN_PITCHERS = 15  # 最低支配下投手数
    MIN_BATTERS = 16   # 最低支配下野手数
    MAX_PLAYERS = 70   # 最大支配下選手数
    MAX_IKUSEI = 50    # 最大育成選手数
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_team = None
        self.current_player_idx = -1
        self.players_data = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Left panel: Team and Player list
        list_frame = QFrame()
        list_frame.setStyleSheet(f"background: {self.theme.bg_card};")
        list_frame.setFixedWidth(250)
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(8, 8, 8, 8)
        
        # Team selector
        team_label = QLabel("チーム選択")
        team_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary};")
        list_layout.addWidget(team_label)
        
        self.team_combo = QComboBox()
        self.team_combo.setStyleSheet(self._input_style())
        self.team_combo.currentTextChanged.connect(self._on_team_changed)
        list_layout.addWidget(self.team_combo)
        
        # Player list
        player_label = QLabel("選手一覧")
        player_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary}; margin-top: 10px;")
        list_layout.addWidget(player_label)
        
        self.player_list = QListWidget()
        self.player_list.setStyleSheet(f"""
            QListWidget {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                border: none;
            }}
            QListWidget::item {{
                padding: 4px;
            }}
            QListWidget::item:selected {{
                background: {self.theme.primary};
            }}
        """)
        self.player_list.currentRowChanged.connect(self._on_player_selected)
        list_layout.addWidget(self.player_list)
        
        # Player count label
        self.player_count_label = QLabel("選手数: 0")
        self.player_count_label.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; margin-top: 4px;")
        list_layout.addWidget(self.player_count_label)
        
        # Add/Delete buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        self.add_player_btn = QPushButton("追加")
        self.add_player_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.success};
                color: white;
                border: none;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #33cc66;
            }}
            QPushButton:disabled {{
                background: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.add_player_btn.clicked.connect(self._add_player)
        btn_layout.addWidget(self.add_player_btn)
        
        self.delete_player_btn = QPushButton("削除")
        self.delete_player_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.error};
                color: white;
                border: none;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #ff4444;
            }}
            QPushButton:disabled {{
                background: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.delete_player_btn.clicked.connect(self._delete_player)
        btn_layout.addWidget(self.delete_player_btn)
        
        list_layout.addLayout(btn_layout)
        
        layout.addWidget(list_frame)
        
        # Right panel: Player editor
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        editor_widget = QWidget()
        self.editor_layout = QVBoxLayout(editor_widget)
        self.editor_layout.setContentsMargins(16, 16, 16, 16)
        self.editor_layout.setSpacing(12)
        
        # Basic info
        basic_group = self._create_group("基本情報")
        basic_grid = QGridLayout()
        basic_grid.setSpacing(6)
        
        basic_grid.addWidget(QLabel("名前:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(self._input_style())
        basic_grid.addWidget(self.name_edit, 0, 1)
        
        basic_grid.addWidget(QLabel("背番号:"), 0, 2)
        self.number_spin = TriangleSpinBox()
        self.number_spin.setRange(0, 999)
        basic_grid.addWidget(self.number_spin, 0, 3)
        
        basic_grid.addWidget(QLabel("年齢:"), 1, 0)
        self.age_spin = TriangleSpinBox()
        self.age_spin.setRange(16, 50)
        basic_grid.addWidget(self.age_spin, 1, 1)
        
        basic_grid.addWidget(QLabel("年俸:"), 1, 2)
        self.salary_spin = TriangleSpinBox()
        self.salary_spin.setRange(0, 1000000000)
        self.salary_spin.setSingleStep(1000000)
        basic_grid.addWidget(self.salary_spin, 1, 3)
        
        basic_group.layout().addLayout(basic_grid)
        self.editor_layout.addWidget(basic_group)
        
        # Batter Stats
        batter_group = self._create_group("野手能力")
        batter_grid = QGridLayout()
        batter_grid.setSpacing(6)
        
        self.stat_spins = {}
        batter_stats = [("ミート", "ミート"), ("パワー", "パワー"), ("走力", "走力"), 
                        ("肩力", "肩力"), ("守備", "守備"), ("捕球", "捕球"),
                        ("選球眼", "選球眼"), ("チャンス", "チャンス"), ("ギャップ", "ギャップ"),
                        ("三振回避", "三振回避"), ("盗塁", "盗塁"), ("走塁", "走塁"),
                        ("バント", "バント"), ("セーフティ", "セーフティ"), ("弾道", "弾道"),
                        ("対左投手", "対左投手"), ("捕手リード", "捕手リード")]
        
        for i, (label, key) in enumerate(batter_stats):
            row, col = divmod(i, 4)
            batter_grid.addWidget(QLabel(f"{label}:"), row, col * 2)
            spin = TriangleSpinBox()
            if key == "弾道":
                spin.setRange(1, 5)
                spin.setValue(2)
            else:
                spin.setRange(1, 99)
                spin.setValue(50)
            batter_grid.addWidget(spin, row, col * 2 + 1)
            self.stat_spins[key] = spin
        
        batter_group.layout().addLayout(batter_grid)
        self.editor_layout.addWidget(batter_group)
        
        # Pitcher stats
        pitcher_group = self._create_group("投手能力")
        pitcher_grid = QGridLayout()
        pitcher_grid.setSpacing(6)
        
        pitcher_stats = [("球速", "球速"), ("スタミナ", "スタミナ"), 
                         ("対左打者", "対左打者"), ("対ピンチ", "対ピンチ"),
                         ("安定感", "安定感"), ("ゴロ傾向", "ゴロ傾向"), ("クイック", "クイック")]
        
        for i, (label, key) in enumerate(pitcher_stats):
            row, col = divmod(i, 4)
            pitcher_grid.addWidget(QLabel(f"{label}:"), row, col * 2)
            spin = TriangleSpinBox()
            if key == "球速":
                spin.setRange(100, 170)
                spin.setValue(145)
            else:
                spin.setRange(1, 99)
                spin.setValue(50)
            pitcher_grid.addWidget(spin, row, col * 2 + 1)
            self.stat_spins[key] = spin
        
        pitcher_group.layout().addLayout(pitcher_grid)
        self.editor_layout.addWidget(pitcher_group)
        
        # Common stats
        common_group = self._create_group("共通能力")
        common_grid = QGridLayout()
        common_grid.setSpacing(6)
        
        common_stats = [("ケガしにくさ", "ケガしにくさ"), ("回復", "回復"), 
                        ("練習態度", "練習態度"), ("野球脳", "野球脳"), ("メンタル", "メンタル")]
        
        for i, (label, key) in enumerate(common_stats):
            row, col = divmod(i, 4)
            common_grid.addWidget(QLabel(f"{label}:"), row, col * 2)
            spin = TriangleSpinBox()
            spin.setRange(1, 99)
            spin.setValue(50)
            common_grid.addWidget(spin, row, col * 2 + 1)
            self.stat_spins[key] = spin
        
        common_group.layout().addLayout(common_grid)
        self.editor_layout.addWidget(common_group)
        
        # Per-Pitch Stats Section
        pitch_group = self._create_group("球種別能力")
        pitch_layout = QVBoxLayout()
        
        # Pitch selector row with add/delete buttons
        pitch_select = QHBoxLayout()
        pitch_select.addWidget(QLabel("球種:"))
        self.pitch_combo = QComboBox()
        self.pitch_combo.setStyleSheet(self._input_style())
        self.pitch_combo.setMinimumWidth(120)
        self.pitch_combo.currentTextChanged.connect(self._on_pitch_type_selected)
        pitch_select.addWidget(self.pitch_combo)
        
        # Add pitch button
        add_pitch_btn = QPushButton("+")
        add_pitch_btn.setFixedSize(28, 28)
        add_pitch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.success}; color: white;
                border: none; border-radius: 4px; font-weight: bold; font-size: 16px;
            }}
            QPushButton:hover {{ background: {self.theme.success}cc; }}
        """)
        add_pitch_btn.clicked.connect(self._add_pitch_type)
        pitch_select.addWidget(add_pitch_btn)
        
        # Delete pitch button
        del_pitch_btn = QPushButton("-")
        del_pitch_btn.setFixedSize(28, 28)
        del_pitch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.danger}; color: white;
                border: none; border-radius: 4px; font-weight: bold; font-size: 16px;
            }}
            QPushButton:hover {{ background: {self.theme.danger}cc; }}
        """)
        del_pitch_btn.clicked.connect(self._delete_pitch_type)
        pitch_select.addWidget(del_pitch_btn)
        
        pitch_select.addStretch()
        pitch_layout.addLayout(pitch_select)
        
        # Per-pitch spinboxes
        pitch_stats_grid = QGridLayout()
        pitch_stats_grid.setSpacing(6)
        
        self.pitch_spins = {}
        pitch_stat_items = [("制球", "control"), ("球威", "stuff"), ("変化量", "movement")]
        
        for i, (label, key) in enumerate(pitch_stat_items):
            pitch_stats_grid.addWidget(QLabel(f"{label}:"), 0, i * 2)
            spin = TriangleSpinBox()
            spin.setRange(1, 99)
            spin.setValue(50)
            pitch_stats_grid.addWidget(spin, 0, i * 2 + 1)
            self.pitch_spins[key] = spin
        
        pitch_layout.addLayout(pitch_stats_grid)
        pitch_group.layout().addLayout(pitch_layout)
        self.editor_layout.addWidget(pitch_group)
        
        self.editor_layout.addStretch()
        
        editor_scroll.setWidget(editor_widget)
        layout.addWidget(editor_scroll, 1)
    
    def _create_group(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        label = QLabel(title)
        label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.primary};")
        layout.addWidget(label)
        return frame
    
    def _input_style(self) -> str:
        return f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 4px;
        """
    
    def load_teams(self):
        """Load team list"""
        from team_data_manager import TeamDataManager
        self.team_combo.clear()
        
        data_dir = TeamDataManager.DATA_DIR
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.endswith("_team.json"):
                    team_name = filename.replace("_team.json", "").replace("_", " ")
                    self.team_combo.addItem(team_name)
    
    def _on_team_changed(self, team_name: str):
        """Load players for selected team"""
        from player_data_manager import PlayerDataManager
        self.current_team = team_name
        self.player_list.clear()
        self.players_data = []
        self.current_player_idx = -1
        
        if not team_name:
            self._update_player_count()
            return
        
        safe_name = team_name.replace(" ", "_").replace("/", "_")
        filepath = os.path.join(PlayerDataManager.DATA_DIR, f"{safe_name}_player.json")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.players_data = data.get("選手一覧", [])
                for p in self.players_data:
                    name = p.get("名前", "不明")
                    pos = p.get("ポジション", "不明")
                    num = p.get("背番号", 0)
                    self.player_list.addItem(f"#{num} {name} ({pos})")
            except Exception:
                pass
        
        self._update_player_count()
    
    def _on_player_selected(self, row: int):
        """Load player data into editor"""
        if row < 0 or row >= len(self.players_data):
            return
        
        self.current_player_idx = row
        p = self.players_data[row]
        
        self.name_edit.setText(p.get("名前", ""))
        self.number_spin.setValue(p.get("背番号", 0))
        self.age_spin.setValue(p.get("年齢", 25))
        self.salary_spin.setValue(p.get("年俸", 10000000))
        
        stats = p.get("能力値", {})
        common = p.get("共通能力", {})
        
        for key, spin in self.stat_spins.items():
            # Check common abilities first, then stats
            if key in common:
                val = common.get(key, 50)
            else:
                val = stats.get(key, 50)
            
            if key == "球速":
                val = stats.get(key, 145)
            elif key == "弾道":
                val = stats.get(key, 2)
            
            spin.setValue(val if isinstance(val, int) else 50)
        
        # Load pitch types into combo - pitches are in 能力値.持ち球
        self.pitch_combo.blockSignals(True)
        self.pitch_combo.clear()
        stats = p.get("能力値", {})
        pitches = stats.get("持ち球", {}) or {}
        if pitches:
            for pitch_name in pitches.keys():
                self.pitch_combo.addItem(pitch_name)
        else:
            self.pitch_combo.addItem("ストレート")
        self.pitch_combo.blockSignals(False)
        
        # Trigger load of first pitch
        if self.pitch_combo.count() > 0:
            self._on_pitch_type_selected(self.pitch_combo.currentText())
    
    def _on_pitch_type_selected(self, pitch_name: str):
        """Load per-pitch stats for selected pitch type"""
        if self.current_player_idx < 0 or not pitch_name:
            return
        
        p = self.players_data[self.current_player_idx]
        stats = p.get("能力値", {})
        pitches = stats.get("持ち球", {}) or {}
        pitch_data = pitches.get(pitch_name, {})
        
        if isinstance(pitch_data, dict):
            self.pitch_spins["control"].setValue(pitch_data.get("control", 50))
            self.pitch_spins["stuff"].setValue(pitch_data.get("stuff", 50))
            self.pitch_spins["movement"].setValue(pitch_data.get("movement", 50))
        elif isinstance(pitch_data, int):
            # Old format - just one value
            for spin in self.pitch_spins.values():
                spin.setValue(pitch_data)
        else:
            for spin in self.pitch_spins.values():
                spin.setValue(50)
    
    def _add_pitch_type(self):
        """Add a new pitch type to the current player"""
        if self.current_player_idx < 0:
            return
        
        p = self.players_data[self.current_player_idx]
        stats = p.get("能力値", {})
        pitches = stats.get("持ち球", {}) or {}
        
        # Check max limit (10 pitches)
        if len(pitches) >= 10:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "エラー", "球種は最大10個までです。")
            return
        
        # Available pitch types
        all_pitches = ["ストレート", "スライダー", "カーブ", "フォーク", "チェンジアップ", 
                       "カットボール", "シンカー", "ツーシーム", "シュート", "ナックル",
                       "スプリット", "パーム", "スクリュー", "ナックルカーブ", "スラッター"]
        
        # Filter available pitches
        available = [pt for pt in all_pitches if pt not in pitches]
        
        if not available:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "エラー", "追加可能な球種がありません。")
            return
        
        from PySide6.QtWidgets import QInputDialog
        pitch_type, ok = QInputDialog.getItem(self, "球種追加", "追加する球種を選択:", available, 0, False)
        
        if ok and pitch_type:
            # Add new pitch type with default values
            if "能力値" not in p:
                p["能力値"] = {}
            if "持ち球" not in p["能力値"]:
                p["能力値"]["持ち球"] = {}
            
            p["能力値"]["持ち球"][pitch_type] = {
                "control": 50,
                "stuff": 50,
                "movement": 50
            }
            
            # Refresh pitch combo
            self.pitch_combo.blockSignals(True)
            self.pitch_combo.addItem(pitch_type)
            self.pitch_combo.setCurrentText(pitch_type)
            self.pitch_combo.blockSignals(False)
            self._on_pitch_type_selected(pitch_type)
    
    def _delete_pitch_type(self):
        """Delete the currently selected pitch type"""
        if self.current_player_idx < 0:
            return
        
        pitch_name = self.pitch_combo.currentText()
        if not pitch_name:
            return
        
        p = self.players_data[self.current_player_idx]
        stats = p.get("能力値", {})
        pitches = stats.get("持ち球", {}) or {}
        
        # Check min limit (1 pitch required)
        if len(pitches) <= 1:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "エラー", "球種は最低1つ必要です。")
            return
        
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "確認", 
                                      f"「{pitch_name}」を削除しますか？",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Remove pitch type
            if "能力値" in p and "持ち球" in p["能力値"]:
                if pitch_name in p["能力値"]["持ち球"]:
                    del p["能力値"]["持ち球"][pitch_name]
            
            # Refresh pitch combo
            self.pitch_combo.blockSignals(True)
            idx = self.pitch_combo.findText(pitch_name)
            if idx >= 0:
                self.pitch_combo.removeItem(idx)
            self.pitch_combo.blockSignals(False)
            
            # Select first available pitch
            if self.pitch_combo.count() > 0:
                self._on_pitch_type_selected(self.pitch_combo.currentText())
    
    def _save_current_player(self):
        """Save current player changes"""
        if self.current_player_idx < 0 or not self.current_team:
            return
        
        p = self.players_data[self.current_player_idx]
        p["名前"] = self.name_edit.text()
        p["背番号"] = self.number_spin.value()
        p["年齢"] = self.age_spin.value()
        p["年俸"] = self.salary_spin.value()
        
        if "能力値" not in p:
            p["能力値"] = {}
        if "共通能力" not in p:
            p["共通能力"] = {}
        
        common_keys = {"ケガしにくさ", "回復", "練習態度", "野球脳", "メンタル"}
        
        for key, spin in self.stat_spins.items():
            if key in common_keys:
                p["共通能力"][key] = spin.value()
            else:
                p["能力値"][key] = spin.value()
        
        # Save current pitch stats to 能力値.持ち球
        pitch_name = self.pitch_combo.currentText()
        if pitch_name:
            if "持ち球" not in p["能力値"]:
                p["能力値"]["持ち球"] = {}
            if pitch_name not in p["能力値"]["持ち球"]:
                p["能力値"]["持ち球"][pitch_name] = {}
            
            if isinstance(p["能力値"]["持ち球"][pitch_name], dict):
                p["能力値"]["持ち球"][pitch_name]["control"] = self.pitch_spins["control"].value()
                p["能力値"]["持ち球"][pitch_name]["stuff"] = self.pitch_spins["stuff"].value()
                p["能力値"]["持ち球"][pitch_name]["movement"] = self.pitch_spins["movement"].value()
            else:
                # Convert old format to dict
                p["能力値"]["持ち球"][pitch_name] = {
                    "control": self.pitch_spins["control"].value(),
                    "stuff": self.pitch_spins["stuff"].value(),
                    "movement": self.pitch_spins["movement"].value()
                }
        
        # Save to file - preserve original structure
        from player_data_manager import PlayerDataManager
        safe_name = self.current_team.replace(" ", "_").replace("/", "_")
        filepath = os.path.join(PlayerDataManager.DATA_DIR, f"{safe_name}_player.json")
        
        # Read original file to preserve metadata
        original_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
            except:
                pass
        
        original_data["選手一覧"] = self.players_data
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)
        
        # Refresh list
        self._on_team_changed(self.current_team)
    
    def save_all_players(self):
        """Save all player changes - called from main save"""
        # First update current player data from UI
        self._save_current_player()
    
    def _update_player_count(self):
        """Update the player count label and button states"""
        count = len(self.players_data)
        
        # Count by position
        pitcher_count = sum(1 for p in self.players_data if p.get("ポジション") == "投手")
        batter_count = count - pitcher_count
        
        self.player_count_label.setText(f"選手: {count} (投{pitcher_count}/野{batter_count})")
        
        # Update button states
        self.add_player_btn.setEnabled(count < self.MAX_PLAYERS)
        # Delete enabled only if above minimum for that position
        can_delete = False
        if self.current_player_idx >= 0 and self.current_player_idx < len(self.players_data):
            current_pos = self.players_data[self.current_player_idx].get("ポジション", "")
            if current_pos == "投手":
                can_delete = pitcher_count > self.MIN_PITCHERS
            else:
                can_delete = batter_count > self.MIN_BATTERS
        self.delete_player_btn.setEnabled(can_delete)
    
    def _add_player(self):
        """Add a new player to the team"""
        if not self.current_team:
            return
        
        if len(self.players_data) >= self.MAX_PLAYERS:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "制限", f"選手数が最大({self.MAX_PLAYERS}人)に達しています。")
            return
        
        # Create default player data
        new_number = self._get_next_available_number()
        new_player = {
            "名前": "新規選手",
            "背番号": new_number,
            "年齢": 20,
            "年俸": 5000000,
            "ポジション": "野手",
            "能力値": {
                "ミート": 40, "パワー": 40, "走力": 40,
                "肩力": 40, "守備": 40, "捕球": 40,
                "選球眼": 40, "チャンス": 40, "ギャップ": 40,
                "三振回避": 40, "盗塁": 40, "走塁": 40,
                "バント": 40, "セーフティ": 40, "弾道": 2,
                "対左投手": 40, "捕手リード": 40,
                "球速": 140, "スタミナ": 40,
                "対左打者": 40, "対ピンチ": 40,
                "安定感": 40, "ゴロ傾向": 50, "クイック": 40
            },
            "共通能力": {
                "ケガしにくさ": 50, "回復": 50,
                "練習態度": 50, "野球脳": 50, "メンタル": 50
            }
        }
        
        self.players_data.append(new_player)
        self._save_players_to_file()
        self._on_team_changed(self.current_team)
        
        # Select the new player
        self.player_list.setCurrentRow(len(self.players_data) - 1)
    
    def _delete_player(self):
        """Delete the currently selected player"""
        if not self.current_team or self.current_player_idx < 0:
            return
        
        # Check position-based limits
        from PySide6.QtWidgets import QMessageBox
        current_player = self.players_data[self.current_player_idx]
        current_pos = current_player.get("ポジション", "")
        
        pitcher_count = sum(1 for p in self.players_data if p.get("ポジション") == "投手")
        batter_count = len(self.players_data) - pitcher_count
        
        if current_pos == "投手" and pitcher_count <= self.MIN_PITCHERS:
            QMessageBox.warning(self, "制限", f"投手が最低({self.MIN_PITCHERS}人)に達しています。")
            return
        elif current_pos != "投手" and batter_count <= self.MIN_BATTERS:
            QMessageBox.warning(self, "制限", f"野手が最低({self.MIN_BATTERS}人)に達しています。")
            return
        
        # Confirmation dialog
        from PySide6.QtWidgets import QMessageBox
        player_name = self.players_data[self.current_player_idx].get("名前", "不明")
        result = QMessageBox.question(
            self, "選手削除",
            f"「{player_name}」を削除しますか？\nこの操作は取り消せません。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
        
        del self.players_data[self.current_player_idx]
        self._save_players_to_file()
        self._on_team_changed(self.current_team)
        
        # Select previous player or first one
        new_idx = min(self.current_player_idx, len(self.players_data) - 1)
        if new_idx >= 0:
            self.player_list.setCurrentRow(new_idx)
    
    def _get_next_available_number(self) -> int:
        """Get the next available uniform number"""
        used_numbers = {p.get("背番号", 0) for p in self.players_data}
        for num in range(1, 100):
            if num not in used_numbers:
                return num
        return 99
    
    def _save_players_to_file(self):
        """Save current players data to file"""
        if not self.current_team:
            return
        
        from player_data_manager import PlayerDataManager
        safe_name = self.current_team.replace(" ", "_").replace("/", "_")
        filepath = os.path.join(PlayerDataManager.DATA_DIR, f"{safe_name}_player.json")
        
        # Read original file to preserve metadata
        original_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
            except:
                pass
        
        original_data["選手一覧"] = self.players_data
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)


class StaffEditorPanel(QWidget):
    """Staff data editor panel"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_team = None
        self.staff_data = []
        self.current_staff_idx = -1
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Left panel
        list_frame = QFrame()
        list_frame.setStyleSheet(f"background: {self.theme.bg_card};")
        list_frame.setFixedWidth(250)
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(8, 8, 8, 8)
        
        # Team selector
        team_label = QLabel("チーム選択")
        team_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary};")
        list_layout.addWidget(team_label)
        
        self.team_combo = QComboBox()
        self.team_combo.setStyleSheet(self._input_style())
        self.team_combo.currentTextChanged.connect(self._on_team_changed)
        list_layout.addWidget(self.team_combo)
        
        # Staff list
        staff_label = QLabel("スタッフ一覧")
        staff_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary}; margin-top: 10px;")
        list_layout.addWidget(staff_label)
        
        self.staff_list = QListWidget()
        self.staff_list.setStyleSheet(f"""
            QListWidget {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                border: none;
            }}
            QListWidget::item {{ padding: 4px; }}
            QListWidget::item:selected {{ background: {self.theme.primary}; }}
        """)
        self.staff_list.currentRowChanged.connect(self._on_staff_selected)
        list_layout.addWidget(self.staff_list)
        
        layout.addWidget(list_frame)
        
        # Right panel
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        editor_widget = QWidget()
        self.editor_layout = QVBoxLayout(editor_widget)
        self.editor_layout.setContentsMargins(16, 16, 16, 16)
        self.editor_layout.setSpacing(12)
        
        # Staff info
        info_group = self._create_group("スタッフ情報")
        info_grid = QGridLayout()
        info_grid.setSpacing(6)
        
        info_grid.addWidget(QLabel("名前:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setStyleSheet(self._input_style())
        info_grid.addWidget(self.name_edit, 0, 1)
        
        info_grid.addWidget(QLabel("役職:"), 1, 0)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["監督", "ヘッドコーチ", "バッティングコーチ", "ピッチングコーチ", 
                                   "守備コーチ", "走塁コーチ", "ブルペンコーチ", "スカウト"])
        self.role_combo.setStyleSheet(self._input_style())
        info_grid.addWidget(self.role_combo, 1, 1)
        
        info_grid.addWidget(QLabel("能力:"), 2, 0)
        self.ability_spin = TriangleSpinBox()
        self.ability_spin.setRange(1, 99)
        self.ability_spin.setValue(50)
        info_grid.addWidget(self.ability_spin, 2, 1)
        
        info_group.layout().addLayout(info_grid)
        self.editor_layout.addWidget(info_group)
        
        self.editor_layout.addStretch()
        editor_scroll.setWidget(editor_widget)
        layout.addWidget(editor_scroll, 1)
    
    def _create_group(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        label = QLabel(title)
        label.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.primary};")
        layout.addWidget(label)
        return frame
    
    def _input_style(self) -> str:
        return f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 4px;
        """
    
    def load_teams(self):
        from team_data_manager import TeamDataManager
        self.team_combo.clear()
        data_dir = TeamDataManager.DATA_DIR
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.endswith("_team.json"):
                    team_name = filename.replace("_team.json", "").replace("_", " ")
                    self.team_combo.addItem(team_name)
    
    def _on_team_changed(self, team_name: str):
        self.current_team = team_name
        self.staff_list.clear()
        self.staff_data = []
        
        if not team_name:
            return
        
        # Load staff data from staff_data folder - use same naming as staff_page.py
        from UI.pages.staff_page import get_staff_data_path
        filepath = get_staff_data_path(team_name)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Staff data uses staff_slots array
                staff_slots = data.get("staff_slots", [])
                self.staff_data = []
                
                for i, slot in enumerate(staff_slots):
                    if slot is not None:
                        staff_entry = {
                            "index": i,
                            "名前": slot.get("name", "不明"),
                            "役職": slot.get("role", "不明"),
                            "能力": slot.get("ability", 50),
                            "slot_data": slot  # Keep original data
                        }
                        self.staff_data.append(staff_entry)
                        self.staff_list.addItem(f"{staff_entry['名前']} ({staff_entry['役職']})")
            except Exception:
                pass
    
    def _on_staff_selected(self, row: int):
        if row < 0 or row >= len(self.staff_data):
            return
        
        self.current_staff_idx = row
        s = self.staff_data[row]
        
        self.name_edit.setText(s.get("名前", ""))
        role = s.get("役職", "監督")
        idx = self.role_combo.findText(role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        self.ability_spin.setValue(s.get("能力", 50))
    
    def _save_current_staff(self):
        if self.current_staff_idx < 0 or not self.current_team:
            return
        
        s = self.staff_data[self.current_staff_idx]
        s["名前"] = self.name_edit.text()
        s["役職"] = self.role_combo.currentText()
        s["能力"] = self.ability_spin.value()
        
        # Update slot_data
        if "slot_data" in s:
            s["slot_data"]["name"] = s["名前"]
            s["slot_data"]["ability"] = s["能力"]
        
        # Reload and update file
        from UI.pages.staff_page import get_staff_data_path
        filepath = get_staff_data_path(self.current_team)
        
        # Read original file
        original_data = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
            except:
                pass
        
        # Update staff_slots with modified data
        staff_slots = original_data.get("staff_slots", [])
        for entry in self.staff_data:
            idx = entry.get("index", -1)
            if 0 <= idx < len(staff_slots) and staff_slots[idx] is not None:
                staff_slots[idx]["name"] = entry["名前"]
                staff_slots[idx]["ability"] = entry["能力"]
        
        original_data["staff_slots"] = staff_slots
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)
        
        self._on_team_changed(self.current_team)
    
    def save_all_staff(self):
        """Save all staff changes - called from main save"""
        # First update current staff data from UI
        self._save_current_staff()

class NameEditorPanel(QWidget):
    """Editor for league and postseason names"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.editors = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("名称設定")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.theme.text_primary};")
        layout.addWidget(header)
        
        # Form Container
        form_frame = QFrame()
        form_frame.setStyleSheet(f"background: {self.theme.bg_card}; border-radius: 8px;")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(16)
        
        # Define fields
        self.fields = [
            ("North League", "North League 名前"),
            ("South League", "South League 名前"),
            ("Japan Series", "グランドチャンピオンシップ名称"),
            ("CS First", "ファーストステージ 名前"),
            ("CS Final", "ファイナルステージ 名前")
        ]
        
        for key, label_text in self.fields:
            row = QVBoxLayout()
            row.setSpacing(4)
            
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 13px;")
            
            edit = QLineEdit()
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background: {self.theme.bg_input};
                    color: {self.theme.text_primary};
                    border: 1px solid {self.theme.border};
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 14px;
                }}
                QLineEdit:focus {{
                    border-color: {self.theme.primary};
                }}
            """)
            self.editors[key] = edit
            
            row.addWidget(lbl)
            row.addWidget(edit)
            form_layout.addLayout(row)
            
        layout.addWidget(form_frame)
        layout.addStretch()

    def load_data(self, game_state):
        self.game_state = game_state
        if not game_state:
            return
            
        # Ensure dict exists if loading from old save
        if not hasattr(game_state, 'league_names'):
            game_state.league_names = {
                "North League": "North League",
                "South League": "South League",
                "Japan Series": "グランドチャンピオンシップ",
                "CS First": "CS First Stage",
                "CS Final": "CS Final Stage"
            }
            
        for key, edit in self.editors.items():
            if key in game_state.league_names:
                edit.setText(game_state.league_names[key])
    
    def save_data(self):
        if not self.game_state:
            return
        
        # Make sure dict exists
        if not hasattr(self.game_state, 'league_names'):
            self.game_state.league_names = {}
            
        for key, edit in self.editors.items():
            self.game_state.league_names[key] = edit.text()
            
        # Write to user_config.json for immediate persistence
        import json
        import os
        config_path = "user_config.json"
        try:
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['league_names'] = self.game_state.league_names
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Config save failed: {e}")
class EditScreen(QWidget):
    """Full-screen edit mode interface"""
    
    back_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self._setup_ui()
    
    def set_game_state(self, game_state):
        """Set game state reference for reloading data"""
        self.game_state = game_state
    
    def reload_game_state_teams(self):
        """Reload team and player data from files into game_state"""
        if not self.game_state:
            return
        
        from team_generator import load_or_create_teams
        
        # Get current team names from files
        from team_data_manager import team_data_manager
        teams_info = team_data_manager.get_all_teams_from_files()
        north_names = [name for name, _ in teams_info["north"]]
        south_names = [name for name, _ in teams_info["south"]]
        
        # Reload teams with updated data
        north_teams, south_teams = load_or_create_teams(north_names, south_names)
        
        # Update game_state with new teams
        self.game_state.north_teams = north_teams
        self.game_state.south_teams = south_teams
        self.game_state.all_teams = north_teams + south_teams
        # Note: game_state.teams is a read-only property that returns all_teams
        
        # Update player_team reference if it exists
        if self.game_state.player_team:
            player_team_name = self.game_state.player_team.name
            for team in self.game_state.all_teams:
                if team.name == player_team_name:
                    self.game_state.player_team = team
                    break
        
    
    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_dark};")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet(f"background: {self.theme.bg_card}; border-right: 1px solid {self.theme.border};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Logo
        logo = QLabel("EDIT MODE")
        logo.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {self.theme.primary};
            padding: 20px;
            letter-spacing: 2px;
        """)
        sidebar_layout.addWidget(logo)
        
        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {self.theme.border};")
        sidebar_layout.addWidget(sep)
        
        # Navigation buttons
        self.team_btn = SidebarButton("チームデータ")
        self.team_btn.clicked.connect(lambda: self._switch_panel(0))
        sidebar_layout.addWidget(self.team_btn)
        
        self.player_btn = SidebarButton("選手データ")
        self.player_btn.clicked.connect(lambda: self._switch_panel(1))
        sidebar_layout.addWidget(self.player_btn)
        
        self.staff_btn = SidebarButton("スタッフデータ")
        self.staff_btn.clicked.connect(lambda: self._switch_panel(2))
        sidebar_layout.addWidget(self.staff_btn)
        
        self.name_btn = SidebarButton("名称データ")
        self.name_btn.clicked.connect(lambda: self._switch_panel(3))
        sidebar_layout.addWidget(self.name_btn)
        
        sidebar_layout.addStretch()
        
        # Action buttons
        self.reset_btn = QPushButton("デフォルトに戻す")
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.error};
                color: white;
                border: none;
                padding: 10px 16px;
                font-weight: 600;
                margin: 8px;
            }}
            QPushButton:hover {{
                background: #ff4444;
            }}
        """)
        self.reset_btn.clicked.connect(self._on_reset)
        sidebar_layout.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.success};
                color: white;
                border: none;
                padding: 10px 16px;
                font-weight: 600;
                margin: 8px;
            }}
            QPushButton:hover {{
                background: #33cc66;
            }}
        """)
        self.save_btn.clicked.connect(self._on_save)
        sidebar_layout.addWidget(self.save_btn)
        
        # Preset Manager Button (moved before back button)
        preset_sep = QFrame()
        preset_sep.setFixedHeight(1)
        preset_sep.setStyleSheet(f"background: {self.theme.border}; margin: 8px 0;")
        sidebar_layout.addWidget(preset_sep)

        self.preset_mgr_btn = QPushButton("プリセットマネージャー")
        self.preset_mgr_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_card};
                color: {self.theme.primary};
                border: 1px solid {self.theme.primary};
                padding: 10px 12px;
                font-weight: 600;
                margin: 6px 8px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: #ffffff;
                color: #000000;
            }}
        """)
        self.preset_mgr_btn.clicked.connect(self._open_preset_manager)
        sidebar_layout.addWidget(self.preset_mgr_btn)
        
        self.back_btn = QPushButton("戻る")
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_muted};
                border: 1px solid {self.theme.border};
                padding: 10px 16px;
                font-weight: 600;
                margin: 8px;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_card};
                color: {self.theme.text_primary};
            }}
        """)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        sidebar_layout.addWidget(self.back_btn)
        
        layout.addWidget(sidebar)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        self.team_panel = TeamEditorPanel()
        self.player_panel = PlayerEditorPanel()
        self.staff_panel = StaffEditorPanel()
        self.name_panel = NameEditorPanel()
        
        self.content_stack.addWidget(self.team_panel)
        self.content_stack.addWidget(self.player_panel)
        self.content_stack.addWidget(self.staff_panel)
        self.content_stack.addWidget(self.name_panel)
        
        layout.addWidget(self.content_stack, 1)
        
        # Initial state
        self._switch_panel(0)
    def _switch_panel(self, index: int):
        self.content_stack.setCurrentIndex(index)
        
        self.team_btn.set_active(index == 0)
        self.player_btn.set_active(index == 1)
        self.staff_btn.set_active(index == 2)
        self.name_btn.set_active(index == 3)
    
    def load_data(self):
        """Load all data when entering edit mode"""
        self.team_panel.load_teams()
        self.player_panel.load_teams()
        self.staff_panel.load_teams()
        self.name_panel.load_data(self.game_state)
    
    def _on_save(self):
        """Save all changes to data files"""
        # Save team data (handles file renaming if name changed)
        self.team_panel.save_current_team()
        
        # Save player data
        self.player_panel.save_all_players()
        
        # Save staff data
        self.staff_panel.save_all_staff()
        
        # Save name data
        self.name_panel.save_data()
        
        # Reload all data
        self.load_data()
        
        # Reload game_state teams if available
        self.reload_game_state_teams()
        
        QMessageBox.information(self, "保存完了", "データを保存しました。")
    
    def _on_reset(self):
        """Reset all data to saved defaults"""
        from team_data_manager import team_data_manager
        from player_data_manager import player_data_manager
        from UI.pages.staff_page import reset_staff_to_default, has_staff_default_data
        
        # Check if default data exists
        has_team_default = team_data_manager.has_default_data()
        has_player_default = player_data_manager.has_default_data()
        has_staff_default = has_staff_default_data()
        
        if not (has_team_default or has_player_default or has_staff_default):
            reply = QMessageBox.question(
                self, "デフォルトデータがありません",
                "保存されたデフォルトデータがありません。\n現在のデータをデフォルトとして保存しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                team_data_manager.save_default_data()
                player_data_manager.save_default_data()
                from UI.pages.staff_page import save_staff_default_data
                save_staff_default_data()
                QMessageBox.information(self, "保存完了", "現在のデータをデフォルトとして保存しました。")
            return
        
        reply = QMessageBox.question(
            self, "確認",
            "すべてのデータをデフォルトに戻しますか？\n編集内容は失われます。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset all data to defaults
            success_count = 0
            if has_team_default:
                team_data_manager.reset_to_default()
                success_count += 1
            if has_player_default:
                player_data_manager.reset_to_default()
                success_count += 1
            if has_staff_default:
                reset_staff_to_default()
                success_count += 1
            
            # Reload UI data
            self.load_data()
            
            # Reload game_state teams if available
            self.reload_game_state_teams()
            
            QMessageBox.information(self, "完了", "データをデフォルトに戻しました。")
    
    def _save_current_as_default(self):
        """Save current data as default"""
        from team_data_manager import team_data_manager
        from player_data_manager import player_data_manager
        from UI.pages.staff_page import save_staff_default_data
        
        reply = QMessageBox.question(
            self, "確認",
            "現在のデータをデフォルトとして保存しますか？\n既存のデフォルトデータは上書きされます。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            team_data_manager.save_default_data()
            player_data_manager.save_default_data()
            save_staff_default_data()
            QMessageBox.information(self, "保存完了", "現在のデータをデフォルトとして保存しました。")
            
    def _open_preset_manager(self):
        """Open the unified Preset Manager Dialog"""
        # Save current state first to ensure latest data
        self.team_panel.save_current_team()
        self.player_panel.save_all_players()
        self.staff_panel.save_all_staff()
        
        dialog = PresetManagerDialog(
            self, 
            current_data_callback=self._collect_all_data_from_files,
            load_callback=self._apply_preset_data
        )
        dialog.exec()
        
        # After dialog closes, reload data in case something was loaded
        self.load_data()
        self.reload_game_state_teams()

    def _collect_all_data_from_files(self):
        """Collect all team, player, and staff data from files"""
        from team_data_manager import TeamDataManager
        from player_data_manager import PlayerDataManager

        
        data = {
            "teams": {},
            "players": {},
            "staff": {}
        }
        
        # Teams
        if os.path.exists(TeamDataManager.DATA_DIR):
            for filename in os.listdir(TeamDataManager.DATA_DIR):
                if filename.endswith("_team.json"):
                    with open(os.path.join(TeamDataManager.DATA_DIR, filename), 'r', encoding='utf-8') as f:
                        t_data = json.load(f)
                        data["teams"][filename] = t_data
        
        # Players
        if os.path.exists(PlayerDataManager.DATA_DIR):
            for filename in os.listdir(PlayerDataManager.DATA_DIR):
                if filename.endswith("_player.json"):
                    with open(os.path.join(PlayerDataManager.DATA_DIR, filename), 'r', encoding='utf-8') as f:
                        p_data = json.load(f)
                        data["players"][filename] = p_data

        # Staff
        # Staff data is stored in staff_data directory, similar to teams
        staff_dir = "staff_data"
        if os.path.exists(staff_dir):
            for filename in os.listdir(staff_dir):
                if filename.endswith(".json"):
                    with open(os.path.join(staff_dir, filename), 'r', encoding='utf-8') as f:
                        s_data = json.load(f)
                        data["staff"][filename] = s_data
                        
        return data

    def _apply_preset_data(self, data):
        """Apply preset data to files"""
        # Backup? Maybe later. For now overwrite.
        
        from team_data_manager import TeamDataManager
        from player_data_manager import PlayerDataManager
        
        # Clear existing directories first to avoid orphaned files? 
        # Ideally yes, but risky. Let's just overwrite/add.
        # Actually proper "Preset Load" usually implies a clean slate.
        # Let's delete existing JSONs in data dirs to match the preset exactly.
        
        # Helper to clear dir
        def clear_json_files(directory):
            if os.path.exists(directory):
                for f in os.listdir(directory):
                    if f.endswith(".json"):
                        os.remove(os.path.join(directory, f))
        
        # Ensure dirs exist
        os.makedirs(TeamDataManager.DATA_DIR, exist_ok=True)
        os.makedirs(PlayerDataManager.DATA_DIR, exist_ok=True)
        os.makedirs("staff_data", exist_ok=True)
        
        # Clear
        clear_json_files(TeamDataManager.DATA_DIR)
        clear_json_files(PlayerDataManager.DATA_DIR)
        clear_json_files("staff_data")
        
        # Write Teams
        for filename, content in data.get("teams", {}).items():
            with open(os.path.join(TeamDataManager.DATA_DIR, filename), 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
                
        # Write Players
        for filename, content in data.get("players", {}).items():
            with open(os.path.join(PlayerDataManager.DATA_DIR, filename), 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
                
        # Write Staff
        for filename, content in data.get("staff", {}).items():
            with open(os.path.join("staff_data", filename), 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)

