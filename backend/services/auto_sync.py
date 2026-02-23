"""
نظام التزامن التلقائي - Dar Al Code
Auto Sync System

هذا الملف يحتوي على جميع البيانات الأساسية التي يجب أن تكون موجودة
في أي بيئة (Preview أو Production)

يتم تنفيذه تلقائياً عند بدء التطبيق
"""

from datetime import datetime, timezone
import uuid
import bcrypt

# ==================== إعدادات الشركة ====================
COMPANY_SETTINGS = {
    "company_name": "DAR AL CODE",
    "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
    "company_name_en": "Dar Al Code Engineering Consultancy",
    "short_name": "دار الكود",
    "short_name_en": "DAR ALCODE",
    "primary_color": "#1E3A5F",
    "secondary_color": "#A78BFA",
    "welcome_text_ar": "أنتم الدار ونحن الكود",
    "welcome_text_en": "You are the Home, We are the Code",
    "version": "2.0.0"
}

# ==================== المستخدمين الأساسيين ====================
# هؤلاء يجب أن يكونوا موجودين في كل بيئة
CORE_USERS = [
    {
        "id": "stas-user-001",
        "username": "stas506",
        "password": "654321",  # سيتم تشفيره
        "role": "stas",
        "full_name": "STAS",
        "full_name_ar": "ستاس",
        "email": "stas@daralcode.com",
        "employee_id": "EMP-STAS",
        "is_active": True
    },
    {
        "id": "mohammed-user-001",
        "username": "mohammed",
        "password": "123456",
        "role": "mohammed",
        "full_name": "Eng. Mohammed bin Saud Al Thunayan",
        "full_name_ar": "م. محمد بن سعود الثنيان",
        "email": "mohammed@daralcode.com",
        "employee_id": "EMP-MOHAMMED",
        "is_active": True
    },
    {
        "id": "sultan-user-001",
        "username": "sultan",
        "password": "123456",
        "role": "sultan",
        "full_name": "Mr.Sultan Al Zamil",
        "full_name_ar": "أ.سلطان الزامل",
        "email": "sultan@daralcode.com",
        "employee_id": "EMP-001",
        "is_active": True
    },
    {
        "id": "naif-user-001",
        "username": "naif",
        "password": "123456",
        "role": "naif",
        "full_name": "Eng. Naif",
        "full_name_ar": "م. نايف",
        "email": "naif@daralcode.com",
        "employee_id": "EMP-NAIF",
        "is_active": True
    },
    {
        "id": "salah-user-001",
        "username": "salah",
        "password": "123456",
        "role": "salah",
        "full_name": "Mr. Salah",
        "full_name_ar": "أ. صلاح",
        "email": "salah@daralcode.com",
        "employee_id": "EMP-004",
        "is_active": True
    }
]

# ==================== الموظفين المستثنين من الحضور ====================
EXEMPT_EMPLOYEES = ["EMP-STAS", "EMP-MOHAMMED", "EMP-004", "EMP-NAIF"]

# ==================== دالة التزامن ====================
async def auto_sync_database(db):
    """
    تزامن تلقائي للبيانات الأساسية
    يُنفذ عند بدء التطبيق
    """
    now = datetime.now(timezone.utc).isoformat()
    sync_results = {
        "timestamp": now,
        "actions": []
    }
    
    # 1. تزامن إعدادات الشركة
    existing_settings = await db.settings.find_one({"type": "company"})
    if not existing_settings:
        await db.settings.insert_one({
            "id": "company-settings-001",
            "type": "company",
            **COMPANY_SETTINGS,
            "created_at": now,
            "updated_at": now
        })
        sync_results["actions"].append("✅ تم إنشاء إعدادات الشركة")
    else:
        # تحديث الإعدادات الأساسية فقط إذا كانت قديمة
        update_fields = {}
        for key in ["company_name_ar", "company_name_en", "short_name", "version"]:
            if existing_settings.get(key) != COMPANY_SETTINGS.get(key):
                update_fields[key] = COMPANY_SETTINGS[key]
        
        if update_fields:
            update_fields["updated_at"] = now
            await db.settings.update_one(
                {"type": "company"},
                {"$set": update_fields}
            )
            sync_results["actions"].append(f"✅ تم تحديث إعدادات الشركة: {list(update_fields.keys())}")
    
    # 2. تزامن المستخدمين الأساسيين
    for user_data in CORE_USERS:
        existing_user = await db.users.find_one({
            "$or": [
                {"username": user_data["username"]},
                {"id": user_data["id"]}
            ]
        })
        
        if not existing_user:
            # إنشاء المستخدم
            hashed_password = bcrypt.hashpw(
                user_data["password"].encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            new_user = {
                **user_data,
                "password": hashed_password,
                "created_at": now,
                "updated_at": now
            }
            await db.users.insert_one(new_user)
            sync_results["actions"].append(f"✅ تم إنشاء مستخدم: {user_data['username']}")
        else:
            # التأكد من أن المستخدم فعال
            if not existing_user.get("is_active", True):
                await db.users.update_one(
                    {"username": user_data["username"]},
                    {"$set": {"is_active": True, "updated_at": now}}
                )
                sync_results["actions"].append(f"✅ تم تفعيل مستخدم: {user_data['username']}")
    
    # 3. التأكد من وجود موظفين للمستخدمين الأساسيين
    for user_data in CORE_USERS:
        if user_data["employee_id"]:
            existing_emp = await db.employees.find_one({"id": user_data["employee_id"]})
            if not existing_emp:
                # إنشاء موظف أساسي
                emp_data = {
                    "id": user_data["employee_id"],
                    "user_id": user_data["id"],
                    "code": user_data["employee_id"].replace("EMP-", ""),
                    "full_name": user_data["full_name"],
                    "full_name_ar": user_data["full_name_ar"],
                    "email": user_data["email"],
                    "is_active": True,
                    "status": "active",
                    "department": "Management",
                    "department_ar": "الإدارة",
                    "position": user_data["role"].title(),
                    "position_ar": user_data["full_name_ar"],
                    "created_at": now,
                    "updated_at": now
                }
                await db.employees.insert_one(emp_data)
                sync_results["actions"].append(f"✅ تم إنشاء موظف: {user_data['employee_id']}")
    
    # 4. سجل التزامن
    if sync_results["actions"]:
        await db.sync_log.insert_one({
            "id": str(uuid.uuid4()),
            "type": "auto_sync",
            "results": sync_results,
            "created_at": now
        })
        print(f"[AUTO-SYNC] {len(sync_results['actions'])} actions performed")
    else:
        print("[AUTO-SYNC] No changes needed - database is in sync")
    
    return sync_results


async def force_full_sync(db):
    """
    تزامن إجباري كامل - يُستخدم عند الحاجة لإعادة تعيين كل شيء
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. تحديث إعدادات الشركة (إجباري)
    await db.settings.update_one(
        {"type": "company"},
        {"$set": {**COMPANY_SETTINGS, "updated_at": now}},
        upsert=True
    )
    
    # 2. إعادة تعيين كلمات مرور المستخدمين الأساسيين
    for user_data in CORE_USERS:
        hashed_password = bcrypt.hashpw(
            user_data["password"].encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        await db.users.update_one(
            {"username": user_data["username"]},
            {
                "$set": {
                    "password": hashed_password,
                    "is_active": True,
                    "role": user_data["role"],
                    "full_name": user_data["full_name"],
                    "full_name_ar": user_data["full_name_ar"],
                    "updated_at": now
                }
            },
            upsert=True
        )
    
    return {
        "success": True,
        "message_ar": "تم التزامن الكامل بنجاح",
        "message_en": "Full sync completed successfully",
        "timestamp": now
    }
