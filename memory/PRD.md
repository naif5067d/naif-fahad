# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Build "DAR AL CODE HR OS," a mobile-first, enterprise-grade HR operating system for an engineering consultancy. The system must follow strict guidelines inspired by NIST RBAC, WCAG 2.2, Event Sourcing, Apple HIG, Material Design, and OWASP.

## Core Architecture

### Backend Stack
- **Framework**: FastAPI (Python)
- **Database**: MongoDB
- **Authentication**: JWT with Role-Based Access Control (RBAC)
- **PDF Generation**: ReportLab with Arabic font support (NotoSansArabic)

### Frontend Stack
- **Framework**: React.js
- **Styling**: Tailwind CSS + shadcn/ui components
- **HTTP Client**: Axios
- **State Management**: React Context (Auth, Language, Theme)

### Key Principles
- Every action is an immutable transaction recorded in append-only ledgers
- Employee profiles are read-only aggregations
- Strict role-based access control (NIST-style)

## User Roles (RBAC)

| Role | Username | Description |
|------|----------|-------------|
| STAS | stas | System Executor - highest privilege |
| CEO | mohammed | Chief Executive Officer |
| Ops Admin | sultan | Operations Administrator |
| Ops Strategic | naif | Operations Strategic |
| Finance | salah | Finance Manager |
| Supervisor | supervisor1 | Team Supervisor |
| Employee | employee1, employee2 | Regular employees |

## Phase 1 - Core Implementation ✅ COMPLETE

### Features Implemented
1. **Authentication & User Switching**
2. **Dashboard** with role-specific stats
3. **Transaction System** with workflow states
4. **Leave Management** with balance calculation
5. **Attendance System** with GPS validation
6. **STAS Mirror** with pre-checks
7. **UI/UX** with Light/Dark mode and RTL support

## Phase 2 - Stabilization Patch ✅ COMPLETE (2026-02-13)

### Issue 1: Approval Routing Fix ✅
### Issue 2: Full Language Switch ✅
### Issue 3: PDF Arabic Rendering + Preview ✅
### Issue 4: Mobile Decision Bar ✅
### Issue 5: Attendance Work Location ✅
### Issue 6: Manual Holiday Calendar ✅
### Issue 7: STAS Maintenance Tools ✅

## Backend Behavior Lock ✅ COMPLETE (2026-02-13)

### 1. WORKFLOW ENGINE (STRICT ORDER) ✅
- Transaction path: Employee → Supervisor → Sultan → Mohammed (if escalated) → STAS → Execute
- Skip supervisor if requester has no supervisor or IS the supervisor
- Self-approval prevention (cannot approve own transaction)
- Stage validation with role checks
- Only STAS can Execute or Cancel
- Executed transactions are immutable

**Implementation:**
- `/app/backend/utils/workflow.py` - Workflow engine with validation
- `validate_stage_actor()` - Validates actor can perform actions
- `should_skip_supervisor_stage()` - Determines supervisor skip logic
- `build_workflow_for_transaction()` - Builds actual workflow

### 2. LEAVE RULE ENGINE (PRE-VALIDATION) ✅
- Validates before transaction creation
- Rejects if: balance insufficient, dates overlap, employee inactive
- Auto-extends leave for holidays
- Sick leave tier tracking

**Implementation:**
- `/app/backend/utils/leave_rules.py` - Complete leave validation
- `get_employee_with_contract()` - Validates employee + active contract
- `validate_leave_request()` - Complete validation with balance, overlap checks
- `extend_leave_for_holidays()` - Holiday adjustment logic

### 3. LOCALIZATION LOCK ✅
- Complete AR/EN translations in `translations.js`
- All UI text from translation keys
- RTL/LTR direction switching
- STAS mirror and PDF support Arabic

### 4. PDF ARABIC FIX ✅
- NotoSansArabic font embedded (Regular + Bold)
- arabic-reshaper + python-bidi for RTL
- No squares, proper Arabic shaping

### 5. ATTENDANCE LOGIC LOCK ✅
- Server-side validation for check-in/out
- Validates: active employee, active contract, not expired
- Work location tracking (HQ/Project)
- Working hours validation (warning only)

**Implementation:**
- `/app/backend/utils/attendance_rules.py` - Complete attendance validation
- `validate_check_in()` - Validates employee, contract, location
- `validate_check_out()` - Validates check-in exists

### 6. CONTRACT & SETTLEMENT LOGIC ✅
- Contract determines employment status and leave eligibility
- Settlement: Only Sultan initiates → Mohammed approves → STAS executes
- Settlement locks employee account on execution
- Duplicate settlement prevention

**Implementation:**
- `/app/backend/routes/contracts.py` - Settlement workflow
- Workflow: `["ceo", "stas"]` after Sultan initiation

## API Endpoints

### Auth
- `GET /api/auth/users` - List active users
- `POST /api/auth/switch/{user_id}` - Switch user
- `GET /api/auth/me` - Current user

### Transactions
- `GET /api/transactions` - List transactions
- `POST /api/transactions/{id}/action` - Approve/Reject with validation
- `GET /api/transactions/{id}/pdf` - PDF download

### Leave
- `POST /api/leave/request` - Create with full pre-validation
- `GET /api/leave/balance` - Balance breakdown
- `GET /api/leave/holidays` - All holidays

### Attendance
- `POST /api/attendance/check-in` - With contract validation
- `POST /api/attendance/check-out` - With validation

### STAS
- `GET /api/stas/pending` - Pending executions
- `POST /api/stas/execute/{id}` - Execute transaction
- CRUD for holidays and maintenance

### Contracts
- `POST /api/contracts/settlement` - Sultan only

## Database Collections
- `users`, `employees`, `transactions`
- `leave_ledger`, `finance_ledger`, `attendance_ledger`
- `public_holidays`, `holidays` (manual)
- `contracts`, `finance_codes`, `counters`

## Phase 3 - UI/UX Enhancement + Work Locations ✅ COMPLETE (2026-02-13)

### Issue 1: Supervisor Workflow Fix ✅
- Fixed workflow to skip supervisor stage when:
  - Employee has no supervisor assigned
  - Employee's supervisor is themselves
  - **NEW:** Employee's supervisor has a non-supervisor role (e.g., Sultan, Naif)
- Implementation in `/app/backend/utils/workflow.py`

### Issue 2: Role-Based Status Colors ✅
- Status colors now match the role responsible for approval:
  - `pending_supervisor`: #1D4ED8 (Supervisor blue)
  - `pending_ops`: #F97316 (Sultan orange)
  - `pending_finance`: #0D9488 (Salah teal)
  - `pending_ceo`: #B91C1C (Mohammed red)
  - `pending_stas`: #7C3AED (STAS purple)
  - `executed`: #16A34A (Green)
  - `rejected`: #DC2626 (Red)

### Issue 3: Role Colors ✅
- Fixed role badge colors:
  - Employee: #3B82F6
  - Supervisor: #1D4ED8
  - Sultan: #F97316
  - Mohammed: #B91C1C
  - STAS: #7C3AED
  - Naif: #4D7C0F
  - Salah: #0D9488

### Issue 4: Full Arabic Localization ✅
- Added translations for:
  - Transaction types (`txTypes`)
  - Workflow stages (`stages`)
  - All status messages
- PDF rendering with proper Arabic text shaping

### Issue 5: Work Locations Feature ✅
- New page: `/work-locations`
- Map integration with Leaflet/OpenStreetMap
- Features:
  - Add/Edit/Delete work locations
  - Set location with map pin click
  - Configure work hours (from/to)
  - Configure work days
  - Set GPS radius (default 500m)
  - Assign employees to locations
  - STAS monitors, Sultan/Naif manage

**API Endpoints:**
- `GET /api/work-locations` - List all locations
- `POST /api/work-locations` - Create location (Sultan/Naif/STAS)
- `PUT /api/work-locations/{id}` - Update location
- `DELETE /api/work-locations/{id}` - Soft delete location
- `POST /api/work-locations/{id}/assign` - Assign employees (Sultan/Naif only)
- `GET /api/work-locations/employee/{id}` - Get employee's locations

## Database Collections
- `users`, `employees`, `transactions`
- `leave_ledger`, `finance_ledger`, `attendance_ledger`
- `public_holidays`, `holidays` (manual)
- `contracts`, `finance_codes`, `counters`
- `work_locations` (NEW)

## Future Tasks (Backlog)

### P1 - High Priority
- Supervisor Assignment Feature (Sultan/Naif can assign supervisors)
- Contract versioning and snapshots
- Warning ledger transactions
- Asset ledger transactions

### P2 - Medium Priority
- Geofencing validation for attendance check-in
- Finance statement reports
- Employee profile editing

---
Last Updated: 2026-02-13
Version: 4.0 (Phase 3 - UI/UX Enhancement + Work Locations Complete)
