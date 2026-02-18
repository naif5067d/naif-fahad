# دليل صحة التنفيذ - نظام الحضور والخصومات
## Evidence Report - Attendance & Deduction Engine

**تاريخ التسليم:** 2026-02-18

---

## 1. العروق المضافة (Trace Functions)

### الملف الرئيسي: `/app/backend/services/day_resolver_v2.py`

```
DayResolverV2 - محرك القرار اليومي مع العروق (Trace Evidence)

ترتيب الفحص الإجباري:
┌────┬─────────────────┬──────────────────────────┐
│ # │ الخطوة (Step) │ الوصف │
├────┼─────────────────┼──────────────────────────┤
│ 1 │ holiday │ العطل الرسمية │
│ 2 │ weekend │ عطلة نهاية الأسبوع │
│ 3 │ leave │ الإجازات المنفذة │
│ 4 │ mission │ المهمات الخارجية │
│ 5 │ forget_checkin │ نسيان البصمة │
│ 6 │ attendance │ البصمة الفعلية │
│ 7 │ permission │ الاستئذان الجزئي │
│ 8 │ excuses │ التبريرات │
│ 9 │ ABSENT │ غياب (افتراضي) │
└────┴─────────────────┴──────────────────────────┘

أول نتيجة صحيحة = الحالة النهائية
```

### الدوال الرئيسية:

| الدالة | المهمة | المكان |
|--------|--------|--------|
| `resolve_day_v2()` | تنفيذ التحليل اليومي | `day_resolver_v2.py:L450` |
| `resolve_and_save_v2()` | تحليل + حفظ | `day_resolver_v2.py:L456` |
| `_check_holidays()` | فحص العطل | `day_resolver_v2.py:L145` |
| `_check_weekend()` | فحص نهاية الأسبوع | `day_resolver_v2.py:L170` |
| `_check_leaves()` | فحص الإجازات | `day_resolver_v2.py:L205` |
| `_check_missions()` | فحص المهمات | `day_resolver_v2.py:L255` |
| `_check_forgotten_punch()` | فحص نسيان البصمة | `day_resolver_v2.py:L285` |
| `_check_attendance()` | فحص البصمة | `day_resolver_v2.py:L315` |
| `_check_permissions()` | فحص الاستئذان | `day_resolver_v2.py:L400` |
| `_generate_trace_summary()` | إنشاء ملخص العروق | `day_resolver_v2.py:L100` |

---

## 2. كيف يعمل النظام خطوة بخطوة

### Flow: من البصمة إلى الخصم

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. تسجيل الحضور (Check-in/Check-out) │
│ ↓ │
│ POST /api/attendance/check-in │
│ → يُحفظ في attendance_ledger │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. تحليل اليوم (Daily Job) │
│ ↓ │
│ POST /api/attendance-engine/jobs/daily │
│ → يشغل DayResolverV2 لكل موظف │
│ → يفحص بالترتيب: holiday→weekend→leave→mission→... │
│ → يُحفظ في daily_status مع trace_log كامل │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. إنشاء مقترح الخصم (Auto-proposal) │
│ ↓ │
│ إذا final_status == ABSENT │
│ → create_absence_deduction_proposal() │
│ → يُحفظ في deduction_proposals بحالة "pending" │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. مراجعة المقترح (Sultan/Naif) │
│ ↓ │
│ POST /api/attendance-engine/deductions/{id}/review │
│ → approved=true → الحالة تصبح "approved" │
│ → approved=false → الحالة تصبح "rejected" │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. تنفيذ الخصم (STAS فقط) │
│ ↓ │
│ POST /api/attendance-engine/deductions/{id}/execute │
│ → execute_proposal() │
│ → يُنشئ سجل في finance_ledger │
│ → الحالة تصبح "executed" │
│ │
│ ⚠️ لا خصم يُسجل بدون STAS │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. كيف يتأكد النظام من عدم ظلم الموظف

### الفحوصات قبل ABSENT:

```python
# في DayResolverV2.resolve():

# 1. هل اليوم عطلة رسمية؟
result = await self._check_holidays()
if result: return result # ✅ عطلة - ليس غياب

# 2. هل اليوم نهاية أسبوع؟
result = await self._check_weekend()
if result: return result # ✅ عطلة - ليس غياب

# 3. هل للموظف إجازة منفذة تشمل هذا اليوم؟
result = await self._check_leaves()
if result: return result # ✅ إجازة - ليس غياب

# 4. هل للموظف مهمة خارجية منفذة؟
result = await self._check_missions()
if result: return result # ✅ مهمة - ليس غياب

# 5. هل للموظف طلب نسيان بصمة منفذ؟
result = await self._check_forgotten_punch()
if result: return result # ✅ نسيان معتمد - ليس غياب

# 6. هل سجل بصمة فعلية؟
result = await self._check_attendance()
if result: return result # ✅ حاضر (كامل/متأخر/مبكر)

# 7. هل لديه استئذان جزئي منفذ؟
result = await self._check_permissions()
if result: return result # ✅ استئذان - ليس غياب

# 8. فقط إذا فشلت جميع الفحوصات:
return self._create_absent_result() # ❌ غياب
```

### العروق (Trace Evidence):

كل فحص يُسجل في `trace_log` حتى لو فشل:

```json
{
"trace_log": [
 {
 "order": 1,
 "step": "holiday",
 "step_ar": "العطل الرسمية",
 "checked": true,
 "found": false,
 "result": "not_found",
 "details": {"searched_date": "2026-02-17"}
 },
 {
 "order": 2,
 "step": "weekend",
 "step_ar": "عطلة نهاية الأسبوع",
 "checked": true,
 "found": false,
 "result": "not_weekend",
 "details": {"day_of_week": 0, "day_name_ar": "الإثنين"}
 },
 // ... باقي الخطوات
],
"trace_summary": {
 "steps_checked": 8,
 "steps_found": 0,
 "deciding_step_ar": "غياب",
 "conclusion_ar": "لم يتم العثور على أي عطلة أو إجازة أو مهمة أو بصمة - يُعتبر غائباً"
}
}
```

---

## 4. كيف تُسجل الخصومات في finance_ledger

### عند تنفيذ المقترح (STAS فقط):

```python
# في deduction_service.py:execute_proposal()

finance_entry = {
 "id": str(uuid.uuid4()),
 "employee_id": proposal['employee_id'],
 "type": "debit", # خصم
 "code": "DEDUCTION",
 "amount": proposal['amount'],
 "currency": "SAR",
 "description": proposal['reason'],
 "description_ar": proposal['reason_ar'],
 "source": "deduction_proposal",
 "source_id": proposal_id,
 "deduction_type": proposal['deduction_type'],
 "month": proposal['month'],
 "explanation": proposal['explanation'],
 "executed_by": executor_id, # STAS
 "executed_at": now,
 "created_at": now
}

await db.finance_ledger.insert_one(finance_entry)
```

### مثال JSON فعلي:

```json
{
"id": "f8a5c2d1-...",
"employee_id": "EMP-001",
"type": "debit",
"code": "DEDUCTION",
"amount": 500.00,
"currency": "SAR",
"description": "Absence without excuse",
"description_ar": "غياب بدون عذر",
"source": "deduction_proposal",
"source_id": "abc123-...",
"deduction_type": "absence",
"month": "2026-02",
"explanation": {
 "سبب القرار": "غياب بدون عذر",
 "التاريخ": "2026-02-17",
 "السجلات المرجعية": {
  "إجازة": "لا يوجد",
  "مهمة": "لا يوجد",
  "بصمة": "لا يوجد",
  "عطلة": "لا يوجد"
 },
 "الراتب اليومي": 500.00,
 "المعادلة": "الراتب الشهري ÷ 30 = الخصم اليومي"
},
"executed_by": "STAS-001",
"executed_at": "2026-02-18T12:00:00Z"
}
```

---

## 5. كيف يتم تشغيل الـ Jobs التلقائية

### ملف الـ Jobs: `/app/backend/services/attendance_jobs.py`

#### Job اليومي:

```bash
# API Endpoint
POST /api/attendance-engine/jobs/daily

# يمكن تشغيله عبر CRON:
# 0 18 * * * curl -X POST https://api/attendance-engine/jobs/daily

# أو يدوياً:
curl -X POST "https://api/attendance-engine/jobs/daily" \
-H "Content-Type: application/json" \
-d '{"target_date": "2026-02-17"}'
```

**ماذا يفعل:**
1. يجلب جميع الموظفين النشطين
2. يشغل `resolve_and_save_v2()` لكل موظف
3. يُنشئ `deduction_proposal` لكل حالة ABSENT
4. يحفظ سجل التشغيل في `job_logs`

#### Job الشهري:

```bash
# API Endpoint
POST /api/attendance-engine/jobs/monthly

# يمكن تشغيله عبر CRON (أول كل شهر):
# 0 0 1 * * curl -X POST https://api/attendance-engine/jobs/monthly -d '{"finalize": true}'

curl -X POST "https://api/attendance-engine/jobs/monthly" \
-H "Content-Type: application/json" \
-d '{"target_month": "2026-02", "finalize": true}'
```

**ماذا يفعل:**
1. يحسب الساعات الشهرية لكل موظف
2. إذا `finalize=true`:
 - يُغلق الشهر
 - يُنشئ مقترحات خصم لنقص الساعات

---

## 6. Tests - اختبارات صحة النظام

### Test 1: وجود بصمة يمنع الغياب

```python
async def test_attendance_prevents_absent():
 # إنشاء بصمة دخول
 await db.attendance_ledger.insert_one({
   "employee_id": "TEST-001",
   "date": "2026-02-17",
   "type": "check_in",
   "timestamp": "2026-02-17T08:00:00Z"
 })
 
 # تحليل اليوم
 result = await resolve_day_v2("TEST-001", "2026-02-17")
 
 # التأكد أن الحالة ليست ABSENT
 assert result['final_status'] != 'ABSENT'
 assert result['final_status'] in ['PRESENT', 'LATE', 'EARLY_LEAVE']
```

### Test 2: وجود إجازة منفذة يمنع الغياب

```python
async def test_leave_prevents_absent():
 # إنشاء إجازة منفذة
 await db.transactions.insert_one({
   "employee_id": "TEST-002",
   "type": "leave_request",
   "status": "executed",
   "data": {
    "start_date": "2026-02-17",
    "end_date": "2026-02-20",
    "leave_type": "annual"
   }
 })
 
 # تحليل اليوم
 result = await resolve_day_v2("TEST-002", "2026-02-18")
 
 # التأكد أن الحالة إجازة
 assert result['final_status'] == 'ON_LEAVE'
 assert result['decision_source'] == 'leave'
```

### Test 3: لا خصم بدون STAS

```python
async def test_no_deduction_without_stas():
 # إنشاء مقترح خصم
 proposal = await create_absence_deduction_proposal("TEST-003", "2026-02-17", {})
 
 # موافقة المدير
 await review_proposal(proposal['id'], approved=True, reviewer_id="sultan")
 
 # التأكد أن الخصم لم يُسجل بعد
 ledger_entry = await db.finance_ledger.find_one({
   "source_id": proposal['id']
 })
 assert ledger_entry is None
 
 # تنفيذ STAS
 await execute_proposal(proposal['id'], executor_id="stas-001")
 
 # الآن الخصم مسجل
 ledger_entry = await db.finance_ledger.find_one({
   "source_id": proposal['id']
 })
 assert ledger_entry is not None
 assert ledger_entry['executed_by'] == 'stas-001'
```

---

## 7. ملخص الـ APIs

### Day Resolver:
- `POST /api/attendance-engine/resolve-day` - تحليل يوم لموظف
- `POST /api/attendance-engine/resolve-bulk` - تحليل يوم لجميع الموظفين
- `GET /api/attendance-engine/daily-status/{employee_id}/{date}` - جلب السجل اليومي

### Jobs:
- `POST /api/attendance-engine/jobs/daily` - تشغيل Job اليومي
- `POST /api/attendance-engine/jobs/monthly` - تشغيل Job الشهري
- `GET /api/attendance-engine/jobs/logs` - سجلات التشغيل

### Deductions:
- `GET /api/attendance-engine/deductions/pending` - المقترحات المعلقة
- `GET /api/attendance-engine/deductions/approved` - المقترحات الموافق عليها
- `POST /api/attendance-engine/deductions/{id}/review` - مراجعة (Sultan/Naif)
- `POST /api/attendance-engine/deductions/{id}/execute` - تنفيذ (STAS)

### Warnings:
- `GET /api/attendance-engine/warnings/pending` - الإنذارات المعلقة
- `POST /api/attendance-engine/warnings/{id}/review` - مراجعة الإنذار
- `POST /api/attendance-engine/warnings/{id}/execute` - تنفيذ الإنذار

### My Finances (Employee):
- `GET /api/attendance-engine/my-finances/deductions` - خصوماتي
- `GET /api/attendance-engine/my-finances/warnings` - إنذاراتي
- `GET /api/attendance-engine/my-finances/summary` - الملخص المالي

---

## 8. الملفات المعدلة/المضافة

| الملف | الحالة | الوصف |
|-------|--------|-------|
| `/app/backend/services/day_resolver_v2.py` | جديد | محرك القرار مع العروق |
| `/app/backend/services/attendance_jobs.py` | جديد | Jobs التلقائية |
| `/app/backend/services/warning_service.py` | جديد | الإنذارات والمخالفات |
| `/app/backend/routes/attendance_engine.py` | معدل | APIs جديدة |

---

**انتهى التقرير**
