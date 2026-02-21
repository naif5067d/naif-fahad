# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Mobile-first, enterprise-grade HR operating system for Dar Al Code engineering consultancy. Strict RBAC, immutable transactions, Arabic-first UI.

## Core Rule
Any transaction not executed by STAS is not considered valid.

## Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Map:** react-leaflet + OpenStreetMap
- **Push Notifications:** Web Push API with VAPID (no Firebase)

## Design System
- **Colors:** 
  - Navy: #1E3A5F (primary)
  - Black: #0A0A0B (text)
  - Gray: #6B7280 (muted)
  - Lavender: #A78BFA (accent)
- **Fonts:** Manrope (English), IBM Plex Sans Arabic (Arabic)
- **Components:** Gradient hero cards, card-based layouts, bottom mobile nav
- **Timezone:** Asia/Riyadh (UTC+3) for all date/time display

## Roles
stas, mohammed (CEO), sultan, naif, salah, supervisor1, employee1/2

---

## Latest Implementation (2026-02-21)

### PWA & Push Notifications System
- **manifest.json**: App name "DAR ALCODE CO", Arabic description
- **Icons**: Professional company logo (192x192, 512x512)
- **Service Worker**: `/sw.js` for background push notifications
- **Push API**: `/api/push/*` endpoints with local VAPID keys
- **Privacy**: No data goes to Firebase/Google

### Header Responsive Fix
- Fixed icons disappearing on mobile viewports
- Added `flex-shrink-0` to prevent icon collapse
- All header controls (notifications, user switcher, language, theme, logout) now visible on all screen sizes

---

## Implemented Features

### Phase 1-37: All Previous Phases ✅
(See CHANGELOG.md for detailed history)

### Key Systems:
1. **Authentication**: JWT-based with Device Fingerprinting
2. **Attendance**: GPS validation, multi-location support
3. **Contracts V2**: Full lifecycle with sandbox mode
4. **Settlement**: End-of-service calculation
5. **Financial Custody**: Admin expense tracking (60 codes)
6. **Tasks**: 4-stage evaluation system
7. **Notifications**: Bell + Push (Web Push API)
8. **PWA**: Installable app with company branding

---

## Pending Issues

### P2: Transaction Deletion Logic
- Current implementation is unsafe
- Needs user clarification on:
  - Who can delete?
  - Which statuses are deletable?
  - Should we rollback executed transactions?

---

## Upcoming Tasks (P1)

1. **Merge Finance Pages**: MyFinances + Attendance/Penalties
2. **Annual Performance Review UI**
3. **Print Penalty Letterhead**
4. **Summon Employee Button (Executive Dashboard)**

## Future Tasks (P2)

1. Loans Module
2. CEO Dashboard Enhancements
3. Task Annual Summary Exposure

---

## Key API Endpoints

### Push Notifications
- `GET /api/push/vapid-key` - Get public VAPID key
- `POST /api/push/subscribe` - Subscribe to push
- `POST /api/push/unsubscribe` - Unsubscribe
- `GET /api/push/status` - Check subscription status
- `POST /api/push/send` - Send notification (admin)
- `POST /api/push/test` - Send test notification

### All Other APIs
(See previous PRD sections)

---

## Collections

### New Collection:
- `push_subscriptions` - User push notification subscriptions

### Protected Collections:
users, employees, contracts, contracts_v2, work_locations, settings, etc.

---

## Credentials for Testing
- STAS: `stas` / `123456`
- Sultan: `sultan` / `123456`
- All users: password `123456`

---

Version: 37.1 (2026-02-21)
