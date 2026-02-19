import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { 
  MapPin, Clock, LogIn, LogOut, Loader2, AlertTriangle, CheckCircle, 
  User, Calendar, Building2, RefreshCw, FileText, Send, History,
  Navigation, Wifi, WifiOff, MapPinOff, Timer
} from 'lucide-react';
import { formatSaudiDate, formatSaudiTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

// أنواع طلبات الحضور
const REQUEST_TYPES = [
  { value: 'forget_checkin', label_ar: 'نسيان بصمة', label_en: 'Forgot Punch', icon: '🔔' },
  { value: 'field_work', label_ar: 'مهمة خارجية', label_en: 'Field Work', icon: '🚗' },
  { value: 'early_leave_request', label_ar: 'طلب خروج مبكر', label_en: 'Early Leave', icon: '🚪' },
  { value: 'late_excuse', label_ar: 'تبرير تأخير', label_en: 'Late Excuse', icon: '⏰' },
];

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
  
  // الحالات الأساسية
  const [loading, setLoading] = useState(false);
  const [todayRecord, setTodayRecord] = useState(null);
  const [assignedLocations, setAssignedLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [adminData, setAdminData] = useState([]);
  const [activeTab, setActiveTab] = useState('punch');
  
  // حالة GPS
  const [gps, setGps] = useState({
    status: 'checking', // checking, ready, error
    lat: null,
    lng: null,
    accuracy: null,
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
  
  // حالة الطلبات
  const [requestForm, setRequestForm] = useState({
    request_type: '',
    date: new Date().toISOString().split('T')[0],
    reason: '',
    from_time: '',
    to_time: ''
  });
  const [myRequests, setMyRequests] = useState([]);
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [submittingRequest, setSubmittingRequest] = useState(false);
  
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
        accuracy: position.accuracy,
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
        accuracy: null,
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
        try {
          const locRes = await api.get(`/api/employees/${user.employee_id}/assigned-locations`);
          const locs = locRes.data || [];
          setAssignedLocations(locs);
          if (locs.length === 1) {
            setSelectedLocation(locs[0].id);
          }
        } catch (err) {
          console.error('Error fetching locations:', err);
          setAssignedLocations([]);
        }
      }
      
      // جلب بيانات الإدارة
      if (isAdmin) {
        const adminRes = await api.get('/api/attendance/admin');
        setAdminData(adminRes.data || []);
      }
    } catch (err) {
      console.error('Error fetching attendance data:', err);
    }
  }, [user?.employee_id, isAdmin]);

  // جلب طلبات الموظف
  const fetchMyRequests = useCallback(async () => {
    try {
      const res = await api.get('/api/transactions', {
        params: { 
          category: 'attendance',
          employee_id: user?.employee_id 
        }
      });
      setMyRequests(res.data?.transactions || res.data || []);
    } catch (err) {
      console.error('Error fetching requests:', err);
    }
  }, [user?.employee_id]);

  // ============ التحقق من أوقات العمل ============
  const checkWorkTime = useCallback(() => {
    if (assignedLocations.length === 0) {
      setWorkTimeStatus({
        canCheckIn: false,
        canCheckOut: false,
        message: lang === 'ar' ? 'لا توجد مواقع عمل معينة' : 'No assigned locations',
        currentLocation: null
      });
      return;
    }
    
    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    
    let canCheckInNow = false;
    let canCheckOutNow = false;
    let activeLocation = null;
    
    for (const loc of assignedLocations) {
      const [startH, startM] = (loc.work_start || '08:00').split(':').map(Number);
      const [endH, endM] = (loc.work_end || '17:00').split(':').map(Number);
      const workStart = startH * 60 + startM;
      const workEnd = endH * 60 + endM;
      
      const earlyMinutes = loc.allow_early_checkin_minutes || 30;
      const graceCheckoutMinutes = loc.grace_checkout_minutes || 15;
      
      const checkInStart = workStart - earlyMinutes;
      const checkInEnd = workEnd + graceCheckoutMinutes;
      const checkOutStart = workStart;
      const checkOutEnd = workEnd + graceCheckoutMinutes + 60;
      
      if (currentTime >= checkInStart && currentTime <= checkInEnd) {
        canCheckInNow = true;
        activeLocation = loc;
      }
      
      if (currentTime >= checkOutStart && currentTime <= checkOutEnd) {
        canCheckOutNow = true;
        if (!activeLocation) activeLocation = loc;
      }
    }
    
    // التحقق من بيانات اليوم الصحيحة
    const hasCheckedIn = todayRecord?.check_in !== null && todayRecord?.check_in !== undefined;
    const hasCheckedOut = todayRecord?.check_out !== null && todayRecord?.check_out !== undefined;
    
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
        latitude: currentGps.lat,
        longitude: currentGps.lng,
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
        latitude: currentGps.lat,
        longitude: currentGps.lng,
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

  // ============ إرسال طلب حضور ============
  const handleSubmitRequest = async () => {
    if (!requestForm.request_type) {
      toast.error(lang === 'ar' ? 'اختر نوع الطلب' : 'Select request type');
      return;
    }
    if (!requestForm.date) {
      toast.error(lang === 'ar' ? 'حدد التاريخ' : 'Select date');
      return;
    }
    if (!requestForm.reason.trim()) {
      toast.error(lang === 'ar' ? 'اكتب السبب' : 'Enter reason');
      return;
    }
    
    setSubmittingRequest(true);
    try {
      await api.post('/api/attendance/request', requestForm);
      toast.success(lang === 'ar' ? 'تم إرسال الطلب بنجاح' : 'Request submitted');
      setRequestDialogOpen(false);
      setRequestForm({
        request_type: '',
        date: new Date().toISOString().split('T')[0],
        reason: '',
        from_time: '',
        to_time: ''
      });
      fetchMyRequests();
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(detail || (lang === 'ar' ? 'فشل إرسال الطلب' : 'Failed to submit'));
    } finally {
      setSubmittingRequest(false);
    }
  };

  // ============ التهيئة ============
  useEffect(() => {
    fetchData();
    fetchMyRequests();
    initGPS();
  }, []);

  useEffect(() => {
    checkWorkTime();
  }, [assignedLocations, todayRecord]);

  // ============ مكون حالة GPS ============
  const GPSStatusCard = () => (
    <div className={`p-4 rounded-xl border-2 transition-all ${
      gps.status === 'checking' ? 'bg-blue-50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800' :
      gps.status === 'ready' ? 'bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800' :
      'bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
            gps.status === 'checking' ? 'bg-blue-100 dark:bg-blue-900' :
            gps.status === 'ready' ? 'bg-emerald-100 dark:bg-emerald-900' :
            'bg-red-100 dark:bg-red-900'
          }`}>
            {gps.status === 'checking' && <Loader2 size={24} className="animate-spin text-blue-600" />}
            {gps.status === 'ready' && <Navigation size={24} className="text-emerald-600" />}
            {gps.status === 'error' && <MapPinOff size={24} className="text-red-600" />}
          </div>
          <div>
            <p className={`font-semibold ${
              gps.status === 'checking' ? 'text-blue-700 dark:text-blue-300' :
              gps.status === 'ready' ? 'text-emerald-700 dark:text-emerald-300' :
              'text-red-700 dark:text-red-300'
            }`}>
              {gps.status === 'checking' && (lang === 'ar' ? 'جاري تحديد الموقع...' : 'Getting location...')}
              {gps.status === 'ready' && (lang === 'ar' ? 'تم تحديد الموقع بنجاح' : 'Location ready')}
              {gps.status === 'error' && `[${gps.errorCode}] ${gps.errorMessage}`}
            </p>
            {gps.status === 'ready' && gps.accuracy && (
              <p className="text-sm text-muted-foreground">
                {lang === 'ar' ? `الدقة: ${Math.round(gps.accuracy)} متر` : `Accuracy: ${Math.round(gps.accuracy)}m`}
              </p>
            )}
          </div>
        </div>
        {gps.status === 'error' && (
          <Button size="sm" variant="outline" onClick={initGPS} className="shrink-0">
            <RefreshCw size={16} className="me-1" />
            {lang === 'ar' ? 'إعادة المحاولة' : 'Retry'}
          </Button>
        )}
        {gps.status === 'ready' && (
          <CheckCircle size={28} className="text-emerald-500 shrink-0" />
        )}
      </div>
    </div>
  );

  // ============ العرض ============
  return (
    <div className="space-y-6 max-w-7xl mx-auto" data-testid="attendance-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Clock className="text-primary" />
          {lang === 'ar' ? 'الحضور والانصراف' : 'Attendance'}
        </h1>
        <Button variant="outline" size="sm" onClick={() => { fetchData(); initGPS(); }}>
          <RefreshCw size={16} className="me-1" />
          {lang === 'ar' ? 'تحديث' : 'Refresh'}
        </Button>
      </div>

      {/* التبويبات */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-3 mb-4">
          <TabsTrigger value="punch" className="flex items-center gap-2">
            <LogIn size={16} />
            {lang === 'ar' ? 'تسجيل الحضور' : 'Punch'}
          </TabsTrigger>
          <TabsTrigger value="requests" className="flex items-center gap-2">
            <FileText size={16} />
            {lang === 'ar' ? 'طلبات الموظفين' : 'Requests'}
          </TabsTrigger>
          {isAdmin && (
            <TabsTrigger value="admin" className="flex items-center gap-2">
              <User size={16} />
              {lang === 'ar' ? 'سجل الكل' : 'All Records'}
            </TabsTrigger>
          )}
        </TabsList>

        {/* =============== تبويب التبصيم =============== */}
        <TabsContent value="punch" className="space-y-4">
          <Card className="border-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <MapPin className="text-primary" size={20} />
                {lang === 'ar' ? 'تسجيل الحضور اليومي' : 'Daily Attendance'}
              </CardTitle>
              <CardDescription>
                {lang === 'ar' 
                  ? 'تأكد من تفعيل الموقع وأنك داخل نطاق موقع العمل'
                  : 'Ensure GPS is enabled and you are within work location'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* حالة GPS */}
              <GPSStatusCard />

              {/* مواقع العمل المعينة */}
              {assignedLocations.length > 0 ? (
                <div className="p-4 rounded-xl bg-gradient-to-r from-primary/5 to-primary/10 border border-primary/20">
                  <p className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <Building2 size={18} className="text-primary" />
                    {lang === 'ar' ? 'مواقع العمل المعينة لك:' : 'Your assigned locations:'}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {assignedLocations.map(loc => (
                      <Badge key={loc.id} variant="secondary" className="px-3 py-1.5 text-sm">
                        {loc.name_ar || loc.name}
                        <span className="text-xs text-muted-foreground ms-2">
                          ({loc.work_start} - {loc.work_end})
                        </span>
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 dark:bg-amber-950/30 dark:border-amber-800">
                  <div className="flex items-center gap-3">
                    <AlertTriangle size={24} className="text-amber-600" />
                    <div>
                      <p className="font-semibold text-amber-700 dark:text-amber-300">
                        [E005] {lang === 'ar' ? 'لا توجد مواقع عمل معينة لك' : 'No locations assigned'}
                      </p>
                      <p className="text-sm text-amber-600 dark:text-amber-400">
                        {lang === 'ar' ? 'راجع الإدارة لتعيين موقع عمل' : 'Contact admin to assign a location'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* اختيار الموقع */}
              {assignedLocations.length > 1 && !todayRecord?.check_in && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <MapPin size={16} />
                    {lang === 'ar' ? 'اختر موقع التبصيم:' : 'Select punch location:'}
                  </Label>
                  <Select value={selectedLocation} onValueChange={setSelectedLocation}>
                    <SelectTrigger className="h-12">
                      <SelectValue placeholder={lang === 'ar' ? 'اختر الموقع' : 'Select location'} />
                    </SelectTrigger>
                    <SelectContent>
                      {assignedLocations.map(loc => (
                        <SelectItem key={loc.id} value={loc.id}>
                          <div className="flex items-center gap-2">
                            <Building2 size={16} />
                            {loc.name_ar || loc.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* حالة اليوم */}
              {todayRecord && (todayRecord.check_in || todayRecord.check_out) && (
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border">
                  <p className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <Calendar size={16} />
                    {lang === 'ar' ? 'سجل اليوم:' : "Today's record:"}
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
                      <LogIn size={20} className="text-emerald-600" />
                      <div>
                        <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الدخول' : 'In'}</p>
                        <p className="font-mono font-semibold">
                          {todayRecord.check_in?.timestamp 
                            ? new Date(todayRecord.check_in.timestamp).toLocaleTimeString('ar-SA', {hour: '2-digit', minute: '2-digit'})
                            : '-'}
                        </p>
                        {todayRecord.check_in?.work_location && (
                          <p className="text-xs text-muted-foreground">{todayRecord.check_in.work_location}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                      <LogOut size={20} className="text-red-600" />
                      <div>
                        <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الخروج' : 'Out'}</p>
                        <p className="font-mono font-semibold">
                          {todayRecord.check_out?.timestamp 
                            ? new Date(todayRecord.check_out.timestamp).toLocaleTimeString('ar-SA', {hour: '2-digit', minute: '2-digit'})
                            : '-'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* أزرار التبصيم */}
              <div className="grid grid-cols-2 gap-4 pt-2">
                <Button
                  onClick={handleCheckIn}
                  disabled={loading || !workTimeStatus.canCheckIn || gps.status === 'checking' || assignedLocations.length === 0}
                  className={`h-16 text-lg font-bold transition-all ${
                    workTimeStatus.canCheckIn && gps.status === 'ready'
                      ? 'bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 shadow-lg shadow-emerald-500/30'
                      : 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
                  }`}
                  data-testid="check-in-btn"
                >
                  {loading ? (
                    <Loader2 size={24} className="animate-spin me-2" />
                  ) : (
                    <LogIn size={24} className="me-2" />
                  )}
                  {lang === 'ar' ? 'تسجيل الدخول' : 'Check In'}
                </Button>
                
                <Button
                  onClick={() => setConfirmDialog({ open: true, type: 'checkout' })}
                  disabled={loading || !workTimeStatus.canCheckOut || gps.status === 'checking'}
                  className={`h-16 text-lg font-bold transition-all ${
                    workTimeStatus.canCheckOut && gps.status === 'ready'
                      ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-lg shadow-red-500/30'
                      : 'bg-gray-300 dark:bg-gray-700 cursor-not-allowed'
                  }`}
                  data-testid="check-out-btn"
                >
                  {loading ? (
                    <Loader2 size={24} className="animate-spin me-2" />
                  ) : (
                    <LogOut size={24} className="me-2" />
                  )}
                  {lang === 'ar' ? 'تسجيل الخروج' : 'Check Out'}
                </Button>
              </div>

              {/* رسالة خارج أوقات العمل */}
              {workTimeStatus.message && (
                <div className="p-3 rounded-lg bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 text-sm text-center flex items-center justify-center gap-2">
                  <Timer size={18} />
                  [E006] {workTimeStatus.message}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* =============== تبويب طلبات الموظفين =============== */}
        <TabsContent value="requests" className="space-y-4">
          <Card className="border-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="text-primary" size={20} />
                    {lang === 'ar' ? 'طلبات الحضور' : 'Attendance Requests'}
                  </CardTitle>
                  <CardDescription>
                    {lang === 'ar' 
                      ? 'نسيان بصمة - مهمة خارجية - خروج مبكر - تبرير تأخير'
                      : 'Forgot punch, field work, early leave, late excuse'}
                  </CardDescription>
                </div>
                <Button onClick={() => setRequestDialogOpen(true)} className="gap-2">
                  <Send size={16} />
                  {lang === 'ar' ? 'طلب جديد' : 'New Request'}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {/* قائمة الطلبات */}
              {myRequests.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <History size={48} className="mx-auto mb-4 opacity-50" />
                  <p>{lang === 'ar' ? 'لا توجد طلبات سابقة' : 'No previous requests'}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {myRequests.slice(0, 10).map((req) => (
                    <div key={req.id} className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-lg">
                            {REQUEST_TYPES.find(t => t.value === req.type)?.icon || '📋'}
                          </div>
                          <div>
                            <p className="font-semibold">
                              {req.data?.request_type_ar || REQUEST_TYPES.find(t => t.value === req.type)?.label_ar || req.type}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {req.data?.date} {req.data?.from_time && `(${req.data.from_time} - ${req.data.to_time})`}
                            </p>
                            <p className="text-sm mt-1">{req.data?.reason}</p>
                          </div>
                        </div>
                        <Badge variant={
                          req.status === 'executed' ? 'default' :
                          req.status?.includes('pending') ? 'secondary' :
                          req.status === 'rejected' ? 'destructive' : 'outline'
                        }>
                          {req.status === 'executed' ? (lang === 'ar' ? 'منفذ' : 'Executed') :
                           req.status?.includes('pending') ? (lang === 'ar' ? 'قيد الانتظار' : 'Pending') :
                           req.status === 'rejected' ? (lang === 'ar' ? 'مرفوض' : 'Rejected') :
                           req.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* =============== تبويب الإدارة =============== */}
        {isAdmin && (
          <TabsContent value="admin">
            <Card>
              <CardHeader>
                <CardTitle>{lang === 'ar' ? 'سجل حضور الموظفين' : 'Employee Attendance'}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                        <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                        <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'الدخول' : 'In'}</th>
                        <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'الخروج' : 'Out'}</th>
                        <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'موقع البصمة' : 'Location'}</th>
                        <th className="p-3 text-center font-semibold">GPS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adminData.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-12 text-center text-muted-foreground">
                            {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                          </td>
                        </tr>
                      ) : (
                        adminData.map((record, i) => (
                          <tr key={i} className="border-b hover:bg-muted/30 transition-colors">
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
                              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                {record.location_name_ar || record.location_name || record.work_location || '-'}
                              </Badge>
                            </td>
                            <td className="p-3 text-center">
                              {record.gps_valid_in ? (
                                <CheckCircle size={18} className="text-emerald-500 mx-auto" />
                              ) : record.check_in ? (
                                <AlertTriangle size={18} className="text-amber-500 mx-auto" />
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
          </TabsContent>
        )}
      </Tabs>

      {/* =============== حوار تأكيد الخروج =============== */}
      <Dialog open={confirmDialog.open} onOpenChange={(open) => setConfirmDialog({ open, type: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle size={20} />
              {lang === 'ar' ? 'تأكيد تسجيل الخروج' : 'Confirm Check-out'}
            </DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground py-4">
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

      {/* =============== حوار طلب جديد =============== */}
      <Dialog open={requestDialogOpen} onOpenChange={setRequestDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText size={20} className="text-primary" />
              {lang === 'ar' ? 'طلب حضور جديد' : 'New Attendance Request'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* نوع الطلب */}
            <div className="space-y-2">
              <Label>{lang === 'ar' ? 'نوع الطلب' : 'Request Type'}</Label>
              <Select 
                value={requestForm.request_type} 
                onValueChange={(v) => setRequestForm(prev => ({ ...prev, request_type: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder={lang === 'ar' ? 'اختر نوع الطلب' : 'Select type'} />
                </SelectTrigger>
                <SelectContent>
                  {REQUEST_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      <span className="flex items-center gap-2">
                        <span>{type.icon}</span>
                        {lang === 'ar' ? type.label_ar : type.label_en}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* التاريخ */}
            <div className="space-y-2">
              <Label>{lang === 'ar' ? 'التاريخ' : 'Date'}</Label>
              <Input 
                type="date"
                value={requestForm.date}
                onChange={(e) => setRequestForm(prev => ({ ...prev, date: e.target.value }))}
              />
            </div>

            {/* الوقت (للمهمة الخارجية والخروج المبكر) */}
            {['field_work', 'early_leave_request'].includes(requestForm.request_type) && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>{lang === 'ar' ? 'من الساعة' : 'From'}</Label>
                  <Input 
                    type="time"
                    value={requestForm.from_time}
                    onChange={(e) => setRequestForm(prev => ({ ...prev, from_time: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>{lang === 'ar' ? 'إلى الساعة' : 'To'}</Label>
                  <Input 
                    type="time"
                    value={requestForm.to_time}
                    onChange={(e) => setRequestForm(prev => ({ ...prev, to_time: e.target.value }))}
                  />
                </div>
              </div>
            )}

            {/* السبب */}
            <div className="space-y-2">
              <Label>{lang === 'ar' ? 'السبب / التفاصيل' : 'Reason / Details'}</Label>
              <Textarea 
                placeholder={lang === 'ar' ? 'اكتب السبب هنا...' : 'Enter reason...'}
                value={requestForm.reason}
                onChange={(e) => setRequestForm(prev => ({ ...prev, reason: e.target.value }))}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequestDialogOpen(false)}>
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button onClick={handleSubmitRequest} disabled={submittingRequest}>
              {submittingRequest && <Loader2 size={16} className="animate-spin me-2" />}
              <Send size={16} className="me-1" />
              {lang === 'ar' ? 'إرسال الطلب' : 'Submit'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
