import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, CalendarDays, Clock, DollarSign, FileSignature, Users, Settings, Shield, Menu, X, Sun, Moon, Globe, UserCircle, ChevronDown, Check, MapPin, Package, Wallet } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';

const NAV_ITEMS = {
  employee: ['dashboard', 'transactions', 'leave', 'attendance'],
  supervisor: ['dashboard', 'transactions', 'leave', 'attendance'],
  sultan: ['dashboard', 'transactions', 'leave', 'attendance', 'finance', 'financialCustody', 'custody', 'contracts', 'employees', 'workLocations'],
  naif: ['dashboard', 'transactions', 'leave', 'attendance', 'financialCustody', 'custody', 'contracts', 'employees', 'workLocations'],
  salah: ['dashboard', 'transactions', 'finance', 'financialCustody'],
  mohammed: ['dashboard', 'transactions', 'financialCustody'],
  stas: ['dashboard', 'transactions', 'stasMirror', 'leave', 'attendance', 'finance', 'financialCustody', 'custody', 'contracts', 'employees', 'workLocations'],
};

const ICONS = {
  dashboard: LayoutDashboard, transactions: FileText, leave: CalendarDays,
  attendance: Clock, finance: DollarSign, contracts: FileSignature,
  employees: Users, settings: Settings, stasMirror: Shield, workLocations: MapPin,
  custody: Package, financialCustody: Wallet,
};

const PATHS = {
  dashboard: '/', transactions: '/transactions', leave: '/leave',
  attendance: '/attendance', finance: '/finance', contracts: '/contracts',
  employees: '/employees', settings: '/settings', stasMirror: '/stas-mirror',
  workLocations: '/work-locations', custody: '/custody', financialCustody: '/financial-custody',
};

const ROLE_COLORS = {
  employee: { bg: '#3B82F6', ring: '#3B82F630' },
  supervisor: { bg: '#1D4ED8', ring: '#1D4ED830' },
  sultan: { bg: '#F97316', ring: '#F9731630' },
  mohammed: { bg: '#B91C1C', ring: '#B91C1C30' },
  stas: { bg: '#7C3AED', ring: '#7C3AED30' },
  naif: { bg: '#4D7C0F', ring: '#4D7C0F30' },
  salah: { bg: '#0D9488', ring: '#0D948830' },
};

// Get role badge style
const getRoleBadgeStyle = (role) => {
  const colors = ROLE_COLORS[role] || ROLE_COLORS.employee;
  return {
    backgroundColor: `${colors.bg}20`,
    color: colors.bg,
    borderColor: colors.ring,
  };
};

const ROLE_LABELS = {
  stas: 'STAS',
  mohammed: 'CEO',
  sultan: 'Ops Admin',
  naif: 'Ops Strategic',
  salah: 'Finance',
  supervisor: 'Supervisor',
  employee: 'Employee',
};

const ROLE_LABELS_AR = {
  stas: 'ستاس',
  mohammed: 'الرئيس التنفيذي',
  sultan: 'مدير العمليات',
  naif: 'العمليات الاستراتيجية',
  salah: 'المالية',
  supervisor: 'مشرف',
  employee: 'موظف',
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
  const switcherRef = useRef(null);

  const role = user?.role || 'employee';
  const items = NAV_ITEMS[role] || NAV_ITEMS.employee;

  const displayName = role === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name);
  const roleLabel = role === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? ROLE_LABELS_AR[role] : ROLE_LABELS[role]);

  useEffect(() => {
    if (allUsers.length === 0) fetchAllUsers();
  }, [allUsers.length, fetchAllUsers]);

  // Close switcher on click outside
  useEffect(() => {
    const handler = (e) => {
      if (switcherRef.current && !switcherRef.current.contains(e.target)) {
        setSwitcherOpen(false);
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

  const navContent = (
    <nav className="flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <h1 className="text-sm font-bold tracking-tight text-foreground truncate" data-testid="app-title">
          {t('app.name')}
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5 truncate">{t('app.company')}</p>
      </div>
      <div className="flex-1 py-2 overflow-y-auto">
        {items.map(item => {
          const Icon = ICONS[item];
          const path = PATHS[item];
          const isActive = location.pathname === path || (item === 'dashboard' && location.pathname === '/');
          return (
            <button
              key={item}
              data-testid={`nav-${item}`}
              onClick={() => { navigate(path); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary font-medium border-r-2 border-primary rtl:border-r-0 rtl:border-l-2'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <Icon size={18} />
              <span>{t(`nav.${item}`)}</span>
            </button>
          );
        })}
      </div>

      {/* Current user display at bottom */}
      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div 
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ring-1"
            style={getRoleBadgeStyle(role)}
          >
            {role === 'stas' ? 'S' : (user?.full_name || 'U')[0]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{displayName}</p>
            <p className="text-xs text-muted-foreground">{roleLabel}</p>
          </div>
        </div>
      </div>
    </nav>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:w-60 md:flex-col md:fixed md:inset-y-0 bg-card border-r border-border z-30">
        {navContent}
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
          <aside className="fixed inset-y-0 left-0 rtl:left-auto rtl:right-0 w-64 bg-card border-r border-border rtl:border-r-0 rtl:border-l z-50">
            <div className="absolute top-3 right-3 rtl:right-auto rtl:left-3">
              <button onClick={() => setSidebarOpen(false)} className="p-1 rounded-md hover:bg-muted" data-testid="close-sidebar">
                <X size={20} />
              </button>
            </div>
            {navContent}
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="md:ms-60">
        {/* Top bar */}
        <header className="sticky top-0 z-20 bg-background/80 backdrop-blur-sm border-b border-border">
          <div className="flex items-center justify-between px-4 h-14">
            <button className="md:hidden p-2 -ms-2 rounded-md hover:bg-muted" onClick={() => setSidebarOpen(true)} data-testid="open-sidebar">
              <Menu size={20} />
            </button>
            <div className="hidden md:block" />

            <div className="flex items-center gap-1.5">
              {/* User Switcher */}
              <div className="relative" ref={switcherRef}>
                <button
                  data-testid="user-switcher-btn"
                  onClick={() => setSwitcherOpen(!switcherOpen)}
                  className="flex items-center gap-2 px-2.5 py-1.5 text-sm rounded-lg hover:bg-muted border border-border transition-all"
                >
                  <div 
                    className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ring-1"
                    style={getRoleBadgeStyle(role)}
                  >
                    {role === 'stas' ? 'S' : (user?.full_name || 'U')[0]}
                  </div>
                  <span className="hidden sm:inline text-xs font-medium truncate max-w-[100px]">{displayName}</span>
                  <ChevronDown size={12} className={`text-muted-foreground transition-transform ${switcherOpen ? 'rotate-180' : ''}`} />
                </button>

                {switcherOpen && (
                  <div className="absolute top-full mt-1.5 end-0 w-72 bg-card border border-border rounded-xl shadow-lg overflow-hidden animate-fade-in z-50" data-testid="user-switcher-dropdown">
                    <div className="px-3 py-2.5 border-b border-border bg-muted/30">
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        {lang === 'ar' ? 'تبديل المستخدم' : 'Switch User'}
                      </p>
                    </div>
                    <div className="max-h-80 overflow-y-auto py-1">
                      {allUsers.filter(u => u.is_active !== false).map(u => {
                        const isActive = u.id === user?.id;
                        const uRole = u.role;
                        const uName = uRole === 'stas' ? 'STAS' : (lang === 'ar' ? (u.full_name_ar || u.full_name) : u.full_name);
                        const uRoleLabel = uRole === 'stas' ? 'STAS' : (lang === 'ar' ? ROLE_LABELS_AR[uRole] : ROLE_LABELS[uRole]);
                        return (
                          <button
                            key={u.id}
                            data-testid={`switch-to-${u.username}`}
                            onClick={() => handleSwitch(u)}
                            disabled={switching}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 text-start transition-colors ${
                              isActive ? 'bg-primary/5' : 'hover:bg-muted/60'
                            }`}
                          >
                            <div 
                              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ring-1 flex-shrink-0"
                              style={getRoleBadgeStyle(uRole)}
                            >
                              {uRole === 'stas' ? 'S' : (u.full_name || 'U')[0]}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm truncate ${isActive ? 'font-semibold text-primary' : 'font-medium'}`}>{uName}</p>
                              <p className="text-[11px] text-muted-foreground">{uRoleLabel}</p>
                            </div>
                            {isActive && <Check size={16} className="text-primary flex-shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Language toggle */}
              <button data-testid="toggle-lang" onClick={toggleLang} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md hover:bg-muted text-muted-foreground transition-colors" title={t('lang.toggle')}>
                <Globe size={14} />
                <span className="hidden sm:inline">{t('lang.toggle')}</span>
              </button>

              {/* Theme toggle */}
              <button data-testid="toggle-theme" onClick={toggleTheme} className="p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors" title={t('theme.toggle')}>
                {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6 max-w-7xl mx-auto animate-fade-in">
          {children}
        </main>
      </div>
    </div>
  );
}
