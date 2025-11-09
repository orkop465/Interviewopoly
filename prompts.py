# prompts.py
# All prompts return compact JSON with strict fields to keep UI consistent.

# LeetCode-style question (short, structured)
LC_QUESTION_PROMPT = """
You are an interviewer creating a SHORT coding interview task.

Return STRICT JSON with keys:
- "title": short name (max 45 chars)
- "question": 1–2 sentences, plain text only (max 240 chars)
- "examples": array of 0–2 concise examples as single-line strings, each max 120 chars
- "hints": array of 2–3 compact hints, each max 90 chars

Constraints:
- Difficulty: {difficulty} (EASY, MEDIUM, HARD)
- Language-agnostic, no code, no markdown.
- Prefer basic arrays/strings/hash maps/graphs.
- Keep it readable and scannable.
"""

# Score a candidate's LC approach (binary)
LC_SCORE_PROMPT = """
You are a pragmatic interviewer. Decide ONLY if the approach is correct.

Given the question and the candidate's answer, return STRICT JSON:
{"correct": true|false, "feedback": "1–2 concise sentences (max 160 chars)"}

Guidelines:
- Correct if the approach names the right data structures/technique and gives steps that would work.
- Incorrect if the approach is wrong, incomplete, or ignores constraints.
- Be neutral and brief. Do not mention ratings or scores.
"""

# System design mini prompt (tight, structured)
SD_QUESTION_PROMPT = """
You are a system design interviewer. Produce a SMALL, SCANNABLE prompt.

Return STRICT JSON:
{
  "title": "short name (max 45 chars)",
  "prompt": "2 sentences, plain text only (max 240 chars)",
  "rubric": [
    "6–7 bullet items, each <= 80 chars, covering API, storage, consistency, scaling, caching, bottlenecks, tradeoffs"
  ]
}

Topic: {topic}
Difficulty: {difficulty} (EASY, MEDIUM, HARD)
No code, no markdown. Keep it compact.
"""

# Score system design answer (binary)
SD_SCORE_PROMPT = """
Evaluate a brief system design answer against the rubric.

Return STRICT JSON:
{"correct": true|false, "feedback": "1–2 crisp sentences (max 160 chars)"}

Guidelines:
- correct=true if most rubric items are covered with realistic choices.
- correct=false if key items are missing or choices are not viable.
- Be succinct and neutral.
"""

# Behavioral prompt (short, structured)
BEHAVIORAL_QUESTION_PROMPT = """
Create ONE behavioral prompt and a tiny STAR tip.

Return STRICT JSON:
{
  "title": "short theme (max 45 chars)",
  "prompt": "1 sentence (max 140 chars)",
  "tip": "very short STAR reminder (max 90 chars)"
}

Theme: {theme}
Difficulty: {difficulty} (EASY, MEDIUM, HARD)
Keep it compact and readable.
"""

# Score behavioral STAR answer (binary)
BEHAVIORAL_SCORE_PROMPT = """
Judge a STAR answer.

Return STRICT JSON:
{"correct": true|false, "feedback": "1–2 sentences (max 140 chars)"}

Guidelines:
- correct=true if Situation, Task, Actions, and Result are all present and specific.
- correct=false if any are missing/vague.
Be brief and neutral.
"""

# Chance/Community card generator (unchanged)
CARD_PROMPT = """
Generate one lighthearted job-search event card.
Keep it 1–2 sentences. Return JSON:
{"title":"...", "effect": {"cash": +/-int, "offers": +/-int, "turn_skip": 0/1, "extra_roll": 0/1}, "flavor":"..."}
Tone: playful, not mean.
"""
