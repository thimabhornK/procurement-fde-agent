"""ERP lookups the agent may call: vendor master, department budget, PO status.

The functions read the synthetic records in sample_data. In a real deployment
they would call the ERP's API with the agent's own read-only account.
"""

from __future__ import annotations

from typing import Any

from procurement_agent.sample_data import ERP, VENDORS


def get_vendor_info(vendor_name: str) -> dict[str, Any]:
    """Vendor status, credit limit, payment terms and approved categories."""
    needle = vendor_name.replace("บริษัท", "").replace("จำกัด", "").strip().lower()
    for vendor_id, vendor in VENDORS.items():
        name = vendor["name"].lower()
        if needle and needle in name:
            master = ERP["vendor_master"].get(vendor_id, {})
            return {"found": True, "vendor_id": vendor_id, "name": vendor["name"],
                    "status": vendor["status"], **master}
    return {"found": False, "message": f"ไม่พบผู้ขายชื่อ '{vendor_name}' ในระบบ ERP"}


def check_budget(department: str) -> dict[str, Any]:
    """Budget allocated, spent and remaining for one department."""
    budget = ERP["budget"].get(department)
    if budget is None:
        return {"found": False, "message": f"ไม่พบรหัสฝ่าย '{department}'"}
    remaining = budget["allocated"] - budget["spent"]
    return {"found": True, "department": department, "name": budget["name"],
            "allocated": budget["allocated"], "spent": budget["spent"],
            "remaining": remaining,
            "remaining_percent": round(remaining / budget["allocated"] * 100, 1)}


def get_po_status(po_number: str) -> dict[str, Any]:
    """Status, amount and vendor of one purchase order."""
    po = ERP["purchase_orders"].get(po_number.strip().upper())
    if po is None:
        return {"found": False, "message": f"ไม่พบใบสั่งซื้อ '{po_number}'"}
    vendor = VENDORS.get(po["vendor_id"], {})
    return {"found": True, "po_number": po_number.strip().upper(),
            "vendor_name": vendor.get("name"), **po}


FUNCTIONS = {f.__name__: f for f in (get_vendor_info, check_budget, get_po_status)}

DEPARTMENTS = ", ".join(f"{code} = {b['name']}" for code, b in ERP["budget"].items())

# Declarations for Gemini function calling.
DECLARATIONS = [
    {
        "name": "get_vendor_info",
        "description": "ดึงข้อมูลผู้ขายจาก ERP: สถานะ วงเครดิต เงื่อนไขชำระเงิน หมวดสินค้าที่อนุมัติ",
        "parameters": {
            "type": "OBJECT",
            "properties": {"vendor_name": {
                "type": "STRING",
                "description": "ชื่อบริษัทผู้ขาย ไม่ต้องมีคำว่า บริษัท หรือ จำกัด"}},
            "required": ["vendor_name"],
        },
    },
    {
        "name": "check_budget",
        "description": "ดูงบประมาณที่ได้รับ ใช้ไป และคงเหลือของฝ่าย",
        "parameters": {
            "type": "OBJECT",
            "properties": {"department": {
                "type": "STRING", "enum": list(ERP["budget"]),
                "description": f"รหัสฝ่าย: {DEPARTMENTS}"}},
            "required": ["department"],
        },
    },
    {
        "name": "get_po_status",
        "description": "ดูสถานะ ยอดเงิน และผู้ขายของใบสั่งซื้อ (PO)",
        "parameters": {
            "type": "OBJECT",
            "properties": {"po_number": {"type": "STRING",
                                         "description": "เลขใบสั่งซื้อ เช่น PO2026001"}},
            "required": ["po_number"],
        },
    },
]


def call(name: str, args: dict) -> dict[str, Any]:
    function = FUNCTIONS.get(name)
    if function is None:
        return {"error": f"ไม่มี tool ชื่อ '{name}'"}
    try:
        return function(**args)
    except TypeError as exc:
        return {"error": f"argument ไม่ถูกต้องสำหรับ {name}: {exc}"}
