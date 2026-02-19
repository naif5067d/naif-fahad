import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

const AuthContext = createContext(null);

// Generate device fingerprint for security
// تجميع بصمة الجهاز الكاملة مع فصل Hardware عن Browser
const generateDeviceFingerprint = () => {
  // Canvas Fingerprint
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  ctx.textBaseline = 'top';
  ctx.font = '14px Arial';
  ctx.fillText('HR System Fingerprint', 2, 2);
  ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
  ctx.fillRect(50, 0, 20, 20);
  const canvasFingerprint = canvas.toDataURL();
  
  // WebGL Info (مهم جداً - لا يتغير بتغيير المتصفح)
  let webglVendor = '';
  let webglRenderer = '';
  try {
    const gl = document.createElement('canvas').getContext('webgl');
    if (gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        webglVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        webglRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
      }
    }
  } catch (e) {}
  
  return {
    // 🔐 Core Hardware (لا يتغير بتغيير المتصفح)
    webglVendor: webglVendor,
    webglRenderer: webglRenderer,
    canvasFingerprint: canvasFingerprint.slice(-100),
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    deviceMemory: navigator.deviceMemory || 0,
    platform: navigator.platform,
    screenResolution: `${screen.width}x${screen.height}`,
    
    // 📱 Soft Browser Data (للتسجيل فقط)
    userAgent: navigator.userAgent,
    language: navigator.language,
    timezone: new Date().getTimezoneOffset().toString(),
    touchSupport: 'ontouchstart' in window,
    cookiesEnabled: navigator.cookieEnabled,
    localStorageEnabled: typeof localStorage !== 'undefined'
  };
};

const generateDeviceSignature = () => {
  const fp = generateDeviceFingerprint();
  // Simple hash for backward compatibility
  const data = [fp.userAgent, fp.language, fp.screenResolution, fp.timezone, fp.canvasFingerprint].join('|');
  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    hash = ((hash << 5) - hash) + data.charCodeAt(i);
    hash |= 0;
  }
  return 'DEV_' + Math.abs(hash).toString(36);
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('hr_token'));
  const [loading, setLoading] = useState(true);
  const [allUsers, setAllUsers] = useState([]);

  // Fetch all users for switcher (STAS only)
  const fetchAllUsers = useCallback(async () => {
    try {
      const res = await api.get('/api/auth/users');
      setAllUsers(res.data);
      return res.data;
    } catch {
      return [];
    }
  }, []);

  // Switch to a specific user by ID (STAS only feature)
  const switchUser = useCallback(async (userId) => {
    try {
      const res = await api.post(`/api/auth/switch/${userId}`);
      const { token: newToken, user: userData } = res.data;
      localStorage.setItem('hr_token', newToken);
      api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      setToken(newToken);
      setUser(userData);
      return userData;
    } catch (err) {
      console.error('Switch user failed:', err);
      return null;
    }
  }, []);

  // Real login function with device fingerprint
  const login = useCallback(async (username, password) => {
    const deviceSignature = generateDeviceSignature();
    const fingerprintData = {
      userAgent: navigator.userAgent,
      language: navigator.language,
      screen: `${screen.width}x${screen.height}`,
      timezone: new Date().getTimezoneOffset(),
      platform: navigator.platform
    };

    const res = await api.post('/api/auth/login', {
      username,
      password,
      device_signature: deviceSignature,
      fingerprint_data: fingerprintData
    });

    const { token: newToken, user: userData } = res.data;
    localStorage.setItem('hr_token', newToken);
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    setToken(newToken);
    setUser(userData);
    
    // Fetch all users only if STAS
    if (userData.role === 'stas') {
      await fetchAllUsers();
    }
    
    return userData;
  }, [fetchAllUsers]);

  useEffect(() => {
    const init = async () => {
      if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        try {
          const res = await api.get('/api/auth/me');
          setUser(res.data);
          // Fetch all users only if STAS (for user switcher)
          if (res.data.role === 'stas') {
            await fetchAllUsers();
          }
        } catch {
          localStorage.removeItem('hr_token');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };
    init();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const logout = () => {
    localStorage.removeItem('hr_token');
    delete api.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
    setAllUsers([]);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, allUsers, switchUser, fetchAllUsers, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
