# DAR AL CODE HR OS - Security Changelog

## 2025-02-21 - Security Enhancements P0 + P1

### Session Security
- ✅ Role-based session duration (STAS: 12h, Managers: 8h, Supervisors: 6h, Employees: 4h)
- ✅ Server-side session tracking (`user_sessions` collection)
- ✅ Token revocation support (`revoked_tokens` collection)
- ✅ Device change detection and auto-logout for employees

### Rate Limiting
- ✅ 5 failed attempts = 15 minutes block
- ✅ IP-based tracking
- ✅ Clear Arabic error messages

### New Endpoints
- `POST /api/auth/logout` - Logout current session
- `POST /api/auth/logout-all` - Logout all devices
- `GET /api/auth/sessions` - List active sessions
- `DELETE /api/auth/sessions/{id}` - Revoke specific session

### Security Headers
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: DENY
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Referrer-Policy: strict-origin-when-cross-origin
- ✅ Permissions-Policy: geolocation=(self), camera=(), microphone=()

### Audit Logging
- ✅ Login success/failure logged
- ✅ Device change events logged
- ✅ Password change logged
- ✅ Logout events logged
- ✅ Session revocation logged

### Frontend
- ✅ "Logout all devices" button in header menu
- ✅ Session info displayed after login
