from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import analytics
import database
from ai_interpreter import interpret

app = FastAPI(title="AI Business Intelligence Assistant")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): database.initialize_database()

class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)

@app.get("/api/health")
def health():
    try:
        result = analytics.summary()
        return {"status": "ok", "records": result["records"]}
    except Exception as exc: raise HTTPException(503, f"Data is not ready: {exc}")

@app.get("/api/summary")
def get_summary():
    try: return analytics.summary()
    except Exception as exc: raise HTTPException(503, f"Could not load analytics: {exc}")

@app.post("/api/question")
def ask(body: Question):
    question = body.question.strip()
    if not question: raise HTTPException(422, "Question cannot be empty.")
    parsed, source = interpret(question)
    if not parsed: raise HTTPException(422, "I could not match that question to a supported sales analysis.")
    intent = parsed["intent"]
    data = analytics.summary()
    if intent == "total_revenue": answer = {"text": f"Total net revenue is {data['total_revenue']:,.2f}.", "figures": {"total_revenue": data["total_revenue"]}}
    elif intent == "top_product":
        value = data["top_product"]
        answer = {"text": f"{value['product']} has the highest net revenue at {value['revenue']:,.2f}.", "figures": value}
    elif intent == "top_region":
        value = data["top_region"]
        answer = {"text": f"{value['region']} has the highest net revenue at {value['revenue']:,.2f}.", "figures": value}
    elif intent == "monthly_trend": answer = {"text": "Here is the monthly net revenue trend.", "figures": {"monthly_trend": data["monthly_trend"]}}
    else:
        try: value = analytics.revenue_change(parsed["start_month"], parsed["end_month"])
        except (KeyError, ValueError) as exc: raise HTTPException(422, str(exc))
        answer = {"text": f"Revenue changed by {value['absolute_change']:,.2f} from {value['start_month']} to {value['end_month']}.", "figures": value}
    return {"intent": intent, "source": source, "answer": answer["text"], "figures": answer["figures"]}
