/**
 * صفحة إدارة الحضور والعقوبات - مبسطة وموحدة
 * 
 * تجمع كل ما يخص الحضور والعقوبات في شاشة واحدة سهلة:
 * - عرض الحضور مع الخصومات مباشرة
 * - إشعارات الطلبات المعلقة
 * - إنشاء معاملات الخصم
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
  Download
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// ألوان الحالات
const STATUS_CONFIG = {
  'PRESENT': { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-600', label: 'حاضر' },
  'ABSENT': { bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-600', label: 'غائب' },
  'LATE': { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-600', label: 'متأخر' },
  'ON_LEAVE': { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-600', label: 'إجازة' },
  'ON_MISSION': { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-600', label: 'مهمة' },
  'WEEKEND': { bg: 'bg-slate-50 dark:bg-slate-900/20', text: 'text-slate-500', label: 'عطلة' },
  'HOLIDAY': { bg: 'bg-indigo-50 dark:bg-indigo-900/20', text: 'text-indigo-600', label: 'عطلة رسمية' },
};

export default function AttendanceManagementPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  
  // States
  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState([]);
  const [selectedEmployee, setSelectedEmployee] = useState('all');
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [attendanceData, setAttendanceData] = useState([]);
  const [pendingRequests, setPendingRequests] = useState({ corrections: 0, deductions: 0 });
  const [expandedEmployee, setExpandedEmployee] = useState(null);
  const [showDeductionDialog, setShowDeductionDialog] = useState(false);
  const [deductionForm, setDeductionForm] = useState({ employee_id: '', amount: 0, reason: '', month: '' });
  
  // Fetch employees
  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const res = await api.get('/api/employees');
        // استثناء المدراء
        const filtered = res.data.filter(e => 
          !['stas', 'mohammed', 'salah', 'naif'].includes(e.user_id?.toLowerCase()) &&
          e.is_active !== false
        );
        setEmployees(filtered);
      } catch (err) {
        console.error('Error fetching employees:', err);
      }
    };
    fetchEmployees();
  }, []);

  // Fetch attendance data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // جلب تقرير العقوبات
        const month = startDate.substring(0, 7);
        const res = await api.get('/api/penalties/monthly-report', {
          params: { year: parseInt(month.split('-')[0]), month: parseInt(month.split('-')[1]) }
        });
        
        let data = res.data.employees || [];
        
        // فلترة حسب الموظف المحدد
        if (selectedEmployee !== 'all') {
          data = data.filter(e => e.employee_id === selectedEmployee);
        }
        
        setAttendanceData(data);
        
        // جلب الطلبات المعلقة
        try {
          const pendingRes = await api.get('/api/attendance-engine/deductions/pending');
          setPendingRequests(prev => ({ ...prev, deductions: pendingRes.data?.length || 0 }));
        } catch (e) {}
        
      } catch (err) {
        console.error('Error fetching data:', err);
        toast.error(lang === 'ar' ? 'خطأ في جلب البيانات' : 'Error fetching data');
      } finally {
        setLoading(false);
      }
    };
    
    if (startDate && endDate) {
      fetchData();
    }
  }, [startDate, endDate, selectedEmployee, lang]);

  // حساب الإحصائيات
  const stats = useMemo(() => {
    return {
      totalEmployees: attendanceData.length,
      totalAbsent: attendanceData.reduce((sum, e) => sum + (e.absence?.total_days || 0), 0),
      totalDeduction: attendanceData.reduce((sum, e) => sum + (e.total_deduction_amount || 0), 0),
      totalDeficitHours: attendanceData.reduce((sum, e) => sum + (e.deficit?.total_deficit_hours || 0), 0)
    };
  }, [attendanceData]);

  // إنشاء معاملة خصم
  const handleCreateDeduction = async () => {
    if (!deductionForm.employee_id || !deductionForm.amount || !deductionForm.reason) {
      toast.error(lang === 'ar' ? 'يرجى ملء جميع الحقول' : 'Please fill all fields');
      return;
    }
    
    try {
      await api.post('/api/deductions', {
        ...deductionForm,
        type: 'deduction',
        month: startDate.substring(0, 7)
      });
      toast.success(lang === 'ar' ? 'تم إنشاء معاملة الخصم وإرسالها لمحمد' : 'Deduction created and sent to Mohammed');
      setShowDeductionDialog(false);
      setDeductionForm({ employee_id: '', amount: 0, reason: '', month: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error creating deduction');
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
      
      if (selectedEmployee !== 'all') {
        params.employee_id = selectedEmployee;
      }
      
      const response = await api.get('/api/team-attendance/print-report', {
        params,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      
      toast.success(lang === 'ar' ? 'تم فتح التقرير' : 'Report opened');
    } catch (err) {
      toast.error(lang === 'ar' ? 'خطأ في طباعة التقرير' : 'Error printing report');
    }
  };

  return (
    <div className="space-y-4 p-4 md:p-6" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[hsl(var(--navy))] dark:text-white">
            {lang === 'ar' ? 'الحضور والعقوبات' : 'Attendance & Penalties'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {lang === 'ar' ? 'متابعة حضور الموظفين والخصومات' : 'Track employee attendance and deductions'}
          </p>
        </div>
        
        {/* Pending Requests Alert */}
        {pendingRequests.deductions > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <Bell className="text-amber-500" size={18} />
            <span className="text-sm text-amber-700 dark:text-amber-300">
              {lang === 'ar' ? `${pendingRequests.deductions} خصم معلق` : `${pendingRequests.deductions} pending deductions`}
            </span>
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-gradient-to-br from-[hsl(var(--navy))] to-[hsl(var(--navy-dark))] text-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Users size={24} className="opacity-80" />
              <div>
                <p className="text-xs opacity-80">{lang === 'ar' ? 'الموظفين' : 'Employees'}</p>
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
                <p className="text-xs opacity-80">{lang === 'ar' ? 'أيام الغياب' : 'Absent Days'}</p>
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
                <p className="text-xs opacity-80">{lang === 'ar' ? 'ساعات النقص' : 'Deficit Hours'}</p>
                <p className="text-2xl font-bold">{stats.totalDeficitHours.toFixed(1)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-[hsl(var(--lavender))] to-purple-600 text-white">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <TrendingDown size={24} className="opacity-80" />
              <div>
                <p className="text-xs opacity-80">{lang === 'ar' ? 'إجمالي الخصم' : 'Total Deduction'}</p>
                <p className="text-2xl font-bold">{stats.totalDeduction.toFixed(0)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-3 items-end">
            {/* Employee Filter */}
            <div className="flex-1 min-w-[200px]">
              <Label className="text-xs mb-1 block">{lang === 'ar' ? 'الموظف' : 'Employee'}</Label>
              <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
                <SelectTrigger>
                  <SelectValue placeholder={lang === 'ar' ? 'جميع الموظفين' : 'All Employees'} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{lang === 'ar' ? 'جميع الموظفين' : 'All Employees'}</SelectItem>
                  {employees.map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>
                      {emp.full_name_ar || emp.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Date Range */}
            <div className="flex gap-2">
              <div>
                <Label className="text-xs mb-1 block">{lang === 'ar' ? 'من' : 'From'}</Label>
                <Input 
                  type="date" 
                  value={startDate} 
                  onChange={e => setStartDate(e.target.value)}
                  className="w-[140px]"
                />
              </div>
              <div>
                <Label className="text-xs mb-1 block">{lang === 'ar' ? 'إلى' : 'To'}</Label>
                <Input 
                  type="date" 
                  value={endDate} 
                  onChange={e => setEndDate(e.target.value)}
                  className="w-[140px]"
                />
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handlePrint}>
                <Printer size={16} className="mr-1" />
                {lang === 'ar' ? 'طباعة' : 'Print'}
              </Button>
              <Button 
                size="sm" 
                className="bg-[hsl(var(--navy))] hover:bg-[hsl(var(--navy-dark))]"
                onClick={() => setShowDeductionDialog(true)}
              >
                <Plus size={16} className="mr-1" />
                {lang === 'ar' ? 'معاملة خصم' : 'New Deduction'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Attendance Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText size={20} className="text-[hsl(var(--navy))]" />
            {lang === 'ar' ? 'سجل الحضور والخصومات' : 'Attendance & Deductions Record'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <RefreshCw className="animate-spin text-[hsl(var(--navy))]" size={32} />
            </div>
          ) : attendanceData.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {lang === 'ar' ? 'لا توجد بيانات' : 'No data available'}
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
                      {/* Absence Badge */}
                      {emp.absence?.total_days > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          <UserX size={12} className="mr-1" />
                          {emp.absence.total_days} {lang === 'ar' ? 'غياب' : 'absent'}
                        </Badge>
                      )}
                      
                      {/* Deficit Badge */}
                      {emp.deficit?.total_deficit_hours > 0 && (
                        <Badge variant="outline" className="text-xs text-amber-600 border-amber-300">
                          <Clock size={12} className="mr-1" />
                          {emp.deficit.total_deficit_hours}h
                        </Badge>
                      )}
                      
                      {/* Deduction Badge */}
                      {emp.total_deduction_days > 0 && (
                        <Badge className="bg-[hsl(var(--lavender)/0.2)] text-[hsl(var(--lavender))] text-xs">
                          <TrendingDown size={12} className="mr-1" />
                          {emp.total_deduction_days} {lang === 'ar' ? 'يوم' : 'days'}
                        </Badge>
                      )}
                      
                      {/* Warning Badge */}
                      {emp.absence?.warnings?.length > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          <AlertTriangle size={12} className="mr-1" />
                          {lang === 'ar' ? 'إنذار' : 'Warning'}
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
                        <div className="p-3 bg-red-50 dark:bg-red-900/10 rounded-lg text-center">
                          <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'أيام الغياب' : 'Absent'}</p>
                          <p className="text-xl font-bold text-red-600">{emp.absence?.total_days || 0}</p>
                        </div>
                        <div className="p-3 bg-amber-50 dark:bg-amber-900/10 rounded-lg text-center">
                          <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'دقائق التأخير' : 'Late'}</p>
                          <p className="text-xl font-bold text-amber-600">{emp.deficit?.total_late_minutes || 0}</p>
                        </div>
                        <div className="p-3 bg-orange-50 dark:bg-orange-900/10 rounded-lg text-center">
                          <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'خروج مبكر' : 'Early'}</p>
                          <p className="text-xl font-bold text-orange-600">{emp.deficit?.total_early_leave_minutes || 0}</p>
                        </div>
                        <div className="p-3 bg-[hsl(var(--lavender)/0.1)] rounded-lg text-center">
                          <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'إجمالي الخصم' : 'Deduction'}</p>
                          <p className="text-xl font-bold text-[hsl(var(--lavender))]">{emp.total_deduction_days || 0} {lang === 'ar' ? 'يوم' : 'd'}</p>
                        </div>
                      </div>
                      
                      {/* Daily Details Table */}
                      {emp.daily_details && emp.daily_details.length > 0 && (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-[hsl(var(--navy)/0.05)]">
                              <tr>
                                <th className="text-start p-2 font-medium">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                                <th className="text-center p-2 font-medium">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                                <th className="text-center p-2 font-medium">{lang === 'ar' ? 'الدخول' : 'In'}</th>
                                <th className="text-center p-2 font-medium">{lang === 'ar' ? 'الخروج' : 'Out'}</th>
                                <th className="text-center p-2 font-medium">{lang === 'ar' ? 'تأخير' : 'Late'}</th>
                                <th className="text-center p-2 font-medium">{lang === 'ar' ? 'مبكر' : 'Early'}</th>
                                <th className="text-start p-2 font-medium">{lang === 'ar' ? 'البيان' : 'Note'}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {emp.daily_details
                                .filter(d => d.status === 'ABSENT' || d.late_minutes > 0 || d.early_leave_minutes > 0 || d.status === 'ON_MISSION')
                                .map((day, idx) => {
                                  const config = STATUS_CONFIG[day.status] || STATUS_CONFIG['PRESENT'];
                                  const checkIn = day.check_in_time ? day.check_in_time.slice(11, 16) : '--:--';
                                  const checkOut = day.check_out_time ? day.check_out_time.slice(11, 16) : '--:--';
                                  
                                  return (
                                    <tr key={idx} className={`border-t ${config.bg}`}>
                                      <td className="p-2 font-mono text-xs">{day.date}</td>
                                      <td className="p-2 text-center">
                                        <Badge variant="secondary" className={`text-xs ${config.text}`}>
                                          {day.status_ar || config.label}
                                        </Badge>
                                      </td>
                                      <td className="p-2 text-center font-mono text-xs">
                                        <span className={day.late_minutes > 0 ? 'text-amber-600 font-bold' : ''}>
                                          {checkIn}
                                        </span>
                                      </td>
                                      <td className="p-2 text-center font-mono text-xs">
                                        <span className={day.early_leave_minutes > 0 ? 'text-orange-600 font-bold' : ''}>
                                          {checkOut}
                                        </span>
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
                                          day.status === 'ABSENT' ? '⛔ غياب - خصم يوم' :
                                          day.late_minutes > 0 || day.early_leave_minutes > 0 ? '⏰ نقص ساعات' :
                                          '✅ لا خصم'
                                        )}
                                      </td>
                                    </tr>
                                  );
                                })}
                            </tbody>
                          </table>
                          
                          {emp.daily_details.filter(d => d.status === 'ABSENT' || d.late_minutes > 0 || d.early_leave_minutes > 0).length === 0 && (
                            <p className="text-center py-4 text-muted-foreground text-sm">
                              ✅ {lang === 'ar' ? 'لا توجد مخالفات' : 'No violations'}
                            </p>
                          )}
                        </div>
                      )}
                      
                      {/* Absence Periods */}
                      {emp.absence?.consecutive_streaks?.length > 0 && (
                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg">
                          <p className="text-sm font-medium text-red-700 mb-2">
                            {lang === 'ar' ? 'فترات الغياب المتصل:' : 'Consecutive Absence:'}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {emp.absence.consecutive_streaks.map((s, i) => (
                              <Badge key={i} variant="destructive" className="text-xs">
                                {s.start} → {s.end} ({s.days} {lang === 'ar' ? 'يوم' : 'days'})
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Quick Actions */}
                      <div className="mt-4 flex gap-2">
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => {
                            setDeductionForm({
                              employee_id: emp.employee_id,
                              amount: (emp.total_deduction_days || 0) * (emp.daily_salary || 0),
                              reason: `خصم ${emp.absence?.total_days || 0} يوم غياب + ${emp.deficit?.total_deficit_hours || 0} ساعة نقص`,
                              month: startDate.substring(0, 7)
                            });
                            setShowDeductionDialog(true);
                          }}
                        >
                          <Plus size={14} className="mr-1" />
                          {lang === 'ar' ? 'إنشاء معاملة خصم' : 'Create Deduction'}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Deduction Dialog */}
      <Dialog open={showDeductionDialog} onOpenChange={setShowDeductionDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="text-[hsl(var(--navy))]" size={20} />
              {lang === 'ar' ? 'إنشاء معاملة خصم' : 'Create Deduction Transaction'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Employee */}
            <div>
              <Label>{lang === 'ar' ? 'الموظف' : 'Employee'}</Label>
              <Select 
                value={deductionForm.employee_id} 
                onValueChange={v => setDeductionForm(f => ({ ...f, employee_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder={lang === 'ar' ? 'اختر الموظف' : 'Select Employee'} />
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
            
            {/* Amount */}
            <div>
              <Label>{lang === 'ar' ? 'المبلغ (ر.س)' : 'Amount (SAR)'}</Label>
              <Input 
                type="number" 
                value={deductionForm.amount}
                onChange={e => setDeductionForm(f => ({ ...f, amount: parseFloat(e.target.value) || 0 }))}
              />
            </div>
            
            {/* Reason */}
            <div>
              <Label>{lang === 'ar' ? 'السبب' : 'Reason'}</Label>
              <Textarea 
                value={deductionForm.reason}
                onChange={e => setDeductionForm(f => ({ ...f, reason: e.target.value }))}
                placeholder={lang === 'ar' ? 'اكتب سبب الخصم...' : 'Enter deduction reason...'}
                rows={3}
              />
            </div>
            
            {/* Info */}
            <div className="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg text-sm">
              <p className="text-blue-700 dark:text-blue-300">
                ℹ️ {lang === 'ar' 
                  ? 'سيتم إرسال المعاملة لمحمد للموافقة، ثم لستاس للتنفيذ.' 
                  : 'Transaction will be sent to Mohammed for approval, then STAS for execution.'}
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeductionDialog(false)}>
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button 
              className="bg-[hsl(var(--navy))] hover:bg-[hsl(var(--navy-dark))]"
              onClick={handleCreateDeduction}
            >
              {lang === 'ar' ? 'إرسال للموافقة' : 'Send for Approval'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
