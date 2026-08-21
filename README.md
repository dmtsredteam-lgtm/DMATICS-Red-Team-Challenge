# DMATICS Red Team Challenge — GISEC 2026 Booth Edition

A little **10-minute "breach the target" game** for the DMATICS booth. Five stages,
100 points, a live leaderboard, and a *fake* shell that can't touch the host — safe
to leave running on a public show-floor network all day. One Docker container, no
internet needed.

Target org is a made-up company, **Aegis Vault Systems**. DMATICS is the red team
running the op (branding on the nav, leaderboard and debrief).

> *"Can you breach the target before the blue team burns your access?"*

---

## 1. How it plays — a proper CTF chain

Stages unlock **strictly in order**. You **find** each flag out in the target, then
**submit it on Mission Control** to score *and* unlock the next stage. Mission
Control is the hub — every stage is a direct link (**✓ done / Enter ▸ / 🔒 locked**),
so you never restart from recon.

| Stage | Phase | Find the flag by… | Unlocks after |
|------:|-------|-------------------|---------------|
| 1 | **Reconnaissance** | View-Source on the staff directory → FLAG-1 | *(open from start)* |
| 2 | **Credential Access** | Log in `john.smith / Summer2026` → FLAG-2 on the login page | submit **FLAG-1** |
| 3 | **Lateral Movement** | Open `passwords.txt` on the share → FLAG-3 + `svc_backup` creds | submit **FLAG-2** |
| 4 | **Foothold** | SSH to `aegis-web01`, `cat flag.txt` → FLAG-4 | submit **FLAG-3** |
| 5 | **Exfiltration** | `find / -name '*secret*'` then `cat` the vault → FLAG-5 | submit **FLAG-4** |

The **only** place you submit flags is Mission Control. The SSH console just prints
the flags — copy them back to Mission Control to score.

**Ending the run:** it ends automatically — grab all 5 flags for a **victory
takeover screen** (score auto-recorded), get **caught by the SOC**, or let the
**10-minute clock** run out. Any of these records your score to the leaderboard.

Total: **100 points**. Confident visitor ~5–8 min; a beginner ~10 with a nudge.

---

## 2. The SOC bites back

Get noisy and the (simulated) blue team catches you — a full-screen **SOC ALERT**
fires, the run ends, and your score-so-far is auto-recorded (shown without the ✓
that marks a full clear):

1. **Staff-portal brute force** — `LOGIN_MAX` (default **4**) wrong passwords → lockout.
2. **SSH brute force** — `SSH_MAX` (default **3**) wrong passwords on the console.
3. **Privilege escalation** — in the shell, `sudo -l` is fine, but any escalation
   (`sudo su`, `sudo -i`, GTFObins `sudo find … -exec /bin/sh \;`, etc.) trips the EDR.

Tune thresholds (`LOGIN_MAX`, `SSH_MAX`) and escalation patterns (`PRIVESC_TOKENS`)
at the top of `app.py`.

---

## 3. Quick start (Docker)

```bash
cd dmatics-redteam
docker compose up -d --build
```

- **Player kiosk / tablets:** `http://<booth-host-ip>:8000/`
- **Big-screen leaderboard:** `http://<booth-host-ip>:8000/leaderboard`

Reset scores: `docker compose down && rm -f data/leaderboard.db`.
Laptop demo: `pip install -r requirements.txt && python app.py`.

---

## 4. Look & sound (hacker theme)

- **`static/js/matrix-bg.js`** — animated red digital-rain background (canvas, ~24fps).
- **`static/js/sound.js`** — synth soundtrack + UI SFX, **all live, no audio files**. SOUND ON/OFF toggle bottom-right.
- **`static/js/soc.js`** — the full-screen **SOC ALERT** modal (lock-outs / priv-esc).
- **`static/js/win.js`** — the **victory takeover**: "ACCESS GRANTED", neon confetti burst, victory jingle, stats.
- **`static/js/fx.js`** — stagger reveals, "decrypt" typewriter, glitch-on-hover.
- **`static/css/style.css`** — glassmorphism cards, CRT scanlines, neon-red 3D buttons. One `:root` block to reskin.
- **`static/img/`** — DMATICS logos (white PNG on the dark theme; blue for light/print).

---

## 5. Tuning & config (top of `app.py`)

```python
LOGIN_MAX, SSH_MAX      = 4, 3
STAGE_REQUIRES          = {1:None, 2:"FLAG-1", 3:"FLAG-2", 4:"FLAG-3", 5:"FLAG-4"}
FLAGS = { ... }
TARGET_ORG, TARGET_HOST = "Aegis Vault Systems", "aegis-web01"
VALID_USER, VALID_PASS  = "john.smith", "Summer2026"
SVC_USER,  SVC_PASS     = "svc_backup", "Backup@2026!"
```

If you change `SVC_PASS`, update `challenge_files/passwords.txt`. Run length is
`GAME_SECONDS` (env var, default 600).

---

## 6. Why the shell is safe

Stage 4/5 uses a **fake, whitelisted terminal** — no real OS commands, no
subprocess. Only a fixed set of inputs return output; everything else is *command
not found*, and any `sudo` escalation is intercepted. A visitor can't escape to the host.

---

## 7. Files

```
dmatics-redteam/
├── app.py                  # Flask: staged CTF flow, lock-outs, fake shell, scoring
├── requirements.txt · Dockerfile · docker-compose.yml
├── templates/              # branded UI (dark/red hacker theme)
├── static/{css,js,img}/    # style + matrix-bg/sound/soc/win/fx + logos
├── challenge_files/        # passwords.txt / onboarding_guide.txt / Q3_financials.csv
└── data/                   # leaderboard.db (auto-created, persisted)
```

---

## 8. Per-day checklist

- [ ] `docker compose up -d --build`
- [ ] Change `SECRET_KEY` in `docker-compose.yml` from the default
- [ ] `/leaderboard` on the big screen (F11); `/` on each tablet (kiosk mode)
- [ ] One full run (5 flags → victory screen) + trip one SOC alert to sanity-check
- [ ] End of day: note the winner, then `rm -f data/leaderboard.db`

---

*DMATICS IT Solutions LLC — Offensive Security · Dubai, UAE · info@dmaticsonline.com · **Let's Build!***
