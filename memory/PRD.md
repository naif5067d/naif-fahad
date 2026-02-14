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
users, employees, contracts, finance_codes, public_holidays, 
holidays, work_locations, settings, counters
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

## Remaining Tasks

### P1 (Priority 1)
- Employee Profile Card (بطاقة الموظف)
- Mohammed CEO Dashboard - Escalated transactions view
- Supervisor Assignment UI - Allow Sultan/Naif to assign supervisors
- Contract Deletion for STAS

### P2 (Priority 2)
- New Transaction Types (leave/attendance subtypes)
- STAS Financial Custody Mirror
- Geofencing enforcement
- System-wide Arabic UI audit

## Key Files
- `/app/backend/utils/pdf.py` - PDF generator with bilingual support (FIXED)
- `/app/backend/utils/workflow.py` - validate_stage_actor (STAS excluded from already_acted)
- `/app/backend/routes/transactions.py` - PDF endpoint with branding fetch
- `/app/backend/routes/stas.py` - STAS execution with branding fetch
- `/app/frontend/src/pages/CompanySettingsPage.js` - Company settings UI

## Test Reports
- `/app/test_reports/iteration_13.json` - Latest test results (100% pass)
- `/app/backend/tests/test_iteration13_features.py` - Backend tests

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

---
Version: 13.0 (2026-02-14)
