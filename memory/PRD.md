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
### Phase 10: Company Settings & Workflow Fix ✅ (2026-02-14)

**Changes in Phase 10:**
- **Company Settings Page:** New page `/company-settings` for STAS to manage company logo, name, and slogan (Arabic/English)
- **PDF Generator Fix:** Complete rewrite with proper Arabic fonts (Noto Naskh Arabic), better layout, QR/Barcode signatures
- **Workflow Return Logic:** Fixed STAS return actions to properly reset rejection markers, allowing returned managers to act again
- **Transaction Detail Fix:** Hidden complex fields like `sick_tier_info` from UI display
- **Quick Actions:** Added "Company Settings" button to STAS dashboard

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
- `/app/frontend/src/pages/CompanySettingsPage.js` - Company settings UI
- `/app/frontend/src/lib/dateUtils.js` - Saudi timezone formatting
- `/app/frontend/src/components/Timeline.js` - Timeline component
- `/app/backend/routes/settings.py` - Company branding API
- `/app/backend/routes/transactions.py` - Transaction workflow
- `/app/backend/utils/pdf.py` - PDF generator with Arabic fonts

## Test Reports
- `/app/test_reports/iteration_11.json` - Latest test results (100% pass)
- `/app/backend/tests/test_iteration11_features.py` - Backend tests

---
Version: 11.0 (2026-02-14)
