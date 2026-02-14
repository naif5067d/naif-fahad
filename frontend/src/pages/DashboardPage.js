import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { FileText, CalendarDays, Users, Shield, DollarSign, Clock, ChevronRight, Briefcase, UserCheck, MapPin, Wallet, Settings2 } from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import api from '@/lib/api';

const STAT_CONFIG = {
  employee: [
    { key: 'leave_balance', icon: CalendarDays, label: 'dashboard.leaveBalance', suffix: 'dashboard.days', gradient: true },
    { key: 'pending_transactions', icon: FileText, label: 'dashboard.pendingApprovals' },
  ],
  supervisor: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', gradient: true },
    { key: 'team_size', icon: Users, label: 'dashboard.teamSize' },
  ],
  sultan: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', gradient: true },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
    { key: 'total_transactions', icon: Clock, label: 'dashboard.totalTransactions' },
  ],
  naif: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', gradient: true },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
  salah: [
    { key: 'pending_approvals', icon: DollarSign, label: 'dashboard.pendingFinance', gradient: true },
    { key: 'total_finance_entries', icon: FileText, label: 'dashboard.totalTransactions' },
  ],
  mohammed: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', gradient: true },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
  stas: [
    { key: 'pending_execution', icon: Shield, label: 'dashboard.pendingExecution', gradient: true },
    { key: 'total_transactions', icon: FileText, label: 'dashboard.totalTransactions' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
};

// Quick actions based on role
const QUICK_ACTIONS = {
  employee: [
    { key: 'leave', icon: CalendarDays, path: '/leave', color: '#3B82F6' },
    { key: 'attendance', icon: Clock, path: '/attendance', color: '#10B981' },
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#8B5CF6' },
  ],
  supervisor: [
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#F97316' },
    { key: 'leave', icon: CalendarDays, path: '/leave', color: '#3B82F6' },
    { key: 'attendance', icon: Clock, path: '/attendance', color: '#10B981' },
  ],
  sultan: [
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#F97316' },
    { key: 'employees', icon: Users, path: '/employees', color: '#3B82F6' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody', color: '#A78BFA' },
    { key: 'workLocations', icon: MapPin, path: '/work-locations', color: '#10B981' },
  ],
  naif: [
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#F97316' },
    { key: 'employees', icon: Users, path: '/employees', color: '#3B82F6' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody', color: '#A78BFA' },
  ],
  salah: [
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#14B8A6' },
    { key: 'finance', icon: DollarSign, path: '/finance', color: '#10B981' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody', color: '#A78BFA' },
  ],
  mohammed: [
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#DC2626' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody', color: '#A78BFA' },
  ],
  stas: [
    { key: 'stasMirror', icon: Shield, path: '/stas-mirror', color: '#A78BFA' },
    { key: 'transactions', icon: FileText, path: '/transactions', color: '#F97316' },
    { key: 'employees', icon: Users, path: '/employees', color: '#3B82F6' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody', color: '#10B981' },
    { key: 'companySettings', icon: Settings2, path: '/company-settings', color: '#64748B' },
  ],
};

const STATUS_COLORS = {
  executed: { bg: '#10B98120', text: '#10B981' },
  rejected: { bg: '#EF444420', text: '#EF4444' },
  pending_supervisor: { bg: '#1D4ED820', text: '#1D4ED8' },
  pending_ops: { bg: '#F9731620', text: '#F97316' },
  pending_finance: { bg: '#14B8A620', text: '#14B8A6' },
  pending_ceo: { bg: '#DC262620', text: '#DC2626' },
  pending_stas: { bg: '#A78BFA20', text: '#A78BFA' },
  pending_employee_accept: { bg: '#3B82F620', text: '#3B82F6' },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
  const [recentTxs, setRecentTxs] = useState([]);
  const [nextHoliday, setNextHoliday] = useState(null);

  useEffect(() => {
    api.get('/api/dashboard/stats').then(r => setStats(r.data)).catch(() => {});
    api.get('/api/transactions').then(r => setRecentTxs(r.data.slice(0, 5))).catch(() => {});
    api.get('/api/dashboard/next-holiday').then(r => setNextHoliday(r.data)).catch(() => {});
  }, []);

  const role = user?.role || 'employee';
  const statCards = STAT_CONFIG[role] || STAT_CONFIG.employee;
  const quickActions = QUICK_ACTIONS[role] || QUICK_ACTIONS.employee;
  const displayName = role === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name);

  const getStatusStyle = (status) => STATUS_COLORS[status] || STATUS_COLORS.pending_ops;
  const getTranslatedType = (type) => t(`txTypes.${type}`) || type?.replace(/_/g, ' ');
  const getTranslatedStage = (stage) => {
    if (stage === 'stas') return lang === 'ar' ? 'ستاس' : 'STAS';
    return t(`stages.${stage}`) || stage;
  };

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Welcome Hero Card - Gradient */}
      <div className="gradient-hero rounded-2xl p-6 md:p-8 text-white" data-testid="welcome-hero">
        <div className="relative z-10">
          <p className="text-white/70 text-sm font-medium mb-1">
            {lang === 'ar' ? 'مرحباً بك' : 'Welcome back'}
          </p>
          <h1 className="text-2xl md:text-3xl font-bold mb-2">{displayName}</h1>
          <p className="text-white/80 text-sm">{t(`roles.${role}`)}</p>
          
          {/* Main stat in hero */}
          {statCards[0] && (
            <div className="mt-6 flex items-end gap-3">
              <span className="text-4xl md:text-5xl font-bold">
                {stats[statCards[0].key] ?? 0}
              </span>
              <span className="text-white/70 text-base mb-1">
                {statCards[0].suffix ? t(statCards[0].suffix) : t(statCards[0].label)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{lang === 'ar' ? 'الخدمات' : 'Services'}</h2>
          <button 
            onClick={() => navigate('/transactions')} 
            className="text-sm text-primary font-medium flex items-center gap-1"
          >
            {lang === 'ar' ? 'عرض الكل' : 'View all'}
            <ChevronRight size={16} className="rtl:rotate-180" />
          </button>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {quickActions.map(action => {
            const Icon = action.icon;
            return (
              <button
                key={action.key}
                onClick={() => navigate(action.path)}
                className="quick-action"
                data-testid={`quick-action-${action.key}`}
              >
                <div 
                  className="w-12 h-12 rounded-2xl flex items-center justify-center mb-2"
                  style={{ background: `${action.color}15` }}
                >
                  <Icon size={22} style={{ color: action.color }} />
                </div>
                <span className="text-xs font-medium text-center leading-tight">
                  {t(`nav.${action.key}`)}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Stats Cards Row */}
      {statCards.length > 1 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {statCards.slice(1).map(sc => {
            const Icon = sc.icon;
            return (
              <div key={sc.key} className="stat-card rounded-xl p-4" data-testid={`stat-${sc.key}`}>
                <div className="flex items-center justify-between mb-3">
                  <Icon size={20} className="text-muted-foreground" />
                </div>
                <div className="text-2xl font-bold mb-1">
                  {stats[sc.key] ?? 0}
                  {sc.suffix && <span className="text-sm font-normal text-muted-foreground ms-1">{t(sc.suffix)}</span>}
                </div>
                <p className="text-xs text-muted-foreground">{t(sc.label)}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Next Holiday Card */}
      {nextHoliday && (
        <div className="card-premium p-4 flex items-center gap-4" data-testid="next-holiday-card">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
            <CalendarDays size={22} className="text-amber-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground mb-0.5">{t('dashboard.nextHoliday')}</p>
            <p className="text-sm font-semibold truncate">
              {lang === 'ar' ? nextHoliday.name_ar || nextHoliday.name : nextHoliday.name}
            </p>
            <p className="text-xs text-muted-foreground font-mono">{nextHoliday.date}</p>
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{t('dashboard.recentTransactions')}</h2>
          <button 
            onClick={() => navigate('/transactions')} 
            className="text-sm text-primary font-medium flex items-center gap-1"
          >
            {lang === 'ar' ? 'عرض الكل' : 'View all'}
            <ChevronRight size={16} className="rtl:rotate-180" />
          </button>
        </div>
        
        <div className="space-y-3">
          {recentTxs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground bg-muted/30 rounded-xl">
              <FileText size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">{t('transactions.noTransactions')}</p>
            </div>
          ) : (
            recentTxs.map(tx => {
              const statusStyle = getStatusStyle(tx.status);
              return (
                <button
                  key={tx.id}
                  onClick={() => navigate(`/transactions/${tx.id}`)}
                  className="w-full card-premium p-4 flex items-center gap-4 text-start hover:bg-muted/30 transition-colors"
                  data-testid={`tx-card-${tx.ref_no}`}
                >
                  <div 
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: statusStyle.bg }}
                  >
                    <FileText size={18} style={{ color: statusStyle.text }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{getTranslatedType(tx.type)}</p>
                    <p className="text-xs text-muted-foreground">
                      {lang === 'ar' ? (tx.data?.employee_name_ar || tx.data?.employee_name) : tx.data?.employee_name || tx.ref_no}
                    </p>
                  </div>
                  <div className="text-end flex-shrink-0">
                    <span 
                      className="inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-semibold"
                      style={{ background: statusStyle.bg, color: statusStyle.text }}
                    >
                      {t(`status.${tx.status}`) || tx.status}
                    </span>
                    <p className="text-[10px] text-muted-foreground mt-1">{getTranslatedStage(tx.current_stage)}</p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
