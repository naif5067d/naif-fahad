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

### 2026-02-21
1. **إصلاح التوقيت (P0)** ✅
   - تحويل جميع أوقات الحضور من UTC إلى توقيت الرياض (+03:00)
   - تعديل `/api/attendance/admin` للعرض الصحيح

2. **إصلاح مشكلة "لا يوجد عقد نشط" (P0)** ✅
   - **السبب الجذري**: كان الكود يبحث في `contracts_v2` بشرط `is_active: True`
   - لكن العقود في قاعدة البيانات لديها `is_active: None`
   - **الإصلاح**: إزالة شرط `is_active: True` من الاستعلام
   - **الملف**: `/app/backend/utils/attendance_rules.py` (السطر 287-291)

3. **ميزة تحديث الإصدار** ✅
   - إضافة إدارة إصدار التطبيق في صفحة STAS Mirror
   - استبدال "حذف المعاملات" بـ "إدارة الإصدار"
   - API: `/api/settings/version`

### Session Fixes
- إعادة تعيين كلمات مرور الموظفين (المستخدمين 10 و 16)

## Database Schema Notes
```
contracts_v2:
  - status: "active" | "terminated" | "pending"
  - is_active: قد يكون None (لا تعتمد عليه!)
  - استخدم status: "active" للتحقق من العقد النشط
```

## API Endpoints
- `POST /api/auth/login` - تسجيل الدخول
- `POST /api/attendance/check-in` - تسجيل الحضور
- `GET /api/attendance/admin` - سجل الحضور للإدارة
- `GET /api/settings/version` - إصدار التطبيق
- `PUT /api/settings/version` - تحديث الإصدار (STAS فقط)

## Test Credentials
- Admin: `stas` / `123456`
- Employee: `16` / `123456` (محمد فوزي)
- Employee: `10` / `123456` (وليد صابر)

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- [x] إصلاح التوقيت
- [x] إصلاح "لا يوجد عقد نشط"

### P1 (High)
- [ ] دمج صفحتي "ماليتي" و "الحضور/الجزاءات"
- [ ] واجهة التقييم السنوي للأداء

### P2 (Medium)
- [ ] نظام القروض
- [ ] إظهار الميزات المخفية في الواجهة
- [ ] تحسين صلاحيات المشرفين

## Known Issues
- تحذير bcrypt في السجلات (لا يؤثر على الوظائف)
- GPS مطلوب لتسجيل الحضور (حسب التصميم)
