# DAR AL CODE HR OS - Changelog

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
