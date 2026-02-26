import { useEffect, useState, useRef } from 'react';
import { RefreshCw, Rocket, CheckCircle } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import api from '@/lib/api';

// Check interval: 10 seconds
const CHECK_INTERVAL = 10 * 1000;

export default function VersionChecker() {
  const { lang } = useLanguage();
  const isRTL = lang === 'ar';
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [updateInfo, setUpdateInfo] = useState(null);
  const [justUpdated, setJustUpdated] = useState(false);
  const currentBuildRef = useRef(null);
  const lastRefreshTokenRef = useRef(null);

  useEffect(() => {
    // Check if we just updated
    const storedRefreshToken = localStorage.getItem('app_refresh_token');
    const storedVersion = localStorage.getItem('app_last_version');
    
    // Get initial build number
    const initCheck = async () => {
      try {
        const res = await api.get('/api/admin/app-version');
        currentBuildRef.current = res.data.build || 1;
        lastRefreshTokenRef.current = res.data.refresh_token;
        
        // If refresh token changed and we have a stored one, show "just updated" message
        if (storedRefreshToken && storedRefreshToken !== res.data.refresh_token) {
          setJustUpdated(true);
          setUpdateInfo({ server_version: res.data.version });
          // Update stored values
          localStorage.setItem('app_refresh_token', res.data.refresh_token);
          localStorage.setItem('app_last_version', res.data.version);
          // Hide message after 5 seconds
          setTimeout(() => setJustUpdated(false), 5000);
        } else if (!storedRefreshToken) {
          // First time - just store current values
          localStorage.setItem('app_refresh_token', res.data.refresh_token || '');
          localStorage.setItem('app_last_version', res.data.version || '');
        }
      } catch {
        currentBuildRef.current = 1;
      }
    };
    initCheck();

    // Periodic check for updates
    const interval = setInterval(async () => {
      if (currentBuildRef.current === null) return;
      
      try {
        const res = await api.get(`/api/admin/app-version/check?current_build=${currentBuildRef.current}`);
        
        // Check both build number and refresh token
        if (res.data.needs_update || (res.data.refresh_token && res.data.refresh_token !== lastRefreshTokenRef.current)) {
          setUpdateAvailable(true);
          setUpdateInfo(res.data);
        }
      } catch {
        // Silently fail
      }
    }, CHECK_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    // Store current info before refresh
    if (updateInfo?.refresh_token) {
      localStorage.setItem('app_refresh_token', updateInfo.refresh_token);
      localStorage.setItem('app_last_version', updateInfo.server_version || '');
    }
    // Force hard reload - clear cache
    window.location.reload(true);
  };

  // Show "just updated" message
  if (justUpdated) {
    return (
      <div className="fixed bottom-4 start-4 end-4 md:start-auto md:end-4 md:w-96 z-[100] animate-slide-up">
        <div className="bg-green-600 text-white rounded-xl shadow-2xl p-4" dir={isRTL ? 'rtl' : 'ltr'}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0">
              <CheckCircle size={22} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-sm">
                {isRTL ? 'تم التحديث بنجاح!' : 'Updated Successfully!'}
              </p>
              <p className="text-xs opacity-90 mt-0.5">
                {isRTL ? 'الإصدار الحالي:' : 'Current Version:'} v{updateInfo?.server_version}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!updateAvailable) return null;

  return (
    <div className="fixed bottom-4 start-4 end-4 md:start-auto md:end-4 md:w-96 z-[100] animate-slide-up">
      <div className="bg-primary text-primary-foreground rounded-xl shadow-2xl p-4" dir={isRTL ? 'rtl' : 'ltr'}>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0 animate-pulse">
            <Rocket size={22} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-sm">
              {isRTL ? 'تحديث جديد متوفر!' : 'New Update Available!'}
            </p>
            <p className="text-xs opacity-90 mt-0.5">
              {isRTL ? 'الإصدار' : 'Version'} {updateInfo?.server_version}
            </p>
            {updateInfo?.release_notes && (
              <p className="text-xs opacity-80 mt-1 line-clamp-2">
                {updateInfo.release_notes}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={handleRefresh}
          className="w-full mt-3 px-4 py-2.5 bg-white text-primary font-semibold rounded-lg hover:bg-white/90 transition-colors flex items-center justify-center gap-2"
          data-testid="refresh-now-btn"
        >
          <RefreshCw size={16} />
          {isRTL ? 'تحديث الآن' : 'Update Now'}
        </button>
      </div>
    </div>
  );
}
