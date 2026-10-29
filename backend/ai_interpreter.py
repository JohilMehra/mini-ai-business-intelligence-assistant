"""Interpret supported business questions; model never calculates values."""
import json
import logging
import os
import re
from dotenv import load_dotenv

load_dotenv()
ALLOWED = {"total_revenue", "top_product", "monthly_trend", "top_region", "revenue_change"}
logger = logging.getLogger(__name__)


def _safe_error_message(exc: Exception, api_key: str) -> str:
    message = str(exc)
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = re.sub(
        r"(?i)(authorization|x-goog-api-key|api[_-]?key)(['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+",
        r"\1\2[REDACTED]",
        message,
    )
    message = re.sub(r"(?i)(bearer\s+)[^\s,;'\"}]+", r"\1[REDACTED]", message)
    return message[:500]


def fallback(question: str) -> dict | None:
    q = question.lower()
    if any(x in q for x in ("total revenue", "net revenue", "revenue overall", "how much revenue")): return {"intent": "total_revenue"}
    if "product" in q and any(x in q for x in ("highest", "top", "best")): return {"intent": "top_product"}
    if "region" in q and any(x in q for x in ("highest", "top", "best")): return {"intent": "top_region"}
    if any(x in q for x in ("monthly trend", "revenue by month", "each month", "monthly revenue")): return {"intent": "monthly_trend"}
    found = re.findall(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])\b", q)
    if len(found) == 2 and any(x in q for x in ("change", "compare", "between", "increase", "decrease")):
        return {"intent": "revenue_change", "start_month": f"{found[0][0]}-{int(found[0][1]):02d}", "end_month": f"{found[1][0]}-{int(found[1][1]):02d}"}
    return None


def interpret(question: str) -> tuple[dict | None, str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        parsed = fallback(question)
        return parsed, "fallback" if parsed else "unsupported"
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
          contents=f"Classify question into exactly one of {sorted(ALLOWED)} or unsupported. Return JSON only: {{intent, start_month, end_month}}. Month format YYYY-MM. Do not answer or calculate. Question: {question}",
          config=types.GenerateContentConfig(response_mime_type="application/json"))
        data = json.loads(response.text or "{}")
        intent = data.get("intent")
        if intent not in ALLOWED: raise ValueError("Unsupported intent")
        if intent == "revenue_change":
            for key in ("start_month", "end_month"):
                month = data.get(key, "")
                if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", month): raise ValueError("Invalid month")
        return data, "gemini"
    except Exception as exc:
        logger.warning("Gemini request failed (%s): %s", type(exc).__name__, _safe_error_message(exc, api_key))
        parsed = fallback(question)
        return parsed, "fallback" if parsed else "unsupported"
