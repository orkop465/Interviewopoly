# logic.py
import os
import random
from typing import Dict, Any, List

# Load .env automatically for every teammate without IDE config
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
    _DOTENV_LOADED = True
except Exception:
    _DOTENV_LOADED = False

# Optional OpenAI generation
try:
    from openai import OpenAI
    _HAS_OPENAI_LIB = True
except Exception:
    _HAS_OPENAI_LIB = False

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# Default behavior:
# - If USE_LLM is explicitly set, honor it.
# - Else if an API key is present, use LLM by default.
# - Else fallback to local.
def _parse_bool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "yes", "y", "on")


if os.getenv("USE_LLM") is not None:
    USE_LLM = _parse_bool(os.getenv("USE_LLM"))
else:
    USE_LLM = bool(OPENAI_API_KEY)

_LAST_LLM_ERROR: str = ""


def _debug(msg: str):
    print(f"[logic] {msg}")


def _client_status_detail() -> Dict[str, Any]:
    return {
        "dotenv_loaded": _DOTENV_LOADED,
        "has_openai_lib": _HAS_OPENAI_LIB,
        "api_key_present": bool(OPENAI_API_KEY),
        "use_llm_flag": USE_LLM,
        "model": OPENAI_MODEL,
        "last_llm_error": _LAST_LLM_ERROR,
    }


def _maybe_client():
    global _LAST_LLM_ERROR
    _LAST_LLM_ERROR = ""
    if not USE_LLM:
        _LAST_LLM_ERROR = "USE_LLM is false"
        _debug("LLM disabled by USE_LLM flag, using local judging")
        return None
    if not _HAS_OPENAI_LIB:
        _LAST_LLM_ERROR = "openai library not importable in this interpreter"
        _debug("OpenAI library not found, using local judging")
        return None
    if not OPENAI_API_KEY:
        _LAST_LLM_ERROR = "OPENAI_API_KEY not present in process environment"
        _debug("No OPENAI_API_KEY, using local judging")
        return None
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        _debug(f"OpenAI client created, model={OPENAI_MODEL}")
        return client
    except Exception as e:
        _LAST_LLM_ERROR = f"client init error: {type(e).__name__}: {e}"
        _debug(f"Failed to create OpenAI client, using local judging. Reason: {_LAST_LLM_ERROR}")
        return None


def llm_status() -> Dict[str, Any]:
    """Expose runtime status to the server and UI, and print once for visibility."""
    st = {
        **_client_status_detail(),
        "mode": "openai" if _maybe_client() else "local",
    }
    _debug(f"llm_status: {st}")
    return st


# ---------- Rewards ----------
LC_REWARDS: Dict[str, Dict[str, int]] = {
    "LC_EASY": {"pass_cash": 80, "pass_offers": 2, "fail_cash": 0},
    "LC_MED": {"pass_cash": 120, "pass_offers": 3, "fail_cash": 0},
    "LC_HARD": {"pass_cash": 180, "pass_offers": 4, "fail_cash": 0},
}


# ---------- Utility helpers ----------
def _clean(s: str) -> str:
    return (s or "").strip().replace("\r", "")


def _difficulty_norm(d: str) -> str:
    d = (d or "MEDIUM").upper()
    if d in ("EASY", "MEDIUM", "HARD"):
        return d
    return "MEDIUM"


def _safe_bool_correct(obj: Dict[str, Any], default: bool = False) -> bool:
    if isinstance(obj, dict):
        if "correct" in obj:
            try:
                return bool(obj["correct"])
            except Exception:
                pass
        pf = str(obj.get("pass_fail", "")).upper()
        if pf in ("PASS", "CORRECT", "TRUE"):
            return True
        if pf in ("FAIL", "INCORRECT", "FALSE"):
            return False
    return default


# ---------- LC generation ----------
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
            _debug("Generating LC question via OpenAI")
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert coding interviewer."},
                    {"role": "user", "content": prompt},
                ],
            )
            text = resp.choices[0].message.content or ""
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
        except Exception as e:
            _debug(f"OpenAI LC generation failed: {type(e).__name__}: {e}")

    _debug("Generating LC question locally")
    bank = {
        "EASY": [
            (
                "Given an array of integers, return the index of the first duplicate value you encounter while scanning left to right. If none, return -1.",
                ["Use a set to record seen values", "Return early when you find a duplicate"],
            ),
            (
                "Given a string s, return true if it is an anagram of 'interview', ignoring case and spaces.",
                ["Normalize to lowercase", "Remove spaces before counting letters"],
            ),
        ],
        "MEDIUM": [
            (
                "Design a function that returns the length of the longest substring with at most two distinct characters.",
                ["Sliding window", "Track counts of characters in the window"],
            ),
            (
                "Given an array and integer k, return the number of subarrays whose sum equals k.",
                ["Prefix sums", "Hash map of prefix frequencies"],
            ),
        ],
        "HARD": [
            (
                "Implement LRU cache with O(1) get and put given capacity.",
                ["Doubly linked list plus hash map", "Move to front on access"],
            ),
            (
                "Given n tasks with prerequisites, return a valid ordering or empty list if impossible.",
                ["Topological sort", "Kahn’s algorithm or DFS cycle check"],
            ),
        ],
    }
    q, hints = random.choice(bank[diff])
    return {"question": q, "hints": hints}


# ---------- LC scoring ----------
def _pseudo_tokens_present(text: str) -> int:
    lower = (text or "").lower()
    cues = [
        "for ", "while ", "if ", "else", "return", "initialize", "set ", "append", "pop", "push",
        "[i]", "i+1", "j+1", "map[", "dict", "hash", "set", "queue", "stack", "two pointer", "sliding window",
        "prefix", "visited", "adjacency", "heap", "priority queue"
    ]
    return sum(1 for c in cues if c in lower)


def _hint_hits(question: Dict[str, Any], text: str) -> int:
    lower = (text or "").lower()
    hints = question.get("hints") or []
    hits = 0
    for h in hints:
        for tok in str(h).lower().replace(",", " ").split():
            if len(tok) >= 3 and tok in lower:
                hits += 1
                break
    return hits


def score_lc_answer(question: Dict[str, Any], text: str) -> Dict[str, Any]:
    client = _maybe_client()
    if client:
        try:
            _debug(f"LC scoring via OpenAI model={OPENAI_MODEL}")
            from prompts import LC_SCORE_PROMPT
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a fair technical interviewer. Be strict but unbiased."},
                    {"role": "user",
                     "content": f"{LC_SCORE_PROMPT}\n\nQuestion:\n{question}\n\nCandidate answer:\n{text}"},
                ],
                response_format={"type": "json_object"},
            )
            import json
            raw = resp.choices[0].message.content or "{}"
            obj = json.loads(raw)
            return {
                "correct": _safe_bool_correct(obj),
                "feedback": _clean(obj.get("feedback", "")),
                "judge_source": "openai",
            }
        except Exception as e:
            _debug(f"OpenAI LC scoring failed, falling back: {type(e).__name__}: {e}")

    _debug("LC scoring locally")
    words = len((text or "").split())
    pseudo_score = _pseudo_tokens_present(text)
    hint_score = _hint_hits(question, text)
    correct = (words >= 20 and (pseudo_score >= 2 or hint_score >= 1))
    fb = (
        "Evaluated locally. Pseudocode is enough. Outline the steps clearly and name the key data structures you use."
        if not correct else
        "Good. Clear steps and appropriate data structures."
    )
    return {"correct": bool(correct), "feedback": fb, "judge_source": "local"}


# ---------- SD generation ----------
def generate_sd_prompt(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            _debug("Generating SD prompt via OpenAI")
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a seasoned systems architect."},
                    {
                        "role": "user",
                        "content": f"Create a system design prompt at {diff} difficulty. "
                                   "Keep it ~3 sentences. Include an explicit bullet rubric of 6–8 items "
                                   "covering API, storage model, consistency, scalability, bottlenecks, and tradeoffs.",
                    },
                ],
            )
            text = resp.choices[0].message.content or ""
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
        except Exception as e:
            _debug(f"OpenAI SD generation failed: {type(e).__name__}: {e}")

    _debug("Generating SD prompt locally")
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
    else:
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


# ---------- SD scoring ----------
def score_sd_answer(rubric: List[str], text: str) -> Dict[str, Any]:
    client = _maybe_client()
    if client:
        try:
            _debug(f"SD scoring via OpenAI model={OPENAI_MODEL}")
            from prompts import SD_SCORE_PROMPT
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Act as a system design interviewer. Be strict but fair."},
                    {"role": "user",
                     "content": f"{SD_SCORE_PROMPT}\n\nRubric:\n- " + "\n- ".join(rubric) + f"\n\nCandidate:\n{text}"},
                ],
                response_format={"type": "json_object"},
            )
            import json
            obj = json.loads(resp.choices[0].message.content or "{}")
            return {
                "correct": _safe_bool_correct(obj),
                "feedback": _clean(obj.get("feedback", "")),
                "judge_source": "openai",
            }
        except Exception as e:
            _debug(f"OpenAI SD scoring failed, falling back: {type(e).__name__}: {e}")

    _debug("SD scoring locally")
    lower = (text or "").lower()
    hits = sum(1 for r in rubric if r and r.split()[0].lower() in lower)
    needed = max(1, len(rubric) // 3)
    correct = hits >= needed
    fb = "Touch API shape, storage, scaling, and one consistency choice with brief bullets." if not correct else "Solid coverage of key rubric items."
    return {"correct": bool(correct), "feedback": fb, "judge_source": "local"}


# ---------- Behavioral generation ----------
def generate_beh_prompt(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            _debug("Generating behavioral prompt via OpenAI")
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a behavioral interviewer."},
                    {
                        "role": "user",
                        "content": f"Give one STAR prompt at {diff} difficulty. "
                                   "1 sentence prompt plus a brief coaching tip. Keep it concise.",
                    },
                ],
            )
            text = resp.choices[0].message.content or ""
            parts = text.split("\n")
            prompt = ""
            tip = ""
            for line in parts:
                s = line.strip()
                if not s:
                    continue
                if not prompt:
                    prompt = s
                else:
                    tip = tip or s
            return {"prompt": prompt, "tip": tip or "Use the STAR format: Situation, Task, Action, Result."}
        except Exception as e:
            _debug(f"OpenAI behavioral generation failed: {type(e).__name__}: {e}")

    _debug("Generating behavioral prompt locally")
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


# ---------- Behavioral scoring ----------
def score_beh_answer(text: str) -> Dict[str, Any]:
    client = _maybe_client()
    if client:
        try:
            _debug(f"Behavioral scoring via OpenAI model={OPENAI_MODEL}")
            from prompts import BEHAVIORAL_SCORE_PROMPT
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Coach scoring behavioral STAR answers. Be strict but fair."},
                    {"role": "user", "content": f"{BEHAVIORAL_SCORE_PROMPT}\n\nAnswer:\n{text}"},
                ],
                response_format={"type": "json_object"},
            )
            import json
            obj = json.loads(resp.choices[0].message.content or "{}")
            return {
                "correct": _safe_bool_correct(obj),
                "feedback": _clean(obj.get("feedback", "")),
                "judge_source": "openai",
            }
        except Exception as e:
            _debug(f"OpenAI behavioral scoring failed, falling back: {type(e).__name__}: {e}")

    _debug("Behavioral scoring locally")
    lower = (text or "").lower()
    present = sum(1 for k in ("situation", "task", "action", "result") if k in lower)
    correct = present >= 3
    fb = "Use STAR with specific actions and a measurable result." if not correct else "Clear STAR structure with a concrete outcome."
    return {"correct": bool(correct), "feedback": fb, "judge_source": "local"}


# ---------- Cards and money ----------
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
    return 100
