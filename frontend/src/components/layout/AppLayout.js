import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, CalendarDays, Clock, FileSignature, Users, Settings, Shield, Menu, X, Sun, Moon, Globe, ChevronDown, Check, MapPin, Package, Wallet, Wrench, FileCheck, Receipt, Bell, AlertTriangle } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import api from '@/lib/api';

const NAV_ITEMS = {
  employee: ['dashboard', 'transactions', 'leave', 'attendance'],
  supervisor: ['dashboard', 'transactions', 'leave', 'attendance'],
  sultan: ['dashboard', 'transactions', 'leave', 'attendance', 'financialCustody', 'custody', 'contractsManagement', 'settlement', 'employees', 'workLocations'],
  naif: ['dashboard', 'transactions', 'leave', 'attendance', 'financialCustody', 'custody', 'contractsManagement', 'settlement', 'employees', 'workLocations'],
  salah: ['dashboard', 'transactions', 'financialCustody'],
  mohammed: ['dashboard', 'transactions', 'financialCustody'],
  stas: ['dashboard', 'transactions', 'stasMirror', 'systemMaintenance', 'leave', 'attendance', 'financialCustody', 'custody', 'contractsManagement', 'settlement', 'employees', 'workLocations'],
};

// Mobile bottom nav - only show first 4-5 items
const MOBILE_NAV_ITEMS = ['dashboard', 'transactions', 'leave', 'attendance'];

const ICONS = {
  dashboard: LayoutDashboard, transactions: FileText, leave: CalendarDays,
  attendance: Clock, contracts: FileSignature,
  contractsManagement: FileCheck, settlement: Receipt, employees: Users, settings: Settings, stasMirror: Shield, workLocations: MapPin,
  custody: Package, financialCustody: Wallet, systemMaintenance: Wrench,
};

const PATHS = {
  dashboard: '/', transactions: '/transactions', leave: '/leave',
  attendance: '/attendance', contracts: '/contracts',
  contractsManagement: '/contracts-management', settlement: '/settlement', employees: '/employees', settings: '/settings', stasMirror: '/stas-mirror',
  workLocations: '/work-locations', custody: '/custody', financialCustody: '/financial-custody',
  systemMaintenance: '/system-maintenance',
};

const ROLE_COLORS = {
  employee: { bg: '#3B82F6', text: '#3B82F6' },
  supervisor: { bg: '#1D4ED8', text: '#1D4ED8' },
  sultan: { bg: '#F97316', text: '#F97316' },
  mohammed: { bg: '#DC2626', text: '#DC2626' },
  stas: { bg: '#A78BFA', text: '#A78BFA' },
  naif: { bg: '#22C55E', text: '#22C55E' },
  salah: { bg: '#14B8A6', text: '#14B8A6' },
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
  const { user, allUsers, switchUser, fetchAllUsers } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [alerts, setAlerts] = useState({ alerts: [], count: 0 });
  const switcherRef = useRef(null);
  const alertsRef = useRef(null);

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
      {/* Logo/Brand */}
      <div className="p-5 border-b border-border">
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
        {/* Top header */}
        <header className="sticky top-0 z-20 bg-background/90 backdrop-blur-md border-b border-border">
          <div className="flex items-center justify-between px-4 md:px-6 h-16">
            {/* Mobile menu button */}
            <button 
              className="md:hidden p-2 -ms-2 rounded-lg hover:bg-muted touch-target" 
              onClick={() => setSidebarOpen(true)} 
              data-testid="open-sidebar"
            >
              <Menu size={22} />
            </button>
            
            {/* Page title (desktop) */}
            <div className="hidden md:block" />

            {/* Right side controls */}
            <div className="flex items-center gap-2">
              {/* Notifications Bell (Admin only) */}
              {isAdmin && (
                <div className="relative" ref={alertsRef}>
                  <button
                    data-testid="notifications-bell"
                    onClick={() => setAlertsOpen(!alertsOpen)}
                    className="relative p-2.5 rounded-xl hover:bg-muted text-muted-foreground transition-colors touch-target"
                    title={lang === 'ar' ? 'الإشعارات' : 'Notifications'}
                  >
                    <Bell size={18} />
                    {alerts.count > 0 && (
                      <span className={`absolute -top-1 -end-1 min-w-[18px] h-[18px] flex items-center justify-center text-[10px] font-bold text-white rounded-full ${
                        alerts.critical_count > 0 ? 'bg-red-500 animate-pulse' : 'bg-amber-500'
                      }`}>
                        {alerts.count}
                      </span>
                    )}
                  </button>

                  {alertsOpen && (
                    <div className="absolute top-full mt-2 end-0 w-80 bg-card border border-border rounded-2xl shadow-xl overflow-hidden animate-fade-in z-50" data-testid="alerts-dropdown">
                      <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                          {lang === 'ar' ? 'تنبيهات العقود' : 'Contract Alerts'}
                        </p>
                        <span className="text-xs text-muted-foreground">{alerts.count} {lang === 'ar' ? 'تنبيه' : 'alerts'}</span>
                      </div>
                      <div className="max-h-80 overflow-y-auto">
                        {alerts.alerts.length === 0 ? (
                          <div className="p-4 text-center text-sm text-muted-foreground">
                            {lang === 'ar' ? 'لا توجد تنبيهات' : 'No alerts'}
                          </div>
                        ) : (
                          alerts.alerts.slice(0, 10).map(alert => (
                            <div
                              key={alert.id}
                              className={`px-4 py-3 border-b border-border/50 hover:bg-muted/30 cursor-pointer ${
                                alert.type === 'critical' ? 'bg-red-50/50' : alert.type === 'warning' ? 'bg-amber-50/50' : ''
                              }`}
                              onClick={() => {
                                setAlertsOpen(false);
                                navigate('/contracts-management');
                              }}
                            >
                              <div className="flex items-start gap-2">
                                <AlertTriangle size={16} className={`mt-0.5 flex-shrink-0 ${
                                  alert.type === 'critical' ? 'text-red-500' : alert.type === 'warning' ? 'text-amber-500' : 'text-blue-500'
                                }`} />
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-medium truncate">
                                    {lang === 'ar' ? alert.employee_name_ar || alert.employee_name : alert.employee_name}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    {lang === 'ar' ? alert.message_ar : alert.message_en}
                                  </p>
                                  <p className="text-[10px] text-muted-foreground mt-1">
                                    {alert.contract_serial} • {alert.end_date}
                                  </p>
                                </div>
                                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                                  alert.type === 'critical' ? 'bg-red-100 text-red-700' : 
                                  alert.type === 'warning' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                                }`}>
                                  {alert.days_remaining}{lang === 'ar' ? 'ي' : 'd'}
                                </span>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                      {alerts.count > 10 && (
                        <div className="p-2 border-t border-border bg-muted/30">
                          <button
                            className="w-full text-xs text-primary hover:underline"
                            onClick={() => {
                              setAlertsOpen(false);
                              navigate('/contracts-management');
                            }}
                          >
                            {lang === 'ar' ? `عرض جميع التنبيهات (${alerts.count})` : `View all alerts (${alerts.count})`}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* User Switcher */}
              <div className="relative" ref={switcherRef}>
                <button
                  data-testid="user-switcher-btn"
                  onClick={() => setSwitcherOpen(!switcherOpen)}
                  className="flex items-center gap-2.5 px-3 py-2 text-sm rounded-xl hover:bg-muted border border-border transition-all touch-target"
                >
                  <div 
                    className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
                    style={{ background: colors.bg }}
                  >
                    {role === 'stas' ? (lang === 'ar' ? 'س' : 'S') : (user?.full_name || 'U')[0]}
                  </div>
                  <span className="hidden sm:inline text-sm font-medium truncate max-w-[120px]">{displayName}</span>
                  <ChevronDown size={14} className={`text-muted-foreground transition-transform ${switcherOpen ? 'rotate-180' : ''}`} />
                </button>

                {switcherOpen && (
                  <div className="absolute top-full mt-2 end-0 w-80 bg-card border border-border rounded-2xl shadow-xl overflow-hidden animate-fade-in z-50" data-testid="user-switcher-dropdown">
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

              {/* Language toggle */}
              <button 
                data-testid="toggle-lang" 
                onClick={toggleLang} 
                className="p-2.5 rounded-xl hover:bg-muted text-muted-foreground transition-colors touch-target"
                title={t('lang.toggle')}
              >
                <Globe size={18} />
              </button>

              {/* Theme toggle */}
              <button 
                data-testid="toggle-theme" 
                onClick={toggleTheme} 
                className="p-2.5 rounded-xl hover:bg-muted text-muted-foreground transition-colors touch-target"
                title={t('theme.toggle')}
              >
                {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
              </button>
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
