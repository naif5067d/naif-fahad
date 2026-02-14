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
- **Timezone:** Asia/Riyadh (UTC+3) for all date/time display

## Roles
stas, mohammed (CEO), sultan, naif, salah, supervisor1, employee1/2

## Implemented Features

### Phase 1-3: Core + UI ✅
### Phase 4: P0 Business Logic ✅ (Escalation, Tangible Custody)
### Phase 5: Financial Custody V2 ✅
### Phase 6: UI/UX Overhaul ✅ (2026-02-14)
### Phase 7: Map Feature & Language Fix ✅ (2026-02-14)
### Phase 8: Complete UI/UX Redesign ✅ (2026-02-14)
### Phase 9: PDF & Transactions Enhancement ✅ (2026-02-14)

**Changes in Phase 9:**
- **Professional PDF Generator:** Complete rewrite with proper alignment, fonts, Saudi timezone, bilingual headers
- **Transactions Page Redesign:** Clean cards, status badges, employee info, Saudi timezone dates
- **Timeline Component:** New component with icons, event translations, actor names
- **Saudi Timezone Utility:** `dateUtils.js` with Intl.DateTimeFormat for Asia/Riyadh
- **Company Branding API:** `/api/settings/branding` - STAS can update logo, company name, slogan
- **Approval Workflow Fix:** Prevent duplicate actions - users can only act once per transaction

## Key API Endpoints
- `/api/financial-custody/*` - Full custody lifecycle
- `/api/custody/tangible/*` - Tangible custody
- `/api/transactions/*/action` - approve/reject/escalate (with duplicate action prevention)
- `/api/leave/holidays` - CRUD (POST/PUT/DELETE) for Sultan/Naif/STAS
- `/api/attendance/admin?period=daily|weekly|monthly|yearly` - Admin view
- `/api/finance/codes/*` - Code CRUD
- `/api/dashboard/next-holiday` - Next upcoming holiday
- `/api/work-locations` - Work location CRUD
- `/api/settings/branding` - Company branding (GET/PUT, logo upload)

## Collections
users, employees, transactions, leave_ledger, finance_ledger, attendance_ledger, public_holidays, holidays, contracts, finance_codes, counters, work_locations, custody_ledger, custody_financial, settings

## Completed Bug Fixes
1. ✅ Map/Work Locations - Employees see assigned locations
2. ✅ Language Mixing - STAS properly shows as "ستاس" in Arabic
3. ✅ UI/UX Overhaul - Modern, professional design implemented
4. ✅ PDF Formatting - Professional layout with bilingual headers, proper tables
5. ✅ Time Display - All times now use Saudi timezone (Asia/Riyadh, UTC+3)
6. ✅ Approval Workflow - Users cannot approve/reject same transaction twice

## Remaining Issues
None critical.

## Upcoming Tasks

### P1
- Employee Profile Card (بطاقة الموظف)
- Mohammed CEO Dashboard - Escalated transactions view
- Supervisor Assignment UI - Allow Sultan/Naif to assign supervisors
- Contract Deletion for STAS

### P2
- New Transaction Types (leave/attendance subtypes)
- STAS Financial Custody Mirror
- Geofencing enforcement

## New Files Created (Phase 9)
- `/app/frontend/src/lib/dateUtils.js` - Saudi timezone formatting utilities
- `/app/frontend/src/components/Timeline.js` - Professional timeline component
- `/app/backend/routes/settings.py` - Company branding API

## Key Technical Details

### Saudi Timezone Implementation
```javascript
// Frontend: /app/frontend/src/lib/dateUtils.js
const SAUDI_TIMEZONE = 'Asia/Riyadh';
new Intl.DateTimeFormat('en-GB', { timeZone: SAUDI_TIMEZONE, ... })
```

```python
# Backend: /app/backend/utils/pdf.py
from datetime import timedelta
saudi_time = dt + timedelta(hours=3)
```

### Approval Workflow Prevention
```python
# Backend: /app/backend/utils/workflow.py
# Checks approval_chain for existing user action before allowing new action
for approval in approval_chain:
    if approval.get('approver_id') == actor_user_id:
        return {"valid": False, "error_detail": "You have already taken an action"}
```

---
Version: 10.0 (2026-02-14)
