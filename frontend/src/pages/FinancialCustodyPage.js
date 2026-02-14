import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, CheckCircle, AlertCircle, ArrowLeft, Trash2, Send, Check, X, Loader2, Clock, DollarSign, Eye, ChevronRight } from 'lucide-react';
import { formatGregorianHijriDateTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

const STATUS_MAP = {
  ar: { created: 'جديدة', active: 'نشطة', pending_audit: 'بانتظار التدقيق', pending_approval: 'بانتظار الاعتماد', pending_stas: 'بانتظار التنفيذ', executed: 'منفذة' },
  en: { created: 'Created', active: 'Active', pending_audit: 'Pending Audit', pending_approval: 'Pending Approval', pending_stas: 'Pending STAS', executed: 'Executed' },
};

const STATUS_STYLES = {
  created: 'bg-slate-100 text-slate-700 ring-slate-300 dark:bg-slate-800 dark:text-slate-300',
  active: 'bg-blue-50 text-blue-700 ring-blue-300 dark:bg-blue-950 dark:text-blue-300',
  pending_audit: 'bg-amber-50 text-amber-700 ring-amber-300 dark:bg-amber-950 dark:text-amber-300',
  pending_approval: 'bg-orange-50 text-orange-700 ring-orange-300 dark:bg-orange-950 dark:text-orange-300',
  pending_stas: 'bg-purple-50 text-purple-700 ring-purple-300 dark:bg-purple-950 dark:text-purple-300',
  executed: 'bg-emerald-50 text-emerald-700 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-300',
};

const TIMELINE_COLORS = {
  created: 'bg-slate-400', received: 'bg-blue-500', expense_added: 'bg-red-400', expense_removed: 'bg-red-300',
  submitted_audit: 'bg-amber-500', audited: 'bg-teal-500', audit_rejected: 'bg-red-500',
  approved: 'bg-green-500', approval_rejected: 'bg-red-500', executed: 'bg-emerald-600',
};

export default function FinancialCustodyPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [custodies, setCustodies] = useState([]);
  const [summary, setSummary] = useState({});
  const [selected, setSelected] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ title: '', title_ar: '', total_amount: '' });
  const [expForm, setExpForm] = useState({ code: '', description: '', amount: '' });
  const [codeInfo, setCodeInfo] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [view, setView] = useState('list');
  const [tab, setTab] = useState('all');

  const role = user?.role;
  const canCreate = ['sultan', 'naif', 'mohammed', 'stas'].includes(role);
  const canAddExpense = ['sultan', 'stas'].includes(role);
  const canAudit = ['salah', 'stas'].includes(role);
  const canApprove = ['mohammed', 'stas'].includes(role);
  const canExecute = role === 'stas';

  const fetchList = () => {
    api.get('/api/financial-custody').then(r => setCustodies(r.data)).catch(() => {});
    api.get('/api/financial-custody/summary/totals').then(r => setSummary(r.data)).catch(() => {});
  };
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

  const doAction = async (url, method = 'post', body = null) => {
    setSubmitting(true);
    try {
      const res = method === 'delete' ? await api.delete(url) : await api.post(url, body);
      toast.success(res.data?.message || 'OK');
      if (selected) fetchDetail(selected.id);
      fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleCreate = async () => {
    if (!form.title || !form.total_amount) return toast.error(lang === 'ar' ? 'يرجى ملء الحقول' : 'Fill fields');
    setSubmitting(true);
    try {
      await api.post('/api/financial-custody', { ...form, total_amount: parseFloat(form.total_amount) });
      toast.success(lang === 'ar' ? 'تم إنشاء العهدة' : 'Created');
      setCreateOpen(false); setForm({ title: '', title_ar: '', total_amount: '' }); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const handleAddExpense = async () => {
    if (!expForm.code || !expForm.amount) return toast.error(lang === 'ar' ? 'أدخل الكود والمبلغ' : 'Enter code & amount');
    setSubmitting(true);
    try {
      await api.post(`/api/financial-custody/${selected.id}/expense`, { code: parseInt(expForm.code), description: expForm.description, amount: parseFloat(expForm.amount) });
      setExpForm({ code: '', description: '', amount: '' }); setCodeInfo(null); fetchDetail(selected.id); fetchList();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSubmitting(false); }
  };

  const filtered = custodies.filter(c => {
    if (tab === 'all') return true;
    if (tab === 'active') return ['created', 'active'].includes(c.status);
    if (tab === 'pending') return c.status.startsWith('pending');
    if (tab === 'executed') return c.status === 'executed';
    return true;
  });

  // === DETAIL VIEW ===
  if (view === 'detail' && selected) {
    const budget = selected.total_amount + (selected.carried_amount || 0);
    const pct = budget > 0 ? Math.min((selected.total_spent / budget) * 100, 100) : 0;

    return (
      <div className="space-y-5" data-testid="custody-detail">
        <button onClick={() => { setView('list'); setSelected(null); }} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground" data-testid="back-to-list">
          <ArrowLeft size={16} /> {lang === 'ar' ? 'العودة للقائمة' : 'Back to list'}
        </button>

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-1 rounded">#{selected.custody_number}</span>
              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ring-1 ring-inset ${STATUS_STYLES[selected.status] || ''}`}>{STATUS_MAP[lang]?.[selected.status]}</span>
            </div>
            <h2 className="text-xl font-bold mt-1">{lang === 'ar' ? selected.title_ar || selected.title : selected.title}</h2>
          </div>
          <div className="flex items-center gap-6 text-center">
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">{lang === 'ar' ? 'الميزانية' : 'Budget'}</p><p className="text-lg font-bold font-mono">{budget.toLocaleString()}</p></div>
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">{lang === 'ar' ? 'المصروف' : 'Spent'}</p><p className="text-lg font-bold font-mono text-red-600">{selected.total_spent.toLocaleString()}</p></div>
            <div><p className="text-[10px] text-muted-foreground uppercase tracking-wider">{lang === 'ar' ? 'المتبقي' : 'Remaining'}</p><p className="text-lg font-bold font-mono text-emerald-600">{selected.remaining.toLocaleString()}</p></div>
          </div>
        </div>

        {selected.carried_amount > 0 && (
          <div className="text-xs bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 px-3 py-1.5 rounded-md">
            {lang === 'ar' ? `مرحّل من العهدة السابقة: ${selected.carried_amount.toLocaleString()} ريال` : `Carried from previous: ${selected.carried_amount.toLocaleString()} SAR`}
          </div>
        )}

        {/* Progress */}
        <div className="h-2 bg-muted rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-red-400 to-red-600 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} /></div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          {selected.status === 'created' && canCreate && <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/receive`)} disabled={submitting} size="sm" className="bg-blue-600 text-white"><Check size={14} className="me-1" />{lang === 'ar' ? 'استلام' : 'Receive'}</Button>}
          {selected.status === 'active' && canAddExpense && <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/submit-audit`)} disabled={submitting || !selected.expenses?.length} size="sm" variant="outline" className="border-amber-400 text-amber-700"><Send size={14} className="me-1" />{lang === 'ar' ? 'إرسال للتدقيق' : 'Submit Audit'}</Button>}
          {selected.status === 'pending_audit' && canAudit && <>
            <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/audit`, 'post', { action: 'approve' })} disabled={submitting} size="sm" className="bg-teal-600 text-white"><Check size={14} className="me-1" />{lang === 'ar' ? 'اعتماد التدقيق' : 'Approve'}</Button>
            <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/audit`, 'post', { action: 'reject' })} disabled={submitting} size="sm" variant="destructive"><X size={14} className="me-1" />{lang === 'ar' ? 'إرجاع' : 'Return'}</Button>
          </>}
          {selected.status === 'pending_approval' && canApprove && <>
            <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/approve`, 'post', { action: 'approve' })} disabled={submitting} size="sm" className="bg-emerald-600 text-white"><Check size={14} className="me-1" />{lang === 'ar' ? 'اعتماد نهائي' : 'Approve'}</Button>
            <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/approve`, 'post', { action: 'reject' })} disabled={submitting} size="sm" variant="destructive"><X size={14} className="me-1" />{lang === 'ar' ? 'إرجاع' : 'Return'}</Button>
          </>}
          {selected.status === 'pending_stas' && canExecute && <Button onClick={() => doAction(`/api/financial-custody/${selected.id}/execute`)} disabled={submitting} size="sm" className="bg-purple-600 text-white"><Check size={14} className="me-1" />{lang === 'ar' ? 'تنفيذ' : 'Execute'}{selected.remaining > 0 && ` (${lang === 'ar' ? 'ترحيل' : 'carry'} ${selected.remaining})`}</Button>}
        </div>

        {/* EXPENSE SHEET - Excel Style */}
        <div className="border border-border rounded-lg overflow-hidden shadow-sm">
          <div className="bg-muted/60 px-4 py-2 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold flex items-center gap-2"><DollarSign size={15} /> {lang === 'ar' ? 'جدول الصرف' : 'Expense Sheet'}</h3>
            <span className="text-xs text-muted-foreground font-mono">{selected.expenses?.length || 0} {lang === 'ar' ? 'بند' : 'items'}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="expense-table">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/50 text-xs">
                  <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground w-10">#</th>
                  <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground w-20">{lang === 'ar' ? 'الكود' : 'Code'}</th>
                  <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'البيان' : 'Description'}</th>
                  <th className="px-3 py-2.5 text-end font-semibold text-muted-foreground w-28">{lang === 'ar' ? 'المبلغ' : 'Amount'}</th>
                  <th className="px-3 py-2.5 text-end font-semibold text-muted-foreground w-28">{lang === 'ar' ? 'المتبقي' : 'Balance'}</th>
                  {selected.status === 'active' && canAddExpense && <th className="px-2 py-2.5 w-8"></th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {selected.expenses?.length === 0 && <tr><td colSpan={6} className="text-center py-10 text-muted-foreground">{lang === 'ar' ? 'لا مصروفات' : 'No expenses'}</td></tr>}
                {(() => {
                  let running = budget;
                  return selected.expenses?.map((exp, i) => {
                    running -= exp.amount;
                    return (
                      <tr key={exp.id} className="hover:bg-muted/30 transition-colors" data-testid={`expense-row-${i}`}>
                        <td className="px-3 py-2 text-xs text-muted-foreground font-mono">{i + 1}</td>
                        <td className="px-3 py-2"><span className="inline-block font-mono text-xs font-bold bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">{exp.code}</span></td>
                        <td className="px-3 py-2 text-sm">{exp.description}{exp.edited_by && <span className="text-[10px] text-amber-500 ms-1.5 italic">({lang === 'ar' ? 'معدّل' : 'edited'})</span>}</td>
                        <td className="px-3 py-2 text-end font-mono text-sm text-red-600 font-medium">-{exp.amount.toLocaleString()}</td>
                        <td className="px-3 py-2 text-end font-mono text-sm text-muted-foreground">{running.toLocaleString()}</td>
                        {selected.status === 'active' && canAddExpense && <td className="px-2 py-2"><button onClick={() => { api.delete(`/api/financial-custody/${selected.id}/expense/${exp.id}`).then(() => fetchDetail(selected.id)); }} className="text-red-300 hover:text-red-500 transition-colors"><Trash2 size={13} /></button></td>}
                      </tr>
                    );
                  });
                })()}
                {selected.expenses?.length > 0 && (
                  <tr className="bg-slate-50 dark:bg-slate-900/50 font-semibold border-t-2 border-border">
                    <td className="px-3 py-2.5"></td>
                    <td className="px-3 py-2.5" colSpan={2}>{lang === 'ar' ? 'الإجمالي' : 'TOTAL'}</td>
                    <td className="px-3 py-2.5 text-end font-mono text-red-700 dark:text-red-400">-{selected.total_spent.toLocaleString()}</td>
                    <td className="px-3 py-2.5 text-end font-mono text-emerald-700 dark:text-emerald-400">{selected.remaining.toLocaleString()}</td>
                    {selected.status === 'active' && canAddExpense && <td></td>}
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Add expense inline */}
        {selected.status === 'active' && canAddExpense && (
          <div className="border-2 border-dashed border-blue-200 dark:border-blue-900 rounded-lg p-4 bg-blue-50/30 dark:bg-blue-950/10">
            <p className="text-xs font-semibold text-blue-700 dark:text-blue-400 mb-2.5">{lang === 'ar' ? 'إضافة مصروف جديد' : 'Add New Expense'}</p>
            <div className="flex gap-2 items-end flex-wrap">
              <div className="w-20"><Label className="text-[10px]">{lang === 'ar' ? 'الكود' : 'Code'}</Label><Input data-testid="exp-code" type="number" value={expForm.code} onChange={e => { setExpForm(f => ({ ...f, code: e.target.value })); lookupCode(e.target.value); }} className="h-8 text-xs font-mono" /></div>
              <div className="flex-1 min-w-[120px]">
                <Label className="text-[10px]">{lang === 'ar' ? 'البيان' : 'Description'}</Label>
                <div className="relative">
                  <Input data-testid="exp-desc" value={expForm.description} onChange={e => setExpForm(f => ({ ...f, description: e.target.value }))} className="h-8 text-xs" />
                  {codeInfo?.found && <CheckCircle size={12} className="absolute right-2 rtl:left-2 rtl:right-auto top-1/2 -translate-y-1/2 text-emerald-500" />}
                  {codeInfo && !codeInfo.found && <AlertCircle size={12} className="absolute right-2 rtl:left-2 rtl:right-auto top-1/2 -translate-y-1/2 text-amber-500" />}
                </div>
              </div>
              <div className="w-24"><Label className="text-[10px]">{lang === 'ar' ? 'المبلغ' : 'Amount'}</Label><Input data-testid="exp-amount" type="number" value={expForm.amount} onChange={e => setExpForm(f => ({ ...f, amount: e.target.value }))} className="h-8 text-xs font-mono" /></div>
              <Button onClick={handleAddExpense} disabled={submitting} size="sm" className="h-8 bg-blue-600 text-white" data-testid="add-expense-btn"><Plus size={13} className="me-1" />{lang === 'ar' ? 'إضافة' : 'Add'}</Button>
            </div>
          </div>
        )}

        {/* Professional Timeline */}
        <div>
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><Clock size={15} /> {lang === 'ar' ? 'السجل الزمني' : 'Timeline'}</h3>
          <div className="relative ms-3">
            {/* Vertical line */}
            <div className="absolute top-0 bottom-0 start-[7px] w-px bg-border" />
            <div className="space-y-0">
              {selected.timeline?.map((ev, i) => (
                <div key={i} className="relative flex gap-4 pb-4" data-testid={`timeline-${i}`}>
                  {/* Dot */}
                  <div className={`relative z-10 w-[15px] h-[15px] rounded-full border-2 border-background ${TIMELINE_COLORS[ev.event] || 'bg-gray-400'} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="text-xs font-semibold text-foreground">{ev.actor_name}</p>
                      <time className="text-[10px] text-muted-foreground font-mono whitespace-nowrap">{formatGregorianHijriDateTime(ev.timestamp).combined}</time>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{ev.note}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // === LIST VIEW ===
  return (
    <div className="space-y-5" data-testid="financial-custody-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{lang === 'ar' ? 'العهدة المالية' : 'Financial Custody'}</h1>
        {canCreate && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild><Button data-testid="create-custody-btn"><Plus size={16} className="me-1" />{lang === 'ar' ? 'عهدة جديدة' : 'New'}</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>{lang === 'ar' ? 'إنشاء عهدة مالية' : 'New Financial Custody'}</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label>{lang === 'ar' ? 'عنوان العهدة' : 'Title'}</Label><Input data-testid="custody-title" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></div>
                <div><Label>{lang === 'ar' ? 'العنوان (عربي)' : 'Title (AR)'}</Label><Input data-testid="custody-title-ar" value={form.title_ar} onChange={e => setForm(f => ({ ...f, title_ar: e.target.value }))} dir="rtl" /></div>
                <div><Label>{lang === 'ar' ? 'المبلغ (ريال)' : 'Amount (SAR)'}</Label><Input data-testid="custody-amount" type="number" value={form.total_amount} onChange={e => setForm(f => ({ ...f, total_amount: e.target.value }))} /></div>
                <Button onClick={handleCreate} disabled={submitting} data-testid="submit-create" className="w-full">{submitting ? <Loader2 size={14} className="me-1 animate-spin" /> : null}{lang === 'ar' ? 'إنشاء' : 'Create'}</Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Summary Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: lang === 'ar' ? 'عدد العهد' : 'Total', value: summary.total_custodies || 0, color: 'text-foreground' },
          { label: lang === 'ar' ? 'إجمالي المصروف' : 'Total Spent', value: `${(summary.total_spent || 0).toLocaleString()}`, color: 'text-red-600' },
          { label: lang === 'ar' ? 'المتاح' : 'Available', value: `${(summary.total_remaining || 0).toLocaleString()}`, color: 'text-emerald-600' },
          { label: lang === 'ar' ? 'منفذة' : 'Executed', value: summary.executed || 0, color: 'text-purple-600' },
        ].map((s, i) => (
          <div key={i} className="bg-muted/40 rounded-lg px-4 py-3 border border-border">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{s.label}</p>
            <p className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="h-8">
          <TabsTrigger value="all" className="text-xs h-7">{lang === 'ar' ? 'الكل' : 'All'} ({custodies.length})</TabsTrigger>
          <TabsTrigger value="active" className="text-xs h-7">{lang === 'ar' ? 'نشطة' : 'Active'}</TabsTrigger>
          <TabsTrigger value="pending" className="text-xs h-7">{lang === 'ar' ? 'معلقة' : 'Pending'}</TabsTrigger>
          <TabsTrigger value="executed" className="text-xs h-7">{lang === 'ar' ? 'منفذة' : 'Done'}</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Professional Table */}
      <div className="border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="custody-table">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/50 text-xs border-b border-border">
                <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">#</th>
                <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'العنوان' : 'Title'}</th>
                <th className="px-3 py-2.5 text-end font-semibold text-muted-foreground">{lang === 'ar' ? 'الميزانية' : 'Budget'}</th>
                <th className="px-3 py-2.5 text-end font-semibold text-muted-foreground hidden sm:table-cell">{lang === 'ar' ? 'المرحّل' : 'Carried'}</th>
                <th className="px-3 py-2.5 text-end font-semibold text-muted-foreground">{lang === 'ar' ? 'المصروف' : 'Spent'}</th>
                <th className="px-3 py-2.5 text-end font-semibold text-muted-foreground">{lang === 'ar' ? 'المتبقي' : 'Remaining'}</th>
                <th className="px-3 py-2.5 text-start font-semibold text-muted-foreground">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                <th className="px-3 py-2.5 text-center font-semibold text-muted-foreground hidden sm:table-cell">{lang === 'ar' ? 'بنود' : 'Items'}</th>
                <th className="px-2 py-2.5 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.length === 0 && <tr><td colSpan={9} className="text-center py-12 text-muted-foreground">{lang === 'ar' ? 'لا توجد عهد' : 'No custodies'}</td></tr>}
              {filtered.map(c => (
                <tr key={c.id} className="hover:bg-muted/30 transition-colors cursor-pointer" onClick={() => fetchDetail(c.id)} data-testid={`custody-row-${c.custody_number}`}>
                  <td className="px-3 py-2.5 font-mono text-xs font-bold">{c.custody_number}</td>
                  <td className="px-3 py-2.5 font-medium">{lang === 'ar' ? c.title_ar || c.title : c.title}</td>
                  <td className="px-3 py-2.5 text-end font-mono text-xs">{c.total_amount.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-end font-mono text-xs hidden sm:table-cell text-blue-600">{c.carried_amount > 0 ? c.carried_amount.toLocaleString() : '-'}</td>
                  <td className="px-3 py-2.5 text-end font-mono text-xs text-red-600">{c.total_spent.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-end font-mono text-xs font-medium text-emerald-600">{c.remaining.toLocaleString()}</td>
                  <td className="px-3 py-2.5"><span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1 ring-inset ${STATUS_STYLES[c.status]}`}>{STATUS_MAP[lang]?.[c.status]}</span></td>
                  <td className="px-3 py-2.5 text-center text-xs text-muted-foreground hidden sm:table-cell">{c.expenses?.length || 0}</td>
                  <td className="px-2 py-2.5"><ChevronRight size={14} className="text-muted-foreground" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
