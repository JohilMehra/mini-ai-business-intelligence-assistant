"""Deterministic analytics over eligible SQLite transactions."""
from database import connect


def summary(db_path=None):
    with connect(db_path) as conn:
        total = conn.execute("SELECT COALESCE(SUM(net_revenue),0) FROM sales WHERE eligible=1").fetchone()[0]
        product = conn.execute("SELECT product, SUM(net_revenue) revenue FROM sales WHERE eligible=1 GROUP BY product ORDER BY revenue DESC, product LIMIT 1").fetchone()
        region = conn.execute("SELECT region, SUM(net_revenue) revenue FROM sales WHERE eligible=1 GROUP BY region ORDER BY revenue DESC, region LIMIT 1").fetchone()
        months = [dict(r) for r in conn.execute("SELECT substr(order_date,1,7) month, ROUND(SUM(net_revenue),2) revenue FROM sales WHERE eligible=1 GROUP BY month ORDER BY month")]
        counts = conn.execute("SELECT COUNT(*) imported, SUM(eligible) eligible FROM sales").fetchone()
        duplicate_count = conn.execute("SELECT COUNT(*) FROM import_exclusions").fetchone()[0]
    return {"total_revenue": round(total, 2), "top_product": dict(product) if product else None,
            "top_region": dict(region) if region else None, "monthly_trend": months,
            "records": {"imported": counts["imported"] + duplicate_count, "eligible": counts["eligible"] or 0,
                        "excluded": counts["imported"] + duplicate_count - (counts["eligible"] or 0)}}


def revenue_change(start_month: str, end_month: str, db_path=None):
    for month in (start_month, end_month):
        if len(month) != 7 or month[4] != "-" or not month[:4].isdigit() or not month[5:].isdigit() or not 1 <= int(month[5:]) <= 12:
            raise ValueError("Months must use YYYY-MM format with a valid month.")
    with connect(db_path) as conn:
        values = {}
        for month in (start_month, end_month):
            row = conn.execute("SELECT COALESCE(SUM(net_revenue),0) FROM sales WHERE eligible=1 AND substr(order_date,1,7)=?", (month,)).fetchone()
            values[month] = round(row[0], 2)
    change = round(values[end_month] - values[start_month], 2)
    percent = round(change / values[start_month] * 100, 2) if values[start_month] else None
    return {"start_month": start_month, "start_revenue": values[start_month], "end_month": end_month,
            "end_revenue": values[end_month], "absolute_change": change, "percentage_change": percent}
