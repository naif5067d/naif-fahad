# DAR AL CODE HR OS - Product Requirements Document

## Problem Statement
Build a mobile-first HR Operating System for Dar Al Code Engineering Consultancy with NIST RBAC, append-only ledgers, transaction workflows, STAS execution gate, and PDF generation with hash integrity.

## Architecture
- **Backend**: FastAPI + MongoDB (modular routes architecture)
- **Frontend**: React + Tailwind CSS + shadcn/ui components
- **Auth**: JWT with bcrypt password hashing
- **Storage**: MongoDB with append-only ledger collections

## User Personas & Roles (LOCKED)
| Role | Username | Access Level |
|------|----------|-------------|
| Employee | employee1, employee2 | Self-only transactions, leave, attendance |
| Supervisor | supervisor1 | Direct reports + own transactions |
| Ops Admin | sultan | All operations + employee for attendance |
| Ops Strategic | naif | All operations |
| Finance | salah | Finance transactions only |
| CEO | mohammed | CEO-level approvals only |
| STAS | stas | Governance executor - full system access |

## Core Requirements (Static)
1. RBAC with strict role-based UI + API access
2. Transaction-based system with ref_no, immutable timeline, approval chain
3. Append-only ledgers (Leave, Finance, Attendance, Warning, Asset)
4. STAS Mirror with pre-checks, trace links, before/after projection
5. PDF A4 generation with SHA-256 hash + integrity ID
6. Leave management with holiday compensation
7. GPS attendance with geofence checking
8. 60 Code Finance catalog (codes 1-60 are official, 61+ require transaction)
9. Contracts + Settlement flow
10. Arabic RTL + English LTR toggle
11. Light/Dark theme with strict WCAG contrast
12. Mobile-first responsive design

## What's Been Implemented (Feb 12, 2026)
### Backend
- [x] JWT Authentication (login, me, change-password)
- [x] RBAC middleware with role-based access control
- [x] Transaction engine with workflow stages (Created → Supervisor → Ops → Finance → CEO → STAS)
- [x] Leave management with balance checking + holiday compensation
- [x] Attendance GPS check-in/out with geofence validation
- [x] 60 Code Finance catalog + transactions
- [x] Contracts management + Settlement flow (Sultan → CEO → STAS)
- [x] STAS Mirror with pre-checks, trace links, before/after projection
- [x] Idempotent STAS Execute
- [x] PDF generation with SHA-256 hash + integrity ID
- [x] Append-only ledger system (leave, finance, attendance, warning, asset)
- [x] Employee Profile 360 aggregation endpoint
- [x] Database seeding with all users, employees, finance codes, holidays

### Frontend
- [x] Login page (no signup, clean design)
- [x] Role-based dashboard with summary cards (max 3) + transactions table
- [x] Transaction inbox with filters (status, type, search)
- [x] Transaction detail page with timeline + approval chain
- [x] Leave management (balance cards, request form, holidays)
- [x] Attendance (GPS detection, check-in/out, history)
- [x] 60 Code Finance (catalog table, statement, create transaction)
- [x] Contracts (create contract, settlement flow)
- [x] STAS Mirror (pre-checks PASS/FAIL, before/after, trace links, execute)
- [x] Employee management (STAS can edit/enable/disable)
- [x] Settings page (theme + language)
- [x] Light/Dark theme with CSS variables
- [x] Arabic RTL + English LTR toggle with full translations
- [x] Mobile-first responsive layout (sidebar desktop, hamburger mobile)

## Prioritized Backlog

### P0 (Critical - Next)
- Employee Profile 360 page (frontend)
- Full workflow test: employee creates → supervisor approves → ops approves → STAS executes

### P1 (High Priority)
- Attendance GPS map visualization
- Contract template management by STAS
- Full History Pack PDF for settlement
- More comprehensive Arabic translations
- Desktop keyboard shortcuts

### P2 (Medium Priority)
- Bulk operations for STAS
- Reporting dashboard with charts
- Export ledger data to Excel
- Notification system for pending approvals
- Audit log viewer

### Future/Backlog
- SSO/LDAP integration
- API rate limiting
- File attachments for transactions
- Calendar view for leave
- Mobile app (React Native)
- Real-time notifications (WebSocket)
