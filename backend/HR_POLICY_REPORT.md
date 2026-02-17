# تقرير فني: تحديث سياسة الموارد البشرية
## HR Policy Update Technical Report

**التاريخ:** 2026-02-17
**الإصدار:** 2.0.0

---

## 1. ملخص التغييرات

### ✅ النقاط المنفذة

| # | النقطة | الحالة | الملاحظات |
|---|--------|--------|-----------|
| 1 | معادلة الاستحقاق السنوي (Pro-Rata) | ✅ PASS | `daily_accrual = 21/365`, `earned_to_date = daily * days_worked` |
| 2 | 21 أو 30 يوم - مصدر القرار | ✅ PASS | من العقد `annual_policy_days` أو قرار إداري |
| 3 | منع الترحيل + تنبيهات | ✅ PASS | لا ترحيل تلقائي + CRON alerts |
| 4 | الإجازات الإدارية | ✅ PASS | مسار إداري فقط، لا خصم |
| 5 | قواعد عرض التصعيد | ✅ PASS | "قيد المراجعة" للموظف |
| 6 | قواعد Blocking | ✅ PASS | معاملة واحدة نشطة فقط |
| 7 | ملخص الموظف | ✅ PASS | للموظف: مختصر، للإدارة: شامل |
| 8 | STAS ختم التنفيذ | ✅ PASS | idempotent + Barcode |
| 9 | اللغة والتاريخ | ✅ PASS | توقيت الرياض، عربي/إنجليزي |

---

## 2. الملفات المُعدّلة

### Backend - ملفات جديدة

| الملف | الوصف |
|-------|-------|
| `/app/backend/services/hr_policy.py` | محرك السياسة الشامل - Pro-Rata, Blocking, التواريخ |
| `/app/backend/routes/admin.py` | إدارة السياسات، الترحيل، التنبيهات |

### Backend - ملفات مُحدّثة

| الملف | التغييرات |
|-------|----------|
| `/app/backend/services/leave_service.py` | - استخدام Pro-Rata بدلاً من الرصيد الثابت<br>- تكامل مع hr_policy<br>- حذف منطق "الرصيد الافتتاحي 25" |
| `/app/backend/services/stas_mirror_service.py` | - عرض سياسة 21/30<br>- عرض معادلة Pro-Rata<br>- فحوصات محسنة |
| `/app/backend/routes/leave.py` | - إضافة قاعدة Blocking<br>- استيراد hr_policy |
| `/app/backend/routes/employees.py` | - ملخص محدث للموظف/الإدارة<br>- عرض Pro-Rata والسياسة |
| `/app/backend/routes/contracts_v2.py` | - إضافة حقل `annual_policy_days`<br>- القيم: 21 أو 30 فقط |
| `/app/backend/server.py` | - إضافة admin_router |

---

## 3. تغييرات قاعدة البيانات (Schema)

### مجموعة جديدة: `admin_overrides`
```javascript
{
  "id": "uuid",
  "employee_id": "string",
  "override_type": "annual_leave_policy" | "leave_carryover",
  "value": 21 | 30 | float,
  "year": 2026,
  "from_year": 2025,  // للترحيل
  "to_year": 2026,    // للترحيل
  "reason": "string",
  "approved_by": "user_id",
  "is_active": true,
  "created_at": "ISO datetime"
}
```

### تحديث `contracts_v2`
```javascript
{
  // ... الحقول الموجودة
  "annual_policy_days": 21 | 30  // جديد - السياسة الرسمية
}
```

---

## 4. APIs الجديدة/المُحدّثة

### APIs جديدة

| Method | Endpoint | الوصف | الصلاحية |
|--------|----------|-------|----------|
| POST | `/api/admin/annual-policy` | تغيير سياسة 21/30 | STAS |
| GET | `/api/admin/annual-policy/{employee_id}` | جلب السياسة | STAS, Sultan, Naif |
| POST | `/api/admin/leave-carryover` | ترحيل إجازات بقرار | STAS |
| GET | `/api/admin/balance-alerts` | تنبيهات الأرصدة | STAS, Sultan, Naif |
| POST | `/api/admin/reset-balances` | إعادة تعيين (خطير) | STAS |
| POST | `/api/admin/reset-test-data` | حذف بيانات TEST- | STAS |

### APIs مُحدّثة

| Endpoint | التغيير |
|----------|---------|
| `GET /api/employees/{id}/summary` | يُرجع الآن Pro-Rata والسياسة |
| `POST /api/leave/request` | يفحص Blocking أولاً |

---

## 5. المعادلات المُنفذة

### معادلة الاستحقاق السنوي (Pro-Rata)

```python
# المعادلات الأساسية
annual_entitlement_year = contract.annual_policy_days  # 21 أو 30
days_in_year = 366 if leap_year else 365
daily_accrual = annual_entitlement_year / days_in_year

# حساب أيام العمل
calc_start_date = max(contract_start_date, year_start)
calc_end_date = min(today, year_end)
days_worked = (calc_end_date - calc_start_date).days + 1

# الاستحقاق والرصيد
earned_to_date = daily_accrual * days_worked
used_executed = sum(leave_ledger.debits WHERE date IN year)
available_balance = earned_to_date - used_executed

# التقريب
# العرض: 2 decimals (round(x, 2))
# التخزين: float كامل
```

### مثال عملي
```
الموظف: سلطان الزامل
السياسة: 21 يوم
السنة: 2026 (365 يوم)
بداية الحساب: 2026-01-01
اليوم: 2026-02-17 (48 يوم عمل)
المستخدم: 0 يوم

المعادلة: 21 / 365 × 48 - 0 = 2.76 يوم متاح
```

---

## 6. قاعدة Blocking

### المنطق
```python
# عند تقديم طلب إجازة جديد
active_statuses = [
    "pending_supervisor", "pending_ops", 
    "pending_ceo", "pending_stas", "pending_finance"
]

blocking_tx = await db.transactions.find_one({
    "employee_id": employee_id,
    "type": "leave_request",  # أو نفس نوع الطلب
    "status": {"$in": active_statuses}
})

if blocking_tx:
    raise HTTPException(
        status_code=400,
        detail=f"لديك طلب قيد المراجعة ({blocking_tx['ref_no']})"
    )
```

---

## 7. قواعد عرض التصعيد

### للموظف
```python
# الموظف يرى دائماً "قيد المراجعة" بدلاً من:
# - "تصعيد"
# - "pending_ops"
# - "pending_ceo"
# - "self_request_escalated"
```

### للإدارة
```python
# الأدوار التي ترى التفاصيل الكاملة
roles_can_see_escalation = ['sultan', 'naif', 'stas', 'mohammed', 'ceo']
```

---

## 8. نتائج الاختبارات

### اختبارات يدوية

| الاختبار | النتيجة | الملاحظات |
|----------|---------|-----------|
| Pro-Rata Calculation | ✅ PASS | `21 / 365 × 48 - 0 = 2.76` |
| Blocking Rule | ✅ PASS | رسالة خطأ واضحة بالعربية |
| Policy Source | ✅ PASS | يعرض "العقد" أو "قرار إداري" |
| Employee Summary | ✅ PASS | للموظف: مختصر، للإدارة: كامل |
| Balance Alerts | ✅ PASS | يُرجع قائمة فارغة (لا تنبيهات حالياً) |
| Arabic Error Messages | ✅ PASS | جميع الرسائل بالعربية |

---

## 9. ملاحظات للمستقبل

### التنبيهات (CRON Job)
- `generate_balance_alerts()` جاهزة للتشغيل كـ CRON
- تُنبه قبل 90 يوم من نهاية العقد/السنة
- يجب ربطها بـ Scheduler

### الترحيل
- لا ترحيل تلقائي (وفق السياسة)
- الترحيل يتطلب قرار إداري عبر `/api/admin/leave-carryover`
- يُسجل كـ credit في leave_ledger

### PDF
- Barcode موجود في STAS stamp
- التحقق من عدم كسر الخطوط العربية ✅

---

## 10. Diff ملخص

```diff
+ services/hr_policy.py (جديد - 580 سطر)
+ routes/admin.py (جديد - 180 سطر)

~ services/leave_service.py
  - حذف منطق الرصيد الثابت
  + استخدام calculate_pro_rata_entitlement()
  + استخدام get_annual_leave_balance_v2()

~ services/stas_mirror_service.py
  + عرض سياسة الإجازة (21/30)
  + عرض معادلة Pro-Rata
  + فحوصات إضافية

~ routes/leave.py
  + استيراد check_blocking_transaction
  + فحص Blocking قبل إنشاء الطلب

~ routes/employees.py
  + ملخص مختلف للموظف/الإدارة
  + عرض Pro-Rata والسياسة
  + حقول جاهزة: السلف، العهد، المعاملات النشطة

~ routes/contracts_v2.py
  + حقل annual_policy_days

~ server.py
  + admin_router
```

---

**انتهى التقرير**
