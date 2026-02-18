import { useState, useEffect, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  User, Calendar, Briefcase, Building2, Clock, CreditCard, 
  FileText, AlertTriangle, CheckCircle2, Phone, Mail, 
  ArrowLeft, ChevronRight, CalendarDays, DollarSign, 
  RefreshCw, Award, Timer, UserCheck, Camera, Upload
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function EmployeeProfilePage() {
  const { employeeId } = useParams();
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [employee, setEmployee] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [carryoverDialog, setCarryoverDialog] = useState(false);
  const [carryoverDays, setCarryoverDays] = useState('');
  const [carryoverNote, setCarryoverNote] = useState('');
  const [savingCarryover, setSavingCarryover] = useState(false);

  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);

  useEffect(() => {
    if (employeeId) {
      loadEmployeeData();
    }
  }, [employeeId]);

  const loadEmployeeData = async () => {
    setLoading(true);
    try {
      const [empRes, summaryRes] = await Promise.all([
        api.get(`/api/employees/${employeeId}`),
        api.get(`/api/employees/${employeeId}/summary`)
      ]);
      setEmployee(empRes.data);
      setSummary(summaryRes.data);
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل في تحميل بيانات الموظف' : 'Failed to load employee data');
    } finally {
      setLoading(false);
    }
  };

  const handleCarryover = async () => {
    if (!carryoverDays || parseFloat(carryoverDays) <= 0) {
      toast.error(lang === 'ar' ? 'أدخل عدد أيام صحيح' : 'Enter valid days');
      return;
    }
    
    setSavingCarryover(true);
    try {
      await api.post('/api/notifications/leave-carryover', {
        employee_id: employeeId,
        days_to_carryover: parseFloat(carryoverDays),
        note: carryoverNote
      });
      toast.success(lang === 'ar' ? 'تم ترحيل الإجازات بنجاح' : 'Leave carried over successfully');
      setCarryoverDialog(false);
      setCarryoverDays('');
      setCarryoverNote('');
      loadEmployeeData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setSavingCarryover(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-12">
        <User size={48} className="mx-auto mb-4 text-muted-foreground opacity-50" />
        <p className="text-muted-foreground">{lang === 'ar' ? 'الموظف غير موجود' : 'Employee not found'}</p>
        <Button variant="outline" onClick={() => navigate('/employees')} className="mt-4">
          <ArrowLeft size={16} className="me-2 rtl:rotate-180" />
          {lang === 'ar' ? 'العودة للموظفين' : 'Back to Employees'}
        </Button>
      </div>
    );
  }

  const contract = summary?.contract;
  const leaveDetails = summary?.leave_details;
  const serviceInfo = summary?.service_info;
  const attendance = summary?.attendance;

  return (
    <div className="space-y-6" data-testid="employee-profile-page">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/employees')}>
          <ArrowLeft size={18} className="rtl:rotate-180" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{lang === 'ar' ? 'ملف الموظف' : 'Employee Profile'}</h1>
          <p className="text-sm text-muted-foreground">{employee.employee_number}</p>
        </div>
      </div>

      {/* Employee Card - Hero Section */}
      <div className="gradient-hero rounded-2xl p-6 text-white">
        <div className="flex items-start gap-4">
          <div className="w-20 h-20 rounded-2xl bg-white/20 flex items-center justify-center text-3xl font-bold">
            {(lang === 'ar' ? employee.full_name_ar : employee.full_name)?.[0] || 'U'}
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold mb-1">
              {lang === 'ar' ? (employee.full_name_ar || employee.full_name) : employee.full_name}
            </h2>
            <p className="text-white/80">{lang === 'ar' ? contract?.job_title_ar : contract?.job_title}</p>
            <p className="text-white/60 text-sm mt-1">
              {lang === 'ar' ? contract?.department_ar : contract?.department}
            </p>
            
            {/* Quick stats in hero */}
            <div className="flex flex-wrap gap-4 mt-4">
              <div className="bg-white/10 rounded-lg px-3 py-2">
                <p className="text-xs text-white/60">{lang === 'ar' ? 'مدة الخدمة' : 'Service'}</p>
                <p className="text-lg font-bold">
                  {serviceInfo?.years_display || '0'} {lang === 'ar' ? 'سنة' : 'yr'}
                </p>
              </div>
              <div className="bg-white/10 rounded-lg px-3 py-2">
                <p className="text-xs text-white/60">{lang === 'ar' ? 'رصيد الإجازة' : 'Leave'}</p>
                <p className="text-lg font-bold">
                  {leaveDetails?.balance || 0} {lang === 'ar' ? 'يوم' : 'days'}
                </p>
              </div>
              <div className="bg-white/10 rounded-lg px-3 py-2">
                <p className="text-xs text-white/60">{lang === 'ar' ? 'الحالة' : 'Status'}</p>
                <p className="text-lg font-bold flex items-center gap-1">
                  {employee.is_active ? (
                    <><CheckCircle2 size={16} /> {lang === 'ar' ? 'نشط' : 'Active'}</>
                  ) : (
                    <><AlertTriangle size={16} /> {lang === 'ar' ? 'غير نشط' : 'Inactive'}</>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Info Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        
        {/* Personal Info Card */}
        <div className="card-premium p-5 space-y-4">
          <div className="flex items-center gap-2 text-primary font-semibold">
            <User size={18} />
            <span>{lang === 'ar' ? 'المعلومات الشخصية' : 'Personal Info'}</span>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-3">
              <Mail size={16} className="text-muted-foreground" />
              <span>{employee.email || '-'}</span>
            </div>
            <div className="flex items-center gap-3">
              <Phone size={16} className="text-muted-foreground" />
              <span>{employee.phone || '-'}</span>
            </div>
            <div className="flex items-center gap-3">
              <CreditCard size={16} className="text-muted-foreground" />
              <span>{employee.national_id || '-'}</span>
            </div>
          </div>
        </div>

        {/* Contract Info Card */}
        {contract && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <FileText size={18} />
              <span>{lang === 'ar' ? 'معلومات العقد' : 'Contract Info'}</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'رقم العقد' : 'Contract #'}</span>
                <span className="font-mono">{contract.contract_serial}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'تاريخ البدء' : 'Start Date'}</span>
                <span>{contract.start_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'تاريخ الانتهاء' : 'End Date'}</span>
                <span>{contract.end_date || (lang === 'ar' ? 'غير محدد' : 'Unlimited')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'الحالة' : 'Status'}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  contract.status === 'active' ? 'bg-green-100 text-green-700' : 
                  contract.status === 'terminated' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  {lang === 'ar' ? (
                    contract.status === 'active' ? 'نشط' : 
                    contract.status === 'terminated' ? 'منتهي' : contract.status
                  ) : contract.status}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Service Info Card */}
        {serviceInfo && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <Award size={18} />
              <span>{lang === 'ar' ? 'معلومات الخدمة' : 'Service Info'}</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'مدة الخدمة' : 'Duration'}</span>
                <span>{serviceInfo.years_display || '0'} {lang === 'ar' ? 'سنة' : 'years'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'الأيام' : 'Days'}</span>
                <span>{serviceInfo.total_days || 0}</span>
              </div>
              {serviceInfo.eos_amount && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{lang === 'ar' ? 'مكافأة نهاية الخدمة' : 'EOS'}</span>
                  <span className="font-bold text-green-600">
                    {serviceInfo.eos_amount?.toLocaleString()} {lang === 'ar' ? 'ريال' : 'SAR'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Leave Balance Card */}
        {leaveDetails && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-primary font-semibold">
                <CalendarDays size={18} />
                <span>{lang === 'ar' ? 'رصيد الإجازات' : 'Leave Balance'}</span>
              </div>
              {isAdmin && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setCarryoverDialog(true)}
                  data-testid="carryover-btn"
                >
                  <RefreshCw size={14} className="me-1" />
                  {lang === 'ar' ? 'ترحيل' : 'Carryover'}
                </Button>
              )}
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'الرصيد الحالي' : 'Current'}</span>
                <span className="text-xl font-bold text-primary">{leaveDetails.balance} {lang === 'ar' ? 'يوم' : 'days'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'الاستحقاق' : 'Entitlement'}</span>
                <span>{leaveDetails.entitlement} {lang === 'ar' ? 'يوم/سنة' : 'days/year'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'المكتسب' : 'Earned'}</span>
                <span>{leaveDetails.earned_to_date} {lang === 'ar' ? 'يوم' : 'days'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'المستخدم' : 'Used'}</span>
                <span>{leaveDetails.used} {lang === 'ar' ? 'يوم' : 'days'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Attendance Card */}
        {attendance && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <Clock size={18} />
              <span>{lang === 'ar' ? 'الحضور' : 'Attendance'}</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'حالة اليوم' : 'Today'}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  attendance.today_status === 'present' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  {lang === 'ar' ? attendance.today_status_ar : attendance.today_status}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Salary Card (Admin only) */}
        {isAdmin && contract && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <DollarSign size={18} />
              <span>{lang === 'ar' ? 'الراتب والبدلات' : 'Salary & Allowances'}</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'الأساسي' : 'Basic'}</span>
                <span>{contract.basic_salary?.toLocaleString()} {lang === 'ar' ? 'ريال' : 'SAR'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'بدل السكن' : 'Housing'}</span>
                <span>{contract.housing_allowance?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'بدل النقل' : 'Transport'}</span>
                <span>{contract.transport_allowance?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between border-t pt-2 mt-2">
                <span className="font-medium">{lang === 'ar' ? 'الإجمالي' : 'Total'}</span>
                <span className="font-bold text-primary">
                  {((contract.basic_salary || 0) + (contract.housing_allowance || 0) + (contract.transport_allowance || 0) + (contract.other_allowances || 0)).toLocaleString()} {lang === 'ar' ? 'ريال' : 'SAR'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Bank Info Card (Admin only) */}
        {isAdmin && contract && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <Building2 size={18} />
              <span>{lang === 'ar' ? 'معلومات البنك' : 'Bank Info'}</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{lang === 'ar' ? 'البنك' : 'Bank'}</span>
                <span>{contract.bank_name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">IBAN</span>
                <span className="font-mono text-xs">{contract.bank_iban || '-'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Supervisor Card */}
        {summary?.supervisor && (
          <div className="card-premium p-5 space-y-4">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <UserCheck size={18} />
              <span>{lang === 'ar' ? 'المشرف المباشر' : 'Supervisor'}</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                {(summary.supervisor.full_name || 'S')[0]}
              </div>
              <div>
                <p className="font-medium">
                  {lang === 'ar' ? (summary.supervisor.full_name_ar || summary.supervisor.full_name) : summary.supervisor.full_name}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Carryover Dialog */}
      <Dialog open={carryoverDialog} onOpenChange={setCarryoverDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{lang === 'ar' ? 'ترحيل الإجازات' : 'Leave Carryover'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                {lang === 'ar' ? 'الموظف:' : 'Employee:'} {lang === 'ar' ? employee.full_name_ar : employee.full_name}
              </p>
              <p className="text-sm text-muted-foreground">
                {lang === 'ar' ? 'الرصيد الحالي:' : 'Current Balance:'} <span className="font-bold text-primary">{leaveDetails?.balance || 0}</span> {lang === 'ar' ? 'يوم' : 'days'}
              </p>
            </div>
            <div>
              <Label>{lang === 'ar' ? 'عدد الأيام المرحلة' : 'Days to Carryover'}</Label>
              <Input 
                type="number" 
                min="0" 
                step="0.5"
                max={leaveDetails?.balance || 0}
                value={carryoverDays}
                onChange={e => setCarryoverDays(e.target.value)}
                data-testid="carryover-days-input"
              />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'ملاحظة (اختياري)' : 'Note (optional)'}</Label>
              <Textarea 
                value={carryoverNote}
                onChange={e => setCarryoverNote(e.target.value)}
                placeholder={lang === 'ar' ? 'سبب الترحيل...' : 'Reason for carryover...'}
              />
            </div>
            <Button 
              onClick={handleCarryover} 
              className="w-full" 
              disabled={savingCarryover}
              data-testid="confirm-carryover-btn"
            >
              {savingCarryover ? (lang === 'ar' ? 'جاري الترحيل...' : 'Processing...') : (lang === 'ar' ? 'تأكيد الترحيل' : 'Confirm Carryover')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
