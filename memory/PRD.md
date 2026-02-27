# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
نظام موارد بشرية شامل لشركة دار الكود للاستشارات الهندسية يشمل:
- إدارة الحضور والانصراف
- إدارة الإجازات والعقود
- إدارة العهد المالية والعينية
- نظام مراقبة الأجهزة وكشف التلاعب

## User Personas
- **STAS (stas506)**: مسؤول النظام - صلاحيات كاملة
- **Sultan**: مدير العمليات - إدارة الموظفين والحضور
- **Naif**: العمليات الاستراتيجية
- **Mohammed (CEO)**: الرئيس التنفيذي
- **Salah**: المحاسب

## Core Requirements

### 1. Attendance System
- ✅ نظام حضور جديد مع فصل "ساعات العمل الرسمية" عن "الساعات الخارجية"
- ✅ فلتر متعدد الموظفين مع بحث
- ✅ موافقة جماعية للساعات الخارجية
- ✅ استعلام عجز الحضور

### 2. Device Monitoring System (NEW - 27/02/2026)
- ✅ بصمة جهاز متقدمة تكشف نوع الجهاز بالتفصيل
- ✅ صفحة موحدة `/device-monitoring` تجمع:
  - قائمة الموظفين مع بحث
  - سجل جلسات الدخول/الخروج
  - الأجهزة المسجلة
  - تنبيهات التلاعب التلقائية
- ✅ كشف التلاعب: جلسات متزامنة، تغيير الجهاز، أوقات غير اعتيادية

### 3. Permissions & Controls
- ✅ إخفاء ميزات الخصم من المشرفين
- ✅ تعهد المسؤولية الإلزامي قبل تعديل الحضور
- ✅ سير عمل موافقة للمواقع الجديدة

### 4. Reports
- ✅ تقرير طباعة للساعات الرسمية والخارجية
- ✅ رأس الشركة + رمز QR

## What's Been Implemented

### 27/02/2026 - Device Monitoring System
- Created `/app/frontend/src/utils/advancedFingerprint.js` - Advanced device fingerprinting
- Created `/app/backend/services/advanced_device_analysis.py` - Device analysis service
- Created `/app/frontend/src/pages/DeviceMonitoringPage.js` - Unified monitoring page
- Added APIs: `/api/devices/fraud-analysis/{employee_id}`, `/api/devices/fingerprint-details/{session_id}`
- Removed old `LoginSessionsPage.js` to avoid duplication

### Previous Sessions
- Attendance system overhaul
- Print reports with QR codes
- Location approval workflow
- Data reset for fresh start

## Prioritized Backlog

### P0 (Critical)
- [ ] Full system health check after data reset

### P1 (High)
- [ ] Verify compensation business rules (7-hour limit)
- [ ] In-Kind custody workflow for unreturned items

### P2 (Medium)
- [ ] Verify MaintenanceTrackingPage stability
- [ ] Refactor monolithic pages (ContractsManagementPage, STASMirrorPage)
- [ ] Complete System Architecture view in Stas Mirror

### P3 (Low)
- [ ] Mobile responsiveness improvements
- [ ] Canva-like Smart Editor for Policies
- [ ] Centralized RBAC system

## Technical Architecture

### Frontend
- React with Shadcn/UI components
- RTL support for Arabic
- Role-based navigation

### Backend
- FastAPI with MongoDB
- JWT authentication
- Device fingerprinting for security

### Key Files
- `/app/frontend/src/pages/DeviceMonitoringPage.js` - Device monitoring
- `/app/frontend/src/pages/NewTeamAttendancePage.js` - Attendance management
- `/app/backend/routes/team_attendance.py` - Attendance APIs
- `/app/backend/services/advanced_device_analysis.py` - Device analysis

## Credentials
- Admin/Manager: `sultan` / `123456`
- CEO: `mohammed` / `123456`
- SysAdmin: `stas506` / `654321`
- Supervisor: `nayef` / `123456`
- Accountant: `salah` / `123456`
