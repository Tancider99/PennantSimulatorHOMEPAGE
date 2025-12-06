# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Starfield Inspired Theme System
NASAPunk / Industrial Sci-Fi Aesthetic
"""
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget
from PySide6.QtGui import QColor, QPalette
from dataclasses import dataclass

@dataclass
class Theme:
    """Starfield-like Industrial Sci-Fi Theme"""

    # === Main Colors (Void & Industrial Materials) ===
    bg_darkest: str = "#0b0c10"       # Deep Space Black
    bg_dark: str = "#141619"          # Main Background
    bg_card: str = "#1e2126"          # Panel Background
    bg_card_elevated: str = "#262a30" # Elevated Surface
    bg_card_hover: str = "#323842"    # Hover State
    bg_sidebar: str = "#0b0c10"       # Sidebar background
    
    # === Compatibility Aliases (Fixes AttributeError) ===
    bg_hover: str = "#323842"         # Alias for bg_card_hover
    bg_selected: str = "#2c313a"      # Selection background
    
    # === Accents (HUD & Constellation) ===
    primary: str = "#ffffff"          # Active/Highlight (Pure White)
    primary_hover: str = "#e0e0e0"
    primary_dark: str = "#cccccc"
    primary_light: str = "#ffffff"    # Bright white alias
    
    accent_blue: str = "#5fbcd3"      # HUD Cyan/Blue
    accent_orange: str = "#d65d0e"    # Industrial Orange
    accent_red: str = "#cc241d"       # Alert Red
    
    # === Text Colors (High Contrast) ===
    text_primary: str = "#f0f0f0"     # Main Text
    text_secondary: str = "#9da5b4"   # Secondary Text (Industrial Grey)
    text_muted: str = "#5c6370"       # Muted/Disabled
    text_highlight: str = "#0b0c10"   # Text on White Background
    text_accent: str = "#5fbcd3"      # Accent text color
    text_link: str = "#5fbcd3"        # Link color

    # === Borders (Technical Lines) ===
    border: str = "#3e4451"
    border_light: str = "#4e5766"
    border_muted: str = "#2c313a"     # Subtler border
    border_focus: str = "#ffffff"
    
    # === Status Colors & Variations ===
    success: str = "#98c379"
    success_light: str = "#b5d49d"
    success_hover: str = "#86b366"
    
    warning: str = "#e5c07b"
    warning_light: str = "#ebd09e"
    warning_hover: str = "#d1ad6b"
    
    danger: str = "#e06c75"
    danger_light: str = "#ea959b"
    danger_hover: str = "#d65560"
    
    info: str = "#61afef"
    info_light: str = "#8dc5f4"
    info_hover: str = "#4d9fe8"

    # === Premium/Metal Colors ===
    gold: str = "#d65d0e"             # Map Gold to Orange
    silver: str = "#9da5b4"
    bronze: str = "#8f5e38"
    accent_gold: str = "#d65d0e"      # Alias

    # === UI Elements ===
    bg_overlay: str = "#000000dd"
    bg_input: str = "#0b0c10"
    bg_header: str = "#141619"

    # === Team Colors (NPB) ===
    central_league: str = "#5fbcd3"
    pacific_league: str = "#e06c75"

    # === NPB Rating Colors ===
    rating_s: str = "#ff6b6b"   # S Rank
    rating_a: str = "#ffa726"   # A Rank
    rating_b: str = "#ffd700"   # B Rank
    rating_c: str = "#ffee58"   # C Rank
    rating_d: str = "#66bb6a"   # D Rank
    rating_e: str = "#42a5f5"   # E Rank
    rating_f: str = "#bdbdbd"   # F Rank
    rating_g: str = "#757575"   # G Rank

    # === Metrics (Sharp corners for Starfield style) ===
    radius_small: int = 0
    radius_medium: int = 0
    radius_large: int = 2
    
    shadow_color: str = "#000000"
    shadow_blur: int = 10

    @property
    def accent(self) -> str:
        return self.accent_blue

    @staticmethod
    def get_rating_color(value: int) -> str:
        t = Theme()
        if value >= 90: return t.rating_s
        elif value >= 80: return t.rating_a
        elif value >= 70: return t.rating_b
        elif value >= 60: return t.rating_c
        elif value >= 50: return t.rating_d
        elif value >= 40: return t.rating_e
        elif value >= 30: return t.rating_f
        else: return t.rating_g
        
    @staticmethod
    def get_rating_rank(value: int) -> str:
        if value >= 90: return "S"
        elif value >= 80: return "A"
        elif value >= 70: return "B"
        elif value >= 60: return "C"
        elif value >= 50: return "D"
        elif value >= 40: return "E"
        elif value >= 30: return "F"
        else: return "G"

class ThemeManager:
    """Manages application theming"""

    _instance = None
    _theme = Theme()
    _current_scale = 1.0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_theme(cls) -> Theme:
        return cls._theme

    @classmethod
    def set_scale(cls, scale: float):
        cls._current_scale = scale

    @classmethod
    def apply_theme(cls, app: QApplication):
        theme = cls._theme
        palette = QPalette()
        
        # Base setup
        palette.setColor(QPalette.Window, QColor(theme.bg_dark))
        palette.setColor(QPalette.WindowText, QColor(theme.text_primary))
        palette.setColor(QPalette.Base, QColor(theme.bg_input))
        palette.setColor(QPalette.AlternateBase, QColor(theme.bg_card))
        palette.setColor(QPalette.Text, QColor(theme.text_primary))
        palette.setColor(QPalette.Button, QColor(theme.bg_card))
        palette.setColor(QPalette.ButtonText, QColor(theme.text_primary))
        palette.setColor(QPalette.Highlight, QColor(theme.primary))
        palette.setColor(QPalette.HighlightedText, QColor(theme.text_highlight))
        
        app.setPalette(palette)
        app.setStyleSheet(cls.get_stylesheet())

    @classmethod
    def get_stylesheet(cls) -> str:
        t = cls._theme
        
        return f"""
        * {{
            font-family: "Yu Gothic UI", "Meiryo UI", sans-serif;
            outline: none;
        }}
        QMainWindow, QDialog, QWidget {{
            background-color: {t.bg_dark};
            color: {t.text_primary};
        }}
        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {t.bg_darkest};
            width: 12px; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background-color: {t.border_light};
            min-height: 40px; margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {t.primary};
        }}
        QScrollBar:horizontal {{
            background-color: {t.bg_darkest};
            height: 12px; margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {t.border_light};
            min-width: 40px; margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {t.primary};
        }}
        
        /* Buttons - Sharp Industrial Style */
        QPushButton {{
            background-color: {t.bg_card};
            color: {t.text_primary};
            border: 1px solid {t.border};
            border-radius: 0px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        QPushButton:hover {{
            background-color: {t.bg_card_hover};
            border-color: {t.primary};
            color: {t.primary};
        }}
        QPushButton:pressed {{
            background-color: {t.primary};
            color: {t.text_highlight};
        }}
        QPushButton:disabled {{
            color: {t.text_muted};
            background-color: {t.bg_darkest};
            border-color: {t.bg_card};
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {t.border};
            background-color: {t.bg_dark};
            border-top: 1px solid {t.primary};
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {t.text_secondary};
            padding: 8px 16px;
            border: none;
            font-weight: 600;
            text-transform: uppercase;
        }}
        QTabBar::tab:selected {{
            color: {t.primary};
            border-bottom: 2px solid {t.primary};
        }}
        """

    @classmethod
    def create_shadow_effect(cls, widget: QWidget, blur: int = 10, color: str = None):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(color or "#000000"))
        effect.setOffset(0, 2)
        widget.setGraphicsEffect(effect)
        return effect

def get_theme() -> Theme:
    return ThemeManager.get_theme()