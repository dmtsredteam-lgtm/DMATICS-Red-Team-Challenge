/* ---------------------------------------------------------------------------
 * win.js  -  the "full compromise" victory screen.
 *
 * Fires when a player submits the 5th flag. Full-screen takeover: an ACCESS
 * GRANTED banner that "decrypts" in, a burst of green/red matrix confetti, a
 * little victory jingle, and then a button through to the debrief. The score is
 * already banked server-side (record_score) by the time this shows, so this is
 * pure celebration + a clean hand-off.
 *
 * Call:  showWinAlert(points, elapsedSeconds [, redirectUrl])
 *  -  V.M., DMATICS
 * ------------------------------------------------------------------------- */
(function () {
  "use strict";

  function fmtTime(s) {
    var m = Math.floor(s / 60), r = s % 60;
    return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r;
  }

  window.showWinAlert = function (points, secs, redirect) {
    if (document.getElementById("win-overlay")) return;

    var ov = document.createElement("div");
    ov.id = "win-overlay";
    ov.className = "win-overlay";
    ov.innerHTML =
      '<canvas id="win-confetti"></canvas>' +
      '<div class="win-box">' +
        '<div class="win-badge">☠</div>' +
        '<div class="win-tag">' + (window.__EVENT__ || "GISEC 2026") + ' · RED TEAM ARENA</div>' +
        '<div class="win-title glitch" data-text="ACCESS GRANTED">ACCESS GRANTED</div>' +
        '<div class="win-sub" id="win-typed"></div>' +
        '<div class="win-stats">' +
          '<div><span class="win-num">' + points + '</span><small>/ 100 pts</small></div>' +
          '<div><span class="win-num">5</span><small>/ 5 flags</small></div>' +
          '<div><span class="win-num">' + fmtTime(secs) + '</span><small>time</small></div>' +
        '</div>' +
        '<div class="win-msg">Target fully compromised. The crown jewel is yours — and you slipped past the SOC. Elite work, operator.</div>' +
        '<button class="btn" id="win-go">View Debrief ▸</button>' +
      '</div>';
    document.body.appendChild(ov);

    typeLine("root@" + (window.__TARGET__ || "aegis-web01") + ":~# whoami --> DOMAIN CROWN JEWEL EXFILTRATED");
    confetti();
    victoryJingle();

    var go = redirect || "/finish";
    document.getElementById("win-go").onclick = function () { window.location = go; };
    // Failsafe so a booth kiosk never stalls on the win screen.
    setTimeout(function () { if (document.getElementById("win-overlay")) window.location = go; }, 12000);
  };

  /* typewriter for the sub line */
  function typeLine(text) {
    var el = document.getElementById("win-typed");
    if (!el) return;
    var i = 0;
    (function tick() {
      if (!el) return;
      el.textContent = text.slice(0, i) + (i % 2 ? "_" : "");
      if (i++ <= text.length) setTimeout(tick, 22);
      else el.textContent = text;
    })();
  }

  /* a short rising victory arpeggio (reuses the audio engine if it's up) */
  function victoryJingle() {
    if (!window.DMFX) return;
    DMFX.sfx("flag");
    setTimeout(function () { DMFX.sfx("success"); }, 220);
    setTimeout(function () { DMFX.sfx("flag"); }, 460);
    setTimeout(function () { DMFX.sfx("success"); }, 720);
  }

  /* falling neon glyph "confetti" burst */
  function confetti() {
    var cv = document.getElementById("win-confetti");
    if (!cv) return;
    var ctx = cv.getContext("2d");
    function size() { cv.width = window.innerWidth; cv.height = window.innerHeight; }
    size(); window.addEventListener("resize", size);

    var glyphs = "01ABCDEF#$%DMATICS☠".split("");
    var cols = ["#ff1a33", "#ff5d6c", "#25d0ff", "#ffffff", "#ffb020"];
    var bits = [];
    for (var i = 0; i < 160; i++) {
      bits.push({
        x: Math.random() * cv.width,
        y: Math.random() * -cv.height,
        v: 2 + Math.random() * 5,
        s: 12 + Math.random() * 16,
        c: cols[(Math.random() * cols.length) | 0],
        g: glyphs[(Math.random() * glyphs.length) | 0],
        r: Math.random() * 6
      });
    }
    var frames = 0;
    (function draw() {
      ctx.clearRect(0, 0, cv.width, cv.height);
      for (var i = 0; i < bits.length; i++) {
        var b = bits[i];
        ctx.fillStyle = b.c;
        ctx.font = b.s + "px 'Share Tech Mono', monospace";
        ctx.fillText(b.g, b.x, b.y);
        b.y += b.v; b.x += Math.sin((b.y + b.r) / 40);
        if (b.y > cv.height + 20) { b.y = -20; b.x = Math.random() * cv.width; }
      }
      if (++frames < 600 && document.getElementById("win-overlay")) requestAnimationFrame(draw);
    })();
  }
})();
