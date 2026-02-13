import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Search, CheckCircle, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function FinancePage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [codes, setCodes] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ employee_id: '', code: '', amount: '', description: '', tx_type: 'credit' });
  const [codeInfo, setCodeInfo] = useState(null); // {found, code}
  const [newCodeDef, setNewCodeDef] = useState({ name: '', name_ar: '', category: 'other' });
  const [submitting, setSubmitting] = useState(false);
  const [selectedEmp, setSelectedEmp] = useState('');
  const [statement, setStatement] = useState([]);

  useEffect(() => {
    api.get('/api/finance/codes').then(r => setCodes(r.data)).catch(() => {});
    api.get('/api/employees').then(r => setEmployees(r.data)).catch(() => {});
  }, []);

  // Sultan only can create finance_60
  const canCreate = user?.role === 'sultan' || user?.role === 'stas';

  const fetchStatement = (empId) => {
    setSelectedEmp(empId);
    if (empId) api.get(`/api/finance/statement/${empId}`).then(r => setStatement(r.data)).catch(() => setStatement([]));
  };

  // Manual code lookup with debounce
  const lookupCode = useCallback(async (codeNum) => {
    if (!codeNum || isNaN(parseInt(codeNum))) {
      setCodeInfo(null);
      return;
    }
    try {
      const res = await api.get(`/api/finance/codes/lookup/${parseInt(codeNum)}`);
      setCodeInfo(res.data);
    } catch {
      setCodeInfo(null);
    }
  }, []);

  const handleCodeChange = (val) => {
    setForm(f => ({ ...f, code: val }));
    if (val.length > 0) {
      lookupCode(val);
    } else {
      setCodeInfo(null);
    }
  };

  const handleSubmit = async () => {
    if (!form.employee_id || !form.code || !form.amount) {
      toast.error(lang === 'ar' ? 'يرجى ملء جميع الحقول المطلوبة' : 'Please fill required fields');
      return;
    }

    const payload = {
      employee_id: form.employee_id,
      code: parseInt(form.code),
      amount: parseFloat(form.amount),
      description: form.description,
      tx_type: form.tx_type,
    };

    // If code is new, include the definition
    if (codeInfo && !codeInfo.found) {
      if (!newCodeDef.name) {
        toast.error(lang === 'ar' ? 'يرجى تعريف الرمز الجديد' : 'Please define the new code');
        return;
      }
      payload.code_name = newCodeDef.name;
      payload.code_name_ar = newCodeDef.name_ar || newCodeDef.name;
      payload.code_category = newCodeDef.category;
    }

    setSubmitting(true);
    try {
      const res = await api.post('/api/finance/transaction', payload);
      toast.success(`${lang === 'ar' ? 'تم إنشاء العهدة المالية' : 'Financial custody created'}: ${res.data.ref_no}`);
      setDialogOpen(false);
      setForm({ employee_id: '', code: '', amount: '', description: '', tx_type: 'credit' });
      setCodeInfo(null);
      setNewCodeDef({ name: '', name_ar: '', category: 'other' });
      // Refresh codes list
      api.get('/api/finance/codes').then(r => setCodes(r.data)).catch(() => {});
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSubmitting(false); }
  };

  const filteredCodes = codes.filter(c => {
    if (!search) return true;
    return c.name.toLowerCase().includes(search.toLowerCase()) || c.code.toString().includes(search) || c.name_ar?.includes(search);
  });

  return (
    <div className="space-y-6" data-testid="finance-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{t('finance.title')}</h1>
        {canCreate && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="create-finance-tx-btn" className="bg-primary text-primary-foreground">
                <Plus size={16} className="me-1" /> {t('finance.createTransaction')}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader><DialogTitle>{t('finance.createTransaction')}</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>{t('transactions.employee')}</Label>
                  <Select value={form.employee_id} onValueChange={v => setForm(f => ({ ...f, employee_id: v }))}>
                    <SelectTrigger data-testid="finance-employee-select"><SelectValue placeholder={lang === 'ar' ? 'اختر الموظف' : 'Select employee'} /></SelectTrigger>
                    <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{lang === 'ar' ? e.full_name_ar || e.full_name : e.full_name} ({e.employee_number})</SelectItem>)}</SelectContent>
                  </Select>
                </div>

                {/* Manual Code Input */}
                <div>
                  <Label>{lang === 'ar' ? 'رقم الرمز (يدوي)' : 'Code Number (manual)'}</Label>
                  <Input
                    data-testid="finance-code-input"
                    type="number"
                    value={form.code}
                    onChange={e => handleCodeChange(e.target.value)}
                    placeholder={lang === 'ar' ? 'اكتب رقم الرمز...' : 'Type code number...'}
                  />
                  {codeInfo && codeInfo.found && (
                    <div className="mt-1.5 flex items-center gap-1.5 text-emerald-600 bg-emerald-50 dark:bg-emerald-950/20 rounded px-2 py-1">
                      <CheckCircle size={14} />
                      <span className="text-xs font-medium">{codeInfo.code.code} - {lang === 'ar' ? codeInfo.code.name_ar : codeInfo.code.name}</span>
                    </div>
                  )}
                  {codeInfo && !codeInfo.found && (
                    <div className="mt-1.5 text-orange-600 bg-orange-50 dark:bg-orange-950/20 rounded px-2 py-1">
                      <div className="flex items-center gap-1.5 mb-2">
                        <AlertCircle size={14} />
                        <span className="text-xs font-medium">{lang === 'ar' ? 'رمز جديد - يرجى تعريفه' : 'New code - please define it'}</span>
                      </div>
                      <div className="space-y-2">
                        <Input
                          data-testid="new-code-name"
                          placeholder={lang === 'ar' ? 'اسم الرمز (إنجليزي)' : 'Code name (English)'}
                          value={newCodeDef.name}
                          onChange={e => setNewCodeDef(d => ({ ...d, name: e.target.value }))}
                          className="text-xs h-8"
                        />
                        <Input
                          data-testid="new-code-name-ar"
                          placeholder={lang === 'ar' ? 'اسم الرمز (عربي)' : 'Code name (Arabic)'}
                          value={newCodeDef.name_ar}
                          onChange={e => setNewCodeDef(d => ({ ...d, name_ar: e.target.value }))}
                          className="text-xs h-8"
                          dir="rtl"
                        />
                        <Select value={newCodeDef.category} onValueChange={v => setNewCodeDef(d => ({ ...d, category: v }))}>
                          <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="earnings">{t('finance.earnings')}</SelectItem>
                            <SelectItem value="deductions">{t('finance.deductions')}</SelectItem>
                            <SelectItem value="loans">{t('finance.loans')}</SelectItem>
                            <SelectItem value="other">{t('finance.other')}</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>{t('finance.amount')} (SAR)</Label>
                    <Input data-testid="finance-amount" type="number" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
                  </div>
                  <div>
                    <Label>{lang === 'ar' ? 'النوع' : 'Type'}</Label>
                    <Select value={form.tx_type} onValueChange={v => setForm(f => ({ ...f, tx_type: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="credit">{lang === 'ar' ? 'إيداع' : 'Credit'}</SelectItem>
                        <SelectItem value="debit">{lang === 'ar' ? 'خصم' : 'Debit'}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label>{t('finance.description')}</Label>
                  <Input data-testid="finance-description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
                </div>
                <Button data-testid="submit-finance" onClick={handleSubmit} className="w-full bg-primary text-primary-foreground" disabled={submitting}>
                  {submitting ? t('common.loading') : t('common.submit')}
                </Button>
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
                <thead><tr><th>{t('finance.code')}</th><th>Name</th><th className="hidden sm:table-cell">Name (AR)</th><th>Category</th></tr></thead>
                <tbody>
                  {filteredCodes.map(c => (
                    <tr key={c.code}>
                      <td className="font-mono text-xs font-bold">{c.code}</td>
                      <td className="text-sm">{c.name}</td>
                      <td className="hidden sm:table-cell text-sm">{c.name_ar}</td>
                      <td className="text-xs capitalize text-muted-foreground">{c.category}</td>
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
                  <th>{lang === 'ar' ? 'النوع' : 'Type'}</th>
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
                      <td><span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${e.type === 'credit' ? 'bg-emerald-50 text-emerald-700 ring-emerald-300' : 'bg-red-50 text-red-700 ring-red-300'}`}>{e.type === 'credit' ? (lang === 'ar' ? 'إيداع' : 'Credit') : (lang === 'ar' ? 'خصم' : 'Debit')}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
