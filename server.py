# server.py
import random
from typing import Dict, Any
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from collections import deque

from board import BOARD, Tile
from logic import (
    generate_lc_question, score_lc_answer, LC_REWARDS,
    generate_sd_prompt, score_sd_answer,
    generate_beh_prompt, score_beh_answer,
    generate_card, lap_income, llm_status
)

GAME: Dict[str, Any] = {}


def _debug(msg: str):
    print(f"[server] {msg}")


# FORCED_ROLLS = deque([
#     (3, 4),
# ])


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
    _debug(f"new_game created, llm_status={llm_status()}")


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
        html = f.read()
    _debug("GET / served index.html")
    return HTMLResponse(html)


# Keep this for your own sanity checks if you ever need it,
# but it is no longer surfaced in UI or regular responses.
@app.get("/llm_status")
def get_llm_status():
    st = llm_status()
    _debug(f"GET /llm_status -> {st}")
    return st


@app.get("/state")
def get_state():
    if not GAME:
        new_game()
    _debug("GET /state")
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
    _debug("POST /new")
    return {"ok": True}


@app.post("/roll")
def post_roll():
    if not GAME:
        new_game()

    if GAME.get("skip_turn"):
        GAME["skip_turn"] = False
        GAME["turns"] -= 1
        _debug("POST /roll skipped a turn")
        return {"skipped": True, "message": "Turn skipped", "pos": GAME["pos"], "pos_prev": GAME["pos_prev"],
                "path": [], "d1": 0, "d2": 0, "total": 0}

    if 'FORCED_ROLLS' in globals() and isinstance(globals().get('FORCED_ROLLS'), deque) and globals()['FORCED_ROLLS']:
        d1, d2 = globals()['FORCED_ROLLS'].popleft()
    else:
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
    total = d1 + d2

    old = GAME["pos"]
    path = [(old + i) % len(BOARD) for i in range(1, total + 1)]
    newp = path[-1]

    GAME["pos_prev"] = old
    GAME["pos"] = newp
    GAME["passed_start"] = newp < old

    _debug(f"POST /roll d1={d1} d2={d2} total={total} old={old} new={newp}")
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

    _debug(f"POST /prefetch pos={pos} has_prefetch={GAME['prefetch'] is not None}")
    return {"ok": True, "has_prefetch": GAME["prefetch"] is not None}


@app.post("/resolve")
def post_resolve():
    landing = BOARD[GAME["pos"]]

    if landing.ttype == "COMPANY" and landing.payload.get("group") not in ("RR", "UTIL"):
        if GAME.get("prefetch") and GAME["prefetch"].get("pos") == GAME["pos"]:
            GAME["pending"] = GAME["prefetch"]["pending"]
            GAME["prefetch"] = None
            _debug("POST /resolve served prefetched pending")
            return {"pending": GAME["pending"]}

        qkind = (landing.payload.get("qkind") or "").upper()
        diff = lc_diff_for_side(GAME["pos"])
        if qkind == "LC":
            q = generate_lc_question(diff)
            GAME["pending"] = {"type": f"LC_{diff}", "question": q}
            _debug("POST /resolve created LC pending")
            return {"pending": GAME["pending"]}
        if qkind == "SD":
            q = generate_sd_prompt(diff)
            GAME["pending"] = {"type": "SYS_DESIGN", "question": q, "difficulty": diff}
            _debug("POST /resolve created SD pending")
            return {"pending": GAME["pending"]}
        if qkind == "BH":
            q = generate_beh_prompt(diff)
            GAME["pending"] = {"type": "BEHAVIORAL", "question": q, "difficulty": diff}
            _debug("POST /resolve created BH pending")
            return {"pending": GAME["pending"]}
        return resolve_non_llm_immediate(landing)

    GAME["prefetch"] = None
    _debug("POST /resolve non-company tile")
    return resolve_non_llm_immediate(landing)


@app.post("/submit_answer")
def post_submit_answer(payload: Dict[str, Any]):
    p = GAME.get("pending")
    if not p:
        _debug("POST /submit_answer but no pending")
        return JSONResponse({"ok": False, "error": "No pending challenge"}, status_code=400)

    text = payload.get("text", "") or ""
    kind = p["type"]

    _debug(f"POST /submit_answer kind={kind}")
    if kind in ("LC_EASY", "LC_MED", "LC_HARD", "LC_MEDIUM"):
        if kind == "LC_MEDIUM":
            kind = "LC_MED"
        q = p["question"]
        res = score_lc_answer(q, text)
        rewards = LC_REWARDS[kind if kind in LC_REWARDS else "LC_MED"]
        _debug(f"LC correct={res.get('correct')}")
        if res.get("correct"):
            GAME["cash"] += rewards["pass_cash"]
            GAME["offers"] += rewards["pass_offers"]
            GAME["last_outcome"] = {
                "kind": "success",
                "title": f"Correct - +${rewards['pass_cash']}, +{rewards['pass_offers']} offers",
                "feedback": res.get("feedback", ""),
            }
        else:
            GAME["last_outcome"] = {
                "kind": "error",
                "title": "Incorrect - no reward",
                "feedback": res.get("feedback", ""),
            }

    elif kind == "SYS_DESIGN":
        q = p["question"]
        res = score_sd_answer(q.get("rubric", []), text)
        _debug(f"SD correct={res.get('correct')}")
        if res.get("correct"):
            GAME["cash"] += 150
            GAME["offers"] += 3
            GAME["last_outcome"] = {
                "kind": "success",
                "title": "Correct - +$150, +3 offers",
                "feedback": res.get("feedback", ""),
            }
        else:
            GAME["last_outcome"] = {
                "kind": "error",
                "title": "Incorrect - no reward",
                "feedback": res.get("feedback", ""),
            }

    elif kind == "BEHAVIORAL":
        res = score_beh_answer(text)
        _debug(f"BH correct={res.get('correct')}")
        if res.get("correct"):
            GAME["cash"] += 80
            GAME["offers"] += 2
            GAME["last_outcome"] = {
                "kind": "success",
                "title": "Correct - +$80, +2 offers",
                "feedback": res.get("feedback", ""),
            }
        else:
            GAME["last_outcome"] = {
                "kind": "error",
                "title": "Incorrect - no reward",
                "feedback": res.get("feedback", ""),
            }

    GAME["pending"] = None
    end_turn()

    _debug("POST /submit_answer completed")
    return {
        "ok": True,
        "cash": GAME["cash"],
        "offers": GAME["offers"],
        "turns": GAME["turns"],
        "last_outcome": GAME["last_outcome"],
    }
