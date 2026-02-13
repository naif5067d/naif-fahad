import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Plus, Package, RotateCcw, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function CustodyPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [custodies, setCustodies] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(null); // custody id
  const [form, setForm] = useState({ employee_id: '', item_name: '', item_name_ar: '', description: '', serial_number: '', estimated_value: '' });
  const [submitting, setSubmitting] = useState(false);

  const fetchData = () => {
    api.get('/api/custody/all').then(r => setCustodies(r.data)).catch(() => {});
    api.get('/api/employees').then(r => setEmployees(r.data)).catch(() => {});
  };

  useEffect(() => { fetchData(); }, []);

  const canCreate = ['sultan', 'naif', 'stas'].includes(user?.role);
  const canReturn = user?.role === 'sultan' || user?.role === 'stas';

  const handleCreate = async () => {
    if (!form.employee_id || !form.item_name) {
      toast.error(lang === 'ar' ? 'يرجى ملء الحقول المطلوبة' : 'Please fill required fields');
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/api/custody/tangible', {
        ...form,
        estimated_value: parseFloat(form.estimated_value) || 0
      });
      toast.success(`${lang === 'ar' ? 'تم إنشاء العهدة' : 'Custody created'}: ${res.data.ref_no}`);
      setCreateOpen(false);
      setForm({ employee_id: '', item_name: '', item_name_ar: '', description: '', serial_number: '', estimated_value: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSubmitting(false); }
  };

  const handleReturn = async (custodyId) => {
    setSubmitting(true);
    try {
      const res = await api.post('/api/custody/tangible/return', { custody_id: custodyId });
      toast.success(`${lang === 'ar' ? 'تم طلب الإرجاع' : 'Return requested'}: ${res.data.ref_no}`);
      setReturnOpen(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSubmitting(false); }
  };

  const activeCustodies = custodies.filter(c => c.status === 'active');
  const returnedCustodies = custodies.filter(c => c.status === 'returned');

  return (
    <div className="space-y-6" data-testid="custody-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{lang === 'ar' ? 'العهد الملموسة' : 'Tangible Custody'}</h1>
        {canCreate && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button data-testid="create-custody-btn" className="bg-primary text-primary-foreground">
                <Plus size={16} className="me-1" /> {lang === 'ar' ? 'إنشاء عهدة' : 'Create Custody'}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>{lang === 'ar' ? 'إنشاء عهدة ملموسة' : 'Create Tangible Custody'}</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>{t('transactions.employee')}</Label>
                  <Select value={form.employee_id} onValueChange={v => setForm(f => ({ ...f, employee_id: v }))}>
                    <SelectTrigger data-testid="custody-employee-select"><SelectValue placeholder={lang === 'ar' ? 'اختر الموظف' : 'Select employee'} /></SelectTrigger>
                    <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{lang === 'ar' ? e.full_name_ar || e.full_name : e.full_name} ({e.employee_number})</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>{lang === 'ar' ? 'اسم العنصر (إنجليزي)' : 'Item Name'}</Label>
                    <Input data-testid="custody-item-name" value={form.item_name} onChange={e => setForm(f => ({ ...f, item_name: e.target.value }))} />
                  </div>
                  <div>
                    <Label>{lang === 'ar' ? 'اسم العنصر (عربي)' : 'Item Name (Arabic)'}</Label>
                    <Input data-testid="custody-item-name-ar" value={form.item_name_ar} onChange={e => setForm(f => ({ ...f, item_name_ar: e.target.value }))} dir="rtl" />
                  </div>
                </div>
                <div>
                  <Label>{lang === 'ar' ? 'الرقم التسلسلي' : 'Serial Number'}</Label>
                  <Input data-testid="custody-serial" value={form.serial_number} onChange={e => setForm(f => ({ ...f, serial_number: e.target.value }))} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>{lang === 'ar' ? 'القيمة التقديرية (ريال)' : 'Estimated Value (SAR)'}</Label>
                    <Input data-testid="custody-value" type="number" value={form.estimated_value} onChange={e => setForm(f => ({ ...f, estimated_value: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <Label>{t('finance.description')}</Label>
                  <Input data-testid="custody-description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
                </div>
                <Button data-testid="submit-custody" onClick={handleCreate} className="w-full bg-primary text-primary-foreground" disabled={submitting}>
                  {submitting ? <Loader2 size={16} className="me-1 animate-spin" /> : null}
                  {submitting ? t('common.loading') : t('common.submit')}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Active Custodies */}
      <div>
        <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
          <Package size={18} className="text-primary" />
          {lang === 'ar' ? 'العهد النشطة' : 'Active Custodies'}
          <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">{activeCustodies.length}</span>
        </h2>
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="hr-table" data-testid="active-custody-table">
              <thead><tr>
                <th>{lang === 'ar' ? 'العنصر' : 'Item'}</th>
                <th>{t('transactions.employee')}</th>
                <th className="hidden sm:table-cell">{lang === 'ar' ? 'الرقم التسلسلي' : 'Serial'}</th>
                <th className="hidden sm:table-cell">{lang === 'ar' ? 'القيمة' : 'Value'}</th>
                <th className="hidden md:table-cell">{lang === 'ar' ? 'تاريخ التسليم' : 'Assigned'}</th>
                {canReturn && <th>{t('common.actions')}</th>}
              </tr></thead>
              <tbody>
                {activeCustodies.length === 0 ? (
                  <tr><td colSpan={canReturn ? 6 : 5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
                ) : activeCustodies.map(c => (
                  <tr key={c.id} data-testid={`custody-row-${c.id}`}>
                    <td className="text-sm font-medium">{lang === 'ar' ? c.item_name_ar || c.item_name : c.item_name}</td>
                    <td className="text-sm">{lang === 'ar' ? c.employee_name_ar || c.employee_name : c.employee_name}</td>
                    <td className="hidden sm:table-cell text-xs font-mono">{c.serial_number || '-'}</td>
                    <td className="hidden sm:table-cell text-xs">{c.estimated_value?.toLocaleString() || 0} SAR</td>
                    <td className="hidden md:table-cell text-xs text-muted-foreground">{c.assigned_at?.slice(0, 10)}</td>
                    {canReturn && (
                      <td>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => handleReturn(c.id)}
                          disabled={submitting}
                          data-testid={`return-custody-${c.id}`}
                        >
                          <RotateCcw size={12} className="me-1" /> {lang === 'ar' ? 'تم الاستلام' : 'Received'}
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Returned Custodies */}
      {returnedCustodies.length > 0 && (
        <div>
          <h2 className="text-base font-semibold mb-3 text-muted-foreground">{lang === 'ar' ? 'العهد المُرجعة' : 'Returned Custodies'}</h2>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="hr-table" data-testid="returned-custody-table">
                <thead><tr>
                  <th>{lang === 'ar' ? 'العنصر' : 'Item'}</th>
                  <th>{t('transactions.employee')}</th>
                  <th className="hidden sm:table-cell">{lang === 'ar' ? 'الرقم التسلسلي' : 'Serial'}</th>
                  <th>{lang === 'ar' ? 'تاريخ الإرجاع' : 'Returned'}</th>
                </tr></thead>
                <tbody>
                  {returnedCustodies.map(c => (
                    <tr key={c.id}>
                      <td className="text-sm">{lang === 'ar' ? c.item_name_ar || c.item_name : c.item_name}</td>
                      <td className="text-sm">{lang === 'ar' ? c.employee_name_ar || c.employee_name : c.employee_name}</td>
                      <td className="hidden sm:table-cell text-xs font-mono">{c.serial_number || '-'}</td>
                      <td className="text-xs text-muted-foreground">{c.returned_at?.slice(0, 10) || '-'}</td>
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
