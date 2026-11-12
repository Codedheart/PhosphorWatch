// PhosphorWatch shared window chrome: header bar, pixel icons, right-click menu,
// dialogs, drag + resize. Used by the home screen and by the overlay injected into
// Twitch pages. PW_PALETTES / PW_HAS_VT are prepended by Python (phosphor/web.py).

// ------------------------------------------------------------------ pixel icons
var PW_ICONS = {
  close: ["##....##", "###..###", ".######.", "..####..", "..####..", ".######.", "###..###", "##....##"],
  min:   ["........", "........", "........", "........", "........", "........", "########", "########"],
  pin:   ["..####..", "..####..", "..####..", ".######.", "########", "...##...", "...##...", "...##..."],
  home:  ["...##...", "..####..", ".######.", "########", ".#....#.", ".#.##.#.", ".#.##.#.", ".######."],
  menu:  ["########", "########", "........", "########", "########", "........", "########", "########"],
  up:    ["........", "...##...", "..####..", ".######.", "########", "........", "........", "........"],
  down:  ["........", "........", "........", "########", ".######.", "..####..", "...##...", "........"],
  plus:  ["...##...", "...##...", "...##...", "########", "########", "...##...", "...##...", "...##..."],
  play:  [".#......", ".##.....", ".###....", ".####...", ".####...", ".###....", ".##.....", ".#......"]
};

function pwIcon(name) {
  var rows = PW_ICONS[name], rects = "";
  rows.forEach(function (row, y) {
    var x = 0;
    while (x < row.length) {
      if (row[x] === "#") {
        var s = x;
        while (x < row.length && row[x] === "#") x++;
        rects += '<rect x="' + s + '" y="' + y + '" width="' + (x - s) + '" height="1"/>';
      } else x++;
    }
  });
  return '<svg class="pw-ico" viewBox="0 0 8 8" shape-rendering="crispEdges" fill="currentColor">' + rects + "</svg>";
}

function pwPalette(key) {
  for (var i = 0; i < PW_PALETTES.length; i++) if (PW_PALETTES[i].key === key) return PW_PALETTES[i];
  return PW_PALETTES[0];
}

function pwApplyPalette(el, key) {
  var c = pwPalette(key).colors;
  ["fg", "mid", "dim", "glow", "bg", "scan", "warn", "late"].forEach(function (k) {
    el.style.setProperty("--" + k, c[k]);
  });
}

// Resolves once pywebview has injected its bridge.
function pwApi() {
  return new Promise(function (resolve) {
    function ready() { return window.pywebview && window.pywebview.api && window.pywebview.api.get_state; }
    if (ready()) return resolve(window.pywebview.api);
    var t = setInterval(function () { if (ready()) { clearInterval(t); resolve(window.pywebview.api); } }, 50);
  });
}

// ---------------------------------------------------------- drag / resize
// mode: "move", "e", "s", "se". Pointer capture + screen coords; one call in flight.
function pwStartGesture(ev, mode) {
  if (ev.button !== 0) return;
  ev.preventDefault();
  var target = ev.currentTarget;
  try { target.setPointerCapture(ev.pointerId); } catch (e) {}
  var sx = ev.screenX, sy = ev.screenY, start = null, api = null;
  var pending = null, busy = false, lastE = null;

  pwApi().then(function (a) {
    api = a;
    a.get_geometry().then(function (g) { start = g; if (lastE) move(lastE); });
  });
  function flush() {
    if (busy || !pending || !api) return;
    var g = pending; pending = null; busy = true;
    api.set_geometry(g.x, g.y, g.width, g.height).then(function () { busy = false; flush(); },
                                                       function () { busy = false; });
  }
  function move(e) {
    lastE = e;
    if (!start) return;
    var dx = e.screenX - sx, dy = e.screenY - sy;
    var g = { x: start.x, y: start.y, width: start.width, height: start.height };
    if (mode === "move") { g.x += dx; g.y += dy; }
    if (mode === "e" || mode === "se") g.width += dx;
    if (mode === "s" || mode === "se") g.height += dy;
    pending = g; flush();
  }
  function up(e) {
    target.removeEventListener("pointermove", move);
    target.removeEventListener("pointerup", up);
    target.removeEventListener("pointercancel", up);
    try { target.releasePointerCapture(e.pointerId); } catch (err) {}
    if (api) api.save_geometry();
  }
  target.addEventListener("pointermove", move);
  target.addEventListener("pointerup", up);
  target.addEventListener("pointercancel", up);
}

// ------------------------------------------------------------------- mount
// opts.box     element that gets the pw-root class (palette vars live here)
// opts.overlay true inside Twitch pages (adds HOME button, channel name)
// opts.onState optional callback(state) after every state change
function pwMount(opts) {
  var box = opts.box, api = null, state = null;
  var flashText = "", flashUntil = 0, blink = true;
  var menuEl = null, dialogEl = null;

  box.classList.add("pw-root");
  if (PW_HAS_VT) box.classList.add("vt");

  // frame + header
  box.insertAdjacentHTML("beforeend",
    '<div class="pw-frame"></div>' +
    '<div class="pw-bar pw-scanned">' +
    '  <div class="pw-drag"><span class="pw-status"></span></div>' +
    (opts.overlay ? '  <button class="pw-btn" data-a="home" title="Channels">' + pwIcon("home") + "</button>" : "") +
    '  <button class="pw-btn" data-a="menu" title="Menu (or right-click)">' + pwIcon("menu") + "</button>" +
    '  <button class="pw-btn" data-a="pin" title="Always on top">' + pwIcon("pin") + "</button>" +
    '  <button class="pw-btn" data-a="min" title="Minimize">' + pwIcon("min") + "</button>" +
    '  <button class="pw-btn x" data-a="close" title="Close">' + pwIcon("close") + "</button>" +
    "</div>");
  ["e", "s", "se"].forEach(function (m) {
    var g = document.createElement("div");
    g.className = "pw-grip " + m;
    g.addEventListener("pointerdown", function (ev) { pwStartGesture(ev, m); });
    box.appendChild(g);
  });

  var bar = box.querySelector(".pw-bar");
  var status = box.querySelector(".pw-status");
  var drag = box.querySelector(".pw-drag");
  drag.addEventListener("pointerdown", function (e) {
    if (e.target.closest && e.target.closest(".pw-link")) return;
    pwStartGesture(e, "move");
  });

  function btn(a) { return box.querySelector('[data-a="' + a + '"]'); }

  function renderStatus() {
    if (!state) return;
    var now = Date.now();
    status.className = "pw-status";
    status.onclick = null;
    if (now < flashUntil) {
      status.textContent = flashText; status.classList.add("warn");
    } else if (state.update_busy) {
      status.textContent = state.update_busy; status.classList.add("warn");
    } else if (state.update_tag) {
      status.textContent = "UPDATE " + state.update_tag + " >";
      status.classList.add("warn", "pw-link");
      status.onclick = function () { api.offer_update(); };
    } else {
      status.textContent = "";
      var t = document.createElement("span");
      t.className = "title";
      t.textContent = "PHOSPHOR-WATCH" + (opts.overlay && state.current ? "" : " " + (blink ? "█" : " "));
      status.appendChild(t);
      if (opts.overlay && state.current) {
        var c = document.createElement("span");
        c.className = "chan";
        c.textContent = " > " + state.current.toUpperCase();
        status.appendChild(c);
      }
    }
  }
  setInterval(function () { blink = !blink; renderStatus(); }, 530);

  function setState(s) {
    state = s;
    pwApplyPalette(box, s.theme);
    btn("pin").classList.toggle("on", !!s.on_top);
    renderStatus();
    if (opts.onState) opts.onState(s);
  }

  function flash(text, secs) {
    flashText = text; flashUntil = Date.now() + (secs || 4) * 1000; renderStatus();
  }

  // --------------------------------------------------------------- dialog
  function closeDialog() { if (dialogEl) { dialogEl.remove(); dialogEl = null; } }
  function showDialog(d) {
    closeDialog(); closeMenu();
    dialogEl = document.createElement("div");
    dialogEl.className = "pw-dialog-bg";
    var boxEl = document.createElement("div"); boxEl.className = "pw-dialog";
    var t = document.createElement("div"); t.className = "pw-dialog-title"; t.textContent = d.title;
    var b = document.createElement("div"); b.className = "pw-dialog-body"; b.textContent = d.body;
    var row = document.createElement("div"); row.className = "pw-dialog-btns";
    d.buttons.forEach(function (pair) {
      var el = document.createElement("button");
      el.className = "pw-tbtn"; el.textContent = pair[0];
      el.onclick = function () { closeDialog(); if (pair[1]) api.dialog_action(pair[1]); };
      row.appendChild(el);
    });
    boxEl.appendChild(t); boxEl.appendChild(b); boxEl.appendChild(row);
    dialogEl.appendChild(boxEl);
    box.appendChild(dialogEl);
  }

  // ----------------------------------------------------------------- menu
  function closeMenu() { if (menuEl) { menuEl.remove(); menuEl = null; } }
  function openMenu(x, y, page) {
    if (!state || !api) return;
    closeMenu();
    menuEl = document.createElement("div");
    menuEl.className = "pw-menu pw-scanned";
    var items = [];
    function item(label, fn, checked, disabled) { items.push({ label: label, fn: fn, checked: checked, disabled: disabled }); }
    function sep() { items.push(null); }
    function head(label) { items.push({ head: label }); }
    function stay(fn) { return function () { fn(); openMenu(x, y, page); }; }

    if (page === "theme") {
      item("< BACK", function () { openMenu(x, y); });
      var group = "";
      PW_PALETTES.forEach(function (p) {
        if (p.group !== group) { group = p.group; head(group); }
        item(p.name, stay(function () { state.theme = p.key; setState(state); api.set_theme(p.key); }),
             state.theme === p.key);
      });
    } else if (page === "opacity") {
      item("< BACK", function () { openMenu(x, y); });
      [1, 0.9, 0.8, 0.7, 0.6, 0.5].forEach(function (o) {
        item(Math.round(o * 100) + "%", stay(function () { state.opacity = o; api.set_opacity(o); }),
             Math.abs(state.opacity - o) < 0.01);
      });
    } else {
      if (opts.overlay) item("Channels", function () { api.go_home(); });
      item("Palette >", function () { openMenu(x, y, "theme"); });
      item("Opacity >", function () { openMenu(x, y, "opacity"); });
      item("Always on top", function () { api.toggle_pin(); }, !!state.on_top);
      sep();
      if (state.user) {
        item("Signed in as " + state.user, null, false, true);
        item("Sign out of Twitch", function () { api.logout(); });
      } else {
        item("Sign in to Twitch...", function () { api.login(); });
      }
      sep();
      if (state.update_tag) item("Install update " + state.update_tag + "...", function () { api.offer_update(); });
      item("Check for updates", function () { api.check_updates(true); });
      item("Check for updates automatically", function () { api.toggle_auto_update(); }, !!state.auto_update);
      item("Open settings folder", function () { api.open_data_folder(); });
      item("PhosphorWatch " + state.version_label, null, false, true);
      sep();
      item("Exit", function () { api.close(); });
    }

    items.forEach(function (it) {
      var el = document.createElement("div");
      if (it === null) { el.className = "pw-mi-sep"; }
      else if (it.head) { el.className = "pw-mi-head"; el.textContent = it.head; }
      else {
        el.className = "pw-mi" + (it.disabled ? " disabled" : "");
        var mark = document.createElement("span"); mark.className = "mark";
        mark.textContent = it.checked ? "■" : "";
        var lab = document.createElement("span"); lab.textContent = it.label;
        el.appendChild(mark); el.appendChild(lab);
        if (!it.disabled && it.fn) el.onclick = function (e) { e.stopPropagation(); closeMenu(); it.fn(); };
      }
      menuEl.appendChild(el);
    });
    box.appendChild(menuEl);

    // keep inside the window
    var bw = box.clientWidth, bh = box.clientHeight;
    var mw = menuEl.offsetWidth, mh = menuEl.offsetHeight;
    menuEl.style.left = Math.max(4, Math.min(x, bw - mw - 4)) + "px";
    menuEl.style.top = Math.max(4, Math.min(y, bh - mh - 4)) + "px";
  }

  document.addEventListener("pointerdown", function (e) {
    if (!menuEl) return;
    var path = e.composedPath ? e.composedPath() : [];
    if (path.indexOf(menuEl) < 0 && path.indexOf(btn("menu")) < 0) closeMenu();
  }, true);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeMenu(); closeDialog(); }
  }, true);

  (opts.menuTarget || box).addEventListener("contextmenu", function (e) {
    e.preventDefault(); e.stopPropagation();
    var r = box.getBoundingClientRect();
    openMenu(e.clientX - r.left, e.clientY - r.top);
  });

  pwApi().then(function (a) {
    api = a;
    btn("menu").onclick = function () {
      if (menuEl) return closeMenu();
      var r = btn("menu").getBoundingClientRect(), b = box.getBoundingClientRect();
      openMenu(r.left - b.left, r.bottom - b.top + 2);
    };
    btn("pin").onclick = function () { api.toggle_pin(); };
    btn("min").onclick = function () { api.minimize(); };
    btn("close").onclick = function () { api.close(); };
    if (btn("home")) btn("home").onclick = function () { api.go_home(); };

    // Python pushes {state}, {flash, secs} and {dialog} here.
    window.__pwPush = function (msg) {
      if (msg.state) setState(msg.state);
      if (msg.flash) flash(msg.flash, msg.secs);
      if (msg.dialog) showDialog(msg.dialog);
    };
    api.get_state().then(function (s) {
      setState(s);
      if (s.flash) flash(s.flash, s.flash_secs);
      api.page_ready();
    });
  });

  return {
    api: function () { return api; },
    state: function () { return state; },
    setState: setState,
    flash: flash,
    bar: bar
  };
}
