import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, CalendarDays, Users, Shield, DollarSign, Clock, ChevronRight, 
  Briefcase, UserCheck, MapPin, Wallet, Settings2, Bell, Pin, X, Award, 
  CheckCircle2, AlertTriangle as AlertTriangleIcon, Timer, TrendingDown,
  AlertCircle, Sparkles, ArrowUpRight, Calendar, Crown, Star
} from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import api from '@/lib/api';

// ==================== رسائل تحفيزية يومية ====================
const MOTIVATIONAL_MESSAGES = {
  employee: {
    ar: [
      "أنت جزء مهم من نجاحنا، استمر في التميز!",
      "كل يوم فرصة جديدة للإنجاز، اغتنمها!",
      "عملك يصنع الفرق، شكراً لجهودك!",
      "التميز ليس هدفاً بل عادة، وأنت تثبتها كل يوم!",
      "الإيجابية تبدأ منك، وأنت مصدر إلهام للفريق!",
      "النجاح يأتي لمن يسعى إليه، وأنت على الطريق الصحيح!",
      "كن فخوراً بما تنجزه، فأنت تصنع قيمة حقيقية!",
      "الشغف بالعمل هو سر التميز، واصل شغفك!",
    ],
    en: [
      "You are an important part of our success, keep excelling!",
      "Every day is a new opportunity to achieve, seize it!",
      "Your work makes a difference, thank you for your efforts!",
      "Excellence is not a goal but a habit, and you prove it daily!",
      "Positivity starts with you, and you inspire the team!",
      "Success comes to those who pursue it, and you're on the right path!",
      "Be proud of what you accomplish, you create real value!",
      "Passion for work is the secret to excellence, keep your passion!",
    ]
  },
  supervisor: {
    ar: [
      "قيادتك تُلهم الفريق، شكراً لإدارتك المتميزة!",
      "المشرف الناجح يصنع فرقاً ناجحاً، وأنت مثال حي!",
      "حكمتك في الإدارة تُحدث فارقاً حقيقياً!",
      "أنت ركيزة الفريق، واصل دعمك المميز!",
    ],
    en: [
      "Your leadership inspires the team, thank you for your management!",
      "A successful supervisor creates a successful team, you're a living example!",
      "Your wisdom in management makes a real difference!",
      "You are the team's pillar, continue your distinguished support!",
    ]
  },
  admin: {
    ar: [
      "بفضل قيادتكم الحكيمة، نتقدم نحو النجاح!",
      "رؤيتكم الثاقبة تُشكّل مستقبلنا المشرق!",
      "شكراً لإلهامكم المستمر وتوجيهاتكم الحكيمة!",
      "أنتم القدوة في التميز والإبداع!",
    ],
    en: [
      "With your wise leadership, we advance towards success!",
      "Your insightful vision shapes our bright future!",
      "Thank you for your continuous inspiration and wise guidance!",
      "You are the role model in excellence and creativity!",
    ]
  }
};

// الحصول على رسالة اليوم
const getDailyMessage = (category, lang) => {
  const messages = MOTIVATIONAL_MESSAGES[category]?.[lang] || MOTIVATIONAL_MESSAGES.employee[lang];
  const dayOfYear = Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
  return messages[dayOfYear % messages.length];
};

// ==================== التحية حسب الوقت ====================
const getGreeting = (lang) => {
  const hour = new Date().getHours();
  if (hour < 12) return lang === 'ar' ? 'صباح الخير' : 'Good morning';
  if (hour < 17) return lang === 'ar' ? 'مساء الخير' : 'Good afternoon';
  return lang === 'ar' ? 'مساء الخير' : 'Good evening';
};

const STAT_CONFIG = {
  employee: [
    { key: 'leave_balance', icon: CalendarDays, label: 'dashboard.leaveBalance', suffix: 'dashboard.days', gradient: true },
    { key: 'pending_transactions', icon: FileText, label: 'dashboard.pendingApprovals' },
  ],
  supervisor: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', gradient: true },
    { key: 'team_size', icon: Users, label: 'dashboard.teamSize' },
    { key: 'leave_balance', icon: CalendarDays, label: 'dashboard.leaveBalance', suffix: 'dashboard.days' },
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

// ==================== مكون صورة مع شريط الحالة الدوار ====================
const StatusRingAvatar = ({ photoUrl, name, status, isAdmin }) => {
  // تحديد لون الشريط
  const getRingColor = () => {
    if (isAdmin) return 'from-blue-400 via-blue-500 to-blue-600'; // أزرق للإدارة
    switch (status) {
      case 'present': return 'from-emerald-400 via-emerald-500 to-emerald-600';
      case 'late': return 'from-amber-400 via-amber-500 to-amber-600';
      case 'absent': return 'from-red-400 via-red-500 to-red-600';
      default: return 'from-gray-400 via-gray-500 to-gray-600';
    }
  };

  return (
    <div className="relative">
      {/* الشريط الدوار */}
      <div className={`absolute -inset-1 bg-gradient-to-r ${getRingColor()} rounded-2xl animate-spin-slow opacity-75 blur-sm`} />
      <div className={`absolute -inset-1 bg-gradient-to-r ${getRingColor()} rounded-2xl animate-spin-slow`} />
      
      {/* الصورة */}
      <div className="relative">
        {photoUrl ? (
          <img 
            src={photoUrl}
            alt={name}
            className="w-20 h-20 rounded-2xl object-cover ring-2 ring-white/50"
          />
        ) : (
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-3xl font-bold text-white ring-2 ring-white/50">
            {name?.[0] || 'U'}
          </div>
        )}
      </div>
    </div>
  );
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
  // الإدارة العليا - ليسوا موظفين (ستاس، محمد، صلاح، نايف)
  const isExecutive = ['stas', 'mohammed', 'salah', 'naif'].includes(role);
  // سلطان يُعامل كموظف (له حضور)
  const isAdmin = ['sultan', 'naif', 'stas'].includes(role);
  // البطاقة تظهر لكل من لديه employee_id (موظفين + سلطان)
  const hasEmployeeCard = !!user?.employee_id && !isExecutive;
  
  const [employeeSummary, setEmployeeSummary] = useState(null);
  const [loadingEmployeeSummary, setLoadingEmployeeSummary] = useState(false);

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

  // تحديد فئة الرسالة
  const messageCategory = isExecutive ? 'admin' : (role === 'supervisor' ? 'supervisor' : 'employee');
  const dailyMessage = getDailyMessage(messageCategory, lang);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      
      {/* ==================== بطاقة الإدارة العليا (ستاس/محمد/صلاح/نايف) ==================== */}
      {isExecutive && (
        <div className="relative overflow-hidden rounded-2xl" data-testid="executive-card">
          {/* الخلفية الفضية الفخمة مع الأطراف الزرقاء المضيئة */}
          <div className="absolute inset-0 bg-gradient-to-br from-slate-100 via-slate-50 to-white dark:from-slate-900 dark:via-slate-800 dark:to-slate-900" />
          
          {/* الأطراف الزرقاء المضيئة */}
          <div className="absolute inset-0">
            <div className="absolute top-0 left-0 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl animate-pulse" />
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-400/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '0.5s' }} />
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-blue-600/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
            <div className="absolute bottom-0 right-0 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1.5s' }} />
          </div>
          
          {/* الإطار الذهبي/الفضي */}
          <div className="absolute inset-0 border-2 border-blue-300/30 dark:border-blue-500/20 rounded-2xl" />
          <div className="absolute inset-[2px] border border-slate-200/50 dark:border-slate-700/50 rounded-2xl" />
          
          <div className="relative p-6 md:p-8">
            {/* التاج والزخرفة */}
            <div className="flex justify-center mb-4">
              <div className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-blue-500/10 via-blue-400/20 to-blue-500/10 rounded-full border border-blue-300/30">
                <Crown size={16} className="text-blue-500" />
                <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
                  {t(`roles.${role}`)}
                </span>
                <Crown size={16} className="text-blue-500 transform scale-x-[-1]" />
              </div>
            </div>
            
            {/* الصورة مع الإضاءة الزرقاء */}
            <div className="flex justify-center mb-6">
              <StatusRingAvatar 
                photoUrl={user?.photo_url}
                name={displayName}
                isAdmin={true}
              />
            </div>
            
            {/* الاسم */}
            <div className="text-center mb-4">
              <h1 className="text-2xl md:text-3xl font-bold text-slate-800 dark:text-white mb-1">
                {displayName}
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {getGreeting(lang)}
              </p>
            </div>
            
            {/* الرسالة التحفيزية */}
            <div className="text-center mb-6 px-4">
              <div className="inline-flex items-start gap-2 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-xl border border-blue-100 dark:border-blue-800/30">
                <Sparkles size={18} className="text-blue-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {dailyMessage}
                </p>
              </div>
            </div>
            
            {/* الإحصائيات */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              {statCards.map(sc => {
                const Icon = sc.icon;
                return (
                  <div key={sc.key} className="text-center p-3 bg-white/50 dark:bg-slate-800/50 rounded-xl backdrop-blur-sm border border-slate-200/50 dark:border-slate-700/50">
                    <Icon size={20} className="mx-auto mb-2 text-blue-500" />
                    <p className="text-2xl font-bold text-slate-800 dark:text-white">{stats[sc.key] ?? 0}</p>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      {t(sc.label)}
                    </p>
                  </div>
                );
              })}
            </div>
            
            {/* إشعارات ستاس المثبتة */}
            {announcements.pinned.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <Bell size={14} className="text-blue-500" />
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    {lang === 'ar' ? 'إشعارات مهمة' : 'Important Notices'}
                  </span>
                </div>
                {announcements.pinned.map(ann => (
                  <div key={ann.id} className="flex items-start gap-2 p-3 bg-blue-50/50 dark:bg-blue-950/30 rounded-xl border border-blue-100 dark:border-blue-800/30">
                    <Pin size={14} className="text-blue-500 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-slate-700 dark:text-slate-300">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================== بطاقة الموظفين والمشرفين وسلطان ==================== */}
      {!isExecutive && (
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white" data-testid="employee-unified-card">
          {/* نمط الخلفية */}
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-300 rounded-full blur-3xl transform -translate-x-1/2 translate-y-1/2" />
          </div>
          
          <div className="relative p-6">
            {/* التحية والرسالة التحفيزية */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 rounded-full backdrop-blur-sm mb-2">
                <Sparkles size={14} className="text-amber-300" />
                <span className="text-xs text-white/90">
                  {getGreeting(lang)} {lang === 'ar' ? 'يا' : ''} {displayName?.split(' ')[0]}!
                </span>
              </div>
              <p className="text-sm text-white/80 max-w-md mx-auto leading-relaxed">
                {dailyMessage}
              </p>
            </div>
            
            {/* الصف الرئيسي - الصورة والبيانات */}
            <div className="flex items-start gap-4 mb-6">
              {/* الصورة مع شريط الحالة */}
              <StatusRingAvatar 
                photoUrl={employeeSummary?.employee?.photo_url || user?.photo_url}
                name={displayName}
                status={employeeSummary?.attendance?.today_status || 'unknown'}
                isAdmin={false}
              />
              
              {/* البيانات */}
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold truncate">{displayName}</h3>
                <p className="text-sm text-white/70 truncate">
                  {lang === 'ar' ? employeeSummary?.contract?.job_title_ar : employeeSummary?.contract?.job_title}
                </p>
                <p className="text-xs text-white/50">
                  {lang === 'ar' ? employeeSummary?.contract?.department_ar : employeeSummary?.contract?.department}
                </p>
                
                {/* حالة اليوم */}
                <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" style={{
                  background: employeeSummary?.attendance?.today_status === 'present' ? '#10B98130' :
                              employeeSummary?.attendance?.today_status === 'late' ? '#F5940030' :
                              employeeSummary?.attendance?.today_status === 'absent' ? '#EF444430' : '#64748B30'
                }}>
                  {employeeSummary?.attendance?.today_status === 'present' && <CheckCircle2 size={12} />}
                  {employeeSummary?.attendance?.today_status === 'late' && <Clock size={12} />}
                  {employeeSummary?.attendance?.today_status === 'absent' && <X size={12} />}
                  <span>
                    {employeeSummary?.attendance?.today_status === 'present' ? (lang === 'ar' ? 'حاضر' : 'Present') :
                     employeeSummary?.attendance?.today_status === 'late' ? (lang === 'ar' ? 'متأخر' : 'Late') :
                     employeeSummary?.attendance?.today_status === 'absent' ? (lang === 'ar' ? 'غائب' : 'Absent') :
                     (lang === 'ar' ? 'لم يُسجل بعد' : 'Not yet')}
                  </span>
                </div>
              </div>
              
              {/* سنوات الخبرة */}
              <div className="text-center px-3 py-2 bg-white/10 rounded-xl backdrop-blur-sm">
                <Award size={20} className="mx-auto text-amber-400 mb-1" />
                <p className="text-lg font-bold">{employeeSummary?.service_info?.years_display || '0'}</p>
                <p className="text-[9px] text-white/60 uppercase tracking-wider">
                  {lang === 'ar' ? 'سنوات' : 'Years'}
                </p>
              </div>
            </div>
            
            {/* الإحصائيات السريعة */}
            <div className="grid grid-cols-4 gap-3 mb-4">
              <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm hover:bg-white/20 transition-colors cursor-pointer"
                   onClick={() => navigate('/leave')}>
                <CalendarDays size={18} className="mx-auto mb-1 text-blue-300" />
                <p className="text-xl font-bold">{employeeSummary?.leave_details?.balance || stats.leave_balance || 0}</p>
                <p className="text-[9px] text-white/60 uppercase tracking-wider">
                  {lang === 'ar' ? 'رصيد الإجازة' : 'Leave'}
                </p>
              </div>
              
              <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm hover:bg-white/20 transition-colors cursor-pointer"
                   onClick={() => navigate('/attendance')}>
                <Clock size={18} className="mx-auto mb-1 text-emerald-300" />
                <p className="text-sm font-bold">
                  {employeeSummary?.attendance?.check_in_time || '--:--'}
                </p>
                <p className="text-[9px] text-white/60 uppercase tracking-wider">
                  {lang === 'ar' ? 'وقت الحضور' : 'Check-in'}
                </p>
              </div>
              
              <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm">
                <Timer size={18} className="mx-auto mb-1 text-purple-300" />
                <p className="text-xl font-bold">{employeeSummary?.attendance?.monthly_hours || 0}</p>
                <p className="text-[9px] text-white/60 uppercase tracking-wider">
                  {lang === 'ar' ? 'ساعات الشهر' : 'Hours'}
                </p>
              </div>
              
              <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm hover:bg-white/20 transition-colors cursor-pointer"
                   onClick={() => navigate('/transactions')}>
                <FileText size={18} className="mx-auto mb-1 text-orange-300" />
                <p className="text-xl font-bold">{employeeSummary?.pending_transactions || stats.pending_transactions || 0}</p>
                <p className="text-[9px] text-white/60 uppercase tracking-wider">
                  {lang === 'ar' ? 'معاملات' : 'Pending'}
                </p>
              </div>
            </div>
            
            {/* أشرطة التقدم */}
            <div className="space-y-3 p-4 bg-white/5 rounded-xl backdrop-blur-sm">
              {/* ساعات العمل الشهرية */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-white/70 flex items-center gap-1.5">
                    <Timer size={12} className="text-emerald-400" />
                    {lang === 'ar' ? 'ساعات العمل الشهرية' : 'Monthly Hours'}
                  </span>
                  <span className="text-xs font-mono text-white/90">
                    {employeeSummary?.attendance?.monthly_hours || 0} / {employeeSummary?.attendance?.required_monthly_hours || 176}
                  </span>
                </div>
                <Progress 
                  value={Math.min(100, ((employeeSummary?.attendance?.monthly_hours || 0) / (employeeSummary?.attendance?.required_monthly_hours || 176)) * 100)} 
                  className="h-2 bg-white/10"
                />
              </div>
              
              {/* ساعات النقص */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-white/70 flex items-center gap-1.5">
                    <TrendingDown size={12} className="text-amber-400" />
                    {lang === 'ar' ? 'ساعات النقص' : 'Deficit Hours'}
                  </span>
                  <span className="text-xs font-mono text-white/90">
                    {employeeSummary?.attendance?.deficit_hours || 0} / 8
                  </span>
                </div>
                <Progress 
                  value={Math.min(100, ((employeeSummary?.attendance?.deficit_hours || 0) / 8) * 100)} 
                  className={`h-2 ${(employeeSummary?.attendance?.deficit_hours || 0) >= 6 ? 'bg-red-500/30' : 'bg-white/10'}`}
                />
              </div>
            </div>
            
            {/* تاريخ انتهاء العقد */}
            {employeeSummary?.contract?.end_date && (
              <div className="mt-4 flex items-center justify-between text-sm p-3 bg-white/5 rounded-xl">
                <div className="flex items-center gap-2 text-white/70">
                  <Briefcase size={14} />
                  <span>{lang === 'ar' ? 'انتهاء العقد' : 'Contract ends'}</span>
                </div>
                <span className="font-medium text-white/90">{employeeSummary.contract.end_date}</span>
              </div>
            )}
            
            {/* الإشعارات المثبتة */}
            {announcements.pinned.length > 0 && (
              <div className="mt-4 space-y-2">
                {announcements.pinned.map(ann => (
                  <div key={ann.id} className="flex items-start gap-2 p-3 bg-white/10 rounded-lg backdrop-blur-sm">
                    <Pin size={14} className="text-amber-300 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-white/90">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Loading state */}
      {loadingEmployeeSummary && !isExecutive && (
        <div className="card-premium rounded-2xl p-8 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Regular Announcements */}
      {announcements.regular.length > 0 && (
        <div className="space-y-2">
          {announcements.regular.map(ann => (
            <div key={ann.id} className="flex items-start justify-between p-4 bg-blue-50 border border-blue-200 rounded-xl dark:bg-blue-950/30 dark:border-blue-800">
              <div className="flex items-start gap-3">
                <Bell size={18} className="text-blue-600 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-900 dark:text-blue-100">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">{ann.created_by_name}</p>
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
                } dark:bg-opacity-20`}
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
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{lang === 'ar' ? 'الخدمات' : 'Services'}</h2>
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
          {lang === 'ar' ? 'دار الكود - نظام الموارد البشرية' : 'DAR AL CODE HR OS'} v{appVersion}
        </div>
      )}
    </div>
  );
}
