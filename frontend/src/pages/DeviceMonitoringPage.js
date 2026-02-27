import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Fingerprint, Search, User, Smartphone, Monitor, Tablet, Laptop,
  Clock, Calendar, AlertTriangle, Shield, Eye, RefreshCw, Download,
  Cpu, HardDrive, Wifi, Battery, ChevronDown, ChevronUp, Activity,
  MapPin, Globe, Zap, CheckCircle, XCircle, AlertCircle, History
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// أيقونات الأجهزة
const DeviceIcon = ({ type, size = 24, className = '' }) => {
  const icons = {
    smartphone: Smartphone,
    tablet: Tablet,
    laptop: Laptop,
    monitor: Monitor,
    default: Monitor
  };
  const Icon = icons[type] || icons.default;
  return <Icon size={size} className={className} />;
};

export default function DeviceMonitoringPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  
  // === State ===
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  
  // بيانات الموظف المختار
  const [employeeDevices, setEmployeeDevices] = useState([]);
  const [employeeSessions, setEmployeeSessions] = useState([]);
  const [fraudAlerts, setFraudAlerts] = useState([]);
  const [deviceDetails, setDeviceDetails] = useState(null);
  
  // Dialog
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  
  // الفترة
  const [period, setPeriod] = useState('monthly');

  // === جلب الموظفين ===
  useEffect(() => {
    fetchEmployees();
  }, []);

  // === جلب بيانات الموظف المختار ===
  useEffect(() => {
    if (selectedEmployee) {
      fetchEmployeeData();
    }
  }, [selectedEmployee, period]);

  const fetchEmployees = async () => {
    try {
      const res = await api.get('/api/employees');
      setEmployees(res.data.filter(e => e.is_active));
    } catch (err) {
      console.error('Failed to fetch employees:', err);
    }
  };

  const fetchEmployeeData = async () => {
    if (!selectedEmployee) return;
    setLoading(true);
    
    try {
      const [devicesRes, sessionsRes] = await Promise.all([
        api.get(`/api/devices/employee/${selectedEmployee.id}`),
        api.get(`/api/devices/login-sessions/${selectedEmployee.id}?period=${period}`)
      ]);
      
      setEmployeeDevices(devicesRes.data);
      setEmployeeSessions(sessionsRes.data);
      
      // جلب تحليل التلاعب
      try {
        const alertsRes = await api.get(`/api/devices/fraud-analysis/${selectedEmployee.id}`);
        setFraudAlerts(alertsRes.data.alerts || []);
      } catch {
        setFraudAlerts([]);
      }
    } catch (err) {
      console.error('Failed to fetch employee data:', err);
      toast.error(lang === 'ar' ? 'فشل تحميل البيانات' : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // تصفية الموظفين
  const filteredEmployees = useMemo(() => {
    if (!searchQuery) return employees;
    const q = searchQuery.toLowerCase();
    return employees.filter(e => 
      e.full_name_ar?.toLowerCase().includes(q) ||
      e.full_name?.toLowerCase().includes(q) ||
      e.employee_number?.includes(q)
    );
  }, [employees, searchQuery]);

  // === اختيار موظف ===
  const selectEmployee = (emp) => {
    setSelectedEmployee(emp);
    setEmployeeDevices([]);
    setEmployeeSessions([]);
    setFraudAlerts([]);
  };

  // === فتح تفاصيل الجلسة ===
  const openSessionDetails = (session) => {
    setSelectedSession(session);
    setDetailsDialogOpen(true);
  };

  // === تنسيق الوقت ===
  const formatTime = (dateStr) => {
    if (!dateStr) return '--:--';
    return new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
  };

  const formatFullDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    const days = ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
    return `${days[d.getDay()]} ${d.getDate()}/${d.getMonth()+1}/${d.getFullYear()}`;
  };

  // === حساب المدة ===
  const calculateDuration = (loginAt, logoutAt) => {
    if (!loginAt) return '-';
    const login = new Date(loginAt);
    const logout = logoutAt ? new Date(logoutAt) : new Date();
    const diff = Math.floor((logout - login) / 1000 / 60);
    const hours = Math.floor(diff / 60);
    const mins = diff % 60;
    return `${hours}:${mins.toString().padStart(2,'0')}`;
  };

  // === الإحصائيات ===
  const stats = useMemo(() => {
    const totalSessions = employeeSessions.length;
    const uniqueDevices = new Set(employeeSessions.map(s => s.core_signature || s.device_id)).size;
    const totalMinutes = employeeSessions.reduce((acc, s) => {
      if (s.login_at) {
        const login = new Date(s.login_at);
        const logout = s.logout_at ? new Date(s.logout_at) : new Date();
        acc += (logout - login) / 1000 / 60;
      }
      return acc;
    }, 0);
    const criticalAlerts = fraudAlerts.filter(a => a.severity === 'critical').length;
    
    return {
      totalSessions,
      uniqueDevices,
      totalHours: Math.floor(totalMinutes / 60),
      totalMins: Math.round(totalMinutes % 60),
      criticalAlerts
    };
  }, [employeeSessions, fraudAlerts]);

  // === تجميع الجلسات حسب اليوم ===
  const groupedSessions = useMemo(() => {
    const groups = {};
    employeeSessions.forEach(session => {
      const date = formatDate(session.login_at);
      if (!groups[date]) groups[date] = [];
      groups[date].push(session);
    });
    return groups;
  }, [employeeSessions]);

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6 pb-24" data-testid="device-monitoring-page">
      {/* === Header === */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
            <Fingerprint size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? 'مراقبة التسجيل والخروج' : 'Login Monitoring'}
            </h1>
            <p className="text-sm text-slate-500">
              {lang === 'ar' ? 'تتبع الأجهزة وكشف التلاعب' : 'Device tracking & fraud detection'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* === القائمة الجانبية - الموظفين === */}
        <div className="lg:col-span-1">
          <Card className="sticky top-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <User size={18} />
                {lang === 'ar' ? 'الموظفين' : 'Employees'}
              </CardTitle>
              <div className="relative mt-2">
                <Search size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={lang === 'ar' ? 'بحث بالاسم أو الرقم...' : 'Search...'}
                  className="pr-10 text-sm"
                  data-testid="employee-search"
                />
              </div>
            </CardHeader>
            <CardContent className="max-h-[60vh] overflow-y-auto p-2">
              {filteredEmployees.length === 0 ? (
                <p className="text-center text-slate-400 py-4 text-sm">
                  {lang === 'ar' ? 'لا يوجد موظفين' : 'No employees'}
                </p>
              ) : (
                <div className="space-y-1">
                  {filteredEmployees.map(emp => (
                    <button
                      key={emp.id}
                      onClick={() => selectEmployee(emp)}
                      className={`w-full text-right p-3 rounded-lg transition-all ${
                        selectedEmployee?.id === emp.id
                          ? 'bg-indigo-100 border-2 border-indigo-300'
                          : 'hover:bg-slate-100 border-2 border-transparent'
                      }`}
                      data-testid={`select-emp-${emp.employee_number}`}
                    >
                      <p className="font-medium text-slate-800 text-sm">
                        {lang === 'ar' ? emp.full_name_ar : emp.full_name}
                      </p>
                      <p className="text-xs text-slate-500">#{emp.employee_number}</p>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* === المحتوى الرئيسي === */}
        <div className="lg:col-span-3 space-y-4">
          {!selectedEmployee ? (
            <Card className="border-dashed border-2 border-slate-300">
              <CardContent className="py-16 text-center">
                <Fingerprint size={64} className="mx-auto text-slate-300 mb-4" />
                <p className="text-lg text-slate-500">
                  {lang === 'ar' ? 'اختر موظفاً لعرض تفاصيل أجهزته وسجل دخوله' : 'Select an employee to view details'}
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* === شريط معلومات الموظف === */}
              <div className="bg-gradient-to-l from-indigo-600 to-purple-600 rounded-xl p-4 text-white shadow-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center text-2xl font-bold">
                      {selectedEmployee.full_name_ar?.charAt(0) || '?'}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold">{selectedEmployee.full_name_ar}</h2>
                      <p className="text-indigo-200 text-sm">#{selectedEmployee.employee_number}</p>
                    </div>
                  </div>
                  
                  {/* الإحصائيات */}
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <p className="text-3xl font-bold">{stats.totalSessions}</p>
                      <p className="text-xs text-indigo-200">{lang === 'ar' ? 'جلسة' : 'Sessions'}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold">{stats.uniqueDevices}</p>
                      <p className="text-xs text-indigo-200">{lang === 'ar' ? 'جهاز' : 'Devices'}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold">{stats.totalHours}:{stats.totalMins.toString().padStart(2,'0')}</p>
                      <p className="text-xs text-indigo-200">{lang === 'ar' ? 'ساعة' : 'Hours'}</p>
                    </div>
                    {stats.criticalAlerts > 0 && (
                      <div className="text-center bg-red-500 rounded-lg px-3 py-2">
                        <p className="text-2xl font-bold">{stats.criticalAlerts}</p>
                        <p className="text-xs">{lang === 'ar' ? 'تنبيه!' : 'Alert!'}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* === فترة العرض === */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600 mr-2">
                  {lang === 'ar' ? 'الفترة:' : 'Period:'}
                </span>
                {[
                  { value: 'daily', label: lang === 'ar' ? 'يومي' : 'Daily' },
                  { value: 'weekly', label: lang === 'ar' ? 'أسبوعي' : 'Weekly' },
                  { value: 'monthly', label: lang === 'ar' ? 'شهري' : 'Monthly' },
                  { value: 'yearly', label: lang === 'ar' ? 'سنوي' : 'Yearly' },
                ].map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setPeriod(opt.value)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      period === opt.value
                        ? 'bg-indigo-600 text-white shadow'
                        : 'bg-white border text-slate-600 hover:border-indigo-300'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={fetchEmployeeData} 
                  disabled={loading}
                  className="mr-auto"
                >
                  <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                </Button>
              </div>

              {/* === التنبيهات === */}
              {fraudAlerts.length > 0 && (
                <Card className="border-2 border-red-200 bg-red-50">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-red-700 flex items-center gap-2 text-base">
                      <AlertTriangle size={20} />
                      {lang === 'ar' ? 'تنبيهات أمنية' : 'Security Alerts'}
                      <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                        {fraudAlerts.length}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {fraudAlerts.slice(0, 5).map((alert, idx) => (
                      <div 
                        key={idx} 
                        className={`p-3 rounded-lg border-r-4 ${
                          alert.severity === 'critical' ? 'bg-red-100 border-red-500' :
                          alert.severity === 'high' ? 'bg-orange-100 border-orange-500' :
                          'bg-yellow-100 border-yellow-500'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {alert.severity === 'critical' ? (
                            <XCircle size={16} className="text-red-600" />
                          ) : alert.severity === 'high' ? (
                            <AlertCircle size={16} className="text-orange-600" />
                          ) : (
                            <AlertTriangle size={16} className="text-yellow-600" />
                          )}
                          <span className="font-bold text-sm">{alert.title_ar}</span>
                        </div>
                        <p className="text-xs text-slate-600">{alert.message_ar}</p>
                        <p className="text-[10px] text-slate-400 mt-1">{formatFullDate(alert.timestamp)}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              <Tabs defaultValue="sessions" className="w-full">
                <TabsList className="grid w-full grid-cols-2 h-12 mb-4">
                  <TabsTrigger value="sessions" className="flex items-center gap-2">
                    <History size={16} />
                    {lang === 'ar' ? 'سجل الجلسات' : 'Sessions'}
                  </TabsTrigger>
                  <TabsTrigger value="devices" className="flex items-center gap-2">
                    <Smartphone size={16} />
                    {lang === 'ar' ? 'الأجهزة المسجلة' : 'Devices'}
                  </TabsTrigger>
                </TabsList>

                {/* === تبويب الجلسات === */}
                <TabsContent value="sessions">
                  <Card>
                    <CardContent className="p-0">
                      {loading ? (
                        <div className="py-16 text-center">
                          <RefreshCw size={32} className="animate-spin text-indigo-500 mx-auto" />
                        </div>
                      ) : employeeSessions.length === 0 ? (
                        <div className="py-16 text-center">
                          <Clock size={48} className="mx-auto text-slate-300 mb-4" />
                          <p className="text-slate-500">{lang === 'ar' ? 'لا توجد جلسات في هذه الفترة' : 'No sessions'}</p>
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="bg-slate-800 text-white">
                                <th className="p-3 text-right">#</th>
                                <th className="p-3 text-right">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                                <th className="p-3 text-center">{lang === 'ar' ? 'الدخول' : 'Login'}</th>
                                <th className="p-3 text-center">{lang === 'ar' ? 'الخروج' : 'Logout'}</th>
                                <th className="p-3 text-center">{lang === 'ar' ? 'المدة' : 'Duration'}</th>
                                <th className="p-3 text-right">{lang === 'ar' ? 'الجهاز' : 'Device'}</th>
                                <th className="p-3 text-center">{lang === 'ar' ? 'التفاصيل' : 'Details'}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(groupedSessions).map(([date, sessions], gIdx) => (
                                <>
                                  {/* صف التاريخ */}
                                  <tr key={`d-${gIdx}`} className="bg-indigo-50 border-b-2 border-indigo-200">
                                    <td colSpan={7} className="p-2 font-bold text-indigo-700">
                                      <div className="flex items-center gap-2">
                                        <Calendar size={16} />
                                        {formatFullDate(sessions[0]?.login_at)}
                                        <span className="font-normal text-indigo-500 text-xs">
                                          ({sessions.length} {lang === 'ar' ? 'جلسة' : 'sessions'})
                                        </span>
                                      </div>
                                    </td>
                                  </tr>
                                  {/* صفوف الجلسات */}
                                  {sessions.map((s, idx) => (
                                    <tr 
                                      key={s.id} 
                                      className={`border-b hover:bg-slate-50 cursor-pointer ${
                                        s.device_status === 'new_device' ? 'bg-yellow-50' : 
                                        s.status === 'active' ? 'bg-green-50' : ''
                                      }`}
                                      onClick={() => openSessionDetails(s)}
                                    >
                                      <td className="p-3 text-center text-slate-400 font-mono text-xs">{idx + 1}</td>
                                      <td className="p-3 font-medium text-xs">{date}</td>
                                      <td className="p-3 text-center">
                                        <span className="bg-green-100 text-green-700 px-2 py-1 rounded font-mono font-bold text-xs">
                                          {formatTime(s.login_at)}
                                        </span>
                                      </td>
                                      <td className="p-3 text-center">
                                        {s.logout_at ? (
                                          <span className="bg-red-100 text-red-700 px-2 py-1 rounded font-mono font-bold text-xs">
                                            {formatTime(s.logout_at)}
                                          </span>
                                        ) : (
                                          <span className="text-slate-400 text-xs">--:--</span>
                                        )}
                                      </td>
                                      <td className="p-3 text-center font-mono font-bold text-slate-700 text-xs">
                                        {calculateDuration(s.login_at, s.logout_at)}
                                      </td>
                                      <td className="p-3">
                                        <div className="flex items-center gap-2">
                                          <DeviceIcon 
                                            type={s.is_mobile ? 'smartphone' : s.device_type === 'tablet' ? 'tablet' : 'monitor'} 
                                            size={18}
                                            className={s.status === 'active' ? 'text-green-600' : 'text-slate-500'}
                                          />
                                          <div>
                                            <p className="font-medium text-slate-700 text-xs">{s.device_name || 'جهاز'}</p>
                                            <p className="text-[10px] text-slate-500">{s.browser} • {s.os_display || s.os}</p>
                                          </div>
                                        </div>
                                      </td>
                                      <td className="p-3 text-center">
                                        <div className="flex items-center justify-center gap-1">
                                          {s.status === 'active' && (
                                            <span className="bg-green-500 text-white px-2 py-0.5 rounded-full text-[10px] font-bold animate-pulse">
                                              {lang === 'ar' ? 'نشط' : 'Active'}
                                            </span>
                                          )}
                                          {s.device_status === 'new_device' && (
                                            <span className="bg-yellow-500 text-white px-2 py-0.5 rounded-full text-[10px] font-bold">
                                              {lang === 'ar' ? 'جديد' : 'New'}
                                            </span>
                                          )}
                                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                                            <Eye size={12} />
                                          </Button>
                                        </div>
                                      </td>
                                    </tr>
                                  ))}
                                </>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* === تبويب الأجهزة === */}
                <TabsContent value="devices">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {employeeDevices.length === 0 ? (
                      <Card className="col-span-2 border-dashed">
                        <CardContent className="py-12 text-center">
                          <Smartphone size={48} className="mx-auto text-slate-300 mb-4" />
                          <p className="text-slate-500">{lang === 'ar' ? 'لا توجد أجهزة مسجلة' : 'No devices'}</p>
                        </CardContent>
                      </Card>
                    ) : (
                      employeeDevices.map(device => (
                        <Card 
                          key={device.id}
                          className={`border-2 ${
                            device.status === 'trusted' ? 'border-green-200 bg-green-50' :
                            device.status === 'blocked' ? 'border-red-200 bg-red-50' :
                            'border-yellow-200 bg-yellow-50'
                          }`}
                        >
                          <CardContent className="p-4">
                            {/* رأس الكرت */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex items-center gap-3">
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                                  device.status === 'trusted' ? 'bg-green-100' :
                                  device.status === 'blocked' ? 'bg-red-100' : 'bg-yellow-100'
                                }`}>
                                  <DeviceIcon 
                                    type={device.is_mobile ? 'smartphone' : device.is_tablet ? 'tablet' : 'monitor'}
                                    size={24}
                                    className={
                                      device.status === 'trusted' ? 'text-green-600' :
                                      device.status === 'blocked' ? 'text-red-600' : 'text-yellow-600'
                                    }
                                  />
                                </div>
                                <div>
                                  <p className="font-bold text-slate-800">
                                    {device.friendly_name || device.device_name || 'جهاز'}
                                  </p>
                                  <p className="text-xs text-slate-500">
                                    {device.device_brand} {device.device_model}
                                  </p>
                                </div>
                              </div>
                              <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                                device.status === 'trusted' ? 'bg-green-500 text-white' :
                                device.status === 'blocked' ? 'bg-red-500 text-white' :
                                'bg-yellow-500 text-white'
                              }`}>
                                {device.status === 'trusted' ? (lang === 'ar' ? 'موثوق' : 'Trusted') :
                                 device.status === 'blocked' ? (lang === 'ar' ? 'محظور' : 'Blocked') :
                                 (lang === 'ar' ? 'معلق' : 'Pending')}
                              </span>
                            </div>

                            {/* تفاصيل الجهاز */}
                            <div className="space-y-2 text-xs">
                              <div className="flex items-center gap-2 text-slate-600">
                                <Globe size={14} />
                                <span>{device.browser} • {device.os_display || device.os}</span>
                              </div>
                              <div className="flex items-center gap-2 text-slate-600">
                                <Monitor size={14} />
                                <span>{device.screen_resolution || device.fingerprint_data?.screenResolution || '-'}</span>
                              </div>
                              {device.fingerprint_data?.webglRenderer && (
                                <div className="flex items-center gap-2 text-slate-600">
                                  <Cpu size={14} />
                                  <span className="truncate" title={device.fingerprint_data.webglRenderer}>
                                    {device.fingerprint_data.webglRenderer.slice(0, 40)}...
                                  </span>
                                </div>
                              )}
                              <div className="flex items-center gap-2 text-slate-500 pt-2 border-t">
                                <Clock size={14} />
                                <span>{lang === 'ar' ? 'آخر استخدام:' : 'Last used:'} {formatFullDate(device.last_used_at)}</span>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </>
          )}
        </div>
      </div>

      {/* === Dialog تفاصيل الجلسة === */}
      <Dialog open={detailsDialogOpen} onOpenChange={setDetailsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Fingerprint size={20} className="text-indigo-600" />
              {lang === 'ar' ? 'تفاصيل بصمة الجهاز' : 'Device Fingerprint Details'}
            </DialogTitle>
          </DialogHeader>
          
          {selectedSession && (
            <div className="space-y-4">
              {/* معلومات الجلسة */}
              <div className="grid grid-cols-2 gap-3 p-4 bg-slate-50 rounded-lg">
                <div>
                  <p className="text-xs text-slate-500">{lang === 'ar' ? 'وقت الدخول' : 'Login'}</p>
                  <p className="font-bold text-green-600">{formatTime(selectedSession.login_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">{lang === 'ar' ? 'وقت الخروج' : 'Logout'}</p>
                  <p className="font-bold text-red-600">{selectedSession.logout_at ? formatTime(selectedSession.logout_at) : '--:--'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">{lang === 'ar' ? 'التاريخ' : 'Date'}</p>
                  <p className="font-medium">{formatFullDate(selectedSession.login_at)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">{lang === 'ar' ? 'المدة' : 'Duration'}</p>
                  <p className="font-bold">{calculateDuration(selectedSession.login_at, selectedSession.logout_at)}</p>
                </div>
              </div>

              {/* تفاصيل الجهاز */}
              <div className="space-y-3">
                <h3 className="font-bold text-slate-800 flex items-center gap-2">
                  <Smartphone size={18} />
                  {lang === 'ar' ? 'معلومات الجهاز' : 'Device Info'}
                </h3>
                
                <div className="grid grid-cols-2 gap-3">
                  <InfoRow 
                    icon={<DeviceIcon type={selectedSession.is_mobile ? 'smartphone' : 'monitor'} size={16} />}
                    label={lang === 'ar' ? 'الجهاز' : 'Device'}
                    value={selectedSession.device_name || 'غير معروف'}
                  />
                  <InfoRow 
                    icon={<Globe size={16} />}
                    label={lang === 'ar' ? 'المتصفح' : 'Browser'}
                    value={selectedSession.browser || '-'}
                  />
                  <InfoRow 
                    icon={<Monitor size={16} />}
                    label={lang === 'ar' ? 'النظام' : 'OS'}
                    value={selectedSession.os_display || selectedSession.os || '-'}
                  />
                  <InfoRow 
                    icon={<Activity size={16} />}
                    label={lang === 'ar' ? 'الحالة' : 'Status'}
                    value={selectedSession.status === 'active' ? (lang === 'ar' ? 'نشط' : 'Active') : (lang === 'ar' ? 'منتهية' : 'Ended')}
                    valueClass={selectedSession.status === 'active' ? 'text-green-600' : ''}
                  />
                </div>
              </div>

              {/* البصمة التقنية */}
              {selectedSession.fingerprint_data && (
                <div className="space-y-3">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2">
                    <Cpu size={18} />
                    {lang === 'ar' ? 'البصمة التقنية' : 'Technical Fingerprint'}
                  </h3>
                  
                  <div className="bg-slate-900 text-green-400 p-4 rounded-lg font-mono text-xs space-y-1 overflow-x-auto">
                    <p><span className="text-slate-500">// {lang === 'ar' ? 'الشاشة' : 'Screen'}</span></p>
                    <p>resolution: {selectedSession.fingerprint_data.screenResolution || '-'}</p>
                    <p>colorDepth: {selectedSession.fingerprint_data.screenColorDepth || '-'}</p>
                    <p>pixelRatio: {selectedSession.fingerprint_data.devicePixelRatio || '-'}</p>
                    
                    <p className="mt-2"><span className="text-slate-500">// {lang === 'ar' ? 'الأجهزة' : 'Hardware'}</span></p>
                    <p>memory: {selectedSession.fingerprint_data.deviceMemory || '-'} GB</p>
                    <p>cores: {selectedSession.fingerprint_data.hardwareConcurrency || '-'}</p>
                    <p>touchPoints: {selectedSession.fingerprint_data.maxTouchPoints || '-'}</p>
                    
                    <p className="mt-2"><span className="text-slate-500">// GPU</span></p>
                    <p className="break-all">vendor: {selectedSession.fingerprint_data.webglVendor || '-'}</p>
                    <p className="break-all">renderer: {selectedSession.fingerprint_data.webglRenderer || '-'}</p>
                    
                    <p className="mt-2"><span className="text-slate-500">// {lang === 'ar' ? 'البصمات' : 'Signatures'}</span></p>
                    <p>canvas: {selectedSession.fingerprint_data.canvasFingerprint || '-'}</p>
                    <p>core: {selectedSession.core_signature?.slice(0, 32) || '-'}...</p>
                    
                    {selectedSession.fingerprint_data.connectionEffectiveType && (
                      <>
                        <p className="mt-2"><span className="text-slate-500">// {lang === 'ar' ? 'الاتصال' : 'Connection'}</span></p>
                        <p>type: {selectedSession.fingerprint_data.connectionEffectiveType}</p>
                      </>
                    )}
                    
                    <p className="mt-2"><span className="text-slate-500">// {lang === 'ar' ? 'أخرى' : 'Other'}</span></p>
                    <p>timezone: {selectedSession.fingerprint_data.timezone || '-'}</p>
                    <p>language: {selectedSession.fingerprint_data.language || '-'}</p>
                    <p>platform: {selectedSession.fingerprint_data.platform || '-'}</p>
                  </div>
                </div>
              )}

              {/* User Agent الكامل */}
              {selectedSession.fingerprint_data?.userAgent && (
                <div className="space-y-2">
                  <h3 className="font-bold text-slate-800 text-sm">User Agent</h3>
                  <p className="text-xs bg-slate-100 p-3 rounded-lg break-all text-slate-600 font-mono">
                    {selectedSession.fingerprint_data.userAgent}
                  </p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// مكون عرض معلومة
function InfoRow({ icon, label, value, valueClass = '' }) {
  return (
    <div className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg">
      <span className="text-slate-400">{icon}</span>
      <div>
        <p className="text-[10px] text-slate-500">{label}</p>
        <p className={`text-sm font-medium ${valueClass}`}>{value}</p>
      </div>
    </div>
  );
}
