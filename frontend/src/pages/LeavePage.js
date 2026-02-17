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

  // أنواع الإجازات - للإدارة فقط تفاصيل كاملة
  const LEAVE_TYPES = {
    annual: { 
      label: lang === 'ar' ? 'الاعتيادية' : 'Annual Leave', 
      labelFull: lang === 'ar' ? 'إجازة اعتيادية' : 'Annual Leave',
      hasBalance: true,
      showToEmployee: true
    },
    sick: { 
      label: lang === 'ar' ? 'المرضية' : 'Sick Leave', 
      labelFull: lang === 'ar' ? 'إجازة مرضية' : 'Sick Leave',
      hasBalance: false, 
      requiresFile: true,
      showToEmployee: false  // لا تظهر للموظف - مسار إداري
    },
    marriage: { 
      label: lang === 'ar' ? 'الزواج' : 'Marriage', 
      labelFull: lang === 'ar' ? 'إجازة زواج' : 'Marriage Leave',
      hasBalance: false, 
      days: 5,
      showToEmployee: false
    },
    bereavement: { 
      label: lang === 'ar' ? 'الوفاة' : 'Bereavement', 
      labelFull: lang === 'ar' ? 'إجازة وفاة' : 'Bereavement Leave',
      hasBalance: false, 
      days: 5,
      showToEmployee: false
    },
    exam: { 
      label: lang === 'ar' ? 'الاختبار' : 'Exam', 
      labelFull: lang === 'ar' ? 'إجازة اختبار' : 'Exam Leave',
      hasBalance: false,
      showToEmployee: false
    },
    unpaid: { 
      label: lang === 'ar' ? 'بدون راتب' : 'Unpaid', 
      labelFull: lang === 'ar' ? 'إجازة بدون راتب' : 'Unpaid Leave',
      hasBalance: false,
      showToEmployee: false
    },
  };

  // أنواع الإجازات المتاحة حسب الدور
  const availableLeaveTypes = isEmployee 
    ? Object.entries(LEAVE_TYPES).filter(([k, v]) => v.showToEmployee)
    : Object.entries(LEAVE_TYPES);

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
      <h1 className="text-2xl font-bold tracking-tight">{t('leave.title')}</h1>

      {/* Balance cards - for employees */}
      {canRequest && (
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(balance).map(([type, bal]) => (
            <div key={type} className="bg-muted/40 border border-border rounded-lg px-4 py-3">
              <p className="text-xs text-muted-foreground capitalize">{t(`leave.${type}`) || type}</p>
              <p className="text-xl font-bold font-mono">{bal?.available ?? bal?.balance ?? 0}</p>
              <p className="text-[10px] text-muted-foreground">{t('dashboard.days')}</p>
            </div>
          ))}
        </div>
      )}

      {/* Leave Request Form */}
      {canRequest && (
        <div className="border border-border rounded-lg p-4">
          <h2 className="text-base font-semibold mb-3">{t('leave.newRequest')}</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label>{t('leave.leaveType')}</Label>
              <Select value={form.leave_type} onValueChange={v => setForm(f => ({ ...f, leave_type: v, medical_file: null }))}>
                <SelectTrigger data-testid="leave-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(LEAVE_TYPES).map(([key, val]) => (
                    <SelectItem key={key} value={key}>{val.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{t('leave.reason')}</Label>
              <Input data-testid="leave-reason" value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} />
            </div>
            <div>
              <Label>{t('leave.startDate')}</Label>
              <Input data-testid="leave-start" type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
            </div>
            <div>
              <Label>{t('leave.endDate')}</Label>
              <Input data-testid="leave-end" type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} />
            </div>
            
            {/* رفع ملف للإجازة المرضية */}
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
                  {lang === 'ar' ? 'يجب رفع ملف PDF للتقرير الطبي للتحقق' : 'PDF medical report required for verification'}
                </p>
              </div>
            )}
            
            <div className="sm:col-span-2">
              <Button type="submit" disabled={submitting} data-testid="submit-leave" className="w-full sm:w-auto">
                {submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}
                {submitting ? t('common.loading') : t('leave.submit')}
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
