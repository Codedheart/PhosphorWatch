# PhosphorWatch

A small always-on-top, resizable window that plays **one Twitch stream**, so you don't need a
browser tab open. Same CRT-terminal look and 18 color palettes as
[Phosphor XP](https://github.com/Codedheart/PhosphorXP) and
[Phosphor Count](https://github.com/Codedheart/PhosphorCount).

```
PHOSPHOR-WATCH > SHROUD              ⌂ ≡ ⊥ _ ✕    <- bar slides in when you move the mouse
┌───────────────────────────────────────────┐
│                                           │
│          Twitch's own pop-out player      │
│                                           │
└───────────────────────────────────────────┘
```

## Download (no Python needed)

**[⬇ Download the latest version](../../releases/latest)**, then grab **`PhosphorWatch-windows.zip`**
under *Assets*. Right-click it, **Extract All…**, then double-click **`PhosphorWatch.exe`**. If Windows
says "Windows protected your PC", click **More info**, then **Run anyway**.

It runs on Microsoft Edge **WebView2**, which Windows 10 and 11 already include.

## How it works

| | |
|---|---|
| Channel box | Type a channel name or paste any `twitch.tv/...` link, **Enter** or **WATCH** |
| **+** | Save the channel to **Favorites**. Click a favorite to watch it; hover it for ▲ ▼ ✕ |
| **SIGN IN TO TWITCH >** | Opens Twitch's sign-in page in the window. Once you're in, it returns to the channel screen |
| Move the mouse over the stream | The bar slides in: drag the title to move, **⌂** channels, **≡** menu, pin = always on top, minimize, close |
| Right / bottom edge, corner | Resize |
| Right-click the bar (or **≡**) | Palette, opacity, always on top, sign in / out, check for updates, open settings folder, exit |

### Ads and your account

PhosphorWatch plays Twitch's own player, so it shows exactly what a browser shows. Sign in once and
your account's benefits apply: channels you're **subscribed** to (or everything with **Turbo**) play
without ads. It doesn't block ads.

You sign in **inside PhosphorWatch**, not through Chrome or Edge. Browsers keep their logins to
themselves, so no other app can use them. The sign-in is saved in
`%APPDATA%\PhosphorWatch\webview_profile`, so you only do it once. **Sign out** in the menu clears it.

## Updates

The downloaded app checks GitHub for a newer release when it starts (and every few hours). When
there is one, the header shows **UPDATE v1.x >**. Click it, then **INSTALL**: it downloads the
new zip, checks it, closes, swaps in the new files and reopens. If anything goes wrong it puts the
old version back. The menu has **Check for updates** and an option to turn automatic checks off.

Favorites, settings and the Twitch sign-in are stored in `%APPDATA%\PhosphorWatch`, not in the app
folder, so updates never touch them.

The app has to be able to change its own folder, so keep it somewhere you own, like
**Documents** or the **Desktop**. If it's in Program Files (or was opened straight from inside the
zip) it tells you that and where to move it instead of trying.

Releasing: push a tag like `v1.3`. The version shown in the app comes from that tag.

## Run from source

Needs Python 3.10+ from [python.org](https://www.python.org/downloads/). Double-click **`run.bat`**:
the first run makes a private `.venv` with **pywebview** (the only package) and fetches the VT323
font; without the font the app falls back to Lucida Console. `run.bat --debug` opens the WebView
devtools.

## Build the no-Python zip

- **On GitHub:** push a tag like `v1.0`, and the *Build Windows release* workflow attaches
  `PhosphorWatch-windows.zip` to a new Release. *Actions > Build Windows release > Run workflow*
  makes a test build without releasing.
- **Locally:** double-click **`build.bat`**.

Tests: `python -m pytest -q tests`

## How it's put together

- `phosphor/app.py`: the window (pywebview + WebView2), settings, the update flow, and the `Api`
  the page calls through `window.pywebview.api`.
- `phosphor/assets/web/`: the home screen, the shared chrome (bar, menu, dialogs, drag/resize)
  and the overlay that's injected into Twitch pages inside a shadow root.
- `phosphor/themes.py`: the palettes, shared with the sibling apps. `phosphor/updater.py` is the
  same self-updater they use.

## Credits

VT323 font by Peter Hull, SIL Open Font License (downloaded at build time).
Uses [pywebview](https://pywebview.flowrl.com/) (BSD-3-Clause).
