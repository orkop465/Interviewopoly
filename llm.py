# llm.py (updated)
import json, os, re
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
USE_STUB = os.getenv("USE_LLM_STUB", "false").lower() == "true"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

def _safe_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return fallback

def _report_err(msg: str):
    try:
        import streamlit as st
        st.session_state["llm_error"] = msg
    except Exception:
        pass
    print(f"[LLM ERROR] {msg}")

def chat_json(system_prompt: str, user_prompt: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if USE_STUB:
        return fallback

    try:
        from openai import OpenAI
        client = OpenAI()
    except Exception as e:
        _report_err(f"Failed to init OpenAI client: {type(e).__name__}: {e}")
        return fallback

    model = OPENAI_MODEL

    # GPT-5 path: Responses API minimal call
    if model.startswith("gpt-5"):
        try:
            strict_user = user_prompt.strip() + "\n\nReturn ONLY a valid JSON object."
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user", "content": strict_user},
                ],
                # DO NOT pass temperature, response_format, etc.
            )
            content = getattr(resp, "output_text", "") or ""
            if not content:
                try:
                    parts = []
                    for item in getattr(resp, "output", []):
                        for c in getattr(item, "content", []):
                            if getattr(c, "type", "") == "output_text":
                                parts.append(getattr(c, "text", ""))
                    content = "".join(parts)
                except Exception:
                    content = ""
            if not content:
                raise RuntimeError("Empty response content from Responses API (gpt-5 path)")
            return _safe_json(content, fallback)
        except Exception as e:
            _report_err(f"Responses API (gpt-5) failed: {type(e).__name__}: {e}")
            return fallback

    # Non-5 path: Chat Completions
    try:
        from openai import OpenAI
        # we already have client, reuse
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            # You can include temperature or response_format if your SDK supports
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        content = resp.choices[0].message.content
        return _safe_json(content, fallback)
    except TypeError:
        # retry without those params
        try:
            strict_user = user_prompt.strip() + "\n\nReturn ONLY a valid JSON object."
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user", "content": strict_user},
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            return _safe_json(content, fallback)
        except Exception as e:
            _report_err(f"Chat Completions (no params) failed: {type(e).__name__}: {e}")
            return fallback
    except Exception as e:
        _report_err(f"Chat Completions failed (general): {type(e).__name__}: {e}")
        return fallback
