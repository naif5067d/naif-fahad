# HR Management System - PRD

## Original Problem Statement
نظام إدارة موارد بشرية شامل يتضمن:
- إدارة الموظفين والعقود
- نظام الحضور والانصراف مع GPS
- إدارة الإجازات والأذونات
- نظام المعاملات والموافقات
- لوحة تحكم إدارية (STAS Mirror)

## Core Architecture
- **Backend**: FastAPI + MongoDB
- **Frontend**: React + Shadcn/UI + TailwindCSS
- **Database**: MongoDB (test_database)
  - العقود في جدول `contracts_v2`
  - الموظفين في جدول `employees`

## What's Been Implemented

### 2026-02-21 (Session 2)

1. **إصلاح التوقيت (P0)** ✅
   - تحويل جميع أوقات الحضور من UTC إلى توقيت الرياض (+03:00)

2. **إصلاح مشكلة "لا يوجد عقد نشط" (P0)** ✅
   - **السبب الجذري**: كان الكود يبحث بشرط `is_active: True`
   - العقود في `contracts_v2` لديها `is_active: None`
   - **الملفات المصلحة**:
     - `/app/backend/utils/attendance_rules.py`
     - `/app/backend/services/day_resolver_v2.py`

3. **ميزة تحديث الإصدار** ✅
   - استبدال "حذف المعاملات" بـ "إدارة الإصدار" في STAS Mirror

4. **ربط الموظفين بموقع العمل** ✅
   - جميع الموظفين الآن مربوطين بالمقر الرئيسي

## System Flow (قصة حياة الموظف)

راجع الملف: `/app/memory/SYSTEM_FLOW.md`

### ترتيب الفحص اليومي (Day Resolver V2):
```
1. holiday    → عطلة رسمية
2. weekend    → عطلة نهاية أسبوع (من work_days في موقع العمل)
3. leave      → إجازة منفذة
4. mission    → مهمة خارجية
5. forget     → نسيان بصمة معتمد
6. attendance → بصمة فعلية (تحليل تأخير/خروج مبكر)
7. permission → استئذان
8. excuses    → تبريرات
9. ABSENT     → غياب
```

### كيف يُحدد التأخير:
```python
work_start = "10:00"           # من موقع العمل
grace_period = 10              # فترة السماح (دقائق)
allowed_late = "10:10"         # آخر وقت مسموح

if check_in > allowed_late:
    is_late = True
    late_minutes = check_in - work_start
```

### كيف تُحدد عطلة نهاية الأسبوع:
- من حقل `work_days` في موقع العمل
- إذا `friday: false` → الجمعة عطلة
- كل موظف حسب موقع عمله

## API Endpoints المهمة

| Endpoint | الوصف |
|----------|-------|
| `POST /api/attendance/check-in` | تسجيل حضور |
| `POST /api/attendance/check-out` | تسجيل انصراف |
| `GET /api/attendance-engine/daily-status/{emp_id}/{date}` | تحليل يوم + العروق |
| `POST /api/attendance-engine/process-daily` | التحضير اليدوي |
| `GET /api/settings/version` | إصدار التطبيق |

## Test Credentials
- Admin: `stas` / `123456`
- Employee: `16` / `123456` (محمد فوزي)
- Employee: `10` / `123456` (وليد صابر)

## Prioritized Backlog

### P0 (Critical) - COMPLETED ✅
- [x] إصلاح التوقيت
- [x] إصلاح "لا يوجد عقد نشط"
- [x] شرح آلية النظام

### P1 (High)
- [ ] دمج صفحتي "ماليتي" و "الحضور/الجزاءات"
- [ ] واجهة التقييم السنوي للأداء

### P2 (Medium)
- [ ] نظام القروض
- [ ] إظهار الميزات المخفية في الواجهة
- [ ] تحسين صلاحيات المشرفين
