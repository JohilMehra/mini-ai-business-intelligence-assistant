import pytest
from fastapi.testclient import TestClient
import database, analytics, main, ai_interpreter

@pytest.fixture
def db(tmp_path, monkeypatch):
    csv = tmp_path / "sales.csv"
    csv.write_text("Transaction_Id,Order_date,Product,Category,Region,Sales_channel,Quantity,Unit_price,Discount_amount,Status\nA,01-01-2026,One,C,N,O,2,10,1,Completed\nB,02-01-2026,Two,C,S,O,1,,0,Completed\nC,03-01-2026,Two,C,S,O,9,100,0,Returned\nD,01-02-2026,Zero,C,N,O,0,5,0,Completed\n", encoding="utf-8")
    path = tmp_path / "test.db"
    database.initialize_database(path, csv)
    return path, csv

def test_import_and_repeat_safe(db):
    path, csv = db
    first = database.initialize_database(path, csv)
    second = database.initialize_database(path, csv)
    assert first["imported"] == 4 and first["eligible"] == 2 and first["excluded"] == 2
    assert second["already_imported"]

def test_revenue_exclusions_and_zero(db):
    result = analytics.summary(db[0])
    assert result["total_revenue"] == 19
    assert result["records"] == {"imported": 4, "eligible": 2, "excluded": 2}

def test_top_product_region_and_months(db):
    result = analytics.summary(db[0])
    assert result["top_product"]["product"] == "One"
    assert result["top_region"]["region"] == "N"
    assert [m["month"] for m in result["monthly_trend"]] == ["2026-01", "2026-02"]

def test_month_change(db):
    assert analytics.revenue_change("2026-01", "2026-02", db[0])["absolute_change"] == -19

def test_invalid_month(db):
    with pytest.raises(ValueError): analytics.revenue_change("2026-13", "2026-01")

def test_fallback_supported_and_unsupported(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert ai_interpreter.interpret("show total revenue")[0]["intent"] == "total_revenue"
    assert ai_interpreter.interpret("tell me a joke")[0] is None

def test_api_health_and_invalid_question(db, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(db[0]))
    monkeypatch.setattr(database, "CSV_PATH", db[1])
    client = TestClient(main.app)
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/question", json={"question": "   "}).status_code == 422

def test_question_endpoint(db, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(db[0]))
    monkeypatch.setattr(database, "CSV_PATH", db[1])
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = TestClient(main.app)
    response = client.post("/api/question", json={"question": "total revenue"})
    assert response.status_code == 200 and response.json()["figures"]["total_revenue"] == 19
