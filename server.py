# server.py
import random
from typing import Dict, Any
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from board import BOARD, Tile
from logic import (
    generate_lc_question, score_lc_answer, LC_REWARDS,
    generate_sd_prompt, score_sd_answer,
    generate_beh_prompt, score_beh_answer,
    generate_card, lap_income,
)

GAME: Dict[str, Any] = {}

def new_game():
    GAME.clear()
    GAME.update({
        "pos": 0,
        "pos_prev": 0,
        "cash": 300,
        "offers": 0,
        "owned": [],
        "turns": 20,

        "pending": None,
        "prefetch": None,
        "last_outcome": None,

        "skip_turn": False,
        "extra_roll": False,
        "passed_start": False,
    })

def end_turn():
    if GAME.get("extra_roll"):
        GAME["extra_roll"] = False
    else:
        GAME["turns"] -= 1

def side_for_index(i: int) -> str:
    i %= 40
    if i <= 9:
        return "BOTTOM"
    if i <= 19:
        return "LEFT"
    if i <= 29:
        return "TOP"
    return "RIGHT"

def lc_diff_for_side(i: int) -> str:
    side = side_for_index(i)
    if side == "BOTTOM":
        return "EASY"
    if side in ("LEFT", "TOP"):
        return "MEDIUM"
    return "HARD"

def resolve_non_llm_immediate(tile: Tile):
    if GAME.get("passed_start"):
        inc = lap_income(GAME)
        if inc:
            GAME["cash"] += inc
        GAME["passed_start"] = False

    t = tile.ttype
    if t in ("START", "JAIL", "FREE_PARKING"):
        end_turn()
        return {"pending": None}

    if t == "GOTO_JAIL":
        jail_idx = next((i for i, tt in enumerate(BOARD) if tt.ttype == "JAIL"), None)
        if jail_idx is not None:
            GAME["pos_prev"] = GAME["pos"]
            GAME["pos"] = jail_idx
        end_turn()
        GAME["last_outcome"] = {"kind": "warning", "title": "Go to Jail!", "feedback": ""}
        return {"pending": None}

    if t in ("CHANCE", "COMMUNITY"):
        card = generate_card()
        eff = card.get("effect", {})
        GAME["cash"] += eff.get("cash", 0)
        GAME["offers"] += eff.get("offers", 0)
        if eff.get("turn_skip"):
            GAME["skip_turn"] = True
        if eff.get("extra_roll"):
            GAME["extra_roll"] = True
        end_turn()
        GAME["last_outcome"] = {
            "kind": "info",
            "title": card.get("title", t.title()),
            "feedback": card.get("text", ""),
        }
        return {"pending": None}

    return {"pending": None}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/state")
def get_state():
    if not GAME:
        new_game()
    return {
        "pos": GAME["pos"],
        "pos_prev": GAME["pos_prev"],
        "cash": GAME["cash"],
        "offers": GAME["offers"],
        "owned": GAME["owned"],
        "turns": GAME["turns"],
        "pending": GAME["pending"],
        "last_outcome": GAME.get("last_outcome"),
        "has_prefetch": GAME.get("prefetch") is not None,
        "board": [
            {"name": t.name, "ttype": t.ttype, "payload": t.payload}
            for t in BOARD
        ],
    }

@app.post("/new")
def post_new():
    new_game()
    return {"ok": True}

@app.post("/roll")
def post_roll():
    if not GAME:
        new_game()

    if GAME.get("skip_turn"):
        GAME["skip_turn"] = False
        GAME["turns"] -= 1
        return {"skipped": True, "message": "Turn skipped", "pos": GAME["pos"], "pos_prev": GAME["pos_prev"], "path": [], "d1": 0, "d2": 0, "total": 0}

    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total = d1 + d2

    old = GAME["pos"]
    path = [ (old + i) % len(BOARD) for i in range(1, total + 1) ]
    newp = path[-1]

    GAME["pos_prev"] = old
    GAME["pos"] = newp
    GAME["passed_start"] = newp < old

    return {"skipped": False, "d1": d1, "d2": d2, "total": total, "pos": newp, "pos_prev": old, "path": path}

@app.post("/prefetch")
def post_prefetch(pos: int = Body(..., embed=True)):
    landing = BOARD[pos]
    if landing.ttype == "COMPANY" and landing.payload.get("group") not in ("RR", "UTIL"):
        qkind = (landing.payload.get("qkind") or "").upper()
        diff = lc_diff_for_side(pos)
        if qkind == "LC":
            q = generate_lc_question(diff)
            GAME["prefetch"] = {"pos": pos, "pending": {"type": f"LC_{diff}", "question": q}}
        elif qkind == "SD":
            q = generate_sd_prompt(diff)
            GAME["prefetch"] = {"pos": pos, "pending": {"type": "SYS_DESIGN", "question": q, "difficulty": diff}}
        elif qkind == "BH":
            q = generate_beh_prompt(diff)
            GAME["prefetch"] = {"pos": pos, "pending": {"type": "BEHAVIORAL", "question": q, "difficulty": diff}}
        else:
            GAME["prefetch"] = None
    else:
        GAME["prefetch"] = None

    return {"ok": True, "has_prefetch": GAME["prefetch"] is not None}

@app.post("/resolve")
def post_resolve():
    landing = BOARD[GAME["pos"]]

    if landing.ttype == "COMPANY" and landing.payload.get("group") not in ("RR", "UTIL"):
        if GAME.get("prefetch") and GAME["prefetch"].get("pos") == GAME["pos"]:
            GAME["pending"] = GAME["prefetch"]["pending"]
            GAME["prefetch"] = None
            return {"pending": GAME["pending"]}

        qkind = (landing.payload.get("qkind") or "").upper()
        diff = lc_diff_for_side(GAME["pos"])
        if qkind == "LC":
            q = generate_lc_question(diff)
            GAME["pending"] = {"type": f"LC_{diff}", "question": q}
            return {"pending": GAME["pending"]}
        if qkind == "SD":
            q = generate_sd_prompt(diff)
            GAME["pending"] = {"type": "SYS_DESIGN", "question": q, "difficulty": diff}
            return {"pending": GAME["pending"]}
        if qkind == "BH":
            q = generate_beh_prompt(diff)
            GAME["pending"] = {"type": "BEHAVIORAL", "question": q, "difficulty": diff}
            return {"pending": GAME["pending"]}
        return resolve_non_llm_immediate(landing)

    GAME["prefetch"] = None
    return resolve_non_llm_immediate(landing)

@app.post("/submit_answer")
def post_submit_answer(payload: Dict[str, Any]):
    p = GAME.get("pending")
    if not p:
        return JSONResponse({"ok": False, "error": "No pending challenge"}, status_code=400)

    text = payload.get("text", "") or ""
    kind = p["type"]

    if kind in ("LC_EASY", "LC_MED", "LC_HARD", "LC_MEDIUM"):
        if kind == "LC_MEDIUM":
            kind = "LC_MED"
        q = p["question"]
        res = score_lc_answer(q, text)
        rewards = LC_REWARDS[kind if kind in LC_REWARDS else "LC_MED"]
        if res["pass_fail"] == "PASS":
            GAME["cash"] += rewards["pass_cash"]
            GAME["offers"] += rewards["pass_offers"]
            GAME["last_outcome"] = {"kind": "success", "title": f"PASS (rating {res['rating']}) — +${rewards['pass_cash']}, +{rewards['pass_offers']} offers", "feedback": res["feedback"]}
        else:
            GAME["cash"] += rewards["fail_cash"]
            GAME["last_outcome"] = {"kind": "error", "title": f"FAIL (rating {res['rating']}) — {rewards['fail_cash']} cash", "feedback": res["feedback"]}

    elif kind == "SYS_DESIGN":
        q = p["question"]
        res = score_sd_answer(q.get("rubric", []), text)
        rating = int(res.get("rating", 3))
        if rating >= 4:
            GAME["cash"] += 150
            GAME["offers"] += 3
            GAME["last_outcome"] = {"kind": "success", "title": f"Strong design (rating {rating}) — +$150, +3 offers", "feedback": res.get("feedback", "")}
        elif rating == 3:
            GAME["cash"] += 50
            GAME["offers"] += 1
            GAME["last_outcome"] = {"kind": "warning", "title": "Decent (rating 3) — +$50, +1 offer", "feedback": res.get("feedback", "")}
        else:
            GAME["cash"] -= 50
            GAME["last_outcome"] = {"kind": "error", "title": f"Weak (rating {rating}) — -$50", "feedback": res.get("feedback", "")}

    elif kind == "BEHAVIORAL":
        res = score_beh_answer(text)
        rating = int(res.get("rating", 3))
        if rating >= 4:
            GAME["cash"] += 80
            GAME["offers"] += 2
            GAME["last_outcome"] = {"kind": "success", "title": f"Strong (rating {rating}) — +$80, +2 offers", "feedback": res.get("feedback", "")}
        elif rating == 3:
            GAME["cash"] += 30
            GAME["offers"] += 1
            GAME["last_outcome"] = {"kind": "warning", "title": "Okay (rating 3) — +$30, +1 offer", "feedback": res.get("feedback", "")}
        else:
            GAME["cash"] -= 20
            GAME["last_outcome"] = {"kind": "error", "title": f"Needs work (rating {rating}) — -$20", "feedback": res.get("feedback", "")}

    GAME["pending"] = None
    end_turn()

    return {"ok": True, "cash": GAME["cash"], "offers": GAME["offers"], "turns": GAME["turns"], "last_outcome": GAME["last_outcome"]}
