import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, CalendarDays, Users, Shield, DollarSign, Clock, ChevronRight, 
  Briefcase, MapPin, Wallet, Settings2, Bell, Pin, X, Award, 
  CheckCircle2, Timer, TrendingDown, Sparkles, Crown, Star
} from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import api from '@/lib/api';

// ==================== رسائل تحفيزية حسب الدور ====================
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
      "Success comes to those who pursue it, you're on the right path!",
      "Be proud of what you accomplish, you create real value!",
      "Passion for work is the secret to excellence, keep your passion!",
    ]
  },
  supervisor: {
    ar: [
      "قيادتك تُلهم فريقك، شكراً لإشرافك المتميز!",
      "المشرف الناجح يصنع فرقاً ناجحاً، وأنت مثال حي!",
      "حكمتك في التوجيه تُحدث فارقاً حقيقياً!",
      "أنت ركيزة الفريق، واصل دعمك ورعايتك!",
      "إشرافك الحكيم يُثمر نتائج رائعة، استمر!",
      "الفريق يثق بقيادتك، وأنت جدير بهذه الثقة!",
    ],
    en: [
      "Your leadership inspires your team, thank you for your supervision!",
      "A successful supervisor creates a successful team, you're a living example!",
      "Your wisdom in guidance makes a real difference!",
      "You are the team's pillar, continue your support and care!",
      "Your wise supervision yields great results, keep going!",
      "The team trusts your leadership, and you deserve that trust!",
    ]
  },
  manager: {
    ar: [
      "بفضل قيادتكم الحكيمة، نتقدم نحو النجاح!",
      "رؤيتكم الثاقبة تُشكّل مستقبلنا المشرق!",
      "شكراً لإلهامكم المستمر وتوجيهاتكم الحكيمة!",
      "أنتم القدوة في التميز والإبداع!",
      "قراراتكم الصائبة تقود الفريق للنجاح!",
      "إدارتكم المتميزة هي سر تفوقنا!",
      "نفخر بالعمل تحت قيادتكم الملهمة!",
    ],
    en: [
      "With your wise leadership, we advance towards success!",
      "Your insightful vision shapes our bright future!",
      "Thank you for your continuous inspiration and wise guidance!",
      "You are the role model in excellence and creativity!",
      "Your sound decisions lead the team to success!",
      "Your distinguished management is the secret of our excellence!",
      "We are proud to work under your inspiring leadership!",
    ]
  }
};

const getDailyMessage = (role, lang) => {
  let category = 'employee';
  if (['sultan', 'naif', 'stas', 'mohammed', 'salah'].includes(role)) {
    category = 'manager';
  } else if (role === 'supervisor') {
    category = 'supervisor';
  }
  const messages = MOTIVATIONAL_MESSAGES[category]?.[lang] || MOTIVATIONAL_MESSAGES.employee[lang];
  const dayOfYear = Math.floor((new Date() - new Date(new Date().getFullYear(), 0, 0)) / (1000 * 60 * 60 * 24));
  return messages[dayOfYear % messages.length];
};

const getGreeting = (lang) => {
  const hour = new Date().getHours();
  if (hour < 12) return lang === 'ar' ? 'صباح الخير' : 'Good morning';
  if (hour < 17) return lang === 'ar' ? 'مساء الخير' : 'Good afternoon';
  return lang === 'ar' ? 'مساء الخير' : 'Good evening';
};

const getStatusColor = (status) => {
  switch (status) {
    case 'present': return 'emerald';
    case 'late': return 'amber';
    case 'absent': return 'red';
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
    { key: 'leave_balance', icon: CalendarDays, label: 'dashboard.leaveBalance' },
  ],
  sultan: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees' },
    { key: 'total_transactions', icon: Clock, label: 'dashboard.totalTransactions' },
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

// ==================== بطاقة الإدارة الفخمة ====================
const ExecutiveCard = ({ user, role, lang, stats, statCards, announcements, employeeSummary, showsAttendance, t, navigate }) => {
  const displayName = role === 'stas' ? (lang === 'ar' ? 'ستاس' : 'STAS') : (lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name);
  const dailyMessage = getDailyMessage(role, lang);
  const statusColor = showsAttendance ? getStatusColor(employeeSummary?.attendance?.today_status) : 'blue';
  
  return (
    <div className="relative" data-testid="executive-card">
      {/* الشريط المتموج الأزرق حول الإطار */}
      <div className={`absolute -inset-[3px] rounded-3xl bg-gradient-to-r 
        ${statusColor === 'emerald' ? 'from-emerald-400 via-teal-500 to-emerald-400' : ''}
        ${statusColor === 'amber' ? 'from-amber-400 via-orange-500 to-amber-400' : ''}
        ${statusColor === 'red' ? 'from-red-400 via-rose-500 to-red-400' : ''}
        ${statusColor === 'blue' ? 'from-blue-400 via-indigo-500 to-blue-400' : ''}
        ${statusColor === 'slate' ? 'from-slate-400 via-slate-500 to-slate-400' : ''}
        animate-border-flow opacity-90`} 
      />
      
      {/* الإطار الداخلي الذهبي */}
      <div className="absolute -inset-[1px] rounded-3xl bg-gradient-to-br from-amber-200/30 via-transparent to-amber-200/30" />
      
      {/* البطاقة الرئيسية */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* خلفية النجوم والتأثيرات */}
        <div className="absolute inset-0">
          {/* توهج أزرق */}
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
          {/* خطوط زخرفية */}
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/30 to-transparent" />
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/30 to-transparent" />
        </div>
        
        <div className="relative p-6 md:p-8">
          {/* التاج والدور */}
          <div className="flex justify-center mb-6">
            <div className="relative">
              <div className="absolute -inset-2 bg-gradient-to-r from-amber-400/20 via-yellow-500/30 to-amber-400/20 rounded-full blur-lg animate-pulse" />
              <div className="relative flex items-center gap-3 px-6 py-2 bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800 rounded-full border border-amber-500/30">
                <Crown size={18} className="text-amber-400" />
                <span className="text-sm font-semibold text-amber-200 tracking-wide">
                  {t(`roles.${role}`)}
                </span>
                <Star size={14} className="text-amber-400" />
              </div>
            </div>
          </div>
          
          {/* الصورة مع الإطار الفخم */}
          <div className="flex justify-center mb-6">
            <div className="relative">
              {/* الهالة الذهبية */}
              <div className="absolute -inset-3 bg-gradient-to-r from-amber-400/40 via-yellow-500/50 to-amber-400/40 rounded-2xl blur-md animate-pulse" />
              <div className="absolute -inset-1.5 bg-gradient-to-br from-amber-300/60 to-amber-600/60 rounded-2xl" />
              
              {/* الصورة */}
              <div className="relative">
                {(employeeSummary?.employee?.photo_url || user?.photo_url) ? (
                  <img 
                    src={employeeSummary?.employee?.photo_url || user?.photo_url}
                    alt={displayName}
                    className="w-24 h-24 md:w-28 md:h-28 rounded-xl object-cover"
                  />
                ) : (
                  <div className="w-24 h-24 md:w-28 md:h-28 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-4xl font-bold text-white">
                    {displayName?.[0] || 'U'}
                  </div>
                )}
              </div>
              
              {/* نقطة الحالة (إذا كان يظهر له الحضور مثل سلطان) */}
              {showsAttendance && (
                <span className={`absolute -bottom-1 -end-1 w-6 h-6 rounded-full border-3 border-slate-900 shadow-lg ${
                  employeeSummary?.attendance?.today_status === 'present' ? 'bg-emerald-500' :
                  employeeSummary?.attendance?.today_status === 'late' ? 'bg-amber-500' :
                  employeeSummary?.attendance?.today_status === 'absent' ? 'bg-red-500' : 'bg-slate-500'
                }`} />
              )}
            </div>
          </div>
          
          {/* الاسم والتحية */}
          <div className="text-center mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2 tracking-wide">
              {displayName}
            </h1>
            <p className="text-blue-300/80 text-sm">
              {getGreeting(lang)}
            </p>
          </div>
          
          {/* الرسالة التحفيزية */}
          <div className="mb-8">
            <div className="relative mx-auto max-w-lg">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/20 via-indigo-500/20 to-blue-500/20 rounded-2xl blur" />
              <div className="relative p-4 bg-slate-800/50 rounded-2xl border border-blue-500/20">
                <div className="flex items-start gap-3">
                  <Sparkles size={20} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-slate-200 text-sm leading-relaxed">
                    {dailyMessage}
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          {/* الإحصائيات (للجميع) */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {statCards.map(sc => {
              const Icon = sc.icon;
              return (
                <div key={sc.key} className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/30 to-indigo-500/30 rounded-xl opacity-0 group-hover:opacity-100 blur transition-opacity" />
                  <div className="relative p-4 bg-slate-800/80 rounded-xl border border-slate-700/50 text-center">
                    <Icon size={22} className="mx-auto mb-2 text-blue-400" />
                    <p className="text-2xl font-bold text-white">{stats[sc.key] ?? 0}</p>
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider mt-1">
                      {t(sc.label)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* إحصائيات الحضور لسلطان فقط */}
          {showsAttendance && (
            <div className="grid grid-cols-4 gap-3 mb-6">
              <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/30 text-center cursor-pointer hover:bg-slate-700/50 transition-colors"
                   onClick={() => navigate('/leave')}>
                <CalendarDays size={16} className="mx-auto mb-1 text-blue-400" />
                <p className="text-lg font-bold text-white">{employeeSummary?.leave_details?.balance || 0}</p>
                <p className="text-[9px] text-slate-500 uppercase">{lang === 'ar' ? 'إجازة' : 'Leave'}</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/30 text-center cursor-pointer hover:bg-slate-700/50 transition-colors"
                   onClick={() => navigate('/attendance')}>
                <Clock size={16} className="mx-auto mb-1 text-emerald-400" />
                <p className="text-sm font-bold text-white">{employeeSummary?.attendance?.check_in_time || '--:--'}</p>
                <p className="text-[9px] text-slate-500 uppercase">{lang === 'ar' ? 'حضور' : 'In'}</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/30 text-center">
                <Timer size={16} className="mx-auto mb-1 text-purple-400" />
                <p className="text-lg font-bold text-white">{employeeSummary?.attendance?.monthly_hours || 0}</p>
                <p className="text-[9px] text-slate-500 uppercase">{lang === 'ar' ? 'ساعات' : 'Hours'}</p>
              </div>
              <div className="p-3 bg-slate-800/50 rounded-xl border border-slate-700/30 text-center">
                <Award size={16} className="mx-auto mb-1 text-amber-400" />
                <p className="text-lg font-bold text-white">{employeeSummary?.service_info?.years_display || '0'}</p>
                <p className="text-[9px] text-slate-500 uppercase">{lang === 'ar' ? 'سنوات' : 'Years'}</p>
              </div>
            </div>
          )}
          
          {/* إشعارات ستاس المثبتة */}
          {announcements.pinned && announcements.pinned.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 bg-amber-500/20 rounded-lg">
                  <Bell size={14} className="text-amber-400" />
                </div>
                <span className="text-xs font-semibold text-amber-300 uppercase tracking-wider">
                  {lang === 'ar' ? 'إشعارات مهمة' : 'Important Notices'}
                </span>
                <div className="flex-1 h-px bg-gradient-to-r from-amber-500/30 to-transparent" />
              </div>
              
              {announcements.pinned.map(ann => (
                <div key={ann.id} className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-amber-500/20 to-orange-500/20 rounded-xl opacity-50 group-hover:opacity-100 blur transition-opacity" />
                  <div className="relative flex items-start gap-3 p-4 bg-slate-800/80 rounded-xl border border-amber-500/20">
                    <Pin size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm text-slate-200">{lang === 'ar' ? ann.message_ar : ann.message_en}</p>
                      {ann.created_by_name && (
                        <p className="text-xs text-slate-500 mt-1">— {ann.created_by_name}</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== بطاقة الموظفين والمشرفين ====================
const EmployeeCard = ({ user, role, lang, stats, announcements, employeeSummary, t, navigate }) => {
  const displayName = lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name;
  const dailyMessage = getDailyMessage(role, lang);
  const statusColor = getStatusColor(employeeSummary?.attendance?.today_status);
  
  return (
    <div className="relative" data-testid="employee-card">
      {/* الشريط المتموج حول الإطار */}
      <div className={`absolute -inset-[2px] rounded-2xl bg-gradient-to-r 
        ${statusColor === 'emerald' ? 'from-emerald-400 via-emerald-500 to-emerald-400' : ''}
        ${statusColor === 'amber' ? 'from-amber-400 via-amber-500 to-amber-400' : ''}
        ${statusColor === 'red' ? 'from-red-400 via-red-500 to-red-400' : ''}
        ${statusColor === 'slate' ? 'from-slate-400 via-slate-500 to-slate-400' : ''}
        animate-border-flow opacity-80`} 
      />
      
      {/* البطاقة */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white">
        {/* نمط الخلفية */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-300 rounded-full blur-3xl transform -translate-x-1/2 translate-y-1/2" />
        </div>
        
        <div className="relative p-6">
          {/* التحية والرسالة */}
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
          
          {/* الصورة والبيانات */}
          <div className="flex items-start gap-4 mb-6">
            <div className="relative">
              {(employeeSummary?.employee?.photo_url || user?.photo_url) ? (
                <img 
                  src={employeeSummary?.employee?.photo_url || user?.photo_url}
                  alt={displayName}
                  className="w-20 h-20 rounded-2xl object-cover ring-2 ring-white/30"
                />
              ) : (
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-3xl font-bold text-white ring-2 ring-white/30">
                  {displayName?.[0] || 'U'}
                </div>
              )}
              <span className={`absolute -bottom-1 -end-1 w-5 h-5 rounded-full border-2 border-blue-700 ${
                employeeSummary?.attendance?.today_status === 'present' ? 'bg-emerald-500' :
                employeeSummary?.attendance?.today_status === 'late' ? 'bg-amber-500' :
                employeeSummary?.attendance?.today_status === 'absent' ? 'bg-red-500' : 'bg-slate-400'
              }`} />
            </div>
            
            <div className="flex-1 min-w-0">
              <h3 className="text-xl font-bold truncate">{displayName}</h3>
              <p className="text-sm text-white/70 truncate">
                {lang === 'ar' ? employeeSummary?.contract?.job_title_ar : employeeSummary?.contract?.job_title}
              </p>
              <p className="text-xs text-white/50">
                {lang === 'ar' ? employeeSummary?.contract?.department_ar : employeeSummary?.contract?.department}
              </p>
              
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
            
            <div className="text-center px-3 py-2 bg-white/10 rounded-xl backdrop-blur-sm">
              <Award size={20} className="mx-auto text-amber-400 mb-1" />
              <p className="text-lg font-bold">{employeeSummary?.service_info?.years_display || '0'}</p>
              <p className="text-[9px] text-white/60 uppercase tracking-wider">
                {lang === 'ar' ? 'سنوات' : 'Years'}
              </p>
            </div>
          </div>
          
          {/* الإحصائيات */}
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm hover:bg-white/20 transition-colors cursor-pointer"
                 onClick={() => navigate('/leave')}>
              <CalendarDays size={18} className="mx-auto mb-1 text-blue-300" />
              <p className="text-xl font-bold">{employeeSummary?.leave_details?.balance || stats.leave_balance || 0}</p>
              <p className="text-[9px] text-white/60 uppercase tracking-wider">
                {lang === 'ar' ? 'رصيد' : 'Leave'}
              </p>
            </div>
            
            <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm hover:bg-white/20 transition-colors cursor-pointer"
                 onClick={() => navigate('/attendance')}>
              <Clock size={18} className="mx-auto mb-1 text-emerald-300" />
              <p className="text-sm font-bold">{employeeSummary?.attendance?.check_in_time || '--:--'}</p>
              <p className="text-[9px] text-white/60 uppercase tracking-wider">
                {lang === 'ar' ? 'حضور' : 'Check-in'}
              </p>
            </div>
            
            <div className="text-center p-3 bg-white/10 rounded-xl backdrop-blur-sm">
              <Timer size={18} className="mx-auto mb-1 text-purple-300" />
              <p className="text-xl font-bold">{employeeSummary?.attendance?.monthly_hours || 0}</p>
              <p className="text-[9px] text-white/60 uppercase tracking-wider">
                {lang === 'ar' ? 'ساعات' : 'Hours'}
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
          {announcements.pinned && announcements.pinned.length > 0 && (
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
  // المدراء: سلطان، نايف، ستاس، محمد، صلاح (بطاقة فخمة)
  const isManager = ['stas', 'mohammed', 'salah', 'naif', 'sultan'].includes(role);
  // من يظهر له الحضور: سلطان فقط من المدراء
  const showsAttendance = role === 'sultan';
  const isAdmin = ['sultan', 'naif', 'stas'].includes(role);
  
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
    
    // جلب ملخص الموظف
    if (user?.employee_id) {
      setLoadingEmployeeSummary(true);
      api.get(`/api/employees/${user.employee_id}/summary`)
        .then(r => setEmployeeSummary(r.data))
        .catch((err) => console.log('Employee summary error:', err))
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

  const getStatusStyle = (status) => STATUS_COLORS[status] || STATUS_COLORS.pending_ops;
  const getTranslatedType = (type) => t(`txTypes.${type}`) || type?.replace(/_/g, ' ');
  const getTranslatedStage = (stage) => {
    if (stage === 'stas') return lang === 'ar' ? 'ستاس' : 'STAS';
    return t(`stages.${stage}`) || stage;
  };

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      
      {/* البطاقة الرئيسية */}
      {isManager ? (
        <ExecutiveCard 
          user={user}
          role={role}
          lang={lang}
          stats={stats}
          statCards={statCards}
          announcements={announcements}
          employeeSummary={employeeSummary}
          showsAttendance={showsAttendance}
          t={t}
          navigate={navigate}
        />
      ) : (
        <EmployeeCard 
          user={user}
          role={role}
          lang={lang}
          stats={stats}
          announcements={announcements}
          employeeSummary={employeeSummary}
          t={t}
          navigate={navigate}
        />
      )}
      
      {/* Loading state */}
      {loadingEmployeeSummary && (
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

      {/* Expiring Contracts Alert */}
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

      {/* Quick Actions */}
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

      {/* Next Holiday */}
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
