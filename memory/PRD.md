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

**Changes in Phase 12:**
- **PDF Bilingual Support:** Complete rewrite of `pdf.py` to properly handle bilingual text
  - Arabic text: Reshaped using `arabic_reshaper` and `bidi` for proper RTL display
  - English text: Passed through without reshaping (was causing blank PDFs before)
  - Mixed text: Arabic parts are reshaped, English parts preserved
- **Company Branding in PDF:** Logo and company name now fetched from database and displayed in PDF header
- **STAS Barcode Signature:** STAS signature now uses Code128 barcode instead of QR code
- **Workflow Fix:** STAS can now execute transactions that were previously returned and re-approved
- **Cancel Logic Verified:** Cancelled transactions do not affect leave balance or trigger business logic

### Phase 13: System Maintenance Module ✅ (2026-02-14)

**Changes in Phase 13:**
- **System Maintenance Page:** New page at `/system-maintenance` (STAS only)
- **Storage Info:** Real-time statistics for all MongoDB collections
  - Total documents, transaction documents, protected documents
  - Size estimation per collection
- **Full System Archive:** 
  - Creates compressed JSON backup of entire database
  - Stores in `system_archives` collection
  - Downloadable as JSON file
  - Restorable at any time
- **Purge All Transactions:**
  - Deletes all transaction data (transactions, leave_ledger, finance_ledger, etc.)
  - Preserves protected data (users, employees, contracts, settings)
  - Resets counters and initial leave balances
  - Requires double confirmation ("DELETE ALL")
- **Maintenance Log:** Tracks all archive/purge/restore operations

### Phase 14: System Maintenance V2 + Date Format Audit ✅ (2026-02-14)

**P0 Changes - System Maintenance Enhancements:**
- **Total Storage Size:** Added `total_size_kb`, `transaction_size_kb`, `protected_size_kb` to storage-info API
- **Upload & Restore:** New endpoint `POST /api/maintenance/archives/upload` accepts JSON archive files
  - Validates file type (.json only)
  - Parses and restores all collections from uploaded archive
  - Creates restoration record in `system_archives`
  - Logs restoration operation in `maintenance_log`
- **UI/UX Overhaul:** Complete redesign of System Maintenance page
  - Dark gradient storage summary card with 5 metrics
  - Three action cards: Create Archive (blue), Upload/Restore (green), Purge (red)
  - Collections detail split view (transactions vs protected)
  - Enhanced archives list with download/restore/delete buttons

**P1 Changes - System-Wide Date Format Audit:**
- **New Date Utility:** `formatGregorianHijri()` and `formatGregorianHijriDateTime()` in `/lib/dateUtils.js`
  - Format: `DD/MM/YYYY (DD/MM/YYYY AH هـ)` e.g., `21/02/2026 (09/04/1447 AH هـ)`
  - Returns `{primary, secondary, combined}` for flexibility
- **Pages Updated:**
  - `TransactionsPage.js` - Transaction timestamps
  - `TransactionDetailPage.js` - Transaction created_at and approval timestamps
  - `LeavePage.js` - Holiday dates
  - `DashboardPage.js` - Next holiday date
  - `ContractsPage.js` - Contract start dates
  - `FinancePage.js` - Finance statement dates
  - `AttendancePage.js` - Attendance history dates
  - `FinancialCustodyPage.js` - Timeline event timestamps
  - `SystemMaintenancePage.js` - Archive and log timestamps

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

### P0 (Priority 0) - Next Phase
- **نظام المخالصة الكامل (Full Settlement System):**
  - واجهة إنشاء طلب المخالصة
  - عرض Snapshot في مرآة STAS
  - تنفيذ المخالصة بالكامل
  - PDF المخالصة النهائي

### P1 (Priority 1)
- CEO Dashboard - Escalated transactions view
- Employee Profile Card Enhancement

### P2 (Priority 2)
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
Version: 15.0 (2026-02-14)
