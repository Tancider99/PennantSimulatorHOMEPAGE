# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Offseason Page
Full-screen offseason event management page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from UI.theme import get_theme
from UI.widgets.cards import Card


class OffseasonPage(QWidget):
    """オフシーズン専用フルスクリーンページ"""
    
    back_requested = Signal()  # ホームに戻る
    advance_requested = Signal()  # 次のイベントに進む
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self._setup_ui()
    
    def _setup_ui(self):
        """UIのセットアップ"""
        self.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # ヘッダー
        header = self._create_header()
        layout.addWidget(header)
        
        # メインコンテンツ
        content = self._create_content()
        layout.addWidget(content, 1)
        
        # フッター（ボタン）
        footer = self._create_footer()
        layout.addWidget(footer)
    
    def _create_header(self) -> QWidget:
        """ヘッダーを作成"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {self.theme.primary}, stop:1 {self.theme.accent_blue});
                border-radius: 16px;
                padding: 20px;
            }}
        """)
        layout = QVBoxLayout(header)
        layout.setContentsMargins(30, 20, 30, 20)
        
        # タイトル
        self.title_label = QLabel("OFFSEASON")
        self.title_label.setStyleSheet(f"""
            font-size: 48px;
            font-weight: bold;
            color: white;
            background: transparent;
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 現在のフェーズ
        self.phase_label = QLabel("契約更改")
        self.phase_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.9);
            background: transparent;
        """)
        self.phase_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.phase_label)
        
        # 日付
        self.date_label = QLabel("2027年11月18日")
        self.date_label.setStyleSheet(f"""
            font-size: 16px;
            color: rgba(255, 255, 255, 0.7);
            background: transparent;
        """)
        self.date_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.date_label)
        
        return header
    
    def _create_content(self) -> QWidget:
        """メインコンテンツを作成"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # イベントスケジュールカード
        schedule_card = self._create_schedule_card()
        layout.addWidget(schedule_card)
        
        # ニュースカード
        news_card = self._create_news_card()
        layout.addWidget(news_card)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def _create_schedule_card(self) -> QWidget:
        """イベントスケジュールカードを作成"""
        card = Card()
        card.setMinimumHeight(300)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # タイトル (Stylish, no emoji)
        title_row = QHBoxLayout()
        
        # Icon replacement: styled frame
        icon_frame = QFrame()
        icon_frame.setFixedSize(28, 28)
        icon_frame.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.theme.primary}, stop:1 {self.theme.accent_blue});
            border-radius: 6px;
        """)
        icon_label = QLabel("S")
        icon_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon_label)
        title_row.addWidget(icon_frame)
        
        title = QLabel("OFFSEASON SCHEDULE")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.text_primary};
            background: transparent;
            letter-spacing: 1px;
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)
        
        # イベントリスト
        self.events_container = QVBoxLayout()
        self.events_container.setSpacing(10)
        layout.addLayout(self.events_container)
        
        card.add_widget(container)
        return card
    
    def _create_news_card(self) -> QWidget:
        """ニュースカードを作成"""
        card = Card()
        card.setMinimumHeight(200)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # タイトル (Stylish, no emoji)
        title_row = QHBoxLayout()
        
        # Icon replacement: styled frame
        icon_frame = QFrame()
        icon_frame.setFixedSize(28, 28)
        icon_frame.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.theme.success}, stop:1 {self.theme.primary});
            border-radius: 6px;
        """)
        icon_label = QLabel("N")
        icon_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon_label)
        title_row.addWidget(icon_frame)
        
        title = QLabel("LATEST NEWS")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.theme.text_primary};
            background: transparent;
            letter-spacing: 1px;
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)
        
        # ニュースコンテナ
        self.news_container = QVBoxLayout()
        self.news_container.setSpacing(5)
        layout.addLayout(self.news_container)
        
        layout.addStretch()
        
        card.add_widget(container)
        return card
    
    def _create_footer(self) -> QWidget:
        """フッター（ボタン）を作成"""
        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 戻るボタン
        back_btn = QPushButton("← ホームに戻る")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(50)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_input};
            }}
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(back_btn)
        
        layout.addStretch()
        
        # 進むボタン
        self.advance_btn = QPushButton("次のイベントへ →")
        self.advance_btn.setCursor(Qt.PointingHandCursor)
        self.advance_btn.setFixedHeight(60)
        self.advance_btn.setMinimumWidth(250)
        self.advance_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary}, stop:1 {self.theme.accent_blue});
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                padding: 0 40px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary_hover}, stop:1 {self.theme.accent_blue});
            }}
        """)
        self.advance_btn.clicked.connect(self.advance_requested.emit)
        layout.addWidget(self.advance_btn)
        
        return footer
    
    def set_game_state(self, game_state):
        """ゲーム状態を設定してUIを更新"""
        self.game_state = game_state
        
        if not game_state:
            return
        
        # フェーズを更新
        if hasattr(game_state, 'offseason_phase') and game_state.offseason_phase:
            self.phase_label.setText(game_state.offseason_phase.value)
            self.advance_btn.setText(f"次へ: {game_state.offseason_phase.value}")
        
        # 日付を更新
        if hasattr(game_state, 'current_date') and game_state.current_date:
            try:
                import datetime
                date = datetime.datetime.strptime(game_state.current_date, "%Y-%m-%d")
                self.date_label.setText(f"{date.year}年{date.month}月{date.day}日")
            except:
                self.date_label.setText(game_state.current_date)
        
        # イベントスケジュールを更新
        self._update_events_list()
        
        # ニュースを更新
        self._update_news_list()
    
    def _update_events_list(self):
        """イベントリストを更新"""
        # 既存の項目をクリア
        while self.events_container.count():
            item = self.events_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.game_state or not hasattr(self.game_state, 'offseason_events_schedule'):
            return
        
        events = self.game_state.offseason_events_schedule or []
        current_phase = getattr(self.game_state, 'offseason_phase', None)
        
        for event_date, phase in events:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            
            # 日付
            date_str = event_date.strftime("%m/%d") if hasattr(event_date, 'strftime') else str(event_date)
            date_label = QLabel(date_str)
            date_label.setStyleSheet(f"""
                font-size: 14px;
                color: {self.theme.text_secondary};
                background: transparent;
                min-width: 60px;
            """)
            row_layout.addWidget(date_label)
            
            # フェーズ名
            phase_name = phase.value if hasattr(phase, 'value') else str(phase)
            phase_label = QLabel(phase_name)
            
            # 現在のフェーズはハイライト
            is_current = current_phase and phase == current_phase
            if is_current:
                phase_label.setStyleSheet(f"""
                    font-size: 16px;
                    font-weight: bold;
                    color: {self.theme.primary};
                    background: rgba({int(self.theme.primary[1:3], 16)}, {int(self.theme.primary[3:5], 16)}, {int(self.theme.primary[5:7], 16)}, 0.1);
                    padding: 5px 15px;
                    border-radius: 5px;
                """)
            else:
                phase_label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {self.theme.text_primary};
                    background: transparent;
                """)
            
            row_layout.addWidget(phase_label, 1)
            
            # ステータスインジケータ (Stylish, no emoji)
            status_frame = QFrame()
            status_frame.setFixedSize(12, 12)
            if is_current:
                status_frame.setStyleSheet(f"""
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {self.theme.primary}, stop:1 {self.theme.accent_blue});
                    border-radius: 6px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                """)
            else:
                status_frame.setStyleSheet(f"""
                    background: {self.theme.bg_input};
                    border-radius: 6px;
                    border: 1px solid {self.theme.border};
                """)
            row_layout.addWidget(status_frame)
            
            self.events_container.addWidget(row)
    
    def _update_news_list(self):
        """ニュースリストを更新"""
        # 既存の項目をクリア
        while self.news_container.count():
            item = self.news_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.game_state or not hasattr(self.game_state, 'news_feed'):
            return
        
        news_list = self.game_state.news_feed[:10] if self.game_state.news_feed else []
        
        for news in news_list:
            if isinstance(news, dict):
                msg = news.get('message', '')
                cat = news.get('category', '')
            else:
                msg = str(news)
                cat = ""
            
            news_label = QLabel(f"• {msg}")
            news_label.setWordWrap(True)
            news_label.setStyleSheet(f"""
                font-size: 13px;
                color: {self.theme.text_secondary};
                background: transparent;
                padding: 3px 0;
            """)
            self.news_container.addWidget(news_label)
        
        if not news_list:
            empty_label = QLabel("ニュースはありません")
            empty_label.setStyleSheet(f"""
                font-size: 14px;
                color: {self.theme.text_muted};
                background: transparent;
            """)
            self.news_container.addWidget(empty_label)
