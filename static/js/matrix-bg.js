/* ---------------------------------------------------------------------------
 * matrix-bg.js  -  the animated "video" background for the arena.
 * Full-screen <canvas> red digital-rain (Matrix style) with a glitch sweep and
 * flicker. Canvas not .mp4 on purpose: booth is offline, this scales crisp to
 * the 55" screen and runs on a cheap mini-PC. Honours prefers-reduced-motion.
 *  -  V.M., DMATICS
 * ------------------------------------------------------------------------- */
(function () {
  "use strict";
  var canvas = document.getElementById("dm-matrix");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var GLYPHS = "アカサタナハマヤラワ0123456789ABCDEF#$%<>/\\|=+*".split("");
  var FONT_SIZE = 16, columns, drops;
  function sizeCanvas() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    columns = Math.floor(window.innerWidth / FONT_SIZE);
    drops = new Array(columns);
    for (var i = 0; i < columns; i++) drops[i] = Math.random() * -100;
  }
  var glitch = { active: false, y: 0, life: 0 };
  function maybeGlitch() {
    if (!glitch.active && Math.random() < 0.008) {
      glitch.active = true; glitch.y = Math.random() * window.innerHeight;
      glitch.life = 6 + Math.floor(Math.random() * 8);
    }
  }
  function draw() {
    ctx.fillStyle = "rgba(6, 0, 0, 0.08)";
    ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);
    ctx.font = FONT_SIZE + "px 'Share Tech Mono', monospace";
    for (var i = 0; i < columns; i++) {
      var ch = GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
      var x = i * FONT_SIZE, y = drops[i] * FONT_SIZE;
      if (Math.random() > 0.975) { ctx.fillStyle = "#ffd0d6"; ctx.shadowColor = "#ff2440"; ctx.shadowBlur = 8; }
      else { ctx.fillStyle = "#ff1a33"; ctx.shadowBlur = 0; }
      ctx.fillText(ch, x, y); ctx.shadowBlur = 0;
      if (y > window.innerHeight && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
    maybeGlitch();
    if (glitch.active) {
      var h = 3 + Math.random() * 5;
      ctx.fillStyle = "rgba(255, 30, 60, 0.20)"; ctx.fillRect(0, glitch.y, window.innerWidth, h);
      ctx.fillStyle = "rgba(0, 200, 255, 0.10)"; ctx.fillRect(0, glitch.y + h, window.innerWidth, h * 0.6);
      glitch.y += 2; if (--glitch.life <= 0) glitch.active = false;
    }
  }
  var last = 0;
  function loop(ts) { if (ts - last > 42) { draw(); last = ts; } requestAnimationFrame(loop); }
  sizeCanvas();
  window.addEventListener("resize", sizeCanvas);
  if (reduce) { ctx.fillStyle = "#060000"; ctx.fillRect(0, 0, window.innerWidth, window.innerHeight); draw(); }
  else { requestAnimationFrame(loop); }
})();
