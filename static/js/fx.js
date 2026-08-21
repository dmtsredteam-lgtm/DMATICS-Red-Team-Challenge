/* fx.js - stagger reveals, "decrypt" typewriter on the hero, glitch-on-hover.
 * Hand-rolled (booth offline, no GSAP CDN).  - V.M. */
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".reveal").forEach(function (el, i) {
      if (reduce) { el.style.opacity = 1; return; }
      el.style.opacity = 0; el.style.transform = "translateY(14px)";
      el.style.transition = "opacity .5s ease, transform .5s cubic-bezier(.2,.7,.2,1)";
      setTimeout(function () { el.style.opacity = 1; el.style.transform = "translateY(0)"; }, 90 * i + 60);
    });
    var pool = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%<>/*".split("");
    document.querySelectorAll("[data-decrypt]").forEach(function (el) {
      var full = el.textContent; if (reduce) return;
      var frame = 0, total = full.length;
      var timer = setInterval(function () {
        var shown = Math.floor(frame / 2), out = "";
        for (var i = 0; i < total; i++) {
          if (i < shown) out += full[i];
          else if (full[i] === " ") out += " ";
          else out += pool[Math.floor(Math.random() * pool.length)];
        }
        el.textContent = out; frame++;
        if (shown >= total) { el.textContent = full; clearInterval(timer); }
      }, 40);
    });
    document.querySelectorAll(".glitch").forEach(function (el) {
      if(!el.getAttribute("data-text")) el.setAttribute("data-text", el.textContent);
    });
  });
})();
