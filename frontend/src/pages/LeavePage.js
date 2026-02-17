import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { CalendarDays, Plus, Pencil, Trash2, Loader2, Clock, CalendarCheck } from 'lucide-react';
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
    
    setSubmitting(true);
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
        medical_file_url
      };
      
      const res = await api.post('/api/leave/request', requestData);
      toast.success(`${lang === 'ar' ? 'تم إنشاء الطلب' : 'Request created'}: ${res.data.ref_no}`);
      setForm({ leave_type: 'annual', start_date: '', end_date: '', reason: '', medical_file: null });
      api.get('/api/leave/balance').then(r => setBalance(r.data)).catch(() => {});
    } catch (err) { toast.error(err.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleAddHoliday = async () => {
    if (!holidayForm.name || !holidayForm.date) return toast.error(lang === 'ar' ? 'أدخل الاسم والتاريخ' : 'Enter name and date');
    setSubmitting(true);
    try {
      if (editHoliday) {
        await api.put(`/api/leave/holidays/${editHoliday.id}`, holidayForm);
        toast.success(lang === 'ar' ? 'تم التعديل' : 'Updated');
      } else {
        await api.post('/api/leave/holidays', holidayForm);
        toast.success(lang === 'ar' ? 'تم الإضافة' : 'Added');
      }
      setAddHolidayOpen(false); setEditHoliday(null);
      setHolidayForm({ name: '', name_ar: '', date: '' });
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
                {balance.annual?.earned_to_date && (
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                    {lang === 'ar' ? `المكتسب: ${balance.annual.earned_to_date} يوم` : `Earned: ${balance.annual.earned_to_date} days`}
                  </p>
                )}
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
              <Dialog open={addHolidayOpen} onOpenChange={(open) => { setAddHolidayOpen(open); if (!open) { setEditHoliday(null); setHolidayForm({ name: '', name_ar: '', date: '' }); } }}>
                <DialogTrigger asChild>
                  <Button size="sm" variant="outline" data-testid="add-holiday-btn"><Plus size={14} className="me-1" />{lang === 'ar' ? 'إضافة إجازة' : 'Add Holiday'}</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>{editHoliday ? (lang === 'ar' ? 'تعديل الإجازة' : 'Edit Holiday') : (lang === 'ar' ? 'إضافة إجازة رسمية' : 'Add Public Holiday')}</DialogTitle></DialogHeader>
                  <div className="space-y-3">
                    <div><Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Name'}</Label><Input data-testid="holiday-name" value={holidayForm.name} onChange={e => setHolidayForm(f => ({ ...f, name: e.target.value }))} /></div>
                    <div><Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Name (Arabic)'}</Label><Input data-testid="holiday-name-ar" value={holidayForm.name_ar} onChange={e => setHolidayForm(f => ({ ...f, name_ar: e.target.value }))} dir="rtl" /></div>
                    <div><Label>{lang === 'ar' ? 'التاريخ' : 'Date'}</Label><Input data-testid="holiday-date" type="date" value={holidayForm.date} onChange={e => setHolidayForm(f => ({ ...f, date: e.target.value }))} /></div>
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
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">Name</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground hidden sm:table-cell">Name (AR)</th>
                    <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'المصدر' : 'Source'}</th>
                    {canEditHolidays && <th className="px-2 py-2.5 w-16"></th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {holidays.map(h => (
                    <tr key={h.id || h.date} className="hover:bg-muted/30">
                      <td className="px-3 py-2 font-mono text-xs">{formatGregorianHijri(h.date).combined}</td>
                      <td className="px-3 py-2 text-sm">{h.name}</td>
                      <td className="px-3 py-2 text-sm hidden sm:table-cell">{h.name_ar}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground capitalize">{h.source || 'system'}</td>
                      {canEditHolidays && (
                        <td className="px-2 py-2 flex gap-1">
                          <button onClick={() => { setEditHoliday(h); setHolidayForm({ name: h.name, name_ar: h.name_ar || '', date: h.date }); setAddHolidayOpen(true); }} className="text-muted-foreground hover:text-foreground"><Pencil size={13} /></button>
                          <button onClick={() => handleDeleteHoliday(h.id)} className="text-red-400 hover:text-red-600"><Trash2 size={13} /></button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
