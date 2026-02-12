import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('hr_token'));
  const [loading, setLoading] = useState(true);
  const [allUsers, setAllUsers] = useState([]);

  // Fetch all users for switcher
  const fetchAllUsers = useCallback(async () => {
    try {
      const res = await api.get('/api/auth/users');
      setAllUsers(res.data);
      return res.data;
    } catch {
      return [];
    }
  }, []);

  // Switch to a specific user by ID
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

  useEffect(() => {
    const init = async () => {
      // Always fetch user list
      const users = await fetchAllUsers();

      if (token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        try {
          const res = await api.get('/api/auth/me');
          setUser(res.data);
          setLoading(false);
          return;
        } catch {
          localStorage.removeItem('hr_token');
          setToken(null);
        }
      }

      // Auto-login as first available user if no valid token
      if (users.length > 0) {
        const firstActive = users.find(u => u.is_active !== false);
        if (firstActive) {
          await switchUser(firstActive.id);
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
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, allUsers, switchUser, fetchAllUsers, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
