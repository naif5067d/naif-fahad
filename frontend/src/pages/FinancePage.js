import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Search, Pencil, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function FinancePage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [codes, setCodes] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(null); // code object
  const [addForm, setAddForm] = useState({ code: '', name: '', name_ar: '', category: 'other' });
  const [editForm, setEditForm] = useState({ code: '', name: '', name_ar: '', category: '' });
  const [submitting, setSubmitting] = useState(false);
  const [selectedEmp, setSelectedEmp] = useState('');
  const [statement, setStatement] = useState([]);

  const fetchCodes = () => api.get('/api/finance/codes').then(r => setCodes(r.data)).catch(() => {});
  useEffect(() => {
    fetchCodes();
    api.get('/api/employees').then(r => setEmployees(r.data)).catch(() => {});
  }, []);

  const canEdit = ['sultan', 'naif', 'salah', 'stas'].includes(user?.role);

  const fetchStatement = (empId) => {
    setSelectedEmp(empId);
    if (empId) api.get(`/api/finance/statement/${empId}`).then(r => setStatement(r.data)).catch(() => setStatement([]));
  };

  const handleAdd = async () => {
    if (!addForm.code || !addForm.name) return toast.error(lang === 'ar' ? 'أدخل الرقم والاسم' : 'Enter code and name');
    setSubmitting(true);
    try {
      await api.post('/api/finance/codes/add', { code: parseInt(addForm.code), name: addForm.name, name_ar: addForm.name_ar, category: addForm.category });
      toast.success(lang === 'ar' ? 'تم إضافة الكود' : 'Code added');
      setAddOpen(false); setAddForm({ code: '', name: '', name_ar: '', category: 'other' }); fetchCodes();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleEdit = async () => {
    if (!editOpen) return;
    setSubmitting(true);
    try {
      await api.put(`/api/finance/codes/${editOpen.id}`, { code: parseInt(editForm.code), name: editForm.name, name_ar: editForm.name_ar, category: editForm.category });
      toast.success(lang === 'ar' ? 'تم التعديل' : 'Code updated');
      setEditOpen(null); fetchCodes();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const openEdit = (c) => {
    setEditForm({ code: c.code.toString(), name: c.name, name_ar: c.name_ar || '', category: c.category || 'other' });
    setEditOpen(c);
  };

  const filteredCodes = codes.filter(c => {
    if (!search) return true;
    return c.name.toLowerCase().includes(search.toLowerCase()) || c.code.toString().includes(search) || c.name_ar?.includes(search);
  });

  return (
    <div className="space-y-6" data-testid="finance-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{t('finance.title')}</h1>
        {canEdit && (
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-code-btn" className="bg-primary text-primary-foreground"><Plus size={16} className="me-1" /> {lang === 'ar' ? 'إضافة كود' : 'Add Code'}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>{lang === 'ar' ? 'إضافة كود مالي' : 'Add Finance Code'}</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label>{lang === 'ar' ? 'رقم الكود' : 'Code Number'}</Label><Input data-testid="add-code-num" type="number" value={addForm.code} onChange={e => setAddForm(f => ({ ...f, code: e.target.value }))} /></div>
                <div><Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Name'}</Label><Input data-testid="add-code-name" value={addForm.name} onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))} /></div>
                <div><Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Name (Arabic)'}</Label><Input data-testid="add-code-name-ar" value={addForm.name_ar} onChange={e => setAddForm(f => ({ ...f, name_ar: e.target.value }))} dir="rtl" /></div>
                <div>
                  <Label>{lang === 'ar' ? 'التصنيف' : 'Category'}</Label>
                  <Select value={addForm.category} onValueChange={v => setAddForm(f => ({ ...f, category: v }))}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="earnings">{t('finance.earnings')}</SelectItem>
                      <SelectItem value="deductions">{t('finance.deductions')}</SelectItem>
                      <SelectItem value="loans">{t('finance.loans')}</SelectItem>
                      <SelectItem value="other">{t('finance.other')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleAdd} disabled={submitting} data-testid="confirm-add-code" className="w-full">{submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}{lang === 'ar' ? 'إضافة' : 'Add'}</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Tabs defaultValue="codes">
        <TabsList>
          <TabsTrigger value="codes" data-testid="tab-codes">{t('finance.codes')}</TabsTrigger>
          <TabsTrigger value="statement" data-testid="tab-statement">{t('finance.statement')}</TabsTrigger>
        </TabsList>

        <TabsContent value="codes" className="mt-4">
          <div className="relative mb-3">
            <Search size={16} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input data-testid="code-search" value={search} onChange={e => setSearch(e.target.value)} placeholder={t('common.search')} className="ps-9" />
          </div>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="hr-table" data-testid="finance-codes-table">
                <thead><tr>
                  <th>{t('finance.code')}</th>
                  <th>Name</th>
                  <th className="hidden sm:table-cell">Name (AR)</th>
                  <th>Category</th>
                  {canEdit && <th className="w-10"></th>}
                </tr></thead>
                <tbody>
                  {filteredCodes.map(c => (
                    <tr key={c.id || c.code}>
                      <td className="font-mono text-xs font-bold">{c.code}</td>
                      <td className="text-sm">{c.name}</td>
                      <td className="hidden sm:table-cell text-sm">{c.name_ar}</td>
                      <td className="text-xs capitalize text-muted-foreground">{c.category}</td>
                      {canEdit && (
                        <td><button onClick={(e) => { e.stopPropagation(); openEdit(c); }} className="text-muted-foreground hover:text-foreground"><Pencil size={14} /></button></td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="statement" className="mt-4">
          <div className="mb-3">
            <Select value={selectedEmp} onValueChange={fetchStatement}>
              <SelectTrigger data-testid="statement-employee-select"><SelectValue placeholder={lang === 'ar' ? 'اختر الموظف' : 'Select employee'} /></SelectTrigger>
              <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{lang === 'ar' ? e.full_name_ar || e.full_name : e.full_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="hr-table" data-testid="finance-statement-table">
                <thead><tr>
                  <th>{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                  <th>{t('finance.code')}</th>
                  <th>{t('finance.description')}</th>
                  <th className="text-right">{t('finance.amount')}</th>
                  <th>{lang === 'ar' ? 'العهدة' : 'Custody'}</th>
                </tr></thead>
                <tbody>
                  {statement.length === 0 ? (
                    <tr><td colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
                  ) : statement.map(e => (
                    <tr key={e.id}>
                      <td className="font-mono text-xs">{e.date?.slice(0, 10)}</td>
                      <td className="text-xs">{e.code} - {e.code_name}</td>
                      <td className="text-sm">{e.description}</td>
                      <td className="text-right font-mono font-medium">{e.amount?.toLocaleString()} SAR</td>
                      <td className="text-xs font-mono">{e.custody_number || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog */}
      <Dialog open={!!editOpen} onOpenChange={() => setEditOpen(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>{lang === 'ar' ? 'تعديل الكود' : 'Edit Code'}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>{lang === 'ar' ? 'رقم الكود' : 'Code Number'}</Label><Input data-testid="edit-code-num" type="number" value={editForm.code} onChange={e => setEditForm(f => ({ ...f, code: e.target.value }))} /></div>
            <div><Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Name'}</Label><Input data-testid="edit-code-name" value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} /></div>
            <div><Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Name (Arabic)'}</Label><Input data-testid="edit-code-name-ar" value={editForm.name_ar} onChange={e => setEditForm(f => ({ ...f, name_ar: e.target.value }))} dir="rtl" /></div>
            <div>
              <Label>{lang === 'ar' ? 'التصنيف' : 'Category'}</Label>
              <Select value={editForm.category} onValueChange={v => setEditForm(f => ({ ...f, category: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="earnings">{t('finance.earnings')}</SelectItem>
                  <SelectItem value="deductions">{t('finance.deductions')}</SelectItem>
                  <SelectItem value="loans">{t('finance.loans')}</SelectItem>
                  <SelectItem value="other">{t('finance.other')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleEdit} disabled={submitting} data-testid="confirm-edit-code" className="w-full">{submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}{lang === 'ar' ? 'حفظ' : 'Save'}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
