import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { MapPin, Clock, LogIn, LogOut, Loader2, AlertTriangle, CheckCircle, User, Calendar, Building2 } from 'lucide-react';
import { formatSaudiDate, formatSaudiTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

// أكواد الأخطاء المفصلة
const ERROR_CODES = {
  GPS_NOT_SUPPORTED: { code: 'E001', ar: 'المتصفح لا يدعم تحديد الموقع', en: 'Browser does not support GPS' },
  GPS_PERMISSION_DENIED: { code: 'E002', ar: 'تم رفض إذن الموقع - يرجى السماح من إعدادات المتصفح', en: 'Location permission denied' },
  GPS_POSITION_UNAVAILABLE: { code: 'E003', ar: 'تعذر تحديد الموقع - تأكد من تفعيل GPS في الجهاز', en: 'Position unavailable' },
  GPS_TIMEOUT: { code: 'E004', ar: 'انتهت مهلة تحديد الموقع - حاول مرة أخرى', en: 'Location timeout' },
  NO_ASSIGNED_LOCATIONS: { code: 'E005', ar: 'لا توجد مواقع عمل معينة لك - راجع الإدارة', en: 'No work locations assigned' },
  OUTSIDE_WORK_HOURS: { code: 'E006', ar: 'خارج أوقات العمل المحددة', en: 'Outside work hours' },
  OUTSIDE_GEOFENCE: { code: 'E007', ar: 'أنت خارج نطاق موقع العمل', en: 'Outside work location area' },
  ALREADY_CHECKED_IN: { code: 'E008', ar: 'تم تسجيل الدخول مسبقاً اليوم', en: 'Already checked in today' },
  NOT_CHECKED_IN: { code: 'E009', ar: 'لم تسجل دخول اليوم', en: 'Not checked in today' },
  ALREADY_CHECKED_OUT: { code: 'E010', ar: 'تم تسجيل الخروج مسبقاً اليوم', en: 'Already checked out today' },
};

export default function AttendancePage() {
  const { user } = useAuth();
  const { lang } = useLanguage();
  
  // الحالات
  const [loading, setLoading] = useState(false);
  const [todayRecord, setTodayRecord] = useState(null);
  const [assignedLocations, setAssignedLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [adminData, setAdminData] = useState([]);
  
  // حالة GPS
  const [gps, setGps] = useState({
    status: 'checking', // checking, ready, error
    lat: null,
    lng: null,
    errorCode: null,
    errorMessage: null
  });
  
  // حالة أوقات العمل
  const [workTimeStatus, setWorkTimeStatus] = useState({
    canCheckIn: false,
    canCheckOut: false,
    message: '',
    currentLocation: null
  });
  
  // حوار التأكيد
  const [confirmDialog, setConfirmDialog] = useState({ open: false, type: null });
  
  const isEmployee = user?.role === 'employee';
  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);

  // ============ دوال GPS ============
  const getGPSPosition = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject({ code: 0, message: 'GPS_NOT_SUPPORTED' });
        return;
      }
      
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracy: position.coords.accuracy
          });
        },
        (error) => {
          reject(error);
        },
        { 
          enableHighAccuracy: true, 
          timeout: 15000, 
          maximumAge: 0 
        }
      );
    });
  }, []);

  const initGPS = useCallback(async () => {
    setGps(prev => ({ ...prev, status: 'checking' }));
    
    try {
      const position = await getGPSPosition();
      setGps({
        status: 'ready',
        lat: position.lat,
        lng: position.lng,
        errorCode: null,
        errorMessage: null
      });
      return position;
    } catch (error) {
      let errorInfo;
      
      if (error.code === 0 || error.message === 'GPS_NOT_SUPPORTED') {
        errorInfo = ERROR_CODES.GPS_NOT_SUPPORTED;
      } else if (error.code === 1) {
        errorInfo = ERROR_CODES.GPS_PERMISSION_DENIED;
      } else if (error.code === 2) {
        errorInfo = ERROR_CODES.GPS_POSITION_UNAVAILABLE;
      } else if (error.code === 3) {
        errorInfo = ERROR_CODES.GPS_TIMEOUT;
      } else {
        errorInfo = { code: 'E000', ar: 'خطأ غير معروف', en: 'Unknown error' };
      }
      
      setGps({
        status: 'error',
        lat: null,
        lng: null,
        errorCode: errorInfo.code,
        errorMessage: lang === 'ar' ? errorInfo.ar : errorInfo.en
      });
      
      return null;
    }
  }, [getGPSPosition, lang]);

  // ============ جلب البيانات ============
  const fetchData = useCallback(async () => {
    try {
      // جلب سجل اليوم
      const todayRes = await api.get('/api/attendance/today');
      setTodayRecord(todayRes.data);
      
      // جلب مواقع العمل المعينة للموظف
      if (user?.employee_id) {
        const locRes = await api.get(`/api/employees/${user.employee_id}/assigned-locations`);
        setAssignedLocations(locRes.data || []);
        if (locRes.data?.length === 1) {
          setSelectedLocation(locRes.data[0].id);
        }
      }
      
      // جلب بيانات الإدارة
      if (isAdmin) {
        const adminRes = await api.get('/api/attendance/admin-all');
        setAdminData(adminRes.data || []);
      }
    } catch (err) {
      console.error('Error fetching attendance data:', err);
    }
  }, [user?.employee_id, isAdmin]);

  // ============ التحقق من أوقات العمل ============
  const checkWorkTime = useCallback(() => {
    if (assignedLocations.length === 0) {
      setWorkTimeStatus({
        canCheckIn: false,
        canCheckOut: false,
        message: ERROR_CODES.NO_ASSIGNED_LOCATIONS[lang === 'ar' ? 'ar' : 'en'],
        currentLocation: null
      });
      return;
    }
    
    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    
    // البحث عن موقع يسمح بالبصمة الآن
    let canCheckInNow = false;
    let canCheckOutNow = false;
    let activeLocation = null;
    
    for (const loc of assignedLocations) {
      const [startH, startM] = (loc.work_start || '08:00').split(':').map(Number);
      const [endH, endM] = (loc.work_end || '17:00').split(':').map(Number);
      const workStart = startH * 60 + startM;
      const workEnd = endH * 60 + endM;
      
      const earlyMinutes = loc.allow_early_checkin_minutes || 30;
      const graceMinutes = loc.grace_checkin_minutes || 15;
      const graceCheckoutMinutes = loc.grace_checkout_minutes || 15;
      
      // وقت بداية التسجيل = وقت البداية - السماح المبكر
      const checkInStart = workStart - earlyMinutes;
      // نهاية وقت التسجيل = نهاية الدوام + السماح
      const checkInEnd = workEnd + graceCheckoutMinutes;
      
      // وقت الخروج = من بداية الدوام حتى نهايته + السماح
      const checkOutStart = workStart;
      const checkOutEnd = workEnd + graceCheckoutMinutes;
      
      if (currentTime >= checkInStart && currentTime <= checkInEnd) {
        canCheckInNow = true;
        activeLocation = loc;
      }
      
      if (currentTime >= checkOutStart && currentTime <= checkOutEnd) {
        canCheckOutNow = true;
        if (!activeLocation) activeLocation = loc;
      }
    }
    
    // التحقق من حالة البصمة اليوم
    const hasCheckedIn = todayRecord?.check_in;
    const hasCheckedOut = todayRecord?.check_out;
    
    setWorkTimeStatus({
      canCheckIn: canCheckInNow && !hasCheckedIn,
      canCheckOut: canCheckOutNow && hasCheckedIn && !hasCheckedOut,
      message: !canCheckInNow && !canCheckOutNow 
        ? (lang === 'ar' ? 'خارج أوقات العمل' : 'Outside work hours')
        : '',
      currentLocation: activeLocation
    });
  }, [assignedLocations, todayRecord, lang]);

  // ============ تسجيل الدخول ============
  const handleCheckIn = async () => {
    if (!selectedLocation && assignedLocations.length > 1) {
      toast.error(lang === 'ar' ? 'اختر موقع العمل أولاً' : 'Select work location first');
      return;
    }
    
    const locationId = selectedLocation || assignedLocations[0]?.id;
    
    setLoading(true);
    try {
      // التأكد من GPS
      let currentGps = gps;
      if (gps.status !== 'ready') {
        const position = await initGPS();
        if (!position) {
          toast.error(`[${gps.errorCode}] ${gps.errorMessage}`);
          setLoading(false);
          return;
        }
        currentGps = { lat: position.lat, lng: position.lng };
      }
      
      const response = await api.post('/api/attendance/check-in', {
        work_location: locationId,
        lat: currentGps.lat,
        lng: currentGps.lng,
        gps_available: true
      });
      
      toast.success(lang === 'ar' ? 'تم تسجيل الدخول بنجاح' : 'Check-in successful');
      
      if (response.data?.warnings?.length > 0) {
        response.data.warnings.forEach(w => {
          toast.warning(w.message_ar || w.message);
        });
      }
      
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        toast.error(`[${detail.code || 'ERR'}] ${detail.message_ar || detail.message}`);
      } else {
        toast.error(detail || (lang === 'ar' ? 'فشل تسجيل الدخول' : 'Check-in failed'));
      }
    } finally {
      setLoading(false);
    }
  };

  // ============ تسجيل الخروج ============
  const handleCheckOut = async () => {
    setLoading(true);
    try {
      // التأكد من GPS
      let currentGps = gps;
      if (gps.status !== 'ready') {
        const position = await initGPS();
        if (!position) {
          toast.error(`[${gps.errorCode}] ${gps.errorMessage}`);
          setLoading(false);
          return;
        }
        currentGps = { lat: position.lat, lng: position.lng };
      }
      
      await api.post('/api/attendance/check-out', {
        lat: currentGps.lat,
        lng: currentGps.lng,
        gps_available: true
      });
      
      toast.success(lang === 'ar' ? 'تم تسجيل الخروج بنجاح' : 'Check-out successful');
      setConfirmDialog({ open: false, type: null });
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        toast.error(`[${detail.code || 'ERR'}] ${detail.message_ar || detail.message}`);
      } else {
        toast.error(detail || (lang === 'ar' ? 'فشل تسجيل الخروج' : 'Check-out failed'));
      }
    } finally {
      setLoading(false);
    }
  };

  // ============ التهيئة ============
  useEffect(() => {
    fetchData();
    initGPS();
  }, []);

  useEffect(() => {
    checkWorkTime();
  }, [assignedLocations, todayRecord]);

  // ============ العرض ============
  return (
    <div className="space-y-6" data-testid="attendance-page">
      <h1 className="text-2xl font-bold">{lang === 'ar' ? 'الحضور والانصراف' : 'Attendance'}</h1>

      {/* بطاقة البصمة للموظف */}
      {(isEmployee || isAdmin) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock size={20} />
              {lang === 'ar' ? 'تسجيل الحضور' : 'Attendance Record'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            
            {/* حالة GPS */}
            <div className={`p-3 rounded-lg border ${
              gps.status === 'checking' ? 'bg-blue-50 border-blue-200 text-blue-700' :
              gps.status === 'ready' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
              'bg-red-50 border-red-200 text-red-700'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {gps.status === 'checking' && <Loader2 size={18} className="animate-spin" />}
                  {gps.status === 'ready' && <CheckCircle size={18} />}
                  {gps.status === 'error' && <AlertTriangle size={18} />}
                  <span className="text-sm font-medium">
                    {gps.status === 'checking' && (lang === 'ar' ? 'جاري تحديد الموقع...' : 'Getting location...')}
                    {gps.status === 'ready' && (lang === 'ar' ? 'تم تحديد الموقع ✓' : 'Location ready ✓')}
                    {gps.status === 'error' && `[${gps.errorCode}] ${gps.errorMessage}`}
                  </span>
                </div>
                {gps.status === 'error' && (
                  <Button size="sm" variant="outline" onClick={initGPS}>
                    {lang === 'ar' ? 'إعادة المحاولة' : 'Retry'}
                  </Button>
                )}
              </div>
            </div>

            {/* مواقع العمل المعينة */}
            {assignedLocations.length > 0 && (
              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                <p className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Building2 size={16} />
                  {lang === 'ar' ? 'مواقع العمل المعينة لك:' : 'Your assigned locations:'}
                </p>
                <div className="flex flex-wrap gap-2">
                  {assignedLocations.map(loc => (
                    <span key={loc.id} className="px-2 py-1 bg-background rounded border text-sm">
                      {loc.name_ar || loc.name} ({loc.work_start} - {loc.work_end})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* اختيار الموقع إذا كان أكثر من واحد */}
            {assignedLocations.length > 1 && !todayRecord?.check_in && (
              <div>
                <Label>{lang === 'ar' ? 'اختر موقع البصمة:' : 'Select location:'}</Label>
                <Select value={selectedLocation} onValueChange={setSelectedLocation}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder={lang === 'ar' ? 'اختر الموقع' : 'Select location'} />
                  </SelectTrigger>
                  <SelectContent>
                    {assignedLocations.map(loc => (
                      <SelectItem key={loc.id} value={loc.id}>
                        {loc.name_ar || loc.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* لا توجد مواقع معينة */}
            {assignedLocations.length === 0 && (
              <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-700">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={18} />
                  <span className="text-sm">[E005] {lang === 'ar' ? 'لا توجد مواقع عمل معينة لك - راجع الإدارة' : 'No locations assigned'}</span>
                </div>
              </div>
            )}

            {/* حالة اليوم */}
            {todayRecord && (
              <div className="p-3 rounded-lg bg-slate-50 border">
                <p className="text-sm font-medium mb-2">{lang === 'ar' ? 'سجل اليوم:' : "Today's record:"}</p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">{lang === 'ar' ? 'الدخول:' : 'Check-in:'}</span>
                    <span className="font-mono ms-2">{todayRecord.check_in_time || '-'}</span>
                    {todayRecord.work_location && (
                      <span className="text-xs text-muted-foreground ms-1">({todayRecord.work_location})</span>
                    )}
                  </div>
                  <div>
                    <span className="text-muted-foreground">{lang === 'ar' ? 'الخروج:' : 'Check-out:'}</span>
                    <span className="font-mono ms-2">{todayRecord.check_out_time || '-'}</span>
                  </div>
                </div>
              </div>
            )}

            {/* أزرار البصمة */}
            <div className="flex gap-3">
              {/* زر تسجيل الدخول */}
              <Button
                onClick={handleCheckIn}
                disabled={loading || !workTimeStatus.canCheckIn || gps.status === 'checking' || assignedLocations.length === 0}
                className={`flex-1 h-14 text-lg ${
                  workTimeStatus.canCheckIn && gps.status === 'ready'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-gray-300 cursor-not-allowed'
                }`}
                data-testid="check-in-btn"
              >
                {loading ? (
                  <Loader2 size={20} className="animate-spin me-2" />
                ) : (
                  <LogIn size={20} className="me-2" />
                )}
                {lang === 'ar' ? 'تسجيل الدخول' : 'Check In'}
              </Button>
              
              {/* زر تسجيل الخروج */}
              <Button
                onClick={() => setConfirmDialog({ open: true, type: 'checkout' })}
                disabled={loading || !workTimeStatus.canCheckOut || gps.status === 'checking'}
                className={`flex-1 h-14 text-lg ${
                  workTimeStatus.canCheckOut && gps.status === 'ready'
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-gray-300 cursor-not-allowed'
                }`}
                data-testid="check-out-btn"
              >
                {loading ? (
                  <Loader2 size={20} className="animate-spin me-2" />
                ) : (
                  <LogOut size={20} className="me-2" />
                )}
                {lang === 'ar' ? 'تسجيل الخروج' : 'Check Out'}
              </Button>
            </div>

            {/* رسالة خارج أوقات العمل */}
            {workTimeStatus.message && (
              <div className="p-2 rounded bg-amber-100 text-amber-700 text-sm text-center">
                [E006] {workTimeStatus.message}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* حوار تأكيد الخروج */}
      <Dialog open={confirmDialog.open} onOpenChange={(open) => setConfirmDialog({ open, type: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle size={20} />
              {lang === 'ar' ? 'تأكيد تسجيل الخروج' : 'Confirm Check-out'}
            </DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">
            {lang === 'ar' 
              ? 'هل أنت متأكد من تسجيل الخروج؟ لا يمكن التراجع عن هذا الإجراء.'
              : 'Are you sure you want to check out? This action cannot be undone.'}
          </p>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => setConfirmDialog({ open: false, type: null })}>
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleCheckOut}
              disabled={loading}
            >
              {loading && <Loader2 size={16} className="animate-spin me-2" />}
              {lang === 'ar' ? 'نعم، سجل الخروج' : 'Yes, Check Out'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* جدول الحضور للإدارة */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle>{lang === 'ar' ? 'سجل حضور الموظفين' : 'Employee Attendance'}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-slate-50">
                    <th className="p-3 text-right">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'الدخول' : 'In'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'الخروج' : 'Out'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'موقع البصمة' : 'Location'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'GPS' : 'GPS'}</th>
                  </tr>
                </thead>
                <tbody>
                  {adminData.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-muted-foreground">
                        {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                      </td>
                    </tr>
                  ) : (
                    adminData.map((record, i) => (
                      <tr key={i} className="border-b hover:bg-slate-50">
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                              <User size={14} className="text-primary" />
                            </div>
                            <span className="font-medium">{record.employee_name_ar || record.employee_name}</span>
                          </div>
                        </td>
                        <td className="p-3 font-mono text-muted-foreground">{record.date}</td>
                        <td className="p-3 font-mono">{record.check_in_time || '-'}</td>
                        <td className="p-3 font-mono">{record.check_out_time || '-'}</td>
                        <td className="p-3">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                            {record.location_name_ar || record.location_name || record.work_location || '-'}
                          </span>
                          {record.checkout_location_name && record.checkout_location_name !== record.location_name && (
                            <div className="text-xs text-muted-foreground mt-1">
                              خروج: {record.checkout_location_name}
                            </div>
                          )}
                        </td>
                        <td className="p-3">
                          {record.gps_valid_in ? (
                            <span className="text-emerald-600">✓</span>
                          ) : record.check_in ? (
                            <span className="text-red-600">✗</span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
