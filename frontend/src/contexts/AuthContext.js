import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

const AuthContext = createContext(null);

// Generate device fingerprint for security
const generateDeviceSignature = () => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  ctx.textBaseline = 'top';
  ctx.font = '14px Arial';
  ctx.fillText('fingerprint', 2, 2);
  const canvasData = canvas.toDataURL();
  
  const data = [
    navigator.userAgent,
    navigator.language,
    screen.width + 'x' + screen.height,
    new Date().getTimezoneOffset(),
    canvasData.slice(-50)
  ].join('|');
  
  // Simple hash
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
