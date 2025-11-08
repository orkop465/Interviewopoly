# prompts.py
# Prompt to generate a short LC-style question
LC_QUESTION_PROMPT = """You are an interviewer creating a very short coding interview task.
Constraints:
- Target difficulty: {difficulty} (one of: EASY, MEDIUM, HARD)
- The task must be solvable by describing the APPROACH in 3–6 sentences, not full code.
- Prefer array/string/hash-map/graph basics; avoid edge-case rabbit holes.
 
Return JSON with keys:
- "question": one-paragraph prompt
- "hints": 2 compact hints
- "expected_keywords": 5–10 keywords/phrases indicating a good approach
"""

# Prompt to score a candidate's LC approach
LC_SCORE_PROMPT = """You are a pragmatic interviewer. Given the question and the candidate's approach,
provide:
- pass_fail: "PASS" or "FAIL"
- rating: integer 1–5
- feedback: 2–4 sentences explaining strengths and the main missing piece.
 
Heuristics:
- If the approach mentions expected keywords or a clear correct complexity, lean PASS.
- Reward clarity, correct data structure choice, and complexity awareness.
- FAIL only if the approach is blatantly wrong or dangerously incomplete.
 
Respond with JSON: {{"pass_fail": "...", "rating": 1, "feedback": "..."}}"""

# System design mini prompt
SD_QUESTION_PROMPT = """You are a system design interviewer. Create a SMALL prompt that
can be answered in 5–8 bullet points, not a full design doc.
Include 2–4 functional requirements and 2 scaling constraints.
Topic: {topic} (examples: URL shortener, rate limiter, chat room, news feed).
 
Return JSON: {{"prompt":"...","rubric":["must mention ...","must consider ..."]}}
"""

# Score system design answer (bullets against rubric)
SD_SCORE_PROMPT = """You are evaluating a brief system design answer (5–8 bullets).
Use the rubric items (list) provided. Score 1–5 by coverage & realism.
Return JSON: {{"rating": 1, "feedback": "2–4 sentences with crisp improvement tips"}}"""

# Behavioral prompt
BEHAVIORAL_QUESTION_PROMPT = """Create one behavioral interview prompt about {theme} (e.g., conflict, leadership, failure).
Also include a quick STAR reminder.
 
Return JSON: {{"prompt":"...", "tip":"(Very short STAR reminder)"}}"""

# Score behavioral STAR answer
BEHAVIORAL_SCORE_PROMPT = """Rate a STAR answer on:
- Situation clarity
- Actions specificity
- Measurable Result
 
Return JSON: {{"rating": 1, "feedback": "2–3 sentences of actionable feedback"}}"""

# Chance/Community card generator
CARD_PROMPT = """Generate one lighthearted job-search event card.
Keep it 1–2 sentences. Return JSON:
{{"title":"...", "effect": {{"cash": +/-int, "offers": +/-int, "turn_skip": 0/1, "extra_roll": 0/1}}, "flavor":"..."}}
Tone: playful, not mean."""
