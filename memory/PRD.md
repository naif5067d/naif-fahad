# DAR AL CODE HR OS - Product Requirements Document

## Original Problem Statement
Mobile-first, enterprise-grade HR operating system for Dar Al Code engineering consultancy. Strict RBAC, immutable transactions, Arabic-first UI.

## Core Rule
Any transaction not executed by STAS is not considered valid.

## Architecture
- **Backend:** FastAPI + MongoDB + JWT RBAC
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Map:** react-leaflet + OpenStreetMap
- **Push Notifications:** Web Push API with VAPID (Privacy-focused, no Firebase)

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

## Latest Implementation (2025-02-21)

### PWA with Company Branding
- **manifest.json**: App name "DAR ALCODE CO" with Arabic description
- **Icons**: Official company logo on black background (192x192, 512x512, favicon)
- **iOS Support**: apple-mobile-web-app meta tags
- **When added to home screen**: Shows "DAR ALCODE CO" with company logo

### Push Notifications (Privacy Mode)
- **Web Push API** with VAPID keys (no Firebase)
- **100% Privacy**: All data stays on your server
- **Backend**: `/api/push/*` endpoints
- **Service Worker**: `/sw.js` for background notifications
- **Supported**: Desktop (all browsers) + Android + iPhone (PWA only)

### Header Responsive Fix
- Fixed icons disappearing on mobile viewports
- All header controls visible on all screen sizes

---

## Key API Endpoints

### Push Notifications
- `GET /api/push/vapid-key` - Get public VAPID key
- `POST /api/push/subscribe` - Subscribe to push
- `POST /api/push/unsubscribe` - Unsubscribe
- `GET /api/push/status` - Check subscription status
- `POST /api/push/send` - Send notification (admin)
- `POST /api/push/test` - Send test notification

---

## Collections

### New Collection:
- `push_subscriptions` - User push notification subscriptions

---

## iPhone Instructions
1. Open website in Safari
2. Tap Share button (⬆️)
3. Select "Add to Home Screen"
4. App appears with company logo
5. Enable notifications from inside the app

---

## Credentials for Testing
- STAS: `stas` / `123456`
- All users: password `123456`

---

Version: 37.2 (2025-02-21)
