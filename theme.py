"""Colour palette and Qt stylesheet.

Importing this module does not touch Qt — STYLESHEET is just a string.
"""

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
C = {
    # Layered backgrounds — deep navy/charcoal
    "bg":           "#0d0d1e",
    "bg2":          "#0f0f22",
    "panel":        "#12122a",
    "panel2":       "#171730",
    "panel3":       "#1c1c38",
    "card":         "#191932",
    # Borders
    "border":       "#22224a",
    "border2":      "#2e2e58",
    # Accent — cyan/blue brand colour
    "accent":       "#00d4ff",
    "accent2":      "#0099cc",
    "accent_dim":   "#0099cc",
    "accent_glow":  "#00d4ff33",
    # State indicators
    "live":         "#00e676",
    "danger":       "#f5284a",
    "warning":      "#ffb300",
    "record":       "#f5284a",
    "clip":         "#ff9f43",
    "screenshot":   "#c44dff",
    "good":         "#00e676",
    "warn":         "#ffb300",
    "bad":          "#f5284a",
    # Typography
    "text":         "#e8e8f4",
    "text2":        "#9898c0",
    "subtext":      "#484870",
    # Interactive surfaces
    "hover":        "#1e1e42",
    "hover2":       "#26264e",
    "selected":     "#00d4ff1a",
    # Toolbar / dock
    "toolbar":      "#0f0f28",
    "statusbar":    "#0a0a1a",
}

# ── STYLESHEET ────────────────────────────────────────────────────────────────
STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QDialog, QWidget {{
    background: {C["bg"]};
    color: {C["text"]};
    font-family: 'Segoe UI';
    font-size: 10pt;
}}

/* ── Menu Bar ── */
QMenuBar {{
    background: {C["panel"]};
    color: {C["text"]};
    border-bottom: 1px solid {C["border"]};
    padding: 1px 6px;
    spacing: 2px;
    font-size: 10pt;
}}
QMenuBar::item {{
    padding: 5px 12px;
    border-radius: 6px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {C["hover2"]};
    color: {C["accent"]};
}}
QMenuBar::item:pressed {{
    background: {C["hover2"]};
    color: {C["accent"]};
}}

/* ── Menus ── */
QMenu {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 8px;
    padding: 6px 4px;
    font-size: 10pt;
}}
QMenu::item {{
    padding: 7px 32px 7px 16px;
    border-radius: 6px;
    margin: 1px 4px;
}}
QMenu::item:selected {{
    background: {C["hover2"]};
    color: {C["accent"]};
}}
QMenu::item:disabled {{
    color: {C["subtext"]};
}}
QMenu::separator {{
    height: 1px;
    background: {C["border"]};
    margin: 5px 12px;
}}
QMenu::indicator {{
    width: 16px;
    height: 16px;
    left: 6px;
}}

/* ── Toolbar ── */
QToolBar {{
    background: {C["toolbar"]};
    border: none;
    border-bottom: 1px solid {C["border"]};
    padding: 3px 6px;
    spacing: 3px;
}}
QToolBar::separator {{
    background: {C["border2"]};
    width: 1px;
    margin: 5px 6px;
}}
QToolButton {{
    background: transparent;
    color: {C["text"]};
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 9pt;
    font-weight: 600;
    min-width: 52px;
}}
QToolButton:hover {{
    background: {C["hover2"]};
    border-color: {C["border2"]};
    color: {C["accent"]};
}}
QToolButton:pressed {{
    background: {C["panel"]};
    border-color: {C["accent2"]};
    color: {C["accent"]};
}}
QToolButton:checked {{
    background: {C["selected"]};
    border-color: {C["accent"]};
    color: {C["accent"]};
}}
QToolButton:disabled {{
    color: {C["subtext"]};
    background: transparent;
}}

/* ── Buttons ── */
QPushButton {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 8px;
    padding: 7px 20px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background: {C["hover2"]};
    border-color: {C["accent"]};
    color: {C["accent"]};
}}
QPushButton:pressed {{
    background: {C["panel"]};
    border-color: {C["accent2"]};
    color: {C["accent2"]};
}}
QPushButton:focus {{
    border-color: {C["accent"]};
    outline: none;
}}
QPushButton:disabled {{
    background: {C["panel"]};
    color: {C["subtext"]};
    border-color: {C["border"]};
}}
QPushButton#accent {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {C["accent"]}, stop:1 {C["accent2"]});
    color: #000c14;
    border: none;
    font-weight: bold;
    font-size: 10pt;
}}
QPushButton#accent:hover {{
    background: {C["accent"]};
    color: #000;
}}
QPushButton#accent:pressed {{
    background: {C["accent2"]};
    color: #000;
}}
QPushButton#accent:disabled {{
    background: {C["border"]};
    color: {C["subtext"]};
}}
QPushButton#danger {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #f53050, stop:1 #c01030);
    color: #fff;
    border: none;
    font-weight: bold;
}}
QPushButton#danger:hover {{
    background: {C["danger"]};
}}
QPushButton#danger:pressed {{
    background: #a00020;
}}

/* ── Sliders ── */
QSlider {{ min-height: 26px; }}
QSlider::groove:horizontal {{
    height: 5px;
    background: {C["border"]};
    border-radius: 3px;
    margin: 0 4px;
}}
QSlider::handle:horizontal {{
    background: {C["accent"]};
    width: 18px;
    height: 18px;
    margin: -7px -4px;
    border-radius: 9px;
    border: 2px solid {C["bg"]};
}}
QSlider::handle:horizontal:hover {{
    background: #40e8ff;
    border-color: {C["accent"]};
}}
QSlider::handle:horizontal:focus {{
    border-color: #fff;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {C["accent2"]}, stop:1 {C["accent"]});
    border-radius: 3px;
}}
QSlider::groove:horizontal:disabled {{
    background: {C["border"]};
}}
QSlider::handle:horizontal:disabled {{
    background: {C["subtext"]};
}}

/* ── ComboBox ── */
QComboBox {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    padding: 6px 12px;
    min-height: 30px;
    font-size: 10pt;
}}
QComboBox:hover {{ border-color: {C["accent"]}; }}
QComboBox:focus {{ border-color: {C["accent"]}; background: {C["panel3"]}; outline: none; }}
QComboBox:disabled {{ color: {C["subtext"]}; border-color: {C["border"]}; }}
QComboBox::drop-down {{
    border: none;
    width: 28px;
    border-left: 1px solid {C["border"]};
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 10px; height: 10px;
}}
QComboBox QAbstractItemView {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    selection-background-color: {C["hover2"]};
    selection-color: {C["accent"]};
    padding: 4px;
    outline: none;
}}

/* ── CheckBox / RadioButton ── */
QCheckBox {{
    color: {C["text"]};
    spacing: 10px;
    padding: 4px 0;
    font-size: 10pt;
}}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid {C["border2"]};
    border-radius: 5px;
    background: {C["panel2"]};
}}
QCheckBox::indicator:hover {{ border-color: {C["accent"]}; }}
QCheckBox::indicator:focus {{ border-color: {C["accent"]}; }}
QCheckBox::indicator:checked {{
    background: {C["accent"]};
    border-color: {C["accent"]};
}}
QCheckBox::indicator:checked:hover {{ background: #40e8ff; }}
QRadioButton {{
    color: {C["text"]};
    spacing: 10px;
    padding: 4px 0;
    font-size: 10pt;
}}
QRadioButton::indicator {{
    width: 17px; height: 17px;
    border: 2px solid {C["border2"]};
    border-radius: 9px;
    background: {C["panel2"]};
}}
QRadioButton::indicator:hover {{ border-color: {C["accent"]}; }}
QRadioButton::indicator:checked {{
    background: {C["accent"]};
    border-color: {C["accent"]};
}}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {C["border"]};
    border-radius: 10px;
    margin-top: 16px;
    padding: 12px 10px 10px 10px;
    background: {C["card"]};
    color: {C["accent"]};
    font-weight: bold;
    font-size: 9pt;
    letter-spacing: 0.5px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: -1px;
    padding: 1px 8px;
    background: {C["card"]};
    border-radius: 4px;
}}

/* ── Labels ── */
QLabel {{
    color: {C["text"]};
    background: transparent;
    font-size: 10pt;
}}

/* ── LineEdit ── */
QLineEdit {{
    background: {C["panel2"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    padding: 7px 12px;
    color: {C["text"]};
    selection-background-color: {C["accent2"]};
    font-size: 10pt;
    min-height: 30px;
}}
QLineEdit:focus {{ border-color: {C["accent"]}; background: {C["panel3"]}; outline: none; }}
QLineEdit:disabled {{ color: {C["subtext"]}; border-color: {C["border"]}; }}

/* ── SpinBox / DoubleSpinBox ── */
QSpinBox, QDoubleSpinBox {{
    background: {C["panel2"]};
    border: 1px solid {C["border2"]};
    border-radius: 7px;
    padding: 6px 10px;
    color: {C["text"]};
    min-height: 30px;
    font-size: 10pt;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {C["accent"]}; outline: none; }}
QSpinBox:disabled, QDoubleSpinBox:disabled {{ color: {C["subtext"]}; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 20px;
    border: none;
    background: {C["panel3"]};
    border-radius: 4px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {C["hover2"]};
}}

/* ── ListWidget ── */
QListWidget {{
    background: {C["panel2"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    color: {C["text"]};
    padding: 4px;
    outline: none;
}}
QListWidget::item {{ padding: 6px 10px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {C["hover2"]}; color: {C["accent"]}; }}
QListWidget::item:hover {{ background: {C["hover"]}; }}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: {C["bg2"]};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["border2"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C["accent2"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C["bg2"]};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {C["border2"]};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {C["accent2"]}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Dock Widget ── */
QDockWidget {{
    color: {C["text"]};
    font-size: 10pt;
    font-weight: bold;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}}
QDockWidget::title {{
    background: {C["panel2"]};
    padding: 6px 12px;
    border-bottom: 1px solid {C["border"]};
    text-align: left;
}}
QDockWidget::close-button, QDockWidget::float-button {{
    background: transparent;
    border: none;
    padding: 2px;
    border-radius: 4px;
}}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background: {C["hover2"]};
}}

/* ── Status Bar ── */
QStatusBar {{
    background: {C["statusbar"]};
    color: {C["text2"]};
    border-top: 1px solid {C["border"]};
    padding: 0 8px;
    font-size: 9pt;
}}
QStatusBar::item {{
    border: none;
}}
QStatusBar QLabel {{
    color: {C["text2"]};
    font-size: 9pt;
    padding: 0 6px;
    background: transparent;
}}

/* ── Frame separators ── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {C["border2"]};
}}

/* ── Tooltip ── */
QToolTip {{
    background: {C["panel2"]};
    color: {C["text"]};
    border: 1px solid {C["accent2"]};
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 9pt;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background: {C["border"]};
}}
QSplitter::handle:horizontal {{
    width: 3px;
    border-radius: 2px;
}}
QSplitter::handle:hover {{
    background: {C["accent2"]};
}}
"""
