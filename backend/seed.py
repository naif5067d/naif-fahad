import uuid
from datetime import datetime, timezone
from utils.auth import hash_password

DEFAULT_PASSWORD = "DarAlCode2026!"

SEED_USERS = [
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "stas")),
        "username": "stas",
        "password_hash": None,
        "full_name": "STAS",
        "full_name_ar": "ستاس",
        "role": "stas",
        "email": "stas@daralcode.com",
        "is_active": True,
        "employee_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "mohammed")),
        "username": "mohammed",
        "password_hash": None,
        "full_name": "Mohammed Al-Rashid",
        "full_name_ar": "محمد الراشد",
        "role": "mohammed",
        "email": "mohammed@daralcode.com",
        "is_active": True,
        "employee_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "sultan")),
        "username": "sultan",
        "password_hash": None,
        "full_name": "Sultan Al-Otaibi",
        "full_name_ar": "سلطان العتيبي",
        "role": "sultan",
        "email": "sultan@daralcode.com",
        "is_active": True,
        "employee_id": "EMP-001",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "naif")),
        "username": "naif",
        "password_hash": None,
        "full_name": "Naif Al-Dosari",
        "full_name_ar": "نايف الدوسري",
        "role": "naif",
        "email": "naif@daralcode.com",
        "is_active": True,
        "employee_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "salah")),
        "username": "salah",
        "password_hash": None,
        "full_name": "Salah Al-Ahmad",
        "full_name_ar": "صالح الأحمد",
        "role": "salah",
        "email": "salah@daralcode.com",
        "is_active": True,
        "employee_id": "EMP-004",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "supervisor1")),
        "username": "supervisor1",
        "password_hash": None,
        "full_name": "Ahmad Al-Harbi",
        "full_name_ar": "أحمد الحربي",
        "role": "supervisor",
        "email": "ahmad@daralcode.com",
        "is_active": True,
        "employee_id": "EMP-002",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "employee1")),
        "username": "employee1",
        "password_hash": None,
        "full_name": "Khalid Al-Mutairi",
        "full_name_ar": "خالد المطيري",
        "role": "employee",
        "email": "khalid@daralcode.com",
        "is_active": True,
        "employee_id": "EMP-003",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "employee2")),
        "username": "employee2",
        "password_hash": None,
        "full_name": "Omar Al-Zahrani",
        "full_name_ar": "عمر الزهراني",
        "role": "employee",
        "email": "omar@daralcode.com",
        "is_active": True,
        "employee_id": "EMP-005",
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

SEED_EMPLOYEES = [
    {
        "id": "EMP-001",
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "sultan")),
        "employee_number": "EMP-001",
        "full_name": "Sultan Al-Otaibi",
        "full_name_ar": "سلطان العتيبي",
        "department": "Operations",
        "department_ar": "العمليات",
        "position": "Operations Manager",
        "position_ar": "مدير العمليات",
        "join_date": "2020-01-15",
        "supervisor_id": None,
        "working_calendar": {"saturday_working": True, "weekly_hours": 48},
        "leave_entitlement": {"annual": 30, "sick": 30, "emergency": 5},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "EMP-002",
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "supervisor1")),
        "employee_number": "EMP-002",
        "full_name": "Ahmad Al-Harbi",
        "full_name_ar": "أحمد الحربي",
        "department": "Engineering",
        "department_ar": "الهندسة",
        "position": "Senior Engineer",
        "position_ar": "مهندس أول",
        "join_date": "2021-03-01",
        "supervisor_id": "EMP-001",
        "working_calendar": {"saturday_working": False, "weekly_hours": 40},
        "leave_entitlement": {"annual": 25, "sick": 30, "emergency": 5},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "EMP-003",
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "employee1")),
        "employee_number": "EMP-003",
        "full_name": "Khalid Al-Mutairi",
        "full_name_ar": "خالد المطيري",
        "department": "Engineering",
        "department_ar": "الهندسة",
        "position": "Junior Engineer",
        "position_ar": "مهندس مبتدئ",
        "join_date": "2023-06-15",
        "supervisor_id": "EMP-002",
        "working_calendar": {"saturday_working": False, "weekly_hours": 40},
        "leave_entitlement": {"annual": 25, "sick": 30, "emergency": 5},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "EMP-004",
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "salah")),
        "employee_number": "EMP-004",
        "full_name": "Salah Al-Ahmad",
        "full_name_ar": "صالح الأحمد",
        "department": "Finance",
        "department_ar": "المالية",
        "position": "Finance Manager",
        "position_ar": "مدير مالي",
        "join_date": "2019-08-01",
        "supervisor_id": None,
        "working_calendar": {"saturday_working": True, "weekly_hours": 48},
        "leave_entitlement": {"annual": 30, "sick": 30, "emergency": 5},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "id": "EMP-005",
        "user_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "employee2")),
        "employee_number": "EMP-005",
        "full_name": "Omar Al-Zahrani",
        "full_name_ar": "عمر الزهراني",
        "department": "Engineering",
        "department_ar": "الهندسة",
        "position": "Engineer",
        "position_ar": "مهندس",
        "join_date": "2024-01-10",
        "supervisor_id": "EMP-002",
        "working_calendar": {"saturday_working": False, "weekly_hours": 40},
        "leave_entitlement": {"annual": 25, "sick": 30, "emergency": 5},
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    },
]

FINANCE_CODES = [
    {"code": 1, "name": "Basic Salary", "name_ar": "الراتب الأساسي", "category": "earnings"},
    {"code": 2, "name": "Housing Allowance", "name_ar": "بدل سكن", "category": "earnings"},
    {"code": 3, "name": "Transportation Allowance", "name_ar": "بدل نقل", "category": "earnings"},
    {"code": 4, "name": "Food Allowance", "name_ar": "بدل طعام", "category": "earnings"},
    {"code": 5, "name": "Phone Allowance", "name_ar": "بدل هاتف", "category": "earnings"},
    {"code": 6, "name": "Overtime Pay", "name_ar": "أجر إضافي", "category": "earnings"},
    {"code": 7, "name": "End of Service Benefits", "name_ar": "مكافأة نهاية خدمة", "category": "earnings"},
    {"code": 8, "name": "Annual Leave Pay", "name_ar": "رصيد إجازات سنوية", "category": "earnings"},
    {"code": 9, "name": "Sick Leave Pay", "name_ar": "إجازة مرضية", "category": "earnings"},
    {"code": 10, "name": "Business Trip Allowance", "name_ar": "بدل سفر عمل", "category": "earnings"},
    {"code": 11, "name": "Annual Bonus", "name_ar": "مكافأة سنوية", "category": "earnings"},
    {"code": 12, "name": "Eid Bonus", "name_ar": "مكافأة عيد", "category": "earnings"},
    {"code": 13, "name": "GOSI Employee Share", "name_ar": "حصة الموظف التأمينات", "category": "deductions"},
    {"code": 14, "name": "GOSI Employer Share", "name_ar": "حصة صاحب العمل التأمينات", "category": "deductions"},
    {"code": 15, "name": "Medical Insurance", "name_ar": "تأمين طبي", "category": "deductions"},
    {"code": 16, "name": "Work Injury Compensation", "name_ar": "تعويض إصابة عمل", "category": "earnings"},
    {"code": 17, "name": "Training Allowance", "name_ar": "بدل تدريب", "category": "earnings"},
    {"code": 18, "name": "Remote Work Allowance", "name_ar": "بدل عمل عن بعد", "category": "earnings"},
    {"code": 19, "name": "Danger Allowance", "name_ar": "بدل خطر", "category": "earnings"},
    {"code": 20, "name": "Nature of Work Allowance", "name_ar": "بدل طبيعة عمل", "category": "earnings"},
    {"code": 21, "name": "Representation Allowance", "name_ar": "بدل تمثيل", "category": "earnings"},
    {"code": 22, "name": "Furniture Allowance", "name_ar": "بدل أثاث", "category": "earnings"},
    {"code": 23, "name": "Education Allowance", "name_ar": "بدل تعليم", "category": "earnings"},
    {"code": 24, "name": "Children Allowance", "name_ar": "بدل أولاد", "category": "earnings"},
    {"code": 25, "name": "Ticket Allowance", "name_ar": "بدل تذاكر", "category": "earnings"},
    {"code": 26, "name": "Leave Ticket", "name_ar": "تذكرة إجازة", "category": "earnings"},
    {"code": 27, "name": "Housing Loan", "name_ar": "سلفة سكنية", "category": "loans"},
    {"code": 28, "name": "Personal Loan", "name_ar": "سلفة شخصية", "category": "loans"},
    {"code": 29, "name": "Advance Salary", "name_ar": "سلفة راتب", "category": "loans"},
    {"code": 30, "name": "Deduction - Absence", "name_ar": "خصم غياب", "category": "deductions"},
    {"code": 31, "name": "Deduction - Late Arrival", "name_ar": "خصم تأخير", "category": "deductions"},
    {"code": 32, "name": "Deduction - Early Leave", "name_ar": "خصم خروج مبكر", "category": "deductions"},
    {"code": 33, "name": "Deduction - Violation", "name_ar": "خصم مخالفة", "category": "deductions"},
    {"code": 34, "name": "Deduction - Loan Installment", "name_ar": "قسط سلفة", "category": "deductions"},
    {"code": 35, "name": "Commission", "name_ar": "عمولة", "category": "earnings"},
    {"code": 36, "name": "Project Bonus", "name_ar": "مكافأة مشروع", "category": "earnings"},
    {"code": 37, "name": "Performance Bonus", "name_ar": "مكافأة أداء", "category": "earnings"},
    {"code": 38, "name": "Sales Incentive", "name_ar": "حافز مبيعات", "category": "earnings"},
    {"code": 39, "name": "Signing Bonus", "name_ar": "مكافأة تعاقد", "category": "earnings"},
    {"code": 40, "name": "Relocation Allowance", "name_ar": "بدل انتقال", "category": "earnings"},
    {"code": 41, "name": "Hardship Allowance", "name_ar": "بدل مشقة", "category": "earnings"},
    {"code": 42, "name": "Night Shift Allowance", "name_ar": "بدل وردية ليلية", "category": "earnings"},
    {"code": 43, "name": "Visa Fee", "name_ar": "رسوم تأشيرة", "category": "deductions"},
    {"code": 44, "name": "Iqama Fee", "name_ar": "رسوم إقامة", "category": "deductions"},
    {"code": 45, "name": "Medical Expense", "name_ar": "مصاريف طبية", "category": "deductions"},
    {"code": 46, "name": "Uniform Allowance", "name_ar": "بدل ملابس", "category": "earnings"},
    {"code": 47, "name": "Tool Allowance", "name_ar": "بدل أدوات", "category": "earnings"},
    {"code": 48, "name": "Internet Allowance", "name_ar": "بدل إنترنت", "category": "earnings"},
    {"code": 49, "name": "Utility Allowance", "name_ar": "بدل خدمات", "category": "earnings"},
    {"code": 50, "name": "Marriage Bonus", "name_ar": "مكافأة زواج", "category": "earnings"},
    {"code": 51, "name": "Newborn Bonus", "name_ar": "مكافأة مولود", "category": "earnings"},
    {"code": 52, "name": "Bereavement Pay", "name_ar": "بدل عزاء", "category": "earnings"},
    {"code": 53, "name": "Hajj Leave Pay", "name_ar": "بدل إجازة حج", "category": "earnings"},
    {"code": 54, "name": "Exam Leave Pay", "name_ar": "بدل إجازة امتحان", "category": "earnings"},
    {"code": 55, "name": "Maternity Leave Pay", "name_ar": "بدل إجازة أمومة", "category": "earnings"},
    {"code": 56, "name": "Paternity Leave Pay", "name_ar": "بدل إجازة أبوة", "category": "earnings"},
    {"code": 57, "name": "Suspension Deduction", "name_ar": "خصم إيقاف", "category": "deductions"},
    {"code": 58, "name": "Tax Deduction", "name_ar": "خصم ضريبة", "category": "deductions"},
    {"code": 59, "name": "Charity Deduction", "name_ar": "خصم تبرع", "category": "deductions"},
    {"code": 60, "name": "Miscellaneous", "name_ar": "متفرقات", "category": "other"},
]

PUBLIC_HOLIDAYS_2026 = [
    {"name": "New Year", "name_ar": "رأس السنة", "date": "2026-01-01"},
    {"name": "Founding Day", "name_ar": "يوم التأسيس", "date": "2026-02-22"},
    {"name": "Eid Al-Fitr Day 1", "name_ar": "عيد الفطر - اليوم الأول", "date": "2026-03-20"},
    {"name": "Eid Al-Fitr Day 2", "name_ar": "عيد الفطر - اليوم الثاني", "date": "2026-03-21"},
    {"name": "Eid Al-Fitr Day 3", "name_ar": "عيد الفطر - اليوم الثالث", "date": "2026-03-22"},
    {"name": "Eid Al-Fitr Day 4", "name_ar": "عيد الفطر - اليوم الرابع", "date": "2026-03-23"},
    {"name": "Arafat Day", "name_ar": "يوم عرفة", "date": "2026-05-26"},
    {"name": "Eid Al-Adha Day 1", "name_ar": "عيد الأضحى - اليوم الأول", "date": "2026-05-27"},
    {"name": "Eid Al-Adha Day 2", "name_ar": "عيد الأضحى - اليوم الثاني", "date": "2026-05-28"},
    {"name": "Eid Al-Adha Day 3", "name_ar": "عيد الأضحى - اليوم الثالث", "date": "2026-05-29"},
    {"name": "Saudi National Day", "name_ar": "اليوم الوطني السعودي", "date": "2026-09-23"},
]


async def seed_database(db):
    existing = await db.users.count_documents({})
    if existing > 0:
        return {"message": "Database already seeded", "seeded": False}

    hashed = hash_password(DEFAULT_PASSWORD)
    for u in SEED_USERS:
        u["password_hash"] = hashed
    await db.users.insert_many(SEED_USERS)

    await db.employees.insert_many(SEED_EMPLOYEES)

    codes = []
    for fc in FINANCE_CODES:
        codes.append({
            "id": str(uuid.uuid4()),
            "code": fc["code"],
            "name": fc["name"],
            "name_ar": fc["name_ar"],
            "category": fc["category"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    await db.finance_codes.insert_many(codes)

    holidays = []
    for h in PUBLIC_HOLIDAYS_2026:
        holidays.append({
            "id": str(uuid.uuid4()),
            "name": h["name"],
            "name_ar": h["name_ar"],
            "date": h["date"],
            "year": 2026,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    await db.public_holidays.insert_many(holidays)

    # Seed initial leave balances in leave_ledger (credit entitlements)
    for emp in SEED_EMPLOYEES:
        ent = emp.get("leave_entitlement", {})
        for leave_type, days in ent.items():
            await db.leave_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": emp["id"],
                "transaction_id": None,
                "type": "credit",
                "leave_type": leave_type,
                "days": days,
                "note": "Initial entitlement",
                "date": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            })

    # Initialize transaction counter
    await db.counters.insert_one({"id": "transaction_ref", "seq": 0})

    return {"message": "Database seeded successfully", "seeded": True}
