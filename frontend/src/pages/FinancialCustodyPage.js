import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, CheckCircle, AlertCircle, ArrowLeft, Trash2, Send, Check, X, Loader2, ChevronRight, Clock, FileText, DollarSign } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

const STATUS_COLORS = {
  created: { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-700 dark:text-slate-300', ring: 'ring-slate-300' },
  active: { bg: 'bg-blue-50 dark:bg-blue-950', text: 'text-blue-700 dark:text-blue-300', ring: 'ring-blue-300' },
  pending_audit: { bg: 'bg-amber-50 dark:bg-amber-950', text: 'text-amber-700 dark:text-amber-300', ring: 'ring-amber-300' },
  pending_approval: { bg: 'bg-orange-50 dark:bg-orange-950', text: 'text-orange-700 dark:text-orange-300', ring: 'ring-orange-300' },
  pending_stas: { bg: 'bg-purple-50 dark:bg-purple-950', text: 'text-purple-700 dark:text-purple-300', ring: 'ring-purple-300' },
  executed: { bg: 'bg-emerald-50 dark:bg-emerald-950', text: 'text-emerald-700 dark:text-emerald-300', ring: 'ring-emerald-300' },
};

const STATUS_LABELS = {
  ar: { created: 'جديدة', active: 'نشطة', pending_audit: 'بانتظار التدقيق', pending_approval: 'بانتظار الاعتماد', pending_stas: 'بانتظار التنفيذ', executed: 'منفذة' },
  en: { created: 'Created', active: 'Active', pending_audit: 'Pending Audit', pending_approval: 'Pending Approval', pending_stas: 'Pending STAS', executed: 'Executed' },
};

export default function FinancialCustodyPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [custodies, setCustodies] = useState([]);
  const [selected, setSelected] = useState(null); // Full custody detail
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ title: '', title_ar: '', total_amount: '' });
  const [expForm, setExpForm] = useState({ code: '', description: '', amount: '' });
  const [codeInfo, setCodeInfo] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [view, setView] = useState('list'); // list | detail

  const role = user?.role;
  const canCreate = ['sultan', 'naif', 'mohammed', 'stas'].includes(role);
  const canAddExpense = ['sultan', 'stas'].includes(role);
  const canAudit = ['salah', 'stas'].includes(role);
  const canApprove = ['mohammed', 'stas'].includes(role);
  const canExecute = role === 'stas';

  const fetchList = () => api.get('/api/financial-custody').then(r => setCustodies(r.data)).catch(() => {});
  const fetchDetail = (id) => api.get(`/api/financial-custody/${id}`).then(r => { setSelected(r.data); setView('detail'); }).catch(() => {});

  useEffect(() => { fetchList(); }, []);

  const lookupCode = useCallback(async (val) => {
    if (!val || isNaN(parseInt(val))) { setCodeInfo(null); return; }
    try {
      const res = await api.get(`/api/finance/codes/lookup/${parseInt(val)}`);
      setCodeInfo(res.data);
      if (res.data.found) setExpForm(f => ({ ...f, description: lang === 'ar' ? res.data.code.name_ar : res.data.code.name }));
    } catch { setCodeInfo(null); }
  }, [lang]);

  const handleCreate = async () => {
    if (!form.title || !form.total_amount) return toast.error(lang === 'ar' ? 'يرجى ملء الحقول' : 'Fill required fields');
    setSubmitting(true);
    try {
      const res = await api.post('/api/financial-custody', { ...form, total_amount: parseFloat(form.total_amount) });
      toast.success(`${lang === 'ar' ? 'تم إنشاء العهدة' : 'Custody created'}: ${res.data.custody_number}`);
      setCreateOpen(false); setForm({ title: '', title_ar: '', total_amount: '' }); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleReceive = async () => {
    setSubmitting(true);
    try {
      await api.post(`/api/financial-custody/${selected.id}/receive`);
      toast.success(lang === 'ar' ? 'تم الاستلام' : 'Received');
      fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleAddExpense = async () => {
    if (!expForm.code || !expForm.amount) return toast.error(lang === 'ar' ? 'أدخل الكود والمبلغ' : 'Enter code and amount');
    setSubmitting(true);
    try {
      await api.post(`/api/financial-custody/${selected.id}/expense`, { code: parseInt(expForm.code), description: expForm.description, amount: parseFloat(expForm.amount) });
      toast.success(lang === 'ar' ? 'تمت الإضافة' : 'Expense added');
      setExpForm({ code: '', description: '', amount: '' }); setCodeInfo(null); fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleRemoveExpense = async (expId) => {
    try {
      await api.delete(`/api/financial-custody/${selected.id}/expense/${expId}`);
      fetchDetail(selected.id);
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
  };

  const handleSubmitAudit = async () => {
    setSubmitting(true);
    try {
      await api.post(`/api/financial-custody/${selected.id}/submit-audit`);
      toast.success(lang === 'ar' ? 'تم الإرسال للتدقيق' : 'Sent for audit');
      fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleAudit = async (action) => {
    setSubmitting(true);
    try {
      await api.post(`/api/financial-custody/${selected.id}/audit`, { action });
      toast.success(action === 'approve' ? (lang === 'ar' ? 'تم التدقيق والاعتماد' : 'Audited') : (lang === 'ar' ? 'تم الإرجاع' : 'Returned'));
      fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleApprove = async (action) => {
    setSubmitting(true);
    try {
      await api.post(`/api/financial-custody/${selected.id}/approve`, { action });
      toast.success(action === 'approve' ? (lang === 'ar' ? 'تم الاعتماد' : 'Approved') : (lang === 'ar' ? 'تم الإرجاع' : 'Returned'));
      fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleExecute = async () => {
    setSubmitting(true);
    try {
      const res = await api.post(`/api/financial-custody/${selected.id}/execute`);
      toast.success(res.data.message);
      fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  // === DETAIL VIEW ===
  if (view === 'detail' && selected) {
    const sc = STATUS_COLORS[selected.status] || STATUS_COLORS.created;
    const totalBudget = selected.total_amount + (selected.carried_amount || 0);
    const pctSpent = totalBudget > 0 ? Math.min((selected.total_spent / totalBudget) * 100, 100) : 0;

    return (
      <div className="space-y-5" data-testid="custody-detail">
        <button onClick={() => { setView('list'); setSelected(null); }} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors" data-testid="back-to-list">
          <ArrowLeft size={16} /> {lang === 'ar' ? 'العودة' : 'Back'}
        </button>

        {/* Header Card */}
        <Card className="border-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground font-mono">{lang === 'ar' ? 'عهدة رقم' : 'Custody'} #{selected.custody_number}</p>
                <CardTitle className="text-xl">{lang === 'ar' ? selected.title_ar || selected.title : selected.title}</CardTitle>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ring-1 ring-inset ${sc.bg} ${sc.text} ${sc.ring}`} data-testid="custody-status">
                {STATUS_LABELS[lang]?.[selected.status] || selected.status}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الميزانية' : 'Budget'}</p>
                <p className="text-lg font-bold text-foreground">{totalBudget.toLocaleString()} <span className="text-xs">SAR</span></p>
                {selected.carried_amount > 0 && <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'مرحّل' : 'Carried'}: {selected.carried_amount.toLocaleString()}</p>}
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'المصروف' : 'Spent'}</p>
                <p className="text-lg font-bold text-red-600">{selected.total_spent.toLocaleString()} <span className="text-xs">SAR</span></p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'المتبقي' : 'Remaining'}</p>
                <p className="text-lg font-bold text-emerald-600">{selected.remaining.toLocaleString()} <span className="text-xs">SAR</span></p>
              </div>
            </div>
            {/* Progress bar */}
            <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-red-500 rounded-full transition-all" style={{ width: `${pctSpent}%` }} />
            </div>
            <p className="text-[10px] text-muted-foreground text-center mt-1">{pctSpent.toFixed(0)}% {lang === 'ar' ? 'مصروف' : 'spent'}</p>
          </CardContent>
        </Card>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {selected.status === 'created' && canCreate && (
            <Button onClick={handleReceive} disabled={submitting} data-testid="receive-btn" className="bg-blue-600 hover:bg-blue-700 text-white">
              {submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : <Check size={14} className="me-1" />}
              {lang === 'ar' ? 'استلام العهدة' : 'Receive Custody'}
            </Button>
          )}
          {selected.status === 'active' && canAddExpense && (
            <Button onClick={handleSubmitAudit} disabled={submitting || !selected.expenses?.length} variant="outline" data-testid="submit-audit-btn" className="border-amber-400 text-amber-700 hover:bg-amber-50">
              <Send size={14} className="me-1" /> {lang === 'ar' ? 'إرسال للتدقيق' : 'Submit for Audit'}
            </Button>
          )}
          {selected.status === 'pending_audit' && canAudit && (
            <div className="flex gap-2">
              <Button onClick={() => handleAudit('approve')} disabled={submitting} data-testid="audit-approve-btn" className="bg-emerald-600 text-white"><Check size={14} className="me-1" />{lang === 'ar' ? 'اعتماد التدقيق' : 'Approve Audit'}</Button>
              <Button onClick={() => handleAudit('reject')} disabled={submitting} variant="destructive" data-testid="audit-reject-btn"><X size={14} className="me-1" />{lang === 'ar' ? 'إرجاع' : 'Return'}</Button>
            </div>
          )}
          {selected.status === 'pending_approval' && canApprove && (
            <div className="flex gap-2">
              <Button onClick={() => handleApprove('approve')} disabled={submitting} data-testid="ceo-approve-btn" className="bg-emerald-600 text-white"><Check size={14} className="me-1" />{lang === 'ar' ? 'اعتماد نهائي' : 'Final Approve'}</Button>
              <Button onClick={() => handleApprove('reject')} disabled={submitting} variant="destructive" data-testid="ceo-reject-btn"><X size={14} className="me-1" />{lang === 'ar' ? 'إرجاع' : 'Return'}</Button>
            </div>
          )}
          {selected.status === 'pending_stas' && canExecute && (
            <Button onClick={handleExecute} disabled={submitting} data-testid="execute-btn" className="bg-purple-600 text-white">
              {submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : <Check size={14} className="me-1" />}
              {lang === 'ar' ? 'تنفيذ' : 'Execute'}
              {selected.remaining > 0 && <span className="ms-1 text-xs opacity-80">({lang === 'ar' ? `ترحيل ${selected.remaining} ريال` : `Carry ${selected.remaining} SAR`})</span>}
            </Button>
          )}
        </div>

        {/* Expense Sheet - Excel-like */}
        <div>
          <h3 className="text-base font-semibold mb-2 flex items-center gap-2"><DollarSign size={16} /> {lang === 'ar' ? 'جدول الصرف' : 'Expense Sheet'}</h3>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="hr-table" data-testid="expense-table">
                <thead><tr>
                  <th className="w-10">#</th>
                  <th>{lang === 'ar' ? 'الكود' : 'Code'}</th>
                  <th>{lang === 'ar' ? 'البيان' : 'Description'}</th>
                  <th className="text-right">{lang === 'ar' ? 'المبلغ' : 'Amount'}</th>
                  <th className="text-right">{lang === 'ar' ? 'المتبقي بعد' : 'Remaining'}</th>
                  {selected.status === 'active' && canAddExpense && <th className="w-10"></th>}
                </tr></thead>
                <tbody>
                  {selected.expenses?.length === 0 && (
                    <tr><td colSpan={selected.status === 'active' ? 6 : 5} className="text-center py-6 text-muted-foreground text-sm">{lang === 'ar' ? 'لا توجد مصروفات بعد' : 'No expenses yet'}</td></tr>
                  )}
                  {(() => {
                    let running = totalBudget;
                    return selected.expenses?.map((exp, i) => {
                      running -= exp.amount;
                      return (
                        <tr key={exp.id} data-testid={`expense-row-${i}`}>
                          <td className="text-xs text-muted-foreground font-mono">{i + 1}</td>
                          <td><span className="font-mono text-xs font-bold bg-muted px-1.5 py-0.5 rounded">{exp.code}</span> <span className="text-xs text-muted-foreground">{lang === 'ar' ? exp.code_name_ar : exp.code_name}</span></td>
                          <td className="text-sm">{exp.description}{exp.edited_by && <span className="text-[10px] text-amber-600 ms-1">({lang === 'ar' ? 'معدّل' : 'edited'})</span>}</td>
                          <td className="text-right font-mono text-sm font-medium text-red-600">-{exp.amount.toLocaleString()}</td>
                          <td className="text-right font-mono text-sm text-muted-foreground">{running.toLocaleString()}</td>
                          {selected.status === 'active' && canAddExpense && (
                            <td><button onClick={() => handleRemoveExpense(exp.id)} className="text-red-400 hover:text-red-600"><Trash2 size={14} /></button></td>
                          )}
                        </tr>
                      );
                    });
                  })()}
                  {/* Totals row */}
                  {selected.expenses?.length > 0 && (
                    <tr className="bg-muted/50 font-semibold">
                      <td></td>
                      <td colSpan={2} className="text-sm">{lang === 'ar' ? 'الإجمالي' : 'Total'}</td>
                      <td className="text-right font-mono text-sm text-red-700">-{selected.total_spent.toLocaleString()}</td>
                      <td className="text-right font-mono text-sm text-emerald-700">{selected.remaining.toLocaleString()}</td>
                      {selected.status === 'active' && canAddExpense && <td></td>}
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Add Expense Form (inline, only when active) */}
        {selected.status === 'active' && canAddExpense && (
          <Card className="border-dashed border-2 border-blue-200 dark:border-blue-900 bg-blue-50/30 dark:bg-blue-950/20">
            <CardContent className="pt-4">
              <p className="text-sm font-medium mb-3">{lang === 'ar' ? 'إضافة مصروف' : 'Add Expense'}</p>
              <div className="flex gap-2 items-end flex-wrap">
                <div className="w-24">
                  <Label className="text-xs">{lang === 'ar' ? 'الكود' : 'Code'}</Label>
                  <Input data-testid="exp-code" type="number" value={expForm.code} onChange={e => { setExpForm(f => ({ ...f, code: e.target.value })); lookupCode(e.target.value); }} className="h-9 text-sm font-mono" placeholder="1" />
                </div>
                <div className="flex-1 min-w-[140px]">
                  <Label className="text-xs">{lang === 'ar' ? 'البيان' : 'Description'}</Label>
                  <div className="relative">
                    <Input data-testid="exp-desc" value={expForm.description} onChange={e => setExpForm(f => ({ ...f, description: e.target.value }))} className="h-9 text-sm" />
                    {codeInfo?.found && <CheckCircle size={14} className="absolute right-2 rtl:right-auto rtl:left-2 top-1/2 -translate-y-1/2 text-emerald-500" />}
                    {codeInfo && !codeInfo.found && <AlertCircle size={14} className="absolute right-2 rtl:right-auto rtl:left-2 top-1/2 -translate-y-1/2 text-amber-500" />}
                  </div>
                </div>
                <div className="w-28">
                  <Label className="text-xs">{lang === 'ar' ? 'المبلغ' : 'Amount'}</Label>
                  <Input data-testid="exp-amount" type="number" value={expForm.amount} onChange={e => setExpForm(f => ({ ...f, amount: e.target.value }))} className="h-9 text-sm font-mono" placeholder="0" />
                </div>
                <Button onClick={handleAddExpense} disabled={submitting} data-testid="add-expense-btn" size="sm" className="h-9 bg-blue-600 text-white">
                  <Plus size={14} className="me-1" /> {lang === 'ar' ? 'إضافة' : 'Add'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Timeline */}
        <div>
          <h3 className="text-base font-semibold mb-2 flex items-center gap-2"><Clock size={16} /> {lang === 'ar' ? 'السجل الزمني' : 'Timeline'}</h3>
          <div className="space-y-2">
            {selected.timeline?.map((ev, i) => (
              <div key={i} className="flex items-start gap-3 text-sm border-s-2 border-border ps-3 py-1" data-testid={`timeline-${i}`}>
                <div className="flex-1">
                  <p className="font-medium text-xs">{ev.actor_name} <span className="text-muted-foreground">- {ev.event}</span></p>
                  <p className="text-xs text-muted-foreground">{ev.note}</p>
                </div>
                <p className="text-[10px] text-muted-foreground whitespace-nowrap">{ev.timestamp?.slice(0, 16).replace('T', ' ')}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // === LIST VIEW ===
  return (
    <div className="space-y-5" data-testid="financial-custody-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{lang === 'ar' ? 'العهد المالية (60 كود)' : 'Financial Custody (60 Code)'}</h1>
        {canCreate && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button data-testid="create-custody-btn" className="bg-primary text-primary-foreground"><Plus size={16} className="me-1" /> {lang === 'ar' ? 'عهدة جديدة' : 'New Custody'}</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>{lang === 'ar' ? 'إنشاء عهدة مالية' : 'Create Financial Custody'}</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label>{lang === 'ar' ? 'عنوان العهدة' : 'Custody Title'}</Label><Input data-testid="custody-title" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
                <div><Label>{lang === 'ar' ? 'العنوان (عربي)' : 'Title (Arabic)'}</Label><Input data-testid="custody-title-ar" value={form.title_ar} onChange={e => setForm(f => ({ ...f, title_ar: e.target.value }))} dir="rtl" /></div>
                <div><Label>{lang === 'ar' ? 'المبلغ (ريال)' : 'Amount (SAR)'}</Label><Input data-testid="custody-amount" type="number" value={form.total_amount} onChange={e => setForm(f => ({ ...f, total_amount: e.target.value }))} /></div>
                <Button onClick={handleCreate} disabled={submitting} data-testid="submit-create" className="w-full">{submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}{lang === 'ar' ? 'إنشاء' : 'Create'}</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Custody Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {custodies.length === 0 && <p className="col-span-full text-center text-muted-foreground py-12">{lang === 'ar' ? 'لا توجد عهد' : 'No custodies yet'}</p>}
        {custodies.map(c => {
          const sc = STATUS_COLORS[c.status] || STATUS_COLORS.created;
          const budget = c.total_amount + (c.carried_amount || 0);
          const pct = budget > 0 ? Math.min((c.total_spent / budget) * 100, 100) : 0;
          return (
            <Card key={c.id} className="cursor-pointer hover:shadow-md transition-shadow border" onClick={() => fetchDetail(c.id)} data-testid={`custody-card-${c.custody_number}`}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <p className="font-mono text-xs text-muted-foreground">#{c.custody_number}</p>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1 ring-inset ${sc.bg} ${sc.text} ${sc.ring}`}>{STATUS_LABELS[lang]?.[c.status] || c.status}</span>
                </div>
                <CardTitle className="text-sm mt-1">{lang === 'ar' ? c.title_ar || c.title : c.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-muted-foreground">{lang === 'ar' ? 'المصروف' : 'Spent'}: <span className="font-mono text-red-600">{c.total_spent.toLocaleString()}</span></span>
                  <span className="text-muted-foreground">{lang === 'ar' ? 'المتبقي' : 'Rem'}: <span className="font-mono text-emerald-600">{c.remaining.toLocaleString()}</span></span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                </div>
                <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                  <span>{budget.toLocaleString()} SAR</span>
                  <span className="flex items-center gap-1"><FileText size={12} /> {c.expenses?.length || 0}</span>
                </div>
                {c.carried_amount > 0 && <p className="text-[10px] text-blue-600 mt-1">{lang === 'ar' ? `مرحّل: ${c.carried_amount.toLocaleString()} ريال` : `Carried: ${c.carried_amount.toLocaleString()} SAR`}</p>}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
