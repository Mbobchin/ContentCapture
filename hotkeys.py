"""Global hotkey manager.

Bridges the `keyboard` library's background-thread callbacks to a Qt signal
so all action handlers always run on the Qt main thread.
"""
from PySide6.QtCore import QObject, Signal


class GlobalHotkeyManager(QObject):
    """Bridges the `keyboard` library's background-thread callbacks to Qt signals.

    All public methods are safe to call from the Qt main thread.
    Callbacks emitted by `keyboard` are forwarded via Signal so they always
    arrive on the main thread regardless of which thread the hook fires on.
    """
    triggered = Signal(str)   # emits the action_key string, e.g. "save_clip"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered = {}   # action_key -> hotkey string currently registered
        self._enabled = False
        try:
            import keyboard as _kb
            self._kb = _kb
        except ImportError:
            self._kb = None
            print("[GlobalHotkey] 'keyboard' package not installed — global hotkeys unavailable")

    def is_available(self) -> bool:
        """Return True only when the `keyboard` library could be imported."""
        return self._kb is not None

    def register(self, action_key: str, key_str: str):
        """Register (or replace) the global hotkey for *action_key*.

        Safe to call multiple times; the old binding for the same action is
        removed first.  No-ops if the manager is disabled or unavailable.
        """
        if not self._kb or not self._enabled:
            return
        # Remove any previous binding for this action
        old = self._registered.get(action_key)
        if old:
            try:
                self._kb.remove_hotkey(old)
            except Exception:
                pass
        if not key_str:
            return
        try:
            # The lambda captures action_key by value (a=action_key).
            # Signal.emit() is thread-safe, so calling it from the keyboard
            # hook thread is explicitly allowed.
            self._kb.add_hotkey(
                key_str,
                lambda a=action_key: self.triggered.emit(a),
                suppress=False,
            )
            self._registered[action_key] = key_str
        except Exception as e:
            print(f"[GlobalHotkey] Failed to register '{key_str}' for '{action_key}': {e}")

    def unregister_all(self):
        """Remove every registered global hotkey.  Safe to call when disabled."""
        if not self._kb:
            return
        for key_str in list(self._registered.values()):
            try:
                self._kb.remove_hotkey(key_str)
            except Exception:
                pass
        self._registered.clear()

    def set_enabled(self, enabled: bool):
        """Enable or disable global hotkeys.  Disabling also unregisters all hooks."""
        self._enabled = enabled
        if not enabled:
            self.unregister_all()
