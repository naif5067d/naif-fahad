import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, CalendarDays, Clock, FileSignature, Users, Settings, Shield, Menu, X, Sun, Moon, Globe, ChevronDown, Check, MapPin, Package, Wallet, Wrench, FileCheck, Receipt, AlertTriangle, UsersRound, LogOut, History, ClipboardList, Hammer, Activity, Maximize, Minimize } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import api from '@/lib/api';
import NotificationBell from '@/components/NotificationBell';

const NAV_ITEMS = {
  // الموظفون العاديون يرون الحضور والماليات والمهام
  employee: ['dashboard', 'transactions', 'leave', 'attendance', 'tasks', 'myFinances'],
  // المشرف يرى الحضور والعقوبات لمتابعة فريقه
  supervisor: ['dashboard', 'transactions', 'leave', 'attendance', 'tasks', 'myFinances', 'attendancePenalties'],
  // سلطان موظف + إداري
  // سلطان مدير إداري
  sultan: ['executive', 'dashboard', 'transactions', 'leave', 'attendance', 'tasks', 'maintenanceTracking', 'attendancePenalties', 'financialCustody', 'custody', 'contractsManagement', 'settlement', 'employees', 'workLocations'],
  // نايف إداري فقط
  naif: ['executive', 'dashboard', 'transactions', 'tasks', 'maintenanceTracking', 'attendancePenalties', 'financialCustody', 'custody', 'contractsManagement', 'settlement', 'employees', 'workLocations'],
  // صلاح مالي فقط
  salah: ['dashboard', 'transactions', 'financialCustody'],
  // محمد CEO
  mohammed: ['executive', 'dashboard', 'transactions', 'tasks', 'financialCustody'],
  // ستاس إداري + صلاحيات كاملة (loginSessions خاصة به فقط)
  stas: ['executive', 'dashboard', 'transactions', 'tasks', 'maintenanceTracking', 'stasMirror', 'systemMaintenance', 'attendancePenalties', 'loginSessions', 'financialCustody', 'custody', 'contractsManagement', 'settlement', 'employees', 'workLocations'],
};

// Mobile bottom nav - only show first 4-5 items
const MOBILE_NAV_ITEMS = ['dashboard', 'transactions', 'leave', 'attendance'];

const ICONS = {
  executive: Activity, dashboard: LayoutDashboard, transactions: FileText, leave: CalendarDays,
  attendance: Clock, contracts: FileSignature,
  contractsManagement: FileCheck, settlement: Receipt, employees: Users, settings: Settings, stasMirror: Shield, workLocations: MapPin,
  custody: Package, financialCustody: Wallet, systemMaintenance: Wrench, myFinances: Receipt, teamAttendance: UsersRound, penalties: AlertTriangle,
  attendancePenalties: UsersRound, loginSessions: History, tasks: ClipboardList, maintenanceTracking: Hammer,
};

const PATHS = {
  dashboard: '/', transactions: '/transactions', leave: '/leave',
  attendance: '/attendance', contracts: '/contracts',
  contractsManagement: '/contracts-management', settlement: '/settlement', employees: '/employees', settings: '/settings', stasMirror: '/stas-mirror',
  workLocations: '/work-locations', custody: '/custody', financialCustody: '/financial-custody',
  systemMaintenance: '/system-maintenance', myFinances: '/my-finances', teamAttendance: '/team-attendance', penalties: '/penalties',
  attendancePenalties: '/team-attendance', loginSessions: '/login-sessions', tasks: '/tasks', maintenanceTracking: '/maintenance-tracking',
  executive: '/executive',
};

const ROLE_COLORS = {
  employee: { bg: 'hsl(217, 91%, 60%)', text: 'hsl(217, 91%, 60%)' },
  supervisor: { bg: 'hsl(222, 47%, 24%)', text: 'hsl(222, 47%, 24%)' },
  sultan: { bg: 'hsl(262, 83%, 76%)', text: 'hsl(262, 83%, 76%)' },
  mohammed: { bg: 'hsl(0, 84%, 60%)', text: 'hsl(0, 84%, 60%)' },
  stas: { bg: 'hsl(262, 83%, 76%)', text: 'hsl(262, 83%, 76%)' },
  naif: { bg: 'hsl(160, 84%, 39%)', text: 'hsl(160, 84%, 39%)' },
  salah: { bg: 'hsl(160, 84%, 39%)', text: 'hsl(160, 84%, 39%)' },
};

const ROLE_LABELS = {
  stas: 'STAS', mohammed: 'CEO', sultan: 'Ops Admin',
  naif: 'Ops Strategic', salah: 'Finance', supervisor: 'Supervisor', employee: 'Employee',
};
const ROLE_LABELS_AR = {
  stas: 'ستاس', mohammed: 'الرئيس التنفيذي', sultan: 'مدير العمليات',
  naif: 'العمليات الاستراتيجية', salah: 'المالية', supervisor: 'مشرف', employee: 'موظف',
};

export default function AppLayout({ children }) {
  const { user, allUsers, switchUser, fetchAllUsers, logout, logoutAllDevices } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [alerts, setAlerts] = useState({ alerts: [], count: 0 });
  const [showLogoutMenu, setShowLogoutMenu] = useState(false);
  const switcherRef = useRef(null);
  const alertsRef = useRef(null);
  const logoutRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Check if fullscreen is supported
  const isFullscreenSupported = () => {
    const doc = document.documentElement;
    return !!(
      doc.requestFullscreen ||
      doc.webkitRequestFullscreen ||
      doc.mozRequestFullScreen ||
      doc.msRequestFullscreen
    );
  };

  // Fullscreen handler with mobile support
  const toggleFullscreen = async () => {
    try {
      const doc = document.documentElement;
      const isCurrentlyFullscreen = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );

      if (!isCurrentlyFullscreen) {
        // Enter fullscreen
        if (doc.requestFullscreen) {
          await doc.requestFullscreen();
        } else if (doc.webkitRequestFullscreen) {
          // Safari/iOS
          await doc.webkitRequestFullscreen();
        } else if (doc.mozRequestFullScreen) {
          // Firefox
          await doc.mozRequestFullScreen();
        } else if (doc.msRequestFullscreen) {
          // IE/Edge
          await doc.msRequestFullscreen();
        }
        setIsFullscreen(true);
      } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
          await document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          await document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
          await document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
          await document.msExitFullscreen();
        }
        setIsFullscreen(false);
      }
    } catch (err) {
      // Fullscreen not supported on this device/browser
      console.warn('Fullscreen not supported:', err.message);
      // Show a toast or alert for mobile users
      if (typeof window !== 'undefined' && window.innerWidth < 768) {
        alert(lang === 'ar' ? 'وضع ملء الشاشة غير مدعوم على هذا الجهاز' : 'Fullscreen not supported on this device');
      }
    }
  };

  // Listen for fullscreen changes (with prefixes)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFS = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );
      setIsFullscreen(isFS);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, []);

  const role = user?.role || 'employee';
  const items = NAV_ITEMS[role] || NAV_ITEMS.employee;
  const mobileItems = items.filter(item => MOBILE_NAV_ITEMS.includes(item) || item === 'stasMirror');
  const colors = ROLE_COLORS[role] || ROLE_COLORS.employee;
  const isAdmin = ['sultan', 'naif', 'stas'].includes(role);

  const displayName = role === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name);
  const roleLabel = role === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? ROLE_LABELS_AR[role] : ROLE_LABELS[role]);

  useEffect(() => {
    if (allUsers.length === 0) fetchAllUsers();
  }, [allUsers.length, fetchAllUsers]);

  // Fetch alerts for admin users
  useEffect(() => {
    if (isAdmin) {
      api.get('/api/notifications/header-alerts')
        .then(r => setAlerts(r.data))
        .catch(() => {});
    }
  }, [isAdmin]);

  useEffect(() => {
    const handler = (e) => {
      if (switcherRef.current && !switcherRef.current.contains(e.target)) {
        setSwitcherOpen(false);
      }
      if (alertsRef.current && !alertsRef.current.contains(e.target)) {
        setAlertsOpen(false);
      }
      if (logoutRef.current && !logoutRef.current.contains(e.target)) {
        setShowLogoutMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSwitch = async (u) => {
    if (u.id === user?.id || switching) return;
    setSwitching(true);
    await switchUser(u.id);
    setSwitcherOpen(false);
    setSwitching(false);
    navigate('/');
  };

  // Desktop sidebar content
  const sidebarContent = (
    <nav className="flex flex-col h-full">
      {/* Logo/Brand - Desktop only */}
      <div className="p-5 border-b border-border hidden md:block">
        <h1 className="text-base font-bold tracking-tight text-foreground" data-testid="app-title">
          {t('app.name')}
        </h1>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{t('app.company')}</p>
      </div>
      
      {/* Navigation */}
      <div className="flex-1 py-3 overflow-y-auto">
        {items.map(item => {
          const Icon = ICONS[item];
          const path = PATHS[item];
          const isActive = location.pathname === path || (item === 'dashboard' && location.pathname === '/');
          return (
            <button
              key={item}
              data-testid={`nav-${item}`}
              onClick={() => { navigate(path); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-5 py-3 text-sm font-medium transition-all ${
                isActive
                  ? 'bg-primary/10 text-primary border-s-3 border-primary'
                  : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground border-s-3 border-transparent'
              }`}
            >
              <Icon size={20} strokeWidth={isActive ? 2 : 1.5} />
              <span>{t(`nav.${item}`)}</span>
            </button>
          );
        })}
      </div>

      {/* User info at bottom */}
      <div className="border-t border-border p-4">
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white"
            style={{ background: colors.bg }}
          >
            {role === 'stas' ? (lang === 'ar' ? 'س' : 'S') : (user?.full_name || 'U')[0]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{displayName}</p>
            <p className="text-xs text-muted-foreground">{roleLabel}</p>
          </div>
        </div>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 bg-card border-e border-border z-30">
        {sidebarContent}
      </aside>

      {/* Mobile overlay sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setSidebarOpen(false)} />
          <aside className="fixed inset-y-0 start-0 w-72 bg-card border-e border-border z-50 animate-fade-in">
            <div className="absolute top-4 end-4">
              <button onClick={() => setSidebarOpen(false)} className="p-2 rounded-lg hover:bg-muted touch-target" data-testid="close-sidebar">
                <X size={20} />
              </button>
            </div>
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="md:ms-64 pb-20 md:pb-0">
        {/* Top header - with safe area for iPhone notch/Dynamic Island */}
        <header className="sticky top-0 z-20 bg-background/90 backdrop-blur-md border-b border-border safe-header">
          <div className="flex items-center justify-between px-3 md:px-6 h-14 md:h-16">
            {/* Mobile menu button */}
            <button 
              className="md:hidden p-2 -ms-1 rounded-xl hover:bg-muted active:bg-muted/80" 
              onClick={() => setSidebarOpen(true)} 
              data-testid="open-sidebar"
            >
              <Menu size={22} />
            </button>
            
            {/* Page title (desktop) */}
            <div className="hidden md:block" />

            {/* Right side controls */}
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              {/* Fullscreen Toggle - Desktop only */}
              <button 
                data-testid="toggle-fullscreen" 
                onClick={toggleFullscreen} 
                className="hidden md:flex p-2 rounded-xl hover:bg-muted text-muted-foreground transition-colors"
                title={isFullscreen ? (lang === 'ar' ? 'إلغاء ملء الشاشة' : 'Exit Fullscreen') : (lang === 'ar' ? 'ملء الشاشة' : 'Fullscreen')}
              >
                {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
              </button>

              {/* Notification Bell - ALWAYS visible */}
              <NotificationBell />

              {/* User Switcher - STAS ONLY */}
              {role === 'stas' ? (
                <div className="relative" ref={switcherRef}>
                  <button
                    data-testid="user-switcher-btn"
                    onClick={() => setSwitcherOpen(!switcherOpen)}
                    className="flex items-center gap-1.5 px-1.5 sm:px-2 py-1.5 text-sm rounded-xl hover:bg-muted border border-border transition-all"
                  >
                    <div 
                      className="w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                      style={{ background: colors.bg }}
                    >
                      {lang === 'ar' ? 'س' : 'S'}
                    </div>
                    <span className="hidden sm:inline text-sm font-medium truncate max-w-[80px]">{displayName}</span>
                    <ChevronDown size={12} className={`text-muted-foreground transition-transform flex-shrink-0 ${switcherOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {switcherOpen && (
                    <div className="absolute top-full mt-2 end-0 w-72 bg-card border border-border rounded-2xl shadow-xl overflow-hidden animate-fade-in z-50" data-testid="user-switcher-dropdown">
                      <div className="px-4 py-3 border-b border-border bg-muted/30">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                          {lang === 'ar' ? 'تبديل المستخدم' : 'Switch User'}
                        </p>
                      </div>
                      <div className="max-h-80 overflow-y-auto py-2">
                        {allUsers.filter(u => u.is_active !== false).map(u => {
                          const isActive = u.id === user?.id;
                          const uRole = u.role;
                          const uColors = ROLE_COLORS[uRole] || ROLE_COLORS.employee;
                          const uName = uRole === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? (u.full_name_ar || u.full_name) : u.full_name);
                          const uRoleLabel = uRole === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? ROLE_LABELS_AR[uRole] : ROLE_LABELS[uRole]);
                          return (
                            <button
                              key={u.id}
                              data-testid={`switch-to-${u.username}`}
                              onClick={() => handleSwitch(u)}
                              disabled={switching}
                              className={`w-full flex items-center gap-3 px-4 py-3 text-start transition-colors ${
                                isActive ? 'bg-primary/5' : 'hover:bg-muted/60'
                              }`}
                            >
                              <div 
                                className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
                                style={{ background: uColors.bg }}
                              >
                                {uRole === 'stas' ? (lang === 'ar' ? 'س' : 'S') : (u.full_name || 'U')[0]}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className={`text-sm truncate ${isActive ? 'font-bold text-primary' : 'font-medium'}`}>{uName}</p>
                                <p className="text-xs text-muted-foreground">{uRoleLabel}</p>
                              </div>
                              {isActive && <Check size={18} className="text-primary flex-shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Regular user profile indicator */
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-1.5 text-sm rounded-xl border border-border">
                  <div 
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                    style={{ background: colors.bg }}
                  >
                    {(user?.full_name || 'U')[0]}
                  </div>
                  <span className="text-sm font-medium truncate max-w-[80px]">{displayName}</span>
                </div>
              )}

              {/* Language toggle */}
              <button 
                data-testid="toggle-lang" 
                onClick={toggleLang} 
                className="p-2 rounded-xl hover:bg-muted active:bg-muted/80 text-muted-foreground transition-colors"
                title={t('lang.toggle')}
              >
                <Globe size={18} />
              </button>

              {/* Theme toggle */}
              <button 
                data-testid="toggle-theme" 
                onClick={toggleTheme} 
                className="p-2 rounded-xl hover:bg-muted active:bg-muted/80 text-muted-foreground transition-colors"
                title={t('theme.toggle')}
              >
                {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
              </button>

              {/* Logout button */}
              <div className="relative" ref={logoutRef}>
                <button 
                  data-testid="logout-btn" 
                  onClick={() => setShowLogoutMenu(!showLogoutMenu)}
                  className="p-2 rounded-xl hover:bg-destructive/10 hover:text-destructive active:bg-destructive/15 text-muted-foreground transition-colors"
                  title={lang === 'ar' ? 'تسجيل الخروج' : 'Logout'}
                >
                  <LogOut size={18} />
                </button>
                
                {showLogoutMenu && (
                  <div className="absolute top-full mt-2 end-0 w-56 bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-fade-in z-50">
                    <button
                      onClick={() => { logout(); setShowLogoutMenu(false); }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm hover:bg-muted transition-colors text-start"
                      data-testid="logout-current"
                    >
                      <LogOut size={16} />
                      <span>{lang === 'ar' ? 'تسجيل الخروج' : 'Logout'}</span>
                    </button>
                    <button
                      onClick={async () => {
                        if (window.confirm(lang === 'ar' ? 'سيتم تسجيل خروجك من جميع الأجهزة. هل تريد المتابعة؟' : 'You will be logged out from all devices. Continue?')) {
                          try {
                            await logoutAllDevices();
                          } catch (e) {
                            alert(lang === 'ar' ? 'حدث خطأ' : 'Error occurred');
                          }
                        }
                        setShowLogoutMenu(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-sm hover:bg-destructive/10 text-destructive transition-colors text-start border-t border-border"
                      data-testid="logout-all-devices"
                    >
                      <Shield size={16} />
                      <span>{lang === 'ar' ? 'الخروج من جميع الأجهزة' : 'Logout all devices'}</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in main-content-mobile">
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-nav md:hidden" data-testid="mobile-bottom-nav">
        <div className="flex items-center justify-around px-2 py-2">
          {mobileItems.slice(0, 5).map(item => {
            const Icon = ICONS[item];
            const path = PATHS[item];
            const isActive = location.pathname === path || (item === 'dashboard' && location.pathname === '/');
            return (
              <button
                key={item}
                onClick={() => navigate(path)}
                className={`flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all touch-target ${
                  isActive ? 'text-primary bg-primary/10' : 'text-muted-foreground'
                }`}
                data-testid={`mobile-nav-${item}`}
              >
                <Icon size={22} strokeWidth={isActive ? 2 : 1.5} />
                <span className="text-[10px] font-medium">{t(`nav.${item}`)}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
