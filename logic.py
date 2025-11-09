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
    st = {
        **_client_status_detail(),
        "mode": "openai" if _maybe_client() else "local",
    }
    _debug(f"llm_status: {st}")
    return st


# ---------- Rewards ----------
LC_REWARDS: Dict[str, Dict[str, int]] = {
    "LC_EASY": {"pass_offers": 2},
    "LC_MED": {"pass_offers": 3},
    "LC_HARD": {"pass_offers": 4},
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
    from prompts import LC_QUESTION_PROMPT
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            _debug("Generating LC question via OpenAI (JSON)")
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert coding interviewer. Return strict JSON only."},
                    {"role": "user", "content": LC_QUESTION_PROMPT.format(difficulty=diff)},
                ],
                response_format={"type": "json_object"},
            )
            import json
            obj = json.loads(resp.choices[0].message.content or "{}")
            title = _clean(str(obj.get("title", "")))[:45]
            question = _clean(str(obj.get("question", "")))[:240]
            examples = obj.get("examples") or []
            hints = obj.get("hints") or []
            return {"title": title, "question": question, "examples": examples[:2], "hints": hints[:3]}
        except Exception as e:
            _debug(f"OpenAI LC generation failed: {type(e).__name__}: {e}")

    _debug("Generating LC question locally (compact)")
    bank = {
        "EASY": [
            {
                "title": "First Duplicate Index",
                "question": "Scan left to right. Return the index of the first duplicate value, or -1.",
                "examples": ["[2,1,3,2] -> 3", "[1,2,3] -> -1"],
                "hints": ["Track seen in a set", "Return when you first hit seen value"],
            },
            {
                "title": "Anagram of 'interview'?",
                "question": "Return true if s is an anagram of 'interview' ignoring case/spaces.",
                "examples": ["'Weir t i n v e r' -> true"],
                "hints": ["Lowercase + strip spaces", "Count letters and compare"],
            },
        ],
        "MEDIUM": [
            {
                "title": "Longest Substr ≤2 Distinct",
                "question": "Return length of the longest substring with at most two distinct chars.",
                "examples": ["'eceba' -> 3 ('ece')"],
                "hints": ["Sliding window", "Count per char; shrink when >2"],
            },
            {
                "title": "Subarrays Sum to K (count)",
                "question": "Return how many subarrays sum to K.",
                "examples": ["[1,-1,2] K=2 -> 2"],
                "hints": ["Prefix sums", "Map of prefix->freq"],
            },
        ],
        "HARD": [
            {
                "title": "LRU Cache",
                "question": "Design get/put in O(1) with capacity.",
                "examples": [],
                "hints": ["Hash map + doubly linked list", "Move node to head on access"],
            },
            {
                "title": "Course Schedule Order",
                "question": "Return a valid ordering or empty if impossible.",
                "examples": [],
                "hints": ["Toposort", "Kahn or DFS cycle check"],
            },
        ],
    }
    return random.choice(bank[_difficulty_norm(difficulty)])


# ---------- LC scoring ----------
def score_lc_answer(question: Dict[str, Any], text: str) -> Dict[str, Any]:
    client = _maybe_client()
    if client:
        try:
            _debug(f"LC scoring via OpenAI model={OPENAI_MODEL}")
            from prompts import LC_SCORE_PROMPT
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a fair technical interviewer. Return strict JSON only."},
                    {"role": "user",
                     "content": f"{LC_SCORE_PROMPT}\n\nQuestion:\n{question}\n\nCandidate answer:\n{text}"},
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
            _debug(f"OpenAI LC scoring failed, falling back: {type(e).__name__}: {e}")

    _debug("LC scoring locally")
    words = len((text or "").split())
    pseudo_score = sum(
        1 for c in ("set", "map", "hash", "window", "prefix", "queue", "stack") if c in (text or "").lower())
    correct = (words >= 20 and pseudo_score >= 1)
    fb = ("Evaluated locally. Outline clear steps and name the structures."
          if not correct else "Good. Clear steps and appropriate data structures.")
    return {"correct": bool(correct), "feedback": fb, "judge_source": "local"}


# ---------- SD generation ----------
def generate_sd_prompt(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    from prompts import SD_QUESTION_PROMPT
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            _debug("Generating SD prompt via OpenAI (JSON)")
            topic = random.choice([
                "URL shortener", "rate limiter", "chat room", "news feed",
                "image sharing", "metrics ingestion", "log aggregation"
            ])
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a seasoned systems architect. Return strict JSON only."},
                    {"role": "user", "content": SD_QUESTION_PROMPT.format(topic=topic, difficulty=diff)},
                ],
                response_format={"type": "json_object"},
            )
            import json
            obj = json.loads(resp.choices[0].message.content or "{}")
            title = _clean(str(obj.get("title", "")))[:45]
            prompt = _clean(str(obj.get("prompt", "")))[:240]
            rubric = [_clean(str(x))[:80] for x in (obj.get("rubric") or [])][:7]
            return {"title": title, "prompt": prompt, "rubric": rubric}
        except Exception as e:
            _debug(f"OpenAI SD generation failed: {type(e).__name__}: {e}")

    _debug("Generating SD prompt locally (compact)")
    if diff == "EASY":
        return {
            "title": "URL Shortener",
            "prompt": "Create and resolve short links. Support ~1M keys and 1k rps. Keep it simple.",
            "rubric": [
                "API endpoints",
                "Key gen & collisions",
                "Data model",
                "Caching hot keys",
                "Consistency on create",
                "Scaling strategy",
                "Tradeoffs",
            ],
        }
    if diff == "MEDIUM":
        return {
            "title": "Image Sharing Feed",
            "prompt": "Users post images and follow others. Build a feed and trending list.",
            "rubric": [
                "Post/follow/feed APIs",
                "Blob + metadata storage",
                "Fanout vs fanin",
                "Caching hot feeds",
                "Consistency/backfills",
                "Sharding strategy",
                "Bottlenecks/tradeoffs",
            ],
        }
    return {
        "title": "Global Chat (E2EE)",
        "prompt": "Groups, presence, and E2EE across regions. Low latency and reliable delivery.",
        "rubric": [
            "Protocol/API",
            "Key mgmt basics",
            "Fanout & retries",
            "Ordering/idempotency",
            "Multi-region replicas",
            "Indexes/storage",
            "Observability/tradeoffs",
        ],
    }


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
                    {"role": "system", "content": "Act as a system design interviewer. Return strict JSON only."},
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
    fb = "Cover API, storage, scaling, consistency, and one tradeoff." if not correct else "Solid coverage of key items."
    return {"correct": bool(correct), "feedback": fb, "judge_source": "local"}


# ---------- Behavioral generation ----------
def generate_beh_prompt(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    from prompts import BEHAVIORAL_QUESTION_PROMPT
    diff = _difficulty_norm(difficulty)
    client = _maybe_client()

    if client:
        try:
            _debug("Generating behavioral prompt via OpenAI (JSON)")
            theme = random.choice(["conflict", "leadership", "failure", "ambiguity", "ownership"])
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a behavioral interviewer. Return strict JSON only."},
                    {"role": "user", "content": BEHAVIORAL_QUESTION_PROMPT.format(theme=theme, difficulty=diff)},
                ],
                response_format={"type": "json_object"},
            )
            import json
            obj = json.loads(resp.choices[0].message.content or "{}")
            title = _clean(str(obj.get("title", "")))[:45]
            prompt = _clean(str(obj.get("prompt", "")))[:140]
            tip = _clean(str(obj.get("tip", "")))[:90]
            return {"title": title, "prompt": prompt, "tip": tip}
        except Exception as e:
            _debug(f"OpenAI behavioral generation failed: {type(e).__name__}: {e}")

    _debug("Generating behavioral prompt locally (compact)")
    if diff == "EASY":
        return {
            "title": "Small Conflict",
            "prompt": "Tell me about a time you resolved a minor teammate conflict.",
            "tip": "STAR: Situation, Task, Action, Result.",
        }
    if diff == "MEDIUM":
        return {
            "title": "Changing Requirements",
            "prompt": "Describe delivering under changing requirements while keeping stakeholders aligned.",
            "tip": "Clarify scope, act, quantify the result.",
        }
    return {
        "title": "Lead Through Ambiguity",
        "prompt": "Tell me about leading across teams to deliver a high-impact result amid ambiguity.",
        "tip": "Own the outcome; quantify impact.",
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
                    {"role": "system", "content": "Coach scoring behavioral STAR answers. Return strict JSON only."},
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


# ---------- Cards (no cash anywhere) ----------
def generate_card() -> Dict[str, Any]:
    cards = [
        {"title": "Recruiter Referral", "text": "A friend forwards your resume to a hiring manager.",
         "effect": {"offers": 1}},
        {"title": "Resume Revamp", "text": "You improve your resume. Interview hit rate goes up.",
         "effect": {"offers": 1}},
        {"title": "Mock Interview", "text": "Great feedback boosts your confidence.", "effect": {"offers": 1}},
        {"title": "Tough Panel", "text": "It was rough. Learn and move on.", "effect": {}},
        {"title": "Extra Practice", "text": "Daily leetcoding streak.", "effect": {"extra_roll": True}},
        {"title": "Rest Day", "text": "Take a breath.", "effect": {"turn_skip": True}},
    ]
    return random.choice(cards)
