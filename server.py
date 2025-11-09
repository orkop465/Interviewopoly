# server.py
import random
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from collections import deque

from board import BOARD, Tile
from logic import (
    generate_lc_question, score_lc_answer, LC_REWARDS,
    generate_sd_prompt, score_sd_answer,
    generate_beh_prompt, score_beh_answer,
    generate_card, llm_status
)

GAME: Dict[str, Any] = {}


def _debug(msg: str):
    print(f"[server] {msg}")


# FORCED_ROLLS = deque([
#     (2, 2),
#     (6, 5),
#     (5, 5),
#     (5, 5),
#     (5, 4),
# ])


def new_game():
    GAME.clear()
    GAME.update({
        "pos": 0,
        "pos_prev": 0,
        "offers": 0,
        "owned": [],  # list of {"name": <tile_name>}
        "houses": {},  # map: property_name -> house_count (int)
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


def _is_ownable_property(tile: Tile) -> bool:
    return tile.ttype == "COMPANY" and tile.payload.get("group") not in ("RR", "UTIL")


def _landed_property_name() -> Optional[str]:
    tile = BOARD[GAME["pos"]]
    if _is_ownable_property(tile):
        return tile.name
    return None


def _owned_names_set() -> set:
    return {o.get("name") for o in GAME["owned"] if isinstance(o, dict)}


def _group_of(tile: Tile) -> Optional[str]:
    if not _is_ownable_property(tile):
        return None
    return tile.payload.get("group")


def _properties_in_group(group: str) -> List[str]:
    return [t.name for t in BOARD if _is_ownable_property(t) and t.payload.get("group") == group]


def _has_full_monopoly(group: str) -> bool:
    if not group:
        return False
    needed = set(_properties_in_group(group))
    if not needed:
        return False
    return needed.issubset(_owned_names_set())


def _missing_in_group(group: str) -> List[str]:
    needed = set(_properties_in_group(group))
    return sorted(list(needed - _owned_names_set()))


def _grant_ownership_if_applicable():
    """Add current tile to ownership if ownable and not already owned."""
    prop = _landed_property_name()
    if not prop:
        return
    if any(o.get("name") == prop for o in GAME["owned"]):
        return
    GAME["owned"].append({"name": prop})


def _maybe_build_house_on_current() -> bool:
    """
    If player already owns the landed property AND owns the full color group,
    increment its house count. Returns True if a house was built.
    """
    prop = _landed_property_name()
    if not prop:
        return False
    if prop not in _owned_names_set():
        return False
    tile = BOARD[GAME["pos"]]
    group = _group_of(tile)
    if not _has_full_monopoly(group):
        return False
    GAME["houses"][prop] = GAME["houses"].get(prop, 0) + 1
    return True


def resolve_non_llm_immediate(tile: Tile):
    # Passing GO grants offer points
    if GAME.get("passed_start"):
        GAME["offers"] += 200
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
        GAME["last_outcome"] = {"kind": "warning", "title": "Go to Jail!", "feedback": "", "judge_source": None}
        return {"pending": None}

    if t in ("CHANCE", "COMMUNITY"):
        card = generate_card()
        eff = card.get("effect", {})
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
            "judge_source": None,
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


@app.get("/llm_status")
def get_llm_status():
    st = llm_status()
    _debug(f"GET /llm_status -> {st}")
    return st


@app.get("/state")
def get_state():
    if not GAME:
        new_game()
    st = llm_status()
    _debug(
        f"GET /state llm={st['mode']} dotenv_loaded={st['dotenv_loaded']} api_key_present={st['api_key_present']} use_llm_flag={st['use_llm_flag']} model={st['model']} last_error={st['last_llm_error']}")
    return {
        "pos": GAME["pos"],
        "pos_prev": GAME["pos_prev"],
        "offers": GAME["offers"],
        "owned": GAME["owned"],
        "houses": GAME["houses"],
        "turns": GAME["turns"],
        "pending": GAME["pending"],
        "last_outcome": GAME.get("last_outcome"),
        "has_prefetch": GAME.get("prefetch") is not None,
        "llm": st,
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
        # If the property is already owned but not a full monopoly, do not prefetch
        prop_name = landing.name
        owned = prop_name in _owned_names_set()
        group = _group_of(landing)
        has_mono = _has_full_monopoly(group) if owned else False

        if owned and not has_mono:
            GAME["prefetch"] = None
            _debug("POST /prefetch suppressed due to no full monopoly on owned property")
            return {"ok": True, "has_prefetch": False}

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
        prop_name = landing.name
        owned = prop_name in _owned_names_set()
        group = _group_of(landing)
        has_mono = _has_full_monopoly(group) if owned else False

        # If owned but not a full monopoly: no question, show info, end turn
        if owned and not has_mono:
            missing = _missing_in_group(group)
            GAME["last_outcome"] = {
                "kind": "info",
                "title": "You own this, but not the full set",
                "feedback": f"You need the entire {group} set to start building. Missing: {', '.join(missing)}." if missing else f"You need the entire {group} set to start building.",
                "judge_source": None,
            }
            end_turn()
            _debug(f"POST /resolve owned-no-monopoly, missing={missing}")
            return {"pending": None}

        # If not owned, or owned with a full monopoly, proceed to create a question
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
    build_house = False

    if kind in ("LC_EASY", "LC_MED", "LC_HARD", "LC_MEDIUM"):
        if kind == "LC_MEDIUM":
            kind = "LC_MED"
        q = p["question"]
        res = score_lc_answer(q, text)
        rewards = LC_REWARDS[kind if kind in LC_REWARDS else "LC_MED"]
        _debug(f"LC judged_by={res.get('judge_source')} correct={res.get('correct')}")
        if res.get("correct"):
            GAME["offers"] += rewards["pass_offers"]
            before_owned = _landed_property_name() in _owned_names_set()
            _grant_ownership_if_applicable()
            if before_owned:
                build_house = _maybe_build_house_on_current()
            GAME["last_outcome"] = {
                "kind": "success",
                "title": f"Correct +{rewards['pass_offers']} offers" + (" - House built!" if build_house else ""),
                "feedback": res.get("feedback", ""),
                "judge_source": res.get("judge_source", None),
            }
        else:
            GAME["last_outcome"] = {
                "kind": "error",
                "title": "Incorrect - no reward",
                "feedback": res.get("feedback", ""),
                "judge_source": res.get("judge_source", None),
            }

    elif kind == "SYS_DESIGN":
        q = p["question"]
        res = score_sd_answer(q.get("rubric", []), text)
        _debug(f"SD judged_by={res.get('judge_source')} correct={res.get('correct')}")
        if res.get("correct"):
            GAME["offers"] += 3
            before_owned = _landed_property_name() in _owned_names_set()
            _grant_ownership_if_applicable()
            if before_owned:
                build_house = _maybe_build_house_on_current()
            GAME["last_outcome"] = {
                "kind": "success",
                "title": "Correct +3 offers" + (" - House built!" if build_house else ""),
                "feedback": res.get("feedback", ""),
                "judge_source": res.get("judge_source", None),
            }
        else:
            GAME["last_outcome"] = {
                "kind": "error",
                "title": "Incorrect - no reward",
                "feedback": res.get("feedback", ""),
                "judge_source": res.get("judge_source", None),
            }

    elif kind == "BEHAVIORAL":
        res = score_beh_answer(text)
        _debug(f"BH judged_by={res.get('judge_source')} correct={res.get('correct')}")
        if res.get("correct"):
            GAME["offers"] += 2
            before_owned = _landed_property_name() in _owned_names_set()
            _grant_ownership_if_applicable()
            if before_owned:
                build_house = _maybe_build_house_on_current()
            GAME["last_outcome"] = {
                "kind": "success",
                "title": "Correct +2 offers" + (" - House built!" if build_house else ""),
                "feedback": res.get("feedback", ""),
                "judge_source": res.get("judge_source", None),
            }
        else:
            GAME["last_outcome"] = {
                "kind": "error",
                "title": "Incorrect - no reward",
                "feedback": res.get("feedback", ""),
                "judge_source": res.get("judge_source", None),
            }

    GAME["pending"] = None
    end_turn()

    st = llm_status()
    _debug(f"POST /submit_answer completed, llm_mode={st['mode']}, last_error={st['last_llm_error']}")
    return {
        "ok": True,
        "offers": GAME["offers"],
        "turns": GAME["turns"],
        "owned": GAME["owned"],
        "houses": GAME["houses"],
        "last_outcome": GAME["last_outcome"],
        "llm": st,
    }
