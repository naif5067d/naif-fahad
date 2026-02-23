import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { 
  Bell, Check, CheckCheck, FileText, XCircle, CheckCircle, 
  Clock, DollarSign, AlertTriangle, Calendar, FileWarning,
  Shield, RotateCcw, UserX, LogOut, Settings, Megaphone, X,
  BellRing, BellOff, Loader2
} from 'lucide-react';
import api from '@/lib/api';
import pushService from '@/services/pushNotifications';

// مطابقة الأيقونات
const ICON_MAP = {
  'FileText': FileText,
  'CheckCircle': CheckCircle,
  'XCircle': XCircle,
  'Shield': Shield,
  'Clock': Clock,
  'RotateCcw': RotateCcw,
  'AlertTriangle': AlertTriangle,
  'UserX': UserX,
  'LogOut': LogOut,
  'DollarSign': DollarSign,
  'FileWarning': FileWarning,
  'CalendarCheck': Calendar,
  'CalendarX': Calendar,
  'CalendarClock': Calendar,
  'Megaphone': Megaphone,
  'Bell': Bell,
  'Settings': Settings,
};

// صوت الإشعار - يحتاج تفاعل المستخدم أولاً في المتصفحات الحديثة
let audioContext = null;

const getAudioContext = () => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  // Resume if suspended (Chrome autoplay policy)
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }
  return audioContext;
};

const playNotificationSound = () => {
  try {
    const ctx = getAudioContext();
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    
    // نغمة إشعار مميزة
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(880, ctx.currentTime); // A5
    oscillator.frequency.setValueAtTime(1100, ctx.currentTime + 0.1); // C#6
    oscillator.frequency.setValueAtTime(880, ctx.currentTime + 0.2); // A5
    
    gainNode.gain.setValueAtTime(0.4, ctx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    
    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + 0.4);
  } catch (e) {
    console.log('Audio not supported:', e);
  }
};

// تنسيق الوقت النسبي
const formatRelativeTime = (dateStr, lang) => {
  if (!dateStr) return '';
  
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return lang === 'ar' ? 'الآن' : 'Just now';
  if (diffMins < 60) return lang === 'ar' ? `منذ ${diffMins} دقيقة` : `${diffMins}m ago`;
  if (diffHours < 24) return lang === 'ar' ? `منذ ${diffHours} ساعة` : `${diffHours}h ago`;
  if (diffDays < 7) return lang === 'ar' ? `منذ ${diffDays} يوم` : `${diffDays}d ago`;
  
  return date.toLocaleDateString(lang === 'ar' ? 'ar-EG' : 'en-US', { month: 'short', day: 'numeric' });
};

export default function NotificationBell() {
  const navigate = useNavigate();
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [hasCritical, setHasCritical] = useState(false);
  const [loading, setLoading] = useState(false);
  const [lastCount, setLastCount] = useState(0);
  const [initialized, setInitialized] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const bellRef = useRef(null);
  
  // Check push notification status
  useEffect(() => {
    const checkPushStatus = async () => {
      if ('serviceWorker' in navigator && 'PushManager' in window) {
        try {
          const registration = await navigator.serviceWorker.getRegistration('/sw.js');
          if (registration) {
            const subscription = await registration.pushManager.getSubscription();
            setPushEnabled(!!subscription);
          }
        } catch (e) {
          console.log('[Push] Status check failed:', e);
        }
      }
    };
    checkPushStatus();
  }, [user?.id]);
  
  // Enable push notifications
  const enablePushNotifications = async () => {
    setPushLoading(true);
    try {
      const result = await pushService.initialize(user?.id);
      if (result.success) {
        setPushEnabled(true);
        // Show success notification
        if (Notification.permission === 'granted') {
          new Notification('دار الكود للاستشارات الهندسية', {
            body: lang === 'ar' ? 'تم تفعيل الإشعارات بنجاح' : 'Notifications enabled successfully',
            icon: '/icon-192.png',
            dir: 'rtl'
          });
        }
      } else {
        console.log('[Push] Failed:', result.reason);
        if (result.reason === 'permission_denied') {
          alert(lang === 'ar' ? 'يرجى السماح بالإشعارات من إعدادات المتصفح' : 'Please allow notifications in browser settings');
        } else {
          alert(lang === 'ar' ? 'فشل تفعيل الإشعارات: ' + result.reason : 'Failed to enable notifications: ' + result.reason);
        }
      }
    } catch (e) {
      console.error('[Push] Error:', e);
      alert(lang === 'ar' ? 'حدث خطأ: ' + e.message : 'Error: ' + e.message);
    }
    setPushLoading(false);
  };
  
  // جلب الإشعارات
  const fetchNotifications = useCallback(async () => {
    try {
      const response = await api.get('/api/notifications/bell');
      const data = response.data;
      
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
      setHasCritical(data.has_critical || false);
      
      // تشغيل الصوت عند وصول إشعار جديد (بعد التحميل الأول)
      if (initialized && data.unread_count > lastCount) {
        playNotificationSound();
      }
      setLastCount(data.unread_count || 0);
      setInitialized(true);
    } catch (err) {
      console.log('Failed to fetch notifications');
    }
  }, [lastCount, initialized]);
  
  // جلب الإشعارات عند التحميل وكل 30 ثانية وعند تبديل المستخدم
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications, user?.id]);
  
  // إغلاق القائمة عند النقر خارجها
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (bellRef.current && !bellRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // تحديد إشعار كمقروء
  const handleMarkRead = async (notificationId, e) => {
    e?.stopPropagation();
    if (notificationId.startsWith('pending-') || notificationId.startsWith('contract-')) {
      // إشعارات حية - لا نحتاج تحديثها
      return;
    }
    
    try {
      await api.patch(`/api/notifications/${notificationId}/read`);
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {}
  };
  
  // تحديد الكل كمقروء
  const handleMarkAllRead = async () => {
    setLoading(true);
    try {
      await api.post('/api/notifications/mark-all-read');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {}
    setLoading(false);
  };
  
  // حذف جميع الإشعارات
  const handleDeleteAll = async () => {
    setLoading(true);
    try {
      await api.delete('/api/notifications/all');
      setNotifications([]);
      setUnreadCount(0);
      setIsOpen(false);
    } catch (err) {}
    setLoading(false);
  };
  
  // الانتقال للرابط
  const handleNotificationClick = (notification) => {
    if (!notification.is_read) {
      handleMarkRead(notification.id);
    }
    if (notification.reference_url) {
      navigate(notification.reference_url);
      setIsOpen(false);
    }
  };
  
  // الحصول على الأيقونة
  const getIcon = (iconName) => {
    const IconComponent = ICON_MAP[iconName] || Bell;
    return IconComponent;
  };
  
  return (
    <div className="relative flex-shrink-0" ref={bellRef}>
      {/* زر الجرس */}
      <button
        data-testid="notification-bell-btn"
        onClick={() => setIsOpen(!isOpen)}
        className={`relative p-2 sm:p-2.5 rounded-xl transition-all ${
          isOpen ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-muted-foreground'
        }`}
        title={lang === 'ar' ? 'الإشعارات' : 'Notifications'}
      >
        <Bell size={18} className={hasCritical ? 'animate-bounce' : ''} />
        
        {/* شارة العدد */}
        {unreadCount > 0 && (
          <span 
            className={`absolute -top-0.5 -end-0.5 min-w-[18px] h-[18px] flex items-center justify-center text-[9px] font-bold text-white rounded-full transition-all ${
              hasCritical ? 'bg-destructive/100 animate-pulse' : 'bg-primary'
            }`}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      
      {/* القائمة المنسدلة */}
      {isOpen && (
        <div 
          className="absolute top-full mt-2 w-[320px] sm:w-96 max-w-[calc(100vw-2rem)] bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-fade-in z-50"
          style={{ 
            right: lang === 'ar' ? '0' : 'auto', 
            left: lang === 'ar' ? 'auto' : '0',
            transform: 'translateX(0)'
          }}
          data-testid="notification-dropdown"
        >
          {/* Header */}
          <div className="px-3 sm:px-4 py-2.5 sm:py-3 border-b border-border bg-gradient-to-r from-primary/5 to-transparent flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Bell size={16} className="text-primary flex-shrink-0" />
              <h3 className="font-semibold text-sm">
                {lang === 'ar' ? 'الإشعارات' : 'Notifications'}
              </h3>
              {unreadCount > 0 && (
                <span className="px-1.5 sm:px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                  {unreadCount}
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              {/* زر اختبار الصوت */}
              <button
                onClick={() => {
                  playNotificationSound();
                }}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground p-1"
                title={lang === 'ar' ? 'اختبار الصوت' : 'Test sound'}
                data-testid="test-sound-btn"
              >
                <Bell size={14} />
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  disabled={loading}
                  className="flex items-center gap-1 text-xs text-primary hover:underline disabled:opacity-50"
                  data-testid="mark-all-read-btn"
                >
                  <CheckCheck size={14} />
                  <span className="hidden sm:inline">{lang === 'ar' ? 'رؤية الكل' : 'Read all'}</span>
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={handleDeleteAll}
                  disabled={loading}
                  className="flex items-center gap-1 text-xs text-destructive hover:underline disabled:opacity-50"
                  data-testid="delete-all-btn"
                >
                  <X size={14} />
                  <span className="hidden sm:inline">{lang === 'ar' ? 'حذف الكل' : 'Delete all'}</span>
                </button>
              )}
            </div>
          </div>
          
          {/* زر تفعيل الإشعارات الفورية */}
          {'serviceWorker' in navigator && 'PushManager' in window && (
            <div className="px-3 py-2 border-b border-border bg-muted/20">
              <button
                onClick={enablePushNotifications}
                disabled={pushLoading || pushEnabled}
                className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  pushEnabled 
                    ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))] dark:bg-green-900/30 dark:text-[hsl(var(--success))] cursor-default' 
                    : 'bg-primary/10 text-primary hover:bg-primary/20'
                }`}
                data-testid="enable-push-btn"
              >
                {pushLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : pushEnabled ? (
                  <>
                    <BellRing size={16} />
                    <span>{lang === 'ar' ? 'الإشعارات الفورية مفعّلة' : 'Push notifications enabled'}</span>
                  </>
                ) : (
                  <>
                    <BellOff size={16} />
                    <span>{lang === 'ar' ? 'تفعيل الإشعارات الفورية' : 'Enable push notifications'}</span>
                  </>
                )}
              </button>
            </div>
          )}
          
          {/* قائمة الإشعارات */}
          <div className="max-h-[400px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell size={40} className="mx-auto text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground">
                  {lang === 'ar' ? 'لا توجد إشعارات' : 'No notifications'}
                </p>
              </div>
            ) : (
              notifications.slice(0, 15).map((notification, index) => {
                const Icon = getIcon(notification.icon);
                const isUnread = !notification.is_read;
                
                return (
                  <div
                    key={notification.id || index}
                    onClick={() => handleNotificationClick(notification)}
                    className={`relative px-4 py-3 border-b border-border/50 cursor-pointer transition-all hover:bg-muted/50 ${
                      isUnread ? 'bg-primary/5' : ''
                    } ${notification.priority === 'critical' ? 'bg-destructive/10/50 dark:bg-red-950/20' : ''}`}
                    data-testid={`notification-item-${index}`}
                  >
                    {/* مؤشر غير مقروء */}
                    {isUnread && (
                      <span className="absolute top-4 start-1 w-2 h-2 rounded-full bg-primary" />
                    )}
                    
                    <div className="flex items-start gap-3">
                      {/* الأيقونة */}
                      <div 
                        className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{ 
                          backgroundColor: `${notification.color || '#6B7280'}15`,
                          color: notification.color || '#6B7280'
                        }}
                      >
                        <Icon size={20} />
                      </div>
                      
                      {/* المحتوى */}
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${isUnread ? 'font-semibold' : 'font-medium'} line-clamp-1`}>
                          {lang === 'ar' ? notification.title_ar : notification.title}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                          {lang === 'ar' ? notification.message_ar : notification.message}
                        </p>
                        <p className="text-[10px] text-muted-foreground/70 mt-1">
                          {formatRelativeTime(notification.created_at, lang)}
                        </p>
                      </div>
                      
                      {/* زر التحديد كمقروء */}
                      {isUnread && !notification.is_live && (
                        <button
                          onClick={(e) => handleMarkRead(notification.id, e)}
                          className="p-1 rounded-lg hover:bg-muted text-muted-foreground"
                          title={lang === 'ar' ? 'تحديد كمقروء' : 'Mark as read'}
                        >
                          <Check size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
          
          {/* Footer */}
          {notifications.length > 15 && (
            <div className="p-3 border-t border-border bg-muted/30">
              <button
                onClick={() => {
                  setIsOpen(false);
                  // يمكن إضافة صفحة لجميع الإشعارات لاحقاً
                }}
                className="w-full text-center text-xs text-primary hover:underline"
              >
                {lang === 'ar' ? `عرض جميع الإشعارات (${notifications.length})` : `View all notifications (${notifications.length})`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
