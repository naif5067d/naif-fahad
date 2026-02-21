import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Clock, LogIn, LogOut, Smartphone, Monitor, Tablet, 
  Calendar, User, RefreshCw, Download, FileSpreadsheet
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
      toast.error(lang === 'ar' ? 'فشل تحميل السجلات' : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '--:--';
    return new Date(dateStr).toLocaleTimeString('en-GB', { 
      hour: '2-digit', 
      minute: '2-digit'
    });
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
    const months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
    return `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
  };

  const calculateDuration = (loginAt, logoutAt) => {
    if (!loginAt) return '-';
    const login = new Date(loginAt);
    const logout = logoutAt ? new Date(logoutAt) : new Date();
    const diff = Math.floor((logout - login) / 1000 / 60);
    
    const hours = Math.floor(diff / 60);
    const mins = diff % 60;
    return `${hours.toString().padStart(2,'0')}:${mins.toString().padStart(2,'0')}`;
  };

  const DeviceIcon = ({ session }) => {
    if (session.is_mobile) return <Smartphone size={18} className="text-green-600" />;
    if (session.device_type === 'tablet') return <Tablet size={18} className="text-purple-600" />;
    return <Monitor size={18} className="text-blue-600" />;
  };

  // تجميع حسب اليوم
  const groupedByDate = useMemo(() => {
    const groups = {};
    sessions.forEach(session => {
      const date = formatDate(session.login_at);
      if (!groups[date]) groups[date] = [];
      groups[date].push(session);
    });
    return groups;
  }, [sessions]);

  // إحصائيات
  const stats = useMemo(() => {
    const total = sessions.length;
    const totalMinutes = sessions.reduce((acc, s) => {
      if (s.login_at) {
        const login = new Date(s.login_at);
        const logout = s.logout_at ? new Date(s.logout_at) : new Date();
        acc += (logout - login) / 1000 / 60;
      }
      return acc;
    }, 0);
    return { total, totalHours: Math.floor(totalMinutes / 60), totalMins: Math.round(totalMinutes % 60) };
  }, [sessions]);

  const periodOptions = [
    { value: 'daily', label: 'يومي', iconName: 'Calendar' },
    { value: 'weekly', label: 'أسبوعي', iconName: 'CalendarDays' },
    { value: 'monthly', label: 'شهري', iconName: 'CalendarRange' },
    { value: 'yearly', label: 'سنوي', iconName: 'BarChart3' },
  ];

  const selectedEmp = employees.find(e => e.id === selectedEmployee);

  const exportToCSV = () => {
    if (sessions.length === 0) return;
    const headers = ['التاريخ', 'الدخول', 'الخروج', 'المدة', 'الجهاز', 'المتصفح'];
    const rows = sessions.map(s => [
      formatDate(s.login_at),
      formatTime(s.login_at),
      formatTime(s.logout_at),
      calculateDuration(s.login_at, s.logout_at),
      s.device_name || '-',
      s.browser || '-'
    ]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `سجل_${selectedEmp?.full_name_ar || 'موظف'}_${period}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6 pb-24" data-testid="login-sessions-page">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
          <FileSpreadsheet className="text-indigo-600" size={28} />
          {lang === 'ar' ? 'سجل الدخول والخروج' : 'Login Sessions'}
        </h1>
        <p className="text-slate-500 mt-1">
          {lang === 'ar' ? 'تقرير تفصيلي لكل موظف' : 'Detailed employee report'}
        </p>
      </div>

      {/* Controls */}
      <Card className="mb-6 shadow-sm">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Employee Select */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                <User size={16} className="inline ml-1" />
                اختر الموظف
              </label>
              <select
                value={selectedEmployee}
                onChange={(e) => setSelectedEmployee(e.target.value)}
                className="w-full p-3 border-2 rounded-lg text-base focus:border-indigo-500 focus:outline-none"
              >
                <option value="">-- اختر موظف --</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name_ar} - {emp.employee_number || ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Period Select */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                <Calendar size={16} className="inline ml-1" />
                الفترة
              </label>
              <div className="flex gap-2">
                {periodOptions.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setPeriod(opt.value)}
                    className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all ${
                      period === opt.value
                        ? 'bg-indigo-600 text-white shadow'
                        : 'bg-white border-2 text-slate-600 hover:border-indigo-300'
                    }`}
                  >
                    {opt.icon} {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* No Selection */}
      {!selectedEmployee && (
        <Card className="border-dashed border-2 border-slate-300 bg-white">
          <CardContent className="py-16 text-center">
            <User size={56} className="mx-auto text-slate-300 mb-4" />
            <p className="text-lg text-slate-500">اختر موظفاً من القائمة لعرض سجله</p>
          </CardContent>
        </Card>
      )}

      {/* Employee Selected */}
      {selectedEmployee && (
        <>
          {/* Employee Info Bar */}
          <div className="bg-gradient-to-l from-indigo-600 to-indigo-700 rounded-xl p-4 mb-4 text-white flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center text-xl font-bold">
                {selectedEmp?.full_name_ar?.charAt(0) || '؟'}
              </div>
              <div>
                <h2 className="text-lg font-bold">{selectedEmp?.full_name_ar}</h2>
                <p className="text-indigo-200 text-sm">#{selectedEmp?.employee_number}</p>
              </div>
            </div>
            <div className="flex items-center gap-6 text-center">
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-xs text-indigo-200">جلسة</p>
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.totalHours}:{stats.totalMins.toString().padStart(2,'0')}</p>
                <p className="text-xs text-indigo-200">ساعة</p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mb-4">
            <Button variant="outline" size="sm" onClick={fetchSessions} disabled={loading}>
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              تحديث
            </Button>
            <Button variant="outline" size="sm" onClick={exportToCSV} disabled={sessions.length === 0}>
              <Download size={16} />
              تصدير
            </Button>
          </div>

          {/* Table */}
          <Card className="overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              {loading ? (
                <div className="py-16 text-center">
                  <RefreshCw size={32} className="animate-spin text-indigo-500 mx-auto" />
                </div>
              ) : sessions.length === 0 ? (
                <div className="py-16 text-center">
                  <Clock size={48} className="mx-auto text-slate-300 mb-4" />
                  <p className="text-slate-500">لا توجد سجلات في هذه الفترة</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-800 text-white">
                      <th className="p-3 text-right w-12">#</th>
                      <th className="p-3 text-right">التاريخ</th>
                      <th className="p-3 text-center w-24">الدخول</th>
                      <th className="p-3 text-center w-24">الخروج</th>
                      <th className="p-3 text-center w-20">المدة</th>
                      <th className="p-3 text-right">الجهاز</th>
                      <th className="p-3 text-center w-20">الحالة</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(groupedByDate).map(([date, dateSessions], gIdx) => (
                      <>
                        {/* Date Row */}
                        <tr key={`d-${gIdx}`} className="bg-primary/5 border-b-2 border-primary/20">
                          <td colSpan={7} className="p-2 font-bold text-primary flex items-center gap-2">
                            <Calendar size={16} />
                            {formatFullDate(dateSessions[0]?.login_at)}
                            <span className="font-normal text-indigo-500 mr-2">
                              ({dateSessions.length} جلسة)
                            </span>
                          </td>
                        </tr>
                        {/* Session Rows */}
                        {dateSessions.map((s, idx) => (
                          <tr 
                            key={s.id} 
                            className={`border-b hover:bg-slate-50 ${s.status === 'active' ? 'bg-green-50' : idx % 2 ? 'bg-slate-50/50' : ''}`}
                          >
                            <td className="p-3 text-center text-slate-400 font-mono">{idx + 1}</td>
                            <td className="p-3 font-medium">{formatDate(s.login_at)}</td>
                            <td className="p-3 text-center">
                              <span className="inline-block bg-green-100 text-green-700 px-2 py-1 rounded font-mono font-bold">
                                {formatTime(s.login_at)}
                              </span>
                            </td>
                            <td className="p-3 text-center">
                              {s.logout_at ? (
                                <span className="inline-block bg-red-100 text-red-700 px-2 py-1 rounded font-mono font-bold">
                                  {formatTime(s.logout_at)}
                                </span>
                              ) : (
                                <span className="text-slate-400">--:--</span>
                              )}
                            </td>
                            <td className="p-3 text-center font-mono font-bold text-slate-700">
                              {calculateDuration(s.login_at, s.logout_at)}
                            </td>
                            <td className="p-3">
                              <div className="flex items-center gap-2">
                                <DeviceIcon session={s} />
                                <div>
                                  <p className="font-medium text-slate-700">{s.device_name || '-'}</p>
                                  <p className="text-xs text-slate-500">{s.browser}</p>
                                </div>
                              </div>
                            </td>
                            <td className="p-3 text-center">
                              {s.status === 'active' ? (
                                <span className="inline-block bg-green-500 text-white px-2 py-1 rounded-full text-xs font-bold animate-pulse">
                                  نشط
                                </span>
                              ) : (
                                <span className="inline-block bg-slate-200 text-slate-600 px-2 py-1 rounded-full text-xs">
                                  ✓
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </>
                    ))}
                  </tbody>
                  {/* Footer */}
                  <tfoot>
                    <tr className="bg-slate-800 text-white font-bold">
                      <td colSpan={4} className="p-3 text-right">الإجمالي:</td>
                      <td className="p-3 text-center font-mono">
                        {stats.totalHours}:{stats.totalMins.toString().padStart(2,'0')}
                      </td>
                      <td colSpan={2} className="p-3 text-center">
                        {stats.total} جلسة
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
