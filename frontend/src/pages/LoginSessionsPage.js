import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Clock, LogIn, LogOut, Smartphone, Monitor, Tablet, 
  Calendar, User, RefreshCw, Download, ChevronLeft, ChevronRight,
  FileSpreadsheet, Filter, ArrowUpDown
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function LoginSessionsPage() {
  const { lang } = useLanguage();
  const [sessions, setSessions] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [period, setPeriod] = useState('monthly');
  const [loading, setLoading] = useState(false);
  const [sortConfig, setSortConfig] = useState({ key: 'login_at', direction: 'desc' });

  useEffect(() => {
    fetchEmployees();
  }, []);

  useEffect(() => {
    if (selectedEmployee) {
      fetchSessions();
    }
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
    if (!selectedEmployee) return;
    setLoading(true);
    try {
      const url = `/api/devices/login-sessions/${selectedEmployee}?period=${period}`;
      const res = await api.get(url);
      setSessions(res.data);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      toast.error(lang === 'ar' ? 'فشل تحميل السجلات' : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  // الترتيب
  const sortedSessions = useMemo(() => {
    const sorted = [...sessions];
    sorted.sort((a, b) => {
      if (sortConfig.key === 'login_at' || sortConfig.key === 'logout_at') {
        const aVal = a[sortConfig.key] ? new Date(a[sortConfig.key]) : new Date(0);
        const bVal = b[sortConfig.key] ? new Date(b[sortConfig.key]) : new Date(0);
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const aVal = a[sortConfig.key] || '';
      const bVal = b[sortConfig.key] || '';
      return sortConfig.direction === 'asc' 
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    });
    return sorted;
  }, [sessions, sortConfig]);

  // تجميع حسب اليوم
  const groupedByDate = useMemo(() => {
    const groups = {};
    sortedSessions.forEach(session => {
      const date = new Date(session.login_at).toLocaleDateString('ar-EG', {
        year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
      });
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(session);
    });
    return groups;
  }, [sortedSessions]);

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleTimeString('ar-EG', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-EG');
  };

  const calculateDuration = (loginAt, logoutAt) => {
    if (!loginAt) return '-';
    const login = new Date(loginAt);
    const logout = logoutAt ? new Date(logoutAt) : new Date();
    const diff = Math.floor((logout - login) / 1000); // بالثواني
    
    const hours = Math.floor(diff / 3600);
    const mins = Math.floor((diff % 3600) / 60);
    const secs = diff % 60;
    
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const DeviceIcon = ({ session }) => {
    if (session.is_mobile) return <Smartphone size={16} className="text-blue-500" />;
    if (session.device_type === 'tablet') return <Tablet size={16} className="text-purple-500" />;
    return <Monitor size={16} className="text-slate-600" />;
  };

  // إحصائيات
  const stats = useMemo(() => {
    const total = sessions.length;
    const active = sessions.filter(s => s.status === 'active').length;
    const totalMinutes = sessions.reduce((acc, s) => {
      if (s.login_at) {
        const login = new Date(s.login_at);
        const logout = s.logout_at ? new Date(s.logout_at) : new Date();
        acc += (logout - login) / 1000 / 60;
      }
      return acc;
    }, 0);
    const avgMinutes = total > 0 ? Math.round(totalMinutes / total) : 0;
    
    return { total, active, totalMinutes: Math.round(totalMinutes), avgMinutes };
  }, [sessions]);

  const periodOptions = [
    { value: 'daily', label: lang === 'ar' ? 'اليوم' : 'Today' },
    { value: 'weekly', label: lang === 'ar' ? 'أسبوعي' : 'Weekly' },
    { value: 'monthly', label: lang === 'ar' ? 'شهري' : 'Monthly' },
    { value: 'yearly', label: lang === 'ar' ? 'سنوي' : 'Yearly' },
  ];

  const selectedEmployeeData = employees.find(e => e.id === selectedEmployee);

  // تصدير Excel
  const exportToCSV = () => {
    if (sessions.length === 0) return;
    
    const headers = ['التاريخ', 'وقت الدخول', 'وقت الخروج', 'المدة', 'الجهاز', 'المتصفح', 'الحالة'];
    const rows = sessions.map(s => [
      formatDate(s.login_at),
      formatTime(s.login_at),
      formatTime(s.logout_at),
      calculateDuration(s.login_at, s.logout_at),
      s.device_name || '-',
      s.browser || '-',
      s.status === 'active' ? 'نشط' : 'مكتمل'
    ]);
    
    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `login_sessions_${selectedEmployeeData?.full_name_ar || 'employee'}_${period}.csv`;
    link.click();
  };

  return (
    <div className="space-y-6 pb-24 md:pb-6" data-testid="login-sessions-page">
      {/* Header */}
      <div className="bg-gradient-to-l from-indigo-600 to-purple-700 rounded-2xl p-6 text-white shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur">
            <FileSpreadsheet size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold">
              {lang === 'ar' ? 'سجل الدخول والخروج' : 'Login Sessions Report'}
            </h1>
            <p className="text-white/80 text-sm mt-1">
              {lang === 'ar' ? 'تقرير تفصيلي لكل موظف - يومي / أسبوعي / شهري / سنوي' : 'Detailed report per employee'}
            </p>
          </div>
        </div>
      </div>

      {/* Employee Selection Card */}
      <Card className="border-2 border-indigo-200 shadow-lg">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Employee Dropdown */}
            <div className="md:col-span-2">
              <label className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-2">
                <User size={18} className="text-indigo-600" />
                {lang === 'ar' ? 'اختر الموظف' : 'Select Employee'}
              </label>
              <select
                value={selectedEmployee}
                onChange={(e) => setSelectedEmployee(e.target.value)}
                className="w-full p-4 border-2 border-slate-200 rounded-xl text-lg font-medium focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none transition-all bg-white"
                data-testid="employee-select"
              >
                <option value="">
                  {lang === 'ar' ? '-- اختر موظف لعرض سجله --' : '-- Select an employee --'}
                </option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name_ar || emp.full_name} ({emp.employee_number || '-'})
                  </option>
                ))}
              </select>
            </div>

            {/* Period Filter */}
            <div>
              <label className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-2">
                <Calendar size={18} className="text-indigo-600" />
                {lang === 'ar' ? 'الفترة' : 'Period'}
              </label>
              <div className="grid grid-cols-2 gap-2">
                {periodOptions.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setPeriod(opt.value)}
                    className={`p-3 rounded-xl font-medium transition-all ${
                      period === opt.value
                        ? 'bg-indigo-600 text-white shadow-lg'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                    data-testid={`period-${opt.value}`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* No Employee Selected */}
      {!selectedEmployee && (
        <Card className="border-2 border-dashed border-slate-300">
          <CardContent className="py-16 text-center">
            <User size={64} className="mx-auto text-slate-300 mb-4" />
            <h3 className="text-xl font-bold text-slate-500 mb-2">
              {lang === 'ar' ? 'اختر موظفاً لعرض سجله' : 'Select an employee to view their log'}
            </h3>
            <p className="text-slate-400">
              {lang === 'ar' ? 'استخدم القائمة المنسدلة أعلاه لاختيار الموظف' : 'Use the dropdown above to select an employee'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Employee Selected - Show Stats & Table */}
      {selectedEmployee && (
        <>
          {/* Employee Info & Stats */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Employee Card */}
            <Card className="md:col-span-2 bg-gradient-to-br from-slate-800 to-slate-900 text-white">
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-2xl font-bold">
                    {selectedEmployeeData?.full_name_ar?.charAt(0) || '؟'}
                  </div>
                  <div>
                    <h3 className="text-xl font-bold">{selectedEmployeeData?.full_name_ar || '-'}</h3>
                    <p className="text-slate-400">#{selectedEmployeeData?.employee_number || '-'}</p>
                    <p className="text-sm text-indigo-300 mt-1">{selectedEmployeeData?.department || '-'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Stats */}
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-blue-700">{stats.total}</p>
                <p className="text-sm text-blue-600 font-medium">
                  {lang === 'ar' ? 'إجمالي الجلسات' : 'Total Sessions'}
                </p>
              </CardContent>
            </Card>

            <Card className="bg-green-50 border-green-200">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-green-700">{stats.active}</p>
                <p className="text-sm text-green-600 font-medium">
                  {lang === 'ar' ? 'نشط الآن' : 'Active Now'}
                </p>
              </CardContent>
            </Card>

            <Card className="bg-purple-50 border-purple-200">
              <CardContent className="p-4 text-center">
                <p className="text-3xl font-bold text-purple-700">
                  {Math.floor(stats.totalMinutes / 60)}:{(stats.totalMinutes % 60).toString().padStart(2, '0')}
                </p>
                <p className="text-sm text-purple-600 font-medium">
                  {lang === 'ar' ? 'إجمالي الوقت' : 'Total Time'}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Actions Bar */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
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
            <Button 
              onClick={exportToCSV}
              disabled={sessions.length === 0}
              className="gap-2 bg-green-600 hover:bg-green-700"
            >
              <Download size={16} />
              {lang === 'ar' ? 'تصدير Excel' : 'Export CSV'}
            </Button>
          </div>

          {/* Excel-like Table */}
          <Card className="overflow-hidden shadow-xl border-2">
            <div className="bg-slate-800 text-white px-4 py-3 flex items-center justify-between">
              <span className="font-bold flex items-center gap-2">
                <FileSpreadsheet size={20} />
                {lang === 'ar' ? 'جدول السجلات' : 'Sessions Table'}
              </span>
              <span className="text-sm bg-slate-700 px-3 py-1 rounded-full">
                {sessions.length} {lang === 'ar' ? 'سجل' : 'records'}
              </span>
            </div>
            
            <div className="overflow-x-auto">
              {loading ? (
                <div className="flex items-center justify-center py-20">
                  <RefreshCw size={32} className="animate-spin text-indigo-500" />
                </div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-20">
                  <Clock size={48} className="mx-auto text-slate-300 mb-4" />
                  <p className="text-slate-500 font-medium">
                    {lang === 'ar' ? 'لا توجد سجلات في هذه الفترة' : 'No records for this period'}
                  </p>
                </div>
              ) : (
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-gradient-to-r from-slate-100 to-slate-50">
                      <th className="border-b-2 border-slate-300 p-4 text-right font-bold text-slate-700 sticky top-0 bg-slate-100">
                        #
                      </th>
                      <th 
                        className="border-b-2 border-slate-300 p-4 text-right font-bold text-slate-700 cursor-pointer hover:bg-slate-200 transition-colors sticky top-0 bg-slate-100"
                        onClick={() => handleSort('login_at')}
                      >
                        <span className="flex items-center gap-2">
                          <Calendar size={16} />
                          {lang === 'ar' ? 'التاريخ' : 'Date'}
                          <ArrowUpDown size={14} className="text-slate-400" />
                        </span>
                      </th>
                      <th className="border-b-2 border-slate-300 p-4 text-center font-bold text-slate-700 sticky top-0 bg-slate-100">
                        <span className="flex items-center justify-center gap-2">
                          <LogIn size={16} className="text-green-600" />
                          {lang === 'ar' ? 'وقت الدخول' : 'Login Time'}
                        </span>
                      </th>
                      <th className="border-b-2 border-slate-300 p-4 text-center font-bold text-slate-700 sticky top-0 bg-slate-100">
                        <span className="flex items-center justify-center gap-2">
                          <LogOut size={16} className="text-red-600" />
                          {lang === 'ar' ? 'وقت الخروج' : 'Logout Time'}
                        </span>
                      </th>
                      <th className="border-b-2 border-slate-300 p-4 text-center font-bold text-slate-700 sticky top-0 bg-slate-100">
                        <span className="flex items-center justify-center gap-2">
                          <Clock size={16} />
                          {lang === 'ar' ? 'المدة' : 'Duration'}
                        </span>
                      </th>
                      <th className="border-b-2 border-slate-300 p-4 text-right font-bold text-slate-700 sticky top-0 bg-slate-100">
                        {lang === 'ar' ? 'الجهاز' : 'Device'}
                      </th>
                      <th className="border-b-2 border-slate-300 p-4 text-right font-bold text-slate-700 sticky top-0 bg-slate-100">
                        {lang === 'ar' ? 'المتصفح' : 'Browser'}
                      </th>
                      <th className="border-b-2 border-slate-300 p-4 text-center font-bold text-slate-700 sticky top-0 bg-slate-100">
                        {lang === 'ar' ? 'الحالة' : 'Status'}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(groupedByDate).map(([date, dateSessions], groupIdx) => (
                      <>
                        {/* Date Header Row */}
                        <tr key={`date-${groupIdx}`} className="bg-indigo-50">
                          <td colSpan={8} className="p-3 font-bold text-indigo-700 border-b border-indigo-200">
                            <Calendar size={16} className="inline ml-2" />
                            {date}
                            <span className="font-normal text-indigo-500 mr-3">
                              ({dateSessions.length} {lang === 'ar' ? 'جلسة' : 'sessions'})
                            </span>
                          </td>
                        </tr>
                        {/* Session Rows */}
                        {dateSessions.map((session, idx) => (
                          <tr 
                            key={session.id}
                            className={`
                              border-b border-slate-200 transition-colors
                              ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}
                              ${session.status === 'active' ? 'bg-green-50' : ''}
                              hover:bg-indigo-50
                            `}
                          >
                            <td className="p-4 text-center font-mono text-slate-500 text-sm">
                              {idx + 1}
                            </td>
                            <td className="p-4 font-medium text-slate-700">
                              {formatDate(session.login_at)}
                            </td>
                            <td className="p-4 text-center">
                              <span className="inline-flex items-center gap-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg font-mono font-bold">
                                <LogIn size={14} />
                                {formatTime(session.login_at)}
                              </span>
                            </td>
                            <td className="p-4 text-center">
                              {session.logout_at ? (
                                <span className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg font-mono font-bold">
                                  <LogOut size={14} />
                                  {formatTime(session.logout_at)}
                                </span>
                              ) : (
                                <span className="text-slate-400 font-mono">--:--:--</span>
                              )}
                            </td>
                            <td className="p-4 text-center">
                              <span className={`font-mono font-bold ${
                                session.status === 'active' ? 'text-green-600' : 'text-slate-600'
                              }`}>
                                {calculateDuration(session.login_at, session.logout_at)}
                              </span>
                            </td>
                            <td className="p-4">
                              <div className="flex items-center gap-2">
                                <DeviceIcon session={session} />
                                <span className="text-sm font-medium text-slate-700">
                                  {session.device_name || '-'}
                                </span>
                              </div>
                            </td>
                            <td className="p-4">
                              <span className="text-sm text-slate-600">
                                {session.browser || '-'}
                              </span>
                            </td>
                            <td className="p-4 text-center">
                              <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
                                session.status === 'active'
                                  ? 'bg-green-500 text-white animate-pulse'
                                  : 'bg-slate-200 text-slate-600'
                              }`}>
                                {session.status === 'active'
                                  ? (lang === 'ar' ? '🟢 نشط' : '🟢 Active')
                                  : (lang === 'ar' ? '✓ مكتمل' : '✓ Done')
                                }
                              </span>
                            </td>
                          </tr>
                        ))}
                      </>
                    ))}
                  </tbody>
                  {/* Footer with totals */}
                  <tfoot>
                    <tr className="bg-slate-800 text-white font-bold">
                      <td colSpan={4} className="p-4 text-right">
                        {lang === 'ar' ? 'الإجمالي' : 'Total'}
                      </td>
                      <td className="p-4 text-center font-mono">
                        {Math.floor(stats.totalMinutes / 60)}:{(stats.totalMinutes % 60).toString().padStart(2, '0')}:00
                      </td>
                      <td colSpan={3} className="p-4 text-center">
                        {stats.total} {lang === 'ar' ? 'جلسة' : 'sessions'}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
