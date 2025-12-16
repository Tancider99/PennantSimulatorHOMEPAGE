from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from .tables import PlayerTable, SortableTableWidgetItem

class SubstitutionPlayerTable(PlayerTable):
    """
    Game Substitution Table - Specialized with Condition and Game Stats
    """
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def set_strict_mode(self, mode: str):
        """
        Enforce a specific mode and hide switching controls.
        mode: "pitcher" or "fielder" (or "batter")
        """
        if mode == "pitcher":
            # Hide Batter/Pitcher Toggles
            if hasattr(self, 'view_batter_btn'): self.view_batter_btn.setVisible(False)
            if hasattr(self, 'view_pitcher_btn'): self.view_pitcher_btn.setVisible(False)
            
            # Show Type Filter (Starter, Relief, etc), Hide Position Filter
            if hasattr(self, 'type_filter'): self.type_filter.setVisible(True)
            if hasattr(self, 'position_filter'): self.position_filter.setVisible(False)
            
            self._set_view_mode("pitcher")
            
        elif mode in ["fielder", "batter"]:
             # Hide Batter/Pitcher Toggles
            if hasattr(self, 'view_batter_btn'): self.view_batter_btn.setVisible(False)
            if hasattr(self, 'view_pitcher_btn'): self.view_pitcher_btn.setVisible(False)
            
            # Hide Type Filter, Show Position Filter
            if hasattr(self, 'type_filter'): self.type_filter.setVisible(False)
            if hasattr(self, 'position_filter'): self.position_filter.setVisible(True)
            
            self._set_view_mode("batter")
    
    def _refresh_columns(self, mode: str = "batter"):
        """Override to include Condition (調子) column"""
        self.table.clear()
        
        # Clear delegates
        for i in range(self.table.columnCount()):
            self.table.setItemDelegateForColumn(i, None)

        if mode == "batter":
            headers = [
                "#", "調", "名前", "Pos", "ミート", "パワー", "走力",
                "肩力", "守備", "打率", "HR", "打点", "総合"
            ]
            # widths adjusted for Condition column
            widths = [40, 30, 130, 60, 55, 55, 55, 55, 55, 65, 50, 50, 60]
        else:
            headers = [
                "#", "調", "名前", "役割", "球速", "制球", "スタ",
                "変化", "ERA", "勝", "敗", "S", "総合"
            ]
            widths = [40, 30, 130, 60, 55, 55, 55, 55, 60, 40, 40, 40, 60]

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        for i, width in enumerate(widths):
            header.resizeSection(i, width)
        header.setStretchLastSection(True)

        # Rating delegates
        if mode == "batter":
            rating_cols = [4, 5, 6, 7, 8]
        else:
            rating_cols = [4, 5, 6, 7]
            
        for col in rating_cols:
            self.table.setItemDelegateForColumn(col, self.rating_delegate)
            
        self._populate_table(mode)

    def _set_player_row(self, row: int, player, mode: str):
        """Override to show Condition"""
        stats = player.stats
        record = player.record
        
        # Condition icon/text
        condition = player.condition # 1-9 (5 is normal)
        cond_map = {
             1: "絶不調", 2: "不調", 3: "不調", 4: "普通", 
             5: "普通", 6: "好調", 7: "好調", 8: "絶好調", 9: "絶好調"
        }
        cond_text = cond_map.get(condition, "-")
        
        if mode == "batter":
            data = [
                str(player.uniform_number),
                cond_text,
                player.name,
                player.position.value[:2],
                stats.contact,
                stats.power,
                stats.speed,
                stats.arm,
                stats.fielding,
                f".{int(record.batting_average * 1000):03d}" if record.at_bats > 0 else "---",
                str(record.home_runs),
                str(record.rbis),
                f"★ {player.overall_rating}"
            ]
            rating_cols = [4, 5, 6, 7, 8]
        else:
            pitch_role = player.pitch_type.value[:2] if player.pitch_type else "投"
            era = record.era if record.innings_pitched > 0 else 0
            
            # Helper logic for velocity if needed
            vel_rating = 50
            if hasattr(stats, 'kmh_to_rating'):
                vel_rating = stats.kmh_to_rating(stats.velocity)
            else:
                vel_rating = int(max(1, min(99, (stats.velocity - 130) * 2 + 30)))

            data = [
                str(player.uniform_number),
                cond_text,
                player.name,
                pitch_role,
                vel_rating,
                stats.control,
                stats.stamina,
                stats.breaking,
                f"{era:.2f}" if era > 0 else "-.--",
                str(record.wins),
                str(record.losses),
                str(record.saves),
                f"★ {player.overall_rating}"
            ]
            rating_cols = [4, 5, 6, 7]

        for col, value in enumerate(data):
            item = SortableTableWidgetItem()
            
            if col in rating_cols:
                item.setData(Qt.UserRole, value)
                item.setData(Qt.DisplayRole, "")
                item.setTextAlignment(Qt.AlignCenter)
            else:
                item.setText(str(value))
                item.setTextAlignment(Qt.AlignCenter if col != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                
                # Condition Color
                if col == 1:
                    # Explicit colors matching theme roughly
                    if condition >= 8: item.setForeground(QColor("#ff6b6b")) # Red
                    elif condition >= 6: item.setForeground(QColor("#ff9800")) # Orange
                    elif condition <= 2: item.setForeground(QColor("#5fbcd3")) # Blue
                    else: item.setForeground(QColor("#f0f0f0")) # White

            if col == 0:
                item.setData(Qt.UserRole, player)
                
            self.table.setItem(row, col, item)
