# logic.py
import os
import random
from typing import Dict, Any, List

# Optional OpenAI generation. If no API key is present, fall back to built-ins.
try:
    from openai import OpenAI

    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _maybe_client():
    if _HAS_OPENAI and OPENAI_API_KEY:
        try:
            return OpenAI(api_key=OPENAI_API_KEY)
        except Exception:
            return None
    return None


# ---------- Rewards (unchanged keys used elsewhere) ----------
LC_REWARDS: Dict[str, Dict[str, int]] = {
    "LC_EASY": {"pass_cash": 80, "pass_offers": 2, "fail_cash": 10},
    "LC_MED": {"pass_cash": 120, "pass_offers": 3, "fail_cash": 20},
    "LC_HARD": {"pass_cash": 180, "pass_offers": 4, "fail_cash": 30},
}


# ---------- Utility helpers ----------
def _clean(s: str) -> str:
    return s.strip().replace("\r", "")


def _difficulty_norm(d: str) -> str:
    d = (d or "MEDIUM").upper()
    if d in ("EASY", "MEDIUM", "HARD"):
        return d
    return "MEDIUM"


# ---------- LC generation and scoring ----------
def generate_lc_question(difficulty: str) -> Dict[str, Any]:
    """Return {question, hints} for EASY|MEDIUM|HARD."""
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        prompt = (
            f"Create one coding interview question at {diff} difficulty. "
            "Explain the problem statement clearly. Provide 2 to 4 short hints. "
            "Keep it language-agnostic, avoid full code."
        )
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert coding interviewer."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            text = resp.choices[0].message.content
            # naive split
            parts = text.split("Hints:")
            q = _clean(parts[0])
            hints = []
            if len(parts) > 1:
                for line in parts[1].splitlines():
                    line = line.strip("-• ").strip()
                    if line:
                        hints.append(line)
                    if len(hints) >= 4:
                        break
            return {"question": q, "hints": hints}
        except Exception:
            pass  # fall through to built-ins

    # Built-in templates
    bank = {
        "EASY": [
            (
            "Given an array of integers, return the index of the first duplicate value you encounter while scanning left to right. If none, return -1.",
            ["Use a set to record seen values", "Return early when you find a duplicate"]),
            ("Given a string s, return true if it is an anagram of 'interview', ignoring case and spaces.",
             ["Normalize to lowercase", "Remove spaces before counting letters"]),
        ],
        "MEDIUM": [
            ("Design a function that returns the length of the longest substring with at most two distinct characters.",
             ["Sliding window", "Track counts of characters in the window"]),
            ("Given an array and integer k, return the number of subarrays whose sum equals k.",
             ["Prefix sums", "Hash map of prefix frequencies"]),
        ],
        "HARD": [
            ("Implement LRU cache with O(1) get and put given capacity.",
             ["Doubly linked list plus hash map", "Move to front on access"]),
            ("Given n tasks with prerequisites, return a valid ordering or empty list if impossible.",
             ["Topological sort", "Kahn’s algorithm or DFS cycle check"]),
        ],
    }
    q, hints = random.choice(bank[diff])
    return {"question": q, "hints": hints}


def score_lc_answer(question: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Very simple deterministic scoring. If OpenAI is configured, ask it to rate."""
    client = _maybe_client()
    if client:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a fair technical interviewer. Rate 1 to 6."},
                    {"role": "user",
                     "content": f"Question:\n{question}\n\nCandidate answer:\n{text}\n\nRate 1..6 and give 2-3 lines of feedback."},
                ],
                temperature=0.2,
            )
            msg = resp.choices[0].message.content
            # crude parse
            rating = 4
            for tok in ("6", "5", "4", "3", "2", "1"):
                if f" {tok}" in msg or msg.strip().startswith(tok):
                    rating = int(tok)
                    break
            return {"rating": rating, "pass_fail": "PASS" if rating >= 4 else "FAIL", "feedback": _clean(msg)}
        except Exception:
            pass

    # Baseline offline scoring
    tokens = len((text or "").split())
    rating = 2 if tokens < 25 else 4 if tokens < 120 else 5
    fb = "Concise answer. Consider more detail on complexity." if rating <= 4 else "Good structure and tradeoffs."
    return {"rating": rating, "pass_fail": "PASS" if rating >= 4 else "FAIL", "feedback": fb}


# ---------- SD generation and scoring ----------
def generate_sd_prompt(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    """Return {prompt, rubric} for a system design mini by difficulty."""
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a seasoned systems architect."},
                    {"role": "user", "content":
                        f"Create a system design prompt at {diff} difficulty. "
                        "Keep it ~3 sentences. Include an explicit bullet rubric of 6–8 items "
                        "covering API, storage model, consistency, scalability, bottlenecks, and tradeoffs."},
                ],
                temperature=0.6,
            )
            text = resp.choices[0].message.content
            parts = text.split("\n")
            prompt = []
            rubric: List[str] = []
            section = "prompt"
            for line in parts:
                if line.strip().lower().startswith("rubric"):
                    section = "rubric"
                    continue
                if section == "prompt":
                    prompt.append(line)
                else:
                    t = line.strip("-• ").strip()
                    if t:
                        rubric.append(t)
            prompt_s = _clean("\n".join(prompt))
            if not rubric:
                rubric = ["API shape", "Data model", "Scaling plan", "Consistency choice", "Caching", "Bottlenecks",
                          "Tradeoffs"]
            return {"prompt": prompt_s, "rubric": rubric}
        except Exception:
            pass

    # Built-in templates
    if diff == "EASY":
        prompt = "Design a URL shortener. Support creating and resolving short links, and gathering basic click metrics."
        rubric = [
            "Simple REST API for create/resolve",
            "Key-space and ID generation",
            "Data model for mapping and counters",
            "Handling hot keys and caching",
            "Basic availability and consistency choice",
            "Storage choice rationale",
        ]
    elif diff == "MEDIUM":
        prompt = "Design an image sharing service where users post images and follow others. Support feed generation and trending."
        rubric = [
            "API endpoints for post/follow/feed",
            "Write path vs read path tradeoffs",
            "Metadata and blob storage design",
            "Feed fan-out vs fan-in approach",
            "Caching and hot feed mitigation",
            "Consistency model and backfills",
            "Sharding and partition strategies",
        ]
    else:  # HARD
        prompt = "Design a globally distributed chat platform with end-to-end encryption, presence, and group messaging."
        rubric = [
            "Protocol and API design",
            "E2EE key management basics",
            "Message fanout and delivery semantics",
            "Ordering, idempotency, retries",
            "Presence and typing indicators at scale",
            "Multi-region replication and conflicts",
            "Storage choices and indexing",
            "Latency budgets and observability",
        ]
    return {"prompt": prompt, "rubric": rubric}


def score_sd_answer(rubric: List[str], text: str) -> Dict[str, Any]:
    """Heuristic rubric hit count. If OpenAI is available, delegate."""
    client = _maybe_client()
    if client:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Act as a system design interviewer. Rate 1..6 and give feedback."},
                    {"role": "user", "content": f"Rubric:\n- " + "\n- ".join(rubric) + f"\n\nCandidate:\n{text}"},
                ],
                temperature=0.2,
            )
            msg = resp.choices[0].message.content
            rating = 4
            for tok in ("6", "5", "4", "3", "2", "1"):
                if f" {tok}" in msg or msg.strip().startswith(tok):
                    rating = int(tok)
                    break
            return {"rating": rating, "feedback": _clean(msg)}
        except Exception:
            pass

    # Offline heuristic
    score = 1
    lower = (text or "").lower()
    hits = sum(1 for r in rubric if r and r.split()[0].lower() in lower)
    if hits >= 7:
        score = 6
    elif hits >= 5:
        score = 5
    elif hits >= 3:
        score = 4
    elif hits >= 2:
        score = 3
    elif hits >= 1:
        score = 2
    return {"rating": score,
            "feedback": "Consider covering API, storage, scaling, and consistency with clear tradeoffs."}


# ---------- Behavioral generation and scoring ----------
def generate_beh_prompt(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    """Return {prompt, tip} for STAR behavioral by difficulty."""
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a behavioral interviewer."},
                    {"role": "user", "content":
                        f"Give one STAR prompt at {diff} difficulty. "
                        "1 sentence prompt plus a brief coaching tip. Keep it concise."},
                ],
                temperature=0.7,
            )
            text = resp.choices[0].message.content
            parts = text.split("\n")
            prompt = ""
            tip = ""
            for line in parts:
                s = line.strip()
                if not s: continue
                if not prompt:
                    prompt = s
                else:
                    tip = tip or s
            return {"prompt": prompt, "tip": tip or "Use the STAR format: Situation, Task, Action, Result."}
        except Exception:
            pass

    # Built-in prompts
    if diff == "EASY":
        return {
            "prompt": "Tell me about a time you resolved a minor conflict with a teammate.",
            "tip": "Keep it small, focus on clear communication and a concrete outcome using STAR.",
        }
    if diff == "MEDIUM":
        return {
            "prompt": "Describe a time you had to deliver under a changing requirement and kept stakeholders aligned.",
            "tip": "Emphasize how you clarified scope, managed risk, and delivered results.",
        }
    return {
        "prompt": "Tell me about a time you led through ambiguity across multiple teams to deliver a high-impact result.",
        "tip": "Show leadership, alignment across stakeholders, and measurable outcomes.",
    }


def score_beh_answer(text: str) -> Dict[str, Any]:
    client = _maybe_client()
    if client:
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Coach scoring behavioral STAR answers 1..6."},
                    {"role": "user", "content": f"Rate 1..6 and give brief feedback for:\n{text}"},
                ],
                temperature=0.2,
            )
            msg = resp.choices[0].message.content
            rating = 4
            for tok in ("6", "5", "4", "3", "2", "1"):
                if f" {tok}" in msg or msg.strip().startswith(tok):
                    rating = int(tok)
                    break
            return {"rating": rating}
        except Exception:
            pass

    # Offline heuristic
    lower = (text or "").lower()
    score = 2
    for k in ("situation", "task", "action", "result"):
        if k in lower:
            score += 1
    score = max(1, min(score, 6))
    return {"rating": score}


# ---------- Chance/Community, money, and ownership helpers ----------
def generate_card() -> Dict[str, Any]:
    cards = [
        {"title": "Recruiter Referral", "text": "A friend forwards your resume to a hiring manager.",
         "effect": {"offers": 1, "cash": 50}},
        {"title": "Resume Revamp", "text": "You improve your resume. Interview hit rate goes up.",
         "effect": {"offers": 1}},
        {"title": "Mock Interview", "text": "Great feedback boosts your confidence.", "effect": {"cash": 40}},
        {"title": "Tough Panel", "text": "It was rough. Learn and move on.", "effect": {"cash": -30}},
        {"title": "Extra Practice", "text": "Daily leetcoding streak.", "effect": {"extra_roll": True}},
        {"title": "Rest Day", "text": "Take a breath.", "effect": {"turn_skip": True}},
    ]
    return random.choice(cards)


def buy_company(state: Dict[str, Any], name: str, price: int) -> bool:
    if state["cash"] >= price and not any(c["name"] == name for c in state["owned"]):
        state["cash"] -= price
        state["owned"].append({"name": name})
        return True
    return False


def lap_income(state: Dict[str, Any]) -> int:
    """Simple lap reward."""
    return 100
