import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, Clock, CheckCircle, XCircle, AlertTriangle, Building2, Navigation, CalendarDays, User } from 'lucide-react';
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

  const isEmployee = ['employee', 'supervisor'].includes(user?.role);
  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);

  // Fetch employee's assigned work locations
  const fetchAssignedLocations = async (empId) => {
    try {
      const res = await api.get(`/api/work-locations/employee/${empId}`);
      setAssignedLocations(res.data || []);
      if (res.data?.length > 0 && !workLocation) {
        setWorkLocation(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch assigned locations:', err);
    }
  };

  const fetchAdmin = async () => {
    try {
      const res = await api.get('/api/attendance/admin', { params: { period, date: dateFilter } });
      setAdminData(res.data);
    } catch (err) {}
  };

  const fetchData = () => {
    if (isEmployee || isAdmin) {
      api.get('/api/attendance/today').then(r => setToday(r.data)).catch(() => {});
      api.get('/api/attendance/history').then(r => setHistory(r.data)).catch(() => {});
    }
    if (isAdmin) fetchAdmin();
  };

  useEffect(() => { 
    fetchData();
    // Check GPS
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setGpsState({ available: true, lat: pos.coords.latitude, lng: pos.coords.longitude, checking: false }),
        () => setGpsState({ available: false, lat: null, lng: null, checking: false })
      );
    } else {
      setGpsState({ available: false, lat: null, lng: null, checking: false });
    }
  }, []);
  
  useEffect(() => { if (isAdmin) fetchAdmin(); }, [period, dateFilter]);

  useEffect(() => {
    if (user?.employee_id) {
      fetchAssignedLocations(user.employee_id);
    }
  }, [user?.employee_id]);

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      await api.post('/api/attendance/check-in', { 
        location: workLocation, 
        lat: gpsState.lat, 
        lng: gpsState.lng 
      });
      toast.success(t('attendance.checkedIn'));
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOut = async () => {
    setLoading(true);
    try {
      await api.post('/api/attendance/check-out', { 
        lat: gpsState.lat, 
        lng: gpsState.lng 
      });
      toast.success(t('attendance.checkedOut'));
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="attendance-page">
      {/* Header */}
      <div>
        <h1 className="text-xl md:text-2xl font-bold">{t('nav.attendance')}</h1>
        <p className="text-sm text-muted-foreground mt-1">{new Date().toLocaleDateString(lang === 'ar' ? 'ar-SA' : 'en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      {/* Employee: Check in/out Card */}
      {(isEmployee || isAdmin) && (
        <div className="card-premium p-5 space-y-4">
          {/* GPS Status */}
          {!gpsState.checking && !gpsState.available && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-600">
              <AlertTriangle size={18} />
              <span className="text-sm font-medium">{t('attendance.noGps')}</span>
            </div>
          )}

          {/* Assigned Locations */}
          {assignedLocations.length > 0 && (
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
              <p className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
                <MapPin size={16} />
                {lang === 'ar' ? 'مواقع العمل المعينة لك' : 'Your Assigned Work Locations'}
              </p>
              <div className="flex flex-wrap gap-2">
                {assignedLocations.map(loc => (
                  <div key={loc.id} className="text-sm bg-background px-3 py-2 rounded-lg border border-border">
                    <span className="font-medium">{lang === 'ar' ? loc.name_ar : loc.name}</span>
                    <span className="text-muted-foreground ms-2 text-xs">({loc.work_start} - {loc.work_end})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {assignedLocations.length === 0 && !isAdmin && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <p className="text-sm text-amber-600 flex items-center gap-2">
                <AlertTriangle size={16} />
                {lang === 'ar' ? 'لم يتم تعيين موقع عمل لك بعد. تواصل مع مديرك.' : 'No work location assigned yet. Contact your manager.'}
              </p>
            </div>
          )}

          {/* Location Selector & Buttons */}
          <div className="space-y-3">
            <Select value={workLocation} onValueChange={setWorkLocation} disabled={!!today.check_in}>
              <SelectTrigger className="h-12 rounded-xl" data-testid="work-location-select">
                <SelectValue placeholder={lang === 'ar' ? 'اختر موقع العمل' : 'Select work location'} />
              </SelectTrigger>
              <SelectContent>
                {assignedLocations.map(loc => (
                  <SelectItem key={loc.id} value={loc.id}>
                    <div className="flex items-center gap-2">
                      <Navigation size={14} className="text-primary" />
                      {lang === 'ar' ? loc.name_ar : loc.name}
                    </div>
                  </SelectItem>
                ))}
                {assignedLocations.length === 0 && (
                  <>
                    <SelectItem value="HQ">
                      <div className="flex items-center gap-2">
                        <Building2 size={14} className="text-primary" />
                        {t('attendance.hq')}
                      </div>
                    </SelectItem>
                    <SelectItem value="Project">
                      <div className="flex items-center gap-2">
                        <Navigation size={14} className="text-amber-500" />
                        {t('attendance.project')}
                      </div>
                    </SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>

            <div className="grid grid-cols-2 gap-3">
              <Button
                data-testid="check-in-btn"
                onClick={handleCheckIn}
                disabled={loading || !!today.check_in || !workLocation}
                className="h-14 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-base font-semibold"
              >
                <MapPin size={20} className="me-2" />
                {t('attendance.checkIn')}
                {today.check_in && (
                  <span className="ms-2 text-xs opacity-80">✓ {today.check_in.timestamp?.slice(11, 16)}</span>
                )}
              </Button>
              <Button
                data-testid="check-out-btn"
                onClick={handleCheckOut}
                disabled={loading || !today.check_in || !!today.check_out}
                variant="outline"
                className="h-14 rounded-xl text-base font-semibold"
              >
                <Clock size={20} className="me-2" />
                {t('attendance.checkOut')}
                {today.check_out && (
                  <span className="ms-2 text-xs opacity-80">✓ {today.check_out.timestamp?.slice(11, 16)}</span>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* History for Employee */}
      {(isEmployee || isAdmin) && history.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">{t('attendance.history')}</h2>
          <div className="space-y-2">
            {history.slice(0, 10).map((h, i) => (
              <div key={i} className="card-premium p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${h.type === 'check_in' ? 'bg-emerald-500/10' : 'bg-primary/10'}`}>
                    {h.type === 'check_in' ? (
                      <CheckCircle size={18} className="text-emerald-500" />
                    ) : (
                      <XCircle size={18} className="text-primary" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {h.type === 'check_in' ? t('attendance.checkIn') : t('attendance.checkOut')}
                    </p>
                    <p className="text-xs text-muted-foreground">{h.date}</p>
                  </div>
                </div>
                <div className="text-end">
                  <p className="text-sm font-mono font-semibold">{h.timestamp?.slice(11, 19)}</p>
                  {h.gps_status === 'valid' ? (
                    <span className="text-[10px] text-emerald-500">● GPS</span>
                  ) : (
                    <span className="text-[10px] text-muted-foreground">○ No GPS</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Admin View */}
      {isAdmin && (
        <div className="border-t border-border pt-5">
          <h2 className="text-lg font-semibold mb-4">{t('attendance.adminView')}</h2>
          
          {/* Period Filter */}
          <div className="flex gap-3 mb-4 flex-wrap">
            <Tabs value={period} onValueChange={setPeriod} className="w-full">
              <TabsList className="grid grid-cols-4 h-11 rounded-xl p-1 bg-muted/50">
                <TabsTrigger value="daily" className="rounded-lg text-xs">{t('attendance.daily')}</TabsTrigger>
                <TabsTrigger value="weekly" className="rounded-lg text-xs">{t('attendance.weekly')}</TabsTrigger>
                <TabsTrigger value="monthly" className="rounded-lg text-xs">{t('attendance.monthly')}</TabsTrigger>
                <TabsTrigger value="yearly" className="rounded-lg text-xs">{t('attendance.yearly')}</TabsTrigger>
              </TabsList>
            </Tabs>
            <Input
              type="date"
              value={dateFilter}
              onChange={e => setDateFilter(e.target.value)}
              className="w-full sm:w-auto h-11 rounded-xl"
            />
          </div>

          {/* Admin Table */}
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="hr-table">
              <thead>
                <tr>
                  <th>{t('employees.name')}</th>
                  <th>{t('attendance.date')}</th>
                  <th>{t('attendance.checkIn')}</th>
                  <th>{t('attendance.checkOut')}</th>
                  <th>GPS</th>
                </tr>
              </thead>
              <tbody>
                {adminData.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td>
                  </tr>
                ) : (
                  adminData.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <User size={14} className="text-primary" />
                          </div>
                          <span className="font-medium">{lang === 'ar' ? (r.employee_name_ar || r.employee_name) : r.employee_name}</span>
                        </div>
                      </td>
                      <td className="font-mono text-muted-foreground">{r.date}</td>
                      <td className="font-mono">{r.check_in || '-'}</td>
                      <td className="font-mono">{r.check_out || '-'}</td>
                      <td>
                        {r.gps_status === 'valid' ? (
                          <span className="badge badge-success">✓</span>
                        ) : (
                          <span className="badge badge-warning">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
