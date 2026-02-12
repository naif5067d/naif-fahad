import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DollarSign, Plus, Search } from 'lucide-react';
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
  const [submitting, setSubmitting] = useState(false);
  const [selectedEmp, setSelectedEmp] = useState('');
  const [statement, setStatement] = useState([]);

  useEffect(() => {
    api.get('/api/finance/codes').then(r => setCodes(r.data)).catch(() => {});
    api.get('/api/employees').then(r => setEmployees(r.data)).catch(() => {});
  }, []);

  const canCreate = ['sultan', 'naif', 'salah', 'stas'].includes(user?.role);

  const fetchStatement = (empId) => {
    setSelectedEmp(empId);
    if (empId) api.get(`/api/finance/statement/${empId}`).then(r => setStatement(r.data)).catch(() => setStatement([]));
  };

  const handleSubmit = async () => {
    if (!form.employee_id || !form.code || !form.amount) {
      toast.error('Please fill required fields');
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/api/finance/transaction', { ...form, code: parseInt(form.code), amount: parseFloat(form.amount) });
      toast.success(`Finance transaction created: ${res.data.ref_no}`);
      setDialogOpen(false);
      setForm({ employee_id: '', code: '', amount: '', description: '', tx_type: 'credit' });
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
            <DialogContent>
              <DialogHeader><DialogTitle>{t('finance.createTransaction')}</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>{t('transactions.employee')}</Label>
                  <Select value={form.employee_id} onValueChange={v => setForm(f => ({ ...f, employee_id: v }))}>
                    <SelectTrigger data-testid="finance-employee-select"><SelectValue placeholder="Select employee" /></SelectTrigger>
                    <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{e.full_name} ({e.employee_number})</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{t('finance.code')}</Label>
                  <Select value={form.code} onValueChange={v => setForm(f => ({ ...f, code: v }))}>
                    <SelectTrigger data-testid="finance-code-select"><SelectValue placeholder="Select code" /></SelectTrigger>
                    <SelectContent>{codes.map(c => <SelectItem key={c.code} value={String(c.code)}>{c.code} - {c.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>{t('finance.amount')} (SAR)</Label>
                    <Input data-testid="finance-amount" type="number" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
                  </div>
                  <div>
                    <Label>Type</Label>
                    <Select value={form.tx_type} onValueChange={v => setForm(f => ({ ...f, tx_type: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="credit">Credit</SelectItem>
                        <SelectItem value="debit">Debit</SelectItem>
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
              <SelectTrigger data-testid="statement-employee-select"><SelectValue placeholder="Select employee" /></SelectTrigger>
              <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{e.full_name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="hr-table" data-testid="finance-statement-table">
                <thead><tr><th>Date</th><th>Code</th><th>Description</th><th className="text-right">Amount</th><th>Type</th></tr></thead>
                <tbody>
                  {statement.length === 0 ? (
                    <tr><td colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
                  ) : statement.map(e => (
                    <tr key={e.id}>
                      <td className="font-mono text-xs">{e.date?.slice(0, 10)}</td>
                      <td className="text-xs">{e.code} - {e.code_name}</td>
                      <td className="text-sm">{e.description}</td>
                      <td className="text-right font-mono font-medium">{e.amount?.toLocaleString()} SAR</td>
                      <td><span className={`status-badge ${e.type === 'credit' ? 'status-executed' : 'status-rejected'}`}>{e.type}</span></td>
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
