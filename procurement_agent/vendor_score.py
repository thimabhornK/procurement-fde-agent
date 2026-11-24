"""Vendor risk score from ERP history, computed in code.

The same history always gives the same score, and every point can be traced
to a reason. The model only reads the result.
"""

from __future__ import annotations


def score_vendor(history: dict | None) -> dict:
    """Risk score from 1 (low) to 10 (high), with the reasons behind it."""
    if history is None:
        return {"score": None, "level": "unknown", "reasons": ["ไม่มีประวัติผู้ขายในระบบ"]}

    score, reasons = 1, []
    orders = history.get("orders_last_year", 0)
    late = history.get("late_deliveries_last_year", 0)
    late_rate = late / orders if orders else 0.0
    if late_rate >= 0.4:
        score += 4
        reasons.append(f"ส่งล่าช้า {late} จาก {orders} ครั้งในปีที่แล้ว ({late_rate:.0%})")
    elif late_rate >= 0.1:
        score += 2
        reasons.append(f"ส่งล่าช้า {late} จาก {orders} ครั้งในปีที่แล้ว ({late_rate:.0%})")

    claims = history.get("quality_claims_last_year", 0)
    if claims >= 2:
        score += 2
        reasons.append(f"มีเคลมคุณภาพ {claims} ครั้งในปีที่แล้ว")
    elif claims == 1:
        score += 1
        reasons.append("มีเคลมคุณภาพ 1 ครั้งในปีที่แล้ว")

    years = history.get("years_as_vendor", 0)
    if years < 2:
        score += 2
        reasons.append(f"เป็นผู้ขายมาเพียง {years} ปี")

    if history.get("status") != "active":
        score += 3
        reasons.append(f"สถานะผู้ขายในระบบ: {history.get('status')}")

    score = min(score, 10)
    if not reasons:
        reasons.append("ส่งตรงเวลาและไม่มีเคลมคุณภาพในปีที่แล้ว")
    level = "high" if score >= 7 else "medium" if score >= 4 else "low"
    return {"score": score, "level": level, "reasons": reasons}
