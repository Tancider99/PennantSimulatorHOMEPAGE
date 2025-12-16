# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt
try:
    from UI.theme import get_theme
except ImportError:
    pass

class LineScoreTable(QTableWidget):
    """イニングスコア表示用テーブル"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setFixedHeight(75)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(True)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; border: none; }}
            QHeaderView::section {{
                background-color: transparent;
                color: {self.theme.text_secondary};
                font-size: 10px; font-weight: bold;
                border: none; border-bottom: 1px solid {self.theme.border};
            }}
            QTableWidget::item {{
                color: {self.theme.text_primary};
                font-family: "Dseg7"; /* Digital font if available, else fallback */
                font-size: 14px; font-weight: bold;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
        """)
        
        # Initial columns: Team, 1-12, R, H, E
        self.cols = ["TEAM"] + [str(i) for i in range(1, 13)] + ["R", "H", "E"]
        self.setColumnCount(len(self.cols))
        self.setHorizontalHeaderLabels(self.cols)
        self.setRowCount(2)
        
        self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        h = self.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)

    def set_inning_count(self, count):
        """Rebuild columns for specific number of innings"""
        self.cols = ["TEAM"] + [str(i) for i in range(1, count + 1)] + ["R", "H", "E"]
        self.setColumnCount(len(self.cols))
        self.setHorizontalHeaderLabels(self.cols)
        
        h = self.horizontalHeader()
        for i in range(len(self.cols)):
            h.setSectionResizeMode(i, QHeaderView.Stretch)

    def update_names(self, home_name, away_name):
        """Update team names in the first column"""
        # Row 0: Away, Row 1: Home
        i1 = QTableWidgetItem(away_name[:3].upper())
        i1.setTextAlignment(Qt.AlignCenter)
        self.setItem(0, 0, i1)
        
        i2 = QTableWidgetItem(home_name[:3].upper())
        i2.setTextAlignment(Qt.AlignCenter)
        self.setItem(1, 0, i2)

    def update_score_data(self, h_runs, a_runs, h_hits, a_hits, h_err, a_err):
        # Update R, H, E columns (last 3)
        cols = self.columnCount()
        r_col, h_col, e_col = cols-3, cols-2, cols-1
        
        items = [
            (0, r_col, str(a_runs)), (0, h_col, str(a_hits)), (0, e_col, str(a_err)),
            (1, r_col, str(h_runs)), (1, h_col, str(h_hits)), (1, e_col, str(h_err))
        ]
        for r, c, val in items:
            it = QTableWidgetItem(val)
            it.setTextAlignment(Qt.AlignCenter)
            self.setItem(r, c, it)

    def set_inning_score(self, inning, is_top, score):
        # Ensure column exists
        # Columns: TEAM(0), 1(1), 2(2)... K(K) ... R(-3), H(-2), E(-1)
        # Inning N maps to column N.
        # If inning > columnCount - 4, we need to insert columns.
        
        current_max_inning = self.columnCount() - 4
        
        if inning > current_max_inning:
            diff = inning - current_max_inning
            for _ in range(diff):
                insert_idx = self.columnCount() - 3
                new_inning_num = self.columnCount() - 3
                self.insertColumn(insert_idx)
                self.setHorizontalHeaderItem(insert_idx, QTableWidgetItem(str(new_inning_num)))
                self.horizontalHeader().setSectionResizeMode(insert_idx, QHeaderView.Stretch)

        # Set score
        row = 0 if is_top else 1
        col = inning 
        
        it = QTableWidgetItem(str(score))
        it.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, col, it)
