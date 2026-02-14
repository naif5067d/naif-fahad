# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Mobile-first, enterprise-grade HR operating system for Dar Al Code engineering consultancy. Strict RBAC, immutable transactions, Arabic-first UI.

## Core Rule
Any transaction not executed by STAS is not considered valid.

## Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Map:** react-leaflet + OpenStreetMap

## Roles: stas, mohammed (CEO), sultan, naif, salah, supervisor1, employee1/2

## Implemented (All Tested)

### Phase 1-3: Core + UI ✅
### Phase 4: P0 Business Logic ✅ (Escalation, Tangible Custody)
### Phase 5: Financial Custody V2 ✅
### Phase 6: UI/UX Overhaul ✅ (2026-02-14)
### Phase 7: Map Feature & Language Fix ✅ (2026-02-14)

**Changes in Phase 7:**
- Work Locations Map: Employees can now see assigned work locations on Attendance page
- Employee Assignment: Admin (Sultan/Naif) can assign employees to locations via checkboxes
- Language Consistency: STAS displays as "ستاس" in Arabic mode across all UI elements
- Status badges properly translate based on selected language
- Fixed language mixing issues throughout the application

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

## Upcoming Tasks

### P0 (Next Priority)
- Complete UI/UX Redesign - Apply modern design with new color scheme (blue, green, gray, black)
- PDF Formatting - Professional layout with proper structure and fonts

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
Version: 8.0 (2026-02-14)
