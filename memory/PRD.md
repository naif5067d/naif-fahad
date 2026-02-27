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

### 2. Advanced Security Command Center (COMPLETED - 27/02/2026)
- ✅ **مركز قيادة الأمان المتقدم** - لوحة تحكم أمنية احترافية
- ✅ **إحصائيات الأمان الفورية**:
  - جلسات نشطة
  - تنبيهات اليوم
  - حسابات معطلة
  - أجهزة محظورة
  - دخول اليوم
  - أجهزة جديدة
- ✅ **تنبيهات الاحتيال التلقائية**:
  - كشف الجهاز المشترك بين موظفين
  - كشف الجلسات المتزامنة من أجهزة مختلفة
- ✅ **التحكم بالحسابات**:
  - تعطيل حسابات متعددة مع سبب ومدة
  - إلغاء تعطيل الحسابات
  - إنهاء جلسات إجباري (فردي/جماعي/طوارئ)
- ✅ **سجل الأمان المفصل**
- ✅ **صلاحيات STAS فقط**

### 3. Device Fingerprinting System (COMPLETED - 27/02/2026)
- ✅ بصمة جهاز متقدمة تكشف:
  - GPU (WebGL Renderer)
  - نظام التشغيل والإصدار
  - المتصفح والإصدار
  - دقة الشاشة
  - عدد أنوية المعالج
  - حجم الذاكرة
  - نقاط اللمس
  - بصمة Canvas و Audio
- ✅ كشف نوع الجهاز (iPhone, Samsung, Huawei, Mac, Windows, etc.)
- ✅ مقارنة البصمات لكشف التلاعب

### 4. Permissions & Controls
- ✅ إخفاء ميزات الخصم من المشرفين
- ✅ تعهد المسؤولية الإلزامي قبل تعديل الحضور
- ✅ سير عمل موافقة للمواقع الجديدة

### 5. Reports
- ✅ تقرير طباعة للساعات الرسمية والخارجية
- ✅ رأس الشركة + رمز QR

## What's Been Implemented

### 27/02/2026 - Advanced Security Command Center (P0)
**Frontend:**
- `/app/frontend/src/pages/DeviceMonitoringPage.js` - Completely redesigned with modern UI
  - Dark theme security dashboard
  - 6 stat cards with gradient colors
  - 5 tabs: Alerts, Sessions, Control, Suspended, Log
  - Multi-select employee suspension
  - Real-time session monitoring
  - Emergency logout all feature

**Backend APIs:**
- `GET /api/security/stats` - Security statistics
- `GET /api/security/fraud-alerts` - Fraud detection alerts
- `POST /api/security/suspend-accounts` - Suspend multiple accounts
- `POST /api/security/unblock-accounts` - Unblock accounts
- `POST /api/security/force-logout/{employee_id}` - Force logout single user
- `POST /api/security/force-logout-all` - Emergency logout all
- `GET /api/security/suspended-accounts` - List suspended accounts
- `GET /api/security/security-log` - Security audit log
- `GET /api/devices/all-sessions` - All active sessions

### Previous Sessions
- Advanced device fingerprinting
- Attendance system overhaul
- Print reports with QR codes
- Location approval workflow
- Data reset for fresh start

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- ✅ Advanced Security Command Center

### P1 (High)
- [ ] Full system health check after data reset
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
- Dark theme security dashboard

### Backend
- FastAPI with MongoDB
- JWT authentication with session management
- Device fingerprinting for security
- Rate limiting for login attempts

### Key Files
- `/app/frontend/src/pages/DeviceMonitoringPage.js` - Security Command Center
- `/app/frontend/src/utils/advancedFingerprint.js` - Device fingerprinting
- `/app/backend/routes/security.py` - Security APIs
- `/app/backend/routes/devices.py` - Device & session APIs
- `/app/backend/routes/auth.py` - Authentication with suspension check

## Database Schema Updates

### users collection
- `is_suspended` (Boolean) - Account suspension status
- `suspended_at` (DateTime) - Suspension timestamp
- `suspended_until` (DateTime) - Suspension expiry (null = permanent)
- `suspend_reason` (String) - Reason for suspension
- `suspended_by` (String) - Who suspended the account

### login_sessions collection
- `fingerprint_data` (Object) - Full device fingerprint
- `core_signature` (String) - Hardware hash for fraud detection
- `status` (String) - active, completed, force_logout

### security_log collection
- `action` (String) - account_suspended, account_unblocked, force_logout, etc.
- `employee_id`, `employee_name`
- `performed_by`, `performed_by_name`
- `reason`, `ip_address`, `created_at`

## Credentials
- Admin/Manager: `sultan` / `123456`
- CEO: `mohammed` / `123456`
- SysAdmin: `stas506` / `654321`
- Supervisor: `nayef` / `123456`
- Accountant: `salah` / `123456`

## Test Reports
- Latest: `/app/test_reports/iteration_47.json` - 100% pass rate (12/12 API tests, all UI tests)
