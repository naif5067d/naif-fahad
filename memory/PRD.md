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
- ✅ **إحصائيات الأمان الفورية**
- ✅ **تنبيهات الاحتيال التلقائية**
- ✅ **التحكم بالحسابات** (تعطيل/إلغاء/إنهاء جلسات)
- ✅ **سجل الأمان المفصل**

### 3. Device Fingerprinting System (COMPLETED - 27/02/2026)
- ✅ بصمة جهاز متقدمة (GPU, OS, Screen, Browser)
- ✅ كشف نوع الجهاز
- ✅ مقارنة البصمات لكشف التلاعب

### 4. Mobile Responsiveness (COMPLETED - 28/02/2026)
- ✅ **Safe Area لـ iPhone** - دعم كامل للـ notch و Dynamic Island
- ✅ **Header مضغوط** على الجوال مع جميع الأزرار ظاهرة
- ✅ **Bottom Navigation** محسّن للجوال
- ✅ **Stats Cards متجاوبة** - 2 أعمدة على الجوال
- ✅ **تمرير أفقي للتبويبات** على الشاشات الضيقة
- ✅ **تمرير أفقي للجداول** على الجوال
- ✅ **Touch Targets** - أزرار بحجم 40x40px minimum
- ✅ **Responsive Breakpoints** - iPad: sidebar, Mobile: bottom nav

## What's Been Implemented

### 28/02/2026 - Mobile Responsiveness (P0)
**CSS Improvements (`index.css`):**
- Safe Area support for iPhone notch/Dynamic Island
- Comprehensive mobile media queries
- Touch-friendly button sizes (44px minimum)
- Horizontal scroll for tables and tabs
- Typography and spacing adjustments
- iOS zoom prevention (font-size: 16px on inputs)

**Layout (`AppLayout.js`):**
- Compact header with gap adjustments
- Smaller buttons on mobile
- Hidden user name on mobile switcher
- Responsive bottom navigation

**Security Center (`DeviceMonitoringPage.js`):**
- Mobile-optimized stat cards
- Responsive tabs with horizontal scroll
- Compact alert cards

### 27/02/2026 - Security Command Center (P0)
- Advanced security dashboard
- Fraud detection alerts
- Account suspension system
- Device fingerprinting

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- ✅ Advanced Security Command Center
- ✅ Mobile Responsiveness

### P1 (High)
- [ ] Full system health check
- [ ] Verify compensation business rules (7-hour limit)
- [ ] In-Kind custody workflow

### P2 (Medium)
- [ ] Verify MaintenanceTrackingPage stability
- [ ] Refactor monolithic pages
- [ ] Complete System Architecture view

### P3 (Low)
- [ ] Canva-like Smart Editor for Policies
- [ ] Centralized RBAC system

## Technical Architecture

### Mobile CSS Classes
- `.safe-header` - iPhone Safe Area support
- `.mobile-nav` - Bottom navigation with safe-area-inset-bottom
- `.mobile-keep-cols` - Preserve 2-column grid on mobile
- `.touch-target` - 44px minimum touch target
- `.mobile-stack` - Stack items vertically on mobile

### Key Files
- `/app/frontend/src/index.css` - Mobile CSS improvements
- `/app/frontend/src/components/layout/AppLayout.js` - Responsive layout
- `/app/frontend/src/pages/DeviceMonitoringPage.js` - Responsive security dashboard

## Test Reports
- Latest: `/app/test_reports/iteration_48.json` - 100% pass rate (Mobile Responsiveness)
- Previous: `/app/test_reports/iteration_47.json` - 100% pass rate (Security APIs)

## Credentials
- Admin/Manager: `sultan` / `123456`
- CEO: `mohammed` / `123456`
- SysAdmin: `stas506` / `654321`
- Supervisor: `nayef` / `123456`
- Accountant: `salah` / `123456`
