"""
MCP server จำลองระบบ ERP สำหรับหน่วยงานจัดซื้อ
ในงานจริง server นี้จะเชื่อมต่อกับ SAP, Oracle หรือระบบ ERP ของลูกค้าจริงๆ
แต่สำหรับ demo นี้ใช้ข้อมูลจำลองแทนเพื่อแสดงให้เห็น concept

MCP protocol ทำงานแบบนี้:
1. Agent ถาม server ว่า "มี tool อะไรบ้าง"
2. Server ตอบกลับด้วยรายการ tool และ schema ของ input/output
3. Agent เลือก tool ที่ต้องการแล้วส่ง request มา
4. Server รัน tool และส่งผลกลับ
"""

from typing import Any

# ข้อมูลจำลองระบบ ERP
ERP_DATABASE = {
    "vendors": {
        "V001": {
            "name": "บริษัท ABC เทคโนโลยี จำกัด",
            "tax_id": "0105550012345",
            "status": "active",
            "credit_limit": 2_000_000,
            "payment_terms": "100% ล่วงหน้า",
            "approved_categories": ["IT equipment", "software"],
        },
        "V002": {
            "name": "บริษัท XYZ ซัพพลาย จำกัด",
            "tax_id": "0105550067890",
            "status": "active",
            "credit_limit": 5_000_000,
            "payment_terms": "30 วันหลังส่งมอบ",
            "approved_categories": ["office supplies", "furniture"],
        },
    },
    "purchase_orders": {
        "PO2024001": {
            "vendor_id": "V001",
            "amount": 750_000,
            "status": "pending_approval",
            "items": "โน้ตบุ๊ก 15 เครื่อง",
            "requested_by": "ฝ่ายไอที",
        },
        "PO2024002": {
            "vendor_id": "V002",
            "amount": 120_000,
            "status": "approved",
            "items": "วัสดุสำนักงานประจำเดือน",
            "requested_by": "ฝ่ายธุรการ",
        },
    },
    "budget": {
        "IT_DEPT": {"allocated": 2_000_000, "spent": 850_000},
        "ADMIN_DEPT": {"allocated": 500_000, "spent": 210_000},
    },
}


# ---- Tool definitions (schema ที่ agent จะเห็น) ----

TOOLS = [
    {
        "name": "get_vendor_info",
        "description": "ดึงข้อมูลผู้ขายจากระบบ ERP เช่น สถานะ วงเครดิต หมวดสินค้าที่อนุมัติ",
        "input_schema": {
            "type": "object",
            "properties": {
                "vendor_name": {
                    "type": "string",
                    "description": "ชื่อบริษัทผู้ขายที่ต้องการค้นหา",
                }
            },
            "required": ["vendor_name"],
        },
    },
    {
        "name": "check_budget",
        "description": "เช็คงบประมาณคงเหลือของแต่ละฝ่าย",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "รหัสฝ่าย เช่น IT_DEPT หรือ ADMIN_DEPT",
                }
            },
            "required": ["department"],
        },
    },
    {
        "name": "get_po_status",
        "description": "ตรวจสอบสถานะใบสั่งซื้อ (Purchase Order) จากรหัส PO",
        "input_schema": {
            "type": "object",
            "properties": {
                "po_number": {
                    "type": "string",
                    "description": "รหัส PO เช่น PO2024001",
                }
            },
            "required": ["po_number"],
        },
    },
]


# ---- Tool implementations (logic จริงที่รันเมื่อถูกเรียก) ----

def get_vendor_info(vendor_name: str) -> dict[str, Any]:
    """ค้นหาข้อมูลผู้ขายจากชื่อบริษัท"""
    for vendor_id, vendor in ERP_DATABASE["vendors"].items():
        if vendor_name.strip() in vendor["name"] or vendor["name"] in vendor_name.strip():
            return {
                "found": True,
                "vendor_id": vendor_id,
                **vendor,
            }
    return {"found": False, "message": f"ไม่พบผู้ขายชื่อ '{vendor_name}' ในระบบ ERP"}


def check_budget(department: str) -> dict[str, Any]:
    """ตรวจสอบงบประมาณคงเหลือ"""
    budget = ERP_DATABASE["budget"].get(department)
    if not budget:
        return {"found": False, "message": f"ไม่พบรหัสฝ่าย '{department}'"}
    remaining = budget["allocated"] - budget["spent"]
    return {
        "found": True,
        "department": department,
        "allocated": budget["allocated"],
        "spent": budget["spent"],
        "remaining": remaining,
        "remaining_percent": round(remaining / budget["allocated"] * 100, 1),
    }


def get_po_status(po_number: str) -> dict[str, Any]:
    """ตรวจสอบสถานะ PO"""
    po = ERP_DATABASE["purchase_orders"].get(po_number)
    if not po:
        return {"found": False, "message": f"ไม่พบ PO '{po_number}'"}
    vendor = ERP_DATABASE["vendors"].get(po["vendor_id"], {})
    return {
        "found": True,
        "po_number": po_number,
        "vendor_name": vendor.get("name", "ไม่ทราบ"),
        "amount": po["amount"],
        "status": po["status"],
        "items": po["items"],
        "requested_by": po["requested_by"],
    }


def call_tool(tool_name: str, tool_input: dict) -> dict[str, Any]:
    """จุดเข้าหลัก: รับชื่อ tool และ input แล้วส่งกลับผลลัพธ์"""
    if tool_name == "get_vendor_info":
        return get_vendor_info(**tool_input)
    elif tool_name == "check_budget":
        return check_budget(**tool_input)
    elif tool_name == "get_po_status":
        return get_po_status(**tool_input)
    else:
        return {"error": f"ไม่รู้จัก tool '{tool_name}'"}
