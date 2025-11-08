# app.py
import random
import time
import threading
import streamlit as st

from board import BOARD, Tile
from logic import (
    generate_lc_question, score_lc_answer, LC_REWARDS,
    generate_sd_prompt, score_sd_answer,
    generate_beh_prompt, score_beh_answer,
    generate_card, buy_company, lap_income,
)
from visual import render_visual_board


# ---------- State helpers ----------

def new_game():
    st.session_state.state = {
        "pos": 0,
        "pos_prev": 0,
        "anim_path": [],

        "cash": 300,
        "offers": 0,
        "owned": [],          # list of {"name": ...}
        "turns": 20,

        "pending": None,      # {type, question}
        "pending_input": None,
        "submit_busy": False,

        "extra_roll": False,
        "skip_turn": False,
        "passed_start": False,

        # phases:
        # idle -> anim_dice_spin -> anim_dice_show -> anim_move -> resolve
        # resolve may set teleport -> teleport -> idle
        "phase": "idle",
        "dice_face": 1,

        # LLM prefetch
        "needs_llm": False,
        "prefetch_inflight": False,
        "prefetched_pending": None,

        # teleport
        "teleport_to": None,

        # last feedback
        "last_outcome": None,
    }

def init_state():
    if "state" not in st.session_state:
        new_game()

def S():
    return st.session_state.state


# ---------- HUD ----------

def draw_hud():
    s = S()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cash", f"${s['cash']}")
    c2.metric("Offer Points", s["offers"])
    c3.metric("Turns Left", s["turns"])
    c4.metric("Owned Companies", len(s["owned"]))


# ---------- Outcome ----------

def render_last_outcome():
    s = S()
    last = s.get("last_outcome")
    if not last:
        return
    kind = last.get("kind", "info")
    title = last.get("title", "")
    feedback = last.get("feedback", "")

    if kind == "success":
        st.success(title)
    elif kind == "warning":
        st.warning(title)
    elif kind == "error":
        st.error(title)
    else:
        st.info(title)

    if feedback:
        st.info(feedback)


# ---------- Turn helper ----------

def end_turn(s):
    if s.get("extra_roll"):
        s["extra_roll"] = False
        return
    s["turns"] -= 1


# ---------- Non-LLM tile resolution ----------

def resolve_non_llm_tile(s, tile: Tile):
    # Lap income if we passed start during this move
    if s.get("passed_start"):
        inc = lap_income(s)
        if inc:
            s["cash"] += inc
        s["passed_start"] = False

    t = tile.ttype

    if t == "START":
        end_turn(s)
        return

    if t == "JAIL":
        end_turn(s)
        return

    if t == "FREE_PARKING":
        end_turn(s)
        return

    if t == "GOTO_JAIL":
        jail_idx = next((i for i, tt in enumerate(BOARD) if tt.ttype == "JAIL"), None)
        if jail_idx is not None:
            s["teleport_to"] = jail_idx
            s["pos_prev"] = s["pos"]
            s["pos"] = jail_idx
            s["anim_path"] = []
            s["phase"] = "teleport"
        return  # end_turn after teleport

    if t in ("CHANCE", "COMMUNITY"):
        card = generate_card()
        eff = card.get("effect", {})
        s["cash"] += eff.get("cash", 0)
        s["offers"] += eff.get("offers", 0)
        if eff.get("turn_skip"):
            s["skip_turn"] = True
        if eff.get("extra_roll"):
            s["extra_roll"] = True
        end_turn(s)
        return

    if t == "COMPANY":
        handle_company_tile(s, tile)
        end_turn(s)
        return


# ---------- Company handling ----------

def handle_company_tile(s, tile: Tile):
    name = tile.name
    price = tile.payload.get("price", 300)
    gate = tile.payload.get("gate", "LC_EASY")

    if any(c["name"] == name for c in s["owned"]):
        st.info(f"You already own {name}.")
        return

    thresholds = {"LC_EASY": 2, "LC_MED": 4, "LC_HARD": 6}
    needed = thresholds.get(gate, 3)

    st.info(f"Company: {name} — ${price} — requires ≥{needed} offer points.")
    if s["offers"] >= needed:
        if st.button(f"Buy {name} for ${price}"):
            if buy_company(s, name, price):
                st.success(f"Purchased {name}!")
    else:
        st.caption(f"Not enough offer points ({s['offers']}/{needed}).")


# ---------- Pending challenge (with submit spinner) ----------

def render_pending_challenge():
    s = S()
    p = s.get("pending")
    if not p:
        return

    # Busy pass: we already clicked submit
    if s.get("submit_busy"):
        t = p["type"]
        with st.spinner("Scoring your answer..."):
            text = s.get("pending_input") or ""

            if t in ("LC_EASY", "LC_MED", "LC_HARD"):
                q = p["question"]
                res = score_lc_answer(q, text)
                rewards = LC_REWARDS[t]
                if res["pass_fail"] == "PASS":
                    s["cash"] += rewards["pass_cash"]
                    s["offers"] += rewards["pass_offers"]
                    s["last_outcome"] = {
                        "kind": "success",
                        "title": f"PASS (rating {res['rating']}) — +${rewards['pass_cash']}, +{rewards['pass_offers']} offers",
                        "feedback": res["feedback"],
                    }
                else:
                    s["cash"] += rewards["fail_cash"]
                    s["last_outcome"] = {
                        "kind": "error",
                        "title": f"FAIL (rating {res['rating']}) — {rewards['fail_cash']} cash",
                        "feedback": res["feedback"],
                    }

            elif t == "SYS_DESIGN":
                q = p["question"]
                res = score_sd_answer(q.get("rubric", []), text)
                rating = int(res.get("rating", 3))
                if rating >= 4:
                    s["cash"] += 150
                    s["offers"] += 3
                    s["last_outcome"] = {"kind": "success", "title": f"Strong design (rating {rating}) — +$150, +3 offers", "feedback": res.get("feedback", "")}
                elif rating == 3:
                    s["cash"] += 50
                    s["offers"] += 1
                    s["last_outcome"] = {"kind": "warning", "title": "Decent (rating 3) — +$50, +1 offer", "feedback": res.get("feedback", "")}
                else:
                    s["cash"] -= 50
                    s["last_outcome"] = {"kind": "error", "title": f"Weak (rating {rating}) — -$50", "feedback": res.get("feedback", "")}

            elif t == "BEHAVIORAL":
                res = score_beh_answer(text)
                rating = int(res.get("rating", 3))
                if rating >= 4:
                    s["cash"] += 80
                    s["offers"] += 2
                    s["last_outcome"] = {"kind": "success", "title": f"Strong (rating {rating}) — +$80, +2 offers", "feedback": res.get("feedback", "")}
                elif rating == 3:
                    s["cash"] += 30
                    s["offers"] += 1
                    s["last_outcome"] = {"kind": "warning", "title": "Okay (rating 3) — +$30, +1 offer", "feedback": res.get("feedback", "")}
                else:
                    s["cash"] -= 20
                    s["last_outcome"] = {"kind": "error", "title": f"Needs work (rating {rating}) — -$20", "feedback": res.get("feedback", "")}

        s["pending"] = None
        s["pending_input"] = None
        s["submit_busy"] = False
        end_turn(s)
        st.rerun()

    # Normal UI
    t = p["type"]
    st.divider()
    c = st.container()

    if t in ("LC_EASY", "LC_MED", "LC_HARD"):
        q = p["question"]
        with c:
            st.subheader("LeetCode Challenge")
            st.write(q.get("question"))
            with st.expander("Hints"):
                for h in q.get("hints", []):
                    st.write("- " + h)
            with st.form(key=f"lc_form_{t}"):
                ans = st.text_area("Describe your approach (no full code needed)", key=f"lc_text_{t}")
                submitted = st.form_submit_button("Submit answer", use_container_width=True)
        if submitted:
            s["pending_input"] = ans
            s["submit_busy"] = True
            st.rerun()
        return

    if t == "SYS_DESIGN":
        q = p["question"]
        with c:
            st.subheader("System Design Mini")
            st.write(q.get("prompt"))
            with st.expander("What I’m looking for"):
                for item in q.get("rubric", []):
                    st.write("- " + item)
            with st.form(key="sd_form"):
                ans = st.text_area("Write 5–8 bullets outlining your design", key="sd_text")
                submitted = st.form_submit_button("Submit design", use_container_width=True)
        if submitted:
            s["pending_input"] = ans
            s["submit_busy"] = True
            st.rerun()
        return

    if t == "BEHAVIORAL":
        q = p["question"]
        with c:
            st.subheader("Behavioral (STAR)")
            st.write(q.get("prompt"))
            st.caption(q.get("tip"))
            with st.form(key="beh_form"):
                ans = st.text_area("Your STAR answer", key="beh_text")
                submitted = st.form_submit_button("Submit behavioral answer", use_container_width=True)
        if submitted:
            s["pending_input"] = ans
            s["submit_busy"] = True
            st.rerun()
        return


# ---------- App ----------

st.set_page_config(page_title="🎲 AI Interview Monopoly", page_icon="🎲", layout="wide")
st.title("🎲 AI Interview Monopoly")

init_state()
state = S()

# Top controls
colA, _ = st.columns([1, 3])
with colA:
    if st.button("New Game"):
        new_game()
        st.rerun()

draw_hud()

phase = state["phase"]

# ---- Phase machine: always render board, then mutate+rerun ----

if phase == "anim_dice_spin":
    # Pawn at prev; die spinning random faces
    render_visual_board(
        BOARD,
        pos=state["pos_prev"],
        prev_pos=state["pos_prev"],
        path=[],
        owned_names=[c["name"] for c in state["owned"]],
        show_dice=True,
        dice_face=state["dice_face"],
        dice_spin=True,
        animate=False,
        teleport=False,
    )
    time.sleep(0.7)
    state["phase"] = "anim_dice_show"
    st.rerun()

elif phase == "anim_dice_show":
    # Pawn still at prev; die frozen on final face
    render_visual_board(
        BOARD,
        pos=state["pos_prev"],
        prev_pos=state["pos_prev"],
        path=[],
        owned_names=[c["name"] for c in state["owned"]],
        show_dice=True,
        dice_face=state["dice_face"],
        dice_spin=False,
        animate=False,
        teleport=False,
    )
    time.sleep(0.5)
    state["phase"] = "anim_move"
    st.rerun()

elif phase == "anim_move":
    # Pawn walks along full anim_path; die hidden
    path = state.get("anim_path", []) or []
    steps = len(path)
    render_visual_board(
        BOARD,
        pos=state["pos"],
        prev_pos=state["pos_prev"],
        path=path,
        owned_names=[c["name"] for c in state["owned"]],
        show_dice=False,
        dice_face=state["dice_face"],
        dice_spin=False,
        animate=True,
        teleport=False,
    )
    # ensure we wait long enough for all hops (fixes 6-step teleport issue)
    hop_ms = 0.26
    total = steps * hop_ms + 0.15
    time.sleep(min(total, 3.0))
    state["phase"] = "resolve"
    st.rerun()

elif phase == "teleport":
    # Pawn already at Jail; show flash
    render_visual_board(
        BOARD,
        pos=state["pos"],
        prev_pos=state["pos"],
        path=[],
        owned_names=[c["name"] for c in state["owned"]],
        show_dice=False,
        dice_face=state["dice_face"],
        dice_spin=False,
        animate=False,
        teleport=True,
    )
    time.sleep(0.4)
    end_turn(state)
    state["teleport_to"] = None
    state["phase"] = "idle"
    st.rerun()

elif phase == "resolve":
    # Static board; compute outcome
    render_visual_board(
        BOARD,
        pos=state["pos"],
        prev_pos=state["pos"],
        path=[],
        owned_names=[c["name"] for c in state["owned"]],
        show_dice=False,
        dice_face=state["dice_face"],
        dice_spin=False,
        animate=False,
        teleport=False,
    )

    landing = BOARD[state["pos"]]

    if state["needs_llm"]:
        if state.get("prefetched_pending"):
            state["pending"] = state["prefetched_pending"]
            state["prefetched_pending"] = None
        else:
            with st.spinner("Interview question incoming…"):
                t = landing.ttype
                if t in ("LC_EASY", "LC_MED", "LC_HARD"):
                    diff = {"LC_EASY": "EASY", "LC_MED": "MEDIUM", "LC_HARD": "HARD"}[t]
                    q = generate_lc_question(diff)
                    state["pending"] = {"type": t, "question": q}
                elif t == "SYS_DESIGN":
                    q = generate_sd_prompt()
                    state["pending"] = {"type": "SYS_DESIGN", "question": q}
                elif t == "BEHAVIORAL":
                    q = generate_beh_prompt()
                    state["pending"] = {"type": "BEHAVIORAL", "question": q}
        state["prefetch_inflight"] = False
        state["needs_llm"] = False
    else:
        resolve_non_llm_tile(state, landing)
        if state["phase"] == "teleport":
            st.rerun()

    if state["phase"] == "resolve":
        state["anim_path"] = []
        state["pos_prev"] = state["pos"]
        state["phase"] = "idle"
    st.rerun()

else:
    # idle: stable view
    render_visual_board(
        BOARD,
        pos=state["pos"],
        prev_pos=state["pos"],
        path=[],
        owned_names=[c["name"] for c in state["owned"]],
        show_dice=False,
        dice_face=state["dice_face"],
        dice_spin=False,
        animate=False,
        teleport=False,
    )

# ---- Tail: outcome, pending UI, roll button ----

render_last_outcome()

# Game over
if state["turns"] <= 0:
    st.success(
        f"Game over! Final: Cash ${state['cash']} | "
        f"Offers {state['offers']} | Companies {len(state['owned'])}"
    )
    st.stop()

# Pending challenge UI (handles submit + spinner internally)
render_pending_challenge()

# Only show Roll when ready
if state["phase"] == "idle" and not state.get("pending") and not state.get("submit_busy"):
    if st.button("Roll 🎲", use_container_width=True):
        state["last_outcome"] = None

        # skip turn?
        if state.get("skip_turn"):
            state["skip_turn"] = False
            state["turns"] -= 1
            st.rerun()

        roll = random.randint(1, 6)
        old_pos = state["pos"]
        state["pos_prev"] = old_pos

        path = [ (old_pos + i) % len(BOARD) for i in range(1, roll + 1) ]
        state["anim_path"] = path
        state["pos"] = path[-1]
        state["passed_start"] = state["pos"] < old_pos
        state["dice_face"] = roll

        landing = BOARD[state["pos"]]
        needs_llm = landing.ttype in ("LC_EASY", "LC_MED", "LC_HARD", "SYS_DESIGN", "BEHAVIORAL")
        state["needs_llm"] = needs_llm

        # LLM prefetch in background
        if needs_llm:
            def _prefetch():
                try:
                    if state.get("passed_start"):
                        inc = lap_income(state)
                        if inc:
                            state["cash"] += inc
                    t = landing.ttype
                    if t in ("LC_EASY", "LC_MED", "LC_HARD"):
                        diff = {"LC_EASY": "EASY", "LC_MED": "MEDIUM", "LC_HARD": "HARD"}[t]
                        q = generate_lc_question(diff)
                        state["prefetched_pending"] = {"type": t, "question": q}
                    elif t == "SYS_DESIGN":
                        q = generate_sd_prompt()
                        state["prefetched_pending"] = {"type": "SYS_DESIGN", "question": q}
                    elif t == "BEHAVIORAL":
                        q = generate_beh_prompt()
                        state["prefetched_pending"] = {"type": "BEHAVIORAL", "question": q}
                finally:
                    state["prefetch_inflight"] = False

            state["prefetch_inflight"] = True
            state["prefetched_pending"] = None
            threading.Thread(target=_prefetch, daemon=True).start()
        else:
            state["prefetch_inflight"] = False
            state["prefetched_pending"] = None

        # start animation flow
        state["phase"] = "anim_dice_spin"
        st.rerun()
