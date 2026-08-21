/* ---------------------------------------------------------------------------
 * sound.js  -  the audio layer (music + SFX), 100% offline.
 * All synthesised live with the Web Audio API - no mp3/wav files (booth is
 * offline). Dark loopable bed + crunchy UI blips. Boots on first gesture;
 * SOUND ON/OFF toggle pinned bottom-right (saved to localStorage).
 * API:  DMFX.sfx('click'|'type'|'success'|'error'|'login'|'flag')   - V.M.
 * ------------------------------------------------------------------------- */
(function () {
  "use strict";
  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  var ctx = null, master = null, musicGain = null;
  var muted = localStorage.getItem("dm_muted") === "1";
  var started = false, musicTimer = null;

  function ensureCtx() {
    if (ctx) return;
    ctx = new AC();
    master = ctx.createGain(); master.gain.value = muted ? 0.0 : 0.9; master.connect(ctx.destination);
    musicGain = ctx.createGain(); musicGain.gain.value = 0.14; musicGain.connect(master);
  }
  function blip(freq, dur, type, vol, slideTo) {
    if (!ctx) return;
    var o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type || "square";
    o.frequency.setValueAtTime(freq, ctx.currentTime);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, ctx.currentTime + dur);
    g.gain.setValueAtTime(0.0001, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(vol || 0.25, ctx.currentTime + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    o.connect(g); g.connect(master); o.start(); o.stop(ctx.currentTime + dur + 0.02);
  }
  function noiseBurst(dur, vol) {
    if (!ctx) return;
    var n = ctx.createBufferSource();
    var buf = ctx.createBuffer(1, ctx.sampleRate * dur, ctx.sampleRate);
    var d = buf.getChannelData(0);
    for (var i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
    n.buffer = buf;
    var g = ctx.createGain(); g.gain.value = vol || 0.15;
    var f = ctx.createBiquadFilter(); f.type = "highpass"; f.frequency.value = 1200;
    n.connect(f); f.connect(g); g.connect(master); n.start();
  }
  var SFX = {
    click:   function () { blip(660, 0.08, "square", 0.22, 880); },
    type:    function () { blip(1200 + Math.random() * 300, 0.03, "square", 0.06); },
    success: function () { blip(523, 0.09, "triangle", 0.28); setTimeout(function(){blip(784,0.12,"triangle",0.28);},90); },
    flag:    function () { blip(659, 0.08, "sawtooth", 0.3); setTimeout(function(){blip(988,0.1,"sawtooth",0.3);},80);
                           setTimeout(function(){blip(1319,0.16,"triangle",0.3);},170); },
    login:   function () { blip(440, 0.1, "sawtooth", 0.25, 660); setTimeout(function(){blip(880,0.14,"triangle",0.25);},110); },
    error:   function () { blip(180, 0.18, "sawtooth", 0.28, 90); noiseBurst(0.12, 0.1); },
  };
  var SCALE = [110.00, 130.81, 146.83, 164.81, 196.00, 220.00, 261.63], step = 0;
  function scheduleBeat() {
    if (!ctx) return;
    var t = ctx.currentTime;
    if (step % 4 === 0) {
      var b = ctx.createOscillator(), bg = ctx.createGain();
      b.type = "sine"; b.frequency.value = 55;
      bg.gain.setValueAtTime(0.0001, t); bg.gain.exponentialRampToValueAtTime(0.5, t + 0.02);
      bg.gain.exponentialRampToValueAtTime(0.0001, t + 0.45);
      b.connect(bg); bg.connect(musicGain); b.start(); b.stop(t + 0.5);
    }
    var f = SCALE[(step * 2) % SCALE.length] * (step % 8 < 4 ? 1 : 1.5);
    var o = ctx.createOscillator(), g = ctx.createGain(), lp = ctx.createBiquadFilter();
    o.type = "sawtooth"; o.frequency.value = f;
    lp.type = "lowpass"; lp.frequency.value = 700 + (step % 8) * 120;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.35, t + 0.03);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.32);
    o.connect(lp); lp.connect(g); g.connect(musicGain); o.start(); o.stop(t + 0.35);
    if (step % 2 === 1) {
      var n = ctx.createBufferSource();
      var buf = ctx.createBuffer(1, ctx.sampleRate * 0.05, ctx.sampleRate);
      var d = buf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1);
      n.buffer = buf;
      var hg = ctx.createGain(); hg.gain.value = 0.06;
      var hf = ctx.createBiquadFilter(); hf.type = "highpass"; hf.frequency.value = 7000;
      n.connect(hf); hf.connect(hg); hg.connect(musicGain); n.start();
    }
    step = (step + 1) % 32;
  }
  function startMusic() { if (!musicTimer) musicTimer = setInterval(scheduleBeat, 250); }
  function boot() { if (started) return; started = true; ensureCtx(); if (ctx.state === "suspended") ctx.resume(); startMusic(); updateToggle(); }
  var btn;
  function makeToggle() {
    btn = document.createElement("button");
    btn.id = "dm-sound-toggle"; btn.type = "button";
    btn.addEventListener("click", function (e) { e.stopPropagation(); boot(); setMuted(!muted); SFX.click(); });
    document.body.appendChild(btn); updateToggle();
  }
  function updateToggle() { if (btn) { btn.textContent = muted ? "♪ SOUND: OFF" : "♪ SOUND: ON"; btn.classList.toggle("off", muted); } }
  function setMuted(m) { muted = m; localStorage.setItem("dm_muted", m ? "1" : "0"); if (master) master.gain.value = m ? 0.0 : 0.9; updateToggle(); }
  window.DMFX = { sfx: function (n) { if (started && SFX[n]) SFX[n](); }, toggle: function () { setMuted(!muted); }, setMuted: setMuted };
  document.addEventListener("DOMContentLoaded", function () {
    makeToggle();
    var kick = function () { boot(); window.removeEventListener("pointerdown", kick); window.removeEventListener("keydown", kick); };
    window.addEventListener("pointerdown", kick); window.addEventListener("keydown", kick);
    document.addEventListener("click", function (e) {
      var el = e.target.closest(".btn, .pill, .stage, a");
      if (el && el.id !== "dm-sound-toggle") window.DMFX.sfx("click");
    });
    document.addEventListener("keydown", function (e) {
      var t = e.target;
      if (t && (t.id === "cmd" || t.id === "flag")) {
        if (e.key.length === 1 || e.key === "Backspace") window.DMFX.sfx("type");
      }
    });
  });
})();
