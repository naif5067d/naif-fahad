# HR-OS System - Product Requirements Document

## Original Problem Statement
نظام إدارة الموارد البشرية متكامل لشركة دار الكود للاستشارات الهندسية يشمل:
- إدارة الحضور والانصراف
- إدارة الإجازات
- إدارة العقود
- إدارة العهد المالية والعينية
- لوحة تحكم تنفيذية
- نظام الإشعارات

## User Personas
1. **STAS (System Admin):** صلاحيات كاملة على النظام
2. **Sultan (مدير العمليات):** إدارة الموظفين والعمليات اليومية
3. **Mohammed (CEO):** عرض اللوحات التنفيذية والتقارير
4. **Nayef (مشرف):** إدارة فريقه

## Core Architecture
```
/app/
├── backend/           # FastAPI
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic
│   └── database.py    # MongoDB connection
└── frontend/          # React + Tailwind + Shadcn
    ├── src/pages/     # Page components
    ├── src/components/# Reusable components
    └── src/contexts/  # React contexts
```

## Key Features Implemented

### 1. Authentication & Authorization
- JWT-based auth with role-based access
- Session management with device fingerprinting

### 2. Attendance Management
- Daily punch-in/out tracking
- Deficit calculation
- Monthly reports with PDF export

### 3. Leave Management
- Leave requests and approvals
- Balance tracking via leave_ledger

### 4. PDF Preview System
- In-page modal using PdfPreviewModal.jsx
- Avoids ad-blocker conflicts

### 5. Executive Dashboard
- Yearly aggregated data (Jan 1 to current date)

### 6. Nuclear Reset (NEW - March 1, 2026)
- Full data wipe for test data
- Preserves: employees, users, contracts, work_locations, settings
- Requires typing "تصفير نووي" for confirmation
- Available only to STAS and Sultan roles

## API Endpoints

### Admin Routes
- `POST /api/admin/nuclear-reset` - Nuclear data reset
- `POST /api/admin/reset-balances` - Reset leave balances
- `POST /api/admin/system-reset-from-date` - Reset from specific date

### Authentication
- `POST /api/auth/login`
- `POST /api/auth/logout`

### Attendance
- `GET /api/attendance/daily-status`
- `POST /api/attendance/punch`

## Database Schema
- **employees:** Employee master data
- **users:** Authentication data
- **contracts_v2:** Contract information
- **daily_status:** Daily attendance records
- **leave_ledger:** Leave balance transactions
- **transactions:** All request transactions

## Test Credentials
- Admin/Manager: `sultan` / `123456`
- CEO: `mohammed` / `12346`
- SysAdmin: `stas506` / `654321`
- Supervisor: `nayef` / `123456`

## Pending Issues (P1-P2)
1. Mobile login page UI broken
2. Summon/Reply workflow incomplete
3. Script error in Financial Custody page
4. Auto-delete leave_ledger on cancelled leave

## Future Tasks
- In-Kind Custody damage assessment
- Smart Editor for Policies (Canva-like)
- System Architecture View UI
- Centralized RBAC refactor

## System Monitoring Features (March 1, 2026)
- Live system metrics via `/api/maintenance/system-metrics`
- Real data from Kubernetes cgroup v2 (RAM, CPU, Storage)
- Fallback to psutil for non-containerized environments
- Auto-refresh every 30 seconds
- Detailed resource limits table
- File storage breakdown analysis

## Last Updated
March 1, 2026 - Added Nuclear Reset feature + Verified System Monitoring
