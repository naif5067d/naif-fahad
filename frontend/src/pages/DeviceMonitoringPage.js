/**
 * Advanced Security Command Center - مركز قيادة الأمان المتقدم
 * ============================================================
 * لوحة تحكم أمنية متقدمة لكشف التلاعب وإدارة الحسابات
 * V2.0 - Enterprise Security Dashboard
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Shield, ShieldAlert, ShieldCheck, ShieldOff, ShieldX,
  Search, User, Users, UserX, UserCheck, UserCog,
  Smartphone, Monitor, Tablet, Laptop, Cpu, HardDrive,
  Clock, Calendar, AlertTriangle, AlertCircle, AlertOctagon,
  Eye, EyeOff, RefreshCw, Lock, Unlock, LogOut,
  Activity, Globe, Server, Signal, Zap, Power,
  CheckCircle, XCircle, History, Fingerprint, Wifi,
  ChevronDown, ChevronUp, ChevronRight, MoreVertical,
  Ban, Check, X, Trash2, FileText, Download,
  Radio, Circle, CircleDot, CircleOff, 
  Settings, Bell, BellOff, BellRing
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

// ==================== UTILITY FUNCTIONS ====================

const parseUserAgent = (ua) => {
  if (!ua) return { device: 'Unknown', os: '', browser: '', deviceType: 'desktop' };
  const uaLower = ua.toLowerCase();
  
  let device = '', deviceType = 'desktop', os = '', browser = '';
  
  if (uaLower.includes('iphone')) {
    deviceType = 'mobile'; os = 'iOS'; device = 'iPhone';
  } else if (uaLower.includes('ipad')) {
    deviceType = 'tablet'; device = 'iPad'; os = 'iPadOS';
  } else if (uaLower.includes('macintosh')) {
    deviceType = 'desktop'; device = 'Mac'; os = 'macOS';
  } else if (uaLower.includes('android')) {
    deviceType = 'mobile'; os = 'Android';
    if (uaLower.includes('samsung')) device = 'Samsung';
    else if (uaLower.includes('huawei')) device = 'Huawei';
    else if (uaLower.includes('xiaomi')) device = 'Xiaomi';
    else device = 'Android';
  } else if (uaLower.includes('windows')) {
    deviceType = 'desktop'; device = 'Windows PC'; os = 'Windows';
  }
  
  if (uaLower.includes('chrome')) browser = 'Chrome';
  else if (uaLower.includes('safari')) browser = 'Safari';
  else if (uaLower.includes('firefox')) browser = 'Firefox';
  else if (uaLower.includes('edge')) browser = 'Edge';
  
  return { device, os, browser, deviceType };
};

const formatTime = (dateStr) => {
  if (!dateStr) return '--:--';
  return new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
};

const formatFullDateTime = (dateStr) => {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  const days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
  return `${days[d.getDay()]} ${formatDate(dateStr)} ${formatTime(dateStr)}`;
};

const calculateDuration = (loginAt, logoutAt) => {
  if (!loginAt) return '-';
  const login = new Date(loginAt);
  const logout = logoutAt ? new Date(logoutAt) : new Date();
  const diff = Math.floor((logout - login) / 1000 / 60);
  const hours = Math.floor(diff / 60);
  const mins = diff % 60;
  return `${hours}:${mins.toString().padStart(2,'0')}`;
};

// ==================== COMPONENTS ====================

const DeviceIcon = ({ type, size = 20, className = '' }) => {
  const icons = { 
    smartphone: Smartphone, mobile: Smartphone, 
    tablet: Tablet, laptop: Laptop, 
    desktop: Monitor, default: Monitor 
  };
  const Icon = icons[type] || icons.default;
  return <Icon size={size} className={className} />;
};

const SeverityBadge = ({ severity }) => {
  const config = {
    critical: { bg: 'bg-red-500', text: 'text-white', label: 'حرج' },
    high: { bg: 'bg-orange-500', text: 'text-white', label: 'عالي' },
    medium: { bg: 'bg-yellow-500', text: 'text-black', label: 'متوسط' },
    low: { bg: 'bg-blue-500', text: 'text-white', label: 'منخفض' }
  };
  const cfg = config[severity] || config.low;
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
};

const StatCard = ({ icon: Icon, label, value, subValue, color = 'slate', trend, onClick }) => {
  const colors = {
    green: 'from-emerald-500 to-emerald-600',
    red: 'from-red-500 to-red-600',
    yellow: 'from-amber-500 to-amber-600',
    blue: 'from-blue-500 to-blue-600',
    purple: 'from-purple-500 to-purple-600',
    slate: 'from-slate-600 to-slate-700'
  };
  
  return (
    <div 
      onClick={onClick}
      className={`relative overflow-hidden rounded-xl md:rounded-2xl bg-gradient-to-br ${colors[color]} p-3 md:p-5 text-white shadow-lg ${onClick ? 'cursor-pointer hover:scale-[1.02] transition-transform active:scale-[0.98]' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-white/70 text-[10px] md:text-xs font-medium mb-0.5 md:mb-1 truncate">{label}</p>
          <p className="text-xl md:text-3xl font-bold">{value}</p>
          {subValue && <p className="text-white/60 text-[10px] md:text-xs mt-1 truncate">{subValue}</p>}
        </div>
        <div className="w-8 h-8 md:w-12 md:h-12 rounded-lg md:rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
          <Icon size={16} className="md:hidden" />
          <Icon size={24} className="hidden md:block" />
        </div>
      </div>
      {trend && (
        <div className={`absolute bottom-2 left-4 text-xs flex items-center gap-1 ${trend > 0 ? 'text-green-300' : 'text-red-300'}`}>
          {trend > 0 ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {Math.abs(trend)}%
        </div>
      )}
    </div>
  );
};

// ==================== MAIN COMPONENT ====================

export default function DeviceMonitoringPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const isStas = user?.role === 'stas';
  
  // ========== STATE ==========
  const [activeTab, setActiveTab] = useState('alerts');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  
  // Stats
  const [stats, setStats] = useState({
    active_sessions: 0,
    suspended_accounts: 0,
    blocked_devices: 0,
    logins_today: 0,
    alerts_today: 0,
    new_devices_today: 0
  });
  
  // Alerts
  const [alerts, setAlerts] = useState([]);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  
  // Employees & Sessions
  const [employees, setEmployees] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSessions, setActiveSessions] = useState([]);
  
  // Suspend Dialog
  const [suspendDialog, setSuspendDialog] = useState(false);
  const [suspendReason, setSuspendReason] = useState('');
  const [suspendDuration, setSuspendDuration] = useState('');
  const [suspendLoading, setSuspendLoading] = useState(false);
  
  // Suspended Accounts
  const [suspendedAccounts, setSuspendedAccounts] = useState([]);
  
  // Security Log
  const [securityLog, setSecurityLog] = useState([]);
  
  // Session Details Modal
  const [sessionDetails, setSessionDetails] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  
  // ========== DATA FETCHING ==========
  
  const fetchStats = async () => {
    try {
      const res = await api.get('/api/security/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };
  
  const fetchAlerts = async () => {
    setLoadingAlerts(true);
    try {
      const res = await api.get('/api/security/fraud-alerts');
      setAlerts(res.data);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    } finally {
      setLoadingAlerts(false);
    }
  };
  
  const fetchEmployees = async () => {
    try {
      const [empRes, usersRes] = await Promise.all([
        api.get('/api/employees'),
        api.get('/api/security/suspended-accounts').catch(() => ({ data: [] }))
      ]);
      
      const activeEmps = empRes.data.filter(e => e.is_active);
      // Add suspension info
      const suspendedIds = new Set(usersRes.data.map(u => u.employee_id));
      const empsWithStatus = activeEmps.map(emp => ({
        ...emp,
        is_suspended: suspendedIds.has(emp.id)
      }));
      
      setEmployees(empsWithStatus);
      setSuspendedAccounts(usersRes.data);
    } catch (err) {
      console.error('Failed to fetch employees:', err);
    }
  };
  
  const fetchActiveSessions = async () => {
    try {
      // Get all active sessions from login_sessions
      const res = await api.get('/api/devices/all-sessions?status=active');
      setActiveSessions(res.data || []);
    } catch (err) {
      // If endpoint doesn't exist, try alternative
      try {
        const empRes = await api.get('/api/employees');
        const activeEmps = empRes.data.filter(e => e.is_active);
        let allSessions = [];
        
        for (const emp of activeEmps.slice(0, 10)) { // Limit for performance
          try {
            const sessRes = await api.get(`/api/devices/login-sessions/${emp.id}?period=daily`);
            const activeSess = sessRes.data.filter(s => s.status === 'active');
            allSessions = [...allSessions, ...activeSess.map(s => ({ ...s, employee_name: emp.full_name_ar }))];
          } catch {}
        }
        
        setActiveSessions(allSessions);
      } catch {}
    }
  };
  
  const fetchSecurityLog = async () => {
    try {
      const res = await api.get('/api/security/security-log?limit=50');
      setSecurityLog(res.data);
    } catch (err) {
      console.error('Failed to fetch security log:', err);
    }
  };
  
  const refreshAll = async () => {
    setRefreshing(true);
    await Promise.all([
      fetchStats(),
      fetchAlerts(),
      fetchEmployees(),
      fetchActiveSessions(),
      fetchSecurityLog()
    ]);
    setRefreshing(false);
    toast.success('تم تحديث البيانات');
  };
  
  // Initial load
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchStats(),
      fetchAlerts(),
      fetchEmployees(),
      fetchActiveSessions(),
      fetchSecurityLog()
    ]).finally(() => setLoading(false));
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchStats();
      fetchAlerts();
      fetchActiveSessions();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);
  
  // ========== ACTIONS ==========
  
  const handleSuspendAccounts = async () => {
    if (selectedEmployees.length === 0) {
      toast.error('اختر موظفاً واحداً على الأقل');
      return;
    }
    if (!suspendReason.trim()) {
      toast.error('أدخل سبب التعطيل');
      return;
    }
    
    setSuspendLoading(true);
    try {
      const res = await api.post('/api/security/suspend-accounts', {
        employee_ids: selectedEmployees,
        reason: suspendReason,
        duration_hours: suspendDuration ? parseInt(suspendDuration) : null,
        notify_employee: true
      });
      
      toast.success(res.data.message_ar || `تم تعطيل ${res.data.suspended_count} حساب`);
      setSuspendDialog(false);
      setSuspendReason('');
      setSuspendDuration('');
      setSelectedEmployees([]);
      
      // Refresh data
      await Promise.all([fetchEmployees(), fetchStats(), fetchSecurityLog()]);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل تعطيل الحسابات');
    } finally {
      setSuspendLoading(false);
    }
  };
  
  const handleUnblockAccount = async (employeeId) => {
    try {
      const res = await api.post('/api/security/unblock-accounts', {
        employee_ids: [employeeId],
        reason: 'إلغاء التعطيل من لوحة الأمان'
      });
      
      toast.success(res.data.message_ar || 'تم إلغاء التعطيل');
      await Promise.all([fetchEmployees(), fetchStats(), fetchSecurityLog()]);
    } catch (err) {
      toast.error('فشل إلغاء التعطيل');
    }
  };
  
  const handleForceLogout = async (employeeId, employeeName) => {
    if (!confirm(`هل تريد إنهاء جميع جلسات ${employeeName}؟`)) return;
    
    try {
      const res = await api.post(`/api/security/force-logout/${employeeId}`);
      toast.success(res.data.message_ar || 'تم إنهاء الجلسات');
      await Promise.all([fetchActiveSessions(), fetchStats()]);
    } catch (err) {
      toast.error('فشل إنهاء الجلسات');
    }
  };
  
  const handleEmergencyLogoutAll = async () => {
    if (!confirm('تحذير! سيتم إنهاء جلسات جميع المستخدمين. هل أنت متأكد؟')) return;
    
    try {
      const res = await api.post('/api/security/force-logout-all');
      toast.success(res.data.message_ar || 'تم إنهاء جميع الجلسات');
      await Promise.all([fetchActiveSessions(), fetchStats()]);
    } catch (err) {
      toast.error('فشل الإجراء');
    }
  };
  
  const viewSessionDetails = async (session) => {
    setSessionDetails(session);
    setDetailsOpen(true);
  };
  
  // ========== FILTERED DATA ==========
  
  const filteredEmployees = useMemo(() => {
    if (!searchQuery) return employees;
    const q = searchQuery.toLowerCase();
    return employees.filter(e => 
      e.full_name_ar?.toLowerCase().includes(q) ||
      e.full_name?.toLowerCase().includes(q) ||
      e.employee_number?.includes(q)
    );
  }, [employees, searchQuery]);
  
  const toggleEmployeeSelection = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };
  
  const selectAllFiltered = () => {
    const ids = filteredEmployees.map(e => e.id);
    setSelectedEmployees(prev => {
      const allSelected = ids.every(id => prev.includes(id));
      if (allSelected) return prev.filter(id => !ids.includes(id));
      return [...new Set([...prev, ...ids])];
    });
  };
  
  // ========== RENDER ==========
  
  if (!isStas) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6" data-testid="access-denied">
        <Card className="max-w-md border-0 bg-slate-800">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-20 h-20 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <ShieldX size={40} className="text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">غير مصرح</h2>
            <p className="text-slate-400">هذه الصفحة متاحة فقط لمسؤول النظام (STAS)</p>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-slate-900" data-testid="device-monitoring-page">
      {/* ========== HEADER - MOBILE OPTIMIZED ========== */}
      <div className="bg-gradient-to-l from-slate-800 via-slate-900 to-black border-b border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4">
            {/* Title Section */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 md:w-14 md:h-14 rounded-xl md:rounded-2xl bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center shadow-lg shadow-red-500/20 flex-shrink-0">
                <ShieldAlert size={20} className="md:hidden text-white" />
                <ShieldAlert size={28} className="hidden md:block text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-lg md:text-2xl font-bold text-white truncate">مركز قيادة الأمان</h1>
                <p className="text-slate-400 text-xs md:text-sm hidden md:block">نظام متقدم لكشف التلاعب ومراقبة الأجهزة</p>
              </div>
            </div>
            
            {/* Actions - Mobile: Full Width */}
            <div className="flex items-center gap-2 md:gap-3">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={refreshAll}
                disabled={refreshing}
                className="border-slate-600 text-slate-300 hover:bg-slate-700 flex-1 md:flex-none"
              >
                <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
                <span className="mr-1.5 text-xs md:text-sm">تحديث</span>
              </Button>
              
              {stats.alerts_today > 0 && (
                <div className="flex items-center gap-1.5 px-2 py-1.5 md:px-3 md:py-2 rounded-lg bg-red-500/20 border border-red-500/30">
                  <BellRing size={14} className="text-red-400 animate-pulse" />
                  <span className="text-red-400 text-xs md:text-sm font-bold">{stats.alerts_today} تنبيه</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* ========== STATS CARDS - MOBILE OPTIMIZED ========== */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4 mobile-keep-cols">
          <StatCard 
            icon={Activity} 
            label="جلسات نشطة" 
            value={stats.active_sessions}
            color="green"
            onClick={() => setActiveTab('sessions')}
          />
          <StatCard 
            icon={AlertOctagon} 
            label="تنبيهات اليوم" 
            value={stats.alerts_today}
            color={stats.alerts_today > 0 ? 'red' : 'slate'}
            onClick={() => setActiveTab('alerts')}
          />
          <StatCard 
            icon={UserX} 
            label="حسابات معطلة" 
            value={stats.suspended_accounts}
            color={stats.suspended_accounts > 0 ? 'yellow' : 'slate'}
            onClick={() => setActiveTab('suspended')}
          />
          <StatCard 
            icon={Ban} 
            label="أجهزة محظورة" 
            value={stats.blocked_devices}
            color="purple"
          />
          <StatCard 
            icon={LogOut} 
            label="دخول اليوم" 
            value={stats.logins_today}
            color="blue"
            onClick={() => setActiveTab('sessions')}
          />
          <StatCard 
            icon={Smartphone} 
            label="أجهزة جديدة" 
            value={stats.new_devices_today}
            color="slate"
          />
        </div>
      </div>
      
      {/* ========== MAIN CONTENT ========== */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-slate-800 border border-slate-700 p-1 rounded-xl">
            <TabsTrigger 
              value="alerts" 
              className="data-[state=active]:bg-red-500 data-[state=active]:text-white rounded-lg px-4"
            >
              <AlertTriangle size={16} className="ml-2" />
              تنبيهات الأمان
              {alerts.length > 0 && (
                <Badge variant="destructive" className="mr-2 text-[10px]">{alerts.length}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger 
              value="sessions" 
              className="data-[state=active]:bg-emerald-500 data-[state=active]:text-white rounded-lg px-4"
            >
              <Activity size={16} className="ml-2" />
              الجلسات النشطة
            </TabsTrigger>
            <TabsTrigger 
              value="control" 
              className="data-[state=active]:bg-blue-500 data-[state=active]:text-white rounded-lg px-4"
            >
              <UserCog size={16} className="ml-2" />
              التحكم بالحسابات
            </TabsTrigger>
            <TabsTrigger 
              value="suspended" 
              className="data-[state=active]:bg-yellow-500 data-[state=active]:text-black rounded-lg px-4"
            >
              <Lock size={16} className="ml-2" />
              المعطلين
            </TabsTrigger>
            <TabsTrigger 
              value="log" 
              className="data-[state=active]:bg-purple-500 data-[state=active]:text-white rounded-lg px-4"
            >
              <History size={16} className="ml-2" />
              سجل الأمان
            </TabsTrigger>
          </TabsList>
          
          {/* ========== ALERTS TAB ========== */}
          <TabsContent value="alerts" className="mt-0">
            <Card className="border-0 bg-slate-800/50 shadow-2xl">
              <CardHeader className="border-b border-slate-700/50">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <AlertTriangle className="text-red-500" size={20} />
                    تنبيهات الأمان النشطة
                  </CardTitle>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={fetchAlerts}
                    disabled={loadingAlerts}
                    className="text-slate-400 hover:text-white"
                  >
                    <RefreshCw size={14} className={loadingAlerts ? 'animate-spin' : ''} />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {loadingAlerts ? (
                  <div className="py-20 text-center">
                    <RefreshCw size={32} className="animate-spin text-slate-500 mx-auto" />
                  </div>
                ) : alerts.length === 0 ? (
                  <div className="py-20 text-center">
                    <div className="w-20 h-20 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
                      <ShieldCheck size={40} className="text-emerald-500" />
                    </div>
                    <p className="text-slate-400 text-lg">لا توجد تنبيهات أمنية</p>
                    <p className="text-slate-500 text-sm mt-1">النظام آمن</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-700/50">
                    {alerts.map((alert, idx) => (
                      <div 
                        key={alert.id || idx}
                        className={`p-5 hover:bg-slate-700/30 transition-colors ${
                          alert.severity === 'critical' ? 'bg-red-500/10' : ''
                        }`}
                      >
                        <div className="flex items-start gap-4">
                          <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                            alert.severity === 'critical' ? 'bg-red-500/20' :
                            alert.severity === 'high' ? 'bg-orange-500/20' :
                            'bg-yellow-500/20'
                          }`}>
                            {alert.type === 'shared_device' ? (
                              <Users className={
                                alert.severity === 'critical' ? 'text-red-500' :
                                alert.severity === 'high' ? 'text-orange-500' : 'text-yellow-500'
                              } size={24} />
                            ) : (
                              <Activity className={
                                alert.severity === 'critical' ? 'text-red-500' :
                                alert.severity === 'high' ? 'text-orange-500' : 'text-yellow-500'
                              } size={24} />
                            )}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <SeverityBadge severity={alert.severity} />
                              <span className="text-white font-bold">{alert.title_ar}</span>
                            </div>
                            <p className="text-slate-300 text-sm">{alert.message_ar}</p>
                            
                            {alert.employee_names && (
                              <div className="mt-3 flex flex-wrap gap-2">
                                {alert.employee_names.map((name, i) => (
                                  <span key={i} className="px-2 py-1 rounded bg-slate-700 text-slate-300 text-xs">
                                    {name}
                                  </span>
                                ))}
                              </div>
                            )}
                            
                            <p className="text-slate-500 text-xs mt-2">
                              <Clock size={12} className="inline ml-1" />
                              {formatFullDateTime(alert.detected_at)}
                            </p>
                          </div>
                          
                          {alert.employees && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              className="border-red-500/50 text-red-400 hover:bg-red-500/20"
                              onClick={() => {
                                setSelectedEmployees(alert.employees);
                                setActiveTab('control');
                              }}
                            >
                              <Ban size={14} className="ml-1" />
                              تعطيل
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* ========== SESSIONS TAB ========== */}
          <TabsContent value="sessions" className="mt-0">
            <Card className="border-0 bg-slate-800/50 shadow-2xl">
              <CardHeader className="border-b border-slate-700/50">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Activity className="text-emerald-500" size={20} />
                    الجلسات النشطة حالياً
                    <Badge className="bg-emerald-500">{activeSessions.length}</Badge>
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={fetchActiveSessions}
                      className="text-slate-400 hover:text-white"
                    >
                      <RefreshCw size={14} />
                    </Button>
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={handleEmergencyLogoutAll}
                      className="bg-red-600 hover:bg-red-700"
                    >
                      <Power size={14} className="ml-1" />
                      إنهاء الكل (طوارئ)
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {activeSessions.length === 0 ? (
                  <div className="py-16 text-center">
                    <Activity size={48} className="mx-auto text-slate-600 mb-4" />
                    <p className="text-slate-400">لا توجد جلسات نشطة حالياً</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-slate-900/50 text-slate-400 text-xs">
                          <th className="p-4 text-right font-medium">الموظف</th>
                          <th className="p-4 text-right font-medium">الجهاز</th>
                          <th className="p-4 text-center font-medium">وقت الدخول</th>
                          <th className="p-4 text-center font-medium">المدة</th>
                          <th className="p-4 text-center font-medium">الحالة</th>
                          <th className="p-4 text-center font-medium w-32">إجراءات</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-700/50">
                        {activeSessions.map((session, idx) => {
                          const fp = session.fingerprint_data || {};
                          const parsed = parseUserAgent(fp.userAgent || session.user_agent || '');
                          const deviceName = fp.deviceModel || fp.deviceBrand || parsed.device || 'جهاز';
                          
                          return (
                            <tr 
                              key={session.id || idx}
                              className="hover:bg-slate-700/30 transition-colors"
                            >
                              <td className="p-4">
                                <div>
                                  <p className="text-white font-medium">{session.employee_name || session.username}</p>
                                  <p className="text-slate-500 text-xs">#{session.employee_id?.slice(-8)}</p>
                                </div>
                              </td>
                              <td className="p-4">
                                <div className="flex items-center gap-2">
                                  <div className="w-10 h-10 rounded-lg bg-slate-700 flex items-center justify-center">
                                    <DeviceIcon type={fp.deviceType || parsed.deviceType} size={18} className="text-slate-400" />
                                  </div>
                                  <div>
                                    <p className="text-white text-sm">{deviceName}</p>
                                    <p className="text-slate-500 text-xs">
                                      {fp.osName || parsed.os} - {fp.browserName || parsed.browser}
                                    </p>
                                  </div>
                                </div>
                              </td>
                              <td className="p-4 text-center">
                                <span className="text-emerald-400 font-mono text-sm">
                                  {formatTime(session.login_at)}
                                </span>
                              </td>
                              <td className="p-4 text-center">
                                <span className="text-white font-mono text-sm">
                                  {calculateDuration(session.login_at, null)}
                                </span>
                              </td>
                              <td className="p-4 text-center">
                                <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs">
                                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
                                  نشط
                                </span>
                              </td>
                              <td className="p-4 text-center">
                                <div className="flex items-center justify-center gap-1">
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    className="h-8 w-8 p-0 text-slate-400 hover:text-white"
                                    onClick={() => viewSessionDetails(session)}
                                  >
                                    <Eye size={16} />
                                  </Button>
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    className="h-8 w-8 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/20"
                                    onClick={() => handleForceLogout(session.employee_id, session.employee_name || session.username)}
                                  >
                                    <LogOut size={16} />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* ========== CONTROL TAB ========== */}
          <TabsContent value="control" className="mt-0">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Employee List */}
              <Card className="lg:col-span-2 border-0 bg-slate-800/50 shadow-2xl">
                <CardHeader className="border-b border-slate-700/50">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white flex items-center gap-2">
                      <Users size={20} className="text-blue-500" />
                      اختيار الموظفين
                      {selectedEmployees.length > 0 && (
                        <Badge className="bg-blue-500">{selectedEmployees.length} محدد</Badge>
                      )}
                    </CardTitle>
                  </div>
                  
                  {/* Search & Actions */}
                  <div className="flex items-center gap-3 mt-4">
                    <div className="relative flex-1">
                      <Search size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500" />
                      <Input
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="بحث بالاسم أو الرقم الوظيفي..."
                        className="pr-10 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                      />
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={selectAllFiltered}
                      className="border-slate-600 text-slate-300"
                    >
                      {filteredEmployees.every(e => selectedEmployees.includes(e.id)) ? 'إلغاء الكل' : 'تحديد الكل'}
                    </Button>
                  </div>
                </CardHeader>
                
                <CardContent className="p-0">
                  <ScrollArea className="h-[400px]">
                    <div className="divide-y divide-slate-700/50">
                      {filteredEmployees.map(emp => (
                        <div 
                          key={emp.id}
                          className={`p-4 flex items-center gap-4 hover:bg-slate-700/30 transition-colors cursor-pointer ${
                            selectedEmployees.includes(emp.id) ? 'bg-blue-500/10' : ''
                          }`}
                          onClick={() => toggleEmployeeSelection(emp.id)}
                        >
                          <Checkbox 
                            checked={selectedEmployees.includes(emp.id)}
                            className="border-slate-600 data-[state=checked]:bg-blue-500"
                          />
                          
                          <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-white font-bold">
                            {emp.full_name_ar?.charAt(0) || '?'}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <p className="text-white font-medium">{emp.full_name_ar}</p>
                            <p className="text-slate-500 text-xs">#{emp.employee_number}</p>
                          </div>
                          
                          {emp.is_suspended && (
                            <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
                              <Lock size={12} className="ml-1" />
                              معطل
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
              
              {/* Actions Panel */}
              <Card className="border-0 bg-slate-800/50 shadow-2xl">
                <CardHeader className="border-b border-slate-700/50">
                  <CardTitle className="text-white flex items-center gap-2">
                    <Settings size={20} className="text-slate-400" />
                    إجراءات الأمان
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-5 space-y-4">
                  {/* Selected Summary */}
                  {selectedEmployees.length > 0 && (
                    <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
                      <p className="text-blue-400 text-sm font-medium">
                        تم تحديد {selectedEmployees.length} موظف
                      </p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {selectedEmployees.slice(0, 5).map(id => {
                          const emp = employees.find(e => e.id === id);
                          return (
                            <span key={id} className="px-2 py-0.5 rounded bg-slate-700 text-slate-300 text-xs">
                              {emp?.full_name_ar?.split(' ')[0]}
                            </span>
                          );
                        })}
                        {selectedEmployees.length > 5 && (
                          <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-400 text-xs">
                            +{selectedEmployees.length - 5}
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Suspend Button */}
                  <Button 
                    className="w-full bg-red-600 hover:bg-red-700 text-white"
                    disabled={selectedEmployees.length === 0}
                    onClick={() => setSuspendDialog(true)}
                  >
                    <Ban size={18} className="ml-2" />
                    تعطيل الحسابات المحددة
                  </Button>
                  
                  {/* Force Logout Selected */}
                  <Button 
                    variant="outline"
                    className="w-full border-orange-500/50 text-orange-400 hover:bg-orange-500/20"
                    disabled={selectedEmployees.length === 0}
                    onClick={async () => {
                      if (!confirm(`إنهاء جلسات ${selectedEmployees.length} موظف؟`)) return;
                      for (const empId of selectedEmployees) {
                        try {
                          await api.post(`/api/security/force-logout/${empId}`);
                        } catch {}
                      }
                      toast.success('تم إنهاء الجلسات');
                      await fetchActiveSessions();
                    }}
                  >
                    <LogOut size={18} className="ml-2" />
                    إنهاء جلسات المحددين
                  </Button>
                  
                  <div className="border-t border-slate-700 pt-4 mt-4">
                    <p className="text-slate-500 text-xs text-center">
                      جميع الإجراءات يتم تسجيلها في سجل الأمان
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          {/* ========== SUSPENDED TAB ========== */}
          <TabsContent value="suspended" className="mt-0">
            <Card className="border-0 bg-slate-800/50 shadow-2xl">
              <CardHeader className="border-b border-slate-700/50">
                <CardTitle className="text-white flex items-center gap-2">
                  <Lock className="text-yellow-500" size={20} />
                  الحسابات المعطلة
                  <Badge className="bg-yellow-500/20 text-yellow-400">{suspendedAccounts.length}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {suspendedAccounts.length === 0 ? (
                  <div className="py-16 text-center">
                    <Unlock size={48} className="mx-auto text-slate-600 mb-4" />
                    <p className="text-slate-400">لا توجد حسابات معطلة</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-700/50">
                    {suspendedAccounts.map((account, idx) => (
                      <div key={account.id || idx} className="p-5 flex items-center justify-between hover:bg-slate-700/30">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
                            <UserX className="text-red-500" size={24} />
                          </div>
                          <div>
                            <p className="text-white font-medium">{account.employee_name_ar || account.full_name}</p>
                            <p className="text-slate-500 text-xs">#{account.employee_number || account.username}</p>
                            {account.suspend_reason && (
                              <p className="text-red-400 text-xs mt-1">السبب: {account.suspend_reason}</p>
                            )}
                            {account.suspended_until && (
                              <p className="text-yellow-400 text-xs">
                                حتى: {formatFullDateTime(account.suspended_until)}
                              </p>
                            )}
                          </div>
                        </div>
                        
                        <Button 
                          variant="outline"
                          size="sm"
                          className="border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/20"
                          onClick={() => handleUnblockAccount(account.employee_id)}
                        >
                          <Unlock size={14} className="ml-1" />
                          إلغاء التعطيل
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* ========== LOG TAB ========== */}
          <TabsContent value="log" className="mt-0">
            <Card className="border-0 bg-slate-800/50 shadow-2xl">
              <CardHeader className="border-b border-slate-700/50">
                <CardTitle className="text-white flex items-center gap-2">
                  <History className="text-purple-500" size={20} />
                  سجل الأمان
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {securityLog.length === 0 ? (
                  <div className="py-16 text-center">
                    <FileText size={48} className="mx-auto text-slate-600 mb-4" />
                    <p className="text-slate-400">لا توجد سجلات</p>
                  </div>
                ) : (
                  <ScrollArea className="h-[500px]">
                    <div className="divide-y divide-slate-700/50">
                      {securityLog.map((log, idx) => {
                        const actionConfig = {
                          account_suspended: { icon: Ban, color: 'text-red-500', label: 'تعطيل حساب' },
                          account_unblocked: { icon: Unlock, color: 'text-emerald-500', label: 'إلغاء تعطيل' },
                          force_logout: { icon: LogOut, color: 'text-orange-500', label: 'إنهاء جلسة' },
                          emergency_logout_all: { icon: Power, color: 'text-red-600', label: 'إنهاء جميع الجلسات' },
                          device_blocked: { icon: Ban, color: 'text-purple-500', label: 'حظر جهاز' },
                          device_unblocked: { icon: Check, color: 'text-emerald-500', label: 'إلغاء حظر جهاز' },
                        };
                        const cfg = actionConfig[log.action] || { icon: Activity, color: 'text-slate-400', label: log.action };
                        const Icon = cfg.icon;
                        
                        return (
                          <div key={log.id || idx} className="p-4 hover:bg-slate-700/30">
                            <div className="flex items-start gap-3">
                              <div className={`w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center ${cfg.color}`}>
                                <Icon size={16} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-white font-medium text-sm">{cfg.label}</span>
                                  {log.employee_name && (
                                    <span className="text-slate-400 text-sm">- {log.employee_name}</span>
                                  )}
                                </div>
                                {log.reason && (
                                  <p className="text-slate-500 text-xs mt-1">السبب: {log.reason}</p>
                                )}
                                <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                                  <span>
                                    <User size={12} className="inline ml-1" />
                                    {log.performed_by_name || log.performed_by}
                                  </span>
                                  <span>
                                    <Clock size={12} className="inline ml-1" />
                                    {formatFullDateTime(log.created_at)}
                                  </span>
                                  {log.ip_address && (
                                    <span>
                                      <Globe size={12} className="inline ml-1" />
                                      {log.ip_address}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      
      {/* ========== SUSPEND DIALOG ========== */}
      <Dialog open={suspendDialog} onOpenChange={setSuspendDialog}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-500">
              <Ban size={20} />
              تعطيل الحسابات
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              سيتم منع {selectedEmployees.length} موظف من تسجيل الدخول وإنهاء جلساتهم النشطة
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm text-slate-400 block mb-2">سبب التعطيل *</label>
              <Textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                placeholder="أدخل سبب التعطيل..."
                className="bg-slate-900 border-slate-700 text-white"
                rows={3}
              />
            </div>
            
            <div>
              <label className="text-sm text-slate-400 block mb-2">مدة التعطيل</label>
              <Select value={suspendDuration} onValueChange={setSuspendDuration}>
                <SelectTrigger className="bg-slate-900 border-slate-700 text-white">
                  <SelectValue placeholder="دائم (حتى الإلغاء)" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  <SelectItem value="">دائم (حتى الإلغاء)</SelectItem>
                  <SelectItem value="1">ساعة واحدة</SelectItem>
                  <SelectItem value="4">4 ساعات</SelectItem>
                  <SelectItem value="8">8 ساعات</SelectItem>
                  <SelectItem value="24">24 ساعة</SelectItem>
                  <SelectItem value="48">48 ساعة</SelectItem>
                  <SelectItem value="168">أسبوع</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <DialogFooter className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => setSuspendDialog(false)}
              className="border-slate-600 text-slate-300"
            >
              إلغاء
            </Button>
            <Button 
              onClick={handleSuspendAccounts}
              disabled={suspendLoading || !suspendReason.trim()}
              className="bg-red-600 hover:bg-red-700"
            >
              {suspendLoading ? (
                <RefreshCw size={16} className="animate-spin" />
              ) : (
                <>
                  <Ban size={16} className="ml-1" />
                  تعطيل {selectedEmployees.length} حساب
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ========== SESSION DETAILS DIALOG ========== */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Fingerprint size={20} className="text-blue-500" />
              تفاصيل الجلسة وبصمة الجهاز
            </DialogTitle>
          </DialogHeader>
          
          {sessionDetails && (
            <div className="space-y-6 py-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-900">
                  <p className="text-slate-500 text-[10px] uppercase">الدخول</p>
                  <p className="text-emerald-400 font-bold">{formatTime(sessionDetails.login_at)}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-900">
                  <p className="text-slate-500 text-[10px] uppercase">الخروج</p>
                  <p className="text-red-400 font-bold">{sessionDetails.logout_at ? formatTime(sessionDetails.logout_at) : 'نشط'}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-900">
                  <p className="text-slate-500 text-[10px] uppercase">المدة</p>
                  <p className="text-white font-bold">{calculateDuration(sessionDetails.login_at, sessionDetails.logout_at)}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-900">
                  <p className="text-slate-500 text-[10px] uppercase">الحالة</p>
                  <p className={`font-bold ${sessionDetails.status === 'active' ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {sessionDetails.status === 'active' ? 'نشط' : 'منتهية'}
                  </p>
                </div>
              </div>
              
              {/* Device Info */}
              {sessionDetails.fingerprint_data && (
                <>
                  <div className="p-4 rounded-xl bg-slate-900">
                    <h4 className="text-white font-bold mb-3 flex items-center gap-2">
                      <Monitor size={16} />
                      معلومات الجهاز
                    </h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-slate-500 text-xs">الجهاز</p>
                        <p className="text-white">{sessionDetails.fingerprint_data.deviceModel || sessionDetails.fingerprint_data.deviceBrand || 'غير محدد'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 text-xs">نظام التشغيل</p>
                        <p className="text-white">{sessionDetails.fingerprint_data.osName} {sessionDetails.fingerprint_data.osVersion}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 text-xs">المتصفح</p>
                        <p className="text-white">{sessionDetails.fingerprint_data.browserName} {sessionDetails.fingerprint_data.browserVersion}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 text-xs">الشاشة</p>
                        <p className="text-white">{sessionDetails.fingerprint_data.screenResolution}</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Technical Fingerprint */}
                  <div className="p-4 rounded-xl bg-black font-mono text-xs">
                    <p className="text-slate-500 mb-2">// البصمة التقنية الكاملة</p>
                    <div className="space-y-1 text-emerald-400">
                      <p>gpu: {sessionDetails.fingerprint_data.webglRenderer || '-'}</p>
                      <p>vendor: {sessionDetails.fingerprint_data.webglVendor || '-'}</p>
                      <p>memory: {sessionDetails.fingerprint_data.deviceMemory || '-'} GB</p>
                      <p>cores: {sessionDetails.fingerprint_data.hardwareConcurrency || '-'}</p>
                      <p>screen: {sessionDetails.fingerprint_data.screenResolution || '-'}</p>
                      <p>pixel_ratio: {sessionDetails.fingerprint_data.devicePixelRatio || '-'}</p>
                      <p>touch_points: {sessionDetails.fingerprint_data.maxTouchPoints || '-'}</p>
                      <p>platform: {sessionDetails.fingerprint_data.platform || '-'}</p>
                      <p>timezone: {sessionDetails.fingerprint_data.timezone || '-'}</p>
                      <p>canvas_fp: {sessionDetails.fingerprint_data.canvasFingerprint?.substring(0, 16) || '-'}...</p>
                      <p>audio_fp: {sessionDetails.fingerprint_data.audioFingerprint?.substring(0, 16) || '-'}...</p>
                      {sessionDetails.core_signature && (
                        <p className="text-yellow-400 mt-2">signature: {sessionDetails.core_signature}</p>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
