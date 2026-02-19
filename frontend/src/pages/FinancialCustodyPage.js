import { useState, useEffect, useCallback, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Plus, CheckCircle, AlertCircle, ArrowLeft, Trash2, Send, Check, X, 
  Loader2, Clock, DollarSign, ChevronRight, FileText, AlertTriangle,
  TrendingUp, TrendingDown, Wallet, Edit2, Save, Printer, Download
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// ==================== CONSTANTS ====================

const STATUS_MAP = {
  ar: { 
    open: 'مفتوحة', 
    pending_audit: 'بانتظار التدقيق', 
    approved: 'معتمدة', 
    executed: 'منفذة', 
    closed: 'مغلقة' 
  },
  en: { 
    open: 'Open', 
    pending_audit: 'Pending Audit', 
    approved: 'Approved', 
    executed: 'Executed', 
    closed: 'Closed' 
  },
};

const STATUS_STYLES = {
  open: 'bg-blue-50 text-blue-700 ring-blue-300 dark:bg-blue-950/50 dark:text-blue-300',
  pending_audit: 'bg-amber-50 text-amber-700 ring-amber-300 dark:bg-amber-950/50 dark:text-amber-300',
  approved: 'bg-emerald-50 text-emerald-700 ring-emerald-300 dark:bg-emerald-950/50 dark:text-emerald-300',
  executed: 'bg-purple-50 text-purple-700 ring-purple-300 dark:bg-purple-950/50 dark:text-purple-300',
  closed: 'bg-slate-100 text-slate-600 ring-slate-300 dark:bg-slate-800 dark:text-slate-400',
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-CA') + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return dateStr;
  }
};

export default function FinancialCustodyPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [custodies, setCustodies] = useState([]);
  const [summary, setSummary] = useState({});
  const [selected, setSelected] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ amount: '', notes: '' });
  const [expForm, setExpForm] = useState({ code: '', description: '', amount: '' });
  const [codeInfo, setCodeInfo] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [view, setView] = useState('list');
  const [tab, setTab] = useState('all');
  const [auditComment, setAuditComment] = useState('');
  const [surplusAlert, setSurplusAlert] = useState(null);
  const [editingExpense, setEditingExpense] = useState(null);
  const [editForm, setEditForm] = useState({ description: '', amount: '' });
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectMode, setSelectMode] = useState(false);
  const codeInputRef = useRef(null);

  const role = user?.role;
  const canCreate = ['sultan', 'mohammed'].includes(role);
  const canAddExpense = ['sultan', 'mohammed'].includes(role);
  const canAudit = ['salah', 'stas'].includes(role);
  const canEditExpense = ['salah', 'stas'].includes(role);
  const canExecute = role === 'stas';
  const canClose = ['sultan', 'mohammed', 'stas'].includes(role);
  const canDelete = role === 'stas';

  // ==================== DATA FETCHING ====================

  const fetchList = useCallback(async () => {
    try {
      const [custodiesRes, summaryRes] = await Promise.all([
        api.get('/api/admin-custody/all'),
        api.get('/api/admin-custody/summary')
      ]);
      setCustodies(custodiesRes.data.filter(c => c.status !== 'deleted'));
      setSummary(summaryRes.data);
    } catch (e) {
      console.error('Error fetching custodies:', e);
    }
  }, []);

  const fetchDetail = async (id) => {
    try {
      const res = await api.get(`/api/admin-custody/${id}`);
      setSelected(res.data);
      setView('detail');
    } catch (e) {
      toast.error(lang === 'ar' ? 'خطأ في تحميل البيانات' : 'Error loading data');
    }
  };

  useEffect(() => { fetchList(); }, [fetchList]);

  // ==================== CODE LOOKUP ====================

  const lookupCode = useCallback(async (val) => {
    const code = parseInt(val);
    if (!val || isNaN(code) || code < 1) {
      setCodeInfo(null);
      return;
    }
    
    try {
      const res = await api.get(`/api/admin-custody/codes/${code}`);
      setCodeInfo(res.data);
    } catch {
      setCodeInfo({ found: false, code: { code, is_new: true } });
    }
  }, []);

  // ==================== PDF / PRINT ====================

  const handlePrintPdf = async (custodyId, custodyNumber) => {
    setSubmitting(true);
    try {
      const response = await api.get(`/api/admin-custody/${custodyId}/pdf?lang=${lang}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      // Open in new tab for printing
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      }
      
      toast.success(lang === 'ar' ? 'جاري فتح الطباعة...' : 'Opening print...');
    } catch (e) {
      toast.error(lang === 'ar' ? 'خطأ في إنشاء PDF' : 'Error generating PDF');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPdf = async (custodyId, custodyNumber) => {
    setSubmitting(true);
    try {
      const response = await api.get(`/api/admin-custody/${custodyId}/pdf?lang=${lang}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `custody_${custodyNumber}_${lang}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(lang === 'ar' ? 'تم تحميل PDF' : 'PDF downloaded');
    } catch (e) {
      toast.error(lang === 'ar' ? 'خطأ في التحميل' : 'Download error');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== DELETE ====================

  const handleDeleteSingle = async (custodyId, custodyNumber) => {
    if (!confirm(lang === 'ar' ? `هل تريد حذف العهدة رقم ${custodyNumber}؟` : `Delete custody ${custodyNumber}?`)) return;
    
    setSubmitting(true);
    try {
      await api.delete(`/api/admin-custody/${custodyId}`);
      toast.success(lang === 'ar' ? 'تم الحذف' : 'Deleted');
      fetchList();
      if (selected?.id === custodyId) {
        setView('list');
        setSelected(null);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) {
      toast.error(lang === 'ar' ? 'اختر عهد للحذف' : 'Select custodies to delete');
      return;
    }
    
    if (!confirm(lang === 'ar' ? `هل تريد حذف ${selectedIds.length} عهدة؟` : `Delete ${selectedIds.length} custodies?`)) return;
    
    setSubmitting(true);
    try {
      const res = await api.delete('/api/admin-custody/bulk', { data: { custody_ids: selectedIds } });
      toast.success(res.data.message_ar || `Deleted ${res.data.deleted_count}`);
      
      if (res.data.failed?.length > 0) {
        toast.warning(`${res.data.failed.length} ${lang === 'ar' ? 'لم يتم حذفها' : 'could not be deleted'}`);
      }
      
      setSelectedIds([]);
      setSelectMode(false);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleSelectAll = () => {
    const deletable = filtered; // STAS يستطيع حذف جميع العهد
    if (selectedIds.length === deletable.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(deletable.map(c => c.id));
    }
  };

  const toggleSelectOne = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  // ==================== ACTIONS ====================

  const handleCreate = async () => {
    if (!form.amount || parseFloat(form.amount) <= 0) {
      toast.error(lang === 'ar' ? 'أدخل مبلغ صحيح' : 'Enter valid amount');
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await api.post('/api/admin-custody/create', {
        amount: parseFloat(form.amount),
        notes: form.notes || null
      });
      
      toast.success(res.data.message_ar || 'تم الإنشاء');
      
      if (res.data.surplus_alert) {
        setSurplusAlert(res.data.surplus_alert);
        setTimeout(() => setSurplusAlert(null), 5000);
      }
      
      setCreateOpen(false);
      setForm({ amount: '', notes: '' });
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddExpense = async () => {
    const code = parseInt(expForm.code);
    const amount = parseFloat(expForm.amount);
    
    if (!code || code < 1) {
      toast.error(lang === 'ar' ? 'أدخل كود صحيح' : 'Enter valid code');
      return;
    }
    if (!amount || amount <= 0) {
      toast.error(lang === 'ar' ? 'أدخل مبلغ صحيح' : 'Enter valid amount');
      return;
    }
    if (!expForm.description.trim()) {
      toast.error(lang === 'ar' ? 'أدخل وصف المصروف (لماذا صرفت؟)' : 'Enter expense description');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.post(`/api/admin-custody/${selected.id}/expense`, {
        code,
        description: expForm.description,
        amount,
        custom_name: code > 60 && !codeInfo?.found ? expForm.description : null
      });
      
      toast.success(lang === 'ar' ? 'تم إضافة المصروف' : 'Expense added');
      setExpForm({ code: '', description: '', amount: '' });
      setCodeInfo(null);
      fetchDetail(selected.id);
      fetchList();
      
      setTimeout(() => codeInputRef.current?.focus(), 100);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteExpense = async (expenseId) => {
    if (!confirm(lang === 'ar' ? 'هل تريد إلغاء هذا المصروف؟' : 'Cancel this expense?')) return;
    
    try {
      await api.delete(`/api/admin-custody/${selected.id}/expense/${expenseId}`);
      toast.success(lang === 'ar' ? 'تم الإلغاء' : 'Cancelled');
      fetchDetail(selected.id);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    }
  };

  const startEditExpense = (expense) => {
    setEditingExpense(expense.id);
    setEditForm({ description: expense.description, amount: expense.amount.toString() });
  };

  const cancelEditExpense = () => {
    setEditingExpense(null);
    setEditForm({ description: '', amount: '' });
  };

  const handleEditExpense = async (expenseId) => {
    const amount = parseFloat(editForm.amount);
    
    if (!editForm.description.trim()) {
      toast.error(lang === 'ar' ? 'أدخل الوصف' : 'Enter description');
      return;
    }
    if (!amount || amount <= 0) {
      toast.error(lang === 'ar' ? 'أدخل مبلغ صحيح' : 'Enter valid amount');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.put(`/api/admin-custody/${selected.id}/expense/${expenseId}`, {
        description: editForm.description,
        amount
      });
      
      toast.success(lang === 'ar' ? 'تم تعديل المصروف' : 'Expense updated');
      setEditingExpense(null);
      setEditForm({ description: '', amount: '' });
      fetchDetail(selected.id);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitAudit = async () => {
    setSubmitting(true);
    try {
      await api.post(`/api/admin-custody/${selected.id}/submit-audit`);
      toast.success(lang === 'ar' ? 'تم الإرسال للتدقيق' : 'Sent for audit');
      fetchDetail(selected.id);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAudit = async (action) => {
    setSubmitting(true);
    try {
      await api.post(`/api/admin-custody/${selected.id}/audit`, {
        action,
        comment: auditComment || null
      });
      toast.success(action === 'approve' 
        ? (lang === 'ar' ? 'تم الاعتماد' : 'Approved')
        : (lang === 'ar' ? 'تم الإرجاع' : 'Returned'));
      setAuditComment('');
      fetchDetail(selected.id);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExecute = async () => {
    setSubmitting(true);
    try {
      await api.post(`/api/admin-custody/${selected.id}/execute`);
      toast.success(lang === 'ar' ? 'تم التنفيذ' : 'Executed');
      fetchDetail(selected.id);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = async () => {
    if (!confirm(lang === 'ar' ? 'هل تريد إغلاق العهدة؟' : 'Close custody?')) return;
    
    setSubmitting(true);
    try {
      const res = await api.post(`/api/admin-custody/${selected.id}/close`);
      toast.success(res.data.message_ar || 'Closed');
      fetchDetail(selected.id);
      fetchList();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  // ==================== FILTERING ====================

  const filtered = custodies.filter(c => {
    if (tab === 'all') return true;
    if (tab === 'open') return c.status === 'open';
    if (tab === 'pending') return c.status === 'pending_audit';
    if (tab === 'approved') return c.status === 'approved';
    if (tab === 'executed') return ['executed', 'closed'].includes(c.status);
    return true;
  });

  // ==================== DETAIL VIEW ====================

  if (view === 'detail' && selected) {
    const budget = selected.budget || (selected.total_amount + (selected.surplus_amount || 0));
    const pct = budget > 0 ? Math.min((selected.spent / budget) * 100, 100) : 0;
    const isEditable = ['open', 'pending_audit'].includes(selected.status);
    const canSalahEdit = selected.status === 'pending_audit' && canEditExpense;
    const canDeleteThis = canDelete; // STAS يستطيع حذف جميع العهد

    return (
      <div className="space-y-5 pb-10" data-testid="custody-detail">
        {/* Back Button */}
        <button 
          onClick={() => { setView('list'); setSelected(null); setEditingExpense(null); }} 
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          data-testid="back-to-list"
        >
          <ArrowLeft size={16} /> {lang === 'ar' ? 'العودة للقائمة' : 'Back to list'}
        </button>

        {/* Header */}
        <div className="bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-xl p-5 border border-border">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="font-mono text-lg font-bold bg-primary text-primary-foreground px-3 py-1 rounded-lg">
                  #{selected.custody_number}
                </span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ring-1 ring-inset ${STATUS_STYLES[selected.status]}`}>
                  {STATUS_MAP[lang]?.[selected.status]}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {lang === 'ar' ? 'أنشأها' : 'Created by'}: {selected.created_by_name} • {formatDate(selected.created_at)}
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Print/Download Buttons */}
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handlePrintPdf(selected.id, selected.custody_number)}
                disabled={submitting}
                className="gap-1.5"
                data-testid="print-btn"
              >
                <Printer size={14} />
                {lang === 'ar' ? 'طباعة' : 'Print'}
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleDownloadPdf(selected.id, selected.custody_number)}
                disabled={submitting}
                className="gap-1.5"
                data-testid="download-btn"
              >
                <Download size={14} />
                PDF
              </Button>
              
              {canDeleteThis && (
                <Button 
                  variant="destructive" 
                  size="sm"
                  onClick={() => handleDeleteSingle(selected.id, selected.custody_number)}
                  disabled={submitting}
                  className="gap-1.5"
                  data-testid="delete-btn"
                >
                  <Trash2 size={14} />
                  {lang === 'ar' ? 'حذف' : 'Delete'}
                </Button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-6 lg:gap-10 mt-4">
            <div className="text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                {lang === 'ar' ? 'الميزانية' : 'Budget'}
              </p>
              <p className="text-2xl font-bold font-mono">{budget.toLocaleString()}</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                {lang === 'ar' ? 'المصروف' : 'Spent'}
              </p>
              <p className="text-2xl font-bold font-mono text-red-600">{selected.spent.toLocaleString()}</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                {lang === 'ar' ? 'المتبقي' : 'Remaining'}
              </p>
              <p className="text-2xl font-bold font-mono text-emerald-600">{selected.remaining.toLocaleString()}</p>
            </div>
          </div>

          {/* Surplus Info */}
          {selected.surplus_amount > 0 && (
            <div className="mt-4 text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200 px-4 py-2 rounded-lg flex items-center gap-2">
              <TrendingUp size={14} />
              {lang === 'ar' 
                ? `مرحّل من العهدة ${selected.surplus_from}: ${selected.surplus_amount.toLocaleString()} ريال`
                : `Carried from custody ${selected.surplus_from}: ${selected.surplus_amount.toLocaleString()} SAR`}
            </div>
          )}

          {/* Progress Bar */}
          <div className="mt-4">
            <div className="flex justify-between text-xs text-muted-foreground mb-1">
              <span>{pct.toFixed(0)}% {lang === 'ar' ? 'مصروف' : 'spent'}</span>
              <span>{(100 - pct).toFixed(0)}% {lang === 'ar' ? 'متبقي' : 'remaining'}</span>
            </div>
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-red-400 via-red-500 to-red-600 rounded-full transition-all duration-700" 
                style={{ width: `${pct}%` }} 
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          {selected.status === 'open' && canAddExpense && selected.expenses?.length > 0 && (
            <Button 
              onClick={handleSubmitAudit} 
              disabled={submitting} 
              className="bg-amber-600 hover:bg-amber-700 text-white"
              data-testid="submit-audit-btn"
            >
              <Send size={14} className="me-1.5" />
              {lang === 'ar' ? 'إرسال للتدقيق' : 'Submit for Audit'}
            </Button>
          )}
          
          {selected.status === 'pending_audit' && canAudit && (
            <div className="flex gap-2 items-center flex-wrap">
              <Input 
                placeholder={lang === 'ar' ? 'ملاحظات (اختياري)' : 'Comment (optional)'}
                value={auditComment}
                onChange={e => setAuditComment(e.target.value)}
                className="w-48 h-9 text-sm"
              />
              <Button 
                onClick={() => handleAudit('approve')} 
                disabled={submitting}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                data-testid="approve-audit-btn"
              >
                <Check size={14} className="me-1" />
                {lang === 'ar' ? 'اعتماد' : 'Approve'}
              </Button>
              <Button 
                onClick={() => handleAudit('reject')} 
                disabled={submitting}
                variant="destructive"
                data-testid="reject-audit-btn"
              >
                <X size={14} className="me-1" />
                {lang === 'ar' ? 'إرجاع' : 'Return'}
              </Button>
            </div>
          )}
          
          {selected.status === 'approved' && canExecute && (
            <Button 
              onClick={handleExecute} 
              disabled={submitting}
              className="bg-purple-600 hover:bg-purple-700 text-white"
              data-testid="execute-btn"
            >
              <Check size={14} className="me-1.5" />
              {lang === 'ar' ? 'تنفيذ' : 'Execute'}
            </Button>
          )}
          
          {selected.status === 'executed' && canClose && (
            <Button 
              onClick={handleClose} 
              disabled={submitting}
              variant="outline"
              data-testid="close-btn"
            >
              <FileText size={14} className="me-1.5" />
              {lang === 'ar' ? 'إغلاق العهدة' : 'Close Custody'}
              {selected.remaining > 0 && (
                <span className="ms-1.5 text-xs bg-blue-100 text-blue-700 px-1.5 rounded">
                  {lang === 'ar' ? `فائض ${selected.remaining}` : `Surplus ${selected.remaining}`}
                </span>
              )}
            </Button>
          )}
        </div>

        {/* EXPENSE TABLE */}
        <div className="border border-border rounded-xl overflow-hidden shadow-sm bg-background">
          <div className="bg-slate-100 dark:bg-slate-800 px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-bold flex items-center gap-2">
              <DollarSign size={16} className="text-primary" />
              {lang === 'ar' ? 'جدول المصروفات' : 'Expense Sheet'}
            </h3>
            <div className="flex items-center gap-3">
              {canSalahEdit && (
                <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                  {lang === 'ar' ? 'يمكنك التعديل' : 'You can edit'}
                </span>
              )}
              <span className="text-xs text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded">
                {selected.expenses?.length || 0} {lang === 'ar' ? 'بند' : 'items'}
              </span>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="expense-table">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/70 text-xs border-b border-border">
                  <th className="px-3 py-3 text-start font-bold text-muted-foreground w-12">#</th>
                  <th className="px-3 py-3 text-start font-bold text-muted-foreground w-16">
                    {lang === 'ar' ? 'الكود' : 'Code'}
                  </th>
                  <th className="px-3 py-3 text-start font-bold text-muted-foreground w-36">
                    {lang === 'ar' ? 'اسم الحساب' : 'Account'}
                  </th>
                  <th className="px-3 py-3 text-start font-bold text-muted-foreground">
                    {lang === 'ar' ? 'الوصف (لماذا صُرف؟)' : 'Description (Why?)'}
                  </th>
                  <th className="px-3 py-3 text-end font-bold text-muted-foreground w-28">
                    {lang === 'ar' ? 'المبلغ' : 'Amount'}
                  </th>
                  <th className="px-3 py-3 text-end font-bold text-muted-foreground w-28">
                    {lang === 'ar' ? 'الرصيد' : 'Balance'}
                  </th>
                  {(isEditable || canSalahEdit) && <th className="px-2 py-3 w-20"></th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(!selected.expenses || selected.expenses.length === 0) && (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-muted-foreground">
                      <DollarSign size={32} className="mx-auto mb-2 opacity-30" />
                      {lang === 'ar' ? 'لا توجد مصروفات بعد' : 'No expenses yet'}
                    </td>
                  </tr>
                )}
                {(() => {
                  let runningBalance = budget;
                  return selected.expenses?.map((exp, i) => {
                    runningBalance -= exp.amount;
                    const isEditing = editingExpense === exp.id;
                    
                    return (
                      <tr 
                        key={exp.id} 
                        className={`hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-colors ${isEditing ? 'bg-amber-50 dark:bg-amber-950/20' : ''}`}
                        data-testid={`expense-row-${i}`}
                      >
                        <td className="px-3 py-2.5 text-xs text-muted-foreground font-mono">{i + 1}</td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center justify-center w-10 h-7 font-mono text-xs font-bold bg-slate-200 dark:bg-slate-700 rounded">
                            {exp.code}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-sm font-medium text-muted-foreground">
                          {lang === 'ar' ? exp.code_name_ar : exp.code_name_en}
                        </td>
                        <td className="px-3 py-2.5">
                          {isEditing ? (
                            <Input 
                              value={editForm.description}
                              onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                              className="h-8 text-sm"
                              data-testid="edit-description"
                            />
                          ) : (
                            <span className="text-sm">
                              {exp.description}
                              {exp.edited_by && (
                                <span className="ms-1.5 text-[10px] text-amber-600 bg-amber-50 px-1.5 rounded">
                                  {lang === 'ar' ? 'معدّل' : 'edited'}
                                </span>
                              )}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-end">
                          {isEditing ? (
                            <Input 
                              type="number"
                              value={editForm.amount}
                              onChange={e => setEditForm(f => ({ ...f, amount: e.target.value }))}
                              className="h-8 text-sm font-mono text-end w-24"
                              data-testid="edit-amount"
                            />
                          ) : (
                            <span className="font-mono text-sm text-red-600 font-semibold">
                              -{exp.amount.toLocaleString()}
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-end font-mono text-sm text-muted-foreground">
                          {runningBalance.toLocaleString()}
                        </td>
                        {(isEditable || canSalahEdit) && (
                          <td className="px-2 py-2.5">
                            <div className="flex items-center gap-1 justify-end">
                              {isEditing ? (
                                <>
                                  <button 
                                    onClick={() => handleEditExpense(exp.id)}
                                    disabled={submitting}
                                    className="p-1.5 rounded-md text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 transition-all"
                                    title={lang === 'ar' ? 'حفظ' : 'Save'}
                                  >
                                    <Save size={14} />
                                  </button>
                                  <button 
                                    onClick={cancelEditExpense}
                                    className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
                                    title={lang === 'ar' ? 'إلغاء' : 'Cancel'}
                                  >
                                    <X size={14} />
                                  </button>
                                </>
                              ) : (
                                <>
                                  {canSalahEdit && (
                                    <button 
                                      onClick={() => startEditExpense(exp)}
                                      className="p-1.5 rounded-md text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-950/50 transition-all"
                                      title={lang === 'ar' ? 'تعديل' : 'Edit'}
                                      data-testid={`edit-expense-${i}`}
                                    >
                                      <Edit2 size={14} />
                                    </button>
                                  )}
                                  {isEditable && canAddExpense && (
                                    <button 
                                      onClick={() => handleDeleteExpense(exp.id)}
                                      className="p-1.5 rounded-md text-red-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/50 transition-all"
                                      title={lang === 'ar' ? 'إلغاء' : 'Cancel'}
                                    >
                                      <Trash2 size={14} />
                                    </button>
                                  )}
                                </>
                              )}
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  });
                })()}
                
                {/* Total Row */}
                {selected.expenses?.length > 0 && (
                  <tr className="bg-slate-100 dark:bg-slate-800 font-bold border-t-2 border-slate-300 dark:border-slate-600">
                    <td className="px-3 py-3"></td>
                    <td className="px-3 py-3"></td>
                    <td className="px-3 py-3"></td>
                    <td className="px-3 py-3">
                      {lang === 'ar' ? 'إجمالي المصروفات' : 'TOTAL EXPENSES'}
                    </td>
                    <td className="px-3 py-3 text-end font-mono text-red-700 dark:text-red-400">
                      -{selected.spent.toLocaleString()}
                    </td>
                    <td className="px-3 py-3 text-end font-mono text-emerald-700 dark:text-emerald-400">
                      {selected.remaining.toLocaleString()}
                    </td>
                    {(isEditable || canSalahEdit) && <td></td>}
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ADD EXPENSE */}
        {isEditable && canAddExpense && (
          <div className="border-2 border-dashed border-primary/30 rounded-xl p-5 bg-primary/5">
            <p className="text-xs font-bold text-primary mb-3 flex items-center gap-2">
              <Plus size={14} />
              {lang === 'ar' ? 'إضافة مصروف جديد' : 'Add New Expense'}
            </p>
            
            <div className="flex gap-3 items-end flex-wrap">
              <div className="w-20">
                <Label className="text-[10px] text-muted-foreground uppercase">
                  {lang === 'ar' ? 'الكود' : 'Code'}
                </Label>
                <Input 
                  ref={codeInputRef}
                  type="number"
                  min="1"
                  value={expForm.code}
                  onChange={e => {
                    setExpForm(f => ({ ...f, code: e.target.value }));
                    lookupCode(e.target.value);
                  }}
                  className="h-10 text-center font-mono font-bold text-lg"
                  placeholder="5"
                  data-testid="exp-code"
                />
              </div>
              
              <div className="w-40">
                <Label className="text-[10px] text-muted-foreground uppercase flex items-center gap-1">
                  {lang === 'ar' ? 'اسم الحساب' : 'Account'}
                  {codeInfo?.found && <CheckCircle size={10} className="text-emerald-500" />}
                </Label>
                <div className="h-10 px-3 flex items-center bg-slate-100 dark:bg-slate-800 rounded-md text-sm font-medium">
                  {codeInfo?.found 
                    ? (lang === 'ar' ? codeInfo.code.name_ar : codeInfo.code.name_en)
                    : codeInfo && !codeInfo.found
                      ? <span className="text-amber-600">{lang === 'ar' ? 'كود جديد' : 'New code'}</span>
                      : <span className="text-muted-foreground">-</span>
                  }
                </div>
              </div>
              
              <div className="flex-1 min-w-[200px]">
                <Label className="text-[10px] text-muted-foreground uppercase">
                  {lang === 'ar' ? 'الوصف (لماذا صرفت؟)' : 'Description (Why?)'}
                </Label>
                <Input 
                  value={expForm.description}
                  onChange={e => setExpForm(f => ({ ...f, description: e.target.value }))}
                  className="h-10"
                  placeholder={lang === 'ar' ? 'مثال: انتقالات لموقع العمل' : 'e.g., Transportation to site'}
                  data-testid="exp-desc"
                />
              </div>
              
              <div className="w-28">
                <Label className="text-[10px] text-muted-foreground uppercase">
                  {lang === 'ar' ? 'المبلغ' : 'Amount'}
                </Label>
                <Input 
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={expForm.amount}
                  onChange={e => setExpForm(f => ({ ...f, amount: e.target.value }))}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddExpense();
                    }
                  }}
                  className="h-10 font-mono text-end"
                  placeholder="0.00"
                  data-testid="exp-amount"
                />
              </div>
              
              <Button 
                onClick={handleAddExpense} 
                disabled={submitting}
                className="h-10 px-6 bg-primary hover:bg-primary/90"
                data-testid="add-expense-btn"
              >
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={16} />}
                <span className="ms-1.5">{lang === 'ar' ? 'إضافة' : 'Add'}</span>
              </Button>
            </div>
            
            <div className="mt-3 text-xs text-muted-foreground flex items-center gap-4">
              <span>{lang === 'ar' ? 'المتبقي:' : 'Remaining:'} <strong className="text-emerald-600">{selected.remaining.toLocaleString()}</strong></span>
              {expForm.amount && (
                <span>
                  {lang === 'ar' ? 'بعد الإضافة:' : 'After adding:'} 
                  <strong className={`ms-1 ${(selected.remaining - parseFloat(expForm.amount || 0)) < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                    {(selected.remaining - parseFloat(expForm.amount || 0)).toLocaleString()}
                  </strong>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Timeline */}
        {selected.logs && selected.logs.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
              <Clock size={15} className="text-muted-foreground" />
              {lang === 'ar' ? 'سجل الأحداث' : 'Activity Log'}
            </h3>
            <div className="space-y-2">
              {selected.logs.slice(0, 10).map((log, i) => (
                <div 
                  key={log.id || i}
                  className="flex items-start gap-3 text-xs bg-muted/30 rounded-lg px-3 py-2"
                >
                  <div className="w-2 h-2 rounded-full bg-primary mt-1.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground">
                      {log.performed_by_name || log.performed_by}
                    </p>
                    <p className="text-muted-foreground">
                      {lang === 'ar' ? (
                        log.action === 'created' ? 'أنشأ العهدة' :
                        log.action === 'expense_added' ? `أضاف مصروف: ${log.details?.amount} ريال` :
                        log.action === 'expense_cancelled' ? 'ألغى مصروف' :
                        log.action === 'expense_edited' ? 'عدّل مصروف' :
                        log.action === 'submitted_for_audit' ? 'أرسل للتدقيق' :
                        log.action === 'audit_approve' ? 'اعتمد التدقيق' :
                        log.action === 'audit_reject' ? 'أرجع العهدة' :
                        log.action === 'executed' ? 'نفّذ العهدة' :
                        log.action === 'closed' ? 'أغلق العهدة' :
                        log.action === 'deleted' ? 'حذف العهدة' :
                        log.action
                      ) : log.action}
                    </p>
                  </div>
                  <time className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {formatDate(log.performed_at)}
                  </time>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ==================== LIST VIEW ====================
  
  return (
    <div className="space-y-5" data-testid="financial-custody-page">
      {/* Surplus Alert */}
      {surplusAlert && (
        <div className="bg-blue-50 dark:bg-blue-950/50 text-blue-800 dark:text-blue-200 px-4 py-3 rounded-lg flex items-center gap-2 animate-pulse">
          <TrendingUp size={18} />
          {surplusAlert}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {lang === 'ar' ? 'العهدة المالية الإدارية' : 'Financial Custody'}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {lang === 'ar' ? 'نظام إدارة العهد المالية الداخلية' : 'Internal financial custody management'}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {canDelete && (
            <Button 
              variant={selectMode ? "secondary" : "outline"}
              size="sm"
              onClick={() => { setSelectMode(!selectMode); setSelectedIds([]); }}
              data-testid="select-mode-btn"
            >
              {selectMode 
                ? (lang === 'ar' ? 'إلغاء التحديد' : 'Cancel') 
                : (lang === 'ar' ? 'تحديد للحذف' : 'Select')}
            </Button>
          )}
          
          {selectMode && selectedIds.length > 0 && (
            <Button 
              variant="destructive"
              size="sm"
              onClick={handleBulkDelete}
              disabled={submitting}
              className="gap-1.5"
              data-testid="bulk-delete-btn"
            >
              <Trash2 size={14} />
              {lang === 'ar' ? `حذف (${selectedIds.length})` : `Delete (${selectedIds.length})`}
            </Button>
          )}
          
          {canCreate && !selectMode && (
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button data-testid="create-custody-btn" className="gap-1.5">
                  <Plus size={16} />
                  {lang === 'ar' ? 'عهدة جديدة' : 'New Custody'}
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>
                    {lang === 'ar' ? 'إنشاء عهدة مالية جديدة' : 'Create New Financial Custody'}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 pt-2">
                  <div>
                    <Label>{lang === 'ar' ? 'مبلغ العهدة (ريال)' : 'Amount (SAR)'}</Label>
                    <Input 
                      type="number"
                      min="1"
                      value={form.amount}
                      onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                      className="font-mono text-lg"
                      placeholder="500"
                      data-testid="custody-amount"
                    />
                  </div>
                  <div>
                    <Label>{lang === 'ar' ? 'ملاحظات (اختياري)' : 'Notes (optional)'}</Label>
                    <Textarea 
                      value={form.notes}
                      onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                      rows={2}
                      data-testid="custody-notes"
                    />
                  </div>
                  <Button 
                    onClick={handleCreate} 
                    disabled={submitting || !form.amount}
                    className="w-full"
                    data-testid="submit-create"
                  >
                    {submitting && <Loader2 size={14} className="me-1.5 animate-spin" />}
                    {lang === 'ar' ? 'إنشاء العهدة' : 'Create Custody'}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-xl p-4 border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Wallet size={16} className="text-slate-500" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {lang === 'ar' ? 'عدد العهد' : 'Total'}
            </span>
          </div>
          <p className="text-2xl font-bold">{summary.total_custodies || 0}</p>
        </div>
        
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/50 dark:to-blue-900/30 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-blue-500" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {lang === 'ar' ? 'الميزانية' : 'Budget'}
            </span>
          </div>
          <p className="text-2xl font-bold font-mono text-blue-700 dark:text-blue-300">
            {(summary.total_budget || 0).toLocaleString()}
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-red-50 to-red-100 dark:from-red-950/50 dark:to-red-900/30 rounded-xl p-4 border border-red-200 dark:border-red-800">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown size={16} className="text-red-500" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {lang === 'ar' ? 'المصروف' : 'Spent'}
            </span>
          </div>
          <p className="text-2xl font-bold font-mono text-red-700 dark:text-red-300">
            {(summary.total_spent || 0).toLocaleString()}
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950/50 dark:to-emerald-900/30 rounded-xl p-4 border border-emerald-200 dark:border-emerald-800">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={16} className="text-emerald-500" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {lang === 'ar' ? 'المتبقي' : 'Remaining'}
            </span>
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-700 dark:text-emerald-300">
            {(summary.total_remaining || 0).toLocaleString()}
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950/50 dark:to-amber-900/30 rounded-xl p-4 border border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-amber-500" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">
              {lang === 'ar' ? 'بانتظار التدقيق' : 'Pending'}
            </span>
          </div>
          <p className="text-2xl font-bold">{summary.pending_audit || 0}</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="h-9 bg-muted/50">
          <TabsTrigger value="all" className="text-xs">
            {lang === 'ar' ? 'الكل' : 'All'} ({custodies.length})
          </TabsTrigger>
          <TabsTrigger value="open" className="text-xs">
            {lang === 'ar' ? 'مفتوحة' : 'Open'}
          </TabsTrigger>
          <TabsTrigger value="pending" className="text-xs">
            {lang === 'ar' ? 'للتدقيق' : 'Pending'}
          </TabsTrigger>
          <TabsTrigger value="approved" className="text-xs">
            {lang === 'ar' ? 'معتمدة' : 'Approved'}
          </TabsTrigger>
          <TabsTrigger value="executed" className="text-xs">
            {lang === 'ar' ? 'منفذة' : 'Executed'}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Custodies Table */}
      <div className="border border-border rounded-xl overflow-hidden shadow-sm bg-background">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="custody-table">
            <thead>
              <tr className="bg-slate-100 dark:bg-slate-800 text-xs border-b border-border">
                {selectMode && (
                  <th className="px-3 py-3 w-10">
                    <Checkbox 
                      checked={selectedIds.length === filtered.length && selectedIds.length > 0}
                      onCheckedChange={toggleSelectAll}
                      data-testid="select-all"
                    />
                  </th>
                )}
                <th className="px-4 py-3 text-start font-bold text-muted-foreground">#</th>
                <th className="px-4 py-3 text-start font-bold text-muted-foreground">
                  {lang === 'ar' ? 'التاريخ' : 'Date'}
                </th>
                <th className="px-4 py-3 text-end font-bold text-muted-foreground">
                  {lang === 'ar' ? 'الميزانية' : 'Budget'}
                </th>
                <th className="px-4 py-3 text-end font-bold text-muted-foreground">
                  {lang === 'ar' ? 'المصروف' : 'Spent'}
                </th>
                <th className="px-4 py-3 text-end font-bold text-muted-foreground">
                  {lang === 'ar' ? 'المتبقي' : 'Remaining'}
                </th>
                <th className="px-4 py-3 text-center font-bold text-muted-foreground">
                  {lang === 'ar' ? 'الحالة' : 'Status'}
                </th>
                <th className="px-4 py-3 text-center font-bold text-muted-foreground">
                  {lang === 'ar' ? 'بنود' : 'Items'}
                </th>
                <th className="px-3 py-3 w-12"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={selectMode ? 9 : 8} className="text-center py-16 text-muted-foreground">
                    <Wallet size={40} className="mx-auto mb-3 opacity-20" />
                    <p>{lang === 'ar' ? 'لا توجد عهد' : 'No custodies found'}</p>
                  </td>
                </tr>
              )}
              {filtered.map(c => {
                const canSelectThis = !['executed', 'closed'].includes(c.status);
                
                return (
                  <tr 
                    key={c.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors cursor-pointer"
                    onClick={(e) => {
                      if (selectMode && canSelectThis) {
                        e.stopPropagation();
                        toggleSelectOne(c.id, c.status);
                      } else if (!selectMode) {
                        fetchDetail(c.id);
                      }
                    }}
                    data-testid={`custody-row-${c.custody_number}`}
                  >
                    {selectMode && (
                      <td className="px-3 py-3" onClick={e => e.stopPropagation()}>
                        <Checkbox 
                          checked={selectedIds.includes(c.id)}
                          disabled={!canSelectThis}
                          onCheckedChange={() => toggleSelectOne(c.id, c.status)}
                        />
                      </td>
                    )}
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center justify-center w-10 h-8 font-mono text-sm font-bold bg-primary/10 text-primary rounded-lg">
                        {c.custody_number}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {formatDate(c.created_at).split(' ')[0]}
                    </td>
                    <td className="px-4 py-3 text-end font-mono text-sm font-medium">
                      {(c.budget || c.total_amount).toLocaleString()}
                      {c.surplus_amount > 0 && (
                        <span className="text-[10px] text-blue-600 ms-1">+{c.surplus_amount}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-end font-mono text-sm text-red-600">
                      {c.spent.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-end font-mono text-sm font-semibold text-emerald-600">
                      {c.remaining.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-block px-2.5 py-1 rounded-full text-[10px] font-bold ring-1 ring-inset ${STATUS_STYLES[c.status]}`}>
                        {STATUS_MAP[lang]?.[c.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-muted-foreground">
                      {c.expense_count || 0}
                    </td>
                    <td className="px-3 py-3">
                      <ChevronRight size={16} className="text-muted-foreground" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
