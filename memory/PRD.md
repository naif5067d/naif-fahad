# HR System - نظام الموارد البشرية

## Original Problem Statement
نظام موارد بشرية شامل لشركة دار الكود للاستشارات الهندسية يشمل:
- إدارة الموظفين والعقود
- نظام المخالصات النهائية
- إدارة العهد المالية والعينية
- نظام الإجازات والحضور
- المسيرات والرواتب

## User Credentials
- **Admin/Manager:** `sultan` / `123456`
- **CEO:** `mohammed` / `123456`
- **SysAdmin:** `stas506` / `654321`
- **Accountant:** `salah` / `123456`

---

## ما تم إنجازه (Completed)

### 2026-02-25 - إصلاحات الاستدعاء وزر التعديل
- ✅ إصلاح ظهور زر التعديل للعقود النشطة للمشرفين (sultan, stas, naif)
- ✅ إضافة اسم مرسل الاستدعاء (sender_name) في إشعار الـ Dashboard
- ✅ إضافة التاريخ الهجري/الميلادي في إشعار الاستدعاء
- ✅ إنشاء endpoint جديد `/api/notifications/summons/active-for-list` لإظهار الاستدعاءات:
  - stas يرى جميع الاستدعاءات
  - باقي المشرفين يرون فقط الاستدعاءات التي أرسلوها
- ✅ عند نقر الموظف على "اطلعت" يُحذف الاستدعاء من قاعدة البيانات نهائياً
- ✅ إضافة شارة الاستدعاء في قائمة الموظفين مع عرض اسم المرسل في tooltip

### 2026-02-25 - إصلاحات المخالصات (سابقاً)
- ✅ إصلاح خطأ `selectedSettlement is not defined` في SettlementPage.js
- ✅ تحديث نص الإقرار القانوني في PDF المخالصة
- ✅ السماح بتعديل وإعادة تنفيذ المخالصات المنفذة
- ✅ إصلاح مشاكل عرض النص العربي في PDF (Amiri font)
- ✅ إضافة البيانات الديناميكية في PDF (المسمى الوظيفي، القسم، IBAN)
- ✅ حساب راتب خارج المسيرات
- ✅ تحويل المبلغ إلى كلمات عربية

### سابقاً
- ✅ نظام المخالصات الأساسي
- ✅ نظام الموظفين والعقود
- ✅ نظام العهد المالية
- ✅ نظام المصادقة والصلاحيات
- ✅ إعادة تنظيم القائمة الجانبية وصفحة لوحة التحكم
- ✅ نقل بيانات الإقامة/الهوية من الموظف إلى العقد

---

## المهام المعلقة (Backlog)

### P0 - أولوية حرجة
- [ ] إكمال إعادة هيكلة صفحة العقود (الجديدة في /pages/contracts/)

### P1 - أولوية عالية
- [ ] سير عمل العهد العينية (إعفاء / تقدير التلفيات)
- [ ] إضافة الشعار للمخالصة PDF
- [ ] تحويل التاريخ الهجري/الميلادي (utility function)

### P2 - أولوية متوسطة
- [ ] تحسين PDF العهد المالية (إطار + ترقيم)
- [ ] واجهة تعديل أسماء التوقيعات في PDF
- [ ] إصلاح التجاوب على الجوال
- [ ] إكمال tab "System Architecture" في Stas Mirror

### P3 - أولوية منخفضة
- [ ] محرر ذكي للسياسات (Canva-like)
- [ ] إدارة علامة التطبيق التجارية
- [ ] نظام صلاحيات RBAC مركزي
- [ ] إصلاح صفحة MaintenanceTrackingPage

---

## Architecture

```
/app/
├── backend/
│   ├── routes/
│   │   ├── settlement.py       # نقاط نهاية المخالصات
│   │   ├── contracts_v2.py     # إدارة العقود (العقد = مصدر الحقيقة)
│   │   ├── notifications.py    # الاستدعاءات والإشعارات
│   │   └── ...
│   └── utils/
│       └── settlement_pdf.py   # توليد PDF المخالصة
└── frontend/
    └── src/
        └── pages/
            ├── SettlementPage.js           # صفحة المخالصات
            ├── ContractsManagementPage.js  # صفحة العقود (القديمة)
            ├── DashboardPage.js            # لوحة التحكم + إشعارات الاستدعاء
            ├── EmployeesPage.js            # قائمة الموظفين + شارات الاستدعاء
            └── contracts/                  # صفحة العقود الجديدة (قيد التطوير)
```

## Key Files
- `frontend/src/pages/SettlementPage.js` - واجهة المخالصات
- `frontend/src/pages/ContractsManagementPage.js` - واجهة العقود
- `frontend/src/pages/DashboardPage.js` - لوحة التحكم مع الاستدعاءات
- `frontend/src/pages/EmployeesPage.js` - قائمة الموظفين
- `backend/routes/settlement.py` - API المخالصات
- `backend/routes/notifications.py` - API الاستدعاءات
- `backend/utils/settlement_pdf.py` - توليد PDF

## Third Party Integrations
- reportlab - توليد PDF
- qrcode - رموز QR
- arabic_reshaper, python-bidi - معالجة النص العربي
- num2words - تحويل الأرقام لكلمات
