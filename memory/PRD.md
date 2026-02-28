# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
نظام موارد بشرية شامل لشركة دار الكود للاستشارات الهندسية

## COMPLETED: PDF Preview & Download System (28/02/2026)

### ما تم إنجازه:
- **PdfPreviewModal Component**: مكوّن مشترك لمعاينة PDF في كل التطبيق
- **زران منفصلان**: "معاينة" (لفتح modal مع iframe) + "تحميل" (لتحميل مباشر)
- **Fallback System**: إذا حُظر window.open من AdBlock، يتم التحميل المباشر
- **تم تحديث الصفحات**:
  - AttendanceManagementPage (تقرير الحضور)
  - FinancialCustodyPage (العهد المالية)
  - ContractsManagementPage (العقود)
  - TransactionDetailPage (المعاملات)
  - SettlementPage (المخالصات)

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
- Full system health check
- Verify compensation business rules

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
