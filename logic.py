# logic.py
import random
from typing import Dict, Any

from llm import chat_json
from prompts import (
    LC_QUESTION_PROMPT, LC_SCORE_PROMPT,
    SD_QUESTION_PROMPT, SD_SCORE_PROMPT,
    BEHAVIORAL_QUESTION_PROMPT, BEHAVIORAL_SCORE_PROMPT,
    CARD_PROMPT
)

# --- Scoring tables ---
LC_REWARDS = {
    "LC_EASY": {"pass_cash": 50, "pass_offers": 1, "fail_cash": -25},
    "LC_MED": {"pass_cash": 100, "pass_offers": 2, "fail_cash": -50},
    "LC_HARD": {"pass_cash": 150, "pass_offers": 3, "fail_cash": -75},
}


def start_income_for_company(price: int) -> int:
    # each lap over Start yields this income per owned company
    return max(20, price // 5)


# --- LC helpers ---
def generate_lc_question(difficulty: str) -> Dict[str, Any]:
    fallback = {
        "question": f"(STUB) {difficulty} — Find the first non-repeating character in a string.",
        "hints": ["Use a frequency map", "Then scan string again"],
        "expected_keywords": ["hash", "dictionary", "count", "O(n)", "two pass"]
    }
    sys = "You are an expert coding interviewer."
    user = LC_QUESTION_PROMPT.format(difficulty=difficulty)
    return chat_json(sys, user, fallback)


def score_lc_answer(question: Dict[str, Any], approach: str) -> Dict[str, Any]:
    fallback = {"pass_fail": "PASS", "rating": 4, "feedback": "(STUB) Clear approach and correct complexity."}
    sys = "You are a fair coding interviewer."
    user = f"""Question: {question}
Candidate approach: {approach}
{LC_SCORE_PROMPT}"""
    return chat_json(sys, user, fallback)


# --- System design helpers ---
def generate_sd_prompt() -> Dict[str, Any]:
    topic = random.choice(["URL shortener", "Rate limiter", "Chat room", "News feed", "File storage"])
    fallback = {
        "prompt": f"(STUB) Design a {topic} with 2–4 bullets of requirements and scaling constraints.",
        "rubric": ["mention data model", "mention scalability", "mention bottlenecks"]
    }
    sys = "You are an experienced system design interviewer."
    user = SD_QUESTION_PROMPT.format(topic=topic)
    return chat_json(sys, user, fallback)


def score_sd_answer(rubric: Any, bullets: str) -> Dict[str, Any]:
    fallback = {"rating": 4, "feedback": "(STUB) Solid coverage of requirements and scalability."}
    sys = "You are scoring a brief system design outline."
    user = f"Rubric: {rubric}\nAnswer bullets:\n{bullets}\n{SD_SCORE_PROMPT}"
    return chat_json(sys, user, fallback)


# --- Behavioral helpers ---
def generate_beh_prompt() -> Dict[str, Any]:
    theme = random.choice(["conflict", "leadership", "failure", "ownership", "ambiguity"])
    fallback = {"prompt": f"(STUB) Tell me about a time you handled {theme}.", "tip": "Use STAR briefly."}
    sys = "You are a behavioral interviewer."
    user = BEHAVIORAL_QUESTION_PROMPT.format(theme=theme)
    return chat_json(sys, user, fallback)


def score_beh_answer(answer: str) -> Dict[str, Any]:
    fallback = {"rating": 4, "feedback": "(STUB) Clear STAR with measurable outcome."}
    sys = "You are scoring a STAR behavioral answer."
    user = f"Candidate answer:\n{answer}\n{BEHAVIORAL_SCORE_PROMPT}"
    return chat_json(sys, user, fallback)


# --- Chance/Community ---
def generate_card() -> Dict[str, Any]:
    fallback = {"title": "(STUB) Surprise referral!",
                "effect": {"cash": 100, "offers": 1, "turn_skip": 0, "extra_roll": 0},
                "flavor": "A friend vouches for you on LinkedIn."}
    sys = "You are a funny but kind game master."
    user = CARD_PROMPT
    return chat_json(sys, user, fallback)


# --- Utility ---
def apply_effect(state: Dict[str, Any], cash_delta: int = 0, offers_delta: int = 0):
    state["cash"] += cash_delta
    state["offers"] += offers_delta


def buy_company(state: Dict[str, Any], name: str, price: int):
    if state["cash"] >= price:
        state["cash"] -= price
        state["owned"].append({"name": name, "price": price})
        state["log"].append(f"Bought {name} for ${price}.")
        return True
    else:
        state["log"].append(f"Not enough cash to buy {name}.")
        return False


def lap_income(state: Dict[str, Any]) -> int:
    # total income gained when passing Start
    total = 0
    for c in state["owned"]:
        total += start_income_for_company(c["price"])
    return total
