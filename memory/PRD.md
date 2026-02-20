# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Mobile-first, enterprise-grade HR operating system for Dar Al Code engineering consultancy. Strict RBAC, immutable transactions, Arabic-first UI.

## Core Rule
Any transaction not executed by STAS is not considered valid.

## Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Map:** react-leaflet + OpenStreetMap

## Design System
- **Colors:** 
  - Navy: #1E3A5F (primary)
  - Black: #0A0A0B (text)
  - Gray: #6B7280 (muted)
  - Lavender: #A78BFA (accent)
- **Fonts:** Manrope (English), IBM Plex Sans Arabic (Arabic)
- **Components:** Gradient hero cards, card-based layouts, bottom mobile nav
- **Timezone:** Asia/Riyadh (UTC+3) for all date/time display

## Roles
stas, mohammed (CEO), sultan, naif, salah, supervisor1, employee1/2

## Implemented Features

### Phase 1-3: Core + UI ✅
### Phase 4: P0 Business Logic ✅ (Escalation, Tangible Custody)
### Phase 5: Financial Custody V2 ✅
### Phase 6: UI/UX Overhaul ✅
### Phase 7: Map Feature & Language Fix ✅
### Phase 8: Complete UI/UX Redesign ✅
### Phase 9: PDF & Transactions Enhancement ✅
### Phase 10: Company Settings & Workflow Fix ✅
### Phase 11: PDF Arabic Text Fix & STAS Execution Flow ✅
### Phase 12: Bilingual PDF Complete Fix ✅ (2026-02-14)
### Phase 13: System Maintenance Module ✅ (2026-02-14)
### Phase 14: System Maintenance V2 + Date Format Audit ✅ (2026-02-14)

### Phase 16: Settlement System Complete (نظام المخالصة) ✅ (2026-02-17)

**المتطلبات المُنفذة:**

1. **حقول البنك والآيبان (Bank & IBAN Fields):**
   - `bank_name`: اسم البنك (إلزامي للمخالصة)
   - `bank_iban`: رقم الآيبان (IBAN)
   - قابلة للتعديل في أي وقت
   - تظهر في نموذج العقد ومعاينة المخالصة

2. **حساب آخر راتب (Last Wage):**
   ```
   آخر راتب = الأساسي + السكن + النقل + طبيعة العمل + بدلات أخرى
   ```
   - **لا** يعتمد على الأساسي فقط
   - يُستخدم في جميع حسابات المخالصة

3. **حساب مكافأة نهاية الخدمة (EOS) - نظام العمل السعودي:**
   - أقل من 5 سنوات: `0.5 × الراتب × السنوات`
   - 5+ سنوات: `(0.5 × 5) + (1 × الباقي)`
   - **نسب الاستقالة:**
     - < 2 سنوات: 0%
     - 2-5 سنوات: 33%
     - 5-10 سنوات: 66%
     - 10+ سنوات: 100%
   - **إنهاء العقد/اتفاق طرفين/وفاة:** 100%
   - **إنهاء خلال التجربة:** 0%

4. **حساب بدل الإجازات (Leave Compensation):**
   ```
   بدل الإجازات = رصيد الإجازة × (آخر راتب ÷ 30)
   ```
   - الرصيد محسوب Pro-Rata يومي:
     ```
     (سياسة الإجازة / 365) × أيام الخدمة - المستخدم
     ```

5. **أنواع إنهاء الخدمة:**
   - `contract_expiry`: انتهاء العقد
   - `resignation`: استقالة
   - `probation_termination`: إنهاء خلال التجربة
   - `mutual_agreement`: اتفاق طرفين
   - `termination`: إنهاء من الشركة

6. **دورة حياة المخالصة:**
   ```
   إنشاء (Sultan/Naif) → معاينة Preview → pending_stas → تنفيذ (STAS) → executed
   ```
   - التنفيذ مرة واحدة فقط
   - بعد التنفيذ: قفل الحساب + إغلاق العقد

7. **بعد تنفيذ المخالصة:**
   - إغلاق العقد (status: closed)
   - قفل حساب الموظف (is_active: false)
   - تسجيل جميع العمليات في finance_ledger
   - حفظ Snapshot كامل

**الملفات الجديدة:**
- `/app/backend/routes/settlement.py` - Settlement API
- `/app/backend/routes/deductions.py` - Deductions/Bonuses API
- `/app/backend/services/service_calculator.py` - EOS, Leave, Wage calculations
- `/app/frontend/src/pages/SettlementPage.js` - واجهة المخالصات

**APIs الجديدة:**
- `GET /api/settlement` - قائمة المخالصات
- `GET /api/settlement/termination-types` - أنواع الإنهاء
- `POST /api/settlement/preview` - معاينة حسابات المخالصة
- `POST /api/settlement` - إنشاء طلب مخالصة
- `POST /api/settlement/{id}/execute` - تنفيذ المخالصة (STAS)
- `POST /api/settlement/{id}/cancel` - إلغاء المخالصة
- `GET /api/settlement/{id}/pdf` - PDF المخالصة
- `GET /api/deductions` - قائمة الخصومات/المكافآت
- `POST /api/deductions` - إنشاء خصم/مكافأة
- `POST /api/deductions/{id}/action` - تنفيذ/رفض (STAS)

**Testing:** 100% pass rate (17/17 backend tests, all frontend features verified)

### Phase 16.1: Settlement PDF Enhancements ✅ (2026-02-17)

**إصلاحات PDF المخالصة:**

1. **شعار الشركة (Company Logo):**
   - يُجلب من `branding['logo_data']` (base64 stored in settings)
   - يُحول من RGBA إلى RGB للتوافق مع PDF
   - يظهر في الترويسة بحجم 20×20mm
   - **ملف:** `backend/utils/settlement_pdf.py` - دالة `create_company_logo()`

2. **نص التعهد الكامل (Full Declaration Text):**
   - عنوان: "الإقرار والتعهد / Declaration / Acknowledgment"
   - النص العربي: "أقر أنا الموقع أدناه بأنني استلمت كافة مستحقاتي من شركة دار الكود للاستشارات الهندسية حسب البيانات المذكورة أعلاه، وهذا المبلغ شامل كافة مستحقاتي المالية حتى تاريخه، وتُعتبر هذه بمثابة براءة ذمة للشركة ولا يحق لي المطالبة بأية مستحقات لاحقة."
   - النص الإنجليزي: "I, the undersigned, confirm that I have received all my entitlements from Dar Al Code Engineering Consultancy according to the above details. This amount includes all my financial dues up to this date and represents a full release of liability for the company."

3. **رموز التوقيعات (Signatures Section):**
   - 3 QR codes: STAS, CEO, HR
   - 1 Barcode: لرقم المعاملة
   - فراغ توقيع الموظف اليدوي

**Testing:** 100% pass rate (10/10 PDF tests)
- `/app/backend/tests/test_settlement_pdf.py` - ملف الاختبارات

---

### Phase 18: Professional Dashboard & Notification Bell System ✅ (2026-02-18)

**الميزات المُنفذة:**

1. **بطاقة الموظف الاحترافية (Premium Employee Card):**
   - تصميم داكن متدرج احترافي
   - صورة الموظف مع مؤشر الحالة (نشط/غير نشط)
   - رسالة ترحيب "مرحباً بك" مع اسم المستخدم
   - 4 إحصائيات سريعة: رصيد الإجازة | ساعات الشهر | حالة اليوم | المعاملات المعلقة
   - شارة سنوات الخدمة
   - تاريخ انتهاء العقد
   - **قسم الإجراءات والخصومات:** يظهر الخصومات والإنذارات والتأخيرات للموظف

2. **نظام الجرس الشامل (Notification Bell):**
   - جرس في Header لجميع المستخدمين
   - شارة عدد الإشعارات غير المقروءة
   - قائمة منسدلة بالإشعارات مع:
     - أيقونات ملونة حسب نوع الإشعار
     - الوقت النسبي (منذ دقيقة، منذ ساعة، الخ)
     - زر تحديد كمقروء
     - زر "تم رؤية الجميع"
   - **صوت تنبيه** عند وصول إشعار جديد
   - تحديث تلقائي كل 30 ثانية
   - تحديث فوري عند تبديل المستخدم

3. **أنواع الإشعارات المدعومة:**
   | للموظف | للإدارة |
   |--------|---------|
   | معاملة مقبولة/مرفوضة | معاملة بانتظار الموافقة |
   | تم تنفيذ الطلب | عقد ينتهي قريباً |
   | خصم جديد | مقترح خصم يحتاج مراجعة |
   | إنذار جديد | موظف تأخر/غاب |
   | تسجيل تأخير | - |

4. **Backend APIs الجديدة:**
   - `GET /api/notifications/bell` - جلب جميع الإشعارات للجرس
   - `GET /api/notifications/my` - إشعارات المستخدم الحالي
   - `GET /api/notifications/unread-count` - عدد غير المقروءة
   - `PATCH /api/notifications/{id}/read` - تحديد كمقروء
   - `POST /api/notifications/mark-all-read` - تحديد الكل كمقروء
   - `DELETE /api/notifications/{id}` - حذف إشعار

**الملفات الجديدة:**
- `/app/backend/models/notifications.py` - نموذج الإشعارات
- `/app/backend/services/notification_service.py` - خدمة الإشعارات
- `/app/frontend/src/components/NotificationBell.js` - مكون الجرس

**الملفات المُحدثة:**
- `/app/backend/routes/notifications.py` - إضافة APIs الجديدة
- `/app/backend/routes/employees.py` - تحديث summary لإرجاع الخصومات
- `/app/frontend/src/pages/DashboardPage.js` - بطاقة الموظف الجديدة
- `/app/frontend/src/components/layout/AppLayout.js` - إضافة الجرس

**Testing:** ✅ Working - All features verified via screenshots

---

### Phase 17: Employee Card, Notifications & Leave Carryover ✅ (2026-02-17)

**الميزات المُنفذة:**

1. **بطاقة الموظف (Employee Card):**
   - **Preview Dialog**: يظهر من صفحة الموظفين بالضغط على أيقونة المستخدم
   - **صفحة Profile الكاملة**: `/employees/{employeeId}` مع:
     - Hero section بمعلومات الموظف
     - المعلومات الشخصية (البريد، الهاتف، الرقم الوطني)
     - معلومات العقد (رقم العقد، تاريخ البدء/الانتهاء، الحالة)
     - معلومات الخدمة (مدة الخدمة بالسنوات والأيام)
     - رصيد الإجازات مع زر الترحيل
     - حالة الحضور اليومي
     - الراتب والبدلات (للمدراء فقط)
     - معلومات البنك (للمدراء فقط)
   - **Files**: `frontend/src/pages/EmployeeProfilePage.js`

2. **إشعارات العقود المنتهية (Contract Expiry Notifications):**
   - **Dashboard**: قسم خاص للعقود المنتهية خلال 3 أشهر
   - **Bell Icon**: في Header للمدراء فقط (Sultan/Naif/STAS)
   - **Employee Row**: الموظف الذي ينتهي عقده أحمر ومضيء
   - **مستويات الإلحاح**: Critical (≤30 يوم) / High (≤60) / Medium (≤90)
   - **APIs**:
     - `GET /api/notifications/expiring-contracts`
     - `GET /api/notifications/header-alerts`
   - **Files**: `backend/routes/notifications.py`, `frontend/src/components/layout/AppLayout.js`

3. **ترحيل الإجازات (Leave Carryover):**
   - متاح لـ: Sultan, Naif, STAS (جميعهم مباشرة بدون موافقات)
   - من صفحة Profile الموظف → زر "ترحيل"
   - التحقق من عدم تجاوز الرصيد الحالي
   - تسجيل في audit log
   - **API**: `POST /api/notifications/leave-carryover`

**Testing:** 100% pass rate (12/12 backend tests, all frontend features working)
- `/app/backend/tests/test_iteration27_notifications.py`

---

### Phase 15: PDF Arabic Text - Guaranteed Fix ✅ (2026-02-17)

**P0 Critical Fix - Arabic Text & Date Formatting in PDF:**
- **Root Cause:** ReportLab's `wordWrap='RTL'` was being applied to ALL text including dates and reference numbers, causing the `-` dashes to be invisible
- **Solution:** Implemented dual-font approach in `backend/utils/pdf.py`:
  - **Arabic text:** Uses `NotoNaskhArabic` font with `wordWrap='RTL'` and `arabic_reshaper` + `bidi` for proper RTL display
  - **LTR text (dates, numbers, English):** Uses `Helvetica` font with `wordWrap='LTR'` - critical for displaying dashes in dates like `2026-02-17`
  - **New helper function:** `make_ltr_para()` creates Helvetica paragraphs for dates, ref numbers, and English text
- **Files Modified:**
  - `backend/utils/pdf.py` - Complete rewrite of PDF generation logic
- **Verified Results:**
  - Arabic PDF: ✅ Company name, employee names, leave types display correctly
  - English PDF: ✅ All labels and content display properly
  - Date Format: ✅ `2026-02-17` with dashes (not `20260217`)
  - Ref Number: ✅ `TXN-2026-0001` with dashes (not `20260001`)
  - QR/Barcode: ✅ Approval signatures display correctly

**Testing:** 100% pass rate (8/8 backend tests, all frontend features verified)

**IMPORTANT RULE (من هنا للأبد):**
- أي Collection جديدة يجب إضافتها في `/app/backend/routes/maintenance.py`
- في `TRANSACTION_COLLECTIONS` (قابلة للحذف) أو `PROTECTED_COLLECTIONS` (محمية)
- هذا يضمن شمولية الأرشفة والحذف

## Key API Endpoints
- `/api/financial-custody/*` - Full custody lifecycle
- `/api/custody/tangible/*` - Tangible custody
- `/api/transactions/*/action` - approve/reject/escalate/return_to_sultan/return_to_ceo
- `/api/transactions/{id}/pdf?lang=ar|en` - Bilingual PDF generation
- `/api/leave/holidays` - CRUD for holidays
- `/api/attendance/admin?period=daily|weekly|monthly|yearly` - Admin view
- `/api/finance/codes/*` - Code CRUD
- `/api/dashboard/next-holiday` - Next upcoming holiday
- `/api/work-locations` - Work location CRUD
- `/api/settings/branding` - Company branding (GET/PUT/POST logo/DELETE logo)
- `/api/stas/pending` - Get pending transactions for STAS
- `/api/stas/mirror/{id}` - Get mirror data for transaction
- `/api/stas/execute/{id}` - Execute transaction
- `/api/maintenance/storage-info` - Storage statistics with total_size_kb
- `/api/maintenance/archive-full` - Create full system archive
- `/api/maintenance/archives` - List/manage archives
- `/api/maintenance/archives/upload` - **NEW** Upload & restore from JSON file
- `/api/maintenance/purge-all-transactions` - Delete all transactions
- `/api/maintenance/logs` - Maintenance operation logs

## Collections

### Transaction Collections (قابلة للحذف):
```
transactions, leave_ledger, finance_ledger, attendance_ledger, 
custody_ledger, custody_financial, warning_ledger, asset_ledger
```

### Protected Collections (محمية):
```
users, employees, contracts, contracts_v2, contract_snapshots, contract_audit_log,
finance_codes, public_holidays, holidays, work_locations, settings, counters
```

### System Collections:
```
system_archives, maintenance_log
```

## Completed Bug Fixes (Phase 12)
1. ✅ PDF English Version - No longer blank
2. ✅ PDF Arabic Version - Proper RTL text rendering
3. ✅ PDF Company Branding - Logo and name displayed in header
4. ✅ PDF STAS Signature - Uses Code128 barcode (not QR code)
5. ✅ STAS Workflow - Can execute transactions after return flow
6. ✅ Cancel Transaction - Does not trigger business logic (no leave deduction)

### Phase 15: Contract System V2 (نظام العقود الشامل) ✅ (2026-02-14)

**المتطلبات المُنفذة:**

1. **نموذج العقد الجديد (Contract Model):**
   - `contract_serial`: ترقيم DAC-YYYY-XXX (مثال: DAC-2026-001)
   - `version`: رقم الإصدار
   - `contract_category`: employment | internship_unpaid
   - `employment_type`: unlimited | fixed_term | trial_paid
   - `status`: draft | pending_stas | active | terminated | closed
   - `is_migrated`: للموظفين القدامى
   - `leave_opening_balance`: رصيد إجازات افتتاحي

2. **ترقيم العقود (Serial Generation):**
   - صيغة DAC-YYYY-XXX
   - يتزايد تلقائياً
   - يُعاد الضبط مع بداية كل سنة
   - البحث يدعم: رقم العقد، آخر 3 أرقام، كود الموظف، اسم الموظف

3. **دورة حياة العقد (Lifecycle):**
   ```
   draft → pending_stas → active → terminated → closed
   ```
   - التنفيذ إلى "active" حصرياً من STAS
   - الإنهاء إلى "terminated" حصرياً من STAS
   - الإغلاق "closed" بعد المخالصة

4. **الصلاحيات:**
   - Sultan/Naif: إنشاء + تعديل + إرسال لـ STAS
   - STAS: كل شيء (إنشاء + تعديل + تنفيذ + إنهاء)

5. **عند تنفيذ العقد:**
   - التحقق من عدم وجود عقد نشط آخر
   - إنشاء User إذا لم يكن موجوداً
   - تفعيل صلاحية الحضور
   - بدء احتساب الإجازات من start_date
   - إضافة leave_opening_balance للمُهاجرين
   - إنشاء Audit Log + Snapshot

6. **قواعد التفعيل:**
   - لا حضور أو طلبات بدون عقد نشط
   - لا يُسمح بأكثر من عقد نشط لموظف واحد
   - لا تعديل على عقد منفذ (فقط Version جديد)
   - لا حذف لعقد منفذ

7. **قالب PDF:**
   - قالب Placeholder جاهز
   - يدعم المتغيرات الديناميكية
   - Snapshot غير قابل للتعديل عند التنفيذ

**الملفات الجديدة:**
- `/app/backend/services/contract_service.py` - Business Logic Layer
- `/app/backend/services/contract_template.py` - PDF Template Engine
- `/app/backend/routes/contracts_v2.py` - API Endpoints
- `/app/frontend/src/pages/ContractsManagementPage.js` - واجهة إدارة العقود

**APIs الجديدة:**
- `GET /api/contracts-v2` - قائمة العقود
- `POST /api/contracts-v2` - إنشاء عقد جديد
- `PUT /api/contracts-v2/{id}` - تعديل عقد
- `DELETE /api/contracts-v2/{id}` - حذف عقد (draft/pending فقط)
- `POST /api/contracts-v2/{id}/submit` - إرسال لـ STAS
- `POST /api/contracts-v2/{id}/execute` - تنفيذ (STAS)
- `POST /api/contracts-v2/{id}/terminate` - إنهاء (STAS)
- `GET /api/contracts-v2/{id}/pdf` - PDF العقد
- `GET /api/contracts-v2/stats/summary` - إحصائيات

## Remaining Tasks

### P0 (Priority 0) - COMPLETED ✅

### P1 (Priority 1) - Next Phase
- **نظام الخصومات والمكافآت الكامل:**
  - واجهة إدخال الخصم والمكافأة
  - سلسلة الموافقات: Sultan → STAS → تنفيذ
  - الربط بالمخالصة تلقائياً
- CEO Dashboard - Escalated transactions view

### P2 (Priority 2)
- نظام الحضور والانصراف المحسّن (Present/Absent/On Leave/Permission)
- New Transaction Types (leave/attendance subtypes)
- STAS Financial Custody Mirror
- Geofencing enforcement
- نظام الإنذارات والجزاءات
- نظام السلف وتتبع الأقساط

---

## Phase 16: Core HR Logic & Settlement Foundation ✅ (2026-02-15)

**المتطلبات المُنفذة:**

### 1️⃣ تثبيت نظام العقود (Service Calculator)
- **ملف جديد:** `backend/services/service_calculator.py`
- **حساب مدة الخدمة:**
  - يعتمد على `start_date` من العقد + `termination_date` أو تاريخ اليوم
  - 365 يوم = سنة واحدة
  - دعم كسور السنة بدقة 4 خانات عشرية
  - لا يتم تخزين - يُحسب ديناميكياً
- **حساب الأجر:**
  - `basic_only` أو `basic_plus_fixed` حسب `wage_definition`
- **حساب مكافأة نهاية الخدمة (EOS):**
  - ≤5 سنوات: 0.5 × الأجر × عدد السنوات
  - >5 سنوات: (0.5 × 5) + (1 × الباقي)
  - نسب الاستقالة: 0% (<2 سنة) / 33% (2-5) / 66% (5-10) / 100% (10+)
  - المعادلات مكتوبة في النتيجة

### 2️⃣ نظام الإجازات 21/30
- **ملف جديد:** `backend/services/leave_service.py`
- **الإجازة السنوية:**
  - أقل من 5 سنوات = 21 يوم
  - 5 سنوات فأكثر = 30 يوم
  - الرصيد يُحسب من `leave_ledger` فقط (credits - debits)
  - لا يوجد رصيد مخزن يدوي
- **الإجازة المرضية 30/60/30:**
  - 30 يوم 100%
  - 60 يوم 75%
  - 30 يوم بدون أجر
  - تُحسب تراكمياً خلال 12 شهر متحركة
- **الإجازات الخاصة:**
  - زواج (5 أيام)، وفاة (5 أيام)، أمومة (70 يوم)، أبوة (3 أيام)، اختبار، بدون أجر

### 3️⃣ الحضور والانضباط
- **ملف جديد:** `backend/services/attendance_service.py`
- **حساب الغياب التلقائي:**
  - نهاية كل يوم: من لم يسجل دخول ولا عنده إجازة = غياب
  - يُسجل في `attendance_ledger` بـ `type: "absence"`
- **أنواع السجلات:**
  - `check_in`, `check_out`, `absence`, `late`, `early_leave`
- **التعديل اليدوي:**
  - مع `audit_log` في نفس السجل
- **رمضان:**
  - زر تفعيل/إلغاء من STAS
  - 6 ساعات عمل
  - تواريخ من/إلى

### 4️⃣ طلبات الحضور منفصلة
- **أنواع طلبات الحضور:**
  - نسيان بصمة (`forget_checkin`)
  - مهمة خارجية (`field_work`)
  - خروج مبكر (`early_leave_request`)
  - تبرير تأخير (`late_excuse`)
- **تظهر في قسم الحضور فقط** - لا تظهر في قائمة الطلبات العامة

### 5️⃣ مرآة STAS الشاملة
- **ملف جديد:** `backend/services/stas_mirror_service.py`
- **Pre-Checks لكل نوع معاملة:**
  - PASS / FAIL / WARN
  - FAIL يمنع التنفيذ
  - WARN تحذير فقط مع تسجيله
- **بيانات المرآة:**
  - العقد ومدة الخدمة والأجر
  - رصيد الإجازات قبل وبعد
  - الغياب غير المسوى
  - العهد النشطة
  - السلف غير المسددة
  - المعادلات الحسابية مكتوبة
- **آلية القرار:**
  - تنفيذ (PASS كامل)
  - إرجاع (مرة واحدة فقط)
  - إلغاء

### 6️⃣ محرك المخالصة (Settlement Engine)
- **ملف جديد:** `backend/services/settlement_service.py`
- **Validator:** التحقق من شروط المخالصة
  - FAIL: عقد غير منتهي، عهد نشطة
  - WARN: سلف، غياب، جزاءات
- **Aggregator:** تجميع البيانات
  - من `contracts_v2`, `leave_ledger`, `attendance_ledger`, `finance_ledger`, `custody_ledger`
- **Snapshot:**
  - يُنشأ عند رفع طلب المخالصة
  - لا يتغير بعد إنشائه
  - التنفيذ يعتمد عليه فقط
- **حساب المخالصة:**
  - مكافأة نهاية الخدمة
  - بدل الإجازات
  - الاستقطاعات (سلف، غياب، جزاءات)
  - الصافي النهائي

### 7️⃣ تعيين المشرف
- **Endpoint جديد:** `PUT /api/employees/{id}/supervisor`
- الطلبات تمر للمشرف أولاً

### 8️⃣ صفحة الحضور المحدثة
- **بطاقات ملخص الفريق:** حاضر، غائب، إجازة، متأخر
- **زر رمضان:** تفعيل/إلغاء من STAS
- **زر إظهار الخريطة:** تفعيل/إلغاء من STAS
- **زر حساب الغياب:** تشغيل يدوي
- **جدول محسن:** عمود الحالة + عمود الإجراء
- **قسم طلبات الحضور:** منفصل عن الإجازات

### 9️⃣ ملخص الموظف الشامل
- **Endpoint جديد:** `GET /api/employees/{id}/summary`
- العقد الحالي، المشرف، رصيد الإجازات، نسبة الاستهلاك
- حالة الحضور، الغياب، الخصومات، آخر حركة مالية

**الملفات الجديدة:**
```
backend/services/
├── service_calculator.py     # حساب مدة الخدمة و EOS
├── leave_service.py          # منطق الإجازات 21/30
├── attendance_service.py     # الغياب التلقائي + رمضان
├── settlement_service.py     # محرك المخالصة
└── stas_mirror_service.py    # مرآة STAS الشاملة
```

**الملفات المُعدّلة:**
```
backend/routes/stas.py        # Pre-checks من Service Layer + إرجاع مرة واحدة + رمضان
backend/routes/employees.py   # تعيين المشرف + ملخص الموظف
frontend/src/pages/AttendancePage.js  # واجهة محدثة بالكامل
```

**APIs الجديدة:**
```
GET  /api/stas/ramadan                    # إعدادات رمضان
POST /api/stas/ramadan/activate           # تفعيل رمضان
POST /api/stas/ramadan/deactivate         # إلغاء رمضان
POST /api/stas/attendance/calculate-daily # حساب الغياب يدوياً
GET  /api/stas/settings/map-visibility    # إظهار الخريطة
POST /api/stas/settings/map-visibility    # تحديث إظهار الخريطة
POST /api/stas/return/{id}                # إرجاع المعاملة (مرة واحدة)
PUT  /api/employees/{id}/supervisor       # تعيين المشرف
GET  /api/employees/{id}/summary          # ملخص شامل
```

---

## Key Files
- `/app/backend/utils/pdf.py` - PDF generator with bilingual support (FIXED)
- `/app/backend/utils/workflow.py` - validate_stage_actor (STAS excluded from already_acted)
- `/app/backend/routes/transactions.py` - PDF endpoint with branding fetch
- `/app/backend/routes/stas.py` - STAS execution with branding fetch
- `/app/backend/routes/maintenance.py` - System maintenance APIs (Phase 14)
- `/app/backend/routes/contracts_v2.py` - Contract System V2 (Phase 15)
- `/app/backend/services/contract_service.py` - Contract business logic (Phase 15)
- `/app/frontend/src/pages/CompanySettingsPage.js` - Company settings UI
- `/app/frontend/src/pages/SystemMaintenancePage.js` - System maintenance UI (Phase 14)
- `/app/frontend/src/pages/ContractsManagementPage.js` - Contract management UI (Phase 15)
- `/app/frontend/src/lib/dateUtils.js` - Date formatting utilities with Gregorian/Hijri support

## Test Reports
- `/app/test_reports/iteration_15.json` - Latest test results (100% pass - Phase 15 Contract System V2)
- `/app/backend/tests/test_contracts_v2.py` - Backend tests for contract system (23 tests)

## Technical Notes

### PDF Generation
The `generate_transaction_pdf` function now accepts an optional `branding` parameter:
```python
def generate_transaction_pdf(transaction: dict, employee: dict = None, lang: str = 'ar', branding: dict = None) -> tuple:
```

The branding dict should contain:
- `company_name_en` / `company_name_ar`
- `slogan_en` / `slogan_ar`
- `logo_data` (base64 encoded image)

### Bilingual Text Handling
```python
def format_text_bilingual(text, target_lang='ar'):
    # Arabic text: apply reshaper + bidi
    # English text: return as-is
    # Mixed: process Arabic parts only
```

### STAS Workflow
STAS is exempted from the "already acted" check in `validate_stage_actor()`:
```python
if actor_role == 'stas':
    return {"valid": True, "stage": current_stage}
```

### Date Formatting (Phase 14)
All dates use dual calendar format - Gregorian primary + Hijri secondary:
```javascript
import { formatGregorianHijri, formatGregorianHijriDateTime } from '@/lib/dateUtils';

// Usage
const { primary, secondary, combined } = formatGregorianHijri(date);
// combined: "21/02/2026 (09/04/1447 AH هـ)"

// With time
const { combined } = formatGregorianHijriDateTime(timestamp);
// combined: "21/02/2026, 14:30 (09/04/1447 AH هـ)"
```

### Contract System V2 (Phase 15)
Contract serial format: DAC-YYYY-XXX
```python
# Serial generation
contract_serial = f"DAC-{current_year}-{seq:03d}"  # DAC-2026-001

# Lifecycle transitions
draft → pending_stas → active → terminated → closed

# Role permissions
Sultan/Naif: create, edit, submit
STAS: create, edit, submit, execute, terminate, close
```

Contract activation flow:
1. Validate no other active contract
2. Create User if not exists
3. Activate employee
4. Initialize leave balance (standard or opening balance for migrated)
5. Create audit log
6. Generate PDF snapshot

---

### Phase 16: Bug Fixes & Service Layer Enhancement ✅ (2026-02-15)

**Completed Bug Fixes:**
1. **A) Timezone** ✅ - All times display in Asia/Riyadh format using `formatSaudiTime()`
2. **B) Ramadan Mode** ✅ - Now accepts `work_start` and `work_end` parameters for custom working hours
3. **C) Map Visibility** ✅ - Added public endpoint `/api/stas/settings/map-visibility/public` accessible by all users
4. **D) Sultan Self-Request** ✅ - Added `should_escalate_to_ceo()` function; sultan's self-requests skip ops and go to CEO
5. **E) Supervisor Assignment** ✅ - Full UI dialog with supervisor selection dropdown in EmployeesPage
6. **G) STAS Mirror** ✅ - Pre-checks correctly show PASS for active contracts, FAIL for terminated

**New Endpoints:**
- `POST /api/stas/ramadan/activate` with `work_start` and `work_end` parameters
- `GET /api/stas/settings/map-visibility/public` (accessible by all authenticated users)
- `PUT /api/employees/{id}/supervisor` with `supervisor_id: null` support for removal

**Service Layer Functions Updated:**
- `attendance_service.py`: `check_late_arrival()`, `check_early_leave()` now use `get_working_hours_for_date()`
- `workflow.py`: Added `should_escalate_to_ceo()` for self-request detection
- `stas_mirror_service.py`: `build_leave_checks()` correctly verifies active contracts

**Test Report:** `/app/test_reports/iteration_17.json` - All tests passed

---

### Phase 17: Critical Bug Fixes - UI/UX Standardization ✅ (2026-02-15)

**إصلاحات P0 الحرجة:**

1. **رؤية الخريطة للموظفين** ✅
   - `AttendancePage.js` الآن يعرض رسالة "موقعك على الخريطة متاح للمشرفين" لجميع المستخدمين عند تفعيل الخريطة
   - يجلب الإعداد من `/api/stas/settings/map-visibility/public`

2. **توحيد اللغة العربية** ✅
   - تغيير اللغة الافتراضية من 'en' إلى 'ar' في `LanguageContext.js`
   - جميع عناصر الواجهة بالعربية: القوائم، الأزرار، الحالات، المراحل
   - صفحة المعاملات `TransactionsPage.js` أعيد كتابتها بالكامل بالعربية

3. **توحيد تنسيق التاريخ** ✅
   - التنسيق الموحد: DD/MM/YYYY, HH:MM بتوقيت الرياض
   - `formatGregorianHijri()` تُرجع التاريخ الميلادي فقط (بدون هجري)
   - إضافة `formatStandardDateTime()` و `formatStandardDate()` للاستخدام الموحد

4. **أزرار الإجراءات لجميع المعاملات** ✅
   - أزرار "موافقة" و "رفض" تظهر للمستخدمين المخولين حسب المرحلة
   - طلبات الحضور (`forget_checkin`, `late_excuse`, etc.) لها نفس أزرار باقي المعاملات
   - زر "تصعيد" للعمليات

5. **إعادة بناء منطق الإجازات** ✅
   - 6 أنواع إجازات:
     - **السنوية**: 21 يوم (أقل من 5 سنوات) / 30 يوم (5+ سنوات) - الرصيد الوحيد المتتبع
     - **المرضية**: عداد تراكمي (30 يوم 100% + 60 يوم 75% + 30 يوم بدون راتب)
     - **الزواج**: 5 أيام مدفوعة - مرة واحدة
     - **الوفاة**: 5 أيام مدفوعة
     - **الاختبار**: حسب الإثبات - مدفوعة
     - **بدون راتب**: لا أجر ولا خصم من السنوية
   - `leave_service.py` أُعيد كتابته بالكامل مع:
     - `get_annual_leave_balance()` - حساب رصيد السنوية فقط
     - `get_sick_leave_usage_12_months()` - عداد المرضية
     - `validate_leave_request()` - التحقق من صحة الطلب
     - `get_employee_leave_summary()` - ملخص شامل للموظف

6. **مسار سير عمل سلطان** ✅
   - طلبات سلطان الذاتية: sultan → CEO → STAS (تتجاوز ops)
   - `build_workflow_with_ceo_escalation()` يُرجع `['ceo', 'stas']`
   - بعد موافقة CEO يذهب مباشرة إلى STAS

**الملفات المُحدّثة:**
- `/app/frontend/src/pages/AttendancePage.js` - إعادة كتابة كاملة
- `/app/frontend/src/pages/TransactionsPage.js` - إعادة كتابة كاملة
- `/app/frontend/src/lib/dateUtils.js` - توحيد التنسيق
- `/app/frontend/src/contexts/LanguageContext.js` - اللغة الافتراضية عربية
- `/app/backend/services/leave_service.py` - إعادة كتابة كاملة
- `/app/backend/utils/workflow.py` - إضافة أنواع طلبات الحضور + تصعيد CEO
- `/app/backend/routes/leave.py` - 6 أنواع إجازات

**تقرير الاختبار:** `/app/test_reports/iteration_18.json` - 100% نجاح

---

## Next Tasks (P0)

### Settlement Module (المخالصة)
- واجهة طلب المخالصة
- Data Snapshot في مرآة STAS
- حساب مستحقات نهاية الخدمة (EOS)
- بدل الإجازات المتبقية

---

## Future Tasks

### P1: CEO Dashboard + Employee Profile Card
- لوحة تحكم خاصة بالمدير التنفيذي
- بطاقة ملخص الموظف

### P2: Warnings & Loans Modules
- نظام الإنذارات
- نظام السلف

---

Version: 23.1 (2026-02-17)

---

### Phase 23.1: Contract Edit & STAS Mirror Fixes ✅ (2026-02-17)

**التعديلات:**

1. **تعديل العقود النشطة** - sultan, naif, stas يمكنهم الآن تعديل العقود النشطة
2. **سياسة الإجازة السنوية** - إضافة حقل `annual_policy_days` (21 أو 30) في نموذج العقد
3. **STAS Mirror** - تحسين عرض Before/After مع ترجمة المفاتيح
4. **الحالات** - `pending_ceo` يظهر "لدى سلطان" للموظف

**ملفات Frontend:**
- `ContractsManagementPage.js` - تعديل العقود النشطة + سياسة الإجازة
- `STASMirrorPage.js` - ترجمة المفاتيح + عرض المعادلة والسياسة

**ملفات Backend:**
- `services/hr_policy.py` - `pending_ceo` → "لدى سلطان"
- `utils/pdf.py` - تحسين تسجيل الخطوط العربية

---

### Phase 23.0: HR Policy Engine - Pro-Rata & Blocking ✅ (2026-02-17)

**تحديث سياسة الموارد البشرية الشاملة**

**المعادلات المُنفذة:**
```
annual_entitlement_year = 21 أو 30 (من العقد أو قرار إداري)
daily_accrual = annual_entitlement_year / days_in_year
earned_to_date = daily_accrual * days_worked_in_year
available_balance = earned_to_date - used_executed
```

**ملفات جديدة:**
- `/app/backend/services/hr_policy.py` - محرك السياسة (580 سطر)
- `/app/backend/routes/admin.py` - إدارة السياسات

**ملفات مُحدّثة:**
- `leave_service.py` - استخدام Pro-Rata
- `stas_mirror_service.py` - عرض السياسة والمعادلة
- `routes/leave.py` - قاعدة Blocking
- `routes/employees.py` - ملخص مُحسّن
- `routes/contracts_v2.py` - حقل annual_policy_days

**APIs جديدة:**
- `POST /api/admin/annual-policy` - تغيير سياسة 21/30
- `POST /api/admin/leave-carryover` - ترحيل بقرار إداري
- `GET /api/admin/balance-alerts` - تنبيهات الأرصدة

**نتائج الاختبار:** 9/9 PASS

**التقرير الكامل:** `/app/backend/HR_POLICY_REPORT.md`

---

### Phase 22.1: Employee-User Linking & Arabic Errors ✅ (2026-02-17)

**P0 Completed - Employee User Linking Fix:**
- ✓ Fixed user_id not being set in employees table when contract is executed
- ✓ Updated contract_service.py to set employee.user_id = new user.id
- ✓ Fixed نايف القريشي's account - now fully functional
- ✓ Leave requests now check both contracts and contracts_v2 collections

**P0 Completed - Arabic Error Messages:**
- ✓ Converted ALL HTTPException messages to Arabic
- ✓ Files updated: auth.py, attendance.py, employees.py, contracts.py, custody.py, finance.py, financial_custody.py, leave.py, settings.py, stas.py
- ✓ Error messages now use message_ar where available

**Files Modified:**
- `/app/backend/services/contract_service.py` - Added user_id update
- `/app/backend/utils/leave_rules.py` - Added contracts_v2 lookup
- Multiple route files - Arabic error messages

**Employee Creation Flow (What gets linked):**
1. Employee created in `employees` collection with `id` and `user_id` (initially same value)
2. When contract executed: User created in `users` with new `id` and `employee_id`
3. Employee's `user_id` updated to match user's `id` (this was missing!)

**Test Result:** نايف القريشي can now login and request leave successfully

---

### Phase 22.0: Employee Management & Map Fix ✅ (2026-02-17)

**P0 Completed - Overlapping Maps Bug Fix:**
- ✓ Fixed multiple maps rendering in Work Locations page
- ✓ Map in dialog now wrapped with `{dialogOpen && <MapContainer />}` condition
- ✓ Unique key prop prevents duplicate instances: `key={dialog-map-${id}-${dialogOpen}}`
- ✓ Removed MapContainer from location cards - replaced with simple coordinate display
- ✓ Single map displays in dialog only, no overlapping maps issue

**P0 Completed - Employee Credentials Management:**
- ✓ New Key icon button in Employees table (STAS only)
- ✓ Dialog shows username and password fields
- ✓ Existing users: Shows current username, password update optional
- ✓ New users: Create username and password
- ✓ Password visibility toggle (eye icon)
- ✓ API: GET/PUT /api/users/{employee_id}/credentials

**P0 Completed - Employee Deletion:**
- ✓ New Trash icon button in Employees table (STAS only)
- ✓ Confirmation dialog in Arabic
- ✓ Prevents deletion if employee has active contract
- ✓ Deletes associated user account
- ✓ API: DELETE /api/employees/{employee_id}

**New Files:**
- `/app/backend/routes/users.py` - User credential management APIs

**Files Modified:**
- `/app/frontend/src/pages/WorkLocationsPage.js` - Map fix
- `/app/frontend/src/pages/EmployeesPage.js` - Credentials + Delete dialogs
- `/app/backend/routes/employees.py` - Delete endpoint
- `/app/backend/server.py` - Added users router

**New API Endpoints:**
- `GET /api/users` - List all users (STAS/Sultan/Naif)
- `GET /api/users/{employee_id}` - Get user by employee ID
- `PUT /api/users/{employee_id}/credentials` - Update username/password (STAS)
- `POST /api/users/create` - Create user for employee (STAS)
- `DELETE /api/employees/{employee_id}` - Delete employee (STAS)

**Test Report:** `/app/test_reports/iteration_23.json` - 100% pass rate

---

### Phase 21.2: Announcements UI & Tabs ✅ (2026-02-17)

**Completed - Announcements Management UI:**
- ✓ Added to System Maintenance page (صيانة النظام)
- ✓ 3 tabs: الإشعارات | التخزين | الأرشيف
- ✓ Create announcement form with Arabic & English fields
- ✓ Pinned toggle (إشعار مثبت) for important announcements
- ✓ List of existing announcements with delete button
- ✓ Location: صيانة النظام → الإشعارات

**Files Modified:**
- `/app/frontend/src/pages/SystemMaintenancePage.js` - Added Tabs, announcements UI

**Test Status:** Frontend UI complete, API working

---

### Phase 21.1: GPS Button, Announcements & Version Display ✅ (2026-02-17)

**Completed - GPS "تحديد مكاني" Button:**
- ✓ Button added to Add/Edit Work Location dialog
- ✓ Uses navigator.geolocation.getCurrentPosition
- ✓ Sets latitude/longitude from device GPS
- ✓ data-testid="use-my-location-btn"

**Completed - Announcements System:**
- ✓ Pinned announcements (is_pinned=true): Always visible under welcome hero with amber pin icon
- ✓ Regular announcements: Shown once, dismissable with X button
- ✓ STAS/Sultan/Mohammed can create announcements
- ✓ API endpoints: GET/POST /api/announcements, POST /api/announcements/{id}/dismiss

**Completed - Version Display:**
- ✓ APP_VERSION = "21.1" in server.py
- ✓ GET /api/health returns version
- ✓ Dashboard shows "DAR AL CODE HR OS v21.1" at bottom

**Completed - Arabic Error Messages:**
- ✓ translations.js updated with Arabic leave messages
- ✓ Backend leave error returns message_ar when available

**Completed - Protected Collections:**
- ✓ work_locations protected from purge operations
- ✓ Leave balance reset uses contract's annual_leave_days (21/30)

**Files Modified:**
- `/app/frontend/src/pages/WorkLocationsPage.js` - GPS button
- `/app/frontend/src/pages/DashboardPage.js` - Announcements + version
- `/app/frontend/src/lib/translations.js` - Arabic error messages
- `/app/backend/routes/announcements.py` - NEW: Announcements API
- `/app/backend/routes/maintenance.py` - Leave reset uses contract days
- `/app/backend/server.py` - APP_VERSION

**Test Report:**
- `/app/test_reports/iteration_22.json` - 100% pass rate

---

### Phase 21: Contracts V2 Enhancements & Leave System ✅ (2026-02-17)

**Completed - Remove Legacy Contracts:**
- ✓ Removed old "العقود" (contracts) from sidebar navigation
- ✓ Only "إدارة العقود" (Contracts Management V2) remains
- ✓ Removed ContractsPage import from App.js

**Completed - New Employee Creation with Contract:**
- ✓ Radio toggle: "موظف جديد" / "موظف قديم (اختيار من القائمة)"
- ✓ New employee fields: Name (AR/EN), National ID, Email, Phone, Employee Code
- ✓ Backend creates employee AND contract in single POST /api/contracts-v2
- ✓ Supports both is_new_employee=true (new) and is_new_employee=false (existing)

**Completed - Leave System Updates:**
- ✓ Annual leave: Only 21 or 30 days options (no 25)
  - 21 يوم (أقل من 5 سنوات)
  - 30 يوم (5 سنوات فأكثر)
- ✓ Monthly permission hours: 0-3 hours (default 2, max capped at 3)
- ✓ Permission hours tracked separately from leave balance
- ✓ Sick leave requires PDF medical file upload

**Completed - Migrated Contract Support:**
- ✓ Toggle "عقد مُهاجر (موظف قديم)" for existing employees
- ✓ Opening balances support fractional values (e.g., 15.5 days)
- ✓ Includes permission_hours opening balance

**Completed - Medical File Upload:**
- ✓ POST /api/upload/medical endpoint for PDF files
- ✓ Validates file type (PDF only) and size (max 5MB)
- ✓ Returns URL for storage in leave transactions
- ✓ LeavePage shows file input when sick leave selected

**Completed - Arabic Leave Types:**
- ✓ All leave types with Arabic labels:
  - الإجازة السنوية (Annual)
  - الإجازة المرضية (Sick) - requires PDF
  - إجازة الزواج (Marriage)
  - إجازة الوفاة (Bereavement)
  - إجازة الاختبار (Exam)
  - إجازة بدون راتب (Unpaid)

**Files Modified:**
- `/app/frontend/src/App.js` - Removed ContractsPage
- `/app/frontend/src/components/layout/AppLayout.js` - Removed 'contracts' from NAV_ITEMS
- `/app/frontend/src/pages/ContractsManagementPage.js` - New employee creation form
- `/app/frontend/src/pages/LeavePage.js` - LEAVE_TYPES with Arabic labels, medical file upload
- `/app/backend/routes/contracts_v2.py` - is_new_employee, annual_leave_days, monthly_permission_hours
- `/app/backend/routes/leave.py` - medical_file_url validation
- `/app/backend/routes/upload.py` - NEW: Medical PDF upload endpoint

**Test Report:**
- `/app/test_reports/iteration_21.json` - 100% pass rate

---

### Phase 20: STAS Barcode Cut-Out & UI Labels ✅ (2026-02-16)

**Completed - PDF Barcode Cut-Out Section:**
- ✓ PDF يحتوي على قسم باركود قابل للقص أسفل الورقة
- ✓ خط منقط مع رمز المقص (✂) فوق المربع للقص السهل
- ✓ المربع يحتوي على: اسم الشركة، نوع المعاملة، اسم الموظف، الباركود، Ref No، التاريخ
- ✓ نسختين من الباركود: واحدة في جدول الموافقات + واحدة للقص

**Completed - Arabic Approver Names:**
- ✓ اسم المعتمد (approver_name) يستخدم full_name_ar بدلاً من full_name
- ✓ المعاملات الجديدة ستظهر الاسم العربي للمعتمد

**Completed - STAS De-personalization:**
- ✓ استبدال "بانتظار STAS" → "بانتظار التنفيذ"
- ✓ استبدال "المرحلة: STAS" → "المرحلة: التنفيذ"
- ✓ STAS يبقى كاسم النظام فقط (ليس شخص)

**Completed - Status Colors:**
- ✓ 🟢 أخضر = منفذة (executed - approved)
- ✓ 🔴 أحمر = مرفوضة/ملغاة (rejected/cancelled)
- ✓ 🔵 أزرق = معادة (returned)

**Files Modified:**
- `/app/backend/utils/pdf.py` - CUT-OUT BARCODE SECTION (lines 651-718)
- `/app/backend/routes/transactions.py` - approver_name uses full_name_ar (line 177)
- `/app/frontend/src/pages/TransactionsPage.js` - STATUS_CONFIG + STAGE_CONFIG updates
- `/app/frontend/src/lib/translations.js` - stas → بانتظار التنفيذ

**Test Report:**
- `/app/test_reports/iteration_20.json` - 100% pass rate for all features

---

### Phase 19: STAS Enhancements & Map Feature ✅ (2026-02-16)

**P0 Completed - STAS Barcode Seal:**
- ✓ PDF generation now uses Code128 barcode instead of QR code for STAS execution stamp
- ✓ Ref No displayed clearly underneath the barcode
- ✓ STAS approval in chain also uses barcode with ref_no
- ✓ Other approvers still use QR codes for their signatures

**P0 Completed - One-Time STAS Execution:**
- ✓ Backend: Returns 400 error with ALREADY_EXECUTED if transaction already executed
- ✓ Error message includes Arabic and English messages
- ✓ Also blocks execution of cancelled/rejected transactions
- ✓ Frontend: Execute button is disabled and shows "تم التنفيذ مسبقاً" when transaction is executed
- ✓ Both desktop and mobile buttons are protected

**P1 Completed - Read-Only Map for Employees:**
- ✓ Employees can view company work locations when map is enabled by admin (via map_visibility setting)
- ✓ Red markers indicate employee's assigned check-in location(s)
- ✓ Blue markers indicate other company locations (for information only)
- ✓ Map dialog is read-only - no editing capability
- ✓ Location list shows "معين لك" badge for assigned locations
- ✓ Uses react-leaflet with OpenStreetMap tiles

**Files Modified:**
- `/app/backend/utils/pdf.py` - Barcode implementation for STAS seal
- `/app/backend/routes/stas.py` - Duplicate execution prevention (lines 151-172)
- `/app/frontend/src/pages/STASMirrorPage.js` - Execute button protection
- `/app/frontend/src/pages/AttendancePage.js` - Map dialog with red/blue markers

**Test Report:**
- `/app/test_reports/iteration_19.json` - 100% pass rate for all features
- `/app/backend/tests/test_iteration19_p0_features.py` - Backend tests

---

## Current Priority Queue (User's 7-Point List)

### ✅ Completed:
1. ~~STAS Seal: Barcode instead of QR with Ref No underneath~~ ✓
2. ~~STAS Execution: One-time execution only~~ ✓
7. ~~Map Logic: Employees see read-only map with colored pins~~ ✓
8. ~~STAS De-personalization: Remove "بانتظار STAS" terminology~~ ✓
9. ~~PDF Cut-Out: Barcode section at bottom for filing~~ ✓
10. ~~Status Colors: Green=approved, Red=rejected, Blue=returned~~ ✓

### 🔴 Remaining P0:
3. **Language Integrity (100%)** - Ensure UI & PDF are fully Arabic OR fully English with no mixing
4. **Standardized Letterhead** - Fixed official header/footer for all transaction PDFs

### 🟠 Remaining P1:
5. **Display Limit** - Limit transaction display to 4 items in specified views
6. **Transaction Blocking Rule** - Prevent new transaction if pending one of same type exists

### 🟢 After 7-Point Completion:
- Contract V2 System (new contract flow)
- Employee Migration to V2 (with opening data snapshot)
- Settlement Module (linked to V2 contracts)

---




---

### Phase 24: Employee Dashboard Card & Photo Management ✅ (2026-02-18)

**الميزات المُنفذة:**

1. **بطاقة الموظف على لوحة التحكم (P0)**
   - تظهر للموظفين العاديين والمشرفين فقط (ليس للمدراء)
   - تعرض: الاسم، المسمى الوظيفي، القسم، حالة نشط
   - إحصائيات سريعة: رصيد الإجازة، سنوات الخدمة، حضور اليوم
   - معلومات العقد: تاريخ انتهاء العقد
   - تصميم أنيق مع خلفية متدرجة
   - **ملف:** `frontend/src/pages/DashboardPage.js`

2. **تقييد تعديل صورة الموظف (P0)**
   - زر الكاميرا يظهر فقط لـ STAS
   - نافذة رفع صورة جديدة مع:
     - معاينة الصورة الحالية
     - زر رفع صورة جديدة
     - زر حذف الصورة
     - معلومات الصيغ المدعومة (JPG, PNG, GIF - أقصى 5MB)
   - **ملف:** `frontend/src/pages/EmployeeProfilePage.js`

3. **API رفع وحذف الصورة**
   - `POST /api/employees/{id}/photo` - رفع صورة (STAS فقط)
   - `GET /api/employees/{id}/photo-file` - جلب ملف الصورة
   - `DELETE /api/employees/{id}/photo` - حذف الصورة (STAS فقط)
   - **ملف:** `backend/routes/employees.py`

**الاختبارات:**
- ✅ بطاقة الموظف تظهر على لوحة التحكم للموظف العادي
- ✅ زر تعديل الصورة مرئي لـ STAS
- ✅ زر تعديل الصورة مخفي عن المستخدمين الآخرين
- ✅ نافذة تعديل الصورة تعمل بشكل صحيح



### Phase 21: Daily Attendance Engine Fix & Automation ✅ (2026-02-18)

**المشكلة المُصلحة:**
- أسماء الحقول في الكود (`work_start_time`) لا تتطابق مع قاعدة البيانات (`work_start`)
- تحويل التوقيت من UTC إلى توقيت الرياض كان خاطئاً

**الإصلاحات:**
1. **تصحيح أسماء الحقول في day_resolver.py و day_resolver_v2.py:**
   - `work_start` بدلاً من `work_start_time`
   - `work_end` بدلاً من `work_end_time`
   - `grace_checkin_minutes` بدلاً من `grace_period_checkin_minutes`
   - `grace_checkout_minutes` بدلاً من `grace_period_checkout_minutes`

2. **تصحيح تحويل التوقيت:**
   - إضافة `from zoneinfo import ZoneInfo`
   - استخدام `RIYADH_TZ = ZoneInfo("Asia/Riyadh")`
   - تحويل أوقات البصمة من UTC إلى توقيت الرياض قبل المقارنة

3. **تصحيح فحص عطلة نهاية الأسبوع:**
   - قراءة `work_days` كـ object (ليس array)
   - فحص اليوم: إذا `work_days[day_name] == false` فهو عطلة

4. **أتمتة الوظائف (APScheduler):**
   - وظيفة يومية: 1:00 صباحاً (توقيت الرياض) = 22:00 UTC
   - وظيفة شهرية: 3:00 صباحاً (توقيت الرياض) في أول كل شهر
   - ملف: `/app/backend/services/scheduler.py`

5. **حد "نسيان البصمة" (3 طلبات شهرياً):**
   - API جديد: `POST /api/attendance-engine/forgotten-punch`
   - التحقق من عدد الطلبات المقبولة في الشهر الحالي
   - رفض الطلب إذا تجاوز 3 طلبات (القاعدة مخفية عن الموظف)

**الملفات المُعدلة:**
- `/app/backend/services/day_resolver.py`
- `/app/backend/services/day_resolver_v2.py`
- `/app/backend/services/scheduler.py` (جديد)
- `/app/backend/routes/attendance_engine.py`
- `/app/backend/server.py`

**الاختبارات (iteration_29):**
- ✅ Day Resolver V2 يعمل مع trace evidence
- ✅ تحويل التوقيت إلى الرياض يعمل
- ✅ APIs ماليّاتي تعمل (summary, deductions, warnings)
- ✅ لوحة الموظف تعرض ساعات العمل وساعات النقص
- ✅ رابط ماليّاتي في القائمة الجانبية
- ✅ APScheduler مُهيأ بشكل صحيح

---

### Phase 30: Device Security System & STAS Transaction Delete ✅ (2026-02-19)

**الميزات المُنفذة:**

1. **نظام التعرف على الأجهزة (Device Fingerprinting):**
   - توليد بصمة فريدة للجهاز من: User Agent, Platform, Screen Resolution, Timezone, Language, WebGL, Canvas, Device Memory, Hardware Concurrency
   - تسجيل الأجهزة: أول جهاز يُعتمد تلقائياً، الأجهزة الجديدة تحتاج اعتماد STAS
   - حالات الجهاز: `trusted` | `pending` | `blocked`
   - **ملف:** `backend/services/device_service.py`

2. **إدارة حسابات الموظفين (Account Block/Unblock):**
   - STAS يمكنه إيقاف حساب موظف للتحقيق
   - حماية حسابات المدراء (EMP-STAS, EMP-MOHAMMED, etc.) من الحظر
   - إلغاء الإيقاف مع تسجيل العملية
   - **APIs:** `POST /api/devices/account/{id}/block`, `POST /api/devices/account/{id}/unblock`

3. **سجل الأمان (Security Audit Log):**
   - تسجيل جميع الأحداث الأمنية: تسجيل جهاز، اعتماد، حظر، إيقاف حساب
   - **Collection:** `security_audit_log`
   - **API:** `GET /api/devices/security-logs`

4. **حذف معاملات STAS الخاصة:**
   - STAS فقط يمكنه حذف معاملاته الخاصة
   - التحقق من الملكية قبل الحذف
   - تسجيل المعاملات المحذوفة في `deleted_transactions_log`
   - **API:** `DELETE /api/transactions/{id}`

5. **تبويب "الأجهزة" في صفحة STAS Mirror:**
   - إدارة حسابات الموظفين (إيقاف/إلغاء الإيقاف)
   - سجل الأجهزة المسجلة مع إجراءات (اعتماد/حظر/حذف)
   - سجل الأمان

6. **تبويب "معاملاتي" في صفحة STAS Mirror:**
   - عرض معاملات STAS الخاصة
   - زر عرض التفاصيل
   - زر حذف المعاملة

**الملفات الجديدة/المُحدثة:**
- `/app/backend/routes/devices.py` - Device management APIs
- `/app/backend/services/device_service.py` - Device service logic
- `/app/backend/routes/transactions.py` - Added DELETE endpoint
- `/app/frontend/src/pages/STASMirrorPage.js` - Added Devices & My Transactions tabs

**APIs جديدة:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/devices/all` | جميع الأجهزة (STAS) |
| GET | `/api/devices/pending` | الأجهزة المعلقة |
| POST | `/api/devices/{id}/approve` | اعتماد جهاز |
| POST | `/api/devices/{id}/block` | حظر جهاز |
| DELETE | `/api/devices/{id}` | حذف جهاز |
| GET | `/api/devices/account/{id}/status` | حالة الحساب |
| POST | `/api/devices/account/{id}/block` | إيقاف حساب |
| POST | `/api/devices/account/{id}/unblock` | إلغاء إيقاف |
| GET | `/api/devices/security-logs` | سجل الأمان |
| DELETE | `/api/transactions/{id}` | حذف معاملة (STAS) |

**الاختبارات:** 100% pass rate (16/16 backend tests)
- `/app/backend/tests/test_iteration30_devices_transactions.py`

---

### Phase 31: Bug Fixes & Ramadan Per-Location ✅ (2026-02-19)

**الإصلاحات المُنفذة:**

1. **إصلاح خطأ "Access denied for your role" لـ STAS:**
   - تم إضافة `'stas'` إلى `require_roles` في `team_attendance.py` (Line 371)
   - الآن STAS يمكنه تعديل حالة الموظفين

2. **إصلاح عرض كلمة المرور:**
   - تم إضافة حقل `plain_password` يُخزن عند إنشاء/تحديث كلمة المرور
   - STAS فقط يمكنه رؤية `plain_password` عبر `GET /api/users/{employee_id}`
   - الواجهة تعرض كلمة المرور المُخزنة عند فتح حوار بيانات الدخول

3. **دعم رمضان لكل موقع (Per-Location Ramadan):**
   - API جديد: `PUT /api/work-locations/{id}/ramadan/activate`
   - API جديد: `PUT /api/work-locations/{id}/ramadan/deactivate`
   - زر تفعيل/إلغاء رمضان ظاهر في كارت كل موقع لـ STAS فقط
   - يحفظ الأوقات الأصلية ويستعيدها عند الإلغاء

**الملفات المُعدلة:**
- `/app/backend/routes/team_attendance.py` - Added 'stas' to require_roles
- `/app/backend/routes/users.py` - plain_password storage and retrieval
- `/app/backend/routes/work_locations.py` - Ramadan per-location APIs
- `/app/frontend/src/pages/WorkLocationsPage.js` - Ramadan UI for STAS
- `/app/frontend/src/pages/EmployeesPage.js` - Display stored password

**الاختبارات:** 100% pass rate (18/18 backend tests)
- `/app/backend/tests/test_iteration31_features.py`

---

### Phase 32: P0 Authentication & Security Fixes ✅ (2026-02-19)

**الإصلاحات المُنفذة:**

1. **إصلاح ثغرة كلمة المرور النصية (Critical Security Fix):**
   - تم إزالة تخزين `plain_password` من جميع نقاط النهاية
   - كلمة المرور الآن تُخزن مُشفرة فقط (bcrypt)
   - لا يمكن عرض كلمة المرور الحالية - فقط تحديثها
   - **ملفات:** `users.py`, `auth.py`

2. **تفعيل صفحة تسجيل الدخول الاحترافية:**
   - صفحة الدخول هي الآن نقطة الدخول الرئيسية للتطبيق
   - تصميم ثنائي اللغة (عربي/إنجليزي) مع شعار الشركة
   - دعم "تذكرني" مع حفظ اسم المستخدم
   - إزالة التسجيل التلقائي كأول مستخدم
   - دعم Device Fingerprinting في تسجيل الدخول
   - **ملفات:** `App.js`, `AuthContext.js`, `LoginPage.js`

3. **تقييد User Switcher لـ STAS فقط:**
   - زر تبديل المستخدمين يظهر فقط لـ STAS بعد تسجيل الدخول
   - المستخدمون العاديون يرون اسمهم فقط (بدون dropdown)
   - حماية Backend: `/api/auth/users` و `/api/auth/switch` محميان لـ STAS فقط
   - **ملف:** `AppLayout.js`

4. **إضافة زر تسجيل الخروج:**
   - زر خروج واضح في Header لجميع المستخدمين
   - يمسح الـ token ويعود لصفحة الدخول
   - **ملف:** `AppLayout.js`

5. **إصلاح صلاحيات STAS:**
   - إضافة `'stas'` لـ 3 endpoints كانت محصورة في sultan/naif:
     - `POST /api/attendance-engine/proposals/{id}/review`
     - `POST /api/attendance-engine/warnings/{id}/review`
     - `POST /api/contracts/settlement`
   - **ملفات:** `attendance_engine.py`, `contracts.py`

**بيانات الاعتماد الافتراضية:**
- **جميع المستخدمين:** كلمة المرور = `DarAlCode2026!`
- **أسماء المستخدمين:** stas, sultan, naif, salah, mohammed, supervisor1

**الاختبارات:** 100% pass rate (13/13 backend, 100% frontend)
- `/app/backend/tests/test_iteration32_auth.py`
- `/app/test_reports/iteration_32.json`

---

## Backlog (P1/P2)

### P1 Tasks:
1. **مرآة STAS للخصومات:** عرض trace_log للخصومات المقترحة في صفحة STAS Mirror
2. **واجهة مراجعة/تنفيذ الخصومات:** للمدراء (sultan/naif) و STAS
3. **ربط صفحة ماليّاتي بـ APIs فعلية:** عرض الخصومات والإنذارات الفعلية

### P2 Tasks:
1. لوحة تحكم CEO
2. نظام القروض
3. تقارير PDF للمعاملات
4. منع الخصومات من تجاوز 50% من الراتب
5. نظام التحذيرات التدريجي

---

## API Endpoints Reference

### Attendance Engine
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/attendance-engine/resolve-day` | تحليل يوم لموظف |
| POST | `/api/attendance-engine/resolve-bulk` | تحليل يوم لجميع الموظفين |
| POST | `/api/attendance-engine/process-daily` | التحضير اليومي التلقائي |
| GET | `/api/attendance-engine/daily-status/{emp}/{date}` | حالة يوم محدد |
| GET | `/api/attendance-engine/daily-status-range/{emp}` | حالة فترة |
| GET | `/api/attendance-engine/monthly-hours/{emp}/{month}` | ساعات الشهر |
| GET | `/api/attendance-engine/my-finances/summary` | ملخص ماليّاتي |
| GET | `/api/attendance-engine/my-finances/deductions` | قائمة الخصومات |
| GET | `/api/attendance-engine/my-finances/warnings` | قائمة الإنذارات |
| POST | `/api/attendance-engine/forgotten-punch` | طلب نسيان بصمة |
| GET | `/api/attendance-engine/forgotten-punch/pending` | الطلبات المعلقة |

### Jobs (Automated)
| Schedule | Job | Description |
|----------|-----|-------------|
| 22:00 UTC | Daily Attendance | معالجة حضور الأمس |
| 00:00 UTC (1st) | Monthly Summary | ملخص الشهر السابق |


---

### Phase 19: Attendance System Complete Fix ✅ (2026-02-19)

**المشاكل التي تم حلها:**

1. **إصلاح نظام GPS للمواقع المتعددة:**
   - تم تحديث `punch_validator.py` ليدعم الموظفين المعينين في مواقع عمل متعددة
   - الآن يتم فحص جميع المواقع المعينة للموظف وليس الموقع الأول فقط
   - إذا كان الموظف داخل نطاق أي موقع معين له، يُسمح بالتبصيم

2. **استعادة قسم طلبات الموظفين:**
   - تم إعادة بناء صفحة الحضور بالكامل مع 3 تبويبات:
     - **تسجيل الحضور**: حالة GPS، مواقع العمل، سجل اليوم، أزرار الدخول/الخروج
     - **طلبات الموظفين**: زر طلب جديد + قائمة الطلبات السابقة
     - **سجل الكل** (للإدارة): جدول حضور جميع الموظفين

3. **4 أنواع طلبات حضور:**
   - 🔔 نسيان بصمة (`forget_checkin`)
   - 🚗 مهمة خارجية (`field_work`)
   - 🚪 طلب خروج مبكر (`early_leave_request`)
   - ⏰ تبرير تأخير (`late_excuse`)

4. **تحسين واجهة المستخدم:**
   - حالة GPS مُحسّنة مع أيقونات ورسائل واضحة
   - عرض مواقع العمل المعينة بشكل واضح
   - سجل اليوم يعرض وقت الدخول/الخروج مع اسم الموقع
   - أزرار تسجيل الدخول/الخروج مع تدرجات ألوان

**APIs الجديدة:**
- `GET /api/employees/{id}/assigned-locations` - جلب جميع مواقع العمل المعينة للموظف

**الملفات المُحدثة:**
- `/app/frontend/src/pages/AttendancePage.js` - إعادة بناء كاملة
- `/app/backend/services/punch_validator.py` - دعم المواقع المتعددة
- `/app/backend/routes/employees.py` - إضافة endpoint المواقع

**Testing:** ✅ 100% pass rate (13/13 backend tests, all frontend features verified)

---

---

### Phase 19: Device Management UI Overhaul ✅ (2026-02-19)

**الميزات المُنفذة:**

1. **تحسين تحليل User-Agent (Backend):**
   - استخدام مكتبة `user-agents` لتحليل دقيق
   - استخراج معلومات سهلة للمستخدم:
     - `friendly_name`: اسم الجهاز بالعربي (مثال: "آيفون 15"، "كمبيوتر ويندوز")
     - `device_brand`: ماركة الجهاز (Apple, Samsung, Huawei, etc.)
     - `device_model`: موديل الجهاز
     - `os_display`: نظام التشغيل بالعربي (iOS, أندرويد, ويندوز)
   - دعم: iPhone, iPad, Mac, Samsung, Huawei, Xiaomi, Windows, Linux

2. **واجهة الأجهزة المعلقة (Pending Devices):**
   - تصميم بارز بخلفية برتقالية متدرجة
   - بطاقات كبيرة لكل جهاز مع:
     - أيقونة نوع الجهاز (Smartphone/Tablet/Monitor)
     - اسم الموظف بارز
     - اسم الجهاز الصديق للمستخدم
     - تاريخ التسجيل
   - أزرار "موافقة" و"رفض" كبيرة وواضحة

3. **إدارة الموظفين والأجهزة:**
   - قائمة منسدلة لاختيار الموظف
   - حقل سبب الإجراء (اختياري)
   - 3 أزرار للتحكم:
     - 🔴 إيقاف الحساب
     - 🟢 تفعيل الحساب
     - 🟠 إعادة تعيين الأجهزة
   - رسالة توجيهية عند عدم اختيار موظف

4. **عرض الأجهزة ككروت (Device Cards Grid):**
   - عرض شبكي (Grid) بدلاً من جدول
   - لكل جهاز بطاقة تحتوي:
     - أيقونة ملونة حسب الحالة
     - اسم الموظف ورقمه
     - حالة الجهاز (موثوق/معلق/محظور)
     - اسم الجهاز الصديق
     - المتصفح ونظام التشغيل
     - آخر استخدام
     - أزرار التحكم

5. **ألوان الحالات:**
   - 🟢 موثوق: أخضر (border-green-400)
   - 🟠 معلق: برتقالي (border-orange-400)
   - 🔴 محظور: أحمر (border-red-400)

**الملفات المُحدثة:**
- `/app/backend/services/device_service.py` - دالة `_parse_user_agent()` و `get_all_devices()`
- `/app/frontend/src/pages/STASMirrorPage.js` - تبويب الأجهزة بالكامل

**الـ APIs:**
- `GET /api/devices/all` - يرجع الآن `friendly_name`, `os_display`, `is_mobile`, etc.
- `POST /api/devices/employee/{id}/reset-devices` - إعادة تعيين جميع أجهزة الموظف

**Testing:** ✅ Working - Backend tested with multiple User-Agent strings, UI verified via screenshot

---

## Pending Issues (P0)

### Issue 1: GPS Check-out Bug (CRITICAL)
- **المشكلة:** خطأ "يجب تفعيل الموقع للتبصيم" يظهر عند تسجيل الخروج رغم تفعيل GPS
- **الملفات المعنية:**
  - `/app/frontend/src/pages/AttendancePage.js` - `handleCheckOut`
  - `/app/backend/services/punch_validator.py` - `validate_full_punch`
- **الحالة:** بانتظار الإصلاح

### Issue 3: Admin Manual Attendance Override (P1)
- **المطلوب:** زر "تحضير" في `/team-attendance` لتسجيل حضور يدوي
- **الملفات:** `TeamAttendancePage.js`, `attendance_engine.py`
- **الحالة:** لم يبدأ

### Issue 4: Transaction Barcode & Camera Search (P2)
- **المطلوب:** باركود على PDF + كاميرا للبحث
- **الحالة:** لم يبدأ

---

## Credentials for Testing
- STAS: `stas` / `123456`
- Sultan: `sultan` / `123456`
- Naif: `naif` / `123456`
- All users: password `123456`

---

### Phase 20: Tasks & Annual Evaluation System ✅ (2026-02-19)

**نظام المهام المرتبط بالتقييم السنوي**

#### الميزات المُنفذة:

1. **إنشاء المهام (المدراء فقط)**
   - المخولين: نايف، سلطان، محمد
   - الحقول: عنوان (عربي/إنجليزي)، وصف، الموظف، تاريخ التسليم، الوزن التقييمي

2. **نظام المراحل (4 مراحل × 25%)**
   - الموظف يضغط "تم الإنجاز" لكل مرحلة
   - المدير يُقيّم كل مرحلة (1-5)
   - تعليق اختياري لكل تقييم

3. **حساب التأخير**
   - خصم 5% لكل يوم تأخير
   - بحد أقصى 25%

4. **حساب الدرجة النهائية**
   - متوسط تقييمات المراحل الأربع
   - تطبيق غرامة التأخير
   - تخزين في سجل الموظف

5. **إغلاق المهمة**
   - المدير يضغط "استلام نهائي"
   - يظهر للمدير وزن المهمة في التقييم السنوي
   - الدرجة تُسجّل في `employee_task_evaluations`

6. **الإشعارات**
   - إشعار للموظف: مهمة جديدة، تقييم مرحلة، إغلاق المهمة
   - إشعار للمدير: مرحلة بانتظار التقييم

7. **الواجهة**
   - صفحة للموظف: مهامي، نسبة الإنجاز، التقييمات
   - صفحة للمدراء: جميع المهام، إنشاء مهمة، التقييم

#### الـ APIs:
- `POST /api/tasks/create` - إنشاء مهمة
- `GET /api/tasks/my-tasks` - مهام الموظف
- `GET /api/tasks/all` - جميع المهام (للإدارة)
- `POST /api/tasks/{id}/complete-stage` - إنهاء مرحلة
- `POST /api/tasks/{id}/evaluate-stage` - تقييم مرحلة
- `POST /api/tasks/{id}/close` - إغلاق المهمة
- `GET /api/tasks/employee/{id}/annual-summary` - ملخص التقييم السنوي

#### قواعد البيانات:
- `tasks` - المهام
- `employee_task_evaluations` - سجل تقييمات المهام
- `notifications` - الإشعارات

#### الملفات:
- `/app/backend/routes/tasks.py`
- `/app/frontend/src/pages/TasksPage.js`

**Testing:** ✅ Backend APIs tested successfully

---

## Device Fingerprinting System Update (2026-02-19)

### التحسينات:
1. **Core Hardware Signature**: WebGL + Canvas + CPU + Memory + Platform + Screen
2. **تغيير المتصفح فقط لا يُعتبر جهاز جديد**
3. **التواريخ ميلادية** (ar-EG بدلاً من ar-SA)


---

### Phase 20: Admin Financial Custody System (نظام العهدة المالية الإدارية) ✅ (2026-02-19)

**بناء من الصفر - نظام إداري داخلي فقط (ليس HR أو رواتب)**

**المستخدمون المصرح لهم:**
- سلطان: إنشاء عهد + إضافة مصروفات
- محمد: إنشاء عهد + إضافة مصروفات  
- صلاح (المحاسب): تدقيق واعتماد/إرجاع
- STAS: تنفيذ + إغلاق + تجاوز التدقيق بعد 24 ساعة

**الميزات المُنفذة:**

1. **إنشاء عهدة جديدة:**
   - رقم تلقائي (001, 002, ...)
   - مبلغ العهدة
   - ترحيل الفائض من العهدة السابقة تلقائياً
   - الميزانية = المبلغ + الفائض المُرحّل

2. **جدول المصروفات (Excel-like):**
   - 60 كود ثابت للمصروفات
   - عند كتابة الكود → يظهر الاسم تلقائياً (بدون قوائم منسدلة)
   - أكواد 61+ تُحفظ تلقائياً
   - حساب لحظي: المصروف والمتبقي
   - لا يُسمح بتجاوز المتبقي

3. **دورة حياة العهدة:**
   ```
   open → pending_audit → approved → executed → closed
   ```
   - سلطان/محمد: إنشاء + صرف + إرسال للتدقيق
   - صلاح: تدقيق (اعتماد/إرجاع) + تعديل المصروفات
   - STAS: تنفيذ (بعد اعتماد صلاح) أو اعتماد مباشر بعد 24 ساعة
   - إغلاق: ترحيل الفائض للعهدة القادمة

4. **القواعد المهمة:**
   - لا تعديل بعد التنفيذ
   - كل تعديل يُسجّل في log
   - لا حذف فعلي - فقط إلغاء
   - لا صرف يتجاوز المتبقي

5. **لوحة الإجماليات:**
   - إجمالي العهد
   - إجمالي المصروف
   - إجمالي المتبقي
   - عدد العهد: مفتوحة/معلقة/منفذة/مغلقة
   - الفائض المتاح للترحيل

**الملفات الجديدة/المُحدثة:**
- `/app/backend/routes/admin_custody.py` - APIs الكاملة + 60 كود ثابت
- `/app/frontend/src/pages/FinancialCustodyPage.js` - واجهة Excel-like

**APIs الجديدة:**
- `GET /api/admin-custody/codes` - جميع الأكواد الـ60+
- `GET /api/admin-custody/codes/{code}` - بحث فوري عن كود
- `POST /api/admin-custody/codes` - إضافة كود جديد (61+)
- `POST /api/admin-custody/create` - إنشاء عهدة
- `GET /api/admin-custody/all` - قائمة العهد
- `GET /api/admin-custody/{id}` - تفاصيل عهدة + مصروفاتها
- `POST /api/admin-custody/{id}/expense` - إضافة مصروف
- `DELETE /api/admin-custody/{id}/expense/{exp_id}` - إلغاء مصروف
- `PUT /api/admin-custody/{id}/expense/{exp_id}` - تعديل مصروف (صلاح)
- `POST /api/admin-custody/{id}/submit-audit` - إرسال للتدقيق
- `POST /api/admin-custody/{id}/audit` - تدقيق (approve/reject)
- `POST /api/admin-custody/{id}/execute` - تنفيذ (STAS)
- `POST /api/admin-custody/{id}/close` - إغلاق
- `GET /api/admin-custody/summary` - إحصائيات
- `GET /api/admin-custody/surplus-available` - الفائض المتاح

**الأكواد الثابتة (1-60):**
| الكود | الاسم |
|-------|-------|
| 1 | اثاث الامانة |
| 5 | انتقالات |
| 11 | ضيافة |
| 15 | محروقات |
| 42 | محروقات وصيانه سيارات |
| ... | (60 كود) |

**Testing:** 100% pass rate (17/17 backend tests, all UI flows verified)
- `/app/test_reports/iteration_35.json`
- `/app/backend/tests/test_admin_custody_system.py`

**Collections:**
- `admin_custodies` - العهد
- `custody_expenses` - المصروفات
- `custody_logs` - سجل الأحداث
- `expense_codes` - الأكواد المضافة (61+)


---

### Phase 36: Executive Dashboard (لوحة الحوكمة التنفيذية) ✅ (2026-02-19)

**المتطلبات المُنفذة:**

لوحة تحكم تنفيذية رسمية عالية المستوى مخصصة للمدير التنفيذي والإدارة العليا، قابلة للعرض على شاشات كبيرة (TV Mode).

**1. التصميم الفاخر (Modern Minimal Executive Style):**
   - ألوان حيادية راقية: أسود داكن (#0A0A0B)، رمادي عميق، أبيض مكسور
   - خلفية داكنة مع borders خفيفة
   - تأثيرات glow احترافية
   - animations سلسة
   - RTL كامل للغة العربية

**2. المكونات الأساسية:**

   **أ) مؤشر صحة الشركة (Company Health Score):**
   - رقم رئيسي كبير في المنتصف (من 100)
   - مؤشر دائري احترافي مع glow effect
   - ألوان ديناميكية حسب النتيجة (أحمر/برتقالي/أزرق/أخضر)
   - تصنيف: ممتاز (85+) / جيد (70+) / مقبول (50+) / يحتاج تحسين

   **ب) المؤشرات الأربعة الرئيسية (KPI Cards):**
   - الحضور والانضباط: نسبة + أيام الحضور + دقائق التأخير
   - أداء المهام: نسبة + المهام المنجزة + متوسط التقييم
   - الانضباط المالي: نسبة + العهد + المصروف + المُعاد
   - انضباط الطلبات: نسبة + المقبولة + المرفوضة + المعلقة

   **ج) الملخص التنفيذي (Executive Summary):**
   - فقرة نصية ذكية تُولّد تلقائياً
   - مثال: "مستوى الأداء العام يتطلب تدخل عاجل."

   **د) الرسوم البيانية الديناميكية:**
   - Area Chart: اتجاه الأداء الشهري (6 أشهر)
   - Pie Chart: توزيع المؤشرات الأربعة

   **هـ) قوائم الأداء:**
   - الأعلى أداءً (Top 5 Performers)
   - يحتاج متابعة (Bottom 5 - Needs Attention)

   **و) الإحصائيات السريعة (Quick Stats):**
   - الموظفين النشطين
   - الطلبات المعلقة
   - العهد المفتوحة
   - المهام الجارية

**3. الخصائص التقنية:**

   - **TV Mode:** يفتح بدون Sidebar (noLayout=true)
   - **وضع العرض الكامل:** زر Fullscreen
   - **التحديث التلقائي:** كل 60 ثانية (قابل للإيقاف)
   - **التنبيهات:** لوحة منسدلة للتنبيهات العاجلة
   - **زر العودة:** للرجوع إلى Dashboard الرئيسي
   - **متوافق مع جميع الأجهزة:** جوال، تابلت، حاسب، شاشات كبيرة

**4. الصلاحيات:**
   - mohammed (CEO) ✓
   - sultan (Ops Admin) ✓
   - naif (Ops Strategic) ✓
   - stas (System Admin) ✓
   - salah (Accountant) ✗ - مرفوض (403)

**5. حساب الدرجات (Weighted Score):**
   ```
   Health Score = (Attendance × 30%) + (Tasks × 35%) + (Financial × 20%) + (Requests × 15%)
   ```

**الملفات الجديدة/المُحدثة:**
- `/app/backend/routes/analytics.py` - Analytics API كامل
- `/app/frontend/src/pages/ExecutiveDashboard.js` - واجهة فاخرة مع charts
- `/app/frontend/src/App.js` - TV Mode routing (noLayout)
- `/app/frontend/src/components/layout/AppLayout.js` - Activity icon

**APIs الجديدة:**
- `GET /api/analytics/executive/dashboard` - بيانات اللوحة الكاملة
- `GET /api/analytics/alerts` - التنبيهات التنفيذية
- `GET /api/analytics/employee/{id}/score` - درجة موظف محدد

**Testing:** 100% pass rate
- Backend: 17/17 tests passed
- Frontend: 14/14 UI components verified
- `/app/test_reports/iteration_36.json`
- `/app/backend/tests/test_executive_dashboard.py`

---

Version: 36.0 (2026-02-19)


---

### Phase 37: Attendance System Deep Fix ✅ (2026-02-20)

**إصلاحات نظام الحضور والعقوبات**

#### 1. إصلاح مشكلة GPS عند تسجيل الخروج (P0):
- **المشكلة:** الموظف لا يستطيع تسجيل الخروج إذا لم يكن GPS متاحاً، حتى لو سجل دخوله بـ GPS صالح
- **الحل:** تعديل `punch_validator.py` للسماح بالخروج بدون GPS إذا كان الدخول تم بـ GPS مُصدّق
- **المنطق الجديد:**
  - عند تسجيل الخروج، يُفحص سجل الدخول لنفس اليوم
  - إذا كان `gps_valid=true` أو `work_location_id` موجود في بصمة الدخول
  - يُسمح بالخروج بدون GPS مع تحذير: "تم تجاوز فحص GPS للخروج"
- **الملف:** `/app/backend/services/punch_validator.py`

#### 2. تحسين حساب الساعات الشهرية المطلوبة (P1):
- **المشكلة:** الساعات المطلوبة ثابتة على 176 ساعة (22 يوم × 8 ساعات)
- **الحل:** حساب ديناميكي يعتمد على:
  - عدد أيام العمل الفعلية في الشهر
  - استبعاد العطل الرسمية من holidays collection
  - إعدادات موقع العمل (work_days, daily_hours)
  - الافتراضي: الجمعة والسبت عطلة
- **النتيجة:** Required Hours = work_days_count × daily_hours
- **الملف:** `/app/backend/routes/employees.py`

#### 3. معلومات إضافية في Employee Summary (P2):
- **حقول جديدة في attendance:**
  - `work_days_in_month`: عدد أيام العمل في الشهر
  - `daily_hours`: ساعات العمل اليومية
  - `hours_until_deduction`: الساعات المتبقية قبل خصم يوم
  - `days_to_deduct`: عدد الأيام للخصم (إذا deficit_hours >= 8)

#### المنطق المُفصّل لنظام الحضور:

**محرك القرار اليومي (day_resolver_v2):**
| الترتيب | الفحص | النتيجة |
|---------|-------|---------|
| 1 | العطل الرسمية | HOLIDAY |
| 2 | عطلة نهاية الأسبوع | WEEKEND |
| 3 | إجازة منفذة | ON_LEAVE |
| 4 | مهمة خارجية | ON_MISSION |
| 5 | نسيان بصمة | PRESENT |
| 6 | بصمة فعلية | PRESENT/LATE/EARLY_LEAVE |
| 7 | استئذان | PERMISSION |
| 8 | تبريرات | يُعدّل الحالة |
| 9 | لا شيء | ABSENT |

**قواعد العقوبات:**
| نوع الغياب | العقوبة |
|------------|---------|
| يوم غياب بدون عذر | خصم أجر يوم كامل |
| 3 أيام متصلة | إنذار أول |
| 5 أيام متصلة | إنذار ثاني |
| 10 أيام متصلة | إنذار نهائي |
| 15 يوم متصل | فصل |
| 10 أيام متفرقة/سنة | إنذار أول |
| 20 يوم متفرق/سنة | إنذار نهائي |
| 30 يوم متفرق/سنة | فصل |
| كل 8 ساعات نقص | خصم يوم |

**الجدولة التلقائية (scheduler.py):**
- يومياً الساعة 1 صباحاً: معالجة daily_status لليوم السابق
- شهرياً أول الشهر: إنشاء monthly_summary

**الملفات المُعدلة:**
- `/app/backend/services/punch_validator.py` - تجاوز GPS للخروج
- `/app/backend/routes/employees.py` - حساب ديناميكي للساعات

**Testing:** ✅ API endpoints verified via curl
- Employee Summary returns dynamic `required_monthly_hours`
- Work days calculated based on holidays and location settings

---

Version: 37.0 (2026-02-20)



---

### Phase 38: Language Unification & System Analysis ✅ (2026-02-20)

**إصلاح تضارب اللغة (P0) + تحليل النظام الشامل**

#### 1. إصلاح تضارب اللغة في الواجهات:

| الملف | الإصلاح |
|-------|---------|
| `AttendancePage.js` | ترجمة رؤوس الجدول (GPS → الموقع، Check-in → الدخول) |
| `ContractsPage.js` | ترجمة نموذج العقد (Type، Employee، Dates، Allowances) |
| `EmployeesPage.js` | ترجمة عمود ID → الرقم |
| `SettlementPage.js` | ترجمة جدول المخالصة + التوقيعات (STAS، CEO، HR، Employee) |
| `ExecutiveDashboard.js` | ترجمة "Company Health Score" → "مؤشر صحة الشركة" |
| `DashboardPage.js` | ترجمة اسم التطبيق |
| `translations.js` | إضافة `nav.executive` = "لوحة التحكم التنفيذية" |

#### 2. تحليل مشكلة مدة الخدمة = 0:

**السبب:** العقد يجب أن يكون حالته `active` أو `terminated` لتظهر مدة الخدمة
- إذا كان العقد `draft` أو `pending_stas` = لن تظهر معلومات الخدمة
- **هذا سلوك صحيح ومقصود**

**التحقق:**
```
EMP-001: contract.status = 'draft' → service_info = null ❌
EMP-002: contract.status = 'active' → service_info = ✅ (4 سنة و 11 شهر و 27 يوم)
```

#### 3. تحليل ربط العقد بالمخالصة:

```
┌─────────────────────────────────────────────────────────────┐
│                        employees                             │
│  id, full_name, supervisor_id, user_id, is_active           │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   contracts_v2  │ │  work_locations │ │      users      │
│   employee_id   │ │ assigned_employees│ │  employee_id   │
│   start_date    │ │    daily_hours  │ │    username    │
│   status        │ │    work_days    │ │    is_active   │
└────────┬────────┘ └────────┬────────┘ └────────────────┘
         │                   │
         │                   ▼
         │          ┌─────────────────┐
         │          │ attendance_ledger│
         │          │   employee_id    │
         │          │   work_location_id│
         │          └────────┬────────┘
         │                   │
         ▼                   ▼
┌─────────────────┐ ┌─────────────────┐
│   settlements   │ │   daily_status  │
│   employee_id   │ │   employee_id   │
│   contract_id   │ │   worked_hours  │
└─────────────────┘ └─────────────────┘
```

#### 4. ماذا يربط الموظف بالنظام:

| المكون | الرابط | الوصف |
|--------|--------|-------|
| **العقد** | `employee_id` | يحدد الراتب، البدلات، تاريخ البدء |
| **موقع العمل** | `assigned_employees[]` | يحدد ساعات العمل، أيام الأسبوع |
| **المستخدم** | `employee_id` | يحدد صلاحيات الدخول، اسم المستخدم |
| **الحضور** | `employee_id` | يسجل بصمات الدخول والخروج |
| **المخالصة** | `employee_id` + `contract_id` | يربط بالعقد لحساب EOS |

#### 5. ما يحدث عند تفعيل العقد (activate):

1. إنشاء/تحديث User إذا لم يكن موجوداً
2. `contract.status` = `active`
3. بدء احتساب الإجازات من `start_date`
4. ظهور مدة الخدمة في Employee Summary

#### 6. ما يحدث عند تنفيذ المخالصة (execute):

1. `contract.status` = `closed`
2. `user.is_active` = `false`
3. تسجيل `last_working_day` و `termination_reason`
4. حساب EOS وتعويض الإجازات

---

Version: 38.0 (2026-02-20)

---

### Phase 39: Complete Language Unification ✅ (2026-02-20)

**إصلاح تضارب اللغة الشامل + تحسين صلاحيات المشرف**

#### 1. الملفات المُعدّلة:

| الملف | الإصلاحات |
|-------|-----------|
| `AttendancePage.js` | ترجمة كاملة (العنوان، الأزرار، الحالات، الجداول، الفلاتر) |
| `TransactionsPage.js` | ترجمة كاملة (STATUS_CONFIG، TYPE_CONFIG، STAGE_CONFIG) |
| `DashboardPage.js` | إضافة `leave_balance` للمشرف |
| `dashboard.py` (Backend) | إضافة رصيد الإجازات للمشرف |

#### 2. نظام الترجمة الجديد:

```javascript
// قبل:
const STATUS_CONFIG = {
  executed: { label: 'منفذة ✓' }  // ثابت
};

// بعد:
const STATUS_CONFIG = {
  executed: { label_ar: 'منفذة ✓', label_en: 'Executed ✓' }
};
const getStatusConfig = (status) => {
  const config = STATUS_CONFIG[status];
  return { ...config, label: lang === 'ar' ? config.label_ar : config.label_en };
};
```

#### 3. صلاحيات المشرف المُحسّنة:

**ما يراه المشرف:**
- ✅ رصيد إجازاته الشخصية
- ✅ طلبات الموظفين التابعين له
- ✅ قائمة الموظفين التابعين
- ❌ لا يرى تفاصيل إدارية
- ❌ لا يرى قائمة جميع الإجازات (25)

**API المُعدّل:**
```python
# dashboard.py
elif role == 'supervisor':
    # رصيد الإجازات الخاص بالمشرف
    leave_entries = await db.leave_ledger.find({...})
    stats['leave_balance'] = sum(...)
    # فريق العمل
    stats['team_size'] = len(direct_reports)
    stats['pending_approvals'] = ...
```

#### 4. قائمة النصوص المُترجمة:

**AttendancePage:**
- `الحضور والانصراف` ↔ `Attendance`
- `تسجيل دخول/خروج` ↔ `Check In/Out`
- `حاضر/غائب/متأخر/إجازة` ↔ `Present/Absent/Late/Leave`
- `يومي/أسبوعي/شهري/سنوي` ↔ `Daily/Weekly/Monthly/Yearly`
- جميع labels الجداول والفلاتر

**TransactionsPage:**
- `المعاملات` ↔ `Transactions`
- جميع الحالات (منفذة، مرفوضة، معلقة...)
- جميع الأنواع (طلب إجازة، نسيان بصمة...)
- جميع المراحل (المشرف، العمليات، المالية...)

---

Version: 39.0 (2026-02-20)


---

### Phase 39.1: Attendance & Penalties System Refactor ✅ (2026-02-20)

**التغييرات المُنفذة:**

#### 1. إعادة تسمية "حضور الفريق" إلى "الحضور والعقوبات":
- ✅ تحديث `translations.js`:
  - `teamAttendance`: "حضور الفريق" → "الحضور والعقوبات" / "Attendance & Penalties"
  - `attendancePenalties`: "الحضور والعقوبات" / "Attendance & Penalties"
  - `adminView`: "حضور الفريق" → "الحضور والعقوبات"
- ✅ تحديث `AttendancePage.js` - عنوان القسم الإداري
- ✅ تحديث `AppLayout.js` - إضافة `attendancePenalties` للمشرف

#### 2. إصلاح عمود "الحالة":
- ✅ تغيير `UNKNOWN` / "غير محدد" إلى `NOT_REGISTERED` / "لم يُسجل"
- ✅ تحديث `team_attendance.py` - الـ backend
- ✅ تحديث `TeamAttendancePage.js` - ألوان وترجمات الحالات

#### 3. صلاحيات المشرف (Supervisor):
- ✅ إضافة `supervisor` لجميع endpoints في `/api/team-attendance/`:
  - `/summary`, `/daily`, `/weekly`, `/monthly`
  - `/{employee_id}/update-status`, `/{employee_id}/trace/{date}`
  - `/employee/{employee_id}`
- ✅ فلترة الموظفين للمشرف:
  - المشرف يرى فقط الموظفين المسؤولين عنهم (`supervisor_id` = employee_id)
  - المدراء (sultan, naif, stas) يرون جميع الموظفين

#### 4. تحديث القائمة الجانبية:
- ✅ إضافة `attendancePenalties` في `NAV_ITEMS.supervisor`
- ✅ المشرف الآن يرى: dashboard, transactions, leave, attendance, tasks, myFinances, **attendancePenalties**

**الملفات المُحدّثة:**
- `/app/frontend/src/lib/translations.js` - الترجمات
- `/app/frontend/src/components/layout/AppLayout.js` - قائمة المشرف
- `/app/frontend/src/pages/AttendancePage.js` - عنوان القسم
- `/app/frontend/src/pages/TeamAttendancePage.js` - ألوان وترجمات الحالات
- `/app/backend/routes/team_attendance.py` - صلاحيات + فلترة المشرف

**التغييرات في Backend:**
```python
# فلترة الموظفين حسب المشرف
if user.get('role') == 'supervisor':
    emp_filter["supervisor_id"] = user.get('employee_id')
```

**الحالات الجديدة:**
| الحالة | العربية | الإنجليزية |
|--------|---------|------------|
| NOT_REGISTERED | لم يُسجل | Not Registered |
| PRESENT | حاضر | Present |
| ABSENT | غائب | Absent |
| LATE | متأخر | Late |
| ON_LEAVE | إجازة | On Leave |
| WEEKEND | عطلة نهاية أسبوع | Weekend |
| HOLIDAY | عطلة رسمية | Holiday |

---

Version: 39.1 (2026-02-20)
