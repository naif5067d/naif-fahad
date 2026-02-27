/**
 * صفحة إدارة الحضور والعقوبات - النسخة المبسطة
 * 
 * 3 أقسام رئيسية:
 * 1. جدول الدوام الرسمي
 * 2. جدول خارج العمل الرسمي
 * 3. معاملات الخصم
 */
import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogFooter 
} from '@/components/ui/dialog';
import { 
  Users, 
  UserCheck, 
  UserX, 
  Clock, 
  Calendar,
  AlertTriangle,
  RefreshCw,
  TrendingDown,
  FileText,
  Printer,
  Bell,
  ChevronDown,
  ChevronUp,
  Plus,
  Eye,
  CheckCircle,
  XCircle,
  Filter,
  Building,
  DollarSign,
  Edit,
  ArrowRight
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// ألوان الحالات - باستخدام ألوان الشركة الرسمية فقط
const STATUS_CONFIG = {
  'PRESENT': { bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'حاضر' },
  'ABSENT': { bg: 'bg-red-50', text: 'text-red-700', label: 'غائب' },
  'LATE': { bg: 'bg-amber-50', text: 'text-amber-700', label: 'متأخر' },
  'ON_LEAVE': { bg: 'bg-blue-50', text: 'text-blue-700', label: 'مجاز' },
  'ON_MISSION': { bg: 'bg-purple-50', text: 'text-purple-700', label: 'مهمة' },
  'WEEKEND': { bg: 'bg-slate-50', text: 'text-slate-500', label: 'نهاية أسبوع' },
  'HOLIDAY': { bg: 'bg-indigo-50', text: 'text-indigo-600', label: 'عطلة رسمية' },
  'EXEMPTED': { bg: 'bg-gray-50', text: 'text-gray-600', label: 'إعفاء' },
  'EXCUSED': { bg: 'bg-gray-50', text: 'text-gray-600', label: 'معذور' },
  'PERMISSION': { bg: 'bg-cyan-50', text: 'text-cyan-700', label: 'استئذان' },
  'EARLY_LEAVE': { bg: 'bg-orange-50', text: 'text-orange-700', label: 'خروج مبكر' },
};

export default function AttendanceManagementPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  
  // States
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('official');
  const [employees, setEmployees] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  
  // Official attendance data
  const [attendanceData, setAttendanceData] = useState([]);
  const [expandedEmployee, setExpandedEmployee] = useState(null);
  
  // Outside hours data
  const [outsideHoursData, setOutsideHoursData] = useState([]);
  
  // Deduction transactions
  const [deductionTransactions, setDeductionTransactions] = useState([]);
  
  // Dialogs
  const [showStatusDialog, setShowStatusDialog] = useState(false);
  const [statusForm, setStatusForm] = useState({ employee_id: '', date: '', status: '', reason: '' });
  const [showDeductionDialog, setShowDeductionDialog] = useState(false);
  const [deductionForm, setDeductionForm] = useState({ employee_id: '', amount: 0, reason: '', month: '' });
  const [showCompensateDialog, setShowCompensateDialog] = useState(false);
  const [compensateForm, setCompensateForm] = useState({ employee_id: '', date: '', hours: null, note: '' });

  // Fetch employees
  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const res = await api.get('/api/employees');
        const filtered = res.data.filter(e => 
          !['stas', 'mohammed', 'salah'].includes(e.user_id?.toLowerCase()) &&
          e.is_active !== false
        );
        setEmployees(filtered);
      } catch (err) {
        console.error('Error fetching employees:', err);
      }
    };
    fetchEmployees();
  }, []);

  // Fetch data based on active tab
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        if (activeTab === 'official') {
          // جلب تقرير العقوبات (الدوام الرسمي)
          const month = startDate.substring(0, 7);
          const res = await api.get('/api/penalties/monthly-report', {
            params: { year: parseInt(month.split('-')[0]), month: parseInt(month.split('-')[1]) }
          });
          
          let data = res.data.employees || [];
          
          if (selectedEmployees.length > 0) {
            data = data.filter(e => selectedEmployees.includes(e.employee_id));
          }
          
          setAttendanceData(data);
        } else if (activeTab === 'outside') {
          // جلب البصمات خارج الدوام
          const params = { start_date: startDate, end_date: endDate };
          if (selectedEmployees.length > 0) {
            params.employee_ids = selectedEmployees.join(',');
          }
          const res = await api.get('/api/team-attendance/outside-hours', { params });
          setOutsideHoursData(res.data.records || []);
        } else if (activeTab === 'deductions') {
          // جلب معاملات الخصم
          const res = await api.get('/api/deduction-transactions');
          setDeductionTransactions(res.data || []);
        }
      } catch (err) {
        console.error('Error fetching data:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [activeTab, startDate, endDate, selectedEmployees]);

  // حساب الإحصائيات
  const stats = useMemo(() => {
    if (activeTab === 'official') {
      return {
        totalEmployees: attendanceData.length,
        totalAbsent: attendanceData.reduce((sum, e) => sum + (e.absence?.total_days || 0), 0),
        totalDeduction: attendanceData.reduce((sum, e) => sum + (e.total_deduction_amount || 0), 0),
        totalDeficitHours: attendanceData.reduce((sum, e) => sum + (e.deficit?.total_deficit_hours || 0), 0)
      };
    } else if (activeTab === 'outside') {
      return {
        totalRecords: outsideHoursData.length,
        totalHours: outsideHoursData.reduce((sum, r) => sum + (r.total_hours || 0), 0),
        uniqueEmployees: new Set(outsideHoursData.map(r => r.employee_id)).size
      };
    } else {
      return {
        pending: deductionTransactions.filter(t => t.status === 'pending_ceo').length,
        pendingExec: deductionTransactions.filter(t => t.status === 'pending_execution').length,
        executed: deductionTransactions.filter(t => t.status === 'executed').length
      };
    }
  }, [activeTab, attendanceData, outsideHoursData, deductionTransactions]);

  // تعديل الحالة
  const handleStatusChange = async () => {
    if (!statusForm.employee_id || !statusForm.date || !statusForm.status) {
      toast.error('يرجى ملء جميع الحقول');
      return;
    }
    
    try {
      await api.post(`/api/team-attendance/${statusForm.employee_id}/update-status?date=${statusForm.date}`, {
        new_status: statusForm.status,
        reason: statusForm.reason || 'تعديل إداري'
      });
      toast.success('تم تعديل الحالة بنجاح');
      setShowStatusDialog(false);
      setStatusForm({ employee_id: '', date: '', status: '', reason: '' });
      // إعادة جلب البيانات
      setLoading(true);
      const month = startDate.substring(0, 7);
      const res = await api.get('/api/penalties/monthly-report', {
        params: { year: parseInt(month.split('-')[0]), month: parseInt(month.split('-')[1]) }
      });
      setAttendanceData(res.data.employees || []);
      setLoading(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'خطأ في تعديل الحالة');
    }
  };

  // إنشاء معاملة خصم
  const handleCreateDeduction = async () => {
    if (!deductionForm.employee_id || !deductionForm.amount || !deductionForm.reason) {
      toast.error('يرجى ملء جميع الحقول');
      return;
    }
    
    try {
      await api.post('/api/deduction-transactions', {
        ...deductionForm,
        month: startDate.substring(0, 7)
      });
      toast.success('تم إنشاء معاملة الخصم وإرسالها لمحمد');
      setShowDeductionDialog(false);
      setDeductionForm({ employee_id: '', amount: 0, reason: '', month: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'خطأ في إنشاء معاملة الخصم');
    }
  };

  // احتساب خارج الدوام كحضور
  const handleCompensate = async () => {
    try {
      await api.post('/api/team-attendance/outside-hours/count-as-attendance', {
        employee_id: compensateForm.employee_id,
        date: compensateForm.date,
        hours_to_count: compensateForm.hours || null,
        note: compensateForm.note
      });
      
      const msg = compensateForm.hours 
        ? `تم تعويض ${compensateForm.hours} ساعة`
        : 'تم احتساب كحضور';
      toast.success(msg);
      
      setShowCompensateDialog(false);
      setCompensateForm({ employee_id: '', date: '', hours: null, note: '' });
      
      // إعادة جلب البيانات
      const params = { start_date: startDate, end_date: endDate };
      const res = await api.get('/api/team-attendance/outside-hours', { params });
      setOutsideHoursData(res.data.records || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'خطأ في الاحتساب');
    }
  };

  // تشغيل التحضير التلقائي
  const handleRunDailyProcess = async () => {
    try {
      toast.info('جاري تشغيل التحضير...');
      const res = await api.post('/api/attendance-engine/jobs/daily', {
        target_date: endDate
      });
      toast.success(res.data?.message || 'تم تشغيل التحضير بنجاح');
      // إعادة جلب البيانات
      setLoading(true);
      const month = startDate.substring(0, 7);
      const reportRes = await api.get('/api/penalties/monthly-report', {
        params: { year: parseInt(month.split('-')[0]), month: parseInt(month.split('-')[1]) }
      });
      setAttendanceData(reportRes.data.employees || []);
      setLoading(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'خطأ في تشغيل التحضير');
    }
  };

  // طباعة التقرير
  const handlePrint = async () => {
    try {
      const params = {
        period: 'monthly',
        month: startDate.substring(0, 7),
        start_date: startDate,
        end_date: endDate
      };
      
      if (selectedEmployees.length > 0) {
        params.employee_ids = selectedEmployees.join(',');
      }
      
      const response = await api.get('/api/team-attendance/print-report', {
        params,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      
      toast.success('تم فتح التقرير');
    } catch (err) {
      toast.error('خطأ في طباعة التقرير');
    }
  };

  return (
    <div className="space-y-4 p-4 md:p-6" dir="rtl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[hsl(var(--navy))]">
            الحضور والعقوبات
          </h1>
          <p className="text-sm text-muted-foreground">
            إدارة الحضور والتأخير والخصومات
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-4">
            {/* Multi-select Employees with Checkboxes */}
            <div>
              <Label className="text-xs mb-2 block font-medium">تحديد الموظفين</Label>
              <div className="flex flex-wrap gap-2 p-3 border rounded-lg bg-muted/20 max-h-[200px] overflow-y-auto">
                {/* Select All / Deselect All */}
                <Button
                  variant={selectedEmployees.length === 0 ? "default" : "outline"}
                  size="sm"
                  className={selectedEmployees.length === 0 ? "bg-[hsl(var(--navy))]" : ""}
                  onClick={() => setSelectedEmployees([])}
                >
                  الكل
                </Button>
                
                {employees.map((emp, idx) => {
                  const isSelected = selectedEmployees.includes(emp.id);
                  const selectionOrder = selectedEmployees.indexOf(emp.id) + 1;
                  
                  return (
                    <Button
                      key={emp.id}
                      variant={isSelected ? "default" : "outline"}
                      size="sm"
                      className={`relative ${isSelected ? "bg-[hsl(var(--navy))] pr-8" : ""}`}
                      onClick={() => {
                        if (isSelected) {
                          setSelectedEmployees(prev => prev.filter(id => id !== emp.id));
                        } else {
                          setSelectedEmployees(prev => [...prev, emp.id]);
                        }
                      }}
                    >
                      {isSelected && (
                        <span className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full bg-white text-[hsl(var(--navy))] text-xs font-bold flex items-center justify-center">
                          {selectionOrder}
                        </span>
                      )}
                      {emp.full_name_ar || emp.full_name}
                    </Button>
                  );
                })}
              </div>
              
              {/* Selected Summary */}
              {selectedEmployees.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1 items-center">
                  <span className="text-xs text-muted-foreground">المحدد:</span>
                  {selectedEmployees.map((empId, idx) => {
                    const emp = employees.find(e => e.id === empId);
                    return (
                      <Badge 
                        key={empId} 
                        variant="secondary" 
                        className="text-xs cursor-pointer hover:bg-red-100"
                        onClick={() => setSelectedEmployees(prev => prev.filter(id => id !== empId))}
                      >
                        {idx + 1}. {emp?.full_name_ar || emp?.full_name} ×
                      </Badge>
                    );
                  })}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-xs text-red-500 hover:text-red-700"
                    onClick={() => setSelectedEmployees([])}
                  >
                    مسح الكل
                  </Button>
                </div>
              )}
            </div>
            
            {/* Date Range and Actions */}
            <div className="flex flex-col md:flex-row gap-3 items-end flex-wrap">
              {/* Date Range */}
              <div className="flex gap-2">
                <div>
                  <Label className="text-xs mb-1 block">من تاريخ</Label>
                  <Input 
                    type="date" 
                    value={startDate} 
                    onChange={e => setStartDate(e.target.value)}
                    className="w-[140px]"
                  />
                </div>
                <div>
                  <Label className="text-xs mb-1 block">إلى تاريخ</Label>
                  <Input 
                    type="date" 
                    value={endDate} 
                    onChange={e => setEndDate(e.target.value)}
                    className="w-[140px]"
                  />
                </div>
              </div>
              
              <div className="flex-1" />
              
              {/* Actions */}
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleRunDailyProcess}
                  title="تشغيل التحضير التلقائي لليوم المحدد"
                >
                  <RefreshCw size={16} className="ml-1" />
                  تحضير
                </Button>
                <Button variant="outline" size="sm" onClick={handlePrint}>
                  <Printer size={16} className="ml-1" />
                  طباعة {selectedEmployees.length > 0 ? `(${selectedEmployees.length})` : ''}
                </Button>
                <Button 
                  size="sm" 
                  className="bg-[hsl(var(--navy))] hover:bg-[hsl(var(--navy-dark))]"
                  onClick={() => setShowDeductionDialog(true)}
                >
                  <Plus size={16} className="ml-1" />
                  معاملة خصم
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-4">
          <TabsTrigger value="official" className="flex items-center gap-2">
            <Building size={16} />
            <span className="hidden sm:inline">الدوام الرسمي</span>
            <span className="sm:hidden">الرسمي</span>
          </TabsTrigger>
          <TabsTrigger value="outside" className="flex items-center gap-2">
            <Clock size={16} className="text-[hsl(var(--navy))]" />
            <span className="hidden sm:inline">خارج العمل الرسمي</span>
            <span className="sm:hidden">خارج</span>
          </TabsTrigger>
          <TabsTrigger value="deductions" className="flex items-center gap-2">
            <DollarSign size={16} />
            <span className="hidden sm:inline">معاملات الخصم</span>
            <span className="sm:hidden">الخصومات</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Official Attendance */}
        <TabsContent value="official">
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <Card className="bg-gradient-to-br from-[hsl(var(--navy))] to-[hsl(var(--navy-dark))] text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Users size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">الموظفين</p>
                    <p className="text-2xl font-bold">{stats.totalEmployees}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-red-500 to-red-600 text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <UserX size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">أيام الغياب</p>
                    <p className="text-2xl font-bold">{stats.totalAbsent}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-amber-500 to-amber-600 text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Clock size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">ساعات النقص</p>
                    <p className="text-2xl font-bold">{stats.totalDeficitHours?.toFixed(1) || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-[hsl(var(--lavender))] to-purple-600 text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <TrendingDown size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">إجمالي الخصم</p>
                    <p className="text-2xl font-bold">{stats.totalDeduction?.toFixed(0) || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Attendance List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText size={20} className="text-[hsl(var(--navy))]" />
                سجل الدوام الرسمي
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-12">
                  <RefreshCw className="animate-spin text-[hsl(var(--navy))]" size={32} />
                </div>
              ) : attendanceData.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  لا توجد بيانات
                </div>
              ) : (
                <div className="space-y-2">
                  {attendanceData.map((emp) => (
                    <div 
                      key={emp.employee_id}
                      className="border rounded-lg overflow-hidden hover:border-[hsl(var(--navy)/0.3)] transition-colors"
                    >
                      {/* Employee Summary Row */}
                      <div 
                        className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/30"
                        onClick={() => setExpandedEmployee(expandedEmployee === emp.employee_id ? null : emp.employee_id)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-[hsl(var(--navy)/0.1)] flex items-center justify-center text-[hsl(var(--navy))] font-bold">
                            {emp.employee_name_ar?.[0] || '?'}
                          </div>
                          <div>
                            <p className="font-medium">{emp.employee_name_ar}</p>
                            <p className="text-xs text-muted-foreground">{emp.employee_id}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 flex-wrap justify-end">
                          {emp.absence?.total_days > 0 && (
                            <Badge variant="destructive" className="text-xs">
                              <UserX size={12} className="ml-1" />
                              {emp.absence.total_days} غياب
                            </Badge>
                          )}
                          
                          {emp.deficit?.total_deficit_hours > 0 && (
                            <Badge variant="outline" className="text-xs text-amber-600 border-amber-300">
                              <Clock size={12} className="ml-1" />
                              {emp.deficit.total_deficit_hours}h
                            </Badge>
                          )}
                          
                          {emp.total_deduction_days > 0 && (
                            <Badge className="bg-[hsl(var(--lavender)/0.2)] text-[hsl(var(--lavender))] text-xs">
                              <TrendingDown size={12} className="ml-1" />
                              {emp.total_deduction_days} يوم
                            </Badge>
                          )}
                          
                          {expandedEmployee === emp.employee_id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </div>
                      </div>
                      
                      {/* Expanded Details */}
                      {expandedEmployee === emp.employee_id && (
                        <div className="border-t bg-muted/20 p-4">
                          {/* Summary Cards */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                            <div className="p-3 bg-red-50 rounded-lg text-center">
                              <p className="text-xs text-muted-foreground">أيام الغياب</p>
                              <p className="text-xl font-bold text-red-600">{emp.absence?.total_days || 0}</p>
                            </div>
                            <div className="p-3 bg-amber-50 rounded-lg text-center">
                              <p className="text-xs text-muted-foreground">دقائق التأخير</p>
                              <p className="text-xl font-bold text-amber-600">{emp.deficit?.total_late_minutes || 0}</p>
                            </div>
                            <div className="p-3 bg-orange-50 rounded-lg text-center">
                              <p className="text-xs text-muted-foreground">خروج مبكر</p>
                              <p className="text-xl font-bold text-orange-600">{emp.deficit?.total_early_leave_minutes || 0}</p>
                            </div>
                            <div className="p-3 bg-[hsl(var(--lavender)/0.1)] rounded-lg text-center">
                              <p className="text-xs text-muted-foreground">إجمالي الخصم</p>
                              <p className="text-xl font-bold text-[hsl(var(--lavender))]">{emp.total_deduction_days || 0} يوم</p>
                            </div>
                          </div>
                          
                          {/* Daily Details Table */}
                          {emp.daily_details && emp.daily_details.length > 0 && (
                            <div className="overflow-x-auto">
                              <table className="w-full text-sm">
                                <thead className="bg-[hsl(var(--navy)/0.05)]">
                                  <tr>
                                    <th className="text-start p-2 font-medium">التاريخ</th>
                                    <th className="text-center p-2 font-medium">الحالة</th>
                                    <th className="text-center p-2 font-medium">بصمة الدخول</th>
                                    <th className="text-center p-2 font-medium">بصمة الخروج</th>
                                    <th className="text-center p-2 font-medium">تأخير</th>
                                    <th className="text-center p-2 font-medium">مبكر</th>
                                    <th className="text-start p-2 font-medium">البيان</th>
                                    <th className="text-center p-2 font-medium">تعديل</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {emp.daily_details.map((day, idx) => {
                                    const config = STATUS_CONFIG[day.status] || STATUS_CONFIG['PRESENT'];
                                    
                                    // استخراج التاريخ والوقت من بصمة الدخول
                                    let checkInDate = '--/--';
                                    let checkInTime = '--:--';
                                    if (day.check_in_time) {
                                      const checkInParts = day.check_in_time.split('T');
                                      if (checkInParts.length >= 2) {
                                        checkInDate = checkInParts[0].slice(5); // MM-DD
                                        checkInTime = checkInParts[1].slice(0, 5); // HH:MM
                                      }
                                    }
                                    
                                    // استخراج التاريخ والوقت من بصمة الخروج
                                    let checkOutDate = '--/--';
                                    let checkOutTime = '--:--';
                                    if (day.check_out_time) {
                                      const checkOutParts = day.check_out_time.split('T');
                                      if (checkOutParts.length >= 2) {
                                        checkOutDate = checkOutParts[0].slice(5); // MM-DD
                                        checkOutTime = checkOutParts[1].slice(0, 5); // HH:MM
                                      }
                                    }
                                    
                                    return (
                                      <tr key={idx} className={`border-t ${config.bg}`}>
                                        <td className="p-2 font-mono text-xs">{day.date}</td>
                                        <td className="p-2 text-center">
                                          <Badge variant="secondary" className={`text-xs ${config.text}`}>
                                            {day.status_ar || config.label}
                                          </Badge>
                                        </td>
                                        <td className="p-2 text-center">
                                          <div className={`font-mono text-xs ${day.late_minutes > 0 ? 'text-amber-600 font-bold' : ''}`}>
                                            <div>{checkInDate}</div>
                                            <div className="text-sm font-semibold">{checkInTime}</div>
                                          </div>
                                        </td>
                                        <td className="p-2 text-center">
                                          <div className={`font-mono text-xs ${day.early_leave_minutes > 0 ? 'text-orange-600 font-bold' : ''}`}>
                                            <div>{checkOutDate}</div>
                                            <div className="text-sm font-semibold">{checkOutTime}</div>
                                          </div>
                                        </td>
                                        <td className="p-2 text-center">
                                          {day.late_minutes > 0 ? (
                                            <span className="text-amber-600 font-bold">{day.late_minutes}د</span>
                                          ) : '-'}
                                        </td>
                                        <td className="p-2 text-center">
                                          {day.early_leave_minutes > 0 ? (
                                            <span className="text-orange-600 font-bold">{day.early_leave_minutes}د</span>
                                          ) : '-'}
                                        </td>
                                        <td className="p-2 text-xs">
                                          {day.penalty_reason_ar || (
                                            day.status === 'ABSENT' ? 'غياب - خصم يوم' :
                                            day.late_minutes > 0 || day.early_leave_minutes > 0 ? 'نقص ساعات' :
                                            'لا خصم'
                                          )}
                                        </td>
                                        <td className="p-2 text-center">
                                          <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-7 w-7 p-0"
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              setStatusForm({
                                                employee_id: emp.employee_id,
                                                date: day.date,
                                                status: day.status,
                                                reason: ''
                                              });
                                              setShowStatusDialog(true);
                                            }}
                                          >
                                            <Edit size={14} />
                                          </Button>
                                        </td>
                                      </tr>
                                    );
                                  })}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Outside Hours */}
        <TabsContent value="outside">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <Card className="bg-gradient-to-br from-yellow-400 to-yellow-500 text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Clock size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">إجمالي الساعات</p>
                    <p className="text-2xl font-bold">{stats.totalHours?.toFixed(1) || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-orange-400 to-orange-500 text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <FileText size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">السجلات</p>
                    <p className="text-2xl font-bold">{stats.totalRecords || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-gradient-to-br from-amber-400 to-amber-500 text-white">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Users size={24} className="opacity-80" />
                  <div>
                    <p className="text-xs opacity-80">الموظفين</p>
                    <p className="text-2xl font-bold">{stats.uniqueEmployees || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Outside Hours List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock size={20} className="text-[hsl(var(--navy))]" />
                سجل خارج العمل الرسمي
                <Badge className="bg-slate-100 text-slate-700 mr-2">غير محتسب</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-12">
                  <RefreshCw className="animate-spin text-[hsl(var(--navy))]" size={32} />
                </div>
              ) : outsideHoursData.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  لا توجد بصمات خارج أوقات العمل
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="text-start p-3 font-medium">الموظف</th>
                        <th className="text-center p-3 font-medium">التاريخ</th>
                        <th className="text-center p-3 font-medium">الدخول</th>
                        <th className="text-center p-3 font-medium">الخروج</th>
                        <th className="text-center p-3 font-medium">الساعات</th>
                        <th className="text-center p-3 font-medium">الموقع</th>
                        <th className="text-center p-3 font-medium">النوع</th>
                        <th className="text-center p-3 font-medium">الإجراء</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outsideHoursData.map((rec, idx) => (
                        <tr key={idx} className={`border-t ${rec.category === 'weekend' ? 'bg-orange-50' : 'bg-amber-50'}`}>
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 rounded-full bg-[hsl(var(--navy)/0.1)] flex items-center justify-center text-[hsl(var(--navy))] font-bold text-xs">
                                {rec.employee_name_ar?.[0] || '?'}
                              </div>
                              <span className="font-medium">{rec.employee_name_ar}</span>
                            </div>
                          </td>
                          <td className="p-3 text-center font-mono">{rec.date}</td>
                          <td className="p-3 text-center font-mono text-[hsl(var(--navy))] font-bold">
                            {rec.check_in_time || '--:--'}
                          </td>
                          <td className="p-3 text-center font-mono text-[hsl(var(--navy))] font-bold">
                            {rec.check_out_time || '--:--'}
                          </td>
                          <td className="p-3 text-center">
                            <Badge className="bg-[hsl(var(--navy)/0.1)] text-[hsl(var(--navy))]">
                              {rec.total_hours?.toFixed(1) || 0} س
                            </Badge>
                          </td>
                          <td className="p-3 text-center text-xs">{rec.work_location || '-'}</td>
                          <td className="p-3 text-center">
                            <Badge className={rec.category === 'weekend' ? 'bg-orange-100 text-orange-700' : 'bg-amber-100 text-amber-700'}>
                              {rec.category === 'weekend' ? 'نهاية أسبوع' : 'يوم عمل'}
                            </Badge>
                          </td>
                          <td className="p-3 text-center">
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs h-7 border-green-500 text-green-600 hover:bg-green-50"
                              onClick={() => {
                                setCompensateForm({
                                  employee_id: rec.employee_id,
                                  date: rec.date,
                                  hours: rec.total_hours,
                                  note: ''
                                });
                                setShowCompensateDialog(true);
                              }}
                            >
                              <CheckCircle size={12} className="ml-1" />
                              احتسب
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Deduction Transactions */}
        <TabsContent value="deductions">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <Card className="bg-amber-50 border-amber-200">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-amber-600">بانتظار محمد</p>
                <p className="text-2xl font-bold text-amber-700">{stats.pending || 0}</p>
              </CardContent>
            </Card>
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-blue-600">بانتظار التنفيذ</p>
                <p className="text-2xl font-bold text-blue-700">{stats.pendingExec || 0}</p>
              </CardContent>
            </Card>
            <Card className="bg-emerald-50 border-emerald-200">
              <CardContent className="p-4 text-center">
                <p className="text-xs text-emerald-600">منفذة</p>
                <p className="text-2xl font-bold text-emerald-700">{stats.executed || 0}</p>
              </CardContent>
            </Card>
          </div>

          {/* Deductions List */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <DollarSign size={20} className="text-[hsl(var(--navy))]" />
                معاملات الخصم
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-12">
                  <RefreshCw className="animate-spin text-[hsl(var(--navy))]" size={32} />
                </div>
              ) : deductionTransactions.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  لا توجد معاملات خصم
                </div>
              ) : (
                <div className="space-y-3">
                  {deductionTransactions.map((txn) => {
                    const statusConfig = {
                      'pending_ceo': { bg: 'bg-amber-100', text: 'text-amber-700', label: 'بانتظار محمد' },
                      'pending_execution': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'بانتظار التنفيذ' },
                      'executed': { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'تم التنفيذ' },
                      'rejected': { bg: 'bg-red-100', text: 'text-red-700', label: 'مرفوض' }
                    }[txn.status] || { bg: 'bg-gray-100', text: 'text-gray-700', label: txn.status };
                    
                    return (
                      <div key={txn.ref_no} className={`border rounded-lg p-4 ${statusConfig.bg}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${statusConfig.bg} ${statusConfig.text}`}>
                              {txn.status === 'executed' ? <CheckCircle size={20} /> : 
                               txn.status === 'rejected' ? <XCircle size={20} /> : 
                               <Clock size={20} />}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-[hsl(var(--navy))]">{txn.ref_no}</span>
                                <Badge className={`${statusConfig.bg} ${statusConfig.text} text-xs`}>
                                  {statusConfig.label}
                                </Badge>
                              </div>
                              <p className="text-sm">{txn.employee_name_ar}</p>
                              <p className="text-xs text-muted-foreground">{txn.reason?.substring(0, 50)}</p>
                            </div>
                          </div>
                          <div className="text-left">
                            <p className="text-2xl font-bold text-[hsl(var(--navy))]">{txn.amount}</p>
                            <p className="text-xs text-muted-foreground">ر.س</p>
                          </div>
                        </div>
                        
                        {/* Approval Chain */}
                        {txn.approval_chain && txn.approval_chain.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-dashed">
                            <div className="flex flex-wrap items-center gap-2">
                              {txn.approval_chain.map((entry, idx) => (
                                <div key={idx} className="flex items-center gap-1">
                                  {idx > 0 && <ArrowRight size={12} className="text-muted-foreground" />}
                                  <Badge variant="outline" className="text-xs">
                                    {entry.actor_name} ({entry.action})
                                  </Badge>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Status Change Dialog */}
      <Dialog open={showStatusDialog} onOpenChange={setShowStatusDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="text-[hsl(var(--navy))]" size={20} />
              تعديل الحالة
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>التاريخ</Label>
              <Input value={statusForm.date} disabled />
            </div>
            
            <div>
              <Label>الحالة الجديدة</Label>
              <Select value={statusForm.status} onValueChange={v => setStatusForm(f => ({ ...f, status: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="اختر الحالة" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PRESENT">حاضر</SelectItem>
                  <SelectItem value="EXCUSED">معذور</SelectItem>
                  <SelectItem value="EXEMPTED">إعفاء</SelectItem>
                  <SelectItem value="ON_LEAVE">مجاز</SelectItem>
                  <SelectItem value="ON_MISSION">مهمة</SelectItem>
                  <SelectItem value="ABSENT">غائب</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>السبب</Label>
              <Textarea 
                value={statusForm.reason}
                onChange={e => setStatusForm(f => ({ ...f, reason: e.target.value }))}
                placeholder="اكتب سبب التعديل..."
              />
            </div>
            
            <div className="p-3 bg-amber-50 rounded-lg text-sm text-amber-700">
              تعديل الحالة سيؤثر على حساب العقوبات. تأكد من السبب قبل الحفظ.
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowStatusDialog(false)}>إلغاء</Button>
            <Button className="bg-[hsl(var(--navy))]" onClick={handleStatusChange}>حفظ التعديل</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Deduction Dialog */}
      <Dialog open={showDeductionDialog} onOpenChange={setShowDeductionDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <DollarSign className="text-[hsl(var(--navy))]" size={20} />
              إنشاء معاملة خصم
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>الموظف</Label>
              <Select value={deductionForm.employee_id} onValueChange={v => setDeductionForm(f => ({ ...f, employee_id: v }))}>
                <SelectTrigger>
                  <SelectValue placeholder="اختر الموظف" />
                </SelectTrigger>
                <SelectContent>
                  {employees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.full_name_ar || emp.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>المبلغ (ر.س)</Label>
              <Input 
                type="number" 
                value={deductionForm.amount}
                onChange={e => setDeductionForm(f => ({ ...f, amount: parseFloat(e.target.value) || 0 }))}
              />
            </div>
            
            <div>
              <Label>السبب</Label>
              <Textarea 
                value={deductionForm.reason}
                onChange={e => setDeductionForm(f => ({ ...f, reason: e.target.value }))}
                placeholder="اكتب سبب الخصم..."
              />
            </div>
            
            <div className="p-3 bg-blue-50 rounded-lg text-sm">
              سيتم إرسال المعاملة لمحمد للموافقة، ثم لستاس للتنفيذ.
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeductionDialog(false)}>إلغاء</Button>
            <Button className="bg-[hsl(var(--navy))]" onClick={handleCreateDeduction}>إرسال للموافقة</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Compensate Dialog */}
      <Dialog open={showCompensateDialog} onOpenChange={setShowCompensateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="text-green-600" size={20} />
              احتساب كحضور
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="p-3 bg-yellow-50 rounded-lg">
              <p className="text-sm"><strong>التاريخ:</strong> {compensateForm.date}</p>
              <p className="text-sm"><strong>الساعات:</strong> {compensateForm.hours?.toFixed(1) || 0} ساعة</p>
            </div>
            
            <div>
              <Label>نوع الاحتساب</Label>
              <Select 
                value={compensateForm.hours === null ? 'full' : 'hours'}
                onValueChange={v => setCompensateForm(f => ({ ...f, hours: v === 'full' ? null : f.hours }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="full">احتساب كحضور كامل (تحويل الغياب إلى حاضر)</SelectItem>
                  <SelectItem value="hours">تعويض ساعات فقط (للتأخيرات)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>ملاحظة (اختياري)</Label>
              <Textarea 
                value={compensateForm.note}
                onChange={e => setCompensateForm(f => ({ ...f, note: e.target.value }))}
                placeholder="أي ملاحظة..."
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCompensateDialog(false)}>إلغاء</Button>
            <Button className="bg-green-600 hover:bg-green-700" onClick={handleCompensate}>
              <CheckCircle size={16} className="ml-1" />
              تأكيد الاحتساب
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
