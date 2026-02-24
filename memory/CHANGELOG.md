# DAR AL CODE HR OS - Changelog

## [2026-02-24] شريط التقدم ورصيد الخروج المبكر + نظام التعويضات

### المميزات الجديدة
1. **شريط تقدم ساعات الشهر**: 
   - يظهر للموظف ساعاته المنجزة من المطلوبة (144 رمضان / 194 عادي)
   - يعرض عجز الساعات إن وجد
   - يظهر في لوحة التحكم الرئيسية ونافذة تفاصيل الحضور

2. **رصيد الخروج المبكر (3 ساعات شهرياً)**:
   - شريط تقدم منفصل يوضح الرصيد المتبقي
   - يُخصم تلقائياً عند طلب خروج مبكر
   - قابل للتعديل من الإدارة (0-5 ساعات)

3. **حالة "الإعفاء" الجديدة**:
   - قرار إداري بعدم المحاسبة على الغياب/التأخير
   - مختلفة عن "حاضر" - ليست تزويراً للحضور
   - متاحة فقط لسلطان وستاس

4. **نظام التعويضات**:
   - API لجلب الموظفين الذين لديهم عجز (تأخيرات/غيابات)
   - API للتعويض: تحويل غياب إلى حضور مع توثيق
   - API للإعفاء: قرار إداري بعدم المحاسبة
   - تبويب "التعويضات" في صفحة الحضور والعقوبات

5. **إصلاح عرض حضور المدير**:
   - سلطان الآن يرى حالة حضوره كما يراها الموظفون

6. **إصلاح خطأ 447 دقيقة تأخير**:
   - عند تعديل الحالة إلى حاضر/إعفاء/إجازة، يتم تصفير دقائق التأخير تلقائياً

7. **إخفاء رسالة التعديل الإداري**:
   - الموظف لا يرى تفاصيل التعديل الإداري (فقط الحالة)

### Backend APIs الجديدة
- `GET /api/team-attendance/compensation-requests` - قائمة الموظفين للتعويض
- `POST /api/team-attendance/compensate/{emp_id}/{date}` - تعويض أو إعفاء
- `POST /api/team-attendance/early-leave-request` - طلب خروج مبكر
- `POST /api/team-attendance/early-leave-execute/{tx_id}` - تنفيذ مع خيار الخصم
- `GET /api/settings/early-leave-balance` - إعدادات رصيد الخروج المبكر
- `PUT /api/settings/early-leave-balance` - تحديث الرصيد

### ملفات معدّلة
- `backend/routes/employees.py`: إضافة `early_leave_balance` للـ summary
- `backend/routes/team_attendance.py`: نظام التعويضات + تصفير دقائق التأخير
- `backend/routes/settings.py`: إعدادات رصيد الخروج المبكر
- `frontend/src/pages/DashboardPage.js`: شريطا التقدم + إخفاء رسالة التعديل
- `frontend/src/pages/TeamAttendancePage.js`: تبويب التعويضات + خيار الإعفاء

### التحقق
- ✅ سلطان يرى حالة حضوره في Dashboard
- ✅ شريط ساعات الشهر يعمل (0/144 رمضان)
- ✅ شريط رصيد الخروج المبكر يعمل (3/3 ساعات)
- ✅ حالة الإعفاء تُحفظ وتُعرض بشكل صحيح
- ✅ نظام التعويض يعمل (تحويل غياب إلى حضور)
- ✅ دقائق التأخير تُصفّر عند تغيير الحالة

---

## [2026-02-23] PWA Icon Management Feature + Bug Fixes

### Added (New Feature)
1. **PWA Icon Management**: STAS user can now upload custom app icons via "الهوية" (Branding) tab
   - Upload custom icon (512x512 recommended)
   - Icons automatically resize to 192x192, 512x512, 180x180 (Apple)
   - Falls back to company logo if no custom icon uploaded
   - Changes reflect immediately - no need to reinstall PWA

### Backend Changes
- `POST /api/company-settings/upload-pwa-icon` - Upload custom PWA icon
- `DELETE /api/company-settings/pwa-icon` - Delete custom icon (revert to logo)
- `GET /api/company-settings/pwa-icon/{size}` - Get resized icon (32, 180, 192, 512)
- `GET /api/company-settings/manifest.json` - Dynamic manifest with custom icons

### Frontend Changes
- Added PWA icon section in STAS Mirror Branding tab with upload/delete UI
- index.html now uses dynamic icons from API (auto-updates)

### Fixed
1. **MaintenanceTrackingPage.js Crash**: Removed invalid `s.icon` reference

### Verified Working
- All PWA icon APIs return correct images
- Dynamic manifest.json with RTL support
- Branding tab shows PWA icon section with "جديد" badge

### Test Report
- `/app/test_reports/iteration_41.json`: All tests passed (100% success rate)

---

## [2026-02-19] Phase 33: Bug Fixes & Deployment Readiness

### Fixed
1. **Deployment Health Check**: Added `/health` endpoint without `/api` prefix for Kubernetes liveness/readiness probes
2. **GPS Validation**: Frontend now strictly validates GPS availability before allowing check-in/check-out
3. **Checkout Confirmation**: Added confirmation dialog "هل أنت متأكد من تسجيل الخروج؟" before check-out
4. **Leave Balance for Migrated Contracts**: Fixed calculation to use `leave_opening_balance` instead of Pro-Rata for migrated employees
5. **Work Location Updates**: Added `allow_early_checkin_minutes` to update endpoint
6. **Holiday Management UI**: Changed from individual days to date ranges (from-to) with automatic day grouping

### Files Modified
- `backend/server.py`: Added `/health` endpoint
- `backend/services/hr_policy.py`: Fixed migrated contract leave balance calculation
- `backend/routes/work_locations.py`: Added `allow_early_checkin_minutes` to update
- `frontend/src/pages/AttendancePage.js`: GPS validation & checkout confirmation
- `frontend/src/pages/LeavePage.js`: Holiday date range support & grouped display

---

## [2026-02-17] Phase 16.1: Settlement PDF Enhancements

### Fixed
- **Company Logo in PDF**: Now fetches logo from `branding['logo_data']` (base64) and properly converts RGBA to RGB for PDF compatibility
- **Declaration Text**: Added full bilingual declaration/acknowledgment section with header "الإقرار والتعهد / Declaration / Acknowledgment"

### Files Modified
- `backend/utils/settlement_pdf.py`: Updated `create_company_logo()` function to handle base64 logo from branding settings

### Tests Added
- `/app/backend/tests/test_settlement_pdf.py`: 10 comprehensive tests for PDF generation

---

## [2026-02-17] Phase 16: Settlement System Complete

### Added
- Settlement module with full lifecycle (create → preview → execute)
- Bank Name & IBAN fields in contracts
- EOS calculation per Saudi Labor Law
- Leave compensation calculation (pro-rata)
- Settlement PDF generation with QR codes and barcode

### New Files
- `backend/routes/settlement.py`
- `backend/services/settlement_service.py`
- `backend/services/service_calculator.py`
- `backend/utils/settlement_pdf.py`
- `frontend/src/pages/SettlementPage.js`

---

## [2026-02-14] Phase 15: PDF Arabic Text Fix

### Fixed
- Arabic text rendering in PDFs using dual-font approach
- Date formatting with dashes (2026-02-17 not 20260217)
- Reference numbers display

---

## [2026-02-14] Phase 14: System Maintenance Module

### Added
- Full archive/restore functionality
- Storage statistics
- Transaction purge capability
- Maintenance logs

---

## [2026-02-14] Phase 13: Contracts V2 System

### Added
- Complete contract lifecycle management
- Serial number generation (DAC-YYYY-XXX)
- Contract status workflow
- PDF contract generation
