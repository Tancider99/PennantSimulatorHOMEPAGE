# -*- coding: utf-8 -*-
"""
ゲーム起動用ロード画面
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import QTimer, Qt

class GameLoadingScreen(QWidget):
    def __init__(self, on_complete=None, parent=None):
        super().__init__(parent)
        self.on_complete = on_complete
        self._setup_ui()
        self._start_loading()

    def _setup_ui(self):
        # 高級感のあるグラデーション背景
        self.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #232a36, stop:0.5 #181c22, stop:1 #232a36);")
        # 中央ロゴ削除

    def resizeEvent(self, event):
        super().resizeEvent(event)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 中央は空白
        main_layout.addStretch(1)

        # 下部エリア
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(48, 24, 48, 48)
        bottom_layout.setSpacing(0)

        # 左下ロゴ（シンプル＆高級感）
        self.logo_label = QLabel("PENNANT SIMULATOR")
        self.logo_label.setStyleSheet("font-size: 26px; font-weight: 700; letter-spacing: 5px; color: #e0e4ea; font-family: 'Segoe UI', 'Yu Gothic UI'; text-shadow: 0px 2px 8px #222;")
        self.logo_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        bottom_layout.addWidget(self.logo_label, alignment=Qt.AlignLeft | Qt.AlignBottom)

        # 右下ロードバー（スタイリッシュ）
        right_box = QVBoxLayout()
        right_box.setSpacing(8)
        right_box.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False) # Hide percent text
        self.progress_bar.setFixedWidth(340)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #232a36;
                border: 2px solid #bfc4d1;
                border-radius: 0px;
                height: 18px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e0e4ea, stop:0.5 #bfc4d1, stop:1 #e0e4ea);
                border-radius: 0px;
                margin: 0px;
            }
        """)
        right_box.addWidget(self.progress_bar)
        self.message_label = QLabel("Initializing...")
        self.message_label.setStyleSheet("font-size: 14px; color: #bfc4d1; font-family: 'Segoe UI', 'Yu Gothic UI';")
        self.message_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        right_box.addWidget(self.message_label)
        bottom_layout.addStretch(1)
        bottom_layout.addLayout(right_box)

        main_layout.addLayout(bottom_layout)

    def _start_loading(self):
        self.progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(40)
        self.messages = [
            "Initializing...",
            "Loading assets...",
            "Preparing teams...",
            "Generating players...",
            "Setting up game state...",
            "Finalizing..."
        ]

    def _update_progress(self):
        self.progress += 2
        self.progress_bar.setValue(self.progress)
        msg_idx = min(len(self.messages)-1, self.progress // 20)
        self.message_label.setText(self.messages[msg_idx])
        if self.progress >= 100:
            self.timer.stop()
            if self.on_complete:
                self.on_complete()
