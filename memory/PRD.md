# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Mobile-first, enterprise-grade HR operating system for Dar Al Code engineering consultancy. Strict RBAC, immutable transactions, Arabic-first UI.

## Core Rule
Any transaction not executed by STAS is not considered valid.

## Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Map:** react-leaflet + OpenStreetMap

## Design System (Updated 2026-02-14)
- **Colors:** 
  - Navy: #1E3A5F (primary)
  - Black: #0A0A0B (text)
  - Gray: #6B7280 (muted)
  - Lavender: #A78BFA (accent)
- **Fonts:** Manrope (English), IBM Plex Sans Arabic (Arabic)
- **Components:** Gradient hero cards, card-based layouts, bottom mobile nav

## Roles
stas, mohammed (CEO), sultan, naif, salah, supervisor1, employee1/2

## Implemented (All Tested)

### Phase 1-3: Core + UI ✅
### Phase 4: P0 Business Logic ✅ (Escalation, Tangible Custody)
### Phase 5: Financial Custody V2 ✅
### Phase 6: UI/UX Overhaul ✅ (2026-02-14)
### Phase 7: Map Feature & Language Fix ✅ (2026-02-14)
### Phase 8: Complete UI/UX Redesign ✅ (2026-02-14)

**Changes in Phase 8:**
- Complete visual redesign with new color scheme (Navy, Lavender, Gray, Black)
- Gradient hero card on dashboard with user welcome and key stats
- Quick actions grid with colored icons
- Mobile-first bottom navigation bar
- Modern card-based transaction list
- Updated attendance page with clear check-in/out buttons
- RTL layout support for Arabic
- Dark mode support
- Professional fonts (Manrope + IBM Plex Sans Arabic)
- Larger, more readable text throughout
- Badge-style status indicators

## Key API Endpoints
- `/api/financial-custody/*` - Full custody lifecycle
- `/api/custody/tangible/*` - Tangible custody
- `/api/transactions/*/action` - approve/reject/escalate
- `/api/leave/holidays` - CRUD (POST/PUT/DELETE) for Sultan/Naif/STAS
- `/api/attendance/admin?period=daily|weekly|monthly|yearly` - Admin view
- `/api/finance/codes/*` - Code CRUD
- `/api/dashboard/next-holiday` - Next upcoming holiday
- `/api/work-locations` - Work location CRUD
- `/api/work-locations/employee/{empId}` - Get assigned locations for employee

## Collections
users, employees, transactions, leave_ledger, finance_ledger, attendance_ledger, public_holidays, holidays, contracts, finance_codes, counters, work_locations, custody_ledger, custody_financial

## Completed Bug Fixes
1. ✅ Map/Work Locations - Employees see assigned locations
2. ✅ Language Mixing - STAS properly shows as "ستاس" in Arabic
3. ✅ UI/UX Overhaul - Modern, professional design implemented

## Remaining Issues
1. ⚠️ PDF Formatting - Needs professional layout with proper structure and fonts

## Upcoming Tasks

### P0 (Next Priority)
- PDF Formatting - Professional layout with proper structure, fonts, and alignment

### P1
- Employee Profile Card (بطاقة الموظف)
- Mohammed CEO Dashboard
- Supervisor Assignment UI
- New Transaction Types (leave/attendance subtypes)
- Contract Deletion for STAS

### P2
- STAS Financial Custody Mirror
- Geofencing enforcement

---
Version: 9.0 (2026-02-14)
