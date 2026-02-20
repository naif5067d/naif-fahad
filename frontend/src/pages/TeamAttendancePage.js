/**
 * Team Attendance & Penalties Page - الحضور والعقوبات
 * 
 * لسلطان ونايف وستاس:
 * - تبويبات: الحضور | العقوبات
 * - قائمة منسدلة لاختيار الموظف
 * - عرض سجل الموظف (يومي/أسبوعي/شهري/سنوي)
 * - تعديل حالة الموظف
 * - زر التحضير اليدوي (لا يتعارض مع الذاتي)
 */
import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
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
  Edit,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  User,
  TrendingDown,
  FileWarning,
  CalendarDays,
  MapPin,
  PlayCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  HandMetal,
  LogIn,
  LogOut
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// الموظفون المستثنون من الحضور والعقوبات (ليسوا موظفين)
const EXEMPT_ROLES = ['stas', 'mohammed', 'salah', 'naif'];

const STATUS_COLORS = {
  'PRESENT': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'ABSENT': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  'LATE': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  'ON_LEAVE': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'ON_ADMIN_LEAVE': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'WEEKEND': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  'HOLIDAY': 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  'ON_MISSION': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  'NOT_REGISTERED': 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
  'UNKNOWN': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  'NOT_PROCESSED': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  'PERMISSION': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400'
};

const STATUS_AR = {
  'PRESENT': 'حاضر',
  'ABSENT': 'غائب',
  'LATE': 'متأخر',
  'ON_LEAVE': 'إجازة',
  'ON_ADMIN_LEAVE': 'إجازة إدارية',
  'WEEKEND': 'عطلة نهاية أسبوع',
  'HOLIDAY': 'عطلة رسمية',
  'ON_MISSION': 'مهمة خارجية',
  'NOT_REGISTERED': 'لم يُسجل',
  'UNKNOWN': 'لم يُسجل',
  'NOT_PROCESSED': 'غير محلل',
  'PERMISSION': 'استئذان',
  'EARLY_LEAVE': 'خروج مبكر',
  'LATE_EXCUSED': 'تأخير معذور',
  'EARLY_EXCUSED': 'خروج مبكر معذور'
};

export default function TeamAttendancePage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  
  // Main tab: 'attendance' or 'penalties'
  const [mainTab, setMainTab] = useState('attendance');
  
  // View mode: 'all' for all employees, 'single' for one employee
  const [viewMode, setViewMode] = useState('all');
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [employees, setEmployees] = useState([]);
  
  const [tab, setTab] = useState('daily');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [year, setYear] = useState(new Date().getFullYear().toString());
  
  const [summary, setSummary] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [weeklyData, setWeeklyData] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [yearlyData, setYearlyData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Employee record for single view
  const [employeeRecord, setEmployeeRecord] = useState(null);
  
  // Manual Attendance Processing
  const [processingAttendance, setProcessingAttendance] = useState(false);
  
  // Penalties data
  const [penaltiesReport, setPenaltiesReport] = useState(null);
  const [expandedPenaltyEmployee, setExpandedPenaltyEmployee] = useState(null);
  
  // Deduction Review (Sultan/Naif only)
  const [pendingDeductions, setPendingDeductions] = useState([]);
  const [selectedDeduction, setSelectedDeduction] = useState(null);
  const [deductionTrace, setDeductionTrace] = useState([]);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [reviewingDeduction, setReviewingDeduction] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [expandedDeduction, setExpandedDeduction] = useState(null);
  
  // Edit Dialog
  const [editDialog, setEditDialog] = useState(null);
  const [editForm, setEditForm] = useState({
    new_status: 'PRESENT',
    reason: '',
    check_in_time: '08:00',
    check_out_time: '17:00',
    supervisor_acknowledgment: false // إقرار المشرف
  });
  
  // Pending Corrections for Sultan
  const [pendingCorrections, setPendingCorrections] = useState([]);
  const [correctionDecision, setCorrectionDecision] = useState(null);
  
  // Trace Dialog
  const [traceDialog, setTraceDialog] = useState(null);
  const [traceData, setTraceData] = useState(null);
  
  // Manual Attendance for Supervisors
  const [myTeamAttendance, setMyTeamAttendance] = useState([]);
  const [manualAttendanceDialog, setManualAttendanceDialog] = useState(null);
  const [manualAttendanceForm, setManualAttendanceForm] = useState({
    check_type: 'check_in',
    time: '',
    reason: '',
    supervisor_acknowledgment: false
  });
  const [submittingManual, setSubmittingManual] = useState(false);
  
  // Check if user is supervisor
  const isSupervisor = user?.role === 'supervisor';
  const isSultan = ['sultan', 'naif'].includes(user?.role);
  const isStas = user?.role === 'stas';

  // Filter employees - exclude non-employee roles
  const filteredEmployees = useMemo(() => {
    return employees.filter(e => !EXEMPT_ROLES.includes(e.role));
  }, [employees]);

  // Fetch employees list
  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const res = await api.get('/api/employees');
        setEmployees(res.data.filter(e => e.is_active !== false));
      } catch (err) {
        console.error('Error fetching employees:', err);
      }
    };
    fetchEmployees();
  }, []);
  
  // Fetch supervisor's team attendance for manual check-in
  useEffect(() => {
    if (isSupervisor && mainTab === 'manual-attendance') {
      fetchMyTeamAttendance();
    }
  }, [isSupervisor, mainTab, date]);
  
  const fetchMyTeamAttendance = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/team-attendance/my-team-attendance', { params: { date } });
      setMyTeamAttendance(res.data || []);
    } catch (err) {
      console.error('Error fetching team attendance:', err);
      toast.error(lang === 'ar' ? 'خطأ في جلب بيانات الفريق' : 'Error fetching team data');
    } finally {
      setLoading(false);
    }
  };
  
  const handleOpenManualAttendance = (employee, checkType) => {
    setManualAttendanceDialog(employee);
    setManualAttendanceForm({
      check_type: checkType,
      time: new Date().toTimeString().slice(0, 5),
      reason: '',
      supervisor_acknowledgment: false
    });
  };
  
  const handleSubmitManualAttendance = async () => {
    if (!manualAttendanceForm.reason) {
      toast.error(lang === 'ar' ? 'يرجى إدخال السبب' : 'Please enter reason');
      return;
    }
    if (!manualAttendanceForm.supervisor_acknowledgment) {
      toast.error(lang === 'ar' 
        ? 'يرجى تأكيد الإقرار بتحمل المسؤولية' 
        : 'Please confirm acknowledgment'
      );
      return;
    }
    
    try {
      setSubmittingManual(true);
      await api.post('/api/team-attendance/manual-attendance', {
        employee_id: manualAttendanceDialog.employee_id,
        check_type: manualAttendanceForm.check_type,
        time: manualAttendanceForm.time,
        reason: manualAttendanceForm.reason,
        supervisor_acknowledgment: true
      });
      
      toast.success(lang === 'ar' 
        ? `تم تسجيل ${manualAttendanceForm.check_type === 'check_in' ? 'الدخول' : 'الخروج'} بنجاح`
        : `${manualAttendanceForm.check_type === 'check_in' ? 'Check-in' : 'Check-out'} recorded successfully`
      );
      
      setManualAttendanceDialog(null);
      fetchMyTeamAttendance();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        toast.error(lang === 'ar' ? detail.message_ar : detail.message_en);
      } else {
        toast.error(detail || 'Error recording attendance');
      }
    } finally {
      setSubmittingManual(false);
    }
  };

  // Fetch pending deductions for review (Sultan/Naif only)
  useEffect(() => {
    if (isSultan) {
      fetchPendingDeductions();
      fetchPendingCorrections();
    }
  }, [user?.role]);

  // Fetch pending corrections (Sultan only)
  const fetchPendingCorrections = async () => {
    try {
      const res = await api.get('/api/team-attendance/pending-corrections');
      setPendingCorrections(res.data || []);
    } catch (err) {
      console.error('Error fetching pending corrections:', err);
    }
  };

  const fetchPendingDeductions = async () => {
    try {
      const res = await api.get('/api/attendance-engine/deductions/pending');
      setPendingDeductions(res.data || []);
    } catch (err) {
      console.error('Error fetching pending deductions:', err);
    }
  };

  const loadDeductionTrace = async (deduction) => {
    setSelectedDeduction(deduction);
    setLoadingTrace(true);
    setDeductionTrace([]);
    try {
      const res = await api.get(`/api/attendance-engine/daily-status/${deduction.employee_id}/${deduction.period_start}`);
      if (res.data?.trace_log && Array.isArray(res.data.trace_log)) {
        setDeductionTrace(res.data.trace_log);
      }
    } catch (err) {
      console.error('Failed to load trace:', err);
    } finally {
      setLoadingTrace(false);
    }
  };

  const handleReviewDeduction = async (proposalId, approved) => {
    setReviewingDeduction(true);
    try {
      await api.post(`/api/attendance-engine/deductions/${proposalId}/review`, {
        approved,
        note: reviewNote
      });
      toast.success(approved 
        ? (lang === 'ar' ? 'تمت الموافقة على الخصم' : 'Deduction approved')
        : (lang === 'ar' ? 'تم رفض الخصم' : 'Deduction rejected')
      );
      setSelectedDeduction(null);
      setReviewNote('');
      fetchPendingDeductions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to review deduction');
    } finally {
      setReviewingDeduction(false);
    }
  };

  // Fetch data based on view mode and tab
  useEffect(() => {
    if (viewMode === 'all') {
      fetchAllData();
    } else if (viewMode === 'single' && selectedEmployee) {
      fetchEmployeeData();
    }
  }, [viewMode, selectedEmployee, tab, date, month, year]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const summaryRes = await api.get('/api/team-attendance/summary', { params: { date } });
      setSummary(summaryRes.data);
      
      if (tab === 'daily') {
        const res = await api.get('/api/team-attendance/daily', { params: { date } });
        setDailyData(res.data);
      } else if (tab === 'weekly') {
        const res = await api.get('/api/team-attendance/weekly', { params: { date } });
        setWeeklyData(res.data);
      } else if (tab === 'monthly') {
        const res = await api.get('/api/team-attendance/monthly', { params: { month } });
        setMonthlyData(res.data);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      toast.error(lang === 'ar' ? 'خطأ في جلب البيانات' : 'Error fetching data');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmployeeData = async () => {
    if (!selectedEmployee) return;
    setLoading(true);
    try {
      const res = await api.get(`/api/team-attendance/employee/${selectedEmployee}`, {
        params: { period: tab, date, month, year }
      });
      setEmployeeRecord(res.data);
    } catch (err) {
      console.error('Error fetching employee data:', err);
      // Fallback to manual filtering
      if (tab === 'daily') {
        const res = await api.get('/api/team-attendance/daily', { params: { date } });
        const empData = res.data.find(e => e.employee_id === selectedEmployee);
        setEmployeeRecord({ daily: empData ? [empData] : [], summary: {} });
      } else if (tab === 'monthly') {
        const res = await api.get('/api/team-attendance/monthly', { params: { month } });
        const empData = res.data.find(e => e.employee_id === selectedEmployee);
        setEmployeeRecord({ monthly: empData, summary: empData || {} });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (employee) => {
    setEditDialog(employee);
    setEditForm({
      new_status: employee.final_status === 'ABSENT' ? 'PRESENT' : employee.final_status,
      reason: '',
      check_in_time: employee.check_in_time?.slice(11, 16) || '08:00',
      check_out_time: employee.check_out_time?.slice(11, 16) || '17:00',
      supervisor_acknowledgment: false
    });
  };

  const handleSaveEdit = async () => {
    if (!editForm.reason) {
      toast.error(lang === 'ar' ? 'يرجى إدخال السبب' : 'Please enter reason');
      return;
    }
    
    try {
      setLoading(true);
      
      if (isSupervisor) {
        // المشرف يرسل طلب تعديل - يحتاج إقرار
        if (!editForm.supervisor_acknowledgment) {
          toast.error(lang === 'ar' 
            ? `عزيزي ${user?.full_name_ar || user?.full_name || 'المشرف'}، تعديلك للحالة يعني تحملك لمسؤوليتها. يرجى تأكيد الإقرار.`
            : `Dear ${user?.full_name || 'Supervisor'}, modifying this status means you take responsibility for it. Please confirm acknowledgment.`
          );
          return;
        }
        
        await api.post(`/api/team-attendance/${editDialog.employee_id}/request-correction/${editDialog.date}`, {
          new_status: editForm.new_status,
          reason: editForm.reason,
          check_in_time: editForm.check_in_time,
          check_out_time: editForm.check_out_time,
          supervisor_acknowledgment: true
        });
        toast.success(lang === 'ar' 
          ? 'تم إرسال طلب التعديل لسلطان للموافقة' 
          : 'Correction request sent to Sultan for approval'
        );
      } else {
        // سلطان/نايف/STAS - تعديل مباشر
        await api.post(`/api/team-attendance/${editDialog.employee_id}/update-status?date=${editDialog.date}`, editForm);
        toast.success(lang === 'ar' ? 'تم تحديث الحالة بنجاح' : 'Status updated successfully');
      }
      
      setEditDialog(null);
      if (viewMode === 'all') fetchAllData();
      else fetchEmployeeData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        toast.error(lang === 'ar' ? detail.message_ar : detail.message_en);
      } else {
        toast.error(detail || 'Error updating status');
      }
    } finally {
      setLoading(false);
    }
  };

  // قرار سلطان على طلب التعديل
  const handleCorrectionDecision = async (correctionId, action, finalStatus = null, note = '') => {
    try {
      setLoading(true);
      await api.post(`/api/team-attendance/correction/${correctionId}/decide`, {
        action,
        final_status: finalStatus,
        decision_note: note
      });
      toast.success(lang === 'ar' 
        ? (action === 'approve' ? 'تمت الموافقة' : action === 'reject' ? 'تم الرفض' : 'تم التعديل')
        : (action === 'approve' ? 'Approved' : action === 'reject' ? 'Rejected' : 'Modified')
      );
      setCorrectionDecision(null);
      fetchPendingCorrections();
      fetchAllData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error processing decision');
    } finally {
      setLoading(false);
    }
  };

  const handleViewTrace = async (employee) => {
    try {
      const res = await api.get(`/api/team-attendance/${employee.employee_id}/trace/${employee.date}`);
      setTraceData(res.data);
      setTraceDialog(employee);
    } catch (err) {
      toast.error('Error fetching trace data');
    }
  };

  const handleEmployeeSelect = (empId) => {
    if (empId === 'all') {
      setViewMode('all');
      setSelectedEmployee(null);
    } else {
      setViewMode('single');
      setSelectedEmployee(empId);
    }
  };

  // Manual Attendance Processing - التحضير اليدوي
  const handleManualProcess = async () => {
    setProcessingAttendance(true);
    try {
      const res = await api.post('/api/attendance-engine/process-daily', { date });
      toast.success(lang === 'ar' 
        ? `تم التحضير بنجاح: ${res.data.processed || 0} موظف` 
        : `Processed successfully: ${res.data.processed || 0} employees`
      );
      // Refresh data
      fetchAllData();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'خطأ في التحضير' : 'Error processing'));
    } finally {
      setProcessingAttendance(false);
    }
  };

  // Fetch Penalties Report
  const fetchPenaltiesReport = async () => {
    setLoading(true);
    try {
      const [yearVal, monthVal] = month.split('-').map(Number);
      const res = await api.get('/api/penalties/monthly-report', {
        params: { year: yearVal, month: monthVal }
      });
      setPenaltiesReport(res.data);
    } catch (err) {
      console.error('Error fetching penalties:', err);
      toast.error(lang === 'ar' ? 'خطأ في جلب العقوبات' : 'Error fetching penalties');
    } finally {
      setLoading(false);
    }
  };

  // Fetch penalties when switching to penalties tab
  useEffect(() => {
    if (mainTab === 'penalties') {
      fetchPenaltiesReport();
    }
  }, [mainTab, month]);

  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    return timestamp.slice(11, 16);
  };

  const selectedEmployeeData = useMemo(() => {
    return employees.find(e => e.id === selectedEmployee);
  }, [employees, selectedEmployee]);

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="team-attendance-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="text-primary" />
            {lang === 'ar' ? 'الحضور والعقوبات' : 'Attendance & Penalties'}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {lang === 'ar' ? 'متابعة حضور الموظفين والعقوبات والخصومات' : 'Track attendance, penalties and deductions'}
          </p>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          {/* Manual Process Button */}
          <Button 
            variant="outline" 
            onClick={handleManualProcess}
            disabled={processingAttendance}
            className="gap-2"
          >
            {processingAttendance ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <PlayCircle size={16} />
            )}
            {lang === 'ar' ? 'تحضير' : 'Process'}
          </Button>
          
          {/* Employee Selector */}
          <Select value={selectedEmployee || 'all'} onValueChange={handleEmployeeSelect}>
            <SelectTrigger className="w-[200px]" data-testid="employee-selector">
              <SelectValue placeholder={lang === 'ar' ? 'اختر موظف' : 'Select Employee'} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <span className="flex items-center gap-2">
                  <Users size={16} />
                  {lang === 'ar' ? 'جميع الموظفين' : 'All Employees'}
                </span>
              </SelectItem>
              {filteredEmployees.map(emp => (
                <SelectItem key={emp.id} value={emp.id}>
                  <span className="flex items-center gap-2">
                    <User size={16} />
                    {lang === 'ar' ? emp.full_name_ar : emp.full_name} ({emp.employee_number})
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* Date Selector */}
          {tab !== 'yearly' && (
            <Input
              type={tab === 'monthly' ? 'month' : 'date'}
              value={tab === 'monthly' ? month : date}
              onChange={(e) => tab === 'monthly' ? setMonth(e.target.value) : setDate(e.target.value)}
              className="w-auto"
            />
          )}
          {tab === 'yearly' && (
            <Select value={year} onValueChange={setYear}>
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[2024, 2025, 2026].map(y => (
                  <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          <Button variant="outline" size="icon" onClick={() => viewMode === 'all' ? fetchAllData() : fetchEmployeeData()} disabled={loading}>
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      {/* Selected Employee Info */}
      {viewMode === 'single' && selectedEmployeeData && (
        <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xl font-bold">
                {selectedEmployeeData.full_name_ar?.[0] || selectedEmployeeData.full_name?.[0] || '?'}
              </div>
              <div>
                <h2 className="text-lg font-bold">
                  {lang === 'ar' ? selectedEmployeeData.full_name_ar : selectedEmployeeData.full_name}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {selectedEmployeeData.employee_number} • {selectedEmployeeData.job_title_ar || selectedEmployeeData.job_title}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards - Only for All Employees View */}
      {viewMode === 'all' && summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Card className="border-emerald-200">
            <CardContent className="p-4 text-center">
              <UserCheck className="mx-auto mb-2 text-emerald-500" size={24} />
              <p className="text-2xl font-bold text-emerald-600">{summary.present}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'حاضر' : 'Present'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-red-200">
            <CardContent className="p-4 text-center">
              <UserX className="mx-auto mb-2 text-red-500" size={24} />
              <p className="text-2xl font-bold text-red-600">{summary.absent}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'غائب' : 'Absent'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-amber-200">
            <CardContent className="p-4 text-center">
              <Clock className="mx-auto mb-2 text-amber-500" size={24} />
              <p className="text-2xl font-bold text-amber-600">{summary.late}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'متأخر' : 'Late'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-blue-200">
            <CardContent className="p-4 text-center">
              <Calendar className="mx-auto mb-2 text-blue-500" size={24} />
              <p className="text-2xl font-bold text-blue-600">{summary.on_leave}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'إجازة' : 'Leave'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-gray-200">
            <CardContent className="p-4 text-center">
              <Calendar className="mx-auto mb-2 text-gray-500" size={24} />
              <p className="text-2xl font-bold text-gray-600">{summary.weekend + summary.holiday}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'عطلة' : 'Off'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-orange-200">
            <CardContent className="p-4 text-center">
              <AlertTriangle className="mx-auto mb-2 text-orange-500" size={24} />
              <p className="text-2xl font-bold text-orange-600">{summary.not_processed}</p>
              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'غير محلل' : 'Pending'}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Tabs: Attendance | Penalties */}
      <Tabs value={mainTab} onValueChange={setMainTab} className="w-full">
        <TabsList className="mb-4 w-full justify-start flex-wrap">
          <TabsTrigger value="attendance" className="flex-1 md:flex-none gap-2">
            <Clock size={16} />
            {lang === 'ar' ? 'الحضور' : 'Attendance'}
          </TabsTrigger>
          {/* تبويب التحضير اليدوي - للمشرفين فقط */}
          {isSupervisor && (
            <TabsTrigger value="manual-attendance" className="flex-1 md:flex-none gap-2">
              <HandMetal size={16} />
              {lang === 'ar' ? 'تحضير يدوي' : 'Manual Check-in'}
            </TabsTrigger>
          )}
          {/* تبويب العقوبات - للإدارة فقط، ليس للمشرفين */}
          {!isSupervisor && (
            <TabsTrigger value="penalties" className="flex-1 md:flex-none gap-2">
              <AlertTriangle size={16} />
              {lang === 'ar' ? 'العقوبات' : 'Penalties'}
            </TabsTrigger>
          )}
          {/* تبويب طلبات التعديل - sultan فقط */}
          {isSultan && (
            <TabsTrigger value="corrections-review" className="flex-1 md:flex-none gap-2">
              <Edit size={16} />
              {lang === 'ar' ? 'طلبات التعديل' : 'Correction Requests'}
              {pendingCorrections.length > 0 && (
                <span className="bg-amber-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {pendingCorrections.length}
                </span>
              )}
            </TabsTrigger>
          )}
          {/* تبويب مراجعة الخصومات - sultan/naif فقط */}
          {isSultan && (
            <TabsTrigger value="deductions-review" className="flex-1 md:flex-none gap-2">
              <FileWarning size={16} />
              {lang === 'ar' ? 'مراجعة الخصومات' : 'Review Deductions'}
              {pendingDeductions.length > 0 && (
                <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {pendingDeductions.length}
                </span>
              )}
            </TabsTrigger>
          )}
        </TabsList>

        {/* Attendance Tab Content */}
        <TabsContent value="attendance">
          {/* Sub Tabs */}
          <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="daily">{lang === 'ar' ? 'يومي' : 'Daily'}</TabsTrigger>
          <TabsTrigger value="weekly">{lang === 'ar' ? 'أسبوعي' : 'Weekly'}</TabsTrigger>
          <TabsTrigger value="monthly">{lang === 'ar' ? 'شهري' : 'Monthly'}</TabsTrigger>
          <TabsTrigger value="yearly">{lang === 'ar' ? 'سنوي' : 'Yearly'}</TabsTrigger>
        </TabsList>

        {/* Daily Tab */}
        <TabsContent value="daily">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">
                {lang === 'ar' ? 'سجل الحضور اليومي' : 'Daily Attendance'}
                {viewMode === 'single' && selectedEmployeeData && (
                  <span className="text-sm font-normal text-muted-foreground mr-2">
                    - {selectedEmployeeData.full_name_ar}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : (viewMode === 'all' ? dailyData : employeeRecord?.daily || []).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/30">
                        <th className="text-center p-3 w-12">#</th>
                        {viewMode === 'all' && <th className="text-start p-3">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>}
                        {viewMode === 'single' && <th className="text-start p-3">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>}
                        <th className="text-center p-3">{lang === 'ar' ? 'الموقع' : 'Location'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'الدخول' : 'In'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'الخروج' : 'Out'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'تأخير' : 'Late'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'إجراء' : 'Action'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(viewMode === 'all' ? dailyData : employeeRecord?.daily || []).map((emp, idx) => (
                        <tr key={emp.employee_id + '-' + (emp.date || idx)} className="border-b hover:bg-muted/50">
                          {/* Quick Check Icon */}
                          <td className="p-3 text-center">
                            {['PRESENT', 'LATE', 'ON_LEAVE', 'ON_MISSION', 'HOLIDAY', 'WEEKEND', 'PERMISSION'].includes(emp.final_status) ? (
                              <CheckCircle className="text-emerald-500 mx-auto" size={20} />
                            ) : emp.final_status === 'ABSENT' ? (
                              <XCircle className="text-red-500 mx-auto" size={20} />
                            ) : (
                              <AlertTriangle className="text-orange-400 mx-auto" size={18} />
                            )}
                          </td>
                          {viewMode === 'all' && (
                            <td className="p-3">
                              <div>
                                <p className="font-medium">{emp.employee_name_ar || emp.employee_name}</p>
                                <p className="text-xs text-muted-foreground">{emp.employee_number}</p>
                              </div>
                            </td>
                          )}
                          {viewMode === 'single' && (
                            <td className="p-3 font-mono text-sm">{emp.date}</td>
                          )}
                          {/* Work Location */}
                          <td className="p-3 text-center">
                            <span className="text-xs text-muted-foreground flex items-center justify-center gap-1">
                              <MapPin size={12} />
                              {emp.work_location_name_ar || emp.work_location_name || (lang === 'ar' ? 'المقر الرئيسي' : 'Main Office')}
                            </span>
                          </td>
                          <td className="p-3 text-center">
                            <Badge className={STATUS_COLORS[emp.final_status] || STATUS_COLORS.UNKNOWN}>
                              {STATUS_AR[emp.final_status] || emp.status_ar || emp.final_status}
                            </Badge>
                          </td>
                          <td className="p-3 text-center font-mono text-xs">
                            {formatTime(emp.check_in_time)}
                          </td>
                          <td className="p-3 text-center font-mono text-xs">
                            {formatTime(emp.check_out_time)}
                          </td>
                          <td className="p-3 text-center">
                            {emp.late_minutes > 0 && (
                              <span className="text-amber-600 font-medium">{emp.late_minutes} د</span>
                            )}
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {emp.can_edit && (
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className="h-8 w-8"
                                  onClick={() => handleEdit(emp)}
                                  title={lang === 'ar' ? 'تعديل' : 'Edit'}
                                >
                                  <Edit size={14} />
                                </Button>
                              )}
                              {emp.has_trace && (
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className="h-8 w-8"
                                  onClick={() => handleViewTrace(emp)}
                                  title={lang === 'ar' ? 'العروق' : 'Trace'}
                                >
                                  <Eye size={14} />
                                </Button>
                              )}
                            </div>
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

        {/* Weekly Tab */}
        <TabsContent value="weekly">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{lang === 'ar' ? 'ملخص الأسبوع' : 'Weekly Summary'}</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : (viewMode === 'all' ? weeklyData : employeeRecord?.weekly ? [employeeRecord.weekly] : []).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-start p-3">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'حضور' : 'Present'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'غياب' : 'Absent'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'تأخير' : 'Late'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'إجازة' : 'Leave'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'دقائق تأخير' : 'Late Min'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(viewMode === 'all' ? weeklyData : employeeRecord?.weekly ? [employeeRecord.weekly] : []).map((emp) => (
                        <tr key={emp.employee_id} className="border-b hover:bg-muted/50">
                          <td className="p-3">
                            <p className="font-medium">{emp.employee_name_ar}</p>
                            <p className="text-xs text-muted-foreground">{emp.employee_number}</p>
                          </td>
                          <td className="p-3 text-center">
                            <span className="text-emerald-600 font-bold">{emp.total_present}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className={emp.total_absent > 0 ? 'text-red-600 font-bold' : ''}>{emp.total_absent}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className={emp.total_late > 0 ? 'text-amber-600 font-bold' : ''}>{emp.total_late}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className="text-blue-600">{emp.total_leave}</span>
                          </td>
                          <td className="p-3 text-center">
                            {emp.total_late_minutes > 0 && (
                              <span className="text-amber-600">{emp.total_late_minutes} د</span>
                            )}
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

        {/* Monthly Tab */}
        <TabsContent value="monthly">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">{lang === 'ar' ? 'ملخص الشهر' : 'Monthly Summary'}</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : (viewMode === 'all' ? monthlyData : employeeRecord?.monthly ? [employeeRecord.monthly] : []).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-start p-3">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'حضور' : 'Present'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'غياب' : 'Absent'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'تأخير' : 'Late'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'دقائق تأخير' : 'Late Min'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'خصم متوقع' : 'Est. Deduction'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(viewMode === 'all' ? monthlyData : employeeRecord?.monthly ? [employeeRecord.monthly] : []).map((emp) => (
                        <tr key={emp.employee_id} className="border-b hover:bg-muted/50">
                          <td className="p-3">
                            <p className="font-medium">{emp.employee_name_ar}</p>
                            <p className="text-xs text-muted-foreground">{emp.employee_number}</p>
                          </td>
                          <td className="p-3 text-center">
                            <span className="text-emerald-600 font-bold">{emp.total_present}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className={emp.total_absent > 0 ? 'text-red-600 font-bold' : ''}>{emp.total_absent}</span>
                          </td>
                          <td className="p-3 text-center">
                            <span className={emp.total_late > 0 ? 'text-amber-600 font-bold' : ''}>{emp.total_late}</span>
                          </td>
                          <td className="p-3 text-center">
                            {emp.total_late_minutes > 0 && (
                              <span className="text-amber-600">{emp.total_late_minutes} د</span>
                            )}
                          </td>
                          <td className="p-3 text-center">
                            {emp.estimated_deduction > 0 && (
                              <span className="text-red-600 font-bold">
                                {emp.estimated_deduction.toFixed(2)} ر.س
                              </span>
                            )}
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

        {/* Yearly Tab */}
        <TabsContent value="yearly">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{lang === 'ar' ? 'ملخص السنة' : 'Yearly Summary'}</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <CalendarDays className="mx-auto mb-4 text-muted-foreground" size={48} />
                  <p>{lang === 'ar' ? 'الملخص السنوي قيد التطوير' : 'Yearly summary coming soon'}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
        </TabsContent>

        {/* Penalties Tab Content */}
        <TabsContent value="penalties">
          {/* Penalties Summary Cards */}
          {penaltiesReport?.summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <Card className="border-blue-200">
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold text-blue-600">{penaltiesReport.summary.total_employees}</p>
                  <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'موظف' : 'Employees'}</p>
                </CardContent>
              </Card>
              
              <Card className="border-red-200">
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold text-red-600">{penaltiesReport.summary.total_absent_days}</p>
                  <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'أيام غياب' : 'Absent Days'}</p>
                </CardContent>
              </Card>
              
              <Card className="border-amber-200">
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold text-amber-600">{penaltiesReport.summary.total_deficit_hours?.toFixed(1) || 0}</p>
                  <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'ساعات نقص' : 'Deficit Hours'}</p>
                </CardContent>
              </Card>
              
              <Card className="border-violet-200">
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold text-violet-600">
                    {penaltiesReport.summary.total_deduction_amount?.toFixed(0) || 0} ر.س
                  </p>
                  <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'إجمالي الخصم' : 'Total Deduction'}</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Rules Info */}
          <Card className="bg-amber-50 dark:bg-amber-900/10 border-amber-200 mb-6">
            <CardContent className="p-4">
              <h3 className="font-bold flex items-center gap-2 mb-3">
                <AlertTriangle className="text-amber-600" size={20} />
                {lang === 'ar' ? 'قواعد الخصم' : 'Deduction Rules'}
              </h3>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-medium text-amber-700">{lang === 'ar' ? 'الغياب:' : 'Absence:'}</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1 mr-2">
                    <li>{lang === 'ar' ? 'يوم غياب = خصم يوم' : '1 day absence = 1 day deduction'}</li>
                    <li>{lang === 'ar' ? '3 أيام متصلة = إنذار أول' : '3 consecutive = 1st warning'}</li>
                    <li>{lang === 'ar' ? '5 أيام متصلة = إنذار ثاني' : '5 consecutive = 2nd warning'}</li>
                    <li>{lang === 'ar' ? '10 أيام متصلة = إنذار نهائي' : '10 consecutive = Final warning'}</li>
                  </ul>
                </div>
                <div>
                  <p className="font-medium text-amber-700">{lang === 'ar' ? 'التأخير والخروج المبكر:' : 'Late & Early Leave:'}</p>
                  <ul className="list-disc list-inside text-muted-foreground space-y-1 mr-2">
                    <li>{lang === 'ar' ? 'يحسب بالدقائق' : 'Calculated in minutes'}</li>
                    <li>{lang === 'ar' ? 'يجمع شهرياً' : 'Accumulated monthly'}</li>
                    <li>{lang === 'ar' ? 'كل 8 ساعات نقص = خصم يوم' : 'Every 8 hours = 1 day deduction'}</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Employees Penalties List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{lang === 'ar' ? 'تفاصيل العقوبات' : 'Penalties Details'}</span>
                <Input
                  type="month"
                  value={month}
                  onChange={(e) => setMonth(e.target.value)}
                  className="w-auto"
                />
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : !penaltiesReport?.employees?.length ? (
                <div className="text-center py-8 text-muted-foreground">
                  {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                </div>
              ) : (
                <div className="space-y-3">
                  {penaltiesReport.employees.map((emp) => (
                    <div 
                      key={emp.employee_id}
                      className="border rounded-lg overflow-hidden"
                    >
                      {/* Employee Row */}
                      <div 
                        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50"
                        onClick={() => setExpandedPenaltyEmployee(expandedPenaltyEmployee === emp.employee_id ? null : emp.employee_id)}
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                            {emp.employee_name_ar?.[0] || '?'}
                          </div>
                          <div>
                            <p className="font-medium">{emp.employee_name_ar}</p>
                            <p className="text-xs text-muted-foreground">{emp.employee_id}</p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          {/* Absence */}
                          {emp.absence?.total_days > 0 && (
                            <Badge variant="destructive" className="text-xs">
                              <UserX size={12} className="mr-1" />
                              {emp.absence.total_days} {lang === 'ar' ? 'غياب' : 'absent'}
                            </Badge>
                          )}
                          
                          {/* Deficit */}
                          {emp.deficit?.total_deficit_hours > 0 && (
                            <Badge variant="outline" className="text-xs text-amber-600 border-amber-200">
                              <Clock size={12} className="mr-1" />
                              {emp.deficit.total_deficit_hours} {lang === 'ar' ? 'ساعة' : 'hrs'}
                            </Badge>
                          )}
                          
                          {/* Total Deduction */}
                          {emp.total_deduction_days > 0 && (
                            <Badge className="bg-violet-100 text-violet-700 text-xs">
                              <TrendingDown size={12} className="mr-1" />
                              {emp.total_deduction_days} {lang === 'ar' ? 'يوم خصم' : 'days'}
                            </Badge>
                          )}
                          
                          {/* Warnings */}
                          {emp.absence?.warnings?.length > 0 && (
                            <Badge variant="destructive" className="text-xs">
                              <AlertTriangle size={12} className="mr-1" />
                              {emp.absence.warnings[0].name_ar}
                            </Badge>
                          )}
                          
                          {expandedPenaltyEmployee === emp.employee_id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                        </div>
                      </div>
                      
                      {/* Expanded Details */}
                      {expandedPenaltyEmployee === emp.employee_id && (
                        <div className="p-4 pt-0 border-t bg-muted/30">
                          <div className="grid md:grid-cols-2 gap-4 mt-4">
                            {/* Absence Details */}
                            <div className="p-3 bg-red-50 dark:bg-red-900/10 rounded-lg">
                              <h4 className="font-medium text-red-700 mb-2 flex items-center gap-2">
                                <UserX size={16} />
                                {lang === 'ar' ? 'الغياب' : 'Absence'}
                              </h4>
                              <div className="text-sm space-y-1">
                                <p>{lang === 'ar' ? 'إجمالي أيام الغياب:' : 'Total absent days:'} <strong>{emp.absence?.total_days || 0}</strong></p>
                                <p>{lang === 'ar' ? 'خصم:' : 'Deduction:'} <strong>{emp.absence?.deduction_days || 0} {lang === 'ar' ? 'يوم' : 'days'}</strong></p>
                              </div>
                            </div>
                            
                            {/* Deficit Details */}
                            <div className="p-3 bg-amber-50 dark:bg-amber-900/10 rounded-lg">
                              <h4 className="font-medium text-amber-700 mb-2 flex items-center gap-2">
                                <Clock size={16} />
                                {lang === 'ar' ? 'نقص الساعات' : 'Hours Deficit'}
                              </h4>
                              <div className="text-sm space-y-1">
                                <p>{lang === 'ar' ? 'دقائق التأخير:' : 'Late minutes:'} <strong>{emp.deficit?.total_late_minutes || 0}</strong></p>
                                <p>{lang === 'ar' ? 'دقائق الخروج المبكر:' : 'Early leave:'} <strong>{emp.deficit?.total_early_leave_minutes || 0}</strong></p>
                                <p>{lang === 'ar' ? 'إجمالي النقص:' : 'Total deficit:'} <strong>{emp.deficit?.total_deficit_hours || 0} {lang === 'ar' ? 'ساعة' : 'hours'}</strong></p>
                                <p>{lang === 'ar' ? 'خصم:' : 'Deduction:'} <strong>{emp.deficit?.deduction_days || 0} {lang === 'ar' ? 'يوم' : 'days'}</strong></p>
                              </div>
                            </div>
                          </div>
                          
                          {/* Summary */}
                          <div className="mt-4 p-3 bg-violet-50 dark:bg-violet-900/10 rounded-lg">
                            <div className="flex justify-between items-center">
                              <div>
                                <p className="font-medium">{lang === 'ar' ? 'إجمالي الخصم:' : 'Total Deduction:'}</p>
                                <p className="text-2xl font-bold text-violet-700">
                                  {emp.total_deduction_days} {lang === 'ar' ? 'يوم' : 'days'}
                                </p>
                              </div>
                              {emp.total_deduction_amount > 0 && (
                                <div className="text-left">
                                  <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'المبلغ:' : 'Amount:'}</p>
                                  <p className="text-xl font-bold text-violet-700">
                                    {emp.total_deduction_amount?.toFixed(2) || 0} ر.س
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Corrections Review Tab - Sultan only */}
        {isSultan && (
          <TabsContent value="corrections-review">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Edit size={20} className="text-amber-500" />
                  {lang === 'ar' ? 'طلبات تعديل الحضور من المشرفين' : 'Attendance Correction Requests from Supervisors'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {pendingCorrections.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <CheckCircle size={40} className="mx-auto mb-3 text-emerald-500" />
                    <p>{lang === 'ar' ? 'لا توجد طلبات تعديل معلقة' : 'No pending correction requests'}</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {pendingCorrections.map((req) => (
                      <div key={req.id} className="p-4 border rounded-xl bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-800">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <User size={16} className="text-muted-foreground" />
                              <span className="font-semibold">{req.employee_name_ar}</span>
                              <Badge variant="outline">{req.date}</Badge>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4 mb-3 text-sm">
                              <div>
                                <span className="text-muted-foreground">{lang === 'ar' ? 'الحالة الأصلية:' : 'Original:'}</span>
                                <Badge className={STATUS_COLORS[req.original_status] + ' ms-2'}>
                                  {STATUS_AR[req.original_status] || req.original_status}
                                </Badge>
                              </div>
                              <div>
                                <span className="text-muted-foreground">{lang === 'ar' ? 'المطلوبة:' : 'Requested:'}</span>
                                <Badge className={STATUS_COLORS[req.requested_status] + ' ms-2'}>
                                  {STATUS_AR[req.requested_status] || req.requested_status}
                                </Badge>
                              </div>
                            </div>
                            
                            <p className="text-sm mb-2">
                              <span className="text-muted-foreground">{lang === 'ar' ? 'السبب:' : 'Reason:'}</span>
                              <span className="ms-2">{req.reason}</span>
                            </p>
                            
                            <p className="text-xs text-muted-foreground">
                              {lang === 'ar' ? 'المشرف:' : 'Supervisor:'} {req.supervisor_name_ar}
                            </p>
                          </div>
                          
                          <div className="flex flex-col gap-2">
                            <Button 
                              size="sm" 
                              className="bg-emerald-600 hover:bg-emerald-700"
                              onClick={() => handleCorrectionDecision(req.id, 'approve')}
                              disabled={loading}
                            >
                              <CheckCircle size={14} className="me-1" />
                              {lang === 'ar' ? 'موافقة' : 'Approve'}
                            </Button>
                            <Button 
                              size="sm" 
                              variant="destructive"
                              onClick={() => handleCorrectionDecision(req.id, 'reject')}
                              disabled={loading}
                            >
                              <XCircle size={14} className="me-1" />
                              {lang === 'ar' ? 'رفض' : 'Reject'}
                            </Button>
                            <Button 
                              size="sm" 
                              variant="outline"
                              onClick={() => setCorrectionDecision(req)}
                              disabled={loading}
                            >
                              <Edit size={14} className="me-1" />
                              {lang === 'ar' ? 'تعديل' : 'Modify'}
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Deductions Review Tab - Sultan/Naif only */}
        {isSultan && (
          <TabsContent value="deductions-review">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileWarning size={20} className="text-orange-500" />
                  {lang === 'ar' ? 'مراجعة الخصومات المقترحة' : 'Review Deduction Proposals'}
                  <span className="text-sm font-normal text-muted-foreground">
                    ({pendingDeductions.length} {lang === 'ar' ? 'بانتظار المراجعة' : 'pending'})
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {pendingDeductions.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    <CheckCircle size={48} className="mx-auto mb-3 text-green-500" />
                    <p className="text-lg font-medium">{lang === 'ar' ? 'لا توجد خصومات معلقة' : 'No pending deductions'}</p>
                    <p className="text-sm">{lang === 'ar' ? 'تمت مراجعة جميع الخصومات' : 'All deductions have been reviewed'}</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Deductions List */}
                    <div className="space-y-3">
                      <h3 className="font-semibold text-sm text-muted-foreground uppercase">
                        {lang === 'ar' ? 'قائمة الخصومات المعلقة' : 'Pending Deductions'}
                      </h3>
                      <div className="space-y-2 max-h-[500px] overflow-y-auto">
                        {pendingDeductions.map(d => (
                          <button
                            key={d.id}
                            onClick={() => loadDeductionTrace(d)}
                            className={`w-full text-right p-4 rounded-lg border transition-all ${
                              selectedDeduction?.id === d.id 
                                ? 'border-orange-500 bg-orange-50' 
                                : 'border-border hover:border-orange-300 hover:bg-orange-50/50'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded">
                                {d.deduction_type_ar || d.deduction_type}
                              </span>
                              <span className="font-bold text-red-600">{d.amount?.toFixed(2)} ر.س</span>
                            </div>
                            <p className="font-medium">{d.employee_name || d.employee_name_ar}</p>
                            <p className="text-xs text-muted-foreground mt-1">{d.period_start}</p>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Selected Deduction Details */}
                    <div>
                      {selectedDeduction ? (
                        <div className="p-4 bg-slate-50 rounded-lg border space-y-4">
                          <h3 className="font-semibold flex items-center gap-2">
                            <Eye size={18} />
                            {lang === 'ar' ? 'تفاصيل الخصم' : 'Deduction Details'}
                          </h3>

                          {/* Basic Info */}
                          <div className="grid grid-cols-2 gap-3">
                            <div className="p-3 bg-white rounded border">
                              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الموظف' : 'Employee'}</p>
                              <p className="font-medium">{selectedDeduction.employee_name || selectedDeduction.employee_name_ar}</p>
                            </div>
                            <div className="p-3 bg-white rounded border">
                              <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'المبلغ' : 'Amount'}</p>
                              <p className="font-bold text-red-600 text-lg">{selectedDeduction.amount?.toFixed(2)} ر.س</p>
                            </div>
                          </div>

                          {/* Reason */}
                          <div className="p-3 bg-red-50 rounded border border-red-200">
                            <p className="text-xs font-semibold text-red-700 mb-1">{lang === 'ar' ? 'السبب' : 'Reason'}</p>
                            <p className="text-sm">{selectedDeduction.reason_ar || selectedDeduction.reason}</p>
                          </div>

                          {/* Trace Log */}
                          <div className="border rounded-lg overflow-hidden">
                            <button
                              onClick={() => setExpandedDeduction(expandedDeduction === selectedDeduction.id ? null : selectedDeduction.id)}
                              className="w-full p-3 bg-violet-50 flex items-center justify-between hover:bg-violet-100"
                            >
                              <span className="font-semibold text-violet-700 flex items-center gap-2">
                                <Eye size={16} />
                                {lang === 'ar' ? 'العروق - سجل الفحوصات' : 'Trace Log'}
                                {deductionTrace.length > 0 && <span className="text-xs">({deductionTrace.length})</span>}
                              </span>
                              {expandedDeduction === selectedDeduction.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                            
                            {expandedDeduction === selectedDeduction.id && (
                              <div className="p-3 space-y-2 max-h-[200px] overflow-y-auto">
                                {loadingTrace ? (
                                  <div className="flex justify-center py-4"><Loader2 className="animate-spin" /></div>
                                ) : deductionTrace.length === 0 ? (
                                  <p className="text-sm text-center text-muted-foreground py-4">
                                    {lang === 'ar' ? 'لا يوجد سجل' : 'No trace log'}
                                  </p>
                                ) : (
                                  deductionTrace.map((check, i) => (
                                    <div key={i} className={`p-2 rounded text-sm ${check.found ? 'bg-green-50' : 'bg-slate-100'}`}>
                                      <div className="flex items-center justify-between">
                                        <span className="flex items-center gap-1">
                                          {check.found ? <CheckCircle size={12} className="text-green-600" /> : <XCircle size={12} className="text-slate-400" />}
                                          {check.step_ar || check.step}
                                        </span>
                                        <span className={`text-xs ${check.found ? 'text-green-600' : 'text-slate-500'}`}>
                                          {check.found ? (lang === 'ar' ? 'وُجد' : 'Found') : (lang === 'ar' ? 'لم يُوجد' : 'Not found')}
                                        </span>
                                      </div>
                                    </div>
                                  ))
                                )}
                              </div>
                            )}
                          </div>

                          {/* Review Actions */}
                          <div className="space-y-3 pt-3 border-t">
                            <Input
                              value={reviewNote}
                              onChange={(e) => setReviewNote(e.target.value)}
                              placeholder={lang === 'ar' ? 'ملاحظة (اختياري)...' : 'Note (optional)...'}
                            />
                            <div className="flex gap-3">
                              <Button
                                onClick={() => handleReviewDeduction(selectedDeduction.id, true)}
                                disabled={reviewingDeduction}
                                className="flex-1 bg-green-600 hover:bg-green-700"
                              >
                                {reviewingDeduction ? <Loader2 className="animate-spin mr-2" size={16} /> : <CheckCircle size={16} className="mr-2" />}
                                {lang === 'ar' ? 'موافقة' : 'Approve'}
                              </Button>
                              <Button
                                onClick={() => handleReviewDeduction(selectedDeduction.id, false)}
                                disabled={reviewingDeduction}
                                variant="destructive"
                                className="flex-1"
                              >
                                {reviewingDeduction ? <Loader2 className="animate-spin mr-2" size={16} /> : <XCircle size={16} className="mr-2" />}
                                {lang === 'ar' ? 'رفض' : 'Reject'}
                              </Button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center h-64 border-2 border-dashed rounded-lg">
                          <div className="text-center text-muted-foreground">
                            <FileWarning size={48} className="mx-auto mb-3 opacity-30" />
                            <p>{lang === 'ar' ? 'اختر خصم للمراجعة' : 'Select a deduction to review'}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* Edit Dialog */}
      <Dialog open={!!editDialog} onOpenChange={() => setEditDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {lang === 'ar' ? 'تعديل حالة الموظف' : 'Update Employee Status'}
            </DialogTitle>
          </DialogHeader>
          
          {editDialog && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">{editDialog.employee_name_ar}</p>
                <p className="text-sm text-muted-foreground">{editDialog.date}</p>
                <Badge className={STATUS_COLORS[editDialog.final_status] + ' mt-2'}>
                  {lang === 'ar' ? 'الحالة الحالية:' : 'Current:'} {STATUS_AR[editDialog.final_status] || editDialog.status_ar}
                </Badge>
              </div>
              
              <div>
                <label className="text-sm font-medium">
                  {lang === 'ar' ? 'الحالة الجديدة' : 'New Status'}
                </label>
                <select
                  className="w-full mt-1 p-2 border rounded-lg bg-background"
                  value={editForm.new_status}
                  onChange={(e) => setEditForm({...editForm, new_status: e.target.value})}
                >
                  <option value="PRESENT">{lang === 'ar' ? 'حاضر' : 'Present'}</option>
                  <option value="ABSENT">{lang === 'ar' ? 'غائب' : 'Absent'}</option>
                  <option value="LATE">{lang === 'ar' ? 'متأخر' : 'Late'}</option>
                  <option value="EXCUSED">{lang === 'ar' ? 'معذور' : 'Excused'}</option>
                  <option value="ON_MISSION">{lang === 'ar' ? 'مهمة خارجية' : 'On Mission'}</option>
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">
                    {lang === 'ar' ? 'وقت الدخول' : 'Check In'}
                  </label>
                  <Input
                    type="time"
                    value={editForm.check_in_time}
                    onChange={(e) => setEditForm({...editForm, check_in_time: e.target.value})}
                    className="mt-1"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">
                    {lang === 'ar' ? 'وقت الخروج' : 'Check Out'}
                  </label>
                  <Input
                    type="time"
                    value={editForm.check_out_time}
                    onChange={(e) => setEditForm({...editForm, check_out_time: e.target.value})}
                    className="mt-1"
                  />
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium">
                  {lang === 'ar' ? 'السبب (مطلوب)' : 'Reason (required)'}
                </label>
                <Input
                  value={editForm.reason}
                  onChange={(e) => setEditForm({...editForm, reason: e.target.value})}
                  placeholder={lang === 'ar' ? 'أدخل سبب التعديل...' : 'Enter reason...'}
                  className="mt-1"
                />
              </div>
              
              {/* إقرار المشرف - يظهر للمشرف فقط */}
              {isSupervisor && (
                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id="supervisor_ack"
                      checked={editForm.supervisor_acknowledgment}
                      onChange={(e) => setEditForm({...editForm, supervisor_acknowledgment: e.target.checked})}
                      className="mt-1 w-5 h-5 rounded border-amber-400"
                    />
                    <label htmlFor="supervisor_ack" className="text-sm text-amber-800 dark:text-amber-200">
                      <span className="font-semibold block mb-1">
                        {lang === 'ar' ? 'إقرار تحمل المسؤولية' : 'Responsibility Acknowledgment'}
                      </span>
                      {lang === 'ar' 
                        ? `عزيزي ${user?.full_name_ar || user?.full_name || 'المشرف'}، تعديلك للحالة يعني تحملك لمسؤوليتها. طلبك سيُرسل لسلطان للموافقة.`
                        : `Dear ${user?.full_name || 'Supervisor'}, modifying this status means you take responsibility. Your request will be sent to Sultan for approval.`
                      }
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog(null)}>
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button onClick={handleSaveEdit} disabled={loading}>
              {loading ? <RefreshCw className="animate-spin" size={16} /> : (
                isSupervisor 
                  ? (lang === 'ar' ? 'إرسال للموافقة' : 'Send for Approval')
                  : (lang === 'ar' ? 'حفظ' : 'Save')
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Trace Dialog */}
      <Dialog open={!!traceDialog} onOpenChange={() => setTraceDialog(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {lang === 'ar' ? 'العروق (Trace Evidence)' : 'Trace Evidence'}
            </DialogTitle>
          </DialogHeader>
          
          {traceData && (
            <div className="space-y-4 py-4">
              {/* Summary */}
              <div className="p-4 bg-muted rounded-lg">
                <p className="font-medium text-lg">{STATUS_AR[traceData.final_status] || traceData.status_ar || traceData.final_status}</p>
                <p className="text-sm text-muted-foreground mt-1">{traceData.decision_reason_ar}</p>
              </div>
              
              {/* Trace Summary */}
              {traceData.trace_summary && (
                <div className="p-4 bg-violet-50 dark:bg-violet-900/20 rounded-lg border border-violet-200 dark:border-violet-800">
                  <p className="font-medium text-violet-700 dark:text-violet-300 mb-2">
                    {lang === 'ar' ? 'ملخص الفحص' : 'Check Summary'}
                  </p>
                  <p className="text-sm">{traceData.trace_summary.conclusion_ar}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    {lang === 'ar' ? `تم فحص ${traceData.trace_summary.steps_checked} خطوات` : `${traceData.trace_summary.steps_checked} steps checked`}
                  </p>
                </div>
              )}
              
              {/* Trace Log */}
              {traceData.trace_log && (
                <div className="space-y-2">
                  <p className="font-medium">{lang === 'ar' ? 'تفاصيل الفحص:' : 'Check Details:'}</p>
                  {traceData.trace_log.map((step, idx) => (
                    <div 
                      key={idx}
                      className={`p-3 rounded-lg border ${
                        step.found 
                          ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200' 
                          : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {step.order}. {step.step_ar}
                        </span>
                        <Badge variant={step.found ? 'default' : 'secondary'}>
                          {step.found ? (lang === 'ar' ? 'موجود' : 'Found') : (lang === 'ar' ? 'لا يوجد' : 'Not Found')}
                        </Badge>
                      </div>
                      {step.details && Object.keys(step.details).length > 0 && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {JSON.stringify(step.details).slice(0, 100)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Correction Decision Dialog - لتعديل القرار */}
      <Dialog open={!!correctionDecision} onOpenChange={() => setCorrectionDecision(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {lang === 'ar' ? 'تعديل القرار' : 'Modify Decision'}
            </DialogTitle>
          </DialogHeader>
          
          {correctionDecision && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">{correctionDecision.employee_name_ar}</p>
                <p className="text-sm text-muted-foreground">{correctionDecision.date}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium">
                  {lang === 'ar' ? 'الحالة النهائية' : 'Final Status'}
                </label>
                <select
                  className="w-full mt-1 p-2 border rounded-lg bg-background"
                  id="final_status_select"
                  defaultValue={correctionDecision.requested_status}
                >
                  <option value="PRESENT">{lang === 'ar' ? 'حاضر' : 'Present'}</option>
                  <option value="ABSENT">{lang === 'ar' ? 'غائب' : 'Absent'}</option>
                  <option value="LATE">{lang === 'ar' ? 'متأخر' : 'Late'}</option>
                  <option value="EXCUSED">{lang === 'ar' ? 'معذور' : 'Excused'}</option>
                  <option value="ON_MISSION">{lang === 'ar' ? 'مهمة خارجية' : 'On Mission'}</option>
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium">
                  {lang === 'ar' ? 'ملاحظة (اختياري)' : 'Note (optional)'}
                </label>
                <Input
                  id="decision_note_input"
                  placeholder={lang === 'ar' ? 'ملاحظة على القرار...' : 'Decision note...'}
                  className="mt-1"
                />
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setCorrectionDecision(null)}>
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button 
              onClick={() => {
                const finalStatus = document.getElementById('final_status_select')?.value;
                const note = document.getElementById('decision_note_input')?.value;
                handleCorrectionDecision(correctionDecision.id, 'modify', finalStatus, note);
              }}
              disabled={loading}
            >
              {loading ? <RefreshCw className="animate-spin" size={16} /> : (lang === 'ar' ? 'تأكيد التعديل' : 'Confirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
