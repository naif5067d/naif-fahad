"""
نظام العهدة المالية الإدارية - Financial Custody System
للإدارة فقط: سلطان، محمد، صلاح، STAS

التدفق:
1. سلطان/محمد ينشئ عهدة جديدة بمبلغ
2. يضيف مصروفات عبر جدول Excel-like (كود + وصف + مبلغ)
3. النظام يحسب تلقائياً: المصروف والمتبقي
4. إرسال للتدقيق (صلاح)
5. صلاح يعتمد أو يرجع + يمكنه التعديل
6. STAS ينفذ
7. إذا بقي فائض، يُرحّل للعهدة الجديدة
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin-custody", tags=["Admin Custody"])

# ==================== الأكواد الـ60 ====================
EXPENSE_CODES = [
    {"code": 1, "name_ar": "اثاث الامانة", "name_en": "Amanah Furniture", "category_ar": "مصاريف إدارية عامة", "category_en": "General administrative expenses"},
    {"code": 2, "name_ar": "ادوات نظافة", "name_en": "Cleaning supplies", "category_ar": "حساب الاستهلاك", "category_en": "Amortisation expense"},
    {"code": 3, "name_ar": "ادوات ومهمات مستهلكة", "name_en": "Consumable tools", "category_ar": "الديون المعدومة", "category_en": "Bad debts"},
    {"code": 4, "name_ar": "اللوازم والمواد", "name_en": "Supplies and materials", "category_ar": "الرسوم المصرفية", "category_en": "Bank charges"},
    {"code": 5, "name_ar": "انتقالات", "name_en": "Transportation", "category_ar": "العمولات والرسوم", "category_en": "Commissions and fees"},
    {"code": 6, "name_ar": "ايجار معدات", "name_en": "Equipment rental", "category_ar": "مصاريف الاستشارات", "category_en": "Consultancy Expenses"},
    {"code": 7, "name_ar": "بدل تذاكر سفر", "name_en": "Travel tickets allowance", "category_ar": "الرسوم والاشتراكات", "category_en": "Dues and subscriptions"},
    {"code": 8, "name_ar": "تذاكر سفر", "name_en": "Travel tickets", "category_ar": "مصاريف الاستشارات الهندسية", "category_en": "Engineering consulting expenses"},
    {"code": 9, "name_ar": "خدمات التأمين - عام", "name_en": "Insurance - General", "category_ar": "التأمين العام", "category_en": "Insurance - General"},
    {"code": 10, "name_ar": "صيانه واصلاح", "name_en": "Repairs and Maintenance", "category_ar": "الصيانة", "category_en": "Maintenance"},
    {"code": 11, "name_ar": "ضيافة", "name_en": "Hospitality", "category_ar": "تعويض الإدارة", "category_en": "Management compensation"},
    {"code": 12, "name_ar": "ضيافة الامانة", "name_en": "Hospitality Amanah", "category_ar": "مصاريف إدارية وعمومية", "category_en": "General and administrative expenses"},
    {"code": 13, "name_ar": "عمل اضافي", "name_en": "Overtime", "category_ar": "جزاءات", "category_en": "Penalties"},
    {"code": 14, "name_ar": "فنادق", "name_en": "Hotels", "category_ar": "بدل تذاكر السفر", "category_en": "Travel tickets allowance"},
    {"code": 15, "name_ar": "محروقات", "name_en": "Fuel", "category_ar": "حساب غير مصنف", "category_en": "Uncategorised Expense"},
    {"code": 16, "name_ar": "مرتبات الامانة", "name_en": "Amanah salaries", "category_ar": "ضريبة", "category_en": "VAT"},
    {"code": 17, "name_ar": "مرتبات الوزارة", "name_en": "Ministry salaries", "category_ar": "زكاة", "category_en": "Zakat"},
    {"code": 18, "name_ar": "مرتبات وحوافز غير منتظمة", "name_en": "Irregular salaries", "category_ar": "مصاريف الأمانة", "category_en": "Amanah expenses"},
    {"code": 19, "name_ar": "مصاريف استشارات هندسية", "name_en": "Engineering consulting", "category_ar": "مصاريف الأمانة", "category_en": "Amanah expenses"},
    {"code": 20, "name_ar": "مصاريف الامانة", "name_en": "Amanah expenses", "category_ar": "أثاث وتركيبات", "category_en": "Furniture and Fixtures"},
    {"code": 21, "name_ar": "مصاريف السكن", "name_en": "Housing expenses", "category_ar": "كرم الضيافة", "category_en": "Hospitality"},
    {"code": 22, "name_ar": "مصاريف سفر", "name_en": "Travel expenses", "category_ar": "مصاريف الرواتب", "category_en": "Payroll Expenses"},
    {"code": 23, "name_ar": "مصروفات غير مصنفة", "name_en": "Uncategorized expenses", "category_ar": "مصاريف الوزارة", "category_en": "Ministry expenses"},
    {"code": 24, "name_ar": "نقل وشحن", "name_en": "Shipping", "category_ar": "علاوة", "category_en": "Bonus"},
    {"code": 25, "name_ar": "اتصالات وانترنت", "name_en": "Communications", "category_ar": "تأجير المعدات", "category_en": "Equipment rental"},
    {"code": 26, "name_ar": "ادوات مكتبية وقرطاسية", "name_en": "Office supplies", "category_ar": "حسن الضيافة", "category_en": "Hospitality"},
    {"code": 27, "name_ar": "التامين - العام", "name_en": "Insurance - General", "category_ar": "الفنادق", "category_en": "Hotels"},
    {"code": 28, "name_ar": "الرسوم الحكومية والقانونية", "name_en": "Legal fees", "category_ar": "الرسوم القانونية", "category_en": "Legal fees"},
    {"code": 29, "name_ar": "الرسوم والاشتراكات", "name_en": "Dues and subscriptions", "category_ar": "التأمين الطبي", "category_en": "Medical insurance"},
    {"code": 30, "name_ar": "الزكاه", "name_en": "Zakat", "category_ar": "نفقات الأجور", "category_en": "Payroll Expenses"},
    {"code": 31, "name_ar": "ايجار", "name_en": "Rent", "category_ar": "بنزين", "category_en": "Petrol"},
    {"code": 32, "name_ar": "بدل اجازة", "name_en": "Leave allowance", "category_ar": "إصلاح وصيانة", "category_en": "Repairs and Maintenance"},
    {"code": 33, "name_ar": "تأمين طبي", "name_en": "Medical insurance", "category_ar": "الشحن والتسليم", "category_en": "Shipping"},
    {"code": 34, "name_ar": "تأمينات اجتماعية", "name_en": "Social insurance", "category_ar": "التأمينات الاجتماعية", "category_en": "Social insurance"},
    {"code": 35, "name_ar": "تعويض الإدارة", "name_en": "Management compensation", "category_ar": "القرطاسية والطباعة", "category_en": "Stationery"},
    {"code": 36, "name_ar": "جزاءات عاملين", "name_en": "Employee penalties", "category_ar": "اللوازم", "category_en": "Supplies"},
    {"code": 37, "name_ar": "دعايا واعلان", "name_en": "Advertising", "category_ar": "اللوازم والمواد", "category_en": "Supplies"},
    {"code": 38, "name_ar": "ديون معدومة", "name_en": "Bad debts", "category_ar": "انتقالات", "category_en": "Transportation"},
    {"code": 39, "name_ar": "رسوم مكتب المحاسبة", "name_en": "Accounting fees", "category_ar": "مصاريف السفر", "category_en": "Travel expenses"},
    {"code": 40, "name_ar": "عمولات واكراميات", "name_en": "Commissions", "category_ar": "تذاكر السفر", "category_en": "Travel Tickets"},
    {"code": 41, "name_ar": "غرامات", "name_en": "Fines", "category_ar": "خدمات", "category_en": "Utilities"},
    {"code": 42, "name_ar": "محروقات وصيانه سيارات", "name_en": "Fuel and car maintenance", "category_ar": "مصاريف المكتب", "category_en": "Office Expenses"},
    {"code": 43, "name_ar": "مخالفات مرورية", "name_en": "Traffic violations", "category_ar": "الاتصالات", "category_en": "Communication"},
    {"code": 44, "name_ar": "مرتبات المكتب", "name_en": "Office salaries", "category_ar": "مصاريف السكن", "category_en": "Housing"},
    {"code": 45, "name_ar": "مساعدات واعانات", "name_en": "Aid and subsidies", "category_ar": "نفقات المكتب", "category_en": "Office expenses"},
    {"code": 46, "name_ar": "مصاريف الإدارة", "name_en": "Admin expenses", "category_ar": "مصاريف الإعلانات", "category_en": "Advertising"},
    {"code": 47, "name_ar": "مصاريف المكتب", "name_en": "Office expenses", "category_ar": "العمل الإضافي", "category_en": "Overtime"},
    {"code": 48, "name_ar": "مصاريف بنكية", "name_en": "Bank charges", "category_ar": "مصاريف الرواتب", "category_en": "Payroll"},
    {"code": 49, "name_ar": "مصاريف ترك الخدمة", "name_en": "End of service", "category_ar": "البنزين", "category_en": "Petrol"},
    {"code": 50, "name_ar": "مصاريف سنوات سابقه", "name_en": "Prior years expenses", "category_ar": "إيجار", "category_en": "Rent"},
    {"code": 51, "name_ar": "مصاريف عمومية وإدارية أخرى", "name_en": "Other G&A expenses", "category_ar": "غرامة مرورية", "category_en": "Traffic fine"},
    {"code": 52, "name_ar": "مكافأت", "name_en": "Bonuses", "category_ar": "مكافآت", "category_en": "Bonuses"},
    {"code": 53, "name_ar": "مصاريف مشروع سكة الحديد", "name_en": "Railway project expenses", "category_ar": "مشاريع", "category_en": "Projects"},
    {"code": 54, "name_ar": "مصاريف سفر محمود مشروع سكة الحديد", "name_en": "Mahmoud travel - Railway", "category_ar": "مشاريع", "category_en": "Projects"},
    {"code": 55, "name_ar": "عهدة", "name_en": "Custody", "category_ar": "عهدة", "category_en": "Custody"},
    {"code": 56, "name_ar": "فيلا م سعود", "name_en": "Villa M Saud", "category_ar": "عقارات", "category_en": "Real Estate"},
    {"code": 57, "name_ar": "مصاريف مشروع الزلفي", "name_en": "Zulfi project expenses", "category_ar": "مشاريع", "category_en": "Projects"},
    {"code": 58, "name_ar": "أجهزة للمكتب", "name_en": "Office equipment", "category_ar": "أجهزة", "category_en": "Equipment"},
    {"code": 59, "name_ar": "رسوم حوالات بنكية", "name_en": "Bank transfer fees", "category_ar": "رسوم بنكية", "category_en": "Bank fees"},
    {"code": 60, "name_ar": "اثاث مكتبي", "name_en": "Office furniture", "category_ar": "أثاث", "category_en": "Furniture"},
]

# ==================== MODELS ====================

class CustodyCreate(BaseModel):
    amount: float = Field(..., gt=0, description="مبلغ العهدة")
    notes: Optional[str] = None

class ExpenseCreate(BaseModel):
    code: int = Field(..., ge=1, description="كود المصروف")
    description: str = Field(..., min_length=1, description="وصف المصروف")
    amount: float = Field(..., gt=0, description="المبلغ")
    custom_name: Optional[str] = None

class AuditAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    comment: Optional[str] = None

class ExpenseEdit(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None

# ==================== HELPER FUNCTIONS ====================

ALLOWED_ROLES = ['sultan', 'mohammed', 'salah', 'stas']

def check_role(user: dict, allowed: list):
    role = user.get('role', '')
    if role not in allowed:
        raise HTTPException(status_code=403, detail="غير مصرح")
    return role

async def get_next_custody_number() -> str:
    last = await db.admin_custodies.find_one({}, sort=[("custody_number_int", -1)])
    next_num = (last.get('custody_number_int', 0) + 1) if last else 1
    return str(next_num).zfill(3), next_num

def get_code_info(code: int) -> dict:
    """جلب معلومات الكود من القائمة الثابتة"""
    for c in EXPENSE_CODES:
        if c['code'] == code:
            return c
    return None

async def get_code_info_db(code: int) -> dict:
    """جلب معلومات الكود من قاعدة البيانات أولاً، ثم القائمة الثابتة"""
    db_code = await db.expense_codes.find_one({"code": code}, {"_id": 0})
    if db_code:
        return db_code
    return get_code_info(code)

# ==================== EXPENSE CODES ====================

@router.get("/codes")
async def get_all_codes(user=Depends(get_current_user)):
    """جلب جميع الأكواد (ثابتة + مضافة)"""
    check_role(user, ALLOWED_ROLES)
    
    # جلب الأكواد المضافة من قاعدة البيانات
    custom_codes = await db.expense_codes.find({"code": {"$gt": 60}}, {"_id": 0}).to_list(100)
    
    # دمج مع الأكواد الثابتة
    all_codes = EXPENSE_CODES.copy()
    all_codes.extend(custom_codes)
    
    return {"codes": all_codes, "total": len(all_codes)}


@router.get("/codes/{code}")
async def get_code(code: int, user=Depends(get_current_user)):
    """جلب معلومات كود محدد"""
    check_role(user, ALLOWED_ROLES)
    
    info = await get_code_info_db(code)
    
    if info:
        return {"found": True, "code": info}
    
    return {
        "found": False,
        "code": {"code": code, "name_ar": None, "name_en": None, "is_new": True}
    }


@router.post("/codes")
async def create_code(
    code: int = Query(..., ge=61),
    name_ar: str = Query(...),
    name_en: Optional[str] = None,
    category_ar: Optional[str] = None,
    user=Depends(get_current_user)
):
    """إنشاء كود جديد (61+)"""
    check_role(user, ['sultan', 'mohammed', 'stas'])
    
    existing = await db.expense_codes.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="الكود موجود مسبقاً")
    
    new_code = {
        "code": code,
        "name_ar": name_ar,
        "name_en": name_en or name_ar,
        "category_ar": category_ar or "غير مصنف",
        "category_en": "Uncategorized",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get('user_id')
    }
    
    await db.expense_codes.insert_one(new_code)
    new_code.pop('_id', None)
    
    return {"success": True, "code": new_code}

# ==================== CUSTODY MANAGEMENT ====================

@router.post("/create")
async def create_custody(data: CustodyCreate, user=Depends(get_current_user)):
    """إنشاء عهدة جديدة"""
    check_role(user, ['sultan', 'mohammed'])
    
    now = datetime.now(timezone.utc).isoformat()
    custody_number, custody_number_int = await get_next_custody_number()
    
    # فحص الفائض من العهد السابقة
    surplus_info = await db.admin_custodies.find_one(
        {"status": "closed", "remaining": {"$gt": 0}},
        sort=[("created_at", -1)]
    )
    
    surplus_amount = 0
    surplus_from = None
    if surplus_info and surplus_info.get('remaining', 0) > 0:
        surplus_amount = surplus_info['remaining']
        surplus_from = surplus_info['custody_number']
    
    custody = {
        "id": str(uuid.uuid4()),
        "custody_number": custody_number,
        "custody_number_int": custody_number_int,
        "total_amount": data.amount,
        "surplus_amount": surplus_amount,
        "surplus_from": surplus_from,
        "budget": data.amount + surplus_amount,
        "spent": 0.0,
        "remaining": data.amount + surplus_amount,
        "status": "open",
        "notes": data.notes,
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', user.get('username', '')),
        "created_at": now,
        "updated_at": now,
        "sent_for_audit_at": None,
        "sent_for_audit_by": None,
        "audited_by": None,
        "audited_by_name": None,
        "audited_at": None,
        "audit_status": None,
        "audit_comment": None,
        "executed_by": None,
        "executed_by_name": None,
        "executed_at": None,
        "closed_at": None,
        "closed_by": None
    }
    
    await db.admin_custodies.insert_one(custody)
    custody.pop('_id', None)
    
    # سجل الأحداث
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody['id'],
        "action": "created",
        "details": {"amount": data.amount, "surplus": surplus_amount},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    # إذا تم ترحيل فائض، تحديث العهدة السابقة
    if surplus_from:
        await db.admin_custodies.update_one(
            {"custody_number": surplus_from},
            {"$set": {"surplus_transferred_to": custody_number, "remaining": 0}}
        )
    
    return {
        "success": True,
        "message_ar": f"تم إنشاء العهدة رقم {custody_number}",
        "custody": custody,
        "surplus_alert": f"تم ترحيل {surplus_amount} ريال من العهدة {surplus_from}" if surplus_from else None
    }


@router.get("/all")
async def get_all_custodies(
    status: Optional[str] = None,
    user=Depends(get_current_user)
):
    """جلب جميع العهد"""
    check_role(user, ALLOWED_ROLES)
    
    query = {}
    if status:
        query["status"] = status
    
    custodies = await db.admin_custodies.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # جلب عدد المصروفات لكل عهدة
    for c in custodies:
        count = await db.custody_expenses.count_documents({"custody_id": c['id'], "status": "active"})
        c['expense_count'] = count
    
    return custodies


@router.get("/summary")
async def get_summary(user=Depends(get_current_user)):
    """إحصائيات العهد"""
    check_role(user, ALLOWED_ROLES)
    
    all_custodies = await db.admin_custodies.find({}, {"_id": 0}).to_list(500)
    
    open_custodies = [c for c in all_custodies if c['status'] == 'open']
    pending_audit = [c for c in all_custodies if c['status'] == 'pending_audit']
    approved = [c for c in all_custodies if c['status'] == 'approved']
    executed = [c for c in all_custodies if c['status'] == 'executed']
    closed = [c for c in all_custodies if c['status'] == 'closed']
    
    return {
        "total_custodies": len(all_custodies),
        "open": len(open_custodies),
        "pending_audit": len(pending_audit),
        "approved": len(approved),
        "executed": len(executed),
        "closed": len(closed),
        "total_budget": sum(c.get('budget', 0) for c in all_custodies if c['status'] not in ['closed']),
        "total_spent": sum(c.get('spent', 0) for c in all_custodies if c['status'] not in ['closed']),
        "total_remaining": sum(c.get('remaining', 0) for c in all_custodies if c['status'] not in ['closed']),
        "total_surplus": sum(c.get('remaining', 0) for c in closed)
    }


@router.get("/surplus-available")
async def get_available_surplus(user=Depends(get_current_user)):
    """جلب الفائض المتاح للترحيل"""
    check_role(user, ALLOWED_ROLES)
    
    closed_with_surplus = await db.admin_custodies.find(
        {"status": "closed", "remaining": {"$gt": 0}, "surplus_transferred_to": None},
        {"_id": 0}
    ).to_list(50)
    
    total = sum(c.get('remaining', 0) for c in closed_with_surplus)
    
    return {
        "available_surplus": total,
        "custodies": closed_with_surplus
    }


@router.get("/{custody_id}")
async def get_custody(custody_id: str, user=Depends(get_current_user)):
    """جلب عهدة محددة مع مصروفاتها"""
    check_role(user, ALLOWED_ROLES)
    
    custody = await db.admin_custodies.find_one({"id": custody_id}, {"_id": 0})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    expenses = await db.custody_expenses.find(
        {"custody_id": custody_id, "status": "active"},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    logs = await db.custody_logs.find(
        {"custody_id": custody_id},
        {"_id": 0}
    ).sort("performed_at", -1).to_list(100)
    
    custody['expenses'] = expenses
    custody['logs'] = logs
    
    return custody

# ==================== EXPENSES ====================

@router.post("/{custody_id}/expense")
async def add_expense(custody_id: str, data: ExpenseCreate, user=Depends(get_current_user)):
    """إضافة مصروف"""
    check_role(user, ['sultan', 'mohammed'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] not in ['open', 'pending_audit']:
        raise HTTPException(status_code=400, detail="لا يمكن إضافة مصروفات - العهدة ليست مفتوحة")
    
    if custody['status'] == 'pending_audit':
        # إرجاع للحالة المفتوحة إذا كانت بانتظار التدقيق
        await db.admin_custodies.update_one(
            {"id": custody_id},
            {"$set": {"status": "open"}}
        )
    
    if data.amount > custody['remaining']:
        raise HTTPException(
            status_code=400,
            detail=f"المبلغ ({data.amount}) يتجاوز المتبقي ({custody['remaining']})"
        )
    
    # جلب معلومات الكود
    code_info = await get_code_info_db(data.code)
    
    # إذا كود جديد (61+) ولم يوجد
    if not code_info and data.code > 60:
        if not data.custom_name:
            raise HTTPException(status_code=400, detail="يجب إدخال اسم للكود الجديد")
        
        code_info = {
            "code": data.code,
            "name_ar": data.custom_name,
            "name_en": data.custom_name,
            "category_ar": "غير مصنف",
            "category_en": "Uncategorized"
        }
        # حفظ الكود الجديد
        await db.expense_codes.insert_one({
            **code_info,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user.get('user_id')
        })
    
    now = datetime.now(timezone.utc).isoformat()
    
    expense = {
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "code": data.code,
        "code_name_ar": code_info.get('name_ar', str(data.code)) if code_info else str(data.code),
        "code_name_en": code_info.get('name_en', str(data.code)) if code_info else str(data.code),
        "category_ar": code_info.get('category_ar', 'غير مصنف') if code_info else 'غير مصنف',
        "description": data.description,
        "amount": data.amount,
        "status": "active",
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', ''),
        "created_at": now,
        "edited_by": None,
        "edited_at": None
    }
    
    await db.custody_expenses.insert_one(expense)
    expense.pop('_id', None)
    
    # تحديث العهدة
    new_spent = custody['spent'] + data.amount
    new_remaining = custody['budget'] - new_spent
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {"spent": new_spent, "remaining": new_remaining, "updated_at": now}}
    )
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "expense_added",
        "details": {"expense_id": expense['id'], "code": data.code, "amount": data.amount},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    return {
        "success": True,
        "expense": expense,
        "custody_update": {"spent": new_spent, "remaining": new_remaining}
    }


@router.delete("/{custody_id}/expense/{expense_id}")
async def cancel_expense(custody_id: str, expense_id: str, user=Depends(get_current_user)):
    """إلغاء مصروف (لا حذف فعلي)"""
    check_role(user, ['sultan', 'mohammed', 'salah'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] == 'executed':
        raise HTTPException(status_code=400, detail="لا يمكن التعديل - العهدة منفذة")
    
    expense = await db.custody_expenses.find_one({"id": expense_id, "custody_id": custody_id})
    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")
    
    if expense['status'] == 'cancelled':
        raise HTTPException(status_code=400, detail="المصروف ملغي مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إلغاء المصروف
    await db.custody_expenses.update_one(
        {"id": expense_id},
        {"$set": {"status": "cancelled", "cancelled_at": now, "cancelled_by": user.get('user_id')}}
    )
    
    # تحديث العهدة
    new_spent = custody['spent'] - expense['amount']
    new_remaining = custody['budget'] - new_spent
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {"spent": new_spent, "remaining": new_remaining, "updated_at": now}}
    )
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "expense_cancelled",
        "details": {"expense_id": expense_id, "amount": expense['amount']},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    return {
        "success": True,
        "message_ar": "تم إلغاء المصروف",
        "custody_update": {"spent": new_spent, "remaining": new_remaining}
    }


@router.put("/{custody_id}/expense/{expense_id}")
async def edit_expense(
    custody_id: str,
    expense_id: str,
    data: ExpenseEdit,
    user=Depends(get_current_user)
):
    """تعديل مصروف (صلاح فقط أثناء التدقيق)"""
    role = check_role(user, ['salah', 'stas'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'pending_audit' and role != 'stas':
        raise HTTPException(status_code=400, detail="التعديل متاح فقط أثناء التدقيق")
    
    expense = await db.custody_expenses.find_one({"id": expense_id, "custody_id": custody_id, "status": "active"})
    if not expense:
        raise HTTPException(status_code=404, detail="المصروف غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    updates = {"edited_by": user.get('user_id'), "edited_at": now}
    
    amount_diff = 0
    if data.description:
        updates['description'] = data.description
    
    if data.amount is not None and data.amount != expense['amount']:
        amount_diff = data.amount - expense['amount']
        new_remaining = custody['remaining'] - amount_diff
        
        if new_remaining < 0:
            raise HTTPException(status_code=400, detail="المبلغ الجديد يتجاوز المتبقي")
        
        updates['amount'] = data.amount
    
    await db.custody_expenses.update_one({"id": expense_id}, {"$set": updates})
    
    # تحديث العهدة إذا تغير المبلغ
    if amount_diff != 0:
        new_spent = custody['spent'] + amount_diff
        new_remaining = custody['budget'] - new_spent
        await db.admin_custodies.update_one(
            {"id": custody_id},
            {"$set": {"spent": new_spent, "remaining": new_remaining, "updated_at": now}}
        )
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "expense_edited",
        "details": {"expense_id": expense_id, "changes": updates},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    return {"success": True, "message_ar": "تم تعديل المصروف"}

# ==================== WORKFLOW ====================

@router.post("/{custody_id}/submit-audit")
async def submit_for_audit(custody_id: str, user=Depends(get_current_user)):
    """إرسال للتدقيق (صلاح)"""
    check_role(user, ['sultan', 'mohammed'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'open':
        raise HTTPException(status_code=400, detail="العهدة يجب أن تكون مفتوحة")
    
    # التحقق من وجود مصروفات
    expense_count = await db.custody_expenses.count_documents({"custody_id": custody_id, "status": "active"})
    if expense_count == 0:
        raise HTTPException(status_code=400, detail="أضف مصروفات أولاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "pending_audit",
            "sent_for_audit_at": now,
            "sent_for_audit_by": user.get('user_id'),
            "updated_at": now
        }}
    )
    
    # إشعار لصلاح
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": "salah",
        "title": "عهدة للتدقيق",
        "message": f"العهدة رقم {custody['custody_number']} بانتظار تدقيقك - المبلغ: {custody['spent']} ريال",
        "type": "custody_audit",
        "reference_id": custody_id,
        "read": False,
        "created_at": now
    })
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "submitted_for_audit",
        "details": {"spent": custody['spent'], "remaining": custody['remaining']},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    return {"success": True, "message_ar": "تم إرسال العهدة للتدقيق", "status": "pending_audit"}


@router.post("/{custody_id}/audit")
async def audit_custody(custody_id: str, data: AuditAction, user=Depends(get_current_user)):
    """تدقيق العهدة (صلاح) - أو STAS بعد 24 ساعة"""
    role = check_role(user, ['salah', 'stas'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'pending_audit':
        raise HTTPException(status_code=400, detail="العهدة ليست بانتظار التدقيق")
    
    # STAS يستطيع الاعتماد بعد 24 ساعة فقط
    if role == 'stas' and custody.get('sent_for_audit_at'):
        sent_time = datetime.fromisoformat(custody['sent_for_audit_at'].replace('Z', '+00:00'))
        if (datetime.now(timezone.utc) - sent_time) < timedelta(hours=24):
            raise HTTPException(status_code=400, detail="STAS يستطيع الاعتماد بعد مرور 24 ساعة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if data.action == 'approve':
        new_status = 'approved'
        audit_status = 'approved'
    else:
        new_status = 'open'
        audit_status = 'rejected'
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {
            "status": new_status,
            "audit_status": audit_status,
            "audited_by": user.get('user_id'),
            "audited_by_name": user.get('full_name', ''),
            "audited_at": now,
            "audit_comment": data.comment,
            "updated_at": now
        }}
    )
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": f"audit_{data.action}",
        "details": {"comment": data.comment},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    # إشعار
    if data.action == 'reject':
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": custody['created_by'],
            "title": "تم إرجاع العهدة",
            "message": f"العهدة رقم {custody['custody_number']} تم إرجاعها: {data.comment or 'بدون ملاحظات'}",
            "type": "custody_rejected",
            "reference_id": custody_id,
            "read": False,
            "created_at": now
        })
    
    return {
        "success": True,
        "message_ar": "تم الاعتماد" if data.action == 'approve' else "تم الإرجاع",
        "status": new_status
    }


@router.post("/{custody_id}/execute")
async def execute_custody(custody_id: str, user=Depends(get_current_user)):
    """تنفيذ العهدة (STAS فقط)"""
    check_role(user, ['stas'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'approved':
        raise HTTPException(status_code=400, detail="العهدة غير معتمدة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "executed",
            "executed_by": user.get('user_id'),
            "executed_by_name": user.get('full_name', ''),
            "executed_at": now,
            "updated_at": now
        }}
    )
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "executed",
        "details": {"spent": custody['spent'], "remaining": custody['remaining']},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    return {
        "success": True,
        "message_ar": "تم تنفيذ العهدة",
        "status": "executed",
        "remaining": custody['remaining']
    }


@router.post("/{custody_id}/close")
async def close_custody(custody_id: str, user=Depends(get_current_user)):
    """إغلاق العهدة"""
    check_role(user, ['sultan', 'mohammed', 'stas'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'executed':
        raise HTTPException(status_code=400, detail="العهدة يجب أن تكون منفذة لإغلاقها")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "closed",
            "closed_by": user.get('user_id'),
            "closed_at": now,
            "updated_at": now
        }}
    )
    
    # سجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "closed",
        "details": {"surplus": custody['remaining']},
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "performed_at": now
    })
    
    msg = "تم إغلاق العهدة"
    if custody['remaining'] > 0:
        msg += f" - فائض {custody['remaining']} ريال سيُرحّل للعهدة القادمة"
    
    return {
        "success": True,
        "message_ar": msg,
        "status": "closed",
        "surplus": custody['remaining']
    }



# ==================== PDF & DELETE ====================

class BulkDeleteRequest(BaseModel):
    custody_ids: List[str] = Field(..., min_length=1)


@router.get("/{custody_id}/pdf")
async def generate_custody_pdf(custody_id: str, lang: str = 'ar', user=Depends(get_current_user)):
    """توليد PDF للعهدة"""
    from fastapi.responses import Response
    from utils.custody_pdf import generate_custody_pdf as gen_pdf
    
    check_role(user, ALLOWED_ROLES)
    
    custody = await db.admin_custodies.find_one({"id": custody_id}, {"_id": 0})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    expenses = await db.custody_expenses.find(
        {"custody_id": custody_id, "status": "active"},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    # Company branding
    branding = await db.company_settings.find_one({}, {"_id": 0})
    
    try:
        pdf_bytes = gen_pdf(custody, expenses, branding, lang)
        
        filename = f"custody_{custody['custody_number']}_{lang}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"خطأ في إنشاء PDF: {str(e)}")


@router.delete("/bulk")
async def bulk_delete_custodies(data: BulkDeleteRequest, user=Depends(get_current_user)):
    """حذف متعدد للعهد (STAS فقط)"""
    check_role(user, ['stas'])
    
    now = datetime.now(timezone.utc).isoformat()
    deleted_count = 0
    failed_ids = []
    
    for custody_id in data.custody_ids:
        custody = await db.admin_custodies.find_one({"id": custody_id})
        
        if not custody:
            failed_ids.append({"id": custody_id, "reason": "غير موجودة"})
            continue
        
        # STAS يستطيع حذف جميع العهد بلا استثناء
        # حذف فعلي من قاعدة البيانات
        
        # حذف كل المصروفات
        await db.custody_expenses.delete_many({"custody_id": custody_id})
        
        # حذف السجلات
        await db.custody_logs.delete_many({"custody_id": custody_id})
        
        # حذف العهدة نفسها
        await db.admin_custodies.delete_one({"id": custody_id})
        
        deleted_count += 1
    
    return {
        "success": True,
        "message_ar": f"تم حذف {deleted_count} عهدة نهائياً",
        "deleted_count": deleted_count,
        "failed": failed_ids
    }


@router.delete("/{custody_id}")
async def delete_single_custody(custody_id: str, user=Depends(get_current_user)):
    """حذف عهدة واحدة (STAS فقط) - حذف فعلي"""
    check_role(user, ['stas'])
    
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    custody_number = custody['custody_number']
    
    # STAS يستطيع حذف جميع العهد - حذف فعلي
    # حذف المصروفات
    await db.custody_expenses.delete_many({"custody_id": custody_id})
    
    # حذف السجلات
    await db.custody_logs.delete_many({"custody_id": custody_id})
    
    # حذف العهدة
    await db.admin_custodies.delete_one({"id": custody_id})
    
    return {
        "success": True,
        "message_ar": f"تم حذف العهدة رقم {custody_number} نهائياً"
    }
