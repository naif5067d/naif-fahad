import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { MapPin, Clock, CheckCircle, XCircle, AlertTriangle, Building2, Navigation, CalendarDays, User, Moon, Edit, Eye, FileText, UserX, Timer, ChevronLeft, Check, X as XIcon, Loader2, Map } from 'lucide-react';
import { formatSaudiDateTime, formatSaudiDate, formatSaudiTime } from '@/lib/dateUtils';
import { MapContainer, TileLayer, Marker, Circle } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '@/lib/api';
import { toast } from 'sonner';

// Fix Leaflet default icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// أيقونة حمراء للموقع المعين للموظف
const redIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// أيقونة زرقاء للمواقع الأخرى
const blueIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// أنواع طلبات الحضور
const ATTENDANCE_REQUEST_TYPES = {
  forget_checkin: { name_ar: 'نسيان بصمة', icon: Timer },
  field_work: { name_ar: 'مهمة خارجية', icon: Navigation },
  early_leave_request: { name_ar: 'طلب خروج مبكر', icon: ChevronLeft },
  late_excuse: { name_ar: 'تبرير تأخير', icon: Clock },
};

export default function AttendancePage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [today, setToday] = useState({ check_in: null, check_out: null });
  const [history, setHistory] = useState([]);
  const [gpsState, setGpsState] = useState({ available: false, lat: null, lng: null, checking: true });
  const [loading, setLoading] = useState(false);
  const [workLocation, setWorkLocation] = useState('');
  const [assignedLocations, setAssignedLocations] = useState([]);
  const [allLocations, setAllLocations] = useState([]); // جميع مواقع الشركة
  const [adminData, setAdminData] = useState([]);
  const [period, setPeriod] = useState('daily');
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().slice(0, 10));
  
  // حالات جديدة
  const [teamSummary, setTeamSummary] = useState({ present: 0, absent: 0, on_leave: 0, late: 0 });
  const [ramadanSettings, setRamadanSettings] = useState(null);
  const [showRamadanDialog, setShowRamadanDialog] = useState(false);
  const [ramadanForm, setRamadanForm] = useState({ start_date: '', end_date: '', work_start: '09:00', work_end: '15:00' });
  const [mapVisible, setMapVisible] = useState(false);
  const [showMapDialog, setShowMapDialog] = useState(false); // dialog لعرض الخريطة
  const [attendanceRequests, setAttendanceRequests] = useState([]);
  
  // حالات طلبات الحضور
  const [showRequestDialog, setShowRequestDialog] = useState(false);
  const [requestForm, setRequestForm] = useState({ request_type: 'forget_checkin', date: new Date().toISOString().slice(0, 10), reason: '', from_time: '', to_time: '' });
  const [submittingRequest, setSubmittingRequest] = useState(false);
  
  // حالات تعديل الحضور الإداري
  const [editDialog, setEditDialog] = useState(null);
  const [editForm, setEditForm] = useState({ check_in_time: '', check_out_time: '', note: '' });
  
  // حالات الإجراءات على الطلبات
  const [actionDialog, setActionDialog] = useState(null);
  const [actionNote, setActionNote] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const isEmployee = ['employee', 'supervisor'].includes(user?.role);
  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);
  const isStas = user?.role === 'stas';
  
  // التاريخ الحالي بتوقيت الرياض
  const todayFormatted = formatSaudiDate(new Date().toISOString());

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
      const res = await api.get('/api/stas/settings/map-visibility/public');
      setMapVisible(res.data?.show_map_to_employees || false);
    } catch (err) {}
  };

  // جلب جميع مواقع الشركة عندما تكون الخريطة مفعلة
  const fetchAllLocations = async () => {
    try {
      const res = await api.get('/api/work-locations');
      setAllLocations(res.data?.filter(l => l.is_active !== false) || []);
    } catch (err) {}
  };

  const fetchAttendanceRequests = async () => {
    try {
      const res = await api.get('/api/transactions', {
        params: { types: 'forget_checkin,field_work,early_leave_request,late_excuse' }
      });
      setAttendanceRequests(res.data || []);
    } catch (err) {}
  };

  const fetchData = () => {
    // جلب إعداد الخريطة للجميع
    fetchMapVisibility();
    // جلب جميع المواقع للخريطة
    fetchAllLocations();
    
    if (isEmployee || isAdmin) {
      api.get('/api/attendance/today').then(r => setToday(r.data)).catch(() => {});
      api.get('/api/attendance/history').then(r => setHistory(r.data)).catch(() => {});
    }
    if (isAdmin) {
      fetchAdmin();
      fetchRamadanSettings();
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
      toast.success('تم تسجيل الدخول بنجاح');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
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
      toast.success('تم تسجيل الخروج بنجاح');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    } finally {
      setLoading(false);
    }
  };

  // تفعيل دوام رمضان
  const handleActivateRamadan = async () => {
    try {
      await api.post('/api/stas/ramadan/activate', ramadanForm);
      toast.success('تم تفعيل دوام رمضان');
      setShowRamadanDialog(false);
      fetchRamadanSettings();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    }
  };

  // إلغاء دوام رمضان
  const handleDeactivateRamadan = async () => {
    try {
      await api.post('/api/stas/ramadan/deactivate');
      toast.success('تم إلغاء دوام رمضان');
      fetchRamadanSettings();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    }
  };

  // تحديث إظهار الخريطة
  const handleToggleMapVisibility = async () => {
    try {
      await api.post(`/api/stas/settings/map-visibility?show=${!mapVisible}`);
      setMapVisible(!mapVisible);
      toast.success('تم تحديث الإعداد');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    }
  };

  // تشغيل حساب الغياب اليدوي
  const handleCalculateAttendance = async () => {
    try {
      setLoading(true);
      await api.post('/api/stas/attendance/calculate-daily');
      toast.success('تم حساب الحضور اليومي');
      fetchAdmin();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    } finally {
      setLoading(false);
    }
  };

  // إرسال طلب حضور
  const handleSubmitRequest = async () => {
    if (!requestForm.reason.trim()) {
      toast.error('يرجى كتابة السبب');
      return;
    }
    setSubmittingRequest(true);
    try {
      await api.post('/api/attendance/request', requestForm);
      toast.success('تم إرسال الطلب بنجاح');
      setShowRequestDialog(false);
      setRequestForm({ request_type: 'forget_checkin', date: new Date().toISOString().slice(0, 10), reason: '', from_time: '', to_time: '' });
      fetchAttendanceRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    } finally {
      setSubmittingRequest(false);
    }
  };

  // تعديل حضور إداري
  const handleAdminEdit = async () => {
    if (!editDialog) return;
    try {
      setLoading(true);
      await api.post(`/api/attendance/admin-edit/${editDialog.employee_id}`, {
        date: editDialog.date,
        check_in_time: editForm.check_in_time || null,
        check_out_time: editForm.check_out_time || null,
        note: editForm.note || ''
      });
      toast.success('تم تعديل الحضور');
      setEditDialog(null);
      fetchAdmin();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    } finally {
      setLoading(false);
    }
  };

  // فتح dialog تعديل الحضور
  const openEditDialog = (record) => {
    setEditForm({
      check_in_time: record.check_in_time || '',
      check_out_time: record.check_out_time || '',
      note: ''
    });
    setEditDialog(record);
  };

  // تحديد إذا كان المستخدم يمكنه الموافقة على الطلب
  const canApproveRequest = (req) => {
    const hasAlreadyActed = req.approval_chain?.some(
      approval => approval.approver_id === user?.id
    );
    if (hasAlreadyActed) return false;
    
    const map = {
      pending_supervisor: ['supervisor', 'sultan', 'naif'],
      pending_ops: ['sultan', 'naif'],
      stas: ['stas'],
    };
    return map[req.status]?.includes(user?.role);
  };

  // معالجة الإجراء على طلب الحضور
  const handleRequestAction = async (action) => {
    if (!actionDialog) return;
    setActionLoading(true);
    try {
      await api.post(`/api/transactions/${actionDialog.id}/action`, { action, note: actionNote });
      toast.success(action === 'approve' ? 'تمت الموافقة' : 'تم الرفض');
      setActionDialog(null);
      setActionNote('');
      fetchAttendanceRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    } finally {
      setActionLoading(false);
    }
  };

  // الحصول على تسمية الحالة
  const getStatusLabel = (status) => {
    const labels = {
      executed: 'منفذة',
      rejected: 'مرفوضة',
      cancelled: 'ملغاة',
      pending_supervisor: 'بانتظار المشرف',
      pending_ops: 'بانتظار العمليات',
      stas: 'بانتظار STAS',
    };
    return labels[status] || status;
  };

  // الحصول على لون الحالة
  const getStatusColor = (status) => {
    const colors = {
      executed: 'bg-emerald-100 text-emerald-700',
      rejected: 'bg-red-100 text-red-700',
      cancelled: 'bg-red-100 text-red-700',
      pending_supervisor: 'bg-blue-100 text-blue-700',
      pending_ops: 'bg-orange-100 text-orange-700',
      stas: 'bg-violet-100 text-violet-700',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="space-y-5" data-testid="attendance-page">
      {/* الترويسة */}
      <div>
        <h1 className="text-xl md:text-2xl font-bold">الحضور والانصراف</h1>
        <p className="text-sm text-muted-foreground mt-1">{todayFormatted}</p>
      </div>

      {/* بطاقة تسجيل الدخول والخروج */}
      {(isEmployee || isAdmin) && (
        <div className="card-premium p-5 space-y-4">
          {/* حالة GPS */}
          {!gpsState.checking && !gpsState.available && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-600">
              <AlertTriangle size={18} />
              <span className="text-sm font-medium">تحديد الموقع غير متاح</span>
            </div>
          )}

          {/* مواقع العمل المعينة */}
          {assignedLocations.length > 0 && (
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/10">
              <p className="text-sm font-semibold text-primary mb-3 flex items-center gap-2">
                <MapPin size={16} />
                مواقع العمل المعينة لك
              </p>
              <div className="flex flex-wrap gap-2">
                {assignedLocations.map(loc => (
                  <div key={loc.id} className="text-sm bg-background px-3 py-2 rounded-lg border border-border">
                    <span className="font-medium">{loc.name_ar || loc.name}</span>
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
                لم يتم تعيين موقع عمل لك بعد. تواصل مع مديرك.
              </p>
            </div>
          )}

          {/* عرض الخريطة للموظفين - يظهر للجميع إذا مفعل من الإدارة */}
          {mapVisible && allLocations.length > 0 && (
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-medium text-primary flex items-center gap-2">
                  <Map size={16} />
                  مواقع العمل
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowMapDialog(true)}
                  className="h-8"
                  data-testid="view-map-btn"
                >
                  <Eye size={14} className="me-1" />
                  عرض الخريطة
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                  موقعك المعين
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                  مواقع أخرى
                </span>
              </div>
            </div>
          )}

          {/* اختيار الموقع وأزرار الدخول/الخروج */}
          <div className="space-y-3">
            <Select value={workLocation} onValueChange={setWorkLocation} disabled={!!today.check_in}>
              <SelectTrigger className="h-12 rounded-xl" data-testid="work-location-select">
                <SelectValue placeholder="اختر موقع العمل" />
              </SelectTrigger>
              <SelectContent>
                {assignedLocations.map(loc => (
                  <SelectItem key={loc.id} value={loc.id}>
                    <div className="flex items-center gap-2">
                      <Navigation size={14} className="text-primary" />
                      {loc.name_ar || loc.name}
                    </div>
                  </SelectItem>
                ))}
                {assignedLocations.length === 0 && (
                  <>
                    <SelectItem value="HQ">
                      <div className="flex items-center gap-2">
                        <Building2 size={14} className="text-primary" />
                        المقر الرئيسي
                      </div>
                    </SelectItem>
                    <SelectItem value="Project">
                      <div className="flex items-center gap-2">
                        <Navigation size={14} className="text-amber-500" />
                        المشروع
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
                تسجيل دخول
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
                تسجيل خروج
                {today.check_out && (
                  <span className="ms-2 text-xs opacity-80">✓ {formatSaudiTime(today.check_out.timestamp)}</span>
                )}
              </Button>
            </div>
            
            {/* زر طلب حضور جديد */}
            <Button 
              variant="outline" 
              className="w-full mt-3 h-11"
              onClick={() => setShowRequestDialog(true)}
              data-testid="new-attendance-request-btn"
            >
              <FileText size={18} className="me-2" />
              طلب حضور جديد (نسيان بصمة / مهمة خارجية / ...)
            </Button>
          </div>
        </div>
      )}

      {/* سجل الحضور */}
      {(isEmployee || isAdmin) && history.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">السجل</h2>
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
                      {h.type === 'check_in' ? 'تسجيل دخول' : 'تسجيل خروج'}
                    </p>
                    <p className="text-xs text-muted-foreground">{formatSaudiDate(h.date)}</p>
                  </div>
                </div>
                <div className="text-end">
                  <p className="text-sm font-mono font-semibold">{formatSaudiTime(h.timestamp)}</p>
                  {h.gps_status === 'valid' ? (
                    <span className="text-[10px] text-emerald-500">● GPS</span>
                  ) : (
                    <span className="text-[10px] text-muted-foreground">○ بدون GPS</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* عرض المدراء */}
      {isAdmin && (
        <div className="border-t border-border pt-5">
          {/* ترويسة القسم الإداري */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-lg font-semibold">حضور الفريق</h2>
            
            <div className="flex flex-wrap gap-2">
              {/* أزرار STAS فقط */}
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
                      إلغاء دوام رمضان
                    </Button>
                  ) : (
                    <Dialog open={showRamadanDialog} onOpenChange={setShowRamadanDialog}>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          <Moon size={14} className="me-1" />
                          تفعيل دوام رمضان
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>تفعيل دوام رمضان (6 ساعات)</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                          <div>
                            <label className="text-sm font-medium">من تاريخ</label>
                            <Input 
                              type="date" 
                              value={ramadanForm.start_date}
                              onChange={e => setRamadanForm({...ramadanForm, start_date: e.target.value})}
                              className="mt-1"
                            />
                          </div>
                          <div>
                            <label className="text-sm font-medium">إلى تاريخ</label>
                            <Input 
                              type="date" 
                              value={ramadanForm.end_date}
                              onChange={e => setRamadanForm({...ramadanForm, end_date: e.target.value})}
                              className="mt-1"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="text-sm font-medium">وقت الدخول</label>
                              <Input 
                                type="time" 
                                value={ramadanForm.work_start}
                                onChange={e => setRamadanForm({...ramadanForm, work_start: e.target.value})}
                                className="mt-1"
                              />
                            </div>
                            <div>
                              <label className="text-sm font-medium">وقت الخروج</label>
                              <Input 
                                type="time" 
                                value={ramadanForm.work_end}
                                onChange={e => setRamadanForm({...ramadanForm, work_end: e.target.value})}
                                className="mt-1"
                              />
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            ملاحظة: ستُطبق أوقات الدوام على حساب التأخير والخروج المبكر
                          </p>
                          <Button onClick={handleActivateRamadan} className="w-full">
                            تفعيل
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                  
                  {/* زر إظهار/إخفاء الخريطة */}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleToggleMapVisibility}
                    className={mapVisible ? 'text-emerald-600 border-emerald-600' : ''}
                  >
                    <Eye size={14} className="me-1" />
                    {mapVisible ? 'إخفاء الخريطة' : 'إظهار الخريطة'}
                  </Button>
                  
                  {/* زر حساب الغياب */}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleCalculateAttendance}
                    disabled={loading}
                  >
                    <FileText size={14} className="me-1" />
                    حساب الغياب
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* إشعار دوام رمضان */}
          {ramadanSettings?.is_active && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 mb-4 flex items-center gap-2">
              <Moon size={18} className="text-amber-600" />
              <span className="text-sm text-amber-700">
                دوام رمضان مفعل (6 ساعات) - من {ramadanSettings.start_date} إلى {ramadanSettings.end_date}
              </span>
            </div>
          )}

          {/* بطاقات ملخص الفريق */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="card-premium p-4 text-center">
              <CheckCircle className="mx-auto text-emerald-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-emerald-600">{teamSummary.present}</p>
              <p className="text-xs text-muted-foreground">حاضر</p>
            </div>
            <div className="card-premium p-4 text-center">
              <UserX className="mx-auto text-red-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-red-600">{teamSummary.absent}</p>
              <p className="text-xs text-muted-foreground">غائب</p>
            </div>
            <div className="card-premium p-4 text-center">
              <CalendarDays className="mx-auto text-blue-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-blue-600">{teamSummary.on_leave}</p>
              <p className="text-xs text-muted-foreground">إجازة</p>
            </div>
            <div className="card-premium p-4 text-center">
              <Timer className="mx-auto text-amber-500 mb-2" size={24} />
              <p className="text-2xl font-bold text-amber-600">{teamSummary.late}</p>
              <p className="text-xs text-muted-foreground">متأخر</p>
            </div>
          </div>
          
          {/* فلتر الفترة */}
          <div className="flex gap-3 mb-4 flex-wrap">
            <Tabs value={period} onValueChange={setPeriod} className="w-full">
              <TabsList className="grid grid-cols-4 h-11 rounded-xl p-1 bg-muted/50">
                <TabsTrigger value="daily" className="rounded-lg text-xs">يومي</TabsTrigger>
                <TabsTrigger value="weekly" className="rounded-lg text-xs">أسبوعي</TabsTrigger>
                <TabsTrigger value="monthly" className="rounded-lg text-xs">شهري</TabsTrigger>
                <TabsTrigger value="yearly" className="rounded-lg text-xs">سنوي</TabsTrigger>
              </TabsList>
            </Tabs>
            <Input
              type="date"
              value={dateFilter}
              onChange={e => setDateFilter(e.target.value)}
              className="w-full sm:w-auto h-11 rounded-xl"
            />
          </div>

          {/* جدول الحضور */}
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="hr-table">
              <thead>
                <tr>
                  <th>الاسم</th>
                  <th>التاريخ</th>
                  <th>الدخول</th>
                  <th>الخروج</th>
                  <th>الحالة</th>
                  <th>GPS</th>
                  {isStas && <th>إجراء</th>}
                </tr>
              </thead>
              <tbody>
                {adminData.length === 0 ? (
                  <tr>
                    <td colSpan={isStas ? 7 : 6} className="text-center py-8 text-muted-foreground">لا توجد بيانات</td>
                  </tr>
                ) : (
                  adminData.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <User size={14} className="text-primary" />
                          </div>
                          <span className="font-medium">{r.employee_name_ar || r.employee_name}</span>
                        </div>
                      </td>
                      <td className="font-mono text-muted-foreground">{formatSaudiDate(r.date)}</td>
                      <td className="font-mono">{r.check_in_time || (r.check_in ? formatSaudiTime(r.check_in) : '-')}</td>
                      <td className="font-mono">{r.check_out_time || (r.check_out ? formatSaudiTime(r.check_out) : '-')}</td>
                      <td>
                        {r.on_leave ? (
                          <span className="badge bg-blue-100 text-blue-700">إجازة</span>
                        ) : r.check_in ? (
                          r.is_late ? (
                            <span className="badge bg-amber-100 text-amber-700">متأخر</span>
                          ) : (
                            <span className="badge bg-emerald-100 text-emerald-700">حاضر</span>
                          )
                        ) : (
                          <span className="badge bg-red-100 text-red-700">غائب</span>
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
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-8"
                            onClick={() => openEditDialog(r)}
                            data-testid={`edit-attendance-${r.employee_id}`}
                          >
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

          {/* طلبات الحضور مع أزرار الإجراءات */}
          {attendanceRequests.length > 0 && (
            <div className="mt-6">
              <h3 className="text-base font-semibold mb-3">طلبات الحضور والبصمة</h3>
              <div className="space-y-2">
                {attendanceRequests.map((req, i) => {
                  const reqType = ATTENDANCE_REQUEST_TYPES[req.type];
                  const Icon = reqType?.icon || FileText;
                  const showActions = canApproveRequest(req);
                  
                  return (
                    <div key={i} className="card-premium p-4" data-testid={`attendance-request-${req.ref_no}`}>
                      {/* معلومات الطلب */}
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                            <Icon size={18} className="text-primary" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">{reqType?.name_ar || req.type}</p>
                            <p className="text-xs text-muted-foreground">{req.ref_no} - {req.employee_name_ar || req.employee_name}</p>
                          </div>
                        </div>
                        <span className={`badge ${getStatusColor(req.status)}`}>
                          {getStatusLabel(req.status)}
                        </span>
                      </div>
                      
                      {/* معلومات إضافية */}
                      <div className="text-xs text-muted-foreground mb-3">
                        <span>{formatSaudiDateTime(req.created_at)}</span>
                        {req.data?.reason && (
                          <span className="ms-3">السبب: {req.data.reason}</span>
                        )}
                      </div>
                      
                      {/* أزرار الإجراءات */}
                      <div className="flex items-center gap-2 pt-3 border-t border-border/50">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/transactions/${req.id}`)}
                          className="flex-1 h-9 rounded-lg hover:bg-primary/10 hover:text-primary"
                          data-testid={`view-request-${req.ref_no}`}
                        >
                          <Eye size={14} className="me-1" />
                          عرض التفاصيل
                        </Button>
                        
                        {showActions && (
                          <>
                            <Button
                              size="sm"
                              onClick={() => setActionDialog({ ...req, action: 'approve' })}
                              className="h-9 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                              data-testid={`approve-request-${req.ref_no}`}
                            >
                              <Check size={14} className="me-1" />
                              موافقة
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => setActionDialog({ ...req, action: 'reject' })}
                              className="h-9 w-9 rounded-lg p-0"
                              data-testid={`reject-request-${req.ref_no}`}
                            >
                              <XIcon size={14} />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Dialog: طلب حضور جديد */}
      <Dialog open={showRequestDialog} onOpenChange={setShowRequestDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>طلب حضور جديد</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium">نوع الطلب</label>
              <Select value={requestForm.request_type} onValueChange={v => setRequestForm({...requestForm, request_type: v})}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(ATTENDANCE_REQUEST_TYPES).map(([key, val]) => (
                    <SelectItem key={key} value={key}>
                      {val.name_ar}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">التاريخ</label>
              <Input type="date" value={requestForm.date} onChange={e => setRequestForm({...requestForm, date: e.target.value})} className="mt-1" />
            </div>
            {['field_work', 'early_leave_request'].includes(requestForm.request_type) && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">من الساعة</label>
                  <Input type="time" value={requestForm.from_time} onChange={e => setRequestForm({...requestForm, from_time: e.target.value})} className="mt-1" />
                </div>
                <div>
                  <label className="text-sm font-medium">إلى الساعة</label>
                  <Input type="time" value={requestForm.to_time} onChange={e => setRequestForm({...requestForm, to_time: e.target.value})} className="mt-1" />
                </div>
              </div>
            )}
            <div>
              <label className="text-sm font-medium">السبب</label>
              <Input 
                value={requestForm.reason} 
                onChange={e => setRequestForm({...requestForm, reason: e.target.value})} 
                placeholder="اكتب السبب..." 
                className="mt-1" 
              />
            </div>
            <Button onClick={handleSubmitRequest} disabled={submittingRequest} className="w-full">
              {submittingRequest ? 'جاري الإرسال...' : 'إرسال الطلب'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog: تعديل حضور إداري */}
      <Dialog open={!!editDialog} onOpenChange={() => setEditDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>تعديل حضور إداري</DialogTitle>
          </DialogHeader>
          {editDialog && (
            <div className="space-y-4 py-2">
              <div className="p-3 bg-muted/50 rounded-lg">
                <p className="text-sm font-medium">{editDialog.employee_name_ar || editDialog.employee_name}</p>
                <p className="text-xs text-muted-foreground">{editDialog.date}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">وقت الدخول</label>
                  <Input type="time" value={editForm.check_in_time} onChange={e => setEditForm({...editForm, check_in_time: e.target.value})} className="mt-1" />
                </div>
                <div>
                  <label className="text-sm font-medium">وقت الخروج</label>
                  <Input type="time" value={editForm.check_out_time} onChange={e => setEditForm({...editForm, check_out_time: e.target.value})} className="mt-1" />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">ملاحظة</label>
                <Input value={editForm.note} onChange={e => setEditForm({...editForm, note: e.target.value})} placeholder="سبب التعديل..." className="mt-1" />
              </div>
              <Button onClick={handleAdminEdit} disabled={loading} className="w-full">
                {loading ? 'جاري الحفظ...' : 'حفظ التعديل'}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog: إجراء على طلب حضور */}
      <Dialog open={!!actionDialog} onOpenChange={() => setActionDialog(null)}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-xl">
              {actionDialog?.action === 'approve' ? 'تأكيد الموافقة' : 'تأكيد الرفض'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 pt-2">
            {/* معلومات الطلب */}
            <div className="bg-muted/30 rounded-xl p-4">
              <p className="text-sm font-mono text-muted-foreground">{actionDialog?.ref_no}</p>
              <p className="text-base font-medium mt-1">{ATTENDANCE_REQUEST_TYPES[actionDialog?.type]?.name_ar || actionDialog?.type}</p>
            </div>
            
            {/* حقل الملاحظة */}
            <div>
              <label className="text-sm font-medium mb-2 block">ملاحظة (اختياري)</label>
              <Input
                data-testid="action-note-input"
                placeholder="أضف ملاحظة..."
                value={actionNote}
                onChange={e => setActionNote(e.target.value)}
                className="h-12 rounded-xl"
              />
            </div>
            
            {/* أزرار الإجراء */}
            <div className="flex gap-3 pt-2">
              <Button 
                variant="outline" 
                onClick={() => setActionDialog(null)} 
                className="flex-1 h-12 rounded-xl"
                data-testid="cancel-action"
              >
                إلغاء
              </Button>
              <Button
                onClick={() => handleRequestAction(actionDialog?.action)}
                disabled={actionLoading}
                className={`flex-1 h-12 rounded-xl font-semibold ${
                  actionDialog?.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'
                } text-white`}
                data-testid="confirm-action"
              >
                {actionLoading && <Loader2 size={18} className="animate-spin me-2" />}
                تأكيد
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
