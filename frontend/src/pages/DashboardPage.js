import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, CalendarDays, Users, Shield, DollarSign, Clock, ChevronRight, 
  Briefcase, MapPin, Wallet, Settings2, Bell, Pin, X, Award, 
  CheckCircle2, Timer, TrendingDown, Sparkles, Info
} from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import api from '@/lib/api';

// ==================== رسائل تحفيزية ====================
const MOTIVATIONAL_MESSAGES = {
  employee: {
    ar: [
      "أنت جزء مهم من نجاحنا، استمر في التميز!",
      "كل يوم فرصة جديدة للإنجاز، اغتنمها!",
      "عملك يصنع الفرق، شكراً لجهودك!",
      "التميز عادة، وأنت تثبتها كل يوم!",
    ],
    en: [
      "You are an important part of our success!",
      "Every day is a new opportunity to achieve!",
      "Your work makes a difference, thank you!",
      "Excellence is a habit, and you prove it daily!",
    ]
  },
  supervisor: {
    ar: [
      "قيادتك تُلهم فريقك، شكراً لإشرافك المتميز!",
      "المشرف الناجح يصنع فرقاً ناجحاً!",
      "حكمتك في التوجيه تُحدث فارقاً حقيقياً!",
    ],
    en: [
      "Your leadership inspires your team!",
      "A successful supervisor creates a successful team!",
      "Your wisdom in guidance makes a real difference!",
    ]
  },
  manager: {
    ar: [
      "بفضل قيادتكم الحكيمة، نتقدم نحو النجاح!",
      "رؤيتكم الثاقبة تُشكّل مستقبلنا المشرق!",
      "شكراً لإلهامكم المستمر وتوجيهاتكم الحكيمة!",
    ],
    en: [
      "With your wise leadership, we advance towards success!",
      "Your insightful vision shapes our bright future!",
      "Thank you for your continuous inspiration!",
    ]
  }
};

const getDailyMessage = (role, lang) => {
  let category = 'employee';
  if (['sultan', 'naif', 'stas', 'mohammed', 'salah'].includes(role)) category = 'manager';
  else if (role === 'supervisor') category = 'supervisor';
  const messages = MOTIVATIONAL_MESSAGES[category]?.[lang] || MOTIVATIONAL_MESSAGES.employee[lang];
  const dayOfYear = Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
  return messages[dayOfYear % messages.length];
};

const getGreeting = (lang) => {
  const hour = new Date().getHours();
  if (hour < 12) return lang === 'ar' ? 'صباح الخير' : 'Good morning';
  return lang === 'ar' ? 'مساء الخير' : 'Good evening';
};

const getStatusColor = (status) => {
  switch (status) {
    case 'present': return 'navy';
    case 'late': return 'lavender';
    case 'absent': return 'destructive';
    case 'leave': return 'success';
    case 'holiday': return 'success';
    case 'weekend': return 'success';
    case 'mission': return 'info';
    case 'not_checked_in': return 'warning';
    default: return 'slate';
  }
};

const STAT_CONFIG = {
  employee: [
    { key: 'leave_balance', icon: CalendarDays, label: 'dashboard.leaveBalance' },
    { key: 'pending_transactions', icon: FileText, label: 'dashboard.pendingApprovals' },
  ],
  supervisor: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals' },
    { key: 'team_size', icon: Users, label: 'dashboard.teamSize' },
  ],
  sultan: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
  naif: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
  salah: [
    { key: 'pending_approvals', icon: DollarSign, label: 'dashboard.pendingFinance' },
    { key: 'total_finance_entries', icon: FileText, label: 'dashboard.totalTransactions' },
  ],
  mohammed: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
  stas: [
    { key: 'pending_execution', icon: Shield, label: 'dashboard.pendingExecution' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
  ],
};

const QUICK_ACTIONS = {
  employee: [
    { key: 'leave', icon: CalendarDays, path: '/leave' },
    { key: 'attendance', icon: Clock, path: '/attendance' },
    { key: 'transactions', icon: FileText, path: '/transactions' },
  ],
  supervisor: [
    { key: 'transactions', icon: FileText, path: '/transactions' },
    { key: 'leave', icon: CalendarDays, path: '/leave' },
    { key: 'attendance', icon: Clock, path: '/attendance' },
  ],
  sultan: [
    { key: 'transactions', icon: FileText, path: '/transactions' },
    { key: 'employees', icon: Users, path: '/employees' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody' },
    { key: 'maintenanceTracking', icon: Briefcase, path: '/maintenance-tracking' },
  ],
  naif: [
    { key: 'transactions', icon: FileText, path: '/transactions' },
    { key: 'employees', icon: Users, path: '/employees' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody' },
    { key: 'maintenanceTracking', icon: Briefcase, path: '/maintenance-tracking' },
  ],
  salah: [
    { key: 'transactions', icon: FileText, path: '/transactions' },
    { key: 'finance', icon: DollarSign, path: '/finance' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody' },
  ],
  mohammed: [
    { key: 'transactions', icon: FileText, path: '/transactions' },
    { key: 'financialCustody', icon: Wallet, path: '/financial-custody' },
  ],
  stas: [
    { key: 'stasMirror', icon: Shield, path: '/stas-mirror' },
    { key: 'transactions', icon: FileText, path: '/transactions' },
    { key: 'employees', icon: Users, path: '/employees' },
    { key: 'maintenanceTracking', icon: Briefcase, path: '/maintenance-tracking' },
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
  const [showStatusDialog, setShowStatusDialog] = useState(false);

  const role = user?.role || 'employee';
  const isManager = ['stas', 'mohammed', 'salah', 'naif', 'sultan'].includes(role);
  // إظهار الحضور للجميع ما عدا salah و stas و mohammed
  const showsAttendance = !['salah', 'stas', 'mohammed'].includes(role);
  const isAdmin = ['sultan', 'naif', 'stas'].includes(role);
  
  const [employeeSummary, setEmployeeSummary] = useState(null);
  const [loadingEmployeeSummary, setLoadingEmployeeSummary] = useState(false);

  // Status configurations with glow colors
  const STATUS_CONFIG_GLOW = {
    present: { 
      color: 'bg-green-500', 
      glow: 'shadow-[0_0_15px_rgba(34,197,94,0.8)]',
      pulse: true,
      label_ar: 'حاضر',
      label_en: 'Present',
      icon: '✓',
      description_ar: 'تم تسجيل حضورك بنجاح',
      description_en: 'Your attendance has been recorded'
    },
    late: { 
      color: 'bg-yellow-500', 
      glow: 'shadow-[0_0_15px_rgba(234,179,8,0.8)]',
      pulse: true,
      label_ar: 'متأخر',
      label_en: 'Late',
      icon: '⚠',
      description_ar: 'تم تسجيل حضورك مع تأخير',
      description_en: 'Your attendance was recorded with delay'
    },
    absent: { 
      color: 'bg-red-500', 
      glow: 'shadow-[0_0_15px_rgba(239,68,68,0.8)]',
      pulse: true,
      label_ar: 'غائب',
      label_en: 'Absent',
      icon: '✗',
      description_ar: 'لم يتم تسجيل حضورك اليوم',
      description_en: 'Your attendance was not recorded today'
    },
    leave: { 
      color: 'bg-blue-500', 
      glow: 'shadow-[0_0_15px_rgba(59,130,246,0.8)]',
      pulse: false,
      label_ar: 'إجازة',
      label_en: 'On Leave',
      icon: '🏖',
      description_ar: 'أنت في إجازة معتمدة',
      description_en: 'You are on approved leave'
    },
    holiday: { 
      color: 'bg-emerald-500', 
      glow: 'shadow-[0_0_15px_rgba(16,185,129,0.8)]',
      pulse: false,
      label_ar: 'عطلة رسمية',
      label_en: 'Holiday',
      icon: '🎉',
      description_ar: 'اليوم عطلة رسمية',
      description_en: 'Today is an official holiday'
    },
    weekend: { 
      color: 'bg-emerald-400', 
      glow: 'shadow-[0_0_15px_rgba(52,211,153,0.8)]',
      pulse: false,
      label_ar: 'عطلة أسبوعية',
      label_en: 'Weekend',
      icon: '📅',
      description_ar: 'اليوم عطلة نهاية الأسبوع',
      description_en: 'Today is a weekend day'
    },
    mission: { 
      color: 'bg-purple-500', 
      glow: 'shadow-[0_0_15px_rgba(168,85,247,0.8)]',
      pulse: false,
      label_ar: 'في مهمة',
      label_en: 'On Mission',
      icon: '🚀',
      description_ar: 'أنت في مهمة عمل خارجية',
      description_en: 'You are on an external work mission'
    },
    not_checked_in: { 
      color: 'bg-amber-500', 
      glow: 'shadow-[0_0_15px_rgba(245,158,11,0.8)]',
      pulse: true,
      label_ar: 'لم يسجل بعد',
      label_en: 'Not Checked In',
      icon: '⏳',
      description_ar: 'لم تسجل حضورك بعد، يرجى تسجيل البصمة',
      description_en: 'You have not checked in yet, please record attendance'
    },
    unknown: { 
      color: 'bg-slate-400', 
      glow: 'shadow-[0_0_10px_rgba(148,163,184,0.5)]',
      pulse: false,
      label_ar: 'غير محدد',
      label_en: 'Unknown',
      icon: '?',
      description_ar: 'حالة الحضور غير محددة',
      description_en: 'Attendance status is unknown'
    }
  };

  const getStatusConfig = (status) => {
    return STATUS_CONFIG_GLOW[status] || STATUS_CONFIG_GLOW.unknown;
  };

  useEffect(() => {
    api.get('/api/dashboard/stats').then(r => setStats(r.data)).catch(() => {});
    api.get('/api/transactions').then(r => setRecentTxs(r.data.slice(0, 5))).catch(() => {});
    api.get('/api/dashboard/next-holiday').then(r => setNextHoliday(r.data)).catch(() => {});
    api.get('/api/announcements').then(r => setAnnouncements(r.data)).catch(() => {});
    api.get('/api/health').then(r => setAppVersion(r.data.version)).catch(() => {});
    
    if (isAdmin) {
      api.get('/api/notifications/expiring-contracts?days_ahead=90')
        .then(r => setExpiringContracts(r.data))
        .catch(() => {});
    }
    
    if (user?.employee_id) {
      setLoadingEmployeeSummary(true);
      api.get(`/api/employees/${user.employee_id}/summary`)
        .then(r => setEmployeeSummary(r.data))
        .catch(() => {})
        .finally(() => setLoadingEmployeeSummary(false));
    }
  }, [isAdmin, user?.employee_id]);

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
  const dailyMessage = getDailyMessage(role, lang);
  const statusColor = showsAttendance ? getStatusColor(employeeSummary?.attendance?.today_status) : 'blue';

  const getStatusStyle = (status) => STATUS_COLORS[status] || STATUS_COLORS.pending_ops;
  const getTranslatedType = (type) => t(`txTypes.${type}`) || type?.replace(/_/g, ' ');
  const getTranslatedStage = (stage) => {
    if (stage === 'stas') return lang === 'ar' ? 'ستاس' : 'STAS';
    return t(`stages.${stage}`) || stage;
  };

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      
      {/* ==================== البطاقة الرئيسية - أفقية ==================== */}
      <div className="relative" data-testid="main-card">
        {/* الشريط المتموج حول الإطار - ألوان الشركة */}
        <div className={`absolute -inset-[2px] rounded-2xl bg-gradient-to-r 
          ${statusColor === 'navy' ? 'from-[hsl(var(--navy))] via-[hsl(222,47%,30%)] to-[hsl(var(--navy))]' : ''}
          ${statusColor === 'lavender' ? 'from-[hsl(var(--lavender))] via-[hsl(262,83%,70%)] to-[hsl(var(--lavender))]' : ''}
          ${statusColor === 'slate' ? 'from-slate-400 via-slate-500 to-slate-400' : ''}
          animate-border-flow`} 
        />
        
        {/* البطاقة - ألوان الشركة */}
        <div className={`relative overflow-hidden rounded-2xl ${
          isManager 
            ? 'bg-gradient-to-br from-[hsl(var(--charcoal))] via-slate-900 to-[hsl(var(--charcoal))] text-white' 
            : 'bg-gradient-to-br from-[hsl(var(--navy))] via-[hsl(222,47%,28%)] to-[hsl(var(--navy))] text-white'
        }`}>
          
          <div className="relative p-5">
            {/* التخطيط الأفقي: ثلث + ثلثين */}
            <div className="flex gap-5">
              
              {/* الثلث الأول: الصورة */}
              <div className="flex-shrink-0 w-1/3 max-w-[120px]">
                <div className="relative">
                  {(employeeSummary?.employee?.photo_url || user?.photo_url) ? (
                    <img 
                      src={employeeSummary?.employee?.photo_url || user?.photo_url}
                      alt={displayName}
                      className="w-full aspect-square rounded-xl object-cover"
                    />
                  ) : (
                    <div className={`w-full aspect-square rounded-xl flex items-center justify-center text-4xl font-bold ${
                      isManager ? 'bg-[hsl(var(--navy))]' : 'bg-slate-700/50'
                    }`}>
                      {displayName?.[0] || 'U'}
                    </div>
                  )}
                  
                  {/* نقطة الحالة المضيئة - قابلة للنقر */}
                  {showsAttendance && (
                    <button
                      onClick={() => setShowStatusDialog(true)}
                      className="absolute -bottom-2 -end-2 group cursor-pointer"
                      data-testid="attendance-status-indicator"
                    >
                      {/* النقطة المضيئة */}
                      <span className={`
                        block w-6 h-6 rounded-full border-2
                        ${isManager ? 'border-[hsl(var(--charcoal))]' : 'border-[hsl(var(--navy))]'}
                        ${getStatusConfig(employeeSummary?.attendance?.today_status).color}
                        ${getStatusConfig(employeeSummary?.attendance?.today_status).glow}
                        ${getStatusConfig(employeeSummary?.attendance?.today_status).pulse ? 'animate-pulse' : ''}
                        transition-all duration-300 group-hover:scale-125
                      `} />
                      {/* نص الحالة المختصر */}
                      <span className={`
                        absolute -bottom-5 start-1/2 -translate-x-1/2 whitespace-nowrap
                        text-[10px] font-bold px-1.5 py-0.5 rounded
                        ${getStatusConfig(employeeSummary?.attendance?.today_status).color}
                        text-white shadow-lg
                      `}>
                        {lang === 'ar' 
                          ? getStatusConfig(employeeSummary?.attendance?.today_status).label_ar 
                          : getStatusConfig(employeeSummary?.attendance?.today_status).label_en}
                      </span>
                    </button>
                  )}
                </div>
                
                {/* سنوات الخبرة تحت الصورة */}
                {showsAttendance && employeeSummary?.service_info?.years_display && (
                  <div className={`mt-3 text-center py-2 rounded-lg ${
                    isManager ? 'bg-slate-800/50' : 'bg-white/10'
                  }`}>
                    <p className="text-lg font-bold">{employeeSummary.service_info.years_display}</p>
                    <p className="text-[9px] opacity-60 uppercase">{lang === 'ar' ? 'سنة خبرة' : 'years'}</p>
                  </div>
                )}
              </div>
              
              {/* الثلثين: المحتوى */}
              <div className="flex-1 min-w-0">
                {/* الاسم والدور */}
                <div className="mb-3">
                  <h2 className="text-xl font-bold truncate">{displayName}</h2>
                  <p className={`text-sm ${isManager ? 'text-[hsl(var(--lavender)/0.8)]' : 'text-white/70'}`}>
                    {t(`roles.${role}`)}
                  </p>
                </div>
                
                {/* الرسالة التحفيزية */}
                <div className={`mb-4 p-3 rounded-lg ${isManager ? 'bg-[hsl(var(--navy)/0.3)]' : 'bg-white/10'}`}>
                  <div className="flex items-start gap-2">
                    <Sparkles size={14} className="text-[hsl(var(--lavender))] mt-0.5" />
                    <p className="text-xs leading-relaxed opacity-90">{dailyMessage}</p>
                  </div>
                </div>
                
                {/* الإحصائيات - ألوان الشركة */}
                {showsAttendance ? (
                  <div className="grid grid-cols-3 gap-2">
                    <div className={`text-center p-2 rounded-lg cursor-pointer ${isManager ? 'bg-[hsl(var(--navy)/0.3)]' : 'bg-white/10'}`}
                         onClick={() => navigate('/leave')}>
                      <CalendarDays size={16} className="mx-auto mb-1 text-[hsl(var(--lavender))]" />
                      <p className="text-lg font-bold">{employeeSummary?.leave_details?.balance || 0}</p>
                      <p className="text-[9px] opacity-60">{lang === 'ar' ? 'إجازة' : 'Leave'}</p>
                    </div>
                    <div className={`text-center p-2 rounded-lg cursor-pointer ${isManager ? 'bg-[hsl(var(--navy)/0.3)]' : 'bg-white/10'}`}
                         onClick={() => navigate('/attendance')}>
                      <Clock size={16} className="mx-auto mb-1 text-white/80" />
                      <p className="text-sm font-bold">{employeeSummary?.attendance?.check_in_time || '--:--'}</p>
                      <p className="text-[9px] opacity-60">{lang === 'ar' ? 'حضور' : 'In'}</p>
                    </div>
                    <div className={`text-center p-2 rounded-lg ${isManager ? 'bg-[hsl(var(--navy)/0.3)]' : 'bg-white/10'}`}>
                      <Timer size={16} className="mx-auto mb-1 text-[hsl(var(--lavender)/0.8)]" />
                      <p className="text-lg font-bold">{employeeSummary?.attendance?.monthly_hours || 0}</p>
                      <p className="text-[9px] opacity-60">{lang === 'ar' ? 'ساعات' : 'Hrs'}</p>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {statCards.map(sc => {
                      const Icon = sc.icon;
                      return (
                        <div key={sc.key} className="text-center p-2 bg-[hsl(var(--navy)/0.3)] rounded-lg">
                          <Icon size={16} className="mx-auto mb-1 text-[hsl(var(--lavender))]" />
                          <p className="text-lg font-bold">{stats[sc.key] ?? 0}</p>
                          <p className="text-[9px] opacity-60">{t(sc.label)}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
            
            {/* أشرطة التقدم (للجميع الذين لديهم حضور) */}
            {showsAttendance && (
              <div className="mt-4 space-y-3">
                {/* شريط ساعات الشهر */}
                <div>
                  <div className="flex justify-between text-[10px] mb-1 opacity-70">
                    <span>{lang === 'ar' ? 'ساعات الشهر' : 'Monthly Hours'}</span>
                    <span className="font-medium">
                      {employeeSummary?.attendance?.monthly_hours || 0}/
                      {employeeSummary?.attendance?.required_monthly_hours || (employeeSummary?.attendance?.is_ramadan_active ? 144 : 194)}
                      {employeeSummary?.attendance?.is_ramadan_active && ' 🌙'}
                    </span>
                  </div>
                  <Progress 
                    value={Math.min(100, ((employeeSummary?.attendance?.monthly_hours || 0) / (employeeSummary?.attendance?.required_monthly_hours || 194)) * 100)} 
                    className="h-2 bg-white/10"
                  />
                  {/* عرض العجز إن وجد */}
                  {(employeeSummary?.attendance?.deficit_hours || 0) > 0 && (
                    <div className="flex justify-between text-[9px] mt-1 text-amber-300">
                      <span className="flex items-center gap-1">
                        <TrendingDown size={10} />
                        {lang === 'ar' ? 'عجز الساعات' : 'Deficit'}
                      </span>
                      <span>{employeeSummary?.attendance?.deficit_hours} {lang === 'ar' ? 'ساعة' : 'hrs'}</span>
                    </div>
                  )}
                </div>
                
                {/* شريط رصيد الخروج المبكر - يعكس المستهلك */}
                <div>
                  <div className="flex justify-between text-[10px] mb-1 opacity-70">
                    <span>{lang === 'ar' ? 'الاستئذان المستهلك' : 'Permission Used'}</span>
                    <span className="font-medium">
                      {employeeSummary?.early_leave_balance?.used_hours || 0}/
                      {employeeSummary?.early_leave_balance?.monthly_allowance || 2}
                      {lang === 'ar' ? ' س' : ' hrs'}
                    </span>
                  </div>
                  <Progress 
                    value={((employeeSummary?.early_leave_balance?.used_hours || 0) / (employeeSummary?.early_leave_balance?.monthly_allowance || 2)) * 100} 
                    className="h-1.5 bg-white/10"
                  />
                </div>
              </div>
            )}
            
            {/* إشعارات ستاس المثبتة */}
            {announcements.pinned?.length > 0 && (
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <Bell size={12} className={isManager ? 'text-[hsl(var(--warning))]' : 'text-[hsl(var(--warning)/0.6)]'} />
                  <span className="text-[10px] font-medium opacity-70 uppercase">
                    {lang === 'ar' ? 'إشعارات' : 'Notices'}
                  </span>
                </div>
                {announcements.pinned.slice(0, 2).map(ann => (
                  <div key={ann.id} className={`flex items-start gap-2 p-2 rounded-lg mb-1 ${
                    isManager ? 'bg-slate-800/50' : 'bg-white/10'
                  }`}>
                    <Pin size={10} className={isManager ? 'text-[hsl(var(--warning))] mt-1' : 'text-[hsl(var(--warning)/0.6)] mt-1'} />
                    <p className="text-xs opacity-90 leading-relaxed">
                      {lang === 'ar' ? ann.message_ar : ann.message_en}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Regular Announcements */}
      {announcements.regular?.length > 0 && (
        <div className="space-y-2">
          {announcements.regular.map(ann => (
            <div key={ann.id} className="flex items-start justify-between p-3 bg-[hsl(var(--info)/0.1)] border border-[hsl(var(--info)/0.2)] rounded-xl dark:bg-[hsl(var(--info)/0.15)]">
              <div className="flex items-start gap-2">
                <Bell size={14} className="text-[hsl(var(--info))] mt-0.5" />
                <p className="text-sm text-foreground">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => dismissAnnouncement(ann.id)} className="text-[hsl(var(--info))] p-1 h-auto">
                <X size={14} />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Expiring Contracts */}
      {isAdmin && expiringContracts.employees?.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell size={16} className="text-[hsl(var(--warning))]" />
              <h2 className="font-semibold">{lang === 'ar' ? 'عقود قاربت على الانتهاء' : 'Expiring Contracts'}</h2>
              <span className="text-xs bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] px-2 py-0.5 rounded-full">
                {expiringContracts.summary.total}
              </span>
            </div>
            <button onClick={() => navigate('/contracts-management')} className="text-sm text-primary flex items-center gap-1">
              {lang === 'ar' ? 'الكل' : 'All'} <ChevronRight size={14} className="rtl:rotate-180" />
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {expiringContracts.employees.slice(0, 3).map(emp => (
              <div key={emp.employee_id} className={`p-3 rounded-xl border ${
                emp.urgency === 'critical' ? 'border-destructive/30 bg-destructive/10' : 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)]'
              }`}>
                <p className="font-medium text-sm truncate">{lang === 'ar' ? emp.employee_name_ar : emp.employee_name}</p>
                <p className="text-xs text-muted-foreground">{emp.days_remaining} {lang === 'ar' ? 'يوم' : 'days'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions - Company Colors */}
      <div>
        <h2 className="font-semibold mb-3">{lang === 'ar' ? 'الخدمات' : 'Services'}</h2>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {quickActions.map(action => {
            const Icon = action.icon;
            return (
              <button 
                key={action.key} 
                onClick={() => navigate(action.path)} 
                className="flex flex-col items-center gap-2 p-3 rounded-xl bg-card border border-border hover:border-[hsl(var(--lavender)/0.4)] hover:bg-[hsl(var(--lavender)/0.05)] active:scale-[0.98] transition-all"
              >
                <div className="w-10 h-10 rounded-xl bg-[hsl(var(--navy)/0.08)] flex items-center justify-center">
                  <Icon size={20} className="text-[hsl(var(--navy))]" />
                </div>
                <span className="text-[10px] font-medium text-center leading-tight text-muted-foreground">{t(`nav.${action.key}`)}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Next Holiday */}
      {nextHoliday && (
        <div className={`card-premium p-3 flex items-center gap-3 ${
          nextHoliday.relative === 'today' ? 'border-2 border-green-400 bg-green-50/50' : ''
        }`}>
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            nextHoliday.relative === 'today' || nextHoliday.relative === 'tomorrow'
              ? 'bg-green-100'
              : 'bg-warning/10'
          }`}>
            <CalendarDays size={18} className={
              nextHoliday.relative === 'today' || nextHoliday.relative === 'tomorrow'
                ? 'text-green-600'
                : 'text-[hsl(var(--warning))]'
            } />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-[10px] text-muted-foreground">{t('dashboard.nextHoliday')}</p>
              {nextHoliday.relative === 'today' && (
                <span className="text-[10px] font-bold text-green-600 bg-green-100 px-1.5 py-0.5 rounded">
                  {lang === 'ar' ? 'اليوم' : 'Today'}
                </span>
              )}
              {nextHoliday.relative === 'tomorrow' && (
                <span className="text-[10px] font-bold text-green-600 bg-green-100 px-1.5 py-0.5 rounded">
                  {lang === 'ar' ? 'غداً' : 'Tomorrow'}
                </span>
              )}
            </div>
            <p className={`text-sm font-medium truncate ${
              nextHoliday.relative === 'today' || nextHoliday.relative === 'tomorrow'
                ? 'text-green-700'
                : ''
            }`}>
              {lang === 'ar' ? nextHoliday.name_ar : nextHoliday.name}
            </p>
            <p className="text-[10px] text-muted-foreground">
              <span className="text-foreground">{nextHoliday.date}</span>
              {nextHoliday.hijri_date && (
                <span className="mx-1">•</span>
              )}
              {nextHoliday.hijri_date && (
                <span>{nextHoliday.hijri_date}</span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">{t('dashboard.recentTransactions')}</h2>
          <button onClick={() => navigate('/transactions')} className="text-sm text-primary flex items-center gap-1">
            {lang === 'ar' ? 'الكل' : 'All'} <ChevronRight size={14} className="rtl:rotate-180" />
          </button>
        </div>
        
        <div className="space-y-2">
          {recentTxs.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground bg-muted/30 rounded-xl">
              <FileText size={24} className="mx-auto mb-1 opacity-50" />
              <p className="text-sm">{t('transactions.noTransactions')}</p>
            </div>
          ) : (
            recentTxs.map(tx => {
              const statusStyle = getStatusStyle(tx.status);
              return (
                <button
                  key={tx.id}
                  onClick={() => navigate(`/transactions/${tx.id}`)}
                  className="w-full card-premium p-3 flex items-center gap-3 text-start hover:bg-muted/30 transition-colors"
                >
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: statusStyle.bg }}>
                    <FileText size={16} style={{ color: statusStyle.text }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{getTranslatedType(tx.type)}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {lang === 'ar' ? tx.data?.employee_name_ar : tx.data?.employee_name}
                    </p>
                  </div>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full" style={{ background: statusStyle.bg, color: statusStyle.text }}>
                    {t(`status.${tx.status}`)}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Version */}
      {appVersion && (
        <div className="text-center text-[10px] text-muted-foreground pt-3 border-t">
          v{appVersion}
        </div>
      )}

      {/* نافذة تفاصيل حالة الحضور */}
      <Dialog open={showStatusDialog} onOpenChange={setShowStatusDialog}>
        <DialogContent className="max-w-sm" data-testid="attendance-status-dialog">
          <DialogHeader>
            <DialogTitle className="text-center">
              {lang === 'ar' ? 'حالة الحضور' : 'Attendance Status'}
            </DialogTitle>
          </DialogHeader>
          
          {employeeSummary?.attendance && (
            <div className="space-y-4">
              {/* الأيقونة الكبيرة */}
              <div className="flex justify-center">
                <div className={`
                  w-20 h-20 rounded-full flex items-center justify-center text-4xl
                  ${getStatusConfig(employeeSummary?.attendance?.today_status).color}
                  ${getStatusConfig(employeeSummary?.attendance?.today_status).glow}
                  ${getStatusConfig(employeeSummary?.attendance?.today_status).pulse ? 'animate-pulse' : ''}
                `}>
                  {getStatusConfig(employeeSummary?.attendance?.today_status).icon}
                </div>
              </div>
              
              {/* الحالة */}
              <div className="text-center">
                <h3 className="text-2xl font-bold">
                  {lang === 'ar' 
                    ? getStatusConfig(employeeSummary?.attendance?.today_status).label_ar 
                    : getStatusConfig(employeeSummary?.attendance?.today_status).label_en}
                </h3>
                <p className="text-muted-foreground text-sm mt-1">
                  {lang === 'ar' 
                    ? getStatusConfig(employeeSummary?.attendance?.today_status).description_ar 
                    : getStatusConfig(employeeSummary?.attendance?.today_status).description_en}
                </p>
              </div>
              
              {/* التفاصيل */}
              <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{lang === 'ar' ? 'وقت الدخول' : 'Check In'}</span>
                  <span className="font-medium">{employeeSummary?.attendance?.check_in_time || '--:--'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{lang === 'ar' ? 'وقت الخروج' : 'Check Out'}</span>
                  <span className="font-medium">{employeeSummary?.attendance?.check_out_time || '--:--'}</span>
                </div>
                {employeeSummary?.attendance?.late_minutes > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{lang === 'ar' ? 'دقائق التأخير' : 'Late Minutes'}</span>
                    <span className="font-medium text-amber-600">{employeeSummary?.attendance?.late_minutes} {lang === 'ar' ? 'دقيقة' : 'min'}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{lang === 'ar' ? 'ساعات الشهر' : 'Monthly Hours'}</span>
                  <span className="font-medium">{employeeSummary?.attendance?.monthly_hours || 0} / {employeeSummary?.attendance?.required_monthly_hours || 194}</span>
                </div>
                {employeeSummary?.attendance?.deficit_hours > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{lang === 'ar' ? 'عجز الساعات' : 'Deficit'}</span>
                    <span className="font-medium text-red-600">{employeeSummary?.attendance?.deficit_hours} {lang === 'ar' ? 'ساعة' : 'hrs'}</span>
                  </div>
                )}
              </div>
              
              {/* الاستئذان المستهلك */}
              <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-purple-700 dark:text-purple-300 font-medium">
                    {lang === 'ar' ? 'الاستئذان المستهلك' : 'Permission Used'}
                  </span>
                  <span className="font-bold text-purple-700 dark:text-purple-300">
                    {employeeSummary?.early_leave_balance?.used_hours || 0} / {employeeSummary?.early_leave_balance?.monthly_allowance || 2} {lang === 'ar' ? 'ساعات' : 'hrs'}
                  </span>
                </div>
                <Progress 
                  value={((employeeSummary?.early_leave_balance?.used_hours || 0) / (employeeSummary?.early_leave_balance?.monthly_allowance || 2)) * 100} 
                  className="h-2"
                />
                {(employeeSummary?.early_leave_balance?.remaining_hours || 0) > 0 && (
                  <p className="text-xs text-purple-600 dark:text-purple-400 mt-2">
                    {lang === 'ar' ? `متبقي: ${employeeSummary?.early_leave_balance?.remaining_hours} ساعات` : `Remaining: ${employeeSummary?.early_leave_balance?.remaining_hours} hrs`}
                  </p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
