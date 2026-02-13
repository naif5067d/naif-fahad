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
- **Core Rule: Any transaction not executed by STAS is not considered valid**

## User Roles (RBAC)

| Role | Username | Description |
|------|----------|-------------|
| STAS | stas | System Executor - highest privilege |
| CEO | mohammed | Chief Executive Officer - Escalated approvals only |
| Ops Admin | sultan | Operations Administrator |
| Ops Strategic | naif | Operations Strategic |
| Finance | salah | Finance Manager |
| Supervisor | supervisor1 | Team Supervisor |
| Employee | employee1, employee2 | Regular employees |

## Phase 1 - Core Implementation ✅ COMPLETE
## Phase 2 - Stabilization Patch ✅ COMPLETE (2026-02-13)
## Phase 3 - UI/UX Enhancement + Work Locations ✅ COMPLETE (2026-02-13)

## Phase 4 - P0 Business Logic ✅ COMPLETE (2026-02-13)

### 1. Escalation System ✅
- Sultan/Naif can "escalate" transactions from ops stage to CEO (Mohammed)
- When escalated: Sultan's permissions freeze for that transaction
- Mohammed can only: Accept (→ STAS) or Reject (→ back to ops)
- Mohammed does NOT edit or execute
- **Workflow:** Employee → Supervisor → Sultan → [Escalate] → Mohammed → STAS

### 2. Financial Custody (60 Code) ✅
- **Created by Sultan ONLY** (Naif cannot create)
- **Manual code input** (not dropdown): type code number, auto-lookup shows definition if found
- If code is new → user defines it and it's saved automatically
- **Workflow:** Sultan creates → `["finance", "ceo", "stas"]`
  - Salah (Finance) audits and can edit
  - Mohammed (CEO) approves
  - STAS executes (final, immutable)
- **API:** POST /api/finance/transaction, GET /api/finance/codes/lookup/{code}

### 3. Tangible Custody ✅
- **Created by Sultan or Naif** (NOT Mohammed)
- Sent to employee for acceptance
- **Reject → cancelled immediately**
- **Accept → STAS → recorded in custody_ledger**
- **Return flow:** Sultan presses "Received" → STAS → removed from employee
- **Active custody blocks settlement (مخالصة)**
- **Workflow:** `["employee_accept", "stas"]`
- **Return Workflow:** `["stas"]`
- **API:** POST /api/custody/tangible, POST /api/custody/tangible/return, GET /api/custody/all

### 4. Mohammed's Role ✅
- Sees ONLY escalated transactions and finance_60/settlement requiring approval
- Does NOT see regular transactions
- Does NOT edit data
- Accept → STAS, Reject → back to ops

## Database Collections
- `users`, `employees`, `transactions`
- `leave_ledger`, `finance_ledger`, `attendance_ledger`
- `public_holidays`, `holidays` (manual)
- `contracts`, `finance_codes`, `counters`
- `work_locations`
- `custody_ledger` (NEW - tangible custody records)

## API Endpoints

### Auth
- `GET /api/auth/users` - List active users
- `POST /api/auth/switch/{user_id}` - Switch user
- `GET /api/auth/me` - Current user

### Transactions
- `GET /api/transactions` - List transactions (role-filtered)
- `POST /api/transactions/{id}/action` - Approve/Reject/Escalate
- `GET /api/transactions/{id}/pdf` - PDF download

### Leave
- `POST /api/leave/request` - Create leave request
- `GET /api/leave/balance` - Balance breakdown

### Finance
- `POST /api/finance/transaction` - Create financial custody (Sultan only)
- `GET /api/finance/codes/lookup/{code}` - Manual code lookup
- `GET /api/finance/codes` - List all finance codes
- `GET /api/finance/statement/{employee_id}` - Finance statement

### Custody
- `POST /api/custody/tangible` - Create tangible custody (Sultan/Naif)
- `POST /api/custody/tangible/return` - Return custody (Sultan)
- `GET /api/custody/employee/{id}` - Employee's custodies
- `GET /api/custody/all` - All custodies
- `GET /api/custody/check-clearance/{id}` - Check clearance eligibility

### STAS
- `GET /api/stas/pending` - Pending executions
- `POST /api/stas/execute/{id}` - Execute transaction
- Holiday & maintenance CRUD

### Work Locations
- CRUD at `/api/work-locations`

## Upcoming Tasks

### P1 - High Priority
- Employee Profile Card (بطاقة الموظف): attendance, custody, transactions view
- Mohammed CEO Dashboard: dedicated view for escalated transactions
- Supervisor Assignment UI (Sultan/Naif can assign supervisors)
- Contract Deletion for STAS
- New Transaction Types (Leave subtypes, Attendance subtypes)

### P2 - Medium Priority
- Complete Work Locations Map Feature (Leaflet)
- PDF Formatting Improvement
- Geofencing validation for attendance check-in

### Future
- Contract versioning and snapshots
- Warning & Asset ledger transactions

---
Last Updated: 2026-02-13
Version: 5.0 (Phase 4 - P0 Business Logic Complete)
