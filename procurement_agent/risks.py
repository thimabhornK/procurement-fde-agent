"""Contract risk types, the output schema, grounding, and a keyword baseline.

The model must pick from a fixed list of risk types and quote the clause it
relied on. That makes the answer checkable: the type can be compared with a
labelled contract, and the quote can be looked up in the contract text.
"""

from __future__ import annotations

import re

# Risk types from the buyer's side, with the definition given to the model.
RISK_TYPES = {
    "full_prepayment": "ผู้ซื้อต้องจ่ายเงินทั้งหมด (100%) ก่อนได้รับสินค้าหรือบริการ "
                       "(การวางมัดจำบางส่วนไม่นับ)",
    "auto_renewal": "สัญญาต่ออายุเองอัตโนมัติ ถ้าผู้ซื้อไม่แจ้งยกเลิกล่วงหน้า",
    "unilateral_price_change": "ผู้ขายปรับราคาได้เองฝ่ายเดียว โดยผู้ซื้อไม่ต้องตกลงด้วย",
    "weak_late_penalty": "สัญญาซื้อสินค้าที่ไม่มีค่าปรับส่งมอบล่าช้า หรือเพดานค่าปรับรวม"
                         "ต่ำกว่า 5% ของมูลค่า (ไม่ใช้กับสัญญาบริการ)",
    "short_warranty": "ระยะเวลารับประกันสินค้าหรืองานสั้นกว่า 12 เดือน "
                      "(ช่วงเวลาแจ้งเคลมตอนรับของไม่นับเป็นการรับประกัน)",
    "liability_cap_low": "จำกัดความรับผิดของผู้ขายไว้ต่ำมากเมื่อเทียบกับความเสียหายที่อาจเกิด",
    "buyer_exit_penalty": "ผู้ซื้อบอกเลิกสัญญาไม่ได้ หรือบอกเลิกแล้วต้องจ่ายเงินก้อนใหญ่",
    "minimum_commitment": "ผู้ซื้อต้องซื้อขั้นต่ำ ต้องจ่ายส่วนต่างถ้าซื้อไม่ถึง "
                          "หรือต้องใช้ผู้ขายรายนี้รายเดียว",
}

# A risk that comes from a missing clause has nothing to quote.
ABSENCE_TYPES = {"weak_late_penalty"}

RISK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "risks": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "type": {"type": "STRING", "enum": list(RISK_TYPES)},
                    "clause": {
                        "type": "STRING",
                        "description": "ข้อความจากสัญญาแบบคำต่อคำ หรือว่างถ้าเป็นความเสี่ยง"
                                       "จากการไม่มีข้อกำหนด",
                    },
                    "reason": {"type": "STRING"},
                },
                "required": ["type", "clause", "reason"],
            },
        }
    },
    "required": ["risks"],
}


def definitions_text() -> str:
    return "\n".join(f"- {name}: {desc}" for name, desc in RISK_TYPES.items())


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def ground(risks: list[dict], contract_text: str) -> tuple[list[dict], list[dict]]:
    """Keep risks whose quoted clause is in the contract; drop the rest.

    Returns (kept, dropped). Duplicate types keep the first occurrence.
    """
    body = _norm(contract_text)
    kept, dropped, seen = [], [], set()
    for risk in risks:
        kind = risk.get("type")
        clause = (risk.get("clause") or "").strip()
        if kind not in RISK_TYPES:
            dropped.append({**risk, "dropped_because": "unknown_type"})
        elif kind in seen:
            continue
        elif not clause and kind not in ABSENCE_TYPES:
            dropped.append({**risk, "dropped_because": "no_clause_quoted"})
        elif clause and _norm(clause) not in body:
            dropped.append({**risk, "dropped_because": "clause_not_in_contract"})
        else:
            seen.add(kind)
            kept.append(risk)
    return kept, dropped


# ---------------------------------------------------------------------------
# Keyword baseline: what a search for familiar phrases would find. The
# evaluation reports it next to the model so the model's value is visible.

def _short_warranty(text: str) -> bool:
    for match in re.finditer(r"รับประกัน[^\n]{0,40}?(\d+)\s*(วัน|เดือน|ปี)", text):
        number, unit = int(match.group(1)), match.group(2)
        months = {"วัน": number / 30, "เดือน": number, "ปี": number * 12}[unit]
        if months < 12:
            return True
    return False


def _weak_late_penalty(text: str) -> bool:
    match = re.search(r"ค่าปรับล่าช้า[^\n]*?ไม่เกิน\s*(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1)) < 5
    return "ค่าปรับล่าช้า" not in text


BASELINE_RULES = {
    "full_prepayment": lambda t: bool(re.search(r"(100\s*%|เต็มจำนวน)\s*ล่วงหน้า", t)),
    "auto_renewal": lambda t: bool(re.search(r"ต่ออายุ(โดย)?อัตโนมัติ", t)),
    "unilateral_price_change": lambda t: bool(re.search(r"ผู้ขาย[^\n]{0,20}(ปรับ|ขึ้น)[^\n]{0,10}"
                                                        r"(ราคา|ค่า)", t)),
    "weak_late_penalty": _weak_late_penalty,
    "short_warranty": _short_warranty,
    "liability_cap_low": lambda t: bool(re.search(r"รับผิด[^\n]{0,40}ไม่เกิน", t)),
    "buyer_exit_penalty": lambda t: bool(re.search(r"ผู้ซื้อบอกเลิก[^\n]{0,60}ต้องชำระ", t)),
    "minimum_commitment": lambda t: bool(re.search(r"ขั้นต่ำ|ไม่น้อยกว่า|แต่เพียงผู้เดียว", t)),
}


def baseline_risks(contract_text: str) -> list[str]:
    return [kind for kind, rule in BASELINE_RULES.items() if rule(contract_text)]
