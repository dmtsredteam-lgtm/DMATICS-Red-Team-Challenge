/* soc.js - the "you got caught" SOC alert pop-up. Full-screen red incident
 * banner + siren, then a button to the debrief. Score is banked server-side
 * before this shows.  Call: showSOCAlert(title, message [, redirectUrl]) */
(function () {
  "use strict";
  window.showSOCAlert = function (title, message, redirect) {
    if (document.getElementById("soc-overlay")) return;
    var ov = document.createElement("div");
    ov.id = "soc-overlay"; ov.className = "soc-overlay";
    ov.innerHTML =
      '<div class="soc-box">' +
        '<div class="soc-siren">⚠</div>' +
        '<div class="soc-tag">INCIDENT DETECTED · ' + (window.__EVENT__ || "GISEC 2026") + '</div>' +
        '<div class="soc-title">' + title + '</div>' +
        '<div class="soc-msg">' + message + '</div>' +
        '<div class="soc-meta">Session terminated · source flagged · your score has been recorded.</div>' +
        '<button class="btn red" id="soc-ack">Acknowledge → Debrief</button>' +
      '</div>';
    document.body.appendChild(ov);
    if (window.DMFX) { DMFX.sfx("error"); setTimeout(function(){DMFX.sfx("error");},350); setTimeout(function(){DMFX.sfx("error");},700); }
    var go = redirect || "/finish";
    document.getElementById("soc-ack").onclick = function () { window.location = go; };
    setTimeout(function () { if (document.getElementById("soc-overlay")) window.location = go; }, 8000);
  };
})();
