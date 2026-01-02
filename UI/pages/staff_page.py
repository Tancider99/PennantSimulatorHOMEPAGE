# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Staff Page
Team Staff Management (Manager, Coaches, Scouts)
Fixed role slots with per-role hire/fire buttons
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QSplitter, QFrame, QPushButton, QComboBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QDialog, QListWidget, QListWidgetItem, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ContentPanel, InfoPanel, ToolbarPanel
from models import StaffRole, StaffMember, TeamLevel, Position
import random


# Import name lists from constants for staff generation
from constants import JAPANESE_SURNAMES, JAPANESE_FIRSTNAMES

# Define all role slots (fixed structure)
ROLE_SLOTS = [
    # 1軍
    (StaffRole.MANAGER_FIRST, TeamLevel.FIRST, "一軍監督"),
    (StaffRole.PITCHING_COACH, TeamLevel.FIRST, "一軍投手コーチ①"),
    (StaffRole.PITCHING_COACH, TeamLevel.FIRST, "一軍投手コーチ②"),
    (StaffRole.BATTING_COACH, TeamLevel.FIRST, "一軍打撃コーチ①"),
    (StaffRole.BATTING_COACH, TeamLevel.FIRST, "一軍打撃コーチ②"),
    (StaffRole.INFIELD_COACH, TeamLevel.FIRST, "一軍内野守備走塁コーチ"),
    (StaffRole.OUTFIELD_COACH, TeamLevel.FIRST, "一軍外野守備走塁コーチ"),
    (StaffRole.BATTERY_COACH, TeamLevel.FIRST, "一軍バッテリーコーチ"),
    (StaffRole.BULLPEN_COACH, TeamLevel.FIRST, "一軍ブルペンコーチ"),
    # 2軍
    (StaffRole.MANAGER_SECOND, TeamLevel.SECOND, "二軍監督"),
    (StaffRole.PITCHING_COACH, TeamLevel.SECOND, "二軍投手コーチ①"),
    (StaffRole.PITCHING_COACH, TeamLevel.SECOND, "二軍投手コーチ②"),
    (StaffRole.BATTING_COACH, TeamLevel.SECOND, "二軍打撃コーチ①"),
    (StaffRole.BATTING_COACH, TeamLevel.SECOND, "二軍打撃コーチ②"),
    (StaffRole.INFIELD_COACH, TeamLevel.SECOND, "二軍内野守備走塁コーチ"),
    (StaffRole.OUTFIELD_COACH, TeamLevel.SECOND, "二軍外野守備走塁コーチ"),
    (StaffRole.BATTERY_COACH, TeamLevel.SECOND, "二軍バッテリーコーチ"),
    (StaffRole.BULLPEN_COACH, TeamLevel.SECOND, "二軍ブルペンコーチ"),
    # 3軍
    (StaffRole.MANAGER_THIRD, TeamLevel.THIRD, "三軍監督"),
    (StaffRole.PITCHING_COACH, TeamLevel.THIRD, "三軍投手コーチ①"),
    (StaffRole.PITCHING_COACH, TeamLevel.THIRD, "三軍投手コーチ②"),
    (StaffRole.BATTING_COACH, TeamLevel.THIRD, "三軍打撃コーチ①"),
    (StaffRole.BATTING_COACH, TeamLevel.THIRD, "三軍打撃コーチ②"),
    (StaffRole.INFIELD_COACH, TeamLevel.THIRD, "三軍内野守備走塁コーチ"),
    (StaffRole.OUTFIELD_COACH, TeamLevel.THIRD, "三軍外野守備走塁コーチ"),
    (StaffRole.BATTERY_COACH, TeamLevel.THIRD, "三軍バッテリーコーチ"),
    (StaffRole.BULLPEN_COACH, TeamLevel.THIRD, "三軍ブルペンコーチ"),
    # スカウト
    (StaffRole.SCOUT_DOMESTIC, None, "国内スカウト①"),
    (StaffRole.SCOUT_DOMESTIC, None, "国内スカウト②"),
    (StaffRole.SCOUT_DOMESTIC, None, "国内スカウト③"),
    (StaffRole.SCOUT_DOMESTIC, None, "国内スカウト④"),
    (StaffRole.SCOUT_DOMESTIC, None, "国内スカウト⑤"),
    (StaffRole.SCOUT_INTERNATIONAL, None, "海外スカウト①"),
    (StaffRole.SCOUT_INTERNATIONAL, None, "海外スカウト②"),
    (StaffRole.SCOUT_INTERNATIONAL, None, "海外スカウト③"),
]


def get_staff_data_path(team_name: str) -> str:
    """Get the path for staff data file"""
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "staff_data")
    os.makedirs(save_dir, exist_ok=True)
    safe_name = "".join(c for c in team_name if c.isalnum() or c in "_ -")
    return os.path.join(save_dir, f"{safe_name}_staff.json")


def get_shared_pool_path() -> str:
    """Get the path for shared candidate pool file"""
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "staff_data")
    os.makedirs(save_dir, exist_ok=True)
    return os.path.join(save_dir, "shared_candidate_pool.json")


# デフォルトデータディレクトリ
STAFF_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "staff_data")
STAFF_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "staff_data_default")


def save_staff_default_data():
    """現在のスタッフデータをデフォルトとして保存"""
    import shutil
    if os.path.exists(STAFF_DATA_DIR):
        if os.path.exists(STAFF_DEFAULT_DIR):
            shutil.rmtree(STAFF_DEFAULT_DIR)
        shutil.copytree(STAFF_DATA_DIR, STAFF_DEFAULT_DIR)
        return True
    return False


def reset_staff_to_default():
    """スタッフデータをデフォルトに戻す"""
    import shutil
    if os.path.exists(STAFF_DEFAULT_DIR) and os.listdir(STAFF_DEFAULT_DIR):
        if os.path.exists(STAFF_DATA_DIR):
            shutil.rmtree(STAFF_DATA_DIR)
        shutil.copytree(STAFF_DEFAULT_DIR, STAFF_DATA_DIR)
        return True
    return False


def has_staff_default_data():
    """デフォルトスタッフデータが存在するか確認"""
    return os.path.exists(STAFF_DEFAULT_DIR) and len(os.listdir(STAFF_DEFAULT_DIR)) > 0


def save_shared_pool(candidate_pool: list):
    """Save the shared candidate pool"""
    data = []
    for c in candidate_pool:
        data.append(_serialize_candidate(c))
    
    path = get_shared_pool_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_shared_pool() -> list:
    """Load the shared candidate pool"""
    path = get_shared_pool_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def save_staff_data(team, staff_slots: list):
    """Save staff data to file (team-specific, no candidate pool)"""
    if not team:
        return
    
    data = {
        "version": 3,
        "staff_slots": []
    }
    
    # Serialize staff slots (each slot can be None or a StaffMember)
    for slot_staff in staff_slots:
        if slot_staff is None:
            data["staff_slots"].append(None)
        else:
            data["staff_slots"].append(_serialize_staff(slot_staff))
    
    path = get_staff_data_path(team.name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _serialize_staff(s: StaffMember) -> dict:
    """Serialize a StaffMember to dict"""
    return {
        "name": s.name,
        "role": s.role.value,
        "age": s.age,
        "salary": s.salary,
        "ability": s.ability,
        "specialty": s.specialty,
        "years_in_role": s.years_in_role,
        "team_level": s.team_level.value if s.team_level else None,
        "is_available": s.is_available,
        "current_mission_id": s.current_mission_id,
        "source": getattr(s, 'source', 'generated'),
        "original_player_name": getattr(s, 'original_player_name', '')
    }


def _serialize_candidate(c) -> dict:
    """Serialize a StaffCandidate to dict"""
    return {
        "name": c["name"],
        "age": c["age"],
        "base_ability": c["base_ability"],
        "role_abilities": c["role_abilities"],
        "source": c.get("source", "generated"),
        "original_player_name": c.get("original_player_name", ""),
        "career_stats": c.get("career_stats", None),  # Career stats for retired players
        "original_position": c.get("original_position", None)
    }


def _deserialize_staff(d: dict) -> StaffMember:
    """Deserialize a dict to StaffMember"""
    role = None
    for r in StaffRole:
        if r.value == d["role"]:
            role = r
            break
    if not role:
        return None
    
    level = None
    if d.get("team_level"):
        for lv in TeamLevel:
            if lv.value == d["team_level"]:
                level = lv
                break
    
    return StaffMember(
        name=d["name"],
        role=role,
        age=d.get("age", 45),
        salary=d.get("salary", 10000000),
        ability=d.get("ability", 50),
        specialty=d.get("specialty", ""),
        years_in_role=d.get("years_in_role", 0),
        team_level=level,
        is_available=d.get("is_available", True),
        current_mission_id=d.get("current_mission_id"),
        source=d.get("source", "generated"),
        original_player_name=d.get("original_player_name", "")
    )


def load_staff_data(team) -> list:
    """Load staff data from file. Returns staff_slots list"""
    path = get_staff_data_path(team.name)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get("version") not in [2, 3]:
            return None  # Old format, regenerate
        
        # Deserialize staff slots
        staff_slots = []
        for slot_data in data.get("staff_slots", []):
            if slot_data is None:
                staff_slots.append(None)
            else:
                staff_slots.append(_deserialize_staff(slot_data))
        
        return staff_slots
    except Exception as e:
        return None


def initialize_staff_from_files(game_state):
    """
    Initialize staff data from files at game start.
    Loads staff_data files for each team and shared_candidate_pool.
    Call this function when starting a new game or loading a saved game.
    """
    if not game_state:
        return
    
    # Load shared candidate pool from file
    loaded_pool = load_shared_pool()
    if loaded_pool:
        game_state.staff_candidate_pool = loaded_pool
    else:
        # Generate initial pool
        game_state.staff_candidate_pool = generate_candidate_pool(30)
        # Save initial pool to file
        save_shared_pool(game_state.staff_candidate_pool)
    
    # Load staff slots for each team from files
    all_teams = getattr(game_state, 'all_teams', []) or getattr(game_state, 'teams', [])
    for team in all_teams:
        loaded_slots = load_staff_data(team)
        
        if loaded_slots and len(loaded_slots) == len(ROLE_SLOTS):
            team.staff_slots = loaded_slots
            # Sync to team.staff for training bonus
            team.staff = [s for s in loaded_slots if s is not None]
        else:
            # Generate new staff for this team
            team.staff_slots = []
            for role, level, display_name in ROLE_SLOTS:
                if game_state.staff_candidate_pool:
                    candidate = random.choice(game_state.staff_candidate_pool)
                    staff = create_staff_from_candidate(candidate, role, level)
                    team.staff_slots.append(staff)
                else:
                    team.staff_slots.append(None)
            # Sync to team.staff
            team.staff = [s for s in team.staff_slots if s is not None]
            # Save generated staff to file
            save_staff_data(team, team.staff_slots)
    
            pass


def generate_candidate(source: str = "generated", player=None) -> dict:
    """Generate a candidate with abilities for ALL roles"""
    if source == "retired_player" and player:
        return _generate_candidate_from_retired_player(player)
    
    # Random candidate with low base ability
    base_ability = random.randint(20, 45)
    
    # Generate role-specific abilities (all roles, some higher/lower)
    role_abilities = {}
    for role in StaffRole:
        # Add some variance to each role
        variance = random.randint(-15, 15)
        role_abilities[role.value] = max(10, min(99, base_ability + variance))
    
    # Generate full name (surname + firstname)
    full_name = random.choice(JAPANESE_SURNAMES) + random.choice(JAPANESE_FIRSTNAMES)
    
    return {
        "name": full_name,
        "age": random.randint(35, 55),
        "base_ability": base_ability,
        "role_abilities": role_abilities,
        "source": "generated",
        "original_player_name": ""
    }


def _generate_candidate_from_retired_player(player) -> dict:
    """Generate a candidate from a retired player with role abilities based on stats"""
    stats = player.stats
    pos = player.position
    
    # Calculate base abilities for different role types
    pitching_ability = int((getattr(stats, 'control', 40) + getattr(stats, 'stuff', 40)) / 2)
    batting_ability = int((getattr(stats, 'contact', 40) + getattr(stats, 'power', 40)) / 2)
    defense_ability = int((getattr(stats, 'fielding', 40) + getattr(stats, 'arm', 40)) / 2)
    catching_ability = int((getattr(stats, 'fielding', 40) + getattr(stats, 'catcher_lead', 40)) / 2)
    intelligence = getattr(stats, 'intelligence', 40)
    
    # Boost for being a retired player (experience bonus)
    experience_bonus = 15
    
    role_abilities = {}
    
    # Manager roles (based on intelligence and experience)
    base_manager = int((intelligence + 50) / 2) + experience_bonus
    role_abilities[StaffRole.MANAGER_FIRST.value] = min(85, base_manager)
    role_abilities[StaffRole.MANAGER_SECOND.value] = min(85, base_manager - 5)
    role_abilities[StaffRole.MANAGER_THIRD.value] = min(85, base_manager - 10)
    
    # Pitching coaches (pitchers get bonus)
    if pos == Position.PITCHER:
        role_abilities[StaffRole.PITCHING_COACH.value] = min(85, pitching_ability + experience_bonus + 10)
        role_abilities[StaffRole.BULLPEN_COACH.value] = min(85, pitching_ability + experience_bonus + 5)
    else:
        role_abilities[StaffRole.PITCHING_COACH.value] = max(20, pitching_ability - 10)
        role_abilities[StaffRole.BULLPEN_COACH.value] = max(20, pitching_ability - 15)
    
    # Batting coaches (batters get bonus)
    if pos != Position.PITCHER:
        role_abilities[StaffRole.BATTING_COACH.value] = min(85, batting_ability + experience_bonus + 10)
    else:
        role_abilities[StaffRole.BATTING_COACH.value] = max(20, 30)
    
    # Defense coaches
    if pos in [Position.SHORTSTOP, Position.SECOND, Position.THIRD, Position.FIRST]:
        role_abilities[StaffRole.INFIELD_COACH.value] = min(85, defense_ability + experience_bonus + 10)
        role_abilities[StaffRole.OUTFIELD_COACH.value] = max(25, defense_ability - 5)
    elif pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
        role_abilities[StaffRole.OUTFIELD_COACH.value] = min(85, defense_ability + experience_bonus + 10)
        role_abilities[StaffRole.INFIELD_COACH.value] = max(25, defense_ability - 5)
    else:
        role_abilities[StaffRole.INFIELD_COACH.value] = max(30, defense_ability)
        role_abilities[StaffRole.OUTFIELD_COACH.value] = max(30, defense_ability)
    
    # Battery coach (catchers get big bonus)
    if pos == Position.CATCHER:
        role_abilities[StaffRole.BATTERY_COACH.value] = min(85, catching_ability + experience_bonus + 15)
    else:
        role_abilities[StaffRole.BATTERY_COACH.value] = max(20, 30)
    
    # Scouts (based on intelligence)
    role_abilities[StaffRole.SCOUT_DOMESTIC.value] = min(80, intelligence + experience_bonus)
    role_abilities[StaffRole.SCOUT_INTERNATIONAL.value] = min(80, intelligence + experience_bonus - 5)
    
    # Extract career stats from player record
    career_stats = None
    if hasattr(player, 'record') and player.record:
        rec = player.record
        if pos == Position.PITCHER:
            career_stats = {
                "is_pitcher": True,
                "games": getattr(rec, 'games_pitched', 0),
                "wins": getattr(rec, 'wins', 0),
                "losses": getattr(rec, 'losses', 0),
                "era": round(getattr(rec, 'era', 0), 2),
                "strikeouts": getattr(rec, 'strikeouts_pitched', 0),
                "saves": getattr(rec, 'saves', 0),
                "holds": getattr(rec, 'holds', 0),
                "innings": round(getattr(rec, 'innings_pitched', 0), 1)
            }
        else:
            career_stats = {
                "is_pitcher": False,
                "games": getattr(rec, 'games_played', 0),
                "at_bats": getattr(rec, 'at_bats', 0),
                "hits": getattr(rec, 'hits', 0),
                "home_runs": getattr(rec, 'home_runs', 0),
                "rbis": getattr(rec, 'rbis', 0),
                "stolen_bases": getattr(rec, 'stolen_bases', 0),
                "avg": round(getattr(rec, 'batting_average', 0), 3)
            }
    
    return {
        "name": player.name,
        "age": player.age + 1,
        "base_ability": max(role_abilities.values()),
        "role_abilities": role_abilities,
        "source": "retired_player",
        "original_player_name": player.name,
        "career_stats": career_stats,
        "original_position": pos.value if pos else None
    }


def generate_candidate_pool(count: int = 30) -> list:
    """Generate a pool of candidates"""
    pool = []
    for _ in range(count):
        pool.append(generate_candidate())
    return pool


def create_staff_from_candidate(candidate: dict, role: StaffRole, level: TeamLevel = None) -> StaffMember:
    """Create a StaffMember from a candidate for a specific role"""
    ability = candidate["role_abilities"].get(role.value, candidate["base_ability"])
    
    # Calculate salary based on ability
    base_salary = 2000  # 2000万円
    salary = int((base_salary + ability * 50) * 10000)
    
    return StaffMember(
        name=candidate["name"],
        role=role,
        age=candidate["age"],
        salary=salary,
        ability=ability,
        specialty="",
        years_in_role=0,
        team_level=level,
        source=candidate.get("source", "generated"),
        original_player_name=candidate.get("original_player_name", "")
    )


class HireDialog(QDialog):
    """Dialog to hire a new staff member for a specific role"""
    
    def __init__(self, parent, candidates: list, target_role: StaffRole, theme=None):
        super().__init__(parent)
        self.candidates = candidates
        self.target_role = target_role
        self.theme = theme or get_theme()
        self.selected_candidate = None
        
        self.setWindowTitle(f"{target_role.value}任命")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme.bg_card}; color: {self.theme.text_primary}; }}
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Title
        title = QLabel(f"{self.target_role.value}候補者リスト")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.theme.text_primary};")
        layout.addWidget(title)
        
        # Info
        info = QLabel("※全候補者がこの役職に就けます。能力はその役職での適性を示します。")
        info.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Candidate list
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
            }}
            QListWidget::item {{
                padding: 8px;
            }}
            QListWidget::item:selected {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
            }}
        """)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget)
        
        # Populate list
        self._refresh_list()
        
        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setStyleSheet(f"background: {self.theme.bg_hover}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 8px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        hire_btn = QPushButton("任命する")
        hire_btn.setStyleSheet(f"background: {self.theme.primary}; color: {self.theme.text_highlight}; border: none; padding: 8px; font-weight: bold;")
        hire_btn.clicked.connect(self._on_hire)
        btn_layout.addWidget(hire_btn)
        layout.addLayout(btn_layout)
    
    def _refresh_list(self):
        self.list_widget.clear()
        
        # Sort by ability for this role (descending)
        sorted_candidates = sorted(
            self.candidates,
            key=lambda c: c["role_abilities"].get(self.target_role.value, c["base_ability"]),
            reverse=True
        )
        
        for c in sorted_candidates:
            ability = c["role_abilities"].get(self.target_role.value, c["base_ability"])
            source_tag = "(元選手)" if c.get("source") == "retired_player" else ""
            text = f"{c['name']} {source_tag} - 能力:{ability} - {c['age']}歳"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, c)
            self.list_widget.addItem(item)
    
    def _on_double_click(self, item):
        self.selected_candidate = item.data(Qt.UserRole)
        self.accept()
    
    def _on_hire(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_candidate = item.data(Qt.UserRole)
            self.accept()


class StaffPage(QWidget):
    """Team staff management page with fixed role slots"""

    staff_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.staff_slots = [None] * len(ROLE_SLOTS)  # One slot per role
        self.candidate_pool = []

        self._setup_ui()

    def _setup_ui(self):
        """Create the staff page layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main splitter (table | detail panel)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # Left: Staff table
        left_widget = QWidget()
        left_widget.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 6, 12)

        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(6)
        self.staff_table.setHorizontalHeaderLabels(["役職", "名前", "年齢", "能力", "年俸", "操作"])
        # Fixed width for role column
        self.staff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.staff_table.setColumnWidth(0, 160)  # Reduced from stretch
        self.staff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # Name stretches
        self.staff_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.staff_table.setColumnWidth(2, 50)
        self.staff_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.staff_table.setColumnWidth(3, 50)
        self.staff_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.staff_table.setColumnWidth(4, 80)
        self.staff_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.staff_table.setColumnWidth(5, 80)
        self.staff_table.verticalHeader().setVisible(False)
        self.staff_table.verticalHeader().setDefaultSectionSize(44)  # Increased row height
        self.staff_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.staff_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.staff_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.staff_table.setAlternatingRowColors(True)  # Striped rows
        self.staff_table.setShowGrid(False)  # Remove all gridlines
        self.staff_table.itemSelectionChanged.connect(self._on_staff_selected)
        self.staff_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                alternate-background-color: {self.theme.bg_card_elevated};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {self.theme.text_primary};
                border-bottom: 1px solid {self.theme.border};
            }}
            QTableWidget::item:hover {{
                background-color: transparent;
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_darkest};
                color: {self.theme.text_secondary};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {self.theme.border};
                font-weight: 600;
            }}
        """)

        left_layout.addWidget(self.staff_table)
        splitter.addWidget(left_widget)

        # Right: Detail panel
        right_widget = self._create_detail_panel()
        splitter.addWidget(right_widget)

        # Set splitter sizes (70/30)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter)

    def _create_detail_panel(self) -> QWidget:
        """Create the staff detail panel (exact roster tab style using InfoPanel)"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.theme.bg_dark};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.theme.bg_dark};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.theme.border};
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 16, 8)
        layout.setSpacing(6)

        # Staff name card (like PlayerCard header)
        name_card = QFrame()
        name_card.setFixedHeight(80)
        name_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        name_layout = QVBoxLayout(name_card)
        name_layout.setContentsMargins(16, 12, 16, 12)
        name_layout.setSpacing(4)
        
        self.detail_header = QLabel("スタッフを選択してください")
        self.detail_header.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 1px;
        """)
        name_layout.addWidget(self.detail_header)
        
        self.detail_subtitle = QLabel("")
        self.detail_subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_secondary};
        """)
        name_layout.addWidget(self.detail_subtitle)
        
        layout.addWidget(name_card)

        # Staff info panel (using InfoPanel like roster)
        self.info_panel = InfoPanel("スタッフ情報")
        layout.addWidget(self.info_panel)

        # Scout status panel (for scouts only)
        self.scout_panel = InfoPanel("スカウト状態")
        self.scout_panel.setVisible(False)
        layout.addWidget(self.scout_panel)

        # Career stats panel (for retired players only)
        self.career_panel = InfoPanel("選手時代の通算成績")
        self.career_panel.setVisible(False)
        layout.addWidget(self.career_panel)

        layout.addStretch()
        scroll.setWidget(panel)
        return scroll

    def _on_staff_selected(self):
        """Handle staff selection in table"""
        selected_rows = self.staff_table.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.staff_slots):
            return
        
        staff = self.staff_slots[row]
        role, level, display_name = ROLE_SLOTS[row]
        
        # Clear all panels
        self._clear_info_panel()
        self._clear_scout_panel()
        self._clear_career_panel()
        
        if staff:
            self.detail_header.setText(staff.name)
            self.detail_subtitle.setText(display_name)
            
            # Build info panel
            self.info_panel.add_row("年齢", f"{staff.age}歳")
            
            # Ability with color
            ability_color = self.theme.text_primary
            if staff.ability >= 70:
                ability_color = self.theme.success
            elif staff.ability >= 50:
                ability_color = self.theme.warning
            else:
                ability_color = self.theme.danger
            self.info_panel.add_row("能力", str(staff.ability), ability_color)
            
            # 年俸を億万形式で表示 (salaryは円単位)
            salary_yen = staff.salary
            man = salary_yen // 10000
            if man >= 10000:
                oku = man // 10000
                remainder = man % 10000
                salary_text = f"{oku}億{remainder}万" if remainder > 0 else f"{oku}億"
            else:
                salary_text = f"{man}万"
            self.info_panel.add_row("年俸", salary_text)
            self.info_panel.add_row("在任期間", f"{staff.years_in_role}年目")
            
            if staff.source == "retired_player":
                self.info_panel.add_row("経歴", f"元選手 ({staff.original_player_name})")
                self._show_career_stats(staff)
            else:
                self.info_panel.add_row("経歴", "スタッフ")
                self.career_panel.setVisible(False)
            
            # Scout info
            if staff.is_scout:
                self.scout_panel.setVisible(True)
                if staff.is_available:
                    self.scout_panel.add_row("状態", "待機中", self.theme.success)
                    self.scout_panel.add_row("ミッション", "なし")
                else:
                    self.scout_panel.add_row("状態", "派遣中", self.theme.warning)
                    self.scout_panel.add_row("ミッション", staff.current_mission_id or "調査中")
            else:
                self.scout_panel.setVisible(False)
        else:
            self.detail_header.setText(f"{display_name}")
            self.detail_subtitle.setText("空席")
            self.info_panel.add_row("状態", "未任命", self.theme.text_muted)
            self.scout_panel.setVisible(False)
            self.career_panel.setVisible(False)

    def _clear_info_panel(self):
        """Clear the info panel contents"""
        while self.info_panel.content_layout.count():
            item = self.info_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

    def _clear_scout_panel(self):
        """Clear the scout panel contents"""
        while self.scout_panel.content_layout.count():
            item = self.scout_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

    def _clear_career_panel(self):
        """Clear the career panel contents"""
        while self.career_panel.content_layout.count():
            item = self.career_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

    def _show_career_stats(self, staff):
        """Show career stats for a retired player staff member"""
        # Try to find the candidate with career stats
        career_stats = None
        original_position = None
        
        for c in self.candidate_pool:
            if c.get("original_player_name") == staff.original_player_name:
                career_stats = c.get("career_stats")
                original_position = c.get("original_position")
                break
        
        self.career_panel.setVisible(True)
        
        if not career_stats:
            self.career_panel.add_row("ポジション", original_position or "-")
            self.career_panel.add_row("データ", "なし", self.theme.text_muted)
            return
        
        self.career_panel.add_row("ポジション", original_position or "-")
        
        # Build stats
        if career_stats.get("is_pitcher"):
            self.career_panel.add_row("登板", str(career_stats.get("games", "-")))
            self.career_panel.add_row("勝-敗", f"{career_stats.get('wins', 0)}-{career_stats.get('losses', 0)}")
            self.career_panel.add_row("防御率", str(career_stats.get("era", "-")))
            self.career_panel.add_row("奪三振", str(career_stats.get("strikeouts", "-")))
            self.career_panel.add_row("セーブ", str(career_stats.get("saves", "-")))
            self.career_panel.add_row("ホールド", str(career_stats.get("holds", "-")))
        else:
            avg = career_stats.get("avg", 0)
            avg_str = f".{int(avg * 1000):03d}" if avg > 0 else ".---"
            self.career_panel.add_row("試合", str(career_stats.get("games", "-")))
            self.career_panel.add_row("打率", avg_str)
            self.career_panel.add_row("打数-安打", f"{career_stats.get('at_bats', 0)}-{career_stats.get('hits', 0)}")
            self.career_panel.add_row("本塁打", str(career_stats.get("home_runs", "-")))
            self.career_panel.add_row("打点", str(career_stats.get("rbis", "-")))
            self.career_panel.add_row("盗塁", str(career_stats.get("stolen_bases", "-")))

    def _create_toolbar(self) -> ToolbarPanel:
        """Create the toolbar"""
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        # Team selector
        team_label = QLabel("チーム:")
        team_label.setStyleSheet(f"color: {self.theme.text_secondary}; margin-left: 8px;")
        toolbar.add_widget(team_label)

        self.team_selector = QComboBox()
        self.team_selector.setMinimumWidth(180)
        self.team_selector.setFixedHeight(32)
        self.team_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {self.theme.text_secondary};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
                border: 1px solid {self.theme.border};
            }}
        """)
        self.team_selector.currentIndexChanged.connect(self._on_team_changed)
        toolbar.add_widget(self.team_selector)

        toolbar.add_stretch()

        return toolbar

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return

        # Update team selector
        self.team_selector.blockSignals(True)
        self.team_selector.clear()

        player_team_obj = game_state.player_team

        for team in game_state.all_teams:
            display_name = team.name
            if player_team_obj and team.name == player_team_obj.name:
                display_name = f"{team.name} (自チーム)"
            self.team_selector.addItem(display_name, team)

        if player_team_obj:
            for i in range(self.team_selector.count()):
                if self.team_selector.itemData(i) == player_team_obj:
                    self.team_selector.setCurrentIndex(i)
                    break
        elif game_state.all_teams:
            self.team_selector.setCurrentIndex(0)

        self.team_selector.blockSignals(False)
        self._on_team_changed(self.team_selector.currentIndex())

    def _on_team_changed(self, index: int):
        """Handle team selection change"""
        if index < 0 or not self.game_state:
            return

        self.current_team = self.team_selector.itemData(index)
        
        # Load candidate pool from game state
        if self.game_state and hasattr(self.game_state, 'staff_candidate_pool'):
            if self.game_state.staff_candidate_pool:
                self.candidate_pool = self.game_state.staff_candidate_pool
            else:
                # Generate initial pool if not exists
                self.candidate_pool = generate_candidate_pool(30)
                self.game_state.staff_candidate_pool = self.candidate_pool
        else:
            self.candidate_pool = generate_candidate_pool(30)
        
        # Load staff from team.staff_slots
        if self.current_team.staff_slots and len(self.current_team.staff_slots) == len(ROLE_SLOTS):
            self.staff_slots = self.current_team.staff_slots
        else:
            # Generate new staff for this team
            self._generate_initial_staff()
            # Save to team
            self.current_team.staff_slots = self.staff_slots
        
        # Sync staff to team.staff for training bonus system
        self._sync_to_team_staff()
        
        self._refresh_table()

    def _generate_initial_staff(self):
        """Generate initial staff for all slots"""
        self.staff_slots = []
        
        for role, level, display_name in ROLE_SLOTS:
            # Pick a random candidate and create staff
            if self.candidate_pool:
                candidate = random.choice(self.candidate_pool)
                staff = create_staff_from_candidate(candidate, role, level)
                self.staff_slots.append(staff)
                # Don't remove from pool - they can be hired elsewhere
            else:
                self.staff_slots.append(None)

    def _sync_to_team_staff(self):
        """Sync staff slots to team.staff for training bonus calculation"""
        if not self.current_team:
            return
        
        self.current_team.staff = [s for s in self.staff_slots if s is not None]

    def _refresh_table(self):
        """Refresh the staff table"""
        self.staff_table.setRowCount(len(ROLE_SLOTS))
        
        for row, (role, level, display_name) in enumerate(ROLE_SLOTS):
            staff = self.staff_slots[row] if row < len(self.staff_slots) else None
            
            # Role name
            role_item = QTableWidgetItem(display_name)
            role_item.setFlags(role_item.flags() & ~Qt.ItemIsEditable)
            self.staff_table.setItem(row, 0, role_item)
            
            if staff:
                # Name
                name_item = QTableWidgetItem(staff.name)
                self.staff_table.setItem(row, 1, name_item)
                
                # Age
                age_item = QTableWidgetItem(f"{staff.age}歳")
                age_item.setTextAlignment(Qt.AlignCenter)
                self.staff_table.setItem(row, 2, age_item)
                
                # Ability
                ability_item = QTableWidgetItem(str(staff.ability))
                ability_item.setTextAlignment(Qt.AlignCenter)
                if staff.ability >= 70:
                    ability_item.setForeground(QColor(self.theme.success))
                elif staff.ability >= 50:
                    ability_item.setForeground(QColor(self.theme.warning))
                else:
                    ability_item.setForeground(QColor(self.theme.danger))
                self.staff_table.setItem(row, 3, ability_item)
                
                # Salary - 億万形式 (salaryは円単位)
                salary_yen = staff.salary
                man = salary_yen // 10000
                if man >= 10000:
                    oku = man // 10000
                    remainder = man % 10000
                    salary_text = f"{oku}億{remainder}万" if remainder > 0 else f"{oku}億"
                else:
                    salary_text = f"{man}万"
                salary_item = QTableWidgetItem(salary_text)
                salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.staff_table.setItem(row, 4, salary_item)
            else:
                # Empty slot
                for col in range(1, 5):
                    empty_item = QTableWidgetItem("-")
                    empty_item.setTextAlignment(Qt.AlignCenter)
                    empty_item.setForeground(QColor(self.theme.text_muted))
                    self.staff_table.setItem(row, col, empty_item)
            
            # Action buttons (only for player team)
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(0)
            
            # Check if this is the player's team
            is_player_team = (self.game_state and 
                             self.game_state.player_team and 
                             self.current_team and
                             self.current_team.name == self.game_state.player_team.name)
            
            btn_layout.addStretch()  # Center: add stretch before
            if is_player_team:
                if staff:
                    # Fire button
                    fire_btn = QPushButton("解任")
                    fire_btn.setFixedSize(60, 28)
                    fire_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {self.theme.danger};
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-size: 11px;
                        }}
                    """)
                    fire_btn.clicked.connect(lambda checked, r=row: self._on_fire(r))
                    btn_layout.addWidget(fire_btn)
                else:
                    # Hire button
                    hire_btn = QPushButton("任命")
                    hire_btn.setFixedSize(60, 28)
                    hire_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {self.theme.accent_blue};
                            color: white;
                            border: none;
                            border-radius: 3px;
                            font-size: 11px;
                        }}
                    """)
                    hire_btn.clicked.connect(lambda checked, r=row: self._on_hire(r))
                    btn_layout.addWidget(hire_btn)
            
            btn_layout.addStretch()  # Center: add stretch after
            self.staff_table.setCellWidget(row, 5, btn_widget)

    def _on_hire(self, slot_index: int):
        """Handle hire button click for a specific slot"""
        role, level, display_name = ROLE_SLOTS[slot_index]
        
        if not self.candidate_pool:
            self.window().show_notification("候補者なし", "候補者プールが空です。", type="warning")
            return
        
        dialog = HireDialog(self, self.candidate_pool, role, theme=self.theme)
        if dialog.exec() and dialog.selected_candidate:
            candidate = dialog.selected_candidate
            
            # Create staff from candidate
            staff = create_staff_from_candidate(candidate, role, level)
            self.staff_slots[slot_index] = staff
            
            # Remove from candidate pool
            if candidate in self.candidate_pool:
                self.candidate_pool.remove(candidate)
            
            # Save to game state
            self._sync_to_team_staff()
            self.current_team.staff_slots = self.staff_slots
            if self.game_state:
                self.game_state.staff_candidate_pool = self.candidate_pool
            self._refresh_table()
            
            self.window().show_notification("任命完了", f"{staff.name}を{display_name}に任命しました。", type="success")

    def _on_fire(self, slot_index: int):
        """Handle fire button click for a specific slot"""
        staff = self.staff_slots[slot_index]
        if not staff:
            return
        
        role, level, display_name = ROLE_SLOTS[slot_index]
        
        reply = QMessageBox.question(
            self, "解任確認",
            f"{staff.name} ({display_name}) を解任しますか？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Add back to candidate pool (as a candidate with preserved abilities)
            candidate = {
                "name": staff.name,
                "age": staff.age,
                "base_ability": staff.ability,
                "role_abilities": {r.value: staff.ability for r in StaffRole},  # Use current ability for all
                "source": staff.source,
                "original_player_name": staff.original_player_name
            }
            self.candidate_pool.append(candidate)
            
            # Clear slot
            self.staff_slots[slot_index] = None
            
            # Save to game state
            self._sync_to_team_staff()
            self.current_team.staff_slots = self.staff_slots
            if self.game_state:
                self.game_state.staff_candidate_pool = self.candidate_pool
            self._refresh_table()
            
            self.window().show_notification("解任完了", f"{staff.name}を解任しました。", type="success")

    def add_retired_player_to_pool(self, player):
        """Add a retired player to the candidate pool"""
        candidate = generate_candidate("retired_player", player)
        self.candidate_pool.append(candidate)
        if self.game_state:
            self.game_state.staff_candidate_pool = self.candidate_pool
    
    def get_scouts(self) -> list:
        """Get all scout StaffMember objects for contracts tab sync"""
        scouts = []
        for slot_index, (role, level, display_name) in enumerate(ROLE_SLOTS):
            if role in [StaffRole.SCOUT_DOMESTIC, StaffRole.SCOUT_INTERNATIONAL]:
                staff = self.staff_slots[slot_index] if slot_index < len(self.staff_slots) else None
                if staff:
                    scouts.append(staff)
        return scouts
