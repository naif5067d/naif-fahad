import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, Clock, CheckCircle, XCircle, AlertTriangle, Building2, Navigation } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function AttendancePage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [today, setToday] = useState({ check_in: null, check_out: null });
  const [history, setHistory] = useState([]);
  const [gpsState, setGpsState] = useState({ available: false, lat: null, lng: null, checking: true });
  const [loading, setLoading] = useState(false);
  const [workLocation, setWorkLocation] = useState('');
  const [assignedLocations, setAssignedLocations] = useState([]);
  const [adminData, setAdminData] = useState([]);
  const [period, setPeriod] = useState('daily');
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().slice(0, 10));

  const isAdmin = ['sultan', 'naif', 'salah', 'mohammed', 'stas'].includes(user?.role);
  const isEmployee = ['employee', 'supervisor'].includes(user?.role);

  const fetchData = () => {
    if (isEmployee || isAdmin) {
      api.get('/api/attendance/today').then(r => setToday(r.data)).catch(() => {});
      api.get('/api/attendance/history').then(r => setHistory(r.data)).catch(() => {});
    }
    if (isAdmin) fetchAdmin();
  };

  const fetchAdmin = () => {
    api.get(`/api/attendance/admin?period=${period}&date=${dateFilter}`).then(r => setAdminData(r.data)).catch(() => setAdminData([]));
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { if (isAdmin) fetchAdmin(); }, [period, dateFilter]);

  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        pos => setGpsState({ available: true, lat: pos.coords.latitude, lng: pos.coords.longitude, checking: false }),
        () => setGpsState({ available: false, lat: null, lng: null, checking: false }),
        { timeout: 10000 }
      );
    } else setGpsState({ available: false, lat: null, lng: null, checking: false });
  }, []);

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      await api.post('/api/attendance/check-in', { latitude: gpsState.lat, longitude: gpsState.lng, gps_available: gpsState.available, work_location: workLocation });
      toast.success(t('attendance.checkedIn'));
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  const handleCheckOut = async () => {
    setLoading(true);
    try {
      await api.post('/api/attendance/check-out', { latitude: gpsState.lat, longitude: gpsState.lng, gps_available: gpsState.available, work_location: workLocation });
      toast.success(t('attendance.checkedOut'));
      fetchData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-6" data-testid="attendance-page">
      <h1 className="text-2xl font-bold tracking-tight">{t('attendance.title')}</h1>

      {/* Employee: Check in/out */}
      {(isEmployee || isAdmin) && (
        <div className="border border-border rounded-lg p-4">
          {!gpsState.checking && !gpsState.available && (
            <div className="flex items-center gap-2 p-2 mb-3 rounded bg-amber-50 dark:bg-amber-950/20 border border-amber-200 text-xs text-amber-700">
              <AlertTriangle size={14} /> {t('attendance.noGps')}
            </div>
          )}
          <div className="flex flex-col sm:flex-row gap-3 items-center">
            <Select value={workLocation} onValueChange={setWorkLocation} disabled={!!today.check_in}>
              <SelectTrigger className="w-40" data-testid="work-location-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="HQ"><div className="flex items-center gap-1.5"><Building2 size={14} className="text-blue-600" />{t('attendance.hq')}</div></SelectItem>
                <SelectItem value="Project"><div className="flex items-center gap-1.5"><HardHat size={14} className="text-amber-600" />{t('attendance.project')}</div></SelectItem>
              </SelectContent>
            </Select>
            <div className="flex gap-2 flex-1">
              <Button data-testid="check-in-btn" onClick={handleCheckIn} disabled={loading || !!today.check_in} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" size="sm">
                <MapPin size={14} className="me-1" /> {t('attendance.checkIn')} {today.check_in && <span className="text-xs ms-1 opacity-80">({today.check_in.timestamp?.slice(11, 16)})</span>}
              </Button>
              <Button data-testid="check-out-btn" onClick={handleCheckOut} disabled={loading || !today.check_in || !!today.check_out} variant="outline" className="flex-1" size="sm">
                <Clock size={14} className="me-1" /> {t('attendance.checkOut')} {today.check_out && <span className="text-xs ms-1 opacity-80">({today.check_out.timestamp?.slice(11, 16)})</span>}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Admin: Attendance Tracking Table */}
      {isAdmin && (
        <div>
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between mb-3">
            <h2 className="text-base font-semibold">{lang === 'ar' ? 'سجل الحضور' : 'Attendance Records'}</h2>
            <div className="flex gap-2 items-center">
              <Tabs value={period} onValueChange={setPeriod}>
                <TabsList className="h-8">
                  <TabsTrigger value="daily" className="text-xs h-7">{lang === 'ar' ? 'يومي' : 'Daily'}</TabsTrigger>
                  <TabsTrigger value="weekly" className="text-xs h-7">{lang === 'ar' ? 'أسبوعي' : 'Weekly'}</TabsTrigger>
                  <TabsTrigger value="monthly" className="text-xs h-7">{lang === 'ar' ? 'شهري' : 'Monthly'}</TabsTrigger>
                  <TabsTrigger value="yearly" className="text-xs h-7">{lang === 'ar' ? 'سنوي' : 'Yearly'}</TabsTrigger>
                </TabsList>
              </Tabs>
              <Input type="date" value={dateFilter} onChange={e => setDateFilter(e.target.value)} className="w-36 h-8 text-xs" data-testid="date-filter" />
            </div>
          </div>

          <div className="border border-border rounded-lg overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="admin-attendance-table">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900/50 text-xs border-b border-border">
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground hidden sm:table-cell">{lang === 'ar' ? 'الرقم' : 'No.'}</th>
                    <th className="px-3 py-2.5 text-center font-semibold text-muted-foreground">{lang === 'ar' ? 'حضور' : 'In'}</th>
                    <th className="px-3 py-2.5 text-center font-semibold text-muted-foreground">{lang === 'ar' ? 'انصراف' : 'Out'}</th>
                    <th className="px-3 py-2.5 text-center font-semibold text-muted-foreground hidden sm:table-cell">{lang === 'ar' ? 'GPS حضور' : 'GPS In'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground hidden md:table-cell">{lang === 'ar' ? 'الموقع' : 'Location'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {adminData.length === 0 ? (
                    <tr><td colSpan={7} className="text-center py-10 text-muted-foreground">{t('common.noData')}</td></tr>
                  ) : adminData.map((row, i) => (
                    <tr key={i} className="hover:bg-muted/30" data-testid={`attendance-row-${i}`}>
                      <td className="px-3 py-2 font-mono text-xs">{row.date}</td>
                      <td className="px-3 py-2 text-sm font-medium">{lang === 'ar' ? row.employee_name_ar || row.employee_name : row.employee_name}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground hidden sm:table-cell">{row.employee_number}</td>
                      <td className="px-3 py-2 text-center font-mono text-xs">{row.check_in_time || <span className="text-red-400">-</span>}</td>
                      <td className="px-3 py-2 text-center font-mono text-xs">{row.check_out_time || <span className="text-amber-400">-</span>}</td>
                      <td className="px-3 py-2 text-center hidden sm:table-cell">{row.gps_valid_in === true ? <CheckCircle size={14} className="inline text-emerald-500" /> : row.gps_valid_in === false ? <XCircle size={14} className="inline text-red-400" /> : <span className="text-muted-foreground">-</span>}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground hidden md:table-cell">{row.work_location || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {adminData.length > 0 && (
              <div className="bg-slate-50 dark:bg-slate-900/50 px-3 py-2 border-t border-border text-xs text-muted-foreground">
                {lang === 'ar' ? `${adminData.length} سجل` : `${adminData.length} records`}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Employee personal history */}
      {isEmployee && history.length > 0 && (
        <div>
          <h2 className="text-base font-semibold mb-3">{t('attendance.history')}</h2>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="attendance-history-table">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900/50 text-xs border-b border-border">
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{t('attendance.date')}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{t('transactions.type')}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{t('attendance.time')}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground hidden sm:table-cell">{t('attendance.gpsStatus')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {history.map(e => (
                    <tr key={e.id} className="hover:bg-muted/30">
                      <td className="px-3 py-2 font-mono text-xs">{e.date}</td>
                      <td className="px-3 py-2 text-sm capitalize">{e.type?.replace('_', ' ')}</td>
                      <td className="px-3 py-2 text-xs font-mono">{e.timestamp?.slice(11, 19)}</td>
                      <td className="px-3 py-2 hidden sm:table-cell">{e.gps_valid ? <CheckCircle size={14} className="text-emerald-500" /> : <XCircle size={14} className="text-red-400" />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
