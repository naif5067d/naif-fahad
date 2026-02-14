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
### Phase 11: PDF Arabic Text Fix & STAS Execution Flow ✅ (2026-02-14)

**Changes in Phase 11:**
- **PDF Arabic Fix:** Used `arabic_reshaper` and `bidi` libraries for proper RTL Arabic text display
- **STAS Execution Bug:** Fixed "You have already taken an action" error - STAS is now excluded from this check
- **Pre-Checks Logic:** Updated to count 'escalate' actions as valid approvals
- **STAS Pending API:** Updated to include both `current_stage=stas` and `status=pending_stas`
- **PDF rowHeights Bug:** Fixed dynamic row heights for stamp_data to avoid ValueError

## Key API Endpoints
- `/api/financial-custody/*` - Full custody lifecycle
- `/api/custody/tangible/*` - Tangible custody
- `/api/transactions/*/action` - approve/reject/escalate/return_to_sultan/return_to_ceo
- `/api/leave/holidays` - CRUD for holidays
- `/api/attendance/admin?period=daily|weekly|monthly|yearly` - Admin view
- `/api/finance/codes/*` - Code CRUD
- `/api/dashboard/next-holiday` - Next upcoming holiday
- `/api/work-locations` - Work location CRUD
- `/api/settings/branding` - Company branding (GET/PUT/POST logo/DELETE logo)
- `/api/transactions/{id}/pdf?lang=ar|en` - PDF generation
- `/api/stas/pending` - Get pending transactions for STAS
- `/api/stas/mirror/{id}` - Get mirror data for transaction
- `/api/stas/execute/{id}` - Execute transaction

## Collections
users, employees, transactions, leave_ledger, finance_ledger, attendance_ledger, public_holidays, holidays, contracts, finance_codes, counters, work_locations, custody_ledger, custody_financial, settings

## Completed Bug Fixes
1. ✅ Map/Work Locations - Employees see assigned locations
2. ✅ Language Mixing - STAS/CEO show same in both languages
3. ✅ UI/UX Overhaul - Modern, professional design
4. ✅ PDF Formatting - Professional layout with QR signatures
5. ✅ Time Display - Saudi timezone (Asia/Riyadh, UTC+3)
6. ✅ Approval Workflow - No duplicate actions
7. ✅ CEO Rejection Flow - Goes to STAS
8. ✅ STAS Return Flow - Properly resets rejection markers
9. ✅ Complex Fields Hidden - No [object Object] in UI
10. ✅ Company Branding API - Full CRUD for logo/name/slogan
11. ✅ PDF Arabic Text - Using arabic_reshaper and bidi for proper RTL
12. ✅ STAS Execution - No more "already acted" error for STAS
13. ✅ Pre-Checks Escalation - Escalate counts as valid approval

## Remaining Tasks

### P1
- Employee Profile Card (بطاقة الموظف)
- Mohammed CEO Dashboard - Escalated transactions view
- Supervisor Assignment UI - Allow Sultan/Naif to assign supervisors
- Contract Deletion for STAS

### P2
- New Transaction Types (leave/attendance subtypes)
- STAS Financial Custody Mirror
- Geofencing enforcement

## Key Files
- `/app/backend/utils/pdf.py` - PDF generator with arabic_reshaper and bidi
- `/app/backend/utils/workflow.py` - validate_stage_actor (STAS excluded from already_acted)
- `/app/backend/routes/stas.py` - STAS Mirror and execution with updated pre-checks
- `/app/frontend/src/pages/STASMirrorPage.js` - STAS Mirror UI
- `/app/frontend/src/pages/CompanySettingsPage.js` - Company settings UI

## Test Reports
- `/app/test_reports/iteration_12.json` - Latest test results (100% pass)
- `/app/backend/tests/test_iteration12_features.py` - Backend tests

---
Version: 12.0 (2026-02-14)
