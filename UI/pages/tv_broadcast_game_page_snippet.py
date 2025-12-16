# ... (Previous imports)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, 
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDialog, QAbstractItemView, QSlider, QGridLayout, QCheckBox, QProgressBar,
    QStyledItemDelegate, QStyle, QStackedWidget
)
# ...

class LineupDialog(QDialog):
    """Lineup Dialog"""
    def __init__(self, home_team, away_team, parent=None):
        super().__init__(parent)
        self.setWindowTitle("STARTING LINEUPS")
        self.resize(800, 600)
        self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        
        layout = QHBoxLayout(self)
        
        # Reuse logic or simply display tables
        self.away_table = self._create_table(away_team, "AWAY")
        layout.addWidget(self.away_table)
        
        self.home_table = self._create_table(home_team, "HOME")
        layout.addWidget(self.home_table)
        
    def _create_table(self, team, title):
        container = QWidget()
        l = QVBoxLayout(container)
        
        lbl = QLabel(f"{title}: {team.name}")
        lbl.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {self.theme.text_highlight}; margin-bottom: 10px;")
        l.addWidget(lbl)
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["#", "Pos", "Name", "AVG"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setStyleSheet(f"background-color: {self.theme.bg_card}; border: none;")
        
        lineup = team.current_lineup
        pos = team.lineup_positions
        
        table.setRowCount(len(lineup))
        for i, pid in enumerate(lineup):
            if pid == -1: continue
            p = team.players[pid]
            
            table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            table.setItem(i, 1, QTableWidgetItem(pos[i]))
            table.setItem(i, 2, QTableWidgetItem(p.name))
            avg = f".{int(p.record.batting_average*1000):03d}"
            table.setItem(i, 3, QTableWidgetItem(avg))
            
        l.addWidget(table)
        return container

# ... (Existing classes: TacticalField, StrikeZoneWidget, ScoreBoardWidget, TrackingDataPanel)

class PlayerInfoPanel(QFrame):
    clicked = Signal(object)
    def __init__(self, title, align_right=False, parent=None):
        super().__init__(parent)
        self.player = None
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"background: {THEME.bg_card}; border: none; border-radius: 4px;")
        
        l = QVBoxLayout(self)
        l.setContentsMargins(15,10,15,10); l.setSpacing(2)
        
        h = QLabel(title)
        h.setStyleSheet(f"color:{THEME.text_secondary}; font-size:10px; font-weight:bold; letter-spacing:1px;")
        h.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        h.setAttribute(Qt.WA_TransparentForMouseEvents) 
        l.addWidget(h)
        
        self.lbl_name = QLabel("---")
        self.lbl_name.setStyleSheet(f"color:{THEME.text_primary}; font-size:18px; font-weight:900;")
        self.lbl_name.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        self.lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents)
        l.addWidget(self.lbl_name)
        
        self.lbl_sub = QLabel("---")
        self.lbl_sub.setStyleSheet(f"color:{THEME.text_secondary}; font-size:11px;")
        self.lbl_sub.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        self.lbl_sub.setAttribute(Qt.WA_TransparentForMouseEvents)
        l.addWidget(self.lbl_sub)
        
        self.stats_box = QHBoxLayout()
        # Align stats box based on side
        if align_right:
            self.stats_box.setAlignment(Qt.AlignRight)
        else:
            self.stats_box.setAlignment(Qt.AlignLeft)
            
        l.addLayout(self.stats_box)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.player: self.clicked.emit(self.player)
        super().mouseDoubleClickEvent(e)

    def update_player(self, p, sub, stats):
        self.player = p
        self.lbl_name.setText(p.name)
        self.lbl_sub.setText(sub)
        
        # Clear layout
        while self.stats_box.count(): 
            item = self.stats_box.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
            elif item.layout():
                l = item.layout()
                while l.count():
                    si = l.takeAt(0)
                    if si.widget(): si.widget().deleteLater()
                l.deleteLater()
            
        for k, v, c in stats:
            bx = QVBoxLayout(); bx.setSpacing(1)
            l = QLabel(k); l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet("color:#888; font-size:9px;")
            
            # Check if value should be displayed as Rank
            display_val = str(v)
            font_size = "14px"
            
            # Logic to detect if this is an ability that needs ranking
            # We will rely on the caller to pass the rank letter if needed, OR we convert here.
            # But the caller (TVBroadcastGamePage) constructs the `stats` list.
            # So we should modify the caller to pass rank.
            # However, if we want visuals (color backgrounds for ranks), we handle it here.
            
            # Simple Text Display for now as requested "See Ability Ranks"
            # If the user passed a rank letter (S-G), we can color it.
            
            val_lbl = QLabel(display_val)
            val_lbl.setAlignment(Qt.AlignCenter)
            val_lbl.setStyleSheet(f"color:{c.name()}; font-size:{font_size}; font-weight:bold; font-family:'Consolas';")
            
            if k == "STM":
                 # Progress bar logic from before...
                 val_bar = QProgressBar()
                 val_bar.setRange(0, 100)
                 try: val_int = int(v)
                 except: val_int = 0
                 val_bar.setValue(val_int)
                 val_bar.setTextVisible(True)
                 val_bar.setFormat(f"{val_int}")
                 val_bar.setAlignment(Qt.AlignCenter)
                 val_bar.setFixedHeight(14)
                 val_bar.setStyleSheet(f"""
                    QProgressBar {{ border: none; background-color: #333; border-radius: 2px; color: white; font-family: 'Consolas'; font-size: 10px; font-weight: bold; }}
                    QProgressBar::chunk {{ background-color: {c.name()}; border-radius: 2px; }}
                """)
                 bx.addWidget(l)
                 bx.addWidget(val_bar)
            else:
                bx.addWidget(l)
                bx.addWidget(val_lbl)
                
            self.stats_box.addLayout(bx)

