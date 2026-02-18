import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { 
  Bell, Check, CheckCheck, FileText, XCircle, CheckCircle, 
  Clock, DollarSign, AlertTriangle, Calendar, FileWarning,
  Shield, RotateCcw, UserX, LogOut, Settings, Megaphone, X
} from 'lucide-react';
import api from '@/lib/api';

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

// صوت الإشعار
const playNotificationSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(600, audioContext.currentTime + 0.1);
    oscillator.frequency.exponentialRampToValueAtTime(900, audioContext.currentTime + 0.2);
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3);
  } catch (e) {
    console.log('Audio not supported');
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
  
  return date.toLocaleDateString(lang === 'ar' ? 'ar-SA' : 'en-US', { month: 'short', day: 'numeric' });
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
  const bellRef = useRef(null);
  
  // جلب الإشعارات
  const fetchNotifications = useCallback(async () => {
    try {
      const response = await api.get('/api/notifications/bell');
      const data = response.data;
      
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
      setHasCritical(data.has_critical || false);
      
      // تشغيل الصوت عند وصول إشعار جديد
      if (data.unread_count > lastCount && lastCount > 0) {
        playNotificationSound();
      }
      setLastCount(data.unread_count || 0);
    } catch (err) {
      console.log('Failed to fetch notifications');
    }
  }, [lastCount]);
  
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
      await api.delete('/api/notifications/delete-all');
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
    <div className="relative" ref={bellRef}>
      {/* زر الجرس */}
      <button
        data-testid="notification-bell-btn"
        onClick={() => setIsOpen(!isOpen)}
        className={`relative p-2.5 rounded-xl transition-all touch-target ${
          isOpen ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-muted-foreground'
        }`}
        title={lang === 'ar' ? 'الإشعارات' : 'Notifications'}
      >
        <Bell size={20} className={hasCritical ? 'animate-bounce' : ''} />
        
        {/* شارة العدد */}
        {unreadCount > 0 && (
          <span 
            className={`absolute -top-1 -end-1 min-w-[20px] h-[20px] flex items-center justify-center text-[10px] font-bold text-white rounded-full transition-all ${
              hasCritical ? 'bg-red-500 animate-pulse' : 'bg-primary'
            }`}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      
      {/* القائمة المنسدلة */}
      {isOpen && (
        <div 
          className="absolute top-full mt-2 end-0 w-96 max-w-[calc(100vw-2rem)] bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-fade-in z-50"
          data-testid="notification-dropdown"
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-border bg-gradient-to-r from-primary/5 to-transparent flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell size={18} className="text-primary" />
              <h3 className="font-semibold text-sm">
                {lang === 'ar' ? 'الإشعارات' : 'Notifications'}
              </h3>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                  {unreadCount}
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-3">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  disabled={loading}
                  className="flex items-center gap-1 text-xs text-primary hover:underline disabled:opacity-50"
                  data-testid="mark-all-read-btn"
                >
                  <CheckCheck size={14} />
                  {lang === 'ar' ? 'رؤية الكل' : 'Read all'}
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={handleDeleteAll}
                  disabled={loading}
                  className="flex items-center gap-1 text-xs text-red-500 hover:underline disabled:opacity-50"
                  data-testid="delete-all-btn"
                >
                  <X size={14} />
                  {lang === 'ar' ? 'حذف الكل' : 'Delete all'}
                </button>
              )}
            </div>
          </div>
          
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
                    } ${notification.priority === 'critical' ? 'bg-red-50/50 dark:bg-red-950/20' : ''}`}
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
