import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, FileSignature, Calculator, Loader2 } from 'lucide-react';
import { formatGregorianHijri } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function ContractsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [contracts, setContracts] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [contractDialog, setContractDialog] = useState(false);
  const [settlementDialog, setSettlementDialog] = useState(false);
  const [cForm, setCForm] = useState({ employee_id: '', contract_type: 'full_time', start_date: '', end_date: '', salary: '', housing_allowance: '0', transport_allowance: '0', other_allowances: '0', probation_months: '3', notice_period_days: '30', notes: '' });
  const [sForm, setSForm] = useState({ employee_id: '', reason: '', settlement_text: '', final_salary: '', leave_encashment: '0', eos_amount: '0', other_payments: '0', deductions: '0' });
  const [submitting, setSubmitting] = useState(false);
  const [calculatingSettlement, setCalculatingSettlement] = useState(false);
  const [settlementPreview, setSettlementPreview] = useState(null);

  const canManage = ['stas', 'sultan', 'naif'].includes(user?.role);
  const canSettle = ['sultan', 'naif'].includes(user?.role);

  useEffect(() => {
    api.get('/api/contracts').then(r => setContracts(r.data)).catch(() => {});
    api.get('/api/employees').then(r => setEmployees(r.data)).catch(() => {});
  }, []);

  // حساب بيانات المخالصة تلقائياً عند اختيار الموظف
  const calculateSettlement = async (employeeId) => {
    if (!employeeId) return;
    setCalculatingSettlement(true);
    setSettlementPreview(null);
    try {
      const res = await api.get(`/api/contracts/settlement/calculate/${employeeId}`);
      setSettlementPreview(res.data);
      setSForm(f => ({
        ...f,
        employee_id: employeeId,
        final_salary: res.data.basic_salary?.toString() || '0',
        leave_encashment: res.data.leave_encashment?.toString() || '0',
        eos_amount: res.data.eos_amount?.toString() || '0',
        deductions: res.data.total_deductions?.toString() || '0'
      }));
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل حساب المخالصة' : 'Failed to calculate settlement');
    } finally {
      setCalculatingSettlement(false);
    }
  };

  const handleCreateContract = async () => {
    setSubmitting(true);
    try {
      const payload = { ...cForm, salary: parseFloat(cForm.salary), housing_allowance: parseFloat(cForm.housing_allowance), transport_allowance: parseFloat(cForm.transport_allowance), other_allowances: parseFloat(cForm.other_allowances), probation_months: parseInt(cForm.probation_months), notice_period_days: parseInt(cForm.notice_period_days) };
      await api.post('/api/contracts', payload);
      toast.success('Contract created');
      setContractDialog(false);
      api.get('/api/contracts').then(r => setContracts(r.data));
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  const handleSettlement = async () => {
    setSubmitting(true);
    try {
      const payload = { ...sForm, final_salary: parseFloat(sForm.final_salary), leave_encashment: parseFloat(sForm.leave_encashment), eos_amount: parseFloat(sForm.eos_amount), other_payments: parseFloat(sForm.other_payments), deductions: parseFloat(sForm.deductions) };
      const res = await api.post('/api/contracts/settlement', payload);
      toast.success(`Settlement created: ${res.data.ref_no}`);
      setSettlementDialog(false);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="space-y-6" data-testid="contracts-page">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-bold tracking-tight">{t('contracts.title')}</h1>
        <div className="flex gap-2">
          {canManage && (
            <Dialog open={contractDialog} onOpenChange={setContractDialog}>
              <DialogTrigger asChild>
                <Button data-testid="create-contract-btn" className="bg-primary text-primary-foreground"><Plus size={16} className="me-1" /> {t('contracts.create')}</Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader><DialogTitle>{t('contracts.create')}</DialogTitle></DialogHeader>
                <div className="space-y-3 max-h-[60vh] overflow-y-auto">
                  <div>
                    <Label>{lang === 'ar' ? 'الموظف' : 'Employee'}</Label>
                    <Select value={cForm.employee_id} onValueChange={v => setCForm(f => ({ ...f, employee_id: v }))}>
                      <SelectTrigger><SelectValue placeholder={lang === 'ar' ? 'اختر' : 'Select'} /></SelectTrigger>
                      <SelectContent>{employees.map(e => <SelectItem key={e.id} value={e.id}>{lang === 'ar' ? e.full_name_ar || e.full_name : e.full_name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>{lang === 'ar' ? 'النوع' : 'Type'}</Label><Select value={cForm.contract_type} onValueChange={v => setCForm(f => ({ ...f, contract_type: v }))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="full_time">{lang === 'ar' ? 'دوام كامل' : 'Full Time'}</SelectItem><SelectItem value="part_time">{lang === 'ar' ? 'دوام جزئي' : 'Part Time'}</SelectItem><SelectItem value="contract">{lang === 'ar' ? 'عقد' : 'Contract'}</SelectItem></SelectContent></Select></div>
                    <div><Label>{lang === 'ar' ? 'الراتب (ريال)' : 'Salary (SAR)'}</Label><Input type="number" value={cForm.salary} onChange={e => setCForm(f => ({ ...f, salary: e.target.value }))} /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>{lang === 'ar' ? 'تاريخ البداية' : 'Start Date'}</Label><Input type="date" value={cForm.start_date} onChange={e => setCForm(f => ({ ...f, start_date: e.target.value }))} /></div>
                    <div><Label>{lang === 'ar' ? 'تاريخ النهاية' : 'End Date'}</Label><Input type="date" value={cForm.end_date} onChange={e => setCForm(f => ({ ...f, end_date: e.target.value }))} /></div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div><Label>{lang === 'ar' ? 'بدل السكن' : 'Housing'}</Label><Input type="number" value={cForm.housing_allowance} onChange={e => setCForm(f => ({ ...f, housing_allowance: e.target.value }))} /></div>
                    <div><Label>{lang === 'ar' ? 'بدل النقل' : 'Transport'}</Label><Input type="number" value={cForm.transport_allowance} onChange={e => setCForm(f => ({ ...f, transport_allowance: e.target.value }))} /></div>
                    <div><Label>{lang === 'ar' ? 'أخرى' : 'Other'}</Label><Input type="number" value={cForm.other_allowances} onChange={e => setCForm(f => ({ ...f, other_allowances: e.target.value }))} /></div>
                  </div>
                  <Button data-testid="submit-contract" onClick={handleCreateContract} className="w-full bg-primary text-primary-foreground" disabled={submitting}>
                    {submitting ? t('common.loading') : t('common.submit')}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          )}
          {canSettle && (
            <Dialog open={settlementDialog} onOpenChange={(open) => { setSettlementDialog(open); if (!open) setSettlementPreview(null); }}>
              <DialogTrigger asChild>
                <Button data-testid="create-settlement-btn" variant="destructive"><FileSignature size={16} className="me-1" /> {t('contracts.settlement')}</Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader><DialogTitle>{lang === 'ar' ? 'إنهاء خدمات / مخالصة' : 'Settlement / Final Clearance'}</DialogTitle></DialogHeader>
                <div className="space-y-4 max-h-[70vh] overflow-y-auto">
                  {/* اختيار الموظف مع زر الحساب التلقائي */}
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <Label>{lang === 'ar' ? 'الموظف' : 'Employee'}</Label>
                      <Select value={sForm.employee_id} onValueChange={v => { setSForm(f => ({ ...f, employee_id: v })); calculateSettlement(v); }}>
                        <SelectTrigger><SelectValue placeholder={lang === 'ar' ? 'اختر الموظف' : 'Select Employee'} /></SelectTrigger>
                        <SelectContent>{employees.filter(e => e.is_active).map(e => <SelectItem key={e.id} value={e.id}>{lang === 'ar' ? e.full_name_ar : e.full_name}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    {sForm.employee_id && (
                      <Button variant="outline" onClick={() => calculateSettlement(sForm.employee_id)} disabled={calculatingSettlement} className="mt-6">
                        {calculatingSettlement ? <Loader2 size={16} className="animate-spin" /> : <Calculator size={16} />}
                      </Button>
                    )}
                  </div>

                  {/* معاينة الحساب التلقائي */}
                  {settlementPreview && (
                    <div className="p-4 bg-slate-50 rounded-lg border space-y-3">
                      <h3 className="font-semibold text-sm flex items-center gap-2">
                        <Calculator size={16} />
                        {lang === 'ar' ? 'الحساب التلقائي' : 'Auto Calculation'}
                      </h3>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>{lang === 'ar' ? 'سنوات الخدمة:' : 'Years of Service:'}</div>
                        <div className="font-medium">{settlementPreview.years_of_service} {lang === 'ar' ? 'سنة' : 'years'}</div>
                        <div>{lang === 'ar' ? 'رصيد الإجازات:' : 'Leave Balance:'}</div>
                        <div className="font-medium">{settlementPreview.leave_balance_days} {lang === 'ar' ? 'يوم' : 'days'}</div>
                      </div>
                      {settlementPreview.deduction_details?.length > 0 && (
                        <div className="border-t pt-2 mt-2">
                          <p className="text-xs font-semibold text-destructive mb-1">{lang === 'ar' ? 'الخصومات المسجلة:' : 'Recorded Deductions:'}</p>
                          {settlementPreview.deduction_details.map((d, i) => (
                            <div key={i} className="text-xs flex justify-between text-muted-foreground">
                              <span>{d.reason || d.date}</span>
                              <span className="text-destructive">-{d.amount} SAR</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="border-t pt-2 flex justify-between font-bold">
                        <span>{lang === 'ar' ? 'صافي المخالصة:' : 'Net Settlement:'}</span>
                        <span className="text-[hsl(var(--success))]">{settlementPreview.net_settlement?.toLocaleString()} SAR</span>
                      </div>
                    </div>
                  )}

                  <div><Label>{lang === 'ar' ? 'السبب' : 'Reason'}</Label><Input value={sForm.reason} onChange={e => setSForm(f => ({ ...f, reason: e.target.value }))} /></div>
                  <div><Label>{lang === 'ar' ? 'نص المخالصة' : 'Settlement Text'}</Label><Input value={sForm.settlement_text} onChange={e => setSForm(f => ({ ...f, settlement_text: e.target.value }))} /></div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>{lang === 'ar' ? 'الراتب النهائي' : 'Final Salary'}</Label>
                      <Input type="number" value={sForm.final_salary} onChange={e => setSForm(f => ({ ...f, final_salary: e.target.value }))} />
                    </div>
                    <div>
                      <Label>{lang === 'ar' ? 'بدل الإجازات' : 'Leave Encashment'}</Label>
                      <Input type="number" value={sForm.leave_encashment} onChange={e => setSForm(f => ({ ...f, leave_encashment: e.target.value }))} />
                    </div>
                    <div>
                      <Label>{lang === 'ar' ? 'مكافأة نهاية الخدمة' : 'EOS Amount'}</Label>
                      <Input type="number" value={sForm.eos_amount} onChange={e => setSForm(f => ({ ...f, eos_amount: e.target.value }))} />
                    </div>
                    <div>
                      <Label>{lang === 'ar' ? 'مدفوعات أخرى' : 'Other Payments'}</Label>
                      <Input type="number" value={sForm.other_payments} onChange={e => setSForm(f => ({ ...f, other_payments: e.target.value }))} />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-destructive">{lang === 'ar' ? 'الخصومات' : 'Deductions'}</Label>
                      <Input type="number" value={sForm.deductions} onChange={e => setSForm(f => ({ ...f, deductions: e.target.value }))} className="border-destructive/30" />
                    </div>
                  </div>

                  {/* صافي المخالصة */}
                  <div className="p-3 bg-[hsl(var(--success)/0.1)] rounded-lg border border-[hsl(var(--success)/0.3)] flex justify-between items-center">
                    <span className="font-semibold">{lang === 'ar' ? 'الإجمالي:' : 'Total:'}</span>
                    <span className="text-xl font-bold text-[hsl(var(--success))]">
                      {(parseFloat(sForm.final_salary || 0) + parseFloat(sForm.leave_encashment || 0) + parseFloat(sForm.eos_amount || 0) + parseFloat(sForm.other_payments || 0) - parseFloat(sForm.deductions || 0)).toLocaleString()} SAR
                    </span>
                  </div>

                  <Button data-testid="submit-settlement" onClick={handleSettlement} variant="destructive" className="w-full" disabled={submitting || !sForm.employee_id}>
                    {submitting ? t('common.loading') : (lang === 'ar' ? 'إنشاء طلب المخالصة' : 'Create Settlement Request')}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="hr-table" data-testid="contracts-table">
            <thead><tr><th>Employee</th><th>{t('contracts.type')}</th><th>V</th><th>{t('contracts.salary')}</th><th className="hidden sm:table-cell">{t('contracts.startDate')}</th><th className="hidden sm:table-cell">Snapshot</th></tr></thead>
            <tbody>
              {contracts.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
              ) : contracts.map(c => (
                <tr key={c.id}>
                  <td className="text-sm">{employees.find(e => e.id === c.employee_id)?.full_name || c.employee_id}</td>
                  <td className="text-sm capitalize">{c.contract_type?.replace('_', ' ')}</td>
                  <td className="font-mono text-xs">v{c.version}</td>
                  <td className="font-mono text-sm text-right">{c.salary?.toLocaleString()} SAR</td>
                  <td className="hidden sm:table-cell text-xs">{formatGregorianHijri(c.start_date).combined}</td>
                  <td className="hidden sm:table-cell">{c.is_snapshot ? <span className="status-badge status-executed">Snapshot</span> : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
