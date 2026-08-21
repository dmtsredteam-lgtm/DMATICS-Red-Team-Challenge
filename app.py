#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# DMATICS Red Team Challenge  ·  GISEC 2026 Booth Edition
# --------------------------------------------------------
# A little 10-minute "breach the target" game we run at the booth. Five stages,
# 100 points, a big-screen leaderboard, and a fake shell that only knows a handful
# of commands so nobody can actually break out onto the host. Everything here is
# simulated on purpose - it's meant to be safe to leave running on a public
# show-floor network all day.
#
# The target org is a made-up company, "Aegis Vault Systems". DMATICS is the
# red team running the op (that's the branding you see in the nav / leaderboard).
#
# Built by the DMATICS Offensive Security team, Dubai.  info@dmaticsonline.com
#
# Changelog:
#   v1.6  - polish pass:
#             * grabbing all 5 flags now auto-ends the run with a victory screen
#               (score recorded automatically) - no more manual "record" button
#             * clearer /submit result: newly vs already-captured vs time-expired
#               (fixes the "FLAG-5 already captured" false message)
#             * dropped the extra submit box in the SSH console - submit only on
#               Mission Control now
#             * removed the dead Staff-Login card from the recon portal
#   v1.5  - proper CTF flow: stages unlock in order (FLAG-1 -> ... -> FLAG-5)
#   v1.4  - SOC bites back: brute-force lock-outs + priv-esc trap, manual capture
#   v1.3  - audio, DMATICS logos, renamed target to "Aegis Vault Systems"
#   v1.2  - hacker theme + digital-rain background
#   v1.1  - fixed the flag-submit parser, added /health
#   v1.0  - first cut for GISEC

import os
import re
import time
import sqlite3
import secrets
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, send_from_directory, flash
)

# --------------------------------------------------------------------------- #
#  Config - the handful of things you'd actually want to tweak per event
# --------------------------------------------------------------------------- #
APP_TITLE   = "DMATICS Red Team Challenge"
EVENT_NAME  = "GISEC 2026"
TARGET_ORG  = "Aegis Vault Systems"
TARGET_HOST = "aegis-web01"
TARGET_FS   = r"\\aegis-fs01\Shared"
DB_PATH     = os.environ.get("DB_PATH", "/app/data/leaderboard.db")
FILES_DIR   = os.path.join(os.path.dirname(__file__), "challenge_files")

# How many bad passwords before the SOC "catches" the player and ends the run.
LOGIN_MAX = 4     # staff portal login
SSH_MAX   = 3     # SSH web console

# The five flags. Update challenge_files/passwords.txt if you change FLAG-3/SVC_PASS.
FLAGS = {
    "FLAG-1": "DMATICS{r3c0n_c0mpl3t3}",       # Stage 1 - recon / view-source
    "FLAG-2": "DMATICS{w3ak_p@ssw0rd_pwn3d}",  # Stage 2 - weak password
    "FLAG-3": "DMATICS{cr3ds_1n_th3_sh@re}",   # Stage 3 - creds on the share
    "FLAG-4": "DMATICS{sh3ll_@cc3ss_g@in3d}",  # Stage 4 - foothold shell
    "FLAG-5": "DMATICS{cr0wn_jewel_5ecur3d}",  # Stage 5 - exfil the vault
}
POINTS = {"FLAG-1": 10, "FLAG-2": 20, "FLAG-3": 20, "FLAG-4": 25, "FLAG-5": 25}  # = 100

# --- the CTF chain: which flag you must have SUBMITTED to enter each stage ----
STAGE_REQUIRES = {1: None, 2: "FLAG-1", 3: "FLAG-2", 4: "FLAG-3", 5: "FLAG-4"}

# Weak "onboarding" creds the player has to figure out (Stage 2)
VALID_USER = "john.smith"
VALID_PASS = "Summer2026"

# Service account hidden on the share, used to reach the box (Stage 3 -> 4)
SVC_USER = "svc_backup"
SVC_PASS = "Backup@2026!"

GAME_SECONDS = int(os.environ.get("GAME_SECONDS", 600))  # 10 minutes

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

@app.context_processor
def inject_globals():
    return dict(target_org=TARGET_ORG, target_host=TARGET_HOST,
                target_fs=TARGET_FS, event=EVENT_NAME,
                login_max=LOGIN_MAX, ssh_max=SSH_MAX)


# --------------------------------------------------------------------------- #
#  Leaderboard storage (tiny SQLite db, one row per finished OR busted run)
# --------------------------------------------------------------------------- #
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            player     TEXT    NOT NULL,
            points     INTEGER NOT NULL DEFAULT 0,
            flags      INTEGER NOT NULL DEFAULT 0,
            seconds    INTEGER NOT NULL DEFAULT 0,
            finished   INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL
        )
    """)
    con.commit()
    con.close()


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def save_score(player, points, flags, seconds, finished):
    con = db()
    con.execute(
        "INSERT INTO scores (player, points, flags, seconds, finished, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (player, points, flags, seconds, int(finished), datetime.utcnow().isoformat()),
    )
    con.commit()
    con.close()


# --------------------------------------------------------------------------- #
#  Per-player progress (all in the signed session cookie)
# --------------------------------------------------------------------------- #
def fresh_progress():
    return {
        "player": None,
        "started_at": None,
        "captured": [],                # flag ids the player has SUBMITTED
        "points": 0,
        "logged_in": False,            # portal login done? (Stage 2 mechanic)
        "shell": False,                # web shell unlocked? (Stage 4 mechanic)
        "login_attempts": LOGIN_MAX,
        "ssh_attempts": SSH_MAX,
        "busted": False,
        "bust_reason": None,
        "saved": False,
    }


def progress():
    if "p" not in session:
        session["p"] = fresh_progress()
    return session["p"]


def has(flag_id):
    return flag_id in progress()["captured"]


def stage_unlocked(stage):
    req = STAGE_REQUIRES.get(stage)
    return req is None or req in progress()["captured"]


def record_score(finished):
    p = progress()
    if p.get("saved"):
        return
    save_score(p["player"], p["points"], len(p["captured"]), elapsed(), finished)
    p["saved"] = True
    session.modified = True


def bust(reason):
    p = progress()
    if not p.get("busted"):
        p["busted"] = True
        p["bust_reason"] = reason
        record_score(finished=False)
        session.modified = True


def capture(flag_id):
    """Add a flag to the captured set + points. Caller checks the guards first."""
    p = progress()
    p["captured"].append(flag_id)
    p["points"] += POINTS[flag_id]
    session.modified = True


ALLOW_WHEN_BUSTED = {"index", "finish", "leaderboard", "leaderboard_data",
                     "status", "health", "static"}


def require_player(f):
    @wraps(f)
    def wrapper(*a, **kw):
        p = progress()
        if not p.get("player"):
            return redirect(url_for("index"))
        if p.get("busted") and request.endpoint not in ALLOW_WHEN_BUSTED:
            return redirect(url_for("finish"))
        return f(*a, **kw)
    return wrapper


def require_stage(stage):
    def deco(f):
        @wraps(f)
        @require_player
        def wrapper(*a, **kw):
            if not stage_unlocked(stage):
                req = STAGE_REQUIRES.get(stage)
                flash(f"🔒 Locked — submit {req} on Mission Control to unlock "
                      f"Stage {stage}.")
                return redirect(url_for("brief"))
            return f(*a, **kw)
        return wrapper
    return deco


def elapsed():
    p = progress()
    if not p.get("started_at"):
        return 0
    return int(time.time() - p["started_at"])


def time_left():
    return max(0, GAME_SECONDS - elapsed())


# --------------------------------------------------------------------------- #
#  The stage map that drives Mission Control's hub of direct links
# --------------------------------------------------------------------------- #
def stage_list():
    caps = progress()["captured"]

    def st(n, name, endpoint, awards, desc):
        req = STAGE_REQUIRES.get(n)
        return dict(n=n, name=name, url=url_for(endpoint), awards=awards,
                    requires=req, desc=desc,
                    done=(awards in caps),
                    unlocked=(req is None or req in caps))

    return [
        st(1, "Reconnaissance", "portal", "FLAG-1",
           "Enumerate the public portal & staff directory. View source to find FLAG-1."),
        st(2, "Credential Access", "login", "FLAG-2",
           "Brute the weak password for the account you found. Login reveals FLAG-2."),
        st(3, "Lateral Movement", "dashboard", "FLAG-3",
           "Loot the internal share for leaked service-account creds & FLAG-3."),
        st(4, "Foothold", "console", "FLAG-4",
           "Pop a shell on " + TARGET_HOST + " and cat the shell flag (FLAG-4)."),
        st(5, "Exfiltration — Crown Jewel", "console", "FLAG-5",
           "Hunt the hidden vault file in the shell and exfil the final flag."),
    ]


# --------------------------------------------------------------------------- #
#  Registration / home / Mission Control
# --------------------------------------------------------------------------- #
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = (request.form.get("player") or "").strip()[:24]
        if name:
            session["p"] = fresh_progress()
            session["p"]["player"] = name
            session["p"]["started_at"] = time.time()
            session.modified = True
            return redirect(url_for("brief"))
        flash("Enter your handle to begin.")
    return render_template("index.html", title=APP_TITLE)


@app.route("/brief")
@require_player
def brief():
    return render_template("brief.html", title=APP_TITLE,
                           p=progress(), elapsed=elapsed(), left=time_left(),
                           stages=stage_list())


# --------------------------------------------------------------------------- #
#  Stage 1 - Reconnaissance
# --------------------------------------------------------------------------- #
@app.route("/portal")
@require_stage(1)
def portal():
    return render_template("portal.html", title=APP_TITLE, p=progress())


@app.route("/portal/directory")
@require_stage(1)
def directory():
    return render_template("directory.html", title=APP_TITLE, p=progress(),
                           flag1=FLAGS["FLAG-1"], valid_user=VALID_USER)


# --------------------------------------------------------------------------- #
#  Stage 2 - Credential Access  (needs FLAG-1)  -  locks out after LOGIN_MAX
# --------------------------------------------------------------------------- #
@app.route("/portal/login", methods=["GET", "POST"])
@require_stage(2)
def login():
    p = progress()
    error = None
    soc = None
    if request.method == "POST" and not p.get("logged_in"):
        u = (request.form.get("username") or "").strip()
        pw = (request.form.get("password") or "").strip()
        if u == VALID_USER and pw == VALID_PASS:
            p["logged_in"] = True
            session.modified = True
        else:
            p["login_attempts"] = max(0, p.get("login_attempts", LOGIN_MAX) - 1)
            session.modified = True
            if p["login_attempts"] <= 0:
                bust("Brute-force authentication attack detected against the "
                     f"{TARGET_ORG} staff portal.")
                soc = {"title": "SOC ALERT — BRUTE FORCE DETECTED",
                       "msg": ("Multiple failed logins on the staff portal tripped "
                               "the detection rule. Account locked, source flagged, "
                               "session killed.")}
            else:
                error = (f"Invalid credentials. Access denied. "
                         f"{p['login_attempts']} attempt(s) remaining before lockout.")
    return render_template("login.html", title=APP_TITLE, p=p,
                           error=error, hint_user=VALID_USER,
                           attempts_left=p.get("login_attempts", LOGIN_MAX),
                           soc=soc,
                           flag2=(FLAGS["FLAG-2"] if p.get("logged_in") else None))


# --------------------------------------------------------------------------- #
#  Stage 3 - Lateral Movement  (needs FLAG-2)
# --------------------------------------------------------------------------- #
@app.route("/dashboard")
@require_stage(3)
def dashboard():
    return render_template("dashboard.html", title=APP_TITLE, p=progress())


@app.route("/dashboard/share")
@require_stage(3)
def share():
    return render_template("share.html", title=APP_TITLE, p=progress())


@app.route("/files/<path:fname>")
@require_stage(3)
def files(fname):
    return send_from_directory(FILES_DIR, fname, as_attachment=False)


# --------------------------------------------------------------------------- #
#  Stage 4 / 5 - Foothold + Exfil  (console needs FLAG-3; vault needs FLAG-4)
# --------------------------------------------------------------------------- #
@app.route("/console", methods=["GET"])
@require_stage(4)
def console():
    p = progress()
    return render_template("console.html", title=APP_TITLE, p=p,
                           svc_user=SVC_USER,
                           attempts_left=p.get("ssh_attempts", SSH_MAX),
                           authed=p.get("shell", False))


@app.route("/console/auth", methods=["POST"])
@require_player
def console_auth():
    p = progress()
    if not stage_unlocked(4):
        return jsonify(ok=False, msg="ssh: stage locked. Submit FLAG-3 first.")
    u = (request.form.get("username") or "").strip()
    pw = (request.form.get("password") or "").strip()
    if u == SVC_USER and pw == SVC_PASS:
        p["shell"] = True
        session.modified = True
        return jsonify(ok=True, msg=f"Authenticated as {SVC_USER}@{TARGET_HOST}")
    p["ssh_attempts"] = max(0, p.get("ssh_attempts", SSH_MAX) - 1)
    session.modified = True
    if p["ssh_attempts"] <= 0:
        bust(f"SSH brute-force login detected against {TARGET_HOST}.")
        return jsonify(ok=False, busted=True,
                       title="SOC ALERT — SSH BRUTE FORCE",
                       reason=("Repeated failed SSH logins on " + TARGET_HOST +
                               " tripped the detection rule. Session terminated."),
                       msg="ssh: too many authentication failures")
    return jsonify(ok=False, attempts=p["ssh_attempts"],
                   msg=(f"ssh: access denied "
                        f"({p['ssh_attempts']} attempt(s) left before lockout)"))


# --- privilege-escalation detector for the fake shell -------------------------
PRIVESC_TOKENS = ("-exec", "sudo su", "sudo -i", "sudo -s", "sudo bash",
                  "sudo sh", "sudo /bin/sh", "sudo /bin/bash", "sudo vi",
                  "sudo vim", "sudo nano", "sudo less", "sudo more", "sudo awk",
                  "sudo perl", "sudo python", "sudo env", "sudo nmap")

def is_privesc(key):
    if not key.startswith("sudo"):
        return False
    if key == "sudo -l":
        return False
    return any(tok in key for tok in PRIVESC_TOKENS)


FAKE_FS = {
    "whoami":   lambda: SVC_USER,
    "id":       lambda: f"uid=1001({SVC_USER}) gid=1001({SVC_USER}) groups=1001({SVC_USER}),27(sudo)",
    "hostname": lambda: TARGET_HOST,
    "pwd":      lambda: f"/home/{SVC_USER}",
    "ls":       lambda: "notes.txt   backup.sh   .secret_vault",
    "cat flag.txt":  lambda: FLAGS["FLAG-4"],
    "cat notes.txt": lambda: "TODO: rotate svc_backup password. Vault path hidden in /home. Look for *secret*.",
    "ls -la": lambda: (
        "drwxr-xr-x 3 svc_backup svc_backup 4096 .\n"
        "drwxr-xr-x 4 root       root       4096 ..\n"
        "-rw-r--r-- 1 svc_backup svc_backup   45 flag.txt\n"
        "-rw-r--r-- 1 svc_backup svc_backup  128 notes.txt\n"
        "-rwxr-xr-x 1 svc_backup svc_backup  320 backup.sh\n"
        "drwx------ 2 svc_backup svc_backup 4096 .secret_vault"
    ),
    "sudo -l": lambda: ("User svc_backup may run the following commands on " + TARGET_HOST + ":\n"
                        "    (ALL) NOPASSWD: /usr/bin/find"),
    "help": lambda: "try: whoami, id, ls, ls -la, cat flag.txt, cat notes.txt, sudo -l, find / -name '*secret*'",
}

VAULT_LOCKED = "[locked] Objective not yet active — submit FLAG-4 on Mission Control to unlock the vault."


@app.route("/console/exec", methods=["POST"])
@require_player
def console_exec():
    p = progress()
    if not p.get("shell"):
        return jsonify(ok=False, out=f"ssh: not authenticated. Login to {TARGET_HOST} first.")

    payload = request.get_json(silent=True) or {}
    cmd = (payload.get("cmd") or "").strip()
    key = re.sub(r"\s+", " ", cmd)

    if is_privesc(key):
        bust(f"Privilege-escalation attempt detected on {TARGET_HOST} "
             f"(sudo abuse via '{cmd}').")
        return jsonify(ok=False, busted=True,
                       title="SOC ALERT — PRIVILEGE ESCALATION",
                       reason=("A sudo privilege-escalation attempt on " + TARGET_HOST +
                               " tripped the EDR rule. Session terminated."),
                       out="[!] sudo: escalation blocked by policy — SOC has been notified.")

    is_vault_find = key in ("find / -name *secret*", "find / -name '*secret*'")
    is_vault_cat  = key.startswith("cat") and "final_flag.txt" in key
    if is_vault_find or is_vault_cat:
        if not has("FLAG-4"):
            return jsonify(ok=True, out=VAULT_LOCKED)
        out = ("/home/svc_backup/.secret_vault/final_flag.txt" if is_vault_find
               else FLAGS["FLAG-5"])
        return jsonify(ok=True, out=out)

    out = None
    if key in FAKE_FS:
        out = FAKE_FS[key]()
    elif key.startswith("cat flag"):
        out = FLAGS["FLAG-4"]

    if out is None:
        return jsonify(ok=True, out=f"bash: {cmd}: command not found (type 'help')")

    # Shell only PRINTS flags - player copies them to Mission Control to score.
    return jsonify(ok=True, out=out)


# --------------------------------------------------------------------------- #
#  Flag submission (the ONLY way to score) + status + finish
# --------------------------------------------------------------------------- #
@app.route("/submit", methods=["POST"])
@require_player
def submit():
    if request.is_json:
        val = (request.get_json(silent=True) or {}).get("flag", "")
    else:
        val = request.form.get("flag", "")
    val = (val or "").strip()

    p = progress()
    for fid, fval in FLAGS.items():
        if val == fval:
            # already captured earlier?
            if fid in p["captured"]:
                return jsonify(ok=True, newly=False, already=True, flag=fid,
                               points=p["points"], captured=p["captured"])
            # clock expired?
            if time_left() <= 0:
                return jsonify(ok=False, expired=True,
                               msg="⏱ Time's up — the run has ended.")
            # good capture
            capture(fid)
            done = len(p["captured"]) == len(FLAGS)
            if done:
                # Full compromise -> end the run and bank the score right away.
                record_score(finished=True)
            return jsonify(ok=True, newly=True, flag=fid,
                           points=p["points"], captured=p["captured"],
                           done=done, elapsed=elapsed())
    return jsonify(ok=False, msg="Not a valid flag.")


@app.route("/status")
@require_player
def status():
    p = progress()
    return jsonify(player=p["player"], points=p["points"],
                   captured=p["captured"], total=len(FLAGS),
                   elapsed=elapsed(), left=time_left(),
                   busted=p.get("busted", False))


@app.route("/finish")
@require_player
def finish():
    p = progress()
    done = len(p["captured"]) == len(FLAGS)
    # Records once (bust / win already recorded on their own; this covers timeout).
    record_score(finished=done)
    return render_template("finish.html", title=APP_TITLE,
                           p=p, elapsed=elapsed(), done=done, total=len(FLAGS),
                           busted=p.get("busted", False),
                           bust_reason=p.get("bust_reason"))


# --------------------------------------------------------------------------- #
#  Big-screen leaderboard
# --------------------------------------------------------------------------- #
@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html", title=APP_TITLE)


@app.route("/leaderboard/data")
def leaderboard_data():
    con = db()
    rows = con.execute(
        "SELECT player, points, flags, seconds, finished FROM scores "
        "ORDER BY points DESC, seconds ASC LIMIT 15"
    ).fetchall()
    con.close()

    def fmt(s):
        return f"{s // 60:02d}:{s % 60:02d}"

    data = [dict(rank=i + 1, player=r["player"], points=r["points"],
                 flags=r["flags"], time=fmt(r["seconds"]),
                 finished=bool(r["finished"])) for i, r in enumerate(rows)]
    return jsonify(data)


@app.route("/health")
def health():
    return jsonify(status="ok", event=EVENT_NAME)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
