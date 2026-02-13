# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Build "DAR AL CODE HR OS," a mobile-first, enterprise-grade HR operating system for an engineering consultancy (Dar Al Code). Strict RBAC, immutable transaction records, Arabic-first UI.

## Core Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Rule:** Any transaction not executed by STAS is not considered valid

## User Roles

| Role | Username | Permissions |
|------|----------|-------------|
| STAS | stas | System Executor - final authority |
| CEO | mohammed | Escalated approvals only (accept/reject) |
| Ops Admin | sultan | Operations, creates custodies, escalates |
| Ops Strategic | naif | Operations support, creates tangible custody |
| Finance | salah | Audit financial custodies, edit codes |
| Supervisor | supervisor1 | Team leave approvals |
| Employee | employee1/2 | Self-service, accept/reject custody |

## Implemented Features

### Phase 1-3 ✅ Core + UI (2026-02-13)
- RBAC, transactions, ledger systems
- Arabic localization, RTL PDF support
- Status color-coding by approver role
- Work Locations backend

### Phase 4 ✅ P0 Business Logic (2026-02-13)
- Escalation system (Sultan → Mohammed → STAS)
- Tangible custody lifecycle
- Financial custody (old version)

### Phase 5 ✅ Financial Custody V2 + Code Mgmt (2026-02-13)

#### Financial Custody (60 Code) - Administrative
- **No employee linkage** - purely administrative
- **Creation:** Sultan / Naif / Mohammed
- **Expense tracking:** Sultan adds expenses (code + amount), running balance
- **Manual code input:** Type code → auto-lookup → if new, define it
- **Workflow:** Created → Received (active) → [Add expenses] → Submit Audit → Salah audits/edits → Mohammed approves → STAS executes
- **Carry-forward:** Remaining balance auto-carries to next custody
- **API:** `/api/financial-custody/*`

#### Finance Code Management
- Codes 1-60 pre-seeded, 61+ user-created
- Edit codes: Sultan, Naif, Salah, STAS
- API: `PUT /api/finance/codes/{id}`, `POST /api/finance/codes/add`

#### Dashboard → "لوحتي" (My Board)
- Renamed for all users
- Next upcoming holiday card for everyone

#### Leave Visibility
- Holidays table hidden from employees
- Only admin sees full leave management

## Key API Endpoints

### Financial Custody
- `POST /api/financial-custody` - Create
- `POST /api/financial-custody/{id}/receive` - Receive
- `POST /api/financial-custody/{id}/expense` - Add expense
- `DELETE /api/financial-custody/{id}/expense/{eid}` - Remove expense
- `POST /api/financial-custody/{id}/submit-audit` - Send to Salah
- `POST /api/financial-custody/{id}/audit` - Salah audits
- `POST /api/financial-custody/{id}/approve` - Mohammed approves
- `POST /api/financial-custody/{id}/execute` - STAS executes

### Transactions (Escalation)
- `POST /api/transactions/{id}/action` - approve/reject/escalate

### Tangible Custody
- `POST /api/custody/tangible` - Create (Sultan/Naif)
- `POST /api/custody/tangible/return` - Return (Sultan)

## Database Collections
- `users`, `employees`, `transactions`
- `leave_ledger`, `finance_ledger`, `attendance_ledger`
- `public_holidays`, `holidays`, `contracts`, `finance_codes`, `counters`
- `work_locations`, `custody_ledger`, `custody_financial`

## Upcoming Tasks

### P1 - High Priority
- Employee Profile Card (بطاقة الموظف)
- Mohammed CEO Dashboard (escalated transactions view)
- Supervisor Assignment UI
- New Transaction Types (detailed leave + attendance types)
- Contract Deletion for STAS

### P2 - Medium Priority
- Complete Work Locations Map Feature (Leaflet)
- PDF Formatting Improvement
- Geofencing for attendance

### Future
- Contract versioning & snapshots
- Warning & Asset ledger transactions

---
Last Updated: 2026-02-13
Version: 6.0
