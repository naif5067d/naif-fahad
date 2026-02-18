/**
 * Team Attendance Page - حضور الفريق
 * 
 * لسلطان ونايف:
 * - قائمة منسدلة لاختيار الموظف
 * - عرض سجل الموظف (يومي/أسبوعي/شهري/سنوي)
 * - تعديل حالة الموظف
 */
import { useState, useEffect, useMemo } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
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
  Search,
  User,
  CalendarDays,
  TrendingDown,
  FileWarning
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

const STATUS_COLORS = {
  'PRESENT': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'ABSENT': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  'LATE': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  'ON_LEAVE': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'ON_ADMIN_LEAVE': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  'WEEKEND': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  'HOLIDAY': 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  'ON_MISSION': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  'UNKNOWN': 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  'NOT_PROCESSED': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
};

const STATUS_ICONS = {
  'PRESENT': CheckCircle,
  'ABSENT': XCircle,
  'LATE': Clock,
  'ON_LEAVE': Calendar,
  'WEEKEND': Calendar,
  'HOLIDAY': Calendar,
  'UNKNOWN': AlertTriangle
};

export default function TeamAttendancePage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [tab, setTab] = useState('daily');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [summary, setSummary] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [weeklyData, setWeeklyData] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Edit Dialog
  const [editDialog, setEditDialog] = useState(null);
  const [editForm, setEditForm] = useState({
    new_status: 'PRESENT',
    reason: '',
    check_in_time: '08:00',
    check_out_time: '17:00'
  });
  
  // Trace Dialog
  const [traceDialog, setTraceDialog] = useState(null);
  const [traceData, setTraceData] = useState(null);

  useEffect(() => {
    fetchData();
  }, [tab, date, month]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch summary
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

  const handleEdit = (employee) => {
    setEditDialog(employee);
    setEditForm({
      new_status: employee.final_status === 'ABSENT' ? 'PRESENT' : employee.final_status,
      reason: '',
      check_in_time: employee.check_in_time?.slice(11, 16) || '08:00',
      check_out_time: employee.check_out_time?.slice(11, 16) || '17:00'
    });
  };

  const handleSaveEdit = async () => {
    if (!editForm.reason) {
      toast.error(lang === 'ar' ? 'يرجى إدخال السبب' : 'Please enter reason');
      return;
    }
    
    try {
      setLoading(true);
      await api.post(`/api/team-attendance/${editDialog.employee_id}/update-status?date=${editDialog.date}`, editForm);
      toast.success(lang === 'ar' ? 'تم تحديث الحالة بنجاح' : 'Status updated successfully');
      setEditDialog(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error updating status');
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

  const filteredDaily = dailyData.filter(e => 
    !searchQuery || 
    e.employee_name_ar?.includes(searchQuery) ||
    e.employee_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.employee_number?.includes(searchQuery)
  );

  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    return timestamp.slice(11, 16);
  };

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="team-attendance-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="text-primary" />
            {lang === 'ar' ? 'حضور الفريق' : 'Team Attendance'}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {lang === 'ar' ? 'متابعة حضور الموظفين وتعديل الحالات' : 'Track employee attendance and modify status'}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-auto"
          />
          <Button variant="outline" size="icon" onClick={fetchData} disabled={loading}>
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
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

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="daily">{lang === 'ar' ? 'يومي' : 'Daily'}</TabsTrigger>
          <TabsTrigger value="weekly">{lang === 'ar' ? 'أسبوعي' : 'Weekly'}</TabsTrigger>
          <TabsTrigger value="monthly">{lang === 'ar' ? 'شهري' : 'Monthly'}</TabsTrigger>
        </TabsList>

        {/* Daily Tab */}
        <TabsContent value="daily">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{lang === 'ar' ? 'سجل الحضور اليومي' : 'Daily Attendance'}</CardTitle>
                <div className="relative">
                  <Search className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                  <Input
                    placeholder={lang === 'ar' ? 'بحث...' : 'Search...'}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-48 pr-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : filteredDaily.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-start p-3">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'الدخول' : 'In'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'الخروج' : 'Out'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'تأخير' : 'Late'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'السبب' : 'Reason'}</th>
                        <th className="text-center p-3">{lang === 'ar' ? 'إجراء' : 'Action'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDaily.map((emp, idx) => (
                        <tr key={emp.employee_id} className="border-b hover:bg-muted/50">
                          <td className="p-3">
                            <div>
                              <p className="font-medium">{emp.employee_name_ar || emp.employee_name}</p>
                              <p className="text-xs text-muted-foreground">{emp.employee_number}</p>
                            </div>
                          </td>
                          <td className="p-3 text-center">
                            <Badge className={STATUS_COLORS[emp.final_status] || STATUS_COLORS.UNKNOWN}>
                              {emp.status_ar || emp.final_status}
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
                          <td className="p-3 text-center text-xs text-muted-foreground max-w-[150px] truncate" title={emp.decision_reason_ar}>
                            {emp.decision_reason_ar?.slice(0, 30) || '-'}
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
              ) : weeklyData.length === 0 ? (
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
                      {weeklyData.map((emp) => (
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
              <Input
                type="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                className="w-auto"
              />
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="animate-spin text-primary" size={32} />
                </div>
              ) : monthlyData.length === 0 ? (
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
                      {monthlyData.map((emp) => (
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
                  {lang === 'ar' ? 'الحالة الحالية:' : 'Current:'} {editDialog.status_ar}
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
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog(null)}>
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button onClick={handleSaveEdit} disabled={loading}>
              {loading ? <RefreshCw className="animate-spin" size={16} /> : (lang === 'ar' ? 'حفظ' : 'Save')}
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
                <p className="font-medium text-lg">{traceData.status_ar || traceData.final_status}</p>
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
    </div>
  );
}
