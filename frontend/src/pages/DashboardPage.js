import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { FileText, CalendarDays, Users, Shield, DollarSign, Clock, ChevronRight, Briefcase, UserCheck, MapPin, Wallet, Settings2, Bell, Pin, X, Award, CheckCircle2, AlertTriangle as AlertTriangleIcon } from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { Button } from '@/components/ui/button';
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
  const [announcements, setAnnouncements] = useState({ pinned: [], regular: [] });
  const [appVersion, setAppVersion] = useState('');
  const [expiringContracts, setExpiringContracts] = useState({ employees: [], summary: {} });

  const role = user?.role || 'employee';
  const isAdmin = ['sultan', 'naif', 'stas'].includes(role);
  // البطاقة تظهر لكل من لديه employee_id (موظفين + مدراء)
  const hasEmployeeCard = !!user?.employee_id;
  
  // بيانات ملخص الموظف للبطاقة الشخصية
  const [employeeSummary, setEmployeeSummary] = useState(null);
  const [loadingEmployeeSummary, setLoadingEmployeeSummary] = useState(false);

  useEffect(() => {
    api.get('/api/dashboard/stats').then(r => setStats(r.data)).catch(() => {});
    api.get('/api/transactions').then(r => setRecentTxs(r.data.slice(0, 5))).catch(() => {});
    api.get('/api/dashboard/next-holiday').then(r => setNextHoliday(r.data)).catch(() => {});
    api.get('/api/announcements').then(r => setAnnouncements(r.data)).catch(() => {});
    api.get('/api/health').then(r => setAppVersion(r.data.version)).catch(() => {});
    
    // جلب العقود المنتهية للمدراء
    if (isAdmin) {
      api.get('/api/notifications/expiring-contracts?days_ahead=90')
        .then(r => setExpiringContracts(r.data))
        .catch(() => {});
    }
    
    // جلب ملخص الموظف لكل من لديه employee_id
    if (hasEmployeeCard && user?.employee_id) {
      setLoadingEmployeeSummary(true);
      api.get(`/api/employees/${user.employee_id}/summary`)
        .then(r => setEmployeeSummary(r.data))
        .catch((err) => console.log('Employee summary error:', err))
        .finally(() => setLoadingEmployeeSummary(false));
    }
  }, [isAdmin, hasEmployeeCard, user?.employee_id]);

  const dismissAnnouncement = async (id) => {
    try {
      await api.post(`/api/announcements/${id}/dismiss`);
      setAnnouncements(prev => ({
        ...prev,
        regular: prev.regular.filter(a => a.id !== id)
      }));
    } catch (err) {}
  };

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
          
          {/* Pinned Announcements - Always visible */}
          {announcements.pinned.length > 0 && (
            <div className="mt-4 space-y-2">
              {announcements.pinned.map(ann => (
                <div key={ann.id} className="flex items-start gap-2 p-3 bg-white/10 rounded-lg backdrop-blur-sm">
                  <Pin size={16} className="text-amber-300 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-white/90">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Regular Announcements - Show once popup style */}
      {announcements.regular.length > 0 && (
        <div className="space-y-2">
          {announcements.regular.map(ann => (
            <div key={ann.id} className="flex items-start justify-between p-4 bg-blue-50 border border-blue-200 rounded-xl">
              <div className="flex items-start gap-3">
                <Bell size={18} className="text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-900">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
                  <p className="text-xs text-blue-600 mt-1">{ann.created_by_name}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => dismissAnnouncement(ann.id)}
                className="text-blue-600 hover:text-blue-800 hover:bg-blue-100"
              >
                <X size={16} />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Employee Personal Card - Shown to anyone with employee_id */}
      {hasEmployeeCard && employeeSummary && (
        <div className="card-premium rounded-2xl overflow-hidden" data-testid="employee-personal-card">
          <div className="p-5 space-y-4">
            {/* Employee Header */}
            <div className="flex items-center gap-4">
              {/* Profile Photo or Initial */}
              {employeeSummary.employee?.photo_url ? (
                <img 
                  src={employeeSummary.employee.photo_url}
                  alt={lang === 'ar' ? user?.full_name_ar : user?.full_name}
                  className="w-16 h-16 rounded-2xl object-cover"
                />
              ) : (
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center text-2xl font-bold text-primary">
                  {(lang === 'ar' ? user?.full_name_ar : user?.full_name)?.[0] || 'U'}
                </div>
              )}
              <div className="flex-1">
                <h3 className="text-lg font-bold">
                  {lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {lang === 'ar' ? employeeSummary.contract?.job_title_ar : employeeSummary.contract?.job_title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {lang === 'ar' ? employeeSummary.contract?.department_ar : employeeSummary.contract?.department}
                </p>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                user?.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {user?.is_active !== false ? (lang === 'ar' ? 'نشط' : 'Active') : (lang === 'ar' ? 'غير نشط' : 'Inactive')}
              </span>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center p-3 bg-muted/50 rounded-xl">
                <CalendarDays size={20} className="mx-auto mb-1 text-primary" />
                <p className="text-xl font-bold text-primary">{employeeSummary.leave_details?.balance || 0}</p>
                <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'رصيد الإجازة' : 'Leave Balance'}</p>
              </div>
              <div className="text-center p-3 bg-muted/50 rounded-xl">
                <Award size={20} className="mx-auto mb-1 text-amber-500" />
                <p className="text-xl font-bold text-amber-600">{employeeSummary.service_info?.years_display || '0'}</p>
                <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'سنوات الخدمة' : 'Service Years'}</p>
              </div>
              <div className="text-center p-3 bg-muted/50 rounded-xl">
                <Clock size={20} className="mx-auto mb-1 text-green-500" />
                <p className="text-xl font-bold">
                  {employeeSummary.attendance?.today_status === 'present' ? (
                    <CheckCircle2 size={24} className="mx-auto text-green-500" />
                  ) : (
                    <AlertTriangleIcon size={24} className="mx-auto text-amber-500" />
                  )}
                </p>
                <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'حضور اليوم' : 'Today'}</p>
              </div>
            </div>

            {/* Contract Info Summary */}
            {employeeSummary.contract && (
              <div className="flex items-center justify-between text-sm pt-2 border-t">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Briefcase size={14} />
                  <span>{lang === 'ar' ? 'انتهاء العقد:' : 'Contract ends:'}</span>
                </div>
                <span className="font-medium">
                  {employeeSummary.contract.end_date || (lang === 'ar' ? 'غير محدد' : 'Unlimited')}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {loadingEmployeeSummary && hasEmployeeCard && (
        <div className="card-premium rounded-2xl p-8 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Expiring Contracts Alert (Admin only) */}
      {isAdmin && expiringContracts.employees?.length > 0 && (
        <div className="space-y-3" data-testid="expiring-contracts-section">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell size={18} className="text-amber-500" />
              <h2 className="text-lg font-semibold">
                {lang === 'ar' ? 'تنبيه: عقود قاربت على الانتهاء' : 'Alert: Expiring Contracts'}
              </h2>
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                {expiringContracts.summary.total} {lang === 'ar' ? 'موظف' : 'employees'}
              </span>
            </div>
            <button 
              onClick={() => navigate('/contracts-management')} 
              className="text-sm text-primary font-medium flex items-center gap-1"
            >
              {lang === 'ar' ? 'عرض الكل' : 'View all'}
              <ChevronRight size={16} className="rtl:rotate-180" />
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {expiringContracts.employees.slice(0, 6).map(emp => (
              <div 
                key={emp.employee_id}
                className={`p-4 rounded-xl border ${
                  emp.urgency === 'critical' ? 'border-red-200 bg-red-50 animate-pulse' : 
                  emp.urgency === 'high' ? 'border-amber-200 bg-amber-50' : 'border-gray-200 bg-gray-50'
                }`}
                data-testid={`expiring-contract-${emp.employee_code}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className={`font-medium ${emp.urgency === 'critical' ? 'text-red-700' : ''}`}>
                      {lang === 'ar' ? emp.employee_name_ar || emp.employee_name : emp.employee_name}
                    </p>
                    <p className="text-xs text-muted-foreground">{emp.employee_code}</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    emp.urgency === 'critical' ? 'bg-red-100 text-red-700' : 
                    emp.urgency === 'high' ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {emp.days_remaining} {lang === 'ar' ? 'يوم' : 'days'}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {lang === 'ar' ? 'انتهاء:' : 'Expires:'} {emp.end_date}
                  </span>
                  <span className="text-muted-foreground">
                    {lang === 'ar' ? 'رصيد الإجازة:' : 'Leave:'} {emp.leave_balance} {lang === 'ar' ? 'يوم' : 'd'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
            <p className="text-xs text-muted-foreground font-mono">{formatGregorianHijri(nextHoliday.date).combined}</p>
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

      {/* App Version */}
      {appVersion && (
        <div className="text-center text-xs text-muted-foreground pt-4 border-t">
          DAR AL CODE HR OS v{appVersion}
        </div>
      )}
    </div>
  );
}
