"""The PhosphorWatch window: an Edge WebView2 window (via pywebview) that shows
Twitch's own pop-out player, with the Phosphor chrome drawn in HTML on top.

Python owns settings, window state and the self-updater; the page talks to it
through ``window.pywebview.api`` (the Api class) and Python pushes state back with
``window.__pwPush(...)``.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import webbrowser

from . import themes, updater, web, winapi
from .config import APP_NAME, MIN_H, MIN_W, Config, clean_channel, data_dir, profile_dir
from .version import VERSION

UPDATE_CHECK_SEC = 6 * 3600     # re-check GitHub every 6 hours while open
FIRST_CHECK_SEC = 4             # first check shortly after start-up
PLAYER_URL = "https://player.twitch.tv/?channel={}&parent=twitch.tv"   # Twitch retired /popout/<name>/player
LOGIN_URL = "https://www.twitch.tv/login"


def version_label() -> str:
    return f"v{VERSION}" if updater.parse_version(VERSION) else "(from source)"


class App:
    def __init__(self) -> None:
        self.cfg = Config()
        if self.cfg["theme"] not in themes.THEMES:
            self.cfg["theme"] = themes.DEFAULT
        self.window = None
        self.current = ""                         # channel on screen, '' on home / sign-in
        self.update_rel: updater.Release | None = None
        self.update_busy: str | None = None
        self._flash: tuple[str, float] | None = None
        self._hwnd = None
        self._closing = False

    # ------------------------------------------------------------ lifecycle
    def run(self) -> None:
        import webview   # imported here so tests don't need a GUI backend

        c = self.cfg
        self.window = webview.create_window(
            APP_NAME, html=web.home_html(), js_api=Api(self),
            width=c["width"], height=c["height"], x=c["x"], y=c["y"],
            min_size=(MIN_W, MIN_H), frameless=True, easy_drag=False,
            on_top=bool(c["on_top"]), background_color=themes.get(c["theme"])["bg"],
        )
        self.window.events.loaded += self._on_loaded
        self.window.events.closing += self._on_closing
        webview.start(self._started, gui="edgechromium", private_mode=False,
                      storage_path=str(profile_dir()), debug="--debug" in sys.argv)

    def _started(self) -> None:
        """Runs on a worker thread once the window exists."""
        try:
            result = updater.take_result()
        except OSError:
            result = None
        if result == "ok":
            self.flash(f"UPDATED TO {version_label().upper()}", 6)
        elif result == "fail":
            self.flash("UPDATE FAILED - OLD VERSION KEPT", 8)
        if self.cfg["opacity"] < 1:
            time.sleep(0.5)
            winapi.set_opacity(self.hwnd(), self.cfg["opacity"])
        threading.Thread(target=self._update_loop, daemon=True).start()

    def _on_loaded(self) -> None:
        url = self.window.get_current_url() or ""
        if "twitch.tv" in url:
            try:
                self.window.evaluate_js(web.overlay_js())
            except Exception as e:      # navigated away mid-inject etc.
                print("overlay inject failed:", e, file=sys.stderr)

    def _on_closing(self) -> None:
        self._closing = True
        try:
            w = self.window
            self.cfg.update(x=w.x, y=w.y, width=w.width, height=w.height)
        except Exception:
            pass
        self.save()

    def save(self) -> None:
        try:
            self.cfg.save()
        except OSError:
            pass

    def hwnd(self):
        if not self._hwnd:
            self._hwnd = winapi.find_own_window(APP_NAME)
        return self._hwnd

    # ---------------------------------------------------------------- state
    def state(self) -> dict:
        c = self.cfg
        s = {
            "favorites": c["favorites"], "last_channel": c["last_channel"], "theme": c["theme"],
            "on_top": c["on_top"], "opacity": c["opacity"], "user": c["user"],
            "auto_update": c["auto_update"], "current": self.current,
            "version_label": version_label(),
            "update_tag": self.update_rel.tag if self.update_rel else "",
            "update_busy": self.update_busy or "",
        }
        if self._flash and self._flash[1] > time.monotonic():
            s["flash"], s["flash_secs"] = self._flash[0], self._flash[1] - time.monotonic()
        return s

    def push(self, msg: dict) -> None:
        if self.window is None or self._closing:
            return
        try:
            self.window.evaluate_js(f"window.__pwPush && window.__pwPush({json.dumps(msg)})")
        except Exception:
            pass   # page is mid-navigation; it pulls fresh state when it loads

    def push_state(self) -> None:
        self.push({"state": self.state()})

    def flash(self, text: str, secs: float = 4.0) -> None:
        self._flash = (text, time.monotonic() + secs)
        self.push({"flash": text, "secs": secs})

    # ----------------------------------------------------------- navigation
    def watch(self, text: str) -> dict:
        name = clean_channel(text)
        if not name:
            return {"ok": False, "error": "NOT A TWITCH CHANNEL NAME"}
        self.current = name
        self.cfg["last_channel"] = name
        self.save()
        self.window.set_title(f"{APP_NAME} - {name}")
        self.window.load_url(PLAYER_URL.format(name))
        return {"ok": True}

    def go_home(self) -> None:
        self.current = ""
        self.window.set_title(APP_NAME)
        self.window.load_html(web.home_html())

    def login(self) -> None:
        self.current = ""
        self.window.load_url(LOGIN_URL)

    def logout(self) -> None:
        self.window.clear_cookies()
        self.cfg["user"] = ""
        self.save()
        self.flash("SIGNED OUT", 3)
        self.go_home()

    # --------------------------------------------------------------- window
    def set_opacity(self, value: float) -> None:
        self.cfg["opacity"] = min(1.0, max(0.3, float(value)))
        self.save()
        winapi.set_opacity(self.hwnd(), self.cfg["opacity"])
        self.push_state()

    def toggle_pin(self) -> None:
        self.cfg["on_top"] = not self.cfg["on_top"]
        self.window.on_top = self.cfg["on_top"]
        self.save()
        self.push_state()

    def quit(self) -> None:
        self.window.destroy()

    # -------------------------------------------------------------- updates
    def _update_loop(self) -> None:
        time.sleep(FIRST_CHECK_SEC)
        while not self._closing:
            # from source there's nothing to install; `git pull` updates instead
            if self.cfg["auto_update"] and updater.parse_version(VERSION) and not self.update_busy:
                self.check_updates(manual=False)
            time.sleep(UPDATE_CHECK_SEC)

    def check_updates(self, manual: bool) -> None:
        if manual:
            self.flash("CHECKING FOR UPDATES...", 10)
        try:
            rel = updater.latest_release()
        except Exception as e:
            if manual:
                self.flash((str(e) or "UPDATE CHECK FAILED").upper(), 5)
            return
        mine = updater.parse_version(VERSION)
        if rel and mine and updater.is_newer(rel.version, mine):
            self.update_rel = rel
            self.push_state()
            if manual:
                self._flash = None
                self.offer_update()
        elif manual:
            if not mine:
                self.flash(f"LATEST IS {rel.tag} - GIT PULL" if rel else "NO RELEASES YET", 6)
            else:
                self.flash(f"UP TO DATE ({version_label().upper()})", 4)
        else:
            self.push_state()

    def _dialog(self, title: str, body: str, buttons: list[tuple[str, str | None]]) -> None:
        self.push({"dialog": {"title": title, "body": body, "buttons": buttons}})

    def offer_update(self) -> None:
        rel = self.update_rel
        if rel is None or self.update_busy:
            return
        where = updater.app_dir()
        if where is None:
            self._dialog("UPDATE AVAILABLE",
                         f"{rel.tag} is out. You're running PhosphorWatch from source, so update "
                         "it with `git pull` in the repo folder (or download the zip).",
                         [("DOWNLOAD PAGE", "page"), ("OK", None)])
            return
        problem = updater.location_problem(where)
        if problem:
            self._dialog("CAN'T UPDATE HERE", problem, [("DOWNLOAD MANUALLY", "page"), ("OK", None)])
            return
        if not rel.asset_url:
            self._dialog("UPDATE AVAILABLE", f"{rel.tag} is out but has no {updater.ASSET} yet. "
                         "It may still be building - try again in a few minutes.",
                         [("DOWNLOAD PAGE", "page"), ("OK", None)])
            return
        self._dialog(f"UPDATE {rel.tag} AVAILABLE",
                     f"You have {version_label()}. PhosphorWatch will download the update, "
                     "close, swap in the new files and reopen.\n\nYour favorites, settings and "
                     "Twitch sign-in are saved separately and stay as they are.",
                     [("INSTALL", "install"), ("WHAT'S NEW", "page"), ("LATER", None)])

    def dialog_action(self, action: str) -> None:
        rel = self.update_rel
        if action == "page" and rel:
            webbrowser.open(rel.page_url)
        elif action == "install":
            self._download_and_install()

    def _download_and_install(self) -> None:
        rel = self.update_rel
        if rel is None or self.update_busy:
            return
        stage = updater.staging_dir()
        last = [-1]

        def progress(frac: float) -> None:
            pct = int(frac * 100)
            if pct != last[0]:
                last[0] = pct
                self.update_busy = f"DOWNLOADING {pct}%"
                self.push_state()

        progress(0.0)
        try:
            stage.mkdir(parents=True, exist_ok=True)
            z = updater.download(rel, stage / updater.ASSET, progress=progress)
            new = updater.extract(z, stage / "new")
            self.update_busy = "INSTALLING..."
            self.push_state()
            bat = updater.write_helper(stage, updater.app_dir(), new, rel.tag, os.getpid())
            updater.launch_helper(bat)
        except Exception as e:
            self.update_busy = None
            msg = str(e) if isinstance(e, updater.UpdateError) else type(e).__name__.upper()
            self.flash(f"UPDATE FAILED: {msg}", 8)
            self.push_state()
            return
        self.quit()          # the helper waits for us to exit, then swaps files and restarts us

    def open_data_folder(self) -> None:
        winapi.open_folder(data_dir())


class Api:
    """Everything the page may call, as window.pywebview.api.<name>(...).
    pywebview runs each call on its own worker thread."""

    def __init__(self, app: App) -> None:
        self._app = app

    # state
    def get_state(self):
        return self._app.state()

    def page_ready(self):
        return True

    def set_theme(self, key):
        a = self._app
        if key in themes.THEMES:
            a.cfg["theme"] = key
            a.save()
        a.push_state()

    def set_user(self, name):
        a = self._app
        name = clean_channel(name)
        if name and name != a.cfg["user"]:
            a.cfg["user"] = name
            a.save()
            a.push_state()

    # navigation
    def watch(self, text):
        return self._app.watch(text)

    def go_home(self):
        self._app.go_home()

    def login(self):
        self._app.login()

    def logout(self):
        self._app.logout()

    # favorites
    def add_favorite(self, text):
        a = self._app
        name = clean_channel(text)
        if not name:
            return {"ok": False, "error": "NOT A TWITCH CHANNEL NAME"}
        if name in a.cfg["favorites"]:
            return {"ok": False, "error": "ALREADY A FAVORITE"}
        a.cfg["favorites"].append(name)
        a.save()
        a.push_state()
        return {"ok": True}

    def remove_favorite(self, name):
        a = self._app
        if name in a.cfg["favorites"]:
            a.cfg["favorites"].remove(name)
            a.save()
        a.push_state()

    def move_favorite(self, name, delta):
        a = self._app
        favs = a.cfg["favorites"]
        if name in favs:
            i = favs.index(name)
            j = max(0, min(len(favs) - 1, i + int(delta)))
            favs.insert(j, favs.pop(i))
            a.save()
        a.push_state()

    # window
    def toggle_pin(self):
        self._app.toggle_pin()

    def set_opacity(self, value):
        self._app.set_opacity(value)

    def minimize(self):
        self._app.window.minimize()

    def close(self):
        self._app.quit()

    def get_geometry(self):
        w = self._app.window
        return {"x": w.x, "y": w.y, "width": w.width, "height": w.height}

    def set_geometry(self, x, y, width, height):
        w = self._app.window
        width, height = max(MIN_W, int(width)), max(MIN_H, int(height))
        if (width, height) != (w.width, w.height):
            w.resize(width, height)
        if (int(x), int(y)) != (w.x, w.y):
            w.move(int(x), int(y))

    def save_geometry(self):
        a = self._app
        w = a.window
        a.cfg.update(x=w.x, y=w.y, width=w.width, height=w.height)
        a.save()

    # updates / misc
    def check_updates(self, manual=True):
        self._app.check_updates(bool(manual))

    def toggle_auto_update(self):
        a = self._app
        a.cfg["auto_update"] = not a.cfg["auto_update"]
        a.save()
        a.push_state()

    def offer_update(self):
        self._app.offer_update()

    def dialog_action(self, action):
        self._app.dialog_action(action)

    def open_data_folder(self):
        self._app.open_data_folder()
