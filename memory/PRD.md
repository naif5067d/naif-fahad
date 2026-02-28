# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
نظام موارد بشرية شامل لشركة دار الكود للاستشارات الهندسية

## COMPLETED: Nuclear Delete Feature (28/02/2026)

### ما تم إنجازه:
- **ميزة الحذف النووي**: زر لحذف جميع البيانات المعاملاتية مع الحفاظ على العقود والمستخدمين
- **Backend API**: `/api/system/nuclear-delete` و `/api/system/collections-stats`
- **نافذة تأكيد**: تعرض البيانات التي ستُحذف والبيانات المحفوظة مع عدد السجلات
- **أمان**: متاح فقط لـ stas و sultan
- **تأكيد**: يتطلب كتابة "حذف نهائي" للتنفيذ
- **استجابة للجوال**: تعمل بشكل صحيح على جميع الشاشات

### الملفات:
1. /app/backend/routes/system.py (API الحذف النووي)
2. /app/frontend/src/pages/TransactionsPage.js (الزر والنافذة)

---

## COMPLETED: Mobile Responsiveness Overhaul (28/02/2026)

### ما تم إنجازه:

#### 1. دعم Safe Area لجميع أجهزة iPhone:
- iPhone SE (375x667) - بدون notch
- iPhone X, XS, 11 Pro (375x812) - notch 44pt
- iPhone XR, 11 (414x896) - notch 48pt
- iPhone 12/13 mini (360x780) - notch 50pt
- iPhone 12, 13, 14 (390x844) - notch 47pt
- iPhone 12/13/14 Pro (393x852) - Dynamic Island 59pt
- iPhone 14 Pro Max, 15 Pro Max (430x932) - Dynamic Island 59pt

#### 2. دعم أجهزة Android:
- Samsung Galaxy S21/S22/S23/S24 series
- Samsung Galaxy A series
- Samsung Galaxy Fold/Z Flip
- Huawei P30/P40/P50, Mate 40/50, Nova
- Xiaomi Mi 11/12/13, Redmi Note, Poco
- OnePlus 9/10/11, Oppo Find X, Realme
- Google Pixel 6/7/8, Pixel Fold
- Vivo X series, Sony Xperia

#### 3. دعم Tablets:
- iPad Mini, Air, Pro 11", Pro 12.9"
- Samsung Galaxy Tab S7/S8/S9
- Huawei MatePad

#### 4. تحسينات الواجهة:
- جميع الأزرار 44x44px (Apple HIG compliant)
- الجداول قابلة للتمرير الأفقي
- التبويبات قابلة للتمرير الأفقي
- Safe Area للهيدر
- Safe Area للـ Bottom Nav

### الملفات:
1. /app/frontend/src/styles/mobile.css (1150+ سطر)
2. /app/frontend/public/index.html (Safe Area CSS)
3. /app/frontend/src/components/layout/AppLayout.js
4. /app/frontend/src/components/NotificationBell.js

---

## Previous Completed Features

### Advanced Security Command Center (27/02/2026)
- مركز قيادة الأمان المتقدم
- كشف التلاعب
- تعطيل حسابات متعددة
- سجل الأمان المفصل

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
- Canva-like Smart Editor for Policies

---

## Credentials
- SysAdmin: stas506 / 654321
- Admin: sultan / 123456
- CEO: mohammed / 12346
- Supervisor: nayef / 123456
