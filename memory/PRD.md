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
   - JWT-based authentication
   - User switcher dropdown (no login page)
   - Role-based navigation

2. **Dashboard**
   - Role-specific statistics cards
   - Recent transactions list
   - Pending approvals count

3. **Transaction System**
   - Unique ref_no generation (TXN-YEAR-NNNN)
   - Workflow states: Created → Supervisor → Ops → Finance → CEO → STAS Execute
   - Timeline tracking
   - Approval chain recording

4. **Leave Management**
   - Leave request creation
   - Balance calculation with holiday adjustment
   - Public holiday list

5. **Attendance System**
   - GPS-based check-in/out
   - Geofence validation
   - History tracking

6. **STAS Mirror**
   - Pre-checks verification
   - Before/After projections
   - Trace links (Veins)
   - Transaction execution

7. **UI/UX**
   - Light/Dark mode
   - RTL Arabic support
   - Mobile-responsive design

## Phase 2 - Stabilization Patch ✅ COMPLETE (2026-02-13)

### Issue 1: Approval Routing Fix ✅
- Workflow correctly skips supervisor step if:
  - Requester has no supervisor assigned (e.g., Sultan, Salah)
  - Requester IS the supervisor of the team
- Implementation: `check_if_requester_is_supervisor()` function in transactions.py

### Issue 2: Full Language Switch ✅
- Complete Arabic/English localization
- All UI elements translated (navigation, buttons, labels, status badges)
- No mixed languages in any view
- Implementation: Comprehensive translations.js with ~150+ translation keys

### Issue 3: PDF Arabic Rendering + Preview ✅
- Arabic fonts embedded (NotoSansArabic-Regular.ttf, NotoSansArabic-Bold.ttf)
- RTL text processing with arabic-reshaper and python-bidi
- Preview button added alongside Download
- Bilingual headers in PDF (English / Arabic)

### Issue 4: Mobile Decision Bar ✅
- Sticky footer on mobile viewports (< md breakpoint)
- Shows Approve/Reject buttons for approvers
- Shows Preview/Execute buttons for STAS
- Fixed positioning at bottom with proper z-index

### Issue 5: Attendance Work Location ✅
- Work Location dropdown with options: HQ, Project
- Required before check-in
- Stored in attendance_ledger
- Displayed in attendance history

### Issue 6: Manual Holiday Calendar ✅
- STAS-only Holiday Management tab
- Add holiday with: English name, Arabic name, Date
- Delete individual holidays
- Manual holidays affect leave calculations
- Source indicator (System vs Manual)

### Issue 7: STAS Maintenance Tools ✅
- System Maintenance tab in STAS Mirror
- Purge Transactions: Requires "CONFIRM" text input
- Archived Users: List and restore functionality
- Protected admin users cannot be archived

## API Endpoints

### Auth
- `GET /api/auth/users` - List all active users
- `POST /api/auth/switch/{user_id}` - Switch to user
- `GET /api/auth/me` - Get current user

### Transactions
- `GET /api/transactions` - List transactions
- `GET /api/transactions/{id}` - Get transaction
- `POST /api/transactions/{id}/action` - Approve/Reject
- `GET /api/transactions/{id}/pdf` - Download PDF

### Leave
- `POST /api/leave/request` - Create leave request
- `GET /api/leave/balance` - Get leave balance
- `GET /api/leave/holidays` - Get all holidays (system + manual)

### Attendance
- `POST /api/attendance/check-in` - Check in with work_location
- `POST /api/attendance/check-out` - Check out
- `GET /api/attendance/today` - Get today's status
- `GET /api/attendance/history` - Get attendance history

### STAS
- `GET /api/stas/pending` - Get pending executions
- `GET /api/stas/mirror/{id}` - Get transaction mirror
- `POST /api/stas/execute/{id}` - Execute transaction
- `GET /api/stas/holidays` - Get manual holidays
- `POST /api/stas/holidays` - Add holiday
- `DELETE /api/stas/holidays/{id}` - Delete holiday
- `POST /api/stas/maintenance/purge-transactions` - Purge all transactions
- `POST /api/stas/users/{id}/archive` - Archive user
- `POST /api/stas/users/{id}/restore` - Restore user
- `GET /api/stas/users/archived` - Get archived users

## Database Collections
- `users` - User accounts with roles
- `employees` - Employee records with supervisor_id
- `transactions` - All transaction records
- `leave_ledger` - Leave balance entries
- `finance_ledger` - Finance entries
- `attendance_ledger` - Attendance records
- `public_holidays` - System holidays (seeded)
- `holidays` - Manual holidays (STAS-managed)
- `contracts` - Employee contracts
- `finance_codes` - 60 finance codes
- `counters` - Sequence counters

## Future Tasks (Backlog)

### P1 - High Priority
- Contract versioning and snapshots
- Employee settlement workflow
- Warning ledger transactions
- Asset ledger transactions

### P2 - Medium Priority
- Geofencing for project locations with map integration
- Finance statement reports
- Employee profile editing

### P3 - Low Priority
- Email notifications
- Export to Excel
- Audit log viewer

---
Last Updated: 2026-02-13
Version: 2.0 (Stabilization Patch Complete)
