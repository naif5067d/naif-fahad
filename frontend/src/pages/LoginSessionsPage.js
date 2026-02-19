import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Clock, LogIn, LogOut, Smartphone, Monitor, Tablet, 
  Calendar, User, Filter, RefreshCw, ChevronDown, Download
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function LoginSessionsPage() {
  const { lang } = useLanguage();
  const [sessions, setSessions] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState('all');
  const [period, setPeriod] = useState('daily');
  const [loading, setLoading] = useState(false);
  const [expandedSession, setExpandedSession] = useState(null);

  useEffect(() => {
    fetchEmployees();
    fetchSessions();
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [selectedEmployee, period]);

  const fetchEmployees = async () => {
    try {
      const res = await api.get('/api/employees');
      setEmployees(res.data);
    } catch (err) {
      console.error('Failed to fetch employees:', err);
    }
  };

  const fetchSessions = async () => {
    setLoading(true);
    try {
      let url = `/api/devices/login-sessions?period=${period}`;
      if (selectedEmployee !== 'all') {
        url = `/api/devices/login-sessions/${selectedEmployee}?period=${period}`;
      }
      const res = await api.get(url);
      setSessions(res.data);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      toast.error(lang === 'ar' ? 'فشل تحميل السجلات' : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ar-EG', { 
      weekday: 'short', 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const calculateDuration = (loginAt, logoutAt) => {
    if (!loginAt || !logoutAt) return '-';
    const login = new Date(loginAt);
    const logout = new Date(logoutAt);
    const diff = Math.floor((logout - login) / 1000 / 60); // بالدقائق
    
    if (diff < 60) return `${diff} ${lang === 'ar' ? 'دقيقة' : 'min'}`;
    const hours = Math.floor(diff / 60);
    const mins = diff % 60;
    return `${hours}${lang === 'ar' ? 'س' : 'h'} ${mins}${lang === 'ar' ? 'د' : 'm'}`;
  };

  const DeviceIcon = ({ session }) => {
    if (session.is_mobile) return <Smartphone size={20} className="text-blue-500" />;
    if (session.device_type === 'tablet') return <Tablet size={20} className="text-purple-500" />;
    return <Monitor size={20} className="text-slate-500" />;
  };

  // تجميع الجلسات حسب التاريخ
  const groupedSessions = sessions.reduce((acc, session) => {
    const date = formatDate(session.login_at);
    if (!acc[date]) acc[date] = [];
    acc[date].push(session);
    return acc;
  }, {});

  const periodLabels = {
    daily: lang === 'ar' ? 'اليوم' : 'Today',
    weekly: lang === 'ar' ? 'الأسبوع' : 'Week',
    monthly: lang === 'ar' ? 'الشهر' : 'Month',
    yearly: lang === 'ar' ? 'السنة' : 'Year'
  };

  // إحصائيات
  const stats = {
    total: sessions.length,
    active: sessions.filter(s => s.status === 'active').length,
    completed: sessions.filter(s => s.status === 'completed').length,
    mobile: sessions.filter(s => s.is_mobile).length,
    desktop: sessions.filter(s => !s.is_mobile).length
  };

  return (
    <div className="space-y-6 pb-24 md:pb-6" data-testid="login-sessions-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Clock size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? 'سجل الدخول والخروج' : 'Login Sessions Log'}
            </h1>
            <p className="text-sm text-slate-500">
              {lang === 'ar' ? 'تتبع جميع عمليات تسجيل الدخول' : 'Track all login activities'}
            </p>
          </div>
        </div>
        
        <Button 
          variant="outline" 
          onClick={fetchSessions}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          {lang === 'ar' ? 'تحديث' : 'Refresh'}
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-blue-700">{stats.total}</p>
            <p className="text-sm text-blue-600">{lang === 'ar' ? 'إجمالي الجلسات' : 'Total Sessions'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-green-700">{stats.active}</p>
            <p className="text-sm text-green-600">{lang === 'ar' ? 'نشط الآن' : 'Active Now'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-slate-50 to-slate-100 border-slate-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-slate-700">{stats.completed}</p>
            <p className="text-sm text-slate-600">{lang === 'ar' ? 'مكتملة' : 'Completed'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-purple-700">{stats.mobile}</p>
            <p className="text-sm text-purple-600">{lang === 'ar' ? 'جوال' : 'Mobile'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-indigo-50 to-indigo-100 border-indigo-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-indigo-700">{stats.desktop}</p>
            <p className="text-sm text-indigo-600">{lang === 'ar' ? 'كمبيوتر' : 'Desktop'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            {/* Employee Filter */}
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium text-slate-600 mb-1 block">
                <User size={14} className="inline ml-1" />
                {lang === 'ar' ? 'الموظف' : 'Employee'}
              </label>
              <select
                value={selectedEmployee}
                onChange={(e) => setSelectedEmployee(e.target.value)}
                className="w-full p-2.5 border-2 rounded-lg text-sm focus:border-indigo-500 focus:outline-none"
                data-testid="employee-filter"
              >
                <option value="all">{lang === 'ar' ? '👥 جميع الموظفين' : '👥 All Employees'}</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name_ar || emp.full_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Period Filter */}
            <div>
              <label className="text-sm font-medium text-slate-600 mb-1 block">
                <Calendar size={14} className="inline ml-1" />
                {lang === 'ar' ? 'الفترة' : 'Period'}
              </label>
              <Tabs value={period} onValueChange={setPeriod} className="w-auto">
                <TabsList className="grid grid-cols-4 h-10">
                  <TabsTrigger value="daily" className="px-4" data-testid="period-daily">
                    {periodLabels.daily}
                  </TabsTrigger>
                  <TabsTrigger value="weekly" className="px-4" data-testid="period-weekly">
                    {periodLabels.weekly}
                  </TabsTrigger>
                  <TabsTrigger value="monthly" className="px-4" data-testid="period-monthly">
                    {periodLabels.monthly}
                  </TabsTrigger>
                  <TabsTrigger value="yearly" className="px-4" data-testid="period-yearly">
                    {periodLabels.yearly}
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sessions Table */}
      <Card>
        <CardHeader className="border-b bg-slate-50">
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <LogIn size={20} />
              {lang === 'ar' ? 'سجل الجلسات' : 'Sessions Log'}
            </span>
            <span className="text-sm font-normal bg-slate-200 px-3 py-1 rounded-full">
              {sessions.length} {lang === 'ar' ? 'سجل' : 'records'}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw size={24} className="animate-spin text-slate-400" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <Clock size={48} className="mx-auto text-slate-300 mb-4" />
              <p className="text-slate-500">
                {lang === 'ar' ? 'لا توجد سجلات في هذه الفترة' : 'No records found for this period'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-100 sticky top-0">
                  <tr>
                    <th className="p-4 text-right font-semibold text-slate-600">
                      {lang === 'ar' ? 'الموظف' : 'Employee'}
                    </th>
                    <th className="p-4 text-right font-semibold text-slate-600">
                      {lang === 'ar' ? 'الجهاز' : 'Device'}
                    </th>
                    <th className="p-4 text-center font-semibold text-slate-600">
                      <LogIn size={16} className="inline ml-1" />
                      {lang === 'ar' ? 'الدخول' : 'Login'}
                    </th>
                    <th className="p-4 text-center font-semibold text-slate-600">
                      <LogOut size={16} className="inline ml-1" />
                      {lang === 'ar' ? 'الخروج' : 'Logout'}
                    </th>
                    <th className="p-4 text-center font-semibold text-slate-600">
                      {lang === 'ar' ? 'المدة' : 'Duration'}
                    </th>
                    <th className="p-4 text-center font-semibold text-slate-600">
                      {lang === 'ar' ? 'الحالة' : 'Status'}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(groupedSessions).map(([date, dateSessions]) => (
                    <>
                      {/* Date Header */}
                      <tr key={date} className="bg-indigo-50">
                        <td colSpan={6} className="p-3 font-bold text-indigo-700">
                          <Calendar size={16} className="inline ml-2" />
                          {date}
                          <span className="font-normal text-indigo-500 mr-2">
                            ({dateSessions.length} {lang === 'ar' ? 'جلسة' : 'sessions'})
                          </span>
                        </td>
                      </tr>
                      {/* Sessions for this date */}
                      {dateSessions.map((session, idx) => (
                        <tr 
                          key={session.id} 
                          className={`border-b hover:bg-slate-50 transition-colors ${
                            session.status === 'active' ? 'bg-green-50/50' : ''
                          }`}
                          data-testid={`session-row-${idx}`}
                        >
                          <td className="p-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                                <User size={18} className="text-indigo-600" />
                              </div>
                              <div>
                                <p className="font-semibold text-slate-800">
                                  {session.employee_name_ar || session.username}
                                </p>
                                <p className="text-xs text-slate-500">
                                  #{session.employee_number || '-'}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="p-4">
                            <div className="flex items-center gap-2">
                              <DeviceIcon session={session} />
                              <div>
                                <p className="font-medium text-slate-700 text-sm">
                                  {session.device_name}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {session.browser} • {session.os_display || session.os}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="p-4 text-center">
                            <div className="inline-flex items-center gap-1 px-3 py-1.5 bg-green-100 rounded-lg">
                              <LogIn size={14} className="text-green-600" />
                              <span className="font-mono font-semibold text-green-700">
                                {formatTime(session.login_at)}
                              </span>
                            </div>
                          </td>
                          <td className="p-4 text-center">
                            {session.logout_at ? (
                              <div className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-100 rounded-lg">
                                <LogOut size={14} className="text-red-600" />
                                <span className="font-mono font-semibold text-red-700">
                                  {formatTime(session.logout_at)}
                                </span>
                              </div>
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>
                          <td className="p-4 text-center">
                            <span className="font-mono text-slate-600">
                              {calculateDuration(session.login_at, session.logout_at)}
                            </span>
                          </td>
                          <td className="p-4 text-center">
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                              session.status === 'active' 
                                ? 'bg-green-500 text-white animate-pulse' 
                                : 'bg-slate-200 text-slate-600'
                            }`}>
                              {session.status === 'active' 
                                ? (lang === 'ar' ? '🟢 نشط' : '🟢 Active')
                                : (lang === 'ar' ? 'مكتمل' : 'Done')
                              }
                            </span>
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
    </div>
  );
}
