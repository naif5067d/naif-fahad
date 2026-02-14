# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Mobile-first, enterprise-grade HR operating system for Dar Al Code engineering consultancy. Strict RBAC, immutable transactions, Arabic-first UI.

## Core Rule
Any transaction not executed by STAS is not considered valid.

## Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Map:** react-leaflet + OpenStreetMap (planned)

## Roles: stas, mohammed (CEO), sultan, naif, salah, supervisor1, employee1/2

## Implemented (All Tested)

### Phase 1-3: Core + UI ✅
### Phase 4: P0 Business Logic ✅ (Escalation, Tangible Custody)
### Phase 5: Financial Custody V2 ✅
### Phase 6: UI/UX Overhaul ✅ (2026-02-14)

**Changes in Phase 6:**
- Financial Custody: Cards → Professional Excel-like TABLE with summary stats
- Expense Sheet: Professional table with running balance column
- Timeline: Vertical line + colored dots across entire app
- Leave Holidays: CRUD for Sultan/Naif/STAS (add/edit/delete)
- Employees hidden from holiday table
- Attendance Admin: Daily/Weekly/Monthly/Yearly table for admin roles
- Dashboard renamed to "لوحتي" (My Board)
- Navigation: "العهدة المالية" (Financial Custody)

## Key API Endpoints
- `/api/financial-custody/*` - Full custody lifecycle
- `/api/custody/tangible/*` - Tangible custody
- `/api/transactions/*/action` - approve/reject/escalate
- `/api/leave/holidays` - CRUD (POST/PUT/DELETE) for Sultan/Naif/STAS
- `/api/attendance/admin?period=daily|weekly|monthly|yearly` - Admin view
- `/api/finance/codes/*` - Code CRUD
- `/api/dashboard/next-holiday` - Next upcoming holiday

## Collections
users, employees, transactions, leave_ledger, finance_ledger, attendance_ledger, public_holidays, holidays, contracts, finance_codes, counters, work_locations, custody_ledger, custody_financial

## Upcoming Tasks

### P1
- Employee Profile Card (بطاقة الموظف)
- Mohammed CEO Dashboard
- Supervisor Assignment UI
- New Transaction Types (leave/attendance subtypes)
- Contract Deletion for STAS
- Work Locations: Leaflet map, employee assignment, GPS validation

### P2
- PDF redesign (different templates per type)
- STAS Financial Custody Mirror
- Geofencing enforcement

---
Version: 7.0 (2026-02-14)
