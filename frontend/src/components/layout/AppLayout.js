import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileText, CalendarDays, Clock, DollarSign, FileSignature, Users, Settings, Shield, Menu, X, Sun, Moon, Globe, LogOut } from 'lucide-react';
import { useState } from 'react';

const NAV_ITEMS = {
  employee: ['dashboard', 'transactions', 'leave', 'attendance'],
  supervisor: ['dashboard', 'transactions', 'leave', 'attendance'],
  sultan: ['dashboard', 'transactions', 'leave', 'attendance', 'finance', 'contracts', 'employees'],
  naif: ['dashboard', 'transactions', 'leave', 'attendance', 'finance', 'contracts', 'employees'],
  salah: ['dashboard', 'transactions', 'finance'],
  mohammed: ['dashboard', 'transactions'],
  stas: ['dashboard', 'transactions', 'stasMirror', 'leave', 'attendance', 'finance', 'contracts', 'employees'],
};

const ICONS = {
  dashboard: LayoutDashboard, transactions: FileText, leave: CalendarDays,
  attendance: Clock, finance: DollarSign, contracts: FileSignature,
  employees: Users, settings: Settings, stasMirror: Shield,
};

const PATHS = {
  dashboard: '/', transactions: '/transactions', leave: '/leave',
  attendance: '/attendance', finance: '/finance', contracts: '/contracts',
  employees: '/employees', settings: '/settings', stasMirror: '/stas-mirror',
};

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const role = user?.role || 'employee';
  const items = NAV_ITEMS[role] || NAV_ITEMS.employee;

  const displayName = role === 'stas' ? 'STAS' : (lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name);
  const roleLabel = role === 'stas' ? 'STAS' : t(`roles.${role}`);

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
      <div className="border-t border-border p-3 space-y-1">
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
            {(user?.full_name || 'U')[0]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{displayName}</p>
            <p className="text-xs text-muted-foreground">{roleLabel}</p>
          </div>
        </div>
        <button data-testid="logout-btn" onClick={logout} className="w-full flex items-center gap-3 px-4 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground rounded-md transition-colors">
          <LogOut size={16} />
          <span>{t('nav.logout')}</span>
        </button>
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
            <div className="flex items-center gap-1">
              <button data-testid="toggle-lang" onClick={toggleLang} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-md hover:bg-muted text-muted-foreground transition-colors" title={t('lang.toggle')}>
                <Globe size={14} />
                <span>{t('lang.toggle')}</span>
              </button>
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
