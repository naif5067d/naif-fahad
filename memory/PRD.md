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

### 2026-02-25 - إصلاحات المخالصات
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

---

## المهام المعلقة (Backlog)

### P1 - أولوية عالية
- [ ] سير عمل العهد العينية (إعفاء / تقدير التلفيات)
- [ ] إضافة الشعار للمخالصة PDF

### P2 - أولوية متوسطة
- [ ] تحسين PDF العهد المالية (إطار + ترقيم)
- [ ] واجهة تعديل أسماء التوقيعات في PDF
- [ ] إصلاح التجاوب على الجوال

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
│   │   ├── settlement.py      # نقاط نهاية المخالصات
│   │   ├── contracts.py       # إدارة العقود
│   │   └── ...
│   └── utils/
│       └── settlement_pdf.py  # توليد PDF المخالصة
└── frontend/
    └── src/
        └── pages/
            └── SettlementPage.js  # صفحة المخالصات
```

## Key Files
- `frontend/src/pages/SettlementPage.js` - واجهة المخالصات
- `backend/routes/settlement.py` - API المخالصات
- `backend/utils/settlement_pdf.py` - توليد PDF
- `backend/utils/arabic_numbers.py` - تحويل الأرقام لكلمات

## Third Party Integrations
- reportlab - توليد PDF
- qrcode - رموز QR
- arabic_reshaper, python-bidi - معالجة النص العربي
- num2words - تحويل الأرقام لكلمات
