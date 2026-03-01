# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
نظام موارد بشرية شامل لشركة دار الكود للاستشارات الهندسية

## COMPLETED: Mobile Login Page Fix (December 2025)

### ما تم إنجازه:
- **إصلاح صفحة تسجيل الدخول للجوال**: تحسين CSS لدعم الشاشات الصغيرة
- **تحسينات**:
  - تغيير التخطيط من `flex` إلى `flex-col lg:flex-row`
  - إضافة `min-h-screen` للقسم الرئيسي
  - تقليل padding وحجم الخطوط للجوال
  - دعم أفضل لشاشات iPhone الصغيرة

### الملف:
- /app/frontend/src/pages/LoginPage.js

---

## COMPLETED: PDF Preview Modal System (December 2025)

### ما تم إنجازه:
- **PdfPreviewModal Component**: مكوّن مشترك يحل مشكلة `ERR_BLOCKED_BY_CLIENT`
- **usePdfPreview Hook**: لتسهيل الاستخدام في أي صفحة
- **حل مشكلة AdBlock**: بدلاً من `window.open` نعرض PDF في modal داخل الصفحة
- **fallback**: إذا فشل iframe يظهر زر تحميل مباشر
- **تم تحديث الصفحات**:
  - AttendanceManagementPage (تقرير الحضور)
  - FinancialCustodyPage (العهد المالية)
  - ContractsManagementPage (العقود)
  - TransactionDetailPage (المعاملات)
  - SettlementPage (المخالصات)
  - TeamAttendancePage (حضور الفريق)

### الملفات:
1. /app/frontend/src/components/PdfPreviewModal.jsx (مكوّن جديد)
2. جميع صفحات الطباعة المحدثة

---

## COMPLETED: Summon Reply Notification System (28/02/2026)

### ما تم إنجازه:
- **عرض الرد في جدول الموظفين**: يظهر نص الرد بدلاً من كلمة "رد" فقط
- **إخفاء الاستدعاء بعد القراءة**: النقر على الاستدعاء المُرد يخفيه من الجدول
- **APIs جديدة**:
  - `POST /api/notifications/summons/{id}/mark-reply-read`: تأكيد قراءة الرد
  - `DELETE /api/notifications/summons/{id}`: حذف الاستدعاء

### الملفات:
1. /app/backend/routes/notifications.py
2. /app/frontend/src/pages/EmployeesPage.js

---

## COMPLETED: Security Restrictions (28/02/2026)

### ما تم إنجازه:
- **مراقبة الأجهزة**: حصرياً لـ STAS فقط
- **الحذف النووي**: حصرياً لـ STAS فقط
- أُزيلت الصلاحيات من sultan و naif

---

## COMPLETED: Nuclear Delete Feature (28/02/2026)

### ما تم إنجازه:
- **ميزة الحذف النووي**: زر لحذف جميع البيانات المعاملاتية
- **أمان**: متاح فقط لـ STAS

---

## COMPLETED: Auto Attendance on Startup (28/02/2026)

### ما تم إنجازه:
- **التحضير التلقائي عند بدء التشغيل**: إذا فات وقت التحضير (7 صباحاً) يتم التحضير فوراً
- **الملف**: /app/backend/services/scheduler.py

---

## Prioritized Backlog

### P1 (High)
- إكمال سير عمل الاستدعاء والرد
- Full system health check

### P2 (Medium)
- Fix MaintenanceTrackingPage stability
- Refactor monolithic pages

### P3 (Future)
- In-Kind Custody Workflow
- System Architecture View in STAS Mirror

---

## Credentials
- SysAdmin: stas506 / 654321
- Admin: sultan / 123456
- CEO: mohammed / 12346
- Supervisor: nayef / 123456
