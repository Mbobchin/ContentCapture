"""Hotkey remapping dialog — local + global hotkeys."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QKeySequenceEdit, QWidget,
)

from config import save_config
from constants import HOTKEY_ACTIONS
from theme import C
from ui.dialogs.base import BaseDialog


class HotkeyDialog(BaseDialog):
    # Re-export for legacy callers that referenced HotkeyDialog.ACTIONS
    ACTIONS = HOTKEY_ACTIONS

    def __init__(self, parent, cfg):
        super().__init__(parent, "Hotkey Remapping")
        self.cfg = cfg
        self.setMinimumWidth(660)
        self.setMinimumHeight(560)

        # Grab GlobalHotkeyManager from parent window (may be None)
        self._global_hk = getattr(parent, "_global_hk", None)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        hdr = QLabel("\u2328  HOTKEY REMAPPING")
        hdr.setStyleSheet(
            f"color:{C['accent']};font-size:13pt;font-weight:bold;"
            f"letter-spacing:1.5px;background:transparent;"
        )
        layout.addWidget(hdr)
        layout.addWidget(self._divider())

        # ── Global Hotkeys group box ──────────────────────────────────────────
        global_box = QGroupBox("Global Hotkeys")
        global_box_layout = QVBoxLayout(global_box)
        global_box_layout.setContentsMargins(12, 10, 12, 10)
        global_box_layout.setSpacing(6)

        self._global_master_cb = QCheckBox(
            "Enable global hotkeys (work while app is not focused)"
        )
        self._global_master_cb.setChecked(cfg.get("global_hotkeys_enabled", False))
        global_box_layout.addWidget(self._global_master_cb)

        global_note = QLabel(
            "Check the \u201cGlobal\u201d column below to make individual actions fire even when "
            "another window (e.g. a game) is in the foreground."
        )
        global_note.setWordWrap(True)
        global_note.setStyleSheet(f"color:{C['text2']};font-size:9pt;background:transparent;")
        global_box_layout.addWidget(global_note)

        if self._global_hk is not None and not self._global_hk.is_available():
            global_box.setEnabled(False)
            global_box.setToolTip(
                "Install the 'keyboard' package to enable global hotkeys  "
                "(pip install keyboard)"
            )

        layout.addWidget(global_box)

        note = QLabel(
            "Click a key field and press the desired combination to remap it. "
            "Click Reset to restore the factory default for that action."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{C['text2']};font-size:9pt;background:transparent;")
        layout.addWidget(note)

        # ── Hotkey table — 4 columns: Action | Key Binding | Global | Reset ──
        self._table = QTableWidget(len(self.ACTIONS), 4, self)
        self._table.setHorizontalHeaderLabels(["Action", "Key Binding", "Global", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._table.setColumnWidth(2, 64)
        self._table.setColumnWidth(3, 80)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setStyleSheet(
            f"QTableWidget{{background:{C['panel2']};border:1px solid {C['border']};"
            f"border-radius:8px;gridline-color:{C['border']};}}"
            f"QTableWidget::item{{padding:4px 8px;}}"
            f"QHeaderView::section{{background:{C['panel3']};color:{C['accent']};"
            f"border:none;border-bottom:1px solid {C['border2']};"
            f"padding:6px 8px;font-weight:bold;font-size:9pt;}}"
        )

        hotkeys = cfg.get("hotkeys", {})
        global_actions = set(cfg.get("global_hotkey_actions", []))
        global_enabled = cfg.get("global_hotkeys_enabled", False)
        hk_available = self._global_hk is not None and self._global_hk.is_available()

        self._edits = {}
        self._global_cbs = {}

        for row, (key, name, default) in enumerate(self.ACTIONS):
            current = hotkeys.get(key, default)

            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor(C["text"]))
            self._table.setItem(row, 0, name_item)

            edit = QKeySequenceEdit(QKeySequence(current), self)
            edit.setStyleSheet(
                f"QKeySequenceEdit{{background:{C['panel3']};color:{C['text']};"
                f"border:1px solid {C['border2']};border-radius:6px;"
                f"padding:4px 8px;font-size:10pt;}}"
                f"QKeySequenceEdit:focus{{border-color:{C['accent']};}}"
            )
            self._table.setCellWidget(row, 1, edit)
            self._edits[key] = edit

            global_cb = QCheckBox()
            global_cb.setChecked(key in global_actions)
            global_cb.setEnabled(global_enabled and hk_available)
            global_cb.setToolTip(
                "Fire this action even when the app is not focused"
                if hk_available
                else "Install the 'keyboard' package to enable global hotkeys"
            )
            cb_container = QWidget()
            cb_inner = QHBoxLayout(cb_container)
            cb_inner.setContentsMargins(0, 0, 0, 0)
            cb_inner.setAlignment(Qt.AlignCenter)
            cb_inner.addWidget(global_cb)
            self._table.setCellWidget(row, 2, cb_container)
            self._global_cbs[key] = global_cb

            reset_btn = QPushButton("Reset")
            reset_btn.setFixedHeight(28)
            reset_btn.setStyleSheet(
                f"QPushButton{{background:{C['panel3']};color:{C['text2']};"
                f"border:1px solid {C['border2']};border-radius:5px;"
                f"padding:0 8px;font-size:9pt;}}"
                f"QPushButton:hover{{background:{C['hover2']};color:{C['accent']};"
                f"border-color:{C['accent']};}}"
            )
            reset_btn.clicked.connect(
                lambda checked, d=default, e=edit: e.setKeySequence(QKeySequence(d))
            )
            btn_container = QWidget()
            btn_inner = QHBoxLayout(btn_container)
            btn_inner.setContentsMargins(4, 2, 4, 2)
            btn_inner.addWidget(reset_btn)
            self._table.setCellWidget(row, 3, btn_container)
            self._table.setRowHeight(row, 38)

        layout.addWidget(self._table)

        # Wire master checkbox → enable/disable per-row global checkboxes
        self._global_master_cb.toggled.connect(self._on_global_master_toggled)

        reset_row = QHBoxLayout()
        reset_all = QPushButton("\u21ba  Reset All to Defaults")
        reset_all.setToolTip("Restore every action to its factory default key")
        reset_all.clicked.connect(self._reset_all)
        reset_row.addStretch()
        reset_row.addWidget(reset_all)
        layout.addLayout(reset_row)
        layout.addLayout(self._buttons("Save"))

    def _on_global_master_toggled(self, checked: bool):
        hk_available = self._global_hk is not None and self._global_hk.is_available()
        for cb in self._global_cbs.values():
            cb.setEnabled(checked and hk_available)

    def _reset_all(self):
        for key, name, default in self.ACTIONS:
            self._edits[key].setKeySequence(QKeySequence(default))

    def accept(self):
        hotkeys = self.cfg.setdefault("hotkeys", {})
        for key, name, default in self.ACTIONS:
            seq = self._edits[key].keySequence()
            hotkeys[key] = seq.toString() if not seq.isEmpty() else default
        self.cfg["hotkeys"] = hotkeys

        self.cfg["global_hotkeys_enabled"] = self._global_master_cb.isChecked()
        self.cfg["global_hotkey_actions"] = [
            key for key, cb in self._global_cbs.items() if cb.isChecked()
        ]

        save_config(self.cfg)
        parent = self.parent()
        if parent and hasattr(parent, "_bind_shortcuts"):
            parent._bind_shortcuts()
        if parent and hasattr(parent, "_apply_global_hotkeys"):
            parent._apply_global_hotkeys()
        super().accept()
