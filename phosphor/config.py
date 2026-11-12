"""Settings persisted as JSON in %APPDATA%\\PhosphorWatch (or ~/.phosphorwatch).

The WebView profile (Twitch sign-in cookies) lives next to it in webview_profile\\,
outside the install folder, so updates never sign you out.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

APP_NAME = "PhosphorWatch"


def data_dir() -> Path:
    base = os.environ.get("PHOSPHOR_WATCH_DATA")
    if base:
        p = Path(base)
    elif os.name == "nt":
        p = Path(os.environ.get("APPDATA", Path.home())) / "PhosphorWatch"
    else:
        p = Path.home() / ".phosphorwatch"
    p.mkdir(parents=True, exist_ok=True)
    return p


def profile_dir() -> Path:
    p = data_dir() / "webview_profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


DEFAULTS: dict = {
    "x": None,                    # None = let Windows centre the first window
    "y": None,
    "width": 640,
    "height": 400,
    "opacity": 1.0,
    "theme": "green",             # see phosphor/themes.py
    "on_top": True,
    "favorites": [],
    "last_channel": "",
    "user": "",                   # Twitch login name, read from the sign-in cookie
    "auto_update": True,          # check GitHub for a newer release at startup / every few hours
    "config_version": 1,
}

MIN_W, MIN_H = 240, 140
OPACITIES = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)

_CHANNEL_RE = re.compile(r"^[A-Za-z0-9_]{1,25}$")


def clean_channel(text: str | None) -> str:
    """'name', '@Name', or any twitch.tv/name link -> 'name'. Anything else -> ''."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    m = re.search(r"twitch\.tv/(?:popout/)?([A-Za-z0-9_]+)", text, re.I)
    if m:
        text = m.group(1)
    text = text.lstrip("@").strip("/")
    return text.lower() if _CHANNEL_RE.match(text) else ""


class Config(dict):
    def __init__(self) -> None:
        super().__init__(json.loads(json.dumps(DEFAULTS)))
        self.path = data_dir() / "config.json"
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            for k, v in saved.items():
                if k in DEFAULTS:
                    self[k] = v
        except (OSError, ValueError):
            pass
        self._sanitize()

    def _sanitize(self) -> None:
        favs = self.get("favorites")
        favs = [clean_channel(f) for f in favs] if isinstance(favs, list) else []
        self["favorites"] = list(dict.fromkeys(f for f in favs if f))
        try:
            self["opacity"] = min(1.0, max(0.3, float(self["opacity"])))
        except (TypeError, ValueError):
            self["opacity"] = 1.0
        for k, lo in (("width", MIN_W), ("height", MIN_H)):
            try:
                self[k] = max(lo, int(self[k]))
            except (TypeError, ValueError):
                self[k] = DEFAULTS[k]
        for k in ("x", "y"):
            if not isinstance(self[k], int):
                self[k] = None

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self, indent=2), encoding="utf-8")
        tmp.replace(self.path)
