"""
Financial Custody System - نظام العهدة المالية الإدارية
للإدارة فقط: سلطان، محمد، صلاح، STAS
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import require_roles, get_current_user
import uuid

router = APIRouter(prefix="/api/admin-custody", tags=["Admin Custody"])

# ==================== الأكواد الثابتة (60 كود) ====================
DEFAULT_EXPENSE_CODES = [
    {"code": 1, "name_ar": "اثاث الامانة", "name_en": "Furniture and Fixtures Amanah", "category_ar": "مصاريف إدارية عامة", "category_en": "General administrative expenses"},
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
    amount: float = Field(..., gt=0)
    notes: Optional[str] = None
    carry_forward_from: Optional[str] = None  # رقم العهدة السابقة للترحيل

class ExpenseCreate(BaseModel):
    code: int = Field(..., ge=1)
    description: str
    amount: float = Field(..., gt=0)
    custom_name: Optional[str] = None  # للأكواد الجديدة (61+)

class ExpenseUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None

class AuditAction(BaseModel):
    action: str  # approve, reject
    comment: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================

async def get_next_custody_number() -> str:
    """توليد رقم العهدة التالي"""
    last = await db.admin_custodies.find_one(
        {},
        sort=[("custody_number", -1)]
    )
    if last and last.get('custody_number'):
        try:
            num = int(last['custody_number']) + 1
        except:
            num = 1
    else:
        num = 1
    return str(num).zfill(3)

async def get_expense_code_info(code: int) -> dict:
    """جلب معلومات كود المصروف"""
    # أولاً: البحث في الأكواد المخصصة
    custom = await db.expense_codes.find_one({"code": code}, {"_id": 0})
    if custom:
        return custom
    
    # ثانياً: البحث في الأكواد الافتراضية
    for c in DEFAULT_EXPENSE_CODES:
        if c['code'] == code:
            return c
    
    return None

async def init_expense_codes():
    """تهيئة الأكواد في قاعدة البيانات"""
    count = await db.expense_codes.count_documents({})
    if count == 0:
        await db.expense_codes.insert_many(DEFAULT_EXPENSE_CODES)

# ==================== ENDPOINTS ====================

@router.on_event("startup")
async def startup():
    await init_expense_codes()


@router.get("/expense-codes")
async def get_all_expense_codes(
    user=Depends(require_roles('sultan', 'mohammed', 'salah', 'stas'))
):
    """جلب جميع أكواد المصروفات"""
    # جلب الأكواد من قاعدة البيانات
    codes = await db.expense_codes.find({}, {"_id": 0}).sort("code", 1).to_list(200)
    
    # إذا فارغة، استخدم الافتراضية
    if not codes:
        codes = DEFAULT_EXPENSE_CODES
    
    return codes


@router.get("/expense-codes/{code}")
async def get_expense_code(
    code: int,
    user=Depends(require_roles('sultan', 'mohammed', 'salah', 'stas'))
):
    """جلب معلومات كود معين"""
    info = await get_expense_code_info(code)
    if info:
        return info
    
    # كود جديد
    return {
        "code": code,
        "name_ar": None,
        "name_en": None,
        "category_ar": None,
        "category_en": None,
        "is_new": True
    }


@router.post("/expense-codes")
async def create_expense_code(
    code: int,
    name_ar: str,
    name_en: Optional[str] = None,
    category_ar: Optional[str] = None,
    category_en: Optional[str] = None,
    user=Depends(require_roles('sultan', 'mohammed', 'stas'))
):
    """إنشاء كود جديد"""
    existing = await db.expense_codes.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="الكود موجود مسبقاً")
    
    new_code = {
        "code": code,
        "name_ar": name_ar,
        "name_en": name_en or name_ar,
        "category_ar": category_ar or "غير مصنف",
        "category_en": category_en or "Uncategorized",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get('user_id')
    }
    
    await db.expense_codes.insert_one(new_code)
    new_code.pop('_id', None)
    
    return {"success": True, "code": new_code}


# ==================== CUSTODY MANAGEMENT ====================

@router.post("/create")
async def create_custody(
    data: CustodyCreate,
    user=Depends(require_roles('sultan', 'mohammed'))
):
    """إنشاء عهدة جديدة"""
    now = datetime.now(timezone.utc).isoformat()
    custody_number = await get_next_custody_number()
    
    # التحقق من الفائض السابق
    surplus_amount = 0
    surplus_from = None
    if data.carry_forward_from:
        prev = await db.admin_custodies.find_one({"custody_number": data.carry_forward_from})
        if prev and prev.get('status') == 'closed':
            surplus_amount = prev.get('remaining', 0)
            surplus_from = data.carry_forward_from
    
    new_custody = {
        "id": str(uuid.uuid4()),
        "custody_number": custody_number,
        "total_amount": data.amount + surplus_amount,
        "original_amount": data.amount,
        "surplus_from": surplus_from,
        "surplus_amount": surplus_amount,
        "spent": 0,
        "remaining": data.amount + surplus_amount,
        "status": "open",  # open, pending_audit, approved, executed, closed
        "notes": data.notes,
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', ''),
        "created_at": now,
        "updated_at": now,
        "audit_status": None,
        "audited_by": None,
        "audited_at": None,
        "audit_comment": None,
        "executed_by": None,
        "executed_at": None
    }
    
    await db.admin_custodies.insert_one(new_custody)
    new_custody.pop('_id', None)
    
    # تسجيل في السجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": new_custody['id'],
        "action": "created",
        "details": {"amount": data.amount, "surplus": surplus_amount},
        "performed_by": user.get('user_id'),
        "performed_at": now
    })
    
    return {
        "success": True,
        "message_ar": f"تم إنشاء العهدة رقم {custody_number}",
        "message_en": f"Custody {custody_number} created",
        "custody": new_custody
    }


@router.get("/all")
async def get_all_custodies(
    status: Optional[str] = None,
    user=Depends(require_roles('sultan', 'mohammed', 'salah', 'stas'))
):
    """جلب جميع العهد"""
    query = {}
    if status:
        query["status"] = status
    
    custodies = await db.admin_custodies.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return custodies


@router.get("/open-surplus")
async def get_open_surplus(
    user=Depends(require_roles('sultan', 'mohammed', 'salah', 'stas'))
):
    """جلب الفائض من العهد المغلقة"""
    closed = await db.admin_custodies.find(
        {"status": "closed", "remaining": {"$gt": 0}},
        {"_id": 0}
    ).to_list(50)
    
    total_surplus = sum(c.get('remaining', 0) for c in closed)
    
    return {
        "total_surplus": total_surplus,
        "custodies": closed
    }


@router.get("/{custody_id}")
async def get_custody(
    custody_id: str,
    user=Depends(require_roles('sultan', 'mohammed', 'salah', 'stas'))
):
    """جلب عهدة معينة مع مصروفاتها"""
    custody = await db.admin_custodies.find_one({"id": custody_id}, {"_id": 0})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    # جلب المصروفات
    expenses = await db.custody_expenses.find(
        {"custody_id": custody_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    custody['expenses'] = expenses
    
    return custody


# ==================== EXPENSES ====================

@router.post("/{custody_id}/expenses")
async def add_expense(
    custody_id: str,
    data: ExpenseCreate,
    user=Depends(require_roles('sultan', 'mohammed'))
):
    """إضافة مصروف للعهدة"""
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] == 'executed':
        raise HTTPException(status_code=400, detail="لا يمكن التعديل - العهدة منفذة")
    
    # التحقق من المتبقي
    if data.amount > custody['remaining']:
        raise HTTPException(
            status_code=400, 
            detail=f"المبلغ ({data.amount}) أكبر من المتبقي ({custody['remaining']})"
        )
    
    # جلب معلومات الكود
    code_info = await get_expense_code_info(data.code)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إذا كود جديد (61+) وغير موجود
    if not code_info and data.code > 60:
        if not data.custom_name:
            raise HTTPException(status_code=400, detail="يجب إدخال اسم للكود الجديد")
        
        # حفظ الكود الجديد
        new_code = {
            "code": data.code,
            "name_ar": data.custom_name,
            "name_en": data.custom_name,
            "category_ar": "غير مصنف",
            "category_en": "Uncategorized",
            "created_at": now,
            "created_by": user.get('user_id')
        }
        await db.expense_codes.insert_one(new_code)
        code_info = new_code
    
    expense = {
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "code": data.code,
        "code_name_ar": code_info.get('name_ar', data.custom_name) if code_info else data.custom_name,
        "code_name_en": code_info.get('name_en', data.custom_name) if code_info else data.custom_name,
        "category_ar": code_info.get('category_ar', 'غير مصنف') if code_info else 'غير مصنف',
        "category_en": code_info.get('category_en', 'Uncategorized') if code_info else 'Uncategorized',
        "description": data.description,
        "amount": data.amount,
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', ''),
        "created_at": now,
        "status": "active"  # active, cancelled
    }
    
    await db.custody_expenses.insert_one(expense)
    expense.pop('_id', None)
    
    # تحديث العهدة
    new_spent = custody['spent'] + data.amount
    new_remaining = custody['total_amount'] - new_spent
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {
            "spent": new_spent,
            "remaining": new_remaining,
            "updated_at": now
        }}
    )
    
    # تسجيل في السجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "expense_added",
        "details": {"expense_id": expense['id'], "amount": data.amount, "code": data.code},
        "performed_by": user.get('user_id'),
        "performed_at": now
    })
    
    return {
        "success": True,
        "expense": expense,
        "custody_update": {
            "spent": new_spent,
            "remaining": new_remaining
        }
    }


@router.delete("/{custody_id}/expenses/{expense_id}")
async def cancel_expense(
    custody_id: str,
    expense_id: str,
    user=Depends(require_roles('sultan', 'mohammed'))
):
    """إلغاء مصروف (ليس حذف)"""
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
    new_remaining = custody['total_amount'] - new_spent
    
    await db.admin_custodies.update_one(
        {"id": custody_id},
        {"$set": {
            "spent": new_spent,
            "remaining": new_remaining,
            "updated_at": now
        }}
    )
    
    # تسجيل في السجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "expense_cancelled",
        "details": {"expense_id": expense_id, "amount": expense['amount']},
        "performed_by": user.get('user_id'),
        "performed_at": now
    })
    
    return {
        "success": True,
        "message_ar": "تم إلغاء المصروف",
        "custody_update": {
            "spent": new_spent,
            "remaining": new_remaining
        }
    }


# ==================== AUDIT & EXECUTION ====================

@router.post("/{custody_id}/send-for-audit")
async def send_for_audit(
    custody_id: str,
    user=Depends(require_roles('sultan', 'mohammed'))
):
    """إرسال للتدقيق (صلاح)"""
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'open':
        raise HTTPException(status_code=400, detail="العهدة ليست مفتوحة")
    
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
        "message": f"العهدة رقم {custody['custody_number']} بانتظار تدقيقك",
        "type": "custody_audit",
        "read": False,
        "created_at": now
    })
    
    return {"success": True, "message_ar": "تم إرسال العهدة للتدقيق"}


@router.post("/{custody_id}/audit")
async def audit_custody(
    custody_id: str,
    data: AuditAction,
    user=Depends(require_roles('salah', 'stas'))
):
    """تدقيق العهدة (صلاح أو STAS)"""
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'pending_audit':
        raise HTTPException(status_code=400, detail="العهدة ليست بانتظار التدقيق")
    
    # STAS يستطيع الاعتماد بعد 24 ساعة
    role = user.get('role')
    if role == 'stas':
        sent_at = custody.get('sent_for_audit_at')
        if sent_at:
            sent_time = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            now_time = datetime.now(timezone.utc)
            if (now_time - sent_time) < timedelta(hours=24):
                raise HTTPException(status_code=400, detail="STAS يستطيع الاعتماد بعد 24 ساعة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if data.action == 'approve':
        new_status = 'approved'
        audit_status = 'approved'
    else:
        new_status = 'open'  # إرجاع لسلطان
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
    
    # تسجيل في السجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": f"audit_{data.action}",
        "details": {"comment": data.comment},
        "performed_by": user.get('user_id'),
        "performed_at": now
    })
    
    return {
        "success": True,
        "message_ar": "تم الاعتماد" if data.action == 'approve' else "تم الإرجاع",
        "new_status": new_status
    }


@router.post("/{custody_id}/execute")
async def execute_custody(
    custody_id: str,
    user=Depends(require_roles('stas'))
):
    """تنفيذ العهدة (STAS فقط)"""
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
    
    # تسجيل في السجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "executed",
        "details": {},
        "performed_by": user.get('user_id'),
        "performed_at": now
    })
    
    return {"success": True, "message_ar": "تم تنفيذ العهدة"}


@router.post("/{custody_id}/close")
async def close_custody(
    custody_id: str,
    user=Depends(require_roles('sultan', 'mohammed', 'stas'))
):
    """إغلاق العهدة"""
    custody = await db.admin_custodies.find_one({"id": custody_id})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    if custody['status'] != 'executed':
        raise HTTPException(status_code=400, detail="العهدة غير منفذة")
    
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
    
    # تسجيل في السجل
    await db.custody_logs.insert_one({
        "id": str(uuid.uuid4()),
        "custody_id": custody_id,
        "action": "closed",
        "details": {"remaining": custody['remaining']},
        "performed_by": user.get('user_id'),
        "performed_at": now
    })
    
    return {
        "success": True,
        "message_ar": "تم إغلاق العهدة",
        "surplus": custody['remaining']
    }


# ==================== DASHBOARD ====================

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    user=Depends(require_roles('sultan', 'mohammed', 'salah', 'stas'))
):
    """لوحة الإجماليات"""
    custodies = await db.admin_custodies.find({}, {"_id": 0}).to_list(500)
    
    summary = {
        "total_custodies": len(custodies),
        "open_custodies": len([c for c in custodies if c['status'] == 'open']),
        "pending_audit": len([c for c in custodies if c['status'] == 'pending_audit']),
        "approved": len([c for c in custodies if c['status'] == 'approved']),
        "executed": len([c for c in custodies if c['status'] == 'executed']),
        "closed": len([c for c in custodies if c['status'] == 'closed']),
        "total_amount": sum(c.get('total_amount', 0) for c in custodies if c['status'] != 'closed'),
        "total_spent": sum(c.get('spent', 0) for c in custodies if c['status'] != 'closed'),
        "total_remaining": sum(c.get('remaining', 0) for c in custodies if c['status'] != 'closed'),
        "total_surplus": sum(c.get('remaining', 0) for c in custodies if c['status'] == 'closed')
    }
    
    return summary
