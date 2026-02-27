import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Shield, Search, User, Smartphone, Monitor, Tablet, Laptop,
  Clock, Calendar, AlertTriangle, Eye, RefreshCw, Lock, Unlock,
  Cpu, HardDrive, Wifi, Battery, Activity, Globe, Server,
  CheckCircle, XCircle, History, Fingerprint, Signal, Zap
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// Parse User Agent to get device info
const parseUserAgent = (ua) => {
  if (!ua) return { device: 'Unknown', os: '', browser: '', deviceType: 'desktop' };
  
  const uaLower = ua.toLowerCase();
  
  // Device Detection
  let device = '';
  let deviceType = 'desktop';
  let os = '';
  let browser = '';
  
  // iPhone Detection
  if (uaLower.includes('iphone')) {
    deviceType = 'mobile';
    os = 'iOS';
    
    // Try to detect iPhone model from screen or UA
    if (uaLower.includes('iphone14') || ua.includes('iPhone14')) device = 'iPhone 14';
    else if (uaLower.includes('iphone15') || ua.includes('iPhone15')) device = 'iPhone 15';
    else if (uaLower.includes('iphone13') || ua.includes('iPhone13')) device = 'iPhone 13';
    else if (uaLower.includes('iphone12') || ua.includes('iPhone12')) device = 'iPhone 12';
    else device = 'iPhone';
    
    // iOS Version
    const iosMatch = ua.match(/iPhone OS (\d+)_(\d+)/);
    if (iosMatch) os = `iOS ${iosMatch[1]}.${iosMatch[2]}`;
  }
  // iPad Detection
  else if (uaLower.includes('ipad') || (uaLower.includes('macintosh') && 'ontouchend' in document)) {
    deviceType = 'tablet';
    device = 'iPad';
    os = 'iPadOS';
  }
  // Mac Detection
  else if (uaLower.includes('macintosh') || uaLower.includes('mac os')) {
    deviceType = 'desktop';
    device = 'Mac';
    os = 'macOS';
    const macMatch = ua.match(/Mac OS X (\d+)[_.](\d+)/);
    if (macMatch) os = `macOS ${macMatch[1]}.${macMatch[2]}`;
  }
  // Android Detection
  else if (uaLower.includes('android')) {
    os = 'Android';
    const androidMatch = ua.match(/Android\s*(\d+\.?\d*)/i);
    if (androidMatch) os = `Android ${androidMatch[1]}`;
    
    // Samsung
    if (uaLower.includes('samsung') || uaLower.includes('sm-')) {
      deviceType = 'mobile';
      if (uaLower.includes('sm-s9') || uaLower.includes('s24')) device = 'Samsung Galaxy S24';
      else if (uaLower.includes('sm-s9') || uaLower.includes('s23')) device = 'Samsung Galaxy S23';
      else if (uaLower.includes('sm-a')) device = 'Samsung Galaxy A';
      else if (uaLower.includes('sm-t') || uaLower.includes('tab')) {
        device = 'Samsung Galaxy Tab';
        deviceType = 'tablet';
      }
      else device = 'Samsung Galaxy';
    }
    // Huawei
    else if (uaLower.includes('huawei') || uaLower.includes('honor')) {
      deviceType = 'mobile';
      device = 'Huawei';
    }
    // Xiaomi
    else if (uaLower.includes('xiaomi') || uaLower.includes('redmi') || uaLower.includes('poco')) {
      deviceType = 'mobile';
      if (uaLower.includes('redmi note')) device = 'Redmi Note';
      else if (uaLower.includes('redmi')) device = 'Redmi';
      else if (uaLower.includes('poco')) device = 'Poco';
      else device = 'Xiaomi';
    }
    // Generic Android
    else {
      deviceType = uaLower.includes('mobile') ? 'mobile' : 'tablet';
      const modelMatch = ua.match(/;\s*([^;)]+)\s*Build/i);
      device = modelMatch ? modelMatch[1].trim() : 'Android Device';
    }
  }
  // Windows Detection
  else if (uaLower.includes('windows')) {
    deviceType = 'desktop';
    device = 'Windows PC';
    const winMatch = ua.match(/Windows NT (\d+\.?\d*)/);
    if (winMatch) {
      const ver = parseFloat(winMatch[1]);
      if (ver >= 10) os = 'Windows 10/11';
      else if (ver >= 6.3) os = 'Windows 8.1';
      else if (ver >= 6.1) os = 'Windows 7';
      else os = 'Windows';
    }
  }
  // Linux Detection
  else if (uaLower.includes('linux') && !uaLower.includes('android')) {
    deviceType = 'desktop';
    device = 'Linux PC';
    os = 'Linux';
  }
  
  // Browser Detection
  if (uaLower.includes('edg/') || uaLower.includes('edge')) browser = 'Edge';
  else if (uaLower.includes('opr/') || uaLower.includes('opera')) browser = 'Opera';
  else if (uaLower.includes('samsungbrowser')) browser = 'Samsung Browser';
  else if (uaLower.includes('firefox')) browser = 'Firefox';
  else if (uaLower.includes('chrome')) browser = 'Chrome';
  else if (uaLower.includes('safari') && !uaLower.includes('chrome')) browser = 'Safari';
  else browser = 'Unknown';
  
  return { device, os, browser, deviceType };
};

// Device Icon Component
const DeviceIcon = ({ type, size = 24, className = '' }) => {
  const icons = {
    smartphone: Smartphone,
    mobile: Smartphone,
    tablet: Tablet,
    laptop: Laptop,
    desktop: Monitor,
    default: Monitor
  };
  const Icon = icons[type] || icons.default;
  return <Icon size={size} className={className} />;
};

export default function DeviceMonitoringPage() {
  const { lang } = useLanguage();
  
  // State
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Employee Data
  const [employeeDevices, setEmployeeDevices] = useState([]);
  const [employeeSessions, setEmployeeSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  
  // Period filter
  const [period, setPeriod] = useState('monthly');

  // Fetch employees
  useEffect(() => {
    fetchEmployees();
  }, []);

  // Fetch employee data when selected
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
      
      // Process sessions to add device info
      const processedSessions = sessionsRes.data.map(session => {
        const fp = session.fingerprint_data || {};
        const ua = fp.userAgent || session.user_agent || '';
        const parsed = parseUserAgent(ua);
        
        // Use advanced fingerprint data if available
        let deviceName = fp.deviceModel || fp.deviceBrand || parsed.device;
        let osDisplay = fp.osName ? `${fp.osName} ${fp.osVersion || ''}` : parsed.os;
        let browserDisplay = fp.browserName ? `${fp.browserName} ${fp.browserVersion || ''}` : parsed.browser;
        
        // Screen info
        let screenInfo = fp.screenResolution || '';
        
        // GPU info
        let gpuInfo = fp.webglRenderer || '';
        if (gpuInfo && gpuInfo.length > 50) gpuInfo = gpuInfo.substring(0, 50) + '...';
        
        return {
          ...session,
          deviceName: deviceName || 'Unknown Device',
          osDisplay: osDisplay || 'Unknown OS',
          browserDisplay: browserDisplay || 'Unknown',
          deviceType: fp.deviceType || parsed.deviceType || 'desktop',
          screenInfo,
          gpuInfo,
          cpuCores: fp.hardwareConcurrency || '',
          memory: fp.deviceMemory ? `${fp.deviceMemory} GB` : '',
          connectionType: fp.connectionEffectiveType || ''
        };
      });
      
      setEmployeeSessions(processedSessions);
    } catch (err) {
      console.error('Failed to fetch employee data:', err);
      toast.error('فشل تحميل البيانات');
    } finally {
      setLoading(false);
    }
  };

  // Filter employees
  const filteredEmployees = useMemo(() => {
    if (!searchQuery) return employees;
    const q = searchQuery.toLowerCase();
    return employees.filter(e => 
      e.full_name_ar?.toLowerCase().includes(q) ||
      e.full_name?.toLowerCase().includes(q) ||
      e.employee_number?.includes(q)
    );
  }, [employees, searchQuery]);

  // Select employee
  const selectEmployee = (emp) => {
    setSelectedEmployee(emp);
    setEmployeeDevices([]);
    setEmployeeSessions([]);
  };

  // View session details
  const viewSessionDetails = (session) => {
    setSelectedSession(session);
    setDetailsOpen(true);
  };

  // Format time
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

  // Calculate duration
  const calculateDuration = (loginAt, logoutAt) => {
    if (!loginAt) return '-';
    const login = new Date(loginAt);
    const logout = logoutAt ? new Date(logoutAt) : new Date();
    const diff = Math.floor((logout - login) / 1000 / 60);
    const hours = Math.floor(diff / 60);
    const mins = diff % 60;
    return `${hours}:${mins.toString().padStart(2,'0')}`;
  };

  // Stats
  const stats = useMemo(() => {
    const totalSessions = employeeSessions.length;
    const uniqueDevices = new Set(employeeSessions.map(s => s.core_signature || s.device_id)).size;
    const activeSessions = employeeSessions.filter(s => s.status === 'active').length;
    
    return { totalSessions, uniqueDevices, activeSessions };
  }, [employeeSessions]);

  // Group sessions by date
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
    <div className="min-h-screen bg-slate-100" data-testid="device-monitoring-page">
      {/* Header */}
      <div className="bg-slate-900 text-white p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/10 backdrop-blur flex items-center justify-center">
              <Fingerprint size={28} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">مراقبة الأجهزة</h1>
              <p className="text-slate-400 text-sm">تتبع الأجهزة وسجل الدخول والخروج</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - Employees */}
          <div className="lg:col-span-1">
            <Card className="sticky top-6 border-0 shadow-lg">
              <CardHeader className="pb-3 bg-slate-50 rounded-t-xl">
                <CardTitle className="text-base flex items-center gap-2 text-slate-700">
                  <User size={18} />
                  الموظفين
                </CardTitle>
                <div className="relative mt-3">
                  <Search size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="بحث..."
                    className="pr-10 text-sm bg-white border-slate-200"
                  />
                </div>
              </CardHeader>
              <CardContent className="max-h-[60vh] overflow-y-auto p-2">
                {filteredEmployees.length === 0 ? (
                  <p className="text-center text-slate-400 py-8 text-sm">لا يوجد موظفين</p>
                ) : (
                  <div className="space-y-1">
                    {filteredEmployees.map(emp => (
                      <button
                        key={emp.id}
                        onClick={() => selectEmployee(emp)}
                        className={`w-full text-right p-3 rounded-xl transition-all ${
                          selectedEmployee?.id === emp.id
                            ? 'bg-slate-900 text-white'
                            : 'hover:bg-slate-100'
                        }`}
                      >
                        <p className="font-semibold text-sm">{emp.full_name_ar}</p>
                        <p className={`text-xs ${selectedEmployee?.id === emp.id ? 'text-slate-400' : 'text-slate-500'}`}>
                          #{emp.employee_number}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            {!selectedEmployee ? (
              <Card className="border-2 border-dashed border-slate-300 bg-white/50">
                <CardContent className="py-20 text-center">
                  <div className="w-20 h-20 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
                    <Fingerprint size={40} className="text-slate-400" />
                  </div>
                  <p className="text-lg text-slate-500">اختر موظفاً لعرض تفاصيل أجهزته</p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Employee Header */}
                <Card className="border-0 shadow-lg overflow-hidden">
                  <div className="bg-gradient-to-l from-slate-900 to-slate-800 p-6 text-white">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center text-2xl font-bold">
                          {selectedEmployee.full_name_ar?.charAt(0)}
                        </div>
                        <div>
                          <h2 className="text-xl font-bold">{selectedEmployee.full_name_ar}</h2>
                          <p className="text-slate-400">#{selectedEmployee.employee_number}</p>
                        </div>
                      </div>
                      
                      {/* Stats */}
                      <div className="flex items-center gap-8">
                        <div className="text-center">
                          <p className="text-3xl font-bold">{stats.totalSessions}</p>
                          <p className="text-xs text-slate-400">جلسة</p>
                        </div>
                        <div className="text-center">
                          <p className="text-3xl font-bold">{stats.uniqueDevices}</p>
                          <p className="text-xs text-slate-400">جهاز</p>
                        </div>
                        <div className="text-center">
                          <p className="text-3xl font-bold text-green-400">{stats.activeSessions}</p>
                          <p className="text-xs text-slate-400">نشط</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Period Filter */}
                <div className="flex items-center gap-2 bg-white p-2 rounded-xl shadow">
                  <span className="text-sm text-slate-600 px-2">الفترة:</span>
                  {[
                    { value: 'daily', label: 'اليوم' },
                    { value: 'weekly', label: 'أسبوع' },
                    { value: 'monthly', label: 'شهر' },
                    { value: 'yearly', label: 'سنة' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => setPeriod(opt.value)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                        period === opt.value
                          ? 'bg-slate-900 text-white'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={fetchEmployeeData} 
                    disabled={loading}
                    className="mr-auto"
                  >
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                  </Button>
                </div>

                {/* Sessions Table */}
                <Card className="border-0 shadow-lg overflow-hidden">
                  <CardHeader className="bg-slate-50 border-b">
                    <CardTitle className="text-base flex items-center gap-2">
                      <History size={18} />
                      سجل الجلسات
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {loading ? (
                      <div className="py-20 text-center">
                        <RefreshCw size={32} className="animate-spin text-slate-400 mx-auto" />
                      </div>
                    ) : employeeSessions.length === 0 ? (
                      <div className="py-20 text-center">
                        <Clock size={48} className="mx-auto text-slate-300 mb-4" />
                        <p className="text-slate-500">لا توجد جلسات في هذه الفترة</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="bg-slate-800 text-white text-xs">
                              <th className="p-3 text-right font-medium">التاريخ</th>
                              <th className="p-3 text-center font-medium">الدخول</th>
                              <th className="p-3 text-center font-medium">الخروج</th>
                              <th className="p-3 text-center font-medium">المدة</th>
                              <th className="p-3 text-right font-medium">الجهاز</th>
                              <th className="p-3 text-right font-medium">النظام</th>
                              <th className="p-3 text-center font-medium">الحالة</th>
                              <th className="p-3 text-center font-medium w-16"></th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(groupedSessions).map(([date, sessions]) => (
                              <>
                                {/* Date Header */}
                                <tr key={`d-${date}`} className="bg-slate-100">
                                  <td colSpan={8} className="p-2">
                                    <div className="flex items-center gap-2 text-slate-600 font-medium text-xs">
                                      <Calendar size={14} />
                                      {formatFullDate(sessions[0]?.login_at)}
                                      <span className="text-slate-400">({sessions.length} جلسة)</span>
                                    </div>
                                  </td>
                                </tr>
                                {/* Session Rows */}
                                {sessions.map((s) => (
                                  <tr 
                                    key={s.id} 
                                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                                    onClick={() => viewSessionDetails(s)}
                                  >
                                    <td className="p-3 text-xs text-slate-500">{date}</td>
                                    <td className="p-3 text-center">
                                      <span className="bg-green-100 text-green-700 px-2 py-1 rounded font-mono text-xs font-bold">
                                        {formatTime(s.login_at)}
                                      </span>
                                    </td>
                                    <td className="p-3 text-center">
                                      {s.logout_at ? (
                                        <span className="bg-red-100 text-red-700 px-2 py-1 rounded font-mono text-xs font-bold">
                                          {formatTime(s.logout_at)}
                                        </span>
                                      ) : (
                                        <span className="text-slate-400 text-xs">--:--</span>
                                      )}
                                    </td>
                                    <td className="p-3 text-center font-mono text-xs font-bold text-slate-700">
                                      {calculateDuration(s.login_at, s.logout_at)}
                                    </td>
                                    <td className="p-3">
                                      <div className="flex items-center gap-2">
                                        <DeviceIcon 
                                          type={s.deviceType} 
                                          size={16}
                                          className={s.status === 'active' ? 'text-green-600' : 'text-slate-500'}
                                        />
                                        <span className="text-xs font-medium text-slate-700">{s.deviceName}</span>
                                      </div>
                                    </td>
                                    <td className="p-3">
                                      <div className="text-xs">
                                        <p className="text-slate-600">{s.osDisplay}</p>
                                        <p className="text-slate-400">{s.browserDisplay}</p>
                                      </div>
                                    </td>
                                    <td className="p-3 text-center">
                                      {s.status === 'active' ? (
                                        <span className="inline-flex items-center gap-1 bg-green-500 text-white px-2 py-0.5 rounded-full text-[10px] font-bold">
                                          <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span>
                                          نشط
                                        </span>
                                      ) : s.status === 'force_logout' ? (
                                        <span className="bg-red-100 text-red-600 px-2 py-0.5 rounded-full text-[10px] font-bold">
                                          إجباري
                                        </span>
                                      ) : (
                                        <span className="bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full text-[10px]">
                                          منتهية
                                        </span>
                                      )}
                                    </td>
                                    <td className="p-3 text-center">
                                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                        <Eye size={14} className="text-slate-400" />
                                      </Button>
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

                {/* Devices Grid */}
                <Card className="border-0 shadow-lg">
                  <CardHeader className="bg-slate-50 border-b">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Smartphone size={18} />
                      الأجهزة المسجلة
                      <span className="text-xs bg-slate-200 px-2 py-0.5 rounded-full text-slate-600">
                        {employeeDevices.length}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {employeeDevices.length === 0 ? (
                      <div className="text-center py-12 text-slate-500">
                        <Smartphone size={40} className="mx-auto mb-3 text-slate-300" />
                        <p>لا توجد أجهزة مسجلة</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {employeeDevices.map(device => {
                          const fp = device.fingerprint_data || {};
                          const parsed = parseUserAgent(fp.userAgent || device.user_agent || '');
                          
                          return (
                            <div 
                              key={device.id}
                              className={`p-4 rounded-xl border-2 transition-all ${
                                device.status === 'trusted' ? 'border-green-200 bg-green-50/50' :
                                device.status === 'blocked' ? 'border-red-200 bg-red-50/50' :
                                'border-yellow-200 bg-yellow-50/50'
                              }`}
                            >
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-3">
                                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                                    device.status === 'trusted' ? 'bg-green-100' :
                                    device.status === 'blocked' ? 'bg-red-100' : 'bg-yellow-100'
                                  }`}>
                                    <DeviceIcon 
                                      type={fp.deviceType || parsed.deviceType || 'desktop'} 
                                      size={24}
                                      className={
                                        device.status === 'trusted' ? 'text-green-600' :
                                        device.status === 'blocked' ? 'text-red-600' : 'text-yellow-600'
                                      }
                                    />
                                  </div>
                                  <div>
                                    <p className="font-bold text-slate-800">
                                      {fp.deviceModel || fp.deviceBrand || parsed.device || device.friendly_name || 'جهاز'}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                      {fp.osName || parsed.os || device.os} - {fp.browserName || parsed.browser || device.browser}
                                    </p>
                                  </div>
                                </div>
                                <span className={`px-2 py-1 rounded-lg text-xs font-bold ${
                                  device.status === 'trusted' ? 'bg-green-500 text-white' :
                                  device.status === 'blocked' ? 'bg-red-500 text-white' :
                                  'bg-yellow-500 text-white'
                                }`}>
                                  {device.status === 'trusted' ? 'موثوق' :
                                   device.status === 'blocked' ? 'محظور' : 'معلق'}
                                </span>
                              </div>
                              
                              {/* Device Specs */}
                              <div className="space-y-2 text-xs border-t pt-3">
                                {(fp.screenResolution || device.screen_resolution) && (
                                  <div className="flex items-center gap-2 text-slate-600">
                                    <Monitor size={12} />
                                    <span>الشاشة: {fp.screenResolution || device.screen_resolution}</span>
                                  </div>
                                )}
                                {(fp.webglRenderer) && (
                                  <div className="flex items-center gap-2 text-slate-600">
                                    <Cpu size={12} />
                                    <span className="truncate">GPU: {fp.webglRenderer.substring(0, 35)}...</span>
                                  </div>
                                )}
                                {(fp.hardwareConcurrency) && (
                                  <div className="flex items-center gap-2 text-slate-600">
                                    <Server size={12} />
                                    <span>المعالج: {fp.hardwareConcurrency} أنوية</span>
                                  </div>
                                )}
                                <div className="flex items-center gap-2 text-slate-400 pt-2 border-t">
                                  <Clock size={12} />
                                  <span>آخر استخدام: {formatFullDate(device.last_used_at)}</span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Session Details Dialog */}
      <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-slate-800">
              <Fingerprint size={20} />
              تفاصيل الجلسة وبصمة الجهاز
            </DialogTitle>
          </DialogHeader>
          
          {selectedSession && (
            <div className="space-y-6">
              {/* Session Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <InfoBox label="الدخول" value={formatTime(selectedSession.login_at)} color="green" />
                <InfoBox label="الخروج" value={selectedSession.logout_at ? formatTime(selectedSession.logout_at) : '--:--'} color="red" />
                <InfoBox label="المدة" value={calculateDuration(selectedSession.login_at, selectedSession.logout_at)} />
                <InfoBox 
                  label="الحالة" 
                  value={selectedSession.status === 'active' ? 'نشط' : 'منتهية'} 
                  color={selectedSession.status === 'active' ? 'green' : 'gray'}
                />
              </div>

              {/* Device Info */}
              <div className="bg-slate-50 rounded-xl p-4">
                <h3 className="font-bold text-slate-800 mb-3 flex items-center gap-2">
                  <DeviceIcon type={selectedSession.deviceType} size={18} />
                  معلومات الجهاز
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500 text-xs">الجهاز</p>
                    <p className="font-semibold text-slate-800">{selectedSession.deviceName}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">نظام التشغيل</p>
                    <p className="font-semibold text-slate-800">{selectedSession.osDisplay}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">المتصفح</p>
                    <p className="font-semibold text-slate-800">{selectedSession.browserDisplay}</p>
                  </div>
                  <div>
                    <p className="text-slate-500 text-xs">نوع الاتصال</p>
                    <p className="font-semibold text-slate-800">{selectedSession.connectionType || 'غير محدد'}</p>
                  </div>
                </div>
              </div>

              {/* Technical Fingerprint */}
              {selectedSession.fingerprint_data && (
                <div className="bg-slate-900 rounded-xl p-4 text-green-400 font-mono text-xs overflow-x-auto">
                  <p className="text-slate-500 mb-2">// البصمة التقنية</p>
                  <p>screen: {selectedSession.fingerprint_data.screenResolution || '-'}</p>
                  <p>memory: {selectedSession.fingerprint_data.deviceMemory || '-'} GB</p>
                  <p>cores: {selectedSession.fingerprint_data.hardwareConcurrency || '-'}</p>
                  <p>gpu: {selectedSession.fingerprint_data.webglRenderer || '-'}</p>
                  <p>canvas: {selectedSession.fingerprint_data.canvasFingerprint?.substring(0, 20) || '-'}...</p>
                  <p>platform: {selectedSession.fingerprint_data.platform || '-'}</p>
                  <p>timezone: {selectedSession.fingerprint_data.timezone || '-'}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Info Box Component
function InfoBox({ label, value, color = 'slate' }) {
  const colors = {
    green: 'bg-green-50 border-green-200',
    red: 'bg-red-50 border-red-200',
    gray: 'bg-slate-50 border-slate-200',
    slate: 'bg-slate-50 border-slate-200'
  };
  
  return (
    <div className={`p-3 rounded-lg border ${colors[color]}`}>
      <p className="text-[10px] text-slate-500 uppercase">{label}</p>
      <p className="text-lg font-bold text-slate-800">{value}</p>
    </div>
  );
}
