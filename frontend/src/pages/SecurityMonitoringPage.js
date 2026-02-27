import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Shield, ShieldAlert, ShieldCheck, ShieldX, ShieldOff,
  Search, User, Users, Smartphone, Monitor, Tablet, Laptop,
  Clock, Calendar, AlertTriangle, AlertCircle, AlertOctagon,
  Eye, EyeOff, RefreshCw, Download, Lock, Unlock, LogOut,
  Cpu, HardDrive, Wifi, WifiOff, Battery, Activity, Globe,
  CheckCircle, XCircle, Ban, History, FileText, Filter,
  ChevronDown, ChevronUp, MoreVertical, Fingerprint, Server,
  Zap, Radio, Signal, MapPin
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// Device Icon Component
const DeviceIcon = ({ type, size = 20, className = '' }) => {
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

// Severity Badge Component
const SeverityBadge = ({ severity }) => {
  const config = {
    critical: { bg: 'bg-red-600', text: 'text-white', label: 'حرج' },
    high: { bg: 'bg-orange-500', text: 'text-white', label: 'عالي' },
    medium: { bg: 'bg-yellow-500', text: 'text-white', label: 'متوسط' },
    low: { bg: 'bg-blue-500', text: 'text-white', label: 'منخفض' }
  };
  const c = config[severity] || config.medium;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
};

export default function SecurityMonitoringPage() {
  const { lang } = useLanguage();
  
  // State
  const [employees, setEmployees] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Stats
  const [stats, setStats] = useState({
    active_sessions: 0,
    suspended_accounts: 0,
    blocked_devices: 0,
    logins_today: 0,
    alerts_today: 0,
    new_devices_today: 0
  });
  
  // Data
  const [fraudAlerts, setFraudAlerts] = useState([]);
  const [suspendedAccounts, setSuspendedAccounts] = useState([]);
  const [securityLog, setSecurityLog] = useState([]);
  const [employeeDetails, setEmployeeDetails] = useState(null);
  
  // Dialogs
  const [suspendDialogOpen, setSuspendDialogOpen] = useState(false);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [suspendReason, setSuspendReason] = useState('');
  const [suspendDuration, setSuspendDuration] = useState('');

  // Fetch data
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [empRes, statsRes, alertsRes, suspendedRes, logRes] = await Promise.all([
        api.get('/api/employees'),
        api.get('/api/security/stats'),
        api.get('/api/security/fraud-alerts'),
        api.get('/api/security/suspended-accounts'),
        api.get('/api/security/security-log?limit=30')
      ]);
      
      setEmployees(empRes.data.filter(e => e.is_active));
      setStats(statsRes.data);
      setFraudAlerts(alertsRes.data);
      setSuspendedAccounts(suspendedRes.data);
      setSecurityLog(logRes.data);
    } catch (err) {
      console.error('Error fetching security data:', err);
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

  // Toggle employee selection
  const toggleEmployee = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  // Select all filtered employees
  const selectAll = () => {
    if (selectedEmployees.length === filteredEmployees.length) {
      setSelectedEmployees([]);
    } else {
      setSelectedEmployees(filteredEmployees.map(e => e.id));
    }
  };

  // Suspend accounts
  const handleSuspend = async () => {
    if (selectedEmployees.length === 0) {
      toast.error('اختر موظفاً واحداً على الأقل');
      return;
    }
    if (!suspendReason.trim()) {
      toast.error('أدخل سبب التعطيل');
      return;
    }
    
    try {
      const res = await api.post('/api/security/suspend-accounts', {
        employee_ids: selectedEmployees,
        reason: suspendReason,
        duration_hours: suspendDuration ? parseInt(suspendDuration) : null
      });
      
      toast.success(res.data.message_ar);
      setSuspendDialogOpen(false);
      setSuspendReason('');
      setSuspendDuration('');
      setSelectedEmployees([]);
      fetchData();
    } catch (err) {
      toast.error('فشل تعطيل الحسابات');
    }
  };

  // Unblock accounts
  const handleUnblock = async (empIds, reason = 'تم التحقق والسماح بالدخول') => {
    try {
      const res = await api.post('/api/security/unblock-accounts', {
        employee_ids: Array.isArray(empIds) ? empIds : [empIds],
        reason
      });
      toast.success(res.data.message_ar);
      fetchData();
    } catch (err) {
      toast.error('فشل إلغاء التعطيل');
    }
  };

  // Force logout
  const handleForceLogout = async (empId) => {
    try {
      const res = await api.post(`/api/security/force-logout/${empId}`);
      toast.success(res.data.message_ar);
      fetchData();
    } catch (err) {
      toast.error('فشل تسجيل الخروج الإجباري');
    }
  };

  // View employee details
  const viewEmployeeDetails = async (empId) => {
    try {
      const res = await api.get(`/api/security/device-usage/${empId}`);
      setEmployeeDetails(res.data);
      setDetailsDialogOpen(true);
    } catch (err) {
      toast.error('فشل جلب التفاصيل');
    }
  };

  // Format time
  const formatTime = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-SA');
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return `${d.toLocaleDateString('ar-SA')} ${d.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}`;
  };

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6" data-testid="security-monitoring-page">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-slate-900 flex items-center justify-center shadow-lg">
              <Shield size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">مركز الأمان</h1>
              <p className="text-sm text-slate-500">مراقبة الأجهزة وإدارة الحسابات</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={`ml-2 ${loading ? 'animate-spin' : ''}`} />
            تحديث
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <StatCard 
          icon={<Activity size={20} />}
          label="جلسات نشطة"
          value={stats.active_sessions}
          color="bg-green-500"
        />
        <StatCard 
          icon={<ShieldOff size={20} />}
          label="حسابات معطلة"
          value={stats.suspended_accounts}
          color="bg-red-500"
        />
        <StatCard 
          icon={<Ban size={20} />}
          label="أجهزة محظورة"
          value={stats.blocked_devices}
          color="bg-orange-500"
        />
        <StatCard 
          icon={<LogOut size={20} />}
          label="دخول اليوم"
          value={stats.logins_today}
          color="bg-blue-500"
        />
        <StatCard 
          icon={<AlertTriangle size={20} />}
          label="تنبيهات"
          value={stats.alerts_today}
          color="bg-yellow-500"
        />
        <StatCard 
          icon={<Smartphone size={20} />}
          label="أجهزة جديدة"
          value={stats.new_devices_today}
          color="bg-purple-500"
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Employee Selection */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Users size={18} />
                  الموظفين
                </span>
                {selectedEmployees.length > 0 && (
                  <span className="text-xs bg-slate-900 text-white px-2 py-1 rounded-full">
                    {selectedEmployees.length} محدد
                  </span>
                )}
              </CardTitle>
              
              {/* Search */}
              <div className="relative mt-2">
                <Search size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="بحث بالاسم أو الرقم..."
                  className="pr-10 text-sm"
                />
              </div>
              
              {/* Select All */}
              <div className="flex items-center gap-2 mt-2 pt-2 border-t">
                <Checkbox 
                  checked={selectedEmployees.length === filteredEmployees.length && filteredEmployees.length > 0}
                  onCheckedChange={selectAll}
                />
                <span className="text-sm text-slate-600">تحديد الكل</span>
              </div>
            </CardHeader>
            
            <CardContent className="max-h-[400px] overflow-y-auto p-2 pt-0">
              <div className="space-y-1">
                {filteredEmployees.map(emp => {
                  const isSuspended = suspendedAccounts.some(s => s.employee_id === emp.id);
                  return (
                    <div
                      key={emp.id}
                      className={`flex items-center gap-3 p-3 rounded-lg transition-all cursor-pointer ${
                        selectedEmployees.includes(emp.id)
                          ? 'bg-slate-900 text-white'
                          : isSuspended
                            ? 'bg-red-50 border border-red-200'
                            : 'hover:bg-slate-50 border border-transparent'
                      }`}
                      onClick={() => toggleEmployee(emp.id)}
                    >
                      <Checkbox 
                        checked={selectedEmployees.includes(emp.id)}
                        className={selectedEmployees.includes(emp.id) ? 'border-white' : ''}
                      />
                      <div className="flex-1 min-w-0">
                        <p className={`font-medium text-sm truncate ${selectedEmployees.includes(emp.id) ? 'text-white' : 'text-slate-800'}`}>
                          {emp.full_name_ar}
                        </p>
                        <p className={`text-xs ${selectedEmployees.includes(emp.id) ? 'text-slate-300' : 'text-slate-500'}`}>
                          #{emp.employee_number}
                        </p>
                      </div>
                      {isSuspended && (
                        <ShieldX size={16} className="text-red-500" />
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          viewEmployeeDetails(emp.id);
                        }}
                      >
                        <Eye size={14} />
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>

            {/* Actions */}
            {selectedEmployees.length > 0 && (
              <div className="p-3 border-t bg-slate-50 space-y-2">
                <Button 
                  className="w-full bg-red-600 hover:bg-red-700"
                  onClick={() => setSuspendDialogOpen(true)}
                >
                  <Lock size={16} className="ml-2" />
                  تعطيل الحسابات ({selectedEmployees.length})
                </Button>
                <Button 
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    selectedEmployees.forEach(id => handleForceLogout(id));
                  }}
                >
                  <LogOut size={16} className="ml-2" />
                  تسجيل خروج إجباري
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Right Panel - Alerts & Logs */}
        <div className="lg:col-span-2 space-y-6">
          {/* Fraud Alerts */}
          {fraudAlerts.length > 0 && (
            <Card className="border-2 border-red-200 bg-red-50/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2 text-red-700">
                  <AlertOctagon size={20} />
                  تنبيهات التلاعب
                  <span className="bg-red-600 text-white text-xs px-2 py-0.5 rounded-full">
                    {fraudAlerts.length}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {fraudAlerts.map(alert => (
                  <div 
                    key={alert.id}
                    className={`p-4 rounded-lg border-r-4 bg-white ${
                      alert.severity === 'critical' ? 'border-red-600' :
                      alert.severity === 'high' ? 'border-orange-500' :
                      'border-yellow-500'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        {alert.type === 'shared_device' ? (
                          <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                            <Users size={20} className="text-red-600" />
                          </div>
                        ) : (
                          <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                            <Smartphone size={20} className="text-orange-600" />
                          </div>
                        )}
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-bold text-slate-800">{alert.title_ar}</span>
                            <SeverityBadge severity={alert.severity} />
                          </div>
                          <p className="text-sm text-slate-600">{alert.message_ar}</p>
                          {alert.employee_names && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {alert.employee_names.map((name, i) => (
                                <span key={i} className="text-xs bg-slate-100 px-2 py-0.5 rounded">
                                  {name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="destructive" onClick={() => {
                          if (alert.employees) {
                            setSuspendReason(`تلاعب: ${alert.title_ar}`);
                            setSelectedEmployees(alert.employees);
                            setSuspendDialogOpen(true);
                          }
                        }}>
                          <Lock size={14} className="ml-1" />
                          تعطيل
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Suspended Accounts */}
          {suspendedAccounts.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldOff size={18} />
                  الحسابات المعطلة
                  <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                    {suspendedAccounts.length}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {suspendedAccounts.map(acc => (
                    <div 
                      key={acc.id}
                      className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                          <User size={20} className="text-red-600" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">{acc.employee_name_ar || acc.username}</p>
                          <p className="text-xs text-slate-500">
                            السبب: {acc.suspend_reason || 'غير محدد'}
                          </p>
                          {acc.suspended_until && (
                            <p className="text-xs text-orange-600">
                              ينتهي: {formatDateTime(acc.suspended_until)}
                            </p>
                          )}
                        </div>
                      </div>
                      <Button 
                        size="sm" 
                        variant="outline"
                        className="border-green-300 text-green-700 hover:bg-green-50"
                        onClick={() => handleUnblock(acc.employee_id)}
                      >
                        <Unlock size={14} className="ml-1" />
                        إلغاء التعطيل
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Security Log */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <History size={18} />
                سجل الأمان
              </CardTitle>
            </CardHeader>
            <CardContent>
              {securityLog.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <FileText size={40} className="mx-auto mb-2 opacity-30" />
                  <p>لا توجد سجلات</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {securityLog.map(log => (
                    <div 
                      key={log.id}
                      className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg text-sm"
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        log.action.includes('suspend') || log.action.includes('block') 
                          ? 'bg-red-100 text-red-600'
                          : log.action.includes('unblock') 
                            ? 'bg-green-100 text-green-600'
                            : 'bg-blue-100 text-blue-600'
                      }`}>
                        {log.action.includes('suspend') || log.action.includes('block') ? (
                          <Lock size={16} />
                        ) : log.action.includes('unblock') ? (
                          <Unlock size={16} />
                        ) : (
                          <Activity size={16} />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-800">
                          {log.action === 'account_suspended' ? 'تعطيل حساب' :
                           log.action === 'account_unblocked' ? 'إلغاء تعطيل' :
                           log.action === 'force_logout' ? 'تسجيل خروج إجباري' :
                           log.action === 'device_blocked' ? 'حظر جهاز' :
                           log.action}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                          {log.employee_name || log.employee_id} - بواسطة {log.performed_by_name}
                        </p>
                      </div>
                      <span className="text-xs text-slate-400 whitespace-nowrap">
                        {formatDateTime(log.created_at)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Suspend Dialog */}
      <Dialog open={suspendDialogOpen} onOpenChange={setSuspendDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <ShieldX size={20} />
              تعطيل الحسابات
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-3 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm font-medium text-red-800">
                سيتم تعطيل {selectedEmployees.length} حساب
              </p>
              <p className="text-xs text-red-600 mt-1">
                لن يتمكن هؤلاء الموظفين من تسجيل الدخول حتى يتم إلغاء التعطيل
              </p>
            </div>
            
            <div>
              <Label>سبب التعطيل *</Label>
              <Textarea
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                placeholder="اكتب سبب تعطيل الحساب..."
                className="mt-1"
              />
            </div>
            
            <div>
              <Label>مدة التعطيل (اختياري)</Label>
              <div className="flex gap-2 mt-1">
                {['1', '6', '24', '48', '168'].map(hours => (
                  <Button
                    key={hours}
                    type="button"
                    variant={suspendDuration === hours ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSuspendDuration(suspendDuration === hours ? '' : hours)}
                  >
                    {hours === '1' ? 'ساعة' : 
                     hours === '6' ? '6 ساعات' :
                     hours === '24' ? 'يوم' :
                     hours === '48' ? 'يومين' : 'أسبوع'}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {suspendDuration ? `سينتهي التعطيل بعد ${suspendDuration} ساعة` : 'دائم حتى الإلغاء اليدوي'}
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setSuspendDialogOpen(false)}>
              إلغاء
            </Button>
            <Button className="bg-red-600 hover:bg-red-700" onClick={handleSuspend}>
              <Lock size={16} className="ml-2" />
              تعطيل الحسابات
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Employee Details Dialog */}
      <Dialog open={detailsDialogOpen} onOpenChange={setDetailsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Fingerprint size={20} className="text-slate-600" />
              تفاصيل الموظف والأجهزة
            </DialogTitle>
          </DialogHeader>
          
          {employeeDetails && (
            <div className="space-y-6">
              {/* Employee Info */}
              <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl">
                <div className="w-16 h-16 rounded-full bg-slate-900 text-white flex items-center justify-center text-2xl font-bold">
                  {employeeDetails.employee?.full_name_ar?.charAt(0) || '?'}
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-slate-800">
                    {employeeDetails.employee?.full_name_ar}
                  </h3>
                  <p className="text-sm text-slate-500">
                    #{employeeDetails.employee?.employee_number} - {employeeDetails.employee?.department}
                  </p>
                </div>
                {employeeDetails.is_suspended && (
                  <div className="px-4 py-2 bg-red-100 rounded-lg">
                    <p className="text-sm font-bold text-red-700 flex items-center gap-2">
                      <ShieldX size={16} />
                      معطل
                    </p>
                    <p className="text-xs text-red-600">{employeeDetails.suspend_reason}</p>
                  </div>
                )}
              </div>

              {/* Devices */}
              <div>
                <h4 className="font-bold text-slate-800 mb-3 flex items-center gap-2">
                  <Smartphone size={18} />
                  الأجهزة المسجلة ({employeeDetails.devices?.length || 0})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {employeeDetails.devices?.map(device => (
                    <div 
                      key={device.id}
                      className={`p-4 rounded-xl border-2 ${
                        device.status === 'trusted' ? 'border-green-200 bg-green-50' :
                        device.status === 'blocked' ? 'border-red-200 bg-red-50' :
                        'border-yellow-200 bg-yellow-50'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <DeviceIcon 
                            type={device.device_type} 
                            size={24}
                            className={
                              device.status === 'trusted' ? 'text-green-600' :
                              device.status === 'blocked' ? 'text-red-600' : 'text-yellow-600'
                            }
                          />
                          <div>
                            <p className="font-bold text-slate-800">{device.friendly_name || device.device_type}</p>
                            <p className="text-xs text-slate-500">{device.browser} - {device.os}</p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          device.status === 'trusted' ? 'bg-green-500 text-white' :
                          device.status === 'blocked' ? 'bg-red-500 text-white' :
                          'bg-yellow-500 text-white'
                        }`}>
                          {device.status === 'trusted' ? 'موثوق' :
                           device.status === 'blocked' ? 'محظور' : 'معلق'}
                        </span>
                      </div>
                      
                      {/* Device Details */}
                      <div className="space-y-1 text-xs">
                        {device.fingerprint_data?.screenResolution && (
                          <div className="flex items-center gap-2 text-slate-600">
                            <Monitor size={12} />
                            <span>الشاشة: {device.fingerprint_data.screenResolution}</span>
                          </div>
                        )}
                        {device.fingerprint_data?.webglRenderer && (
                          <div className="flex items-center gap-2 text-slate-600">
                            <Cpu size={12} />
                            <span className="truncate">GPU: {device.fingerprint_data.webglRenderer.slice(0, 30)}...</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2 text-slate-500 pt-2 border-t mt-2">
                          <Clock size={12} />
                          <span>آخر استخدام: {formatDateTime(device.last_used_at)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent Sessions */}
              <div>
                <h4 className="font-bold text-slate-800 mb-3 flex items-center gap-2">
                  <History size={18} />
                  آخر الجلسات
                </h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-100">
                        <th className="p-2 text-right">التاريخ</th>
                        <th className="p-2 text-center">الدخول</th>
                        <th className="p-2 text-center">الخروج</th>
                        <th className="p-2 text-right">الجهاز</th>
                        <th className="p-2 text-center">الحالة</th>
                      </tr>
                    </thead>
                    <tbody>
                      {employeeDetails.recent_sessions?.slice(0, 10).map(session => (
                        <tr key={session.id} className="border-b hover:bg-slate-50">
                          <td className="p-2">{formatDate(session.login_at)}</td>
                          <td className="p-2 text-center font-mono">{formatTime(session.login_at)}</td>
                          <td className="p-2 text-center font-mono">{session.logout_at ? formatTime(session.logout_at) : '-'}</td>
                          <td className="p-2">
                            <div className="flex items-center gap-2">
                              <DeviceIcon type={session.device_type} size={14} />
                              <span className="text-xs">{session.device_name || session.os}</span>
                            </div>
                          </td>
                          <td className="p-2 text-center">
                            {session.status === 'active' ? (
                              <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">نشط</span>
                            ) : session.status === 'force_logout' ? (
                              <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs">خروج إجباري</span>
                            ) : (
                              <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs">منتهية</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Stat Card Component
function StatCard({ icon, label, value, color }) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg ${color} text-white flex items-center justify-center`}>
            {icon}
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-800">{value}</p>
            <p className="text-xs text-slate-500">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
