import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { MapPin, Clock, CheckCircle, XCircle, AlertTriangle, Building2, Navigation, CalendarDays, User, Moon, Edit, Eye, FileText, UserX, Timer, ChevronLeft } from 'lucide-react';
import { formatGregorianHijri, formatSaudiTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

// Format date with Gregorian as primary and Hijri as secondary
function formatDateWithHijri(date, lang) {
  const d = new Date(date);
  
  // Gregorian date
  const gregorian = d.toLocaleDateString(lang === 'ar' ? 'ar-EG' : 'en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  
  // Hijri date - use Arabic numerals only for Arabic
  const hijriLocale = lang === 'ar' ? 'ar-SA-u-ca-islamic-nu-arab' : 'en-SA-u-ca-islamic';
  let hijri = d.toLocaleDateString(hijriLocale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    calendar: 'islamic'
  });
  
  // For English, convert any Arabic numerals to Western numerals
  if (lang !== 'ar') {
    hijri = hijri.replace(/[\u0660-\u0669]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x0660 + 48));
  }
  
  return { gregorian, hijri };
}

// طلبات الحضور والبصمة (منفصلة عن طلبات الإجازات)
const ATTENDANCE_REQUEST_TYPES = {
  forget_checkin: { name_ar: 'نسيان بصمة', name_en: 'Forgot Check-in', icon: Timer },
  field_work: { name_ar: 'مهمة خارجية', name_en: 'Field Work', icon: Navigation },
  early_leave_request: { name_ar: 'طلب خروج مبكر', name_en: 'Early Leave Request', icon: ChevronLeft },
  late_excuse: { name_ar: 'تبرير تأخير', name_en: 'Late Excuse', icon: Clock },
};

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
  
  // حالات جديدة
  const [activeTab, setActiveTab] = useState('my-attendance');
  const [teamSummary, setTeamSummary] = useState({ present: 0, absent: 0, on_leave: 0, late: 0 });
  const [ramadanSettings, setRamadanSettings] = useState(null);
  const [showRamadanDialog, setShowRamadanDialog] = useState(false);
  const [ramadanForm, setRamadanForm] = useState({ start_date: '', end_date: '' });
  const [mapVisible, setMapVisible] = useState(false);
  const [attendanceRequests, setAttendanceRequests] = useState([]);

  const isEmployee = ['employee', 'supervisor'].includes(user?.role);
  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);
  const isStas = user?.role === 'stas';
  
  // Get today's date formatted
  const todayFormatted = formatDateWithHijri(new Date(), lang);

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
      
      // حساب ملخص الفريق
      const present = res.data.filter(r => r.check_in).length;
      const absent = res.data.filter(r => !r.check_in && !r.on_leave).length;
      const onLeave = res.data.filter(r => r.on_leave).length;
      const late = res.data.filter(r => r.is_late).length;
      setTeamSummary({ present, absent, on_leave: onLeave, late });
    } catch (err) {}
  };

  const fetchRamadanSettings = async () => {
    try {
      const res = await api.get('/api/stas/ramadan');
      setRamadanSettings(res.data);
    } catch (err) {}
  };

  const fetchMapVisibility = async () => {
    try {
      // استخدام endpoint عام للقراءة
      const res = await api.get('/api/stas/settings/map-visibility/public');
      setMapVisible(res.data?.show_map_to_employees || false);
    } catch (err) {}
  };

  const fetchAttendanceRequests = async () => {
    try {
      // جلب طلبات الحضور فقط (منفصلة عن الإجازات)
      const res = await api.get('/api/transactions', {
        params: { types: 'forget_checkin,field_work,early_leave_request,late_excuse' }
      });
      setAttendanceRequests(res.data || []);
    } catch (err) {}
  };

  const fetchData = () => {
    if (isEmployee || isAdmin) {
      api.get('/api/attendance/today').then(r => setToday(r.data)).catch(() => {});
      api.get('/api/attendance/history').then(r => setHistory(r.data)).catch(() => {});
    }
    if (isAdmin) {
      fetchAdmin();
      fetchRamadanSettings();
      fetchMapVisibility();
      fetchAttendanceRequests();
    }
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

  // تفعيل دوام رمضان
  const handleActivateRamadan = async () => {
    try {
      await api.post('/api/stas/ramadan/activate', ramadanForm);
      toast.success(lang === 'ar' ? 'تم تفعيل دوام رمضان' : 'Ramadan mode activated');
      setShowRamadanDialog(false);
      fetchRamadanSettings();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  // إلغاء دوام رمضان
  const handleDeactivateRamadan = async () => {
    try {
      await api.post('/api/stas/ramadan/deactivate');
      toast.success(lang === 'ar' ? 'تم إلغاء دوام رمضان' : 'Ramadan mode deactivated');
      fetchRamadanSettings();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  // تحديث إظهار الخريطة
  const handleToggleMapVisibility = async () => {
    try {
      await api.post(`/api/stas/settings/map-visibility?show=${!mapVisible}`);
      setMapVisible(!mapVisible);
      toast.success(lang === 'ar' ? 'تم تحديث الإعداد' : 'Setting updated');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  // تشغيل حساب الغياب اليدوي
  const handleCalculateAttendance = async () => {
    try {
      setLoading(true);
      await api.post('/api/stas/attendance/calculate-daily');
      toast.success(lang === 'ar' ? 'تم حساب الحضور اليومي' : 'Daily attendance calculated');
      fetchAdmin();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="attendance-page">
      {/* Header */}
      <div>
        <h1 className="text-xl md:text-2xl font-bold">{t('nav.attendance')}</h1>
        <p className="text-sm text-foreground mt-1">{todayFormatted.gregorian}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{todayFormatted.hijri}</p>
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
                  <span className="ms-2 text-xs opacity-80">✓ {formatSaudiTime(today.check_in.timestamp)}</span>
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
                  <span className="ms-2 text-xs opacity-80">✓ {formatSaudiTime(today.check_out.timestamp)}</span>
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
                    <p className="text-xs text-muted-foreground">{formatGregorianHijri(h.date).combined}</p>
                  </div>
                </div>
                <div className="text-end">
                  <p className="text-sm font-mono font-semibold">{formatSaudiTime(h.timestamp)}</p>
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
          {/* Admin Header with Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-lg font-semibold">{lang === 'ar' ? 'حضور الفريق' : 'Team Attendance'}</h2>
            
            <div className="flex flex-wrap gap-2">
              {/* رمضان Mode Button - STAS Only */}
              {isStas && (
                <>
                  {ramadanSettings?.is_active ? (
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={handleDeactivateRamadan}
                      className="text-amber-600 border-amber-600 hover:bg-amber-50"
                    >
                      <Moon size={14} className="me-1" />
                      {lang === 'ar' ? 'إلغاء دوام رمضان' : 'Deactivate Ramadan'}
                    </Button>
                  ) : (
                    <Dialog open={showRamadanDialog} onOpenChange={setShowRamadanDialog}>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          <Moon size={14} className="me-1" />
                          {lang === 'ar' ? 'تفعيل دوام رمضان' : 'Activate Ramadan'}
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>{lang === 'ar' ? 'تفعيل دوام رمضان (6 ساعات)' : 'Activate Ramadan Mode (6 hours)'}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                          <div>
                            <label className="text-sm font-medium">{lang === 'ar' ? 'من تاريخ' : 'Start Date'}</label>
                            <Input 
                              type="date" 
                              value={ramadanForm.start_date}
                              onChange={e => setRamadanForm({...ramadanForm, start_date: e.target.value})}
                              className="mt-1"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">{lang === 'ar' ? 'إلى تاريخ' : 'End Date'}</label>
                            <Input 
                              type="date" 
                              value={ramadanForm.end_date}
                              onChange={e => setRamadanForm({...ramadanForm, end_date: e.target.value})}
                              className="mt-1"
                            />
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {lang === 'ar' 
                              ? 'ملاحظة: ساعات الدوام 6 ساعات، أوقات الدخول والخروج تُحدد حسب القسم'
                              : 'Note: 6 working hours, entry/exit times vary by department'}
                          </p>
                          <Button onClick={handleActivateRamadan} className="w-full">
                            {lang === 'ar' ? 'تفعيل' : 'Activate'}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                  
                  {/* Map Visibility Toggle */}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleToggleMapVisibility}
                    className={mapVisible ? 'text-emerald-600 border-emerald-600' : ''}
                  >
                    <Eye size={14} className="me-1" />
                    {mapVisible 
                      ? (lang === 'ar' ? 'إخفاء الخريطة' : 'Hide Map')
                      : (lang === 'ar' ? 'إظهار الخريطة' : 'Show Map')}
                  </Button>
                  
                  {/* Calculate Attendance Button */}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleCalculateAttendance}
                    disabled={loading}
                  >
                    <FileText size={14} className="me-1" />
                    {lang === 'ar' ? 'حساب الغياب' : 'Calculate Absence'}
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Ramadan Mode Notice */}
          {ramadanSettings?.is_active && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 mb-4 flex items-center gap-2">
              <Moon size={18} className="text-amber-600" />
              <span className="text-sm text-amber-700">
                {lang === 'ar' 
                  ? `دوام رمضان مفعل (6 ساعات) - من ${ramadanSettings.start_date} إلى ${ramadanSettings.end_date}`
                  : `Ramadan mode active (6 hours) - ${ramadanSettings.start_date} to ${ramadanSettings.end_date}`}
              </span>
            </div>
          )}

          {/* Team Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="card-premium p-4 text-center">
              <CheckCircle className="mx-auto text-emerald-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-emerald-600">{teamSummary.present}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'حاضر' : 'Present'}</p>
            </div>
            <div className="card-premium p-4 text-center">
              <UserX className="mx-auto text-red-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-red-600">{teamSummary.absent}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'غائب' : 'Absent'}</p>
            </div>
            <div className="card-premium p-4 text-center">
              <CalendarDays className="mx-auto text-blue-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-blue-600">{teamSummary.on_leave}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'إجازة' : 'On Leave'}</p>
            </div>
            <div className="card-premium p-4 text-center">
              <Timer className="mx-auto text-amber-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-amber-600">{teamSummary.late}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'متأخر' : 'Late'}</p>
            </div>
          </div>
          
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

          {/* Admin Table - Enhanced */}
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="hr-table">
              <thead>
                <tr>
                  <th>{t('employees.name')}</th>
                  <th>{t('attendance.date')}</th>
                  <th>{t('attendance.checkIn')}</th>
                  <th>{t('attendance.checkOut')}</th>
                  <th>{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                  <th>GPS</th>
                  {isStas && <th>{lang === 'ar' ? 'إجراء' : 'Action'}</th>}
                </tr>
              </thead>
              <tbody>
                {adminData.length === 0 ? (
                  <tr>
                    <td colSpan={isStas ? 7 : 6} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td>
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
                      <td className="font-mono text-muted-foreground">{formatGregorianHijri(r.date).combined}</td>
                      <td className="font-mono">{r.check_in || '-'}</td>
                      <td className="font-mono">{r.check_out || '-'}</td>
                      <td>
                        {r.on_leave ? (
                          <span className="badge bg-blue-100 text-blue-700">{lang === 'ar' ? 'إجازة' : 'Leave'}</span>
                        ) : r.check_in ? (
                          r.is_late ? (
                            <span className="badge bg-amber-100 text-amber-700">{lang === 'ar' ? 'متأخر' : 'Late'}</span>
                          ) : (
                            <span className="badge bg-emerald-100 text-emerald-700">{lang === 'ar' ? 'حاضر' : 'Present'}</span>
                          )
                        ) : (
                          <span className="badge bg-red-100 text-red-700">{lang === 'ar' ? 'غائب' : 'Absent'}</span>
                        )}
                      </td>
                      <td>
                        {r.gps_status === 'valid' ? (
                          <span className="badge badge-success">✓</span>
                        ) : (
                          <span className="badge badge-warning">-</span>
                        )}
                      </td>
                      {isStas && (
                        <td>
                          <Button variant="ghost" size="sm" className="h-8">
                            <Edit size={14} />
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* طلبات الحضور والبصمة */}
          {attendanceRequests.length > 0 && (
            <div className="mt-6">
              <h3 className="text-base font-semibold mb-3">{lang === 'ar' ? 'طلبات الحضور والبصمة' : 'Attendance Requests'}</h3>
              <div className="space-y-2">
                {attendanceRequests.slice(0, 5).map((req, i) => {
                  const reqType = ATTENDANCE_REQUEST_TYPES[req.type];
                  const Icon = reqType?.icon || FileText;
                  return (
                    <div key={i} className="card-premium p-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                          <Icon size={18} className="text-primary" />
                        </div>
                        <div>
                          <p className="text-sm font-medium">{lang === 'ar' ? reqType?.name_ar : reqType?.name_en}</p>
                          <p className="text-xs text-muted-foreground">{req.ref_no} - {req.employee_name}</p>
                        </div>
                      </div>
                      <span className={`badge ${req.status === 'executed' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                        {req.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
