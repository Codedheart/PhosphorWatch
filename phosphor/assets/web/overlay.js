// Injected into Twitch pages (player + sign-in). THEME_CSS / FONT_CSS and chrome.js
// are prepended by Python (phosphor/web.py). Everything lives in a shadow root so
// Twitch's styles and ours can't collide.

function pwLoginCookie() {
  try {
    var m = document.cookie.match(/(?:^|;\s*)login=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  } catch (e) { return ""; }
}

function pwBuildOverlay() {
  if (!document.body) return setTimeout(pwBuildOverlay, 50);

  // @font-face must live in the document, not the shadow root
  if (FONT_CSS) {
    var fs = document.createElement("style");
    fs.textContent = FONT_CSS;
    document.head.appendChild(fs);
  }

  var host = document.createElement("div");
  host.id = "phosphorwatch-overlay";
  host.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483647;";
  document.documentElement.appendChild(host);
  var root = host.attachShadow({ mode: "open" });

  var style = document.createElement("style");
  style.textContent = THEME_CSS + [
    ".wrap{position:fixed;inset:0;pointer-events:none;}",
    ".pw-bar{position:absolute;top:0;left:0;right:0;pointer-events:auto;z-index:50;",
    "  transform:translateY(-100%);transition:transform .15s ease;}",
    ".show .pw-bar,.pinned .pw-bar{transform:none;}",
    ".pw-frame{opacity:0;transition:opacity .15s;}",
    ".show .pw-frame,.pinned .pw-frame{opacity:1;}",
    ".pw-grip{pointer-events:auto;}",
    ".pw-grip.se{opacity:0;transition:opacity .15s;}",
    ".show .pw-grip.se,.pinned .pw-grip.se{opacity:1;}"
  ].join("\n");
  root.appendChild(style);

  var wrap = document.createElement("div");
  wrap.className = "wrap";
  root.appendChild(wrap);

  var lastUser = null;
  var ui = pwMount({
    box: wrap, overlay: true,
    onState: function (s) {
      // Not watching (sign-in page etc.): keep the bar up so there's always a way back.
      wrap.classList.toggle("pinned", !s.current);
      if (lastUser === null) {
        lastUser = s.user;
        checkUser();
        setInterval(checkUser, 2000);
      }
    }
  });

  // Track who is signed in (Twitch sets a readable `login` cookie).
  function checkUser() {
    var u = pwLoginCookie(), api = ui.api(), s = ui.state();
    // An unreadable/missing cookie never signs us "out"; SIGN OUT in the menu does that.
    if (!api || !s || !u || u === lastUser) return;
    var justSignedIn = !lastUser && u;
    lastUser = u;
    api.set_user(u);
    if (justSignedIn && !s.current) setTimeout(function () { api.go_home(); }, 800);
  }

  // Show the bar on mouse activity; hide after a moment unless the mouse is on it.
  var hideT = null, overUi = false;
  function poke() {
    wrap.classList.add("show");
    clearTimeout(hideT);
    hideT = setTimeout(function () {
      if (!overUi && !root.querySelector(".pw-menu, .pw-dialog-bg")) wrap.classList.remove("show");
    }, 1800);
  }
  window.addEventListener("mousemove", poke, true);
  ui.bar.addEventListener("mouseenter", function () { overUi = true; poke(); });
  ui.bar.addEventListener("mouseleave", function () { overUi = false; poke(); });
  document.addEventListener("mouseleave", function () {
    if (!overUi && !root.querySelector(".pw-menu, .pw-dialog-bg")) { clearTimeout(hideT); wrap.classList.remove("show"); }
  });
}

pwBuildOverlay();
