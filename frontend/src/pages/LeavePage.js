import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { CalendarDays, Plus, Pencil, Trash2, Loader2, Clock, CalendarCheck, AlertTriangle, FileText, Info } from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function LeavePage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [balance, setBalance] = useState({});
  const [usedLeaves, setUsedLeaves] = useState({});  // الإجازات المستهلكة
  const [permissionHours, setPermissionHours] = useState({ used: 0, total: 2 });  // ساعات الاستئذان
  const [holidays, setHolidays] = useState([]);
  const [form, setForm] = useState({ leave_type: 'annual', start_date: '', end_date: '', reason: '', medical_file: null });
  const [submitting, setSubmitting] = useState(false);
  const [holidayForm, setHolidayForm] = useState({ name: '', name_ar: '', date: '' });
  const [editHoliday, setEditHoliday] = useState(null);
  const [addHolidayOpen, setAddHolidayOpen] = useState(false);
  
  // تحذير المادة 117 للإجازة المرضية
  const [sickLeaveWarning, setSickLeaveWarning] = useState(null);
  const [showSickWarningDialog, setShowSickWarningDialog] = useState(false);
  const [pendingSubmit, setPendingSubmit] = useState(false);

  const canRequest = ['employee', 'supervisor', 'sultan', 'salah'].includes(user?.role);
  const canEditHolidays = ['sultan', 'naif', 'stas'].includes(user?.role);
  const isAdmin = ['sultan', 'naif', 'salah', 'mohammed', 'stas'].includes(user?.role);
  const isEmployee = user?.role === 'employee';

  // أنواع الإجازات - الموظف يستطيع رفع جميع الأنواع
  // لكن لا يرى الأرصدة إلا للاعتيادية
  const LEAVE_TYPES = {
    annual: { 
      label: lang === 'ar' ? 'الاعتيادية' : 'Annual Leave', 
      labelFull: lang === 'ar' ? 'إجازة اعتيادية' : 'Annual Leave',
      hasBalance: true,
      showBalanceToEmployee: true  // الوحيدة التي يراها الموظف
    },
    sick: { 
      label: lang === 'ar' ? 'المرضية' : 'Sick Leave', 
      labelFull: lang === 'ar' ? 'إجازة مرضية' : 'Sick Leave',
      hasBalance: true,  // 120 يوم (30+60+30)
      showBalanceToEmployee: false,  // مخفي عن الموظف
      requiresFile: true,
      tiers: [
        { days: 30, salary: 100, label_ar: '30 يوم براتب كامل' },
        { days: 60, salary: 50, label_ar: '60 يوم بنصف الراتب' },
        { days: 30, salary: 0, label_ar: '30 يوم بدون أجر' }
      ]
    },
    marriage: { 
      label: lang === 'ar' ? 'الزواج' : 'Marriage', 
      labelFull: lang === 'ar' ? 'إجازة زواج' : 'Marriage Leave',
      hasBalance: true, 
      fixedDays: 5,
      showBalanceToEmployee: false
    },
    bereavement: { 
      label: lang === 'ar' ? 'الوفاة' : 'Bereavement', 
      labelFull: lang === 'ar' ? 'إجازة وفاة' : 'Bereavement Leave',
      hasBalance: true, 
      fixedDays: 5,
      showBalanceToEmployee: false
    },
    exam: { 
      label: lang === 'ar' ? 'الاختبار' : 'Exam', 
      labelFull: lang === 'ar' ? 'إجازة اختبار' : 'Exam Leave',
      hasBalance: false,  // حسب القرار
      showBalanceToEmployee: false
    },
    unpaid: { 
      label: lang === 'ar' ? 'بدون راتب' : 'Unpaid', 
      labelFull: lang === 'ar' ? 'إجازة بدون راتب' : 'Unpaid Leave',
      hasBalance: false,  // تُسجل فقط
      showBalanceToEmployee: false
    },
  };

  // الموظف يستطيع رفع جميع أنواع الإجازات
  const availableLeaveTypes = Object.entries(LEAVE_TYPES);

  useEffect(() => {
    if (canRequest) {
      api.get('/api/leave/balance').then(r => setBalance(r.data)).catch(() => {});
      api.get('/api/leave/used').then(r => setUsedLeaves(r.data)).catch(() => {});
      api.get('/api/leave/permission-hours').then(r => setPermissionHours(r.data)).catch(() => {});
    }
    api.get('/api/leave/holidays').then(r => setHolidays(r.data)).catch(() => {});
  }, [canRequest]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.start_date || !form.end_date) return toast.error(lang === 'ar' ? 'أدخل التواريخ' : 'Enter dates');
    
    // التحقق من رفع ملف للإجازة المرضية
    if (form.leave_type === 'sick' && !form.medical_file) {
      return toast.error(lang === 'ar' ? 'الإجازة المرضية تتطلب رفع ملف طبي PDF' : 'Sick leave requires medical PDF file');
    }
    
    // للإجازة المرضية: جلب معلومات الشريحة وعرض التحذير إذا تجاوز 30 يوم
    if (form.leave_type === 'sick' && !pendingSubmit) {
      try {
        const previewRes = await api.post('/api/leave/sick-preview', {
          start_date: form.start_date,
          end_date: form.end_date
        });
        
        // إذا كان الاستهلاك الحالي + الأيام الجديدة > 30 يوم، اعرض التحذير
        const currentUsed = previewRes.data.current_used || 0;
        const requestedDays = previewRes.data.requested_days || 0;
        const totalAfterRequest = currentUsed + requestedDays;
        
        // تحقق إذا هناك خصم (دخول شريحة 50% أو 0%)
        const hasDeduction = previewRes.data.tier_distribution?.some(tier => tier.salary_percent < 100);
        
        if (hasDeduction || totalAfterRequest > 30) {
          setSickLeaveWarning({
            ...previewRes.data,
            total_after_request: totalAfterRequest,
            has_deduction: hasDeduction
          });
          setShowSickWarningDialog(true);
          return; // توقف وانتظر تأكيد/توقيع المستخدم
        }
      } catch (err) {
        // تابع حتى لو فشل التحقق
        console.log('Sick leave preview failed, continuing...');
      }
    }
    
    await submitLeaveRequest();
  };
  
  const submitLeaveRequest = async () => {
    setSubmitting(true);
    setPendingSubmit(false);
    try {
      // إذا كان هناك ملف، نرفعه أولاً
      let medical_file_url = null;
      if (form.medical_file) {
        const formData = new FormData();
        formData.append('file', form.medical_file);
        const uploadRes = await api.post('/api/upload/medical', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        medical_file_url = uploadRes.data.url;
      }
      
      const requestData = {
        leave_type: form.leave_type,
        start_date: form.start_date,
        end_date: form.end_date,
        reason: form.reason,
        medical_file_url,
        // إضافة موافقة الموظف على الخصم إذا كانت مطلوبة
        employee_deduction_consent: sickLeaveWarning?.has_deduction ? true : undefined
      };
      
      const res = await api.post('/api/leave/request', requestData);
      toast.success(`${lang === 'ar' ? 'تم إنشاء الطلب' : 'Request created'}: ${res.data.ref_no}`);
      setForm({ leave_type: 'annual', start_date: '', end_date: '', reason: '', medical_file: null });
      setSickLeaveWarning(null);
      api.get('/api/leave/balance').then(r => setBalance(r.data)).catch(() => {});
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };
  
  const handleConfirmSickLeave = () => {
    setShowSickWarningDialog(false);
    setPendingSubmit(true);
    submitLeaveRequest();
  };

  const handleAddHoliday = async () => {
    const startDate = holidayForm.start_date || holidayForm.date;
    const endDate = holidayForm.end_date || holidayForm.date || startDate;
    
    if (!holidayForm.name || !startDate) return toast.error(lang === 'ar' ? 'أدخل الاسم وتاريخ البداية' : 'Enter name and start date');
    
    setSubmitting(true);
    try {
      if (editHoliday) {
        await api.put(`/api/leave/holidays/${editHoliday.id}`, { ...holidayForm, date: startDate });
        toast.success(lang === 'ar' ? 'تم التعديل' : 'Updated');
      } else {
        // إضافة جميع أيام الإجازة في النطاق
        const start = new Date(startDate);
        const end = new Date(endDate);
        let addedCount = 0;
        
        for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
          const dateStr = d.toISOString().slice(0, 10);
          await api.post('/api/leave/holidays', {
            name: holidayForm.name,
            name_ar: holidayForm.name_ar,
            date: dateStr
          });
          addedCount++;
        }
        
        toast.success(lang === 'ar' 
          ? `تم إضافة ${addedCount} يوم إجازة` 
          : `Added ${addedCount} holiday days`);
      }
      setAddHolidayOpen(false); setEditHoliday(null);
      setHolidayForm({ name: '', name_ar: '', start_date: '', end_date: '' });
      api.get('/api/leave/holidays').then(r => setHolidays(r.data)).catch(() => {});
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleDeleteHoliday = async (id) => {
    try {
      await api.delete(`/api/leave/holidays/${id}`);
      toast.success(lang === 'ar' ? 'تم الحذف' : 'Deleted');
      api.get('/api/leave/holidays').then(r => setHolidays(r.data)).catch(() => {});
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
  };

  return (
    <div className="space-y-6" data-testid="leave-page">
      <h1 className="text-2xl font-bold tracking-tight">{lang === 'ar' ? 'إدارة الإجازات' : 'Leave Management'}</h1>

      {/* عرض مختلف للموظف والإدارة */}
      {canRequest && (
        <>
          {isEmployee ? (
            /* ====== عرض الموظف: مختصر ====== */
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* رصيد الاعتيادية */}
              <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-emerald-500 rounded-lg">
                    <CalendarCheck size={20} className="text-white" />
                  </div>
                  <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-200">
                    {lang === 'ar' ? 'رصيد الاعتيادية' : 'Annual Balance'}
                  </p>
                </div>
                <p className="text-3xl font-bold text-emerald-700 dark:text-emerald-300">
                  {balance.annual?.available ?? balance.annual?.balance ?? 0}
                  <span className="text-base font-normal ms-1">{lang === 'ar' ? 'يوم' : 'days'}</span>
                </p>
                {/* عرض مصدر الرصيد */}
                {balance.annual?.is_migrated ? (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                    {lang === 'ar' 
                      ? `رصيد افتتاحي: ${balance.annual.opening_balance || balance.annual.earned_to_date} يوم` 
                      : `Opening balance: ${balance.annual.opening_balance || balance.annual.earned_to_date} days`}
                  </p>
                ) : balance.annual?.earned_to_date ? (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                    {lang === 'ar' ? `المكتسب: ${balance.annual.earned_to_date} يوم` : `Earned: ${balance.annual.earned_to_date} days`}
                  </p>
                ) : null}
              </div>

              {/* ساعات الاستئذان المستهلكة */}
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 border border-blue-200 dark:border-blue-800 rounded-xl p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-blue-500 rounded-lg">
                    <Clock size={20} className="text-white" />
                  </div>
                  <p className="text-sm font-semibold text-blue-800 dark:text-blue-200">
                    {lang === 'ar' ? 'ساعات الاستئذان المستهلكة' : 'Permission Hours Used'}
                  </p>
                </div>
                <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">
                  {permissionHours.used || 0}
                  <span className="text-base font-normal ms-1">/ {permissionHours.total || 2}</span>
                  <span className="text-base font-normal ms-1">{lang === 'ar' ? 'ساعات' : 'hrs'}</span>
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  {lang === 'ar' ? 'هذا الشهر' : 'This month'}
                </p>
              </div>
            </div>
          ) : (
            /* ====== عرض الإدارة: كامل ====== */
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {/* رصيد الاعتيادية */}
              <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg px-4 py-3">
                <p className="text-xs text-emerald-700 dark:text-emerald-300 font-medium">{lang === 'ar' ? 'الاعتيادية' : 'Annual'}</p>
                <p className="text-xl font-bold font-mono text-emerald-800 dark:text-emerald-200">{balance.annual?.available ?? 0}</p>
                <p className="text-[10px] text-emerald-600 dark:text-emerald-400">{lang === 'ar' ? 'يوم' : 'days'}</p>
              </div>
              
              {/* الإجازات المستهلكة للإدارة */}
              {Object.entries(usedLeaves).filter(([k]) => k !== 'annual').map(([type, days]) => (
                <div key={type} className="bg-muted/40 border border-border rounded-lg px-4 py-3">
                  <p className="text-xs text-muted-foreground">{LEAVE_TYPES[type]?.label || type}</p>
                  <p className="text-xl font-bold font-mono">{days}</p>
                  <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'يوم مستهلك' : 'days used'}</p>
                </div>
              ))}
              
              {/* ساعات الاستئذان */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3">
                <p className="text-xs text-blue-700 dark:text-blue-300 font-medium">{lang === 'ar' ? 'الاستئذان' : 'Permission'}</p>
                <p className="text-xl font-bold font-mono text-blue-800 dark:text-blue-200">{permissionHours.used}/{permissionHours.total}</p>
                <p className="text-[10px] text-blue-600 dark:text-blue-400">{lang === 'ar' ? 'ساعات' : 'hours'}</p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Leave Request Form - للموظف: فقط الاعتيادية */}
      {canRequest && (
        <div className="border border-border rounded-lg p-4">
          <h2 className="text-base font-semibold mb-3">{lang === 'ar' ? 'طلب إجازة جديد' : 'New Leave Request'}</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label>{lang === 'ar' ? 'نوع الإجازة' : 'Leave Type'}</Label>
              <Select value={form.leave_type} onValueChange={v => setForm(f => ({ ...f, leave_type: v, medical_file: null }))}>
                <SelectTrigger data-testid="leave-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {availableLeaveTypes.map(([key, val]) => (
                    <SelectItem key={key} value={key}>{val.labelFull}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{lang === 'ar' ? 'السبب' : 'Reason'}</Label>
              <Input data-testid="leave-reason" value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'تاريخ البداية' : 'Start Date'}</Label>
              <Input data-testid="leave-start" type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'تاريخ النهاية' : 'End Date'}</Label>
              <Input data-testid="leave-end" type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} />
            </div>
            
            {/* رفع ملف للإجازة المرضية - إلزامي */}
            {form.leave_type === 'sick' && (
              <div className="sm:col-span-2">
                <Label className="text-red-600">
                  {lang === 'ar' ? '* ملف التقرير الطبي (PDF)' : '* Medical Report (PDF)'}
                </Label>
                <Input 
                  type="file" 
                  accept=".pdf"
                  onChange={e => setForm(f => ({ ...f, medical_file: e.target.files[0] }))}
                  className="mt-1"
                  data-testid="medical-file-input"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {lang === 'ar' ? 'يجب رفع ملف PDF للتقرير الطبي المعتمد' : 'Approved medical PDF report is required'}
                </p>
              </div>
            )}
            
            <div className="sm:col-span-2">
              <Button type="submit" disabled={submitting} data-testid="submit-leave" className="w-full sm:w-auto">
                {submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}
                {submitting ? (lang === 'ar' ? 'جاري الإرسال...' : 'Submitting...') : (lang === 'ar' ? 'تقديم الطلب' : 'Submit Request')}
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Public Holidays - Admin can edit, employees don't see table */}
      {isAdmin && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold flex items-center gap-2"><CalendarDays size={18} /> {t('leave.publicHolidays')}</h2>
            {canEditHolidays && (
              <Dialog open={addHolidayOpen} onOpenChange={(open) => { setAddHolidayOpen(open); if (!open) { setEditHoliday(null); setHolidayForm({ name: '', name_ar: '', start_date: '', end_date: '' }); } }}>
                <DialogTrigger asChild>
                  <Button size="sm" variant="outline" data-testid="add-holiday-btn"><Plus size={14} className="me-1" />{lang === 'ar' ? 'إضافة إجازة' : 'Add Holiday'}</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>{editHoliday ? (lang === 'ar' ? 'تعديل الإجازة' : 'Edit Holiday') : (lang === 'ar' ? 'إضافة إجازة رسمية' : 'Add Public Holiday')}</DialogTitle></DialogHeader>
                  <div className="space-y-3">
                    <div><Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Name'}</Label><Input data-testid="holiday-name" value={holidayForm.name} onChange={e => setHolidayForm(f => ({ ...f, name: e.target.value }))} placeholder="Eid Al-Fitr" /></div>
                    <div><Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Name (Arabic)'}</Label><Input data-testid="holiday-name-ar" value={holidayForm.name_ar} onChange={e => setHolidayForm(f => ({ ...f, name_ar: e.target.value }))} dir="rtl" placeholder="عيد الفطر" /></div>
                    <div className="grid grid-cols-2 gap-3">
                      <div><Label>{lang === 'ar' ? 'من تاريخ' : 'Start Date'}</Label><Input data-testid="holiday-start-date" type="date" value={holidayForm.start_date || holidayForm.date || ''} onChange={e => setHolidayForm(f => ({ ...f, start_date: e.target.value, date: e.target.value }))} /></div>
                      <div><Label>{lang === 'ar' ? 'إلى تاريخ' : 'End Date'}</Label><Input data-testid="holiday-end-date" type="date" value={holidayForm.end_date || holidayForm.date || ''} onChange={e => setHolidayForm(f => ({ ...f, end_date: e.target.value }))} /></div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {lang === 'ar' ? 'سيتم إضافة جميع أيام الإجازة تلقائياً بين التاريخين' : 'All holiday days between the dates will be added automatically'}
                    </p>
                    <Button onClick={handleAddHoliday} disabled={submitting} data-testid="save-holiday" className="w-full">{submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}{editHoliday ? (lang === 'ar' ? 'حفظ' : 'Save') : (lang === 'ar' ? 'إضافة' : 'Add')}</Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="holidays-table">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900/50 text-xs border-b border-border">
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'الإجازة' : 'Holiday'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'من' : 'From'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'إلى' : 'To'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'الأيام' : 'Days'}</th>
                    {canEditHolidays && <th className="px-2 py-2.5 w-16"></th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {/* Group consecutive holidays by name */}
                  {(() => {
                    // Group holidays by base name (remove numbers like "1", "2" etc.)
                    const groups = {};
                    holidays.forEach(h => {
                      const baseName = (h.name_ar || h.name || '').replace(/\s*\d+\s*$/, '').trim() || h.name;
                      if (!groups[baseName]) {
                        groups[baseName] = [];
                      }
                      groups[baseName].push(h);
                    });
                    
                    // Convert to range format
                    return Object.entries(groups).map(([name, days]) => {
                      // Sort by date
                      days.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
                      const startDate = days[0]?.date;
                      const endDate = days[days.length - 1]?.date;
                      const nameAr = days[0]?.name_ar?.replace(/\s*\d+\s*$/, '').trim() || name;
                      const nameEn = days[0]?.name?.replace(/\s*\d+\s*$/, '').trim() || name;
                      
                      return (
                        <tr key={name} className="hover:bg-muted/30">
                          <td className="px-3 py-2 text-sm font-medium">
                            {lang === 'ar' ? nameAr : nameEn}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">{formatGregorianHijri(startDate).combined}</td>
                          <td className="px-3 py-2 font-mono text-xs">{formatGregorianHijri(endDate).combined}</td>
                          <td className="px-3 py-2 text-sm text-center">
                            <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium">
                              {days.length}
                            </span>
                          </td>
                          {canEditHolidays && (
                            <td className="px-2 py-2">
                              <div className="flex items-center gap-1">
                                <button 
                                  onClick={() => {
                                    // Open edit dialog with first day's data
                                    setEditHoliday(days[0]);
                                    setHolidayForm({ 
                                      name: nameEn, 
                                      name_ar: nameAr, 
                                      start_date: startDate,
                                      end_date: endDate
                                    });
                                    setAddHolidayOpen(true);
                                  }} 
                                  className="text-blue-400 hover:text-blue-600 p-1"
                                  title={lang === 'ar' ? 'تعديل' : 'Edit'}
                                >
                                  <Pencil size={13} />
                                </button>
                                <button 
                                  onClick={() => {
                                    if (confirm(lang === 'ar' ? `هل تريد حذف جميع أيام ${nameAr}؟` : `Delete all ${nameEn} days?`)) {
                                      days.forEach(d => handleDeleteHoliday(d.id));
                                    }
                                  }} 
                                  className="text-red-400 hover:text-red-600 p-1"
                                  title={lang === 'ar' ? 'حذف' : 'Delete'}
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            </td>
                          )}
                        </tr>
                      );
                    });
                  })()}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* تحذير المادة 117 للإجازة المرضية - رسالة رسمية مع طلب التوقيع */}
      <Dialog open={showSickWarningDialog} onOpenChange={setShowSickWarningDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="w-5 h-5" />
              {lang === 'ar' ? 'تنبيه رسمي - المادة 117' : 'Official Notice - Article 117'}
            </DialogTitle>
          </DialogHeader>
          
          {sickLeaveWarning && (
            <div className="space-y-4 py-2">
              {/* رسالة رسمية للموظف */}
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border-2 border-amber-300">
                <p className="text-base font-medium text-amber-900 dark:text-amber-100 mb-3">
                  {lang === 'ar' 
                    ? `عزيزي ${user?.full_name?.split(' ')[0] || 'الموظف'}،` 
                    : `Dear ${user?.full_name?.split(' ')[0] || 'Employee'},`
                  }
                </p>
                
                <p className="text-sm text-amber-800 dark:text-amber-200 mb-3">
                  {lang === 'ar'
                    ? `بناءً على طلبك للإجازة المرضية (${sickLeaveWarning.requested_days || 0} يوم)، واستهلاكك الحالي (${sickLeaveWarning.current_used || 0} يوم من 120 يوم)، سيتم تطبيق الخصم التالي حسب المادة 117 من نظام العمل السعودي:`
                    : `Based on your sick leave request (${sickLeaveWarning.requested_days || 0} days), and your current usage (${sickLeaveWarning.current_used || 0} of 120 days), the following deduction will apply according to Article 117 of Saudi Labor Law:`
                  }
                </p>
                
                {/* تفاصيل الخصم */}
                <div className="space-y-2 mb-3">
                  {sickLeaveWarning.tier_distribution?.map((tier, i) => (
                    <div key={i} className={`p-2 rounded-lg font-medium ${
                      tier.salary_percent === 100 
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                        : tier.salary_percent === 50 
                          ? 'bg-amber-100 text-amber-900 border border-amber-400' 
                          : 'bg-red-100 text-red-800 border border-red-300'
                    }`}>
                      <span className="font-bold">{tier.days} {lang === 'ar' ? 'يوم' : 'days'}</span>
                      <span className="mx-2">→</span>
                      <span>
                        {tier.salary_percent === 100 
                          ? (lang === 'ar' ? 'براتب كامل (بدون خصم)' : 'Full pay (no deduction)') 
                          : tier.salary_percent === 50 
                            ? (lang === 'ar' ? 'خصم 50% من الراتب' : '50% salary deduction') 
                            : (lang === 'ar' ? 'خصم 100% من الراتب (بدون راتب)' : '100% salary deduction (no pay)')
                        }
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* نص اللائحة */}
              <div className="p-3 bg-slate-100 dark:bg-slate-800 rounded-lg border text-xs">
                <p className="font-bold mb-2 text-slate-700 dark:text-slate-300">
                  {lang === 'ar' ? '📜 المادة 117 - نظام العمل السعودي:' : '📜 Article 117 - Saudi Labor Law:'}
                </p>
                <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400">
                  <li>{lang === 'ar' ? 'أول 30 يوم: براتب كامل (100%)' : 'First 30 days: Full pay (100%)'}</li>
                  <li>{lang === 'ar' ? 'الـ 60 يوم التالية: بنصف الراتب (50%)' : 'Next 60 days: Half pay (50%)'}</li>
                  <li>{lang === 'ar' ? 'الـ 30 يوم الأخيرة: بدون أجر (0%)' : 'Last 30 days: No pay (0%)'}</li>
                  <li className="font-medium">{lang === 'ar' ? 'الحد الأقصى: 120 يوم في السنة' : 'Maximum: 120 days per year'}</li>
                </ul>
              </div>
              
              {/* طلب التوقيع */}
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-300 text-center">
                <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  {lang === 'ar' 
                    ? '✍️ بالضغط على "توقيع وتقديم"، أوافق على تطبيق الخصم المذكور أعلاه.'
                    : '✍️ By clicking "Sign & Submit", I agree to the above deduction.'
                  }
                </p>
              </div>
            </div>
          )}
          
          <DialogFooter className="gap-2 flex-col sm:flex-row">
            <Button variant="outline" onClick={() => setShowSickWarningDialog(false)} className="w-full sm:w-auto">
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button 
              onClick={handleConfirmSickLeave} 
              className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700"
              data-testid="sign-submit-sick-leave"
            >
              {lang === 'ar' ? '✍️ توقيع وتقديم الطلب' : '✍️ Sign & Submit Request'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
