import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  Wallet, Plus, Send, CheckCircle, XCircle, Play, Lock, 
  FileSpreadsheet, Trash2, AlertTriangle, RefreshCw, Clock,
  ChevronRight, Download, Info
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

const STATUS_MAP = {
  open: { label_ar: 'مفتوحة', label_en: 'Open', color: 'bg-blue-100 text-blue-700', icon: '📂' },
  pending_audit: { label_ar: 'بانتظار التدقيق', label_en: 'Pending Audit', color: 'bg-orange-100 text-orange-700', icon: '⏳' },
  approved: { label_ar: 'معتمدة', label_en: 'Approved', color: 'bg-green-100 text-green-700', icon: '✅' },
  executed: { label_ar: 'منفذة', label_en: 'Executed', color: 'bg-purple-100 text-purple-700', icon: '🔒' },
  closed: { label_ar: 'مغلقة', label_en: 'Closed', color: 'bg-slate-100 text-slate-600', icon: '📦' },
};

export default function AdminCustodyPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [custodies, setCustodies] = useState([]);
  const [expenseCodes, setExpenseCodes] = useState([]);
  const [summary, setSummary] = useState({});
  const [selectedCustody, setSelectedCustody] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [surplus, setSurplus] = useState({ total_surplus: 0, custodies: [] });

  const role = user?.role;
  const canCreate = ['sultan', 'mohammed'].includes(role);
  const canAudit = ['salah', 'stas'].includes(role);
  const canExecute = role === 'stas';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [custodiesRes, codesRes, summaryRes, surplusRes] = await Promise.all([
        api.get('/api/admin-custody/all'),
        api.get('/api/admin-custody/expense-codes'),
        api.get('/api/admin-custody/dashboard/summary'),
        api.get('/api/admin-custody/open-surplus')
      ]);
      setCustodies(custodiesRes.data);
      setExpenseCodes(codesRes.data);
      setSummary(summaryRes.data);
      setSurplus(surplusRes.data);
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل تحميل البيانات' : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    return (num || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
  };

  const getStatusInfo = (status) => STATUS_MAP[status] || STATUS_MAP.open;

  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6 pb-24" data-testid="admin-custody-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
            <Wallet size={28} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? 'العهدة المالية الإدارية' : 'Admin Financial Custody'}
            </h1>
            <p className="text-sm text-slate-500">
              {lang === 'ar' ? 'إدارة العهد والمصروفات' : 'Manage custodies and expenses'}
            </p>
          </div>
        </div>
        
        {canCreate && (
          <Button onClick={() => setShowCreate(true)} className="bg-emerald-600 hover:bg-emerald-700 gap-2 shadow-lg">
            <Plus size={18} />
            {lang === 'ar' ? 'عهدة جديدة' : 'New Custody'}
          </Button>
        )}
      </div>

      {/* Dashboard Summary */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
        <Card className="bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold">{formatNumber(summary.total_amount)}</p>
            <p className="text-xs text-emerald-100">{lang === 'ar' ? 'إجمالي العهد' : 'Total'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-red-500 to-rose-600 text-white">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold">{formatNumber(summary.total_spent)}</p>
            <p className="text-xs text-red-100">{lang === 'ar' ? 'المصروف' : 'Spent'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-blue-500 to-indigo-600 text-white">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold">{formatNumber(summary.total_remaining)}</p>
            <p className="text-xs text-blue-100">{lang === 'ar' ? 'المتبقي' : 'Remaining'}</p>
          </CardContent>
        </Card>
        <Card className="bg-purple-50 border-purple-200">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-purple-700">{summary.open_custodies || 0}</p>
            <p className="text-xs text-purple-600">{lang === 'ar' ? 'مفتوحة' : 'Open'}</p>
          </CardContent>
        </Card>
        <Card className="bg-orange-50 border-orange-200">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-orange-700">{summary.pending_audit || 0}</p>
            <p className="text-xs text-orange-600">{lang === 'ar' ? 'بانتظار التدقيق' : 'Pending'}</p>
          </CardContent>
        </Card>
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-amber-700">{formatNumber(summary.total_surplus)}</p>
            <p className="text-xs text-amber-600">{lang === 'ar' ? 'فائض' : 'Surplus'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Surplus Alert */}
      {surplus.total_surplus > 0 && (
        <div className="bg-amber-50 border-2 border-amber-300 rounded-xl p-4 mb-6 flex items-center gap-3">
          <AlertTriangle className="text-amber-600" size={24} />
          <div>
            <p className="font-bold text-amber-800">
              {lang === 'ar' ? 'يوجد فائض من عهد سابقة!' : 'Surplus available from previous custodies!'}
            </p>
            <p className="text-sm text-amber-700">
              {lang === 'ar' 
                ? `إجمالي الفائض: ${formatNumber(surplus.total_surplus)} ريال - يمكن ترحيله للعهدة الجديدة`
                : `Total surplus: ${formatNumber(surplus.total_surplus)} SAR - Can be carried forward`
              }
            </p>
          </div>
        </div>
      )}

      {/* Custodies List */}
      <div className="space-y-4">
        {loading ? (
          <Card><CardContent className="py-12 text-center"><RefreshCw className="animate-spin mx-auto" /></CardContent></Card>
        ) : custodies.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Wallet size={48} className="mx-auto text-slate-300 mb-4" />
              <p className="text-slate-500">{lang === 'ar' ? 'لا توجد عهد' : 'No custodies'}</p>
            </CardContent>
          </Card>
        ) : (
          custodies.map(custody => (
            <CustodyCard
              key={custody.id}
              custody={custody}
              lang={lang}
              onSelect={() => setSelectedCustody(custody)}
              getStatusInfo={getStatusInfo}
              formatNumber={formatNumber}
              formatDate={formatDate}
            />
          ))
        )}
      </div>

      {/* Create Dialog */}
      {showCreate && (
        <CreateCustodyDialog
          open={showCreate}
          onClose={() => setShowCreate(false)}
          lang={lang}
          surplus={surplus}
          onSuccess={() => { setShowCreate(false); fetchData(); }}
        />
      )}

      {/* Custody Detail */}
      {selectedCustody && (
        <CustodyDetailPage
          custody={selectedCustody}
          expenseCodes={expenseCodes}
          lang={lang}
          role={role}
          canCreate={canCreate}
          canAudit={canAudit}
          canExecute={canExecute}
          onClose={() => setSelectedCustody(null)}
          onUpdate={fetchData}
        />
      )}
    </div>
  );
}

// ==================== Custody Card ====================
function CustodyCard({ custody, lang, onSelect, getStatusInfo, formatNumber, formatDate }) {
  const status = getStatusInfo(custody.status);
  const progress = custody.total_amount > 0 ? (custody.spent / custody.total_amount) * 100 : 0;

  return (
    <Card 
      className="cursor-pointer hover:shadow-lg transition-all border-2 hover:border-emerald-300"
      onClick={onSelect}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-100 flex items-center justify-center">
              <span className="text-2xl font-bold text-emerald-700">#{custody.custody_number}</span>
            </div>
            <div>
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${status.color}`}>
                {status.icon} {lang === 'ar' ? status.label_ar : status.label_en}
              </span>
              <p className="text-xs text-slate-500 mt-1">{formatDate(custody.created_at)}</p>
            </div>
          </div>
          <ChevronRight className="text-slate-400" />
        </div>

        {/* Progress */}
        <div className="mb-3">
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div 
              className="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
        </div>

        {/* Amounts */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-lg font-bold text-emerald-700">{formatNumber(custody.total_amount)}</p>
            <p className="text-xs text-slate-500">{lang === 'ar' ? 'الإجمالي' : 'Total'}</p>
          </div>
          <div>
            <p className="text-lg font-bold text-red-600">{formatNumber(custody.spent)}</p>
            <p className="text-xs text-slate-500">{lang === 'ar' ? 'المصروف' : 'Spent'}</p>
          </div>
          <div>
            <p className="text-lg font-bold text-blue-600">{formatNumber(custody.remaining)}</p>
            <p className="text-xs text-slate-500">{lang === 'ar' ? 'المتبقي' : 'Remaining'}</p>
          </div>
        </div>

        {custody.surplus_from && (
          <div className="mt-2 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
            {lang === 'ar' ? `يتضمن ترحيل ${formatNumber(custody.surplus_amount)} من عهدة ${custody.surplus_from}` : `Includes ${formatNumber(custody.surplus_amount)} carried from #${custody.surplus_from}`}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ==================== Create Dialog ====================
function CreateCustodyDialog({ open, onClose, lang, surplus, onSuccess }) {
  const [amount, setAmount] = useState('');
  const [notes, setNotes] = useState('');
  const [carryForward, setCarryForward] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) {
      toast.error(lang === 'ar' ? 'أدخل مبلغ صحيح' : 'Enter valid amount');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/api/admin-custody/create', {
        amount: parseFloat(amount),
        notes,
        carry_forward_from: carryForward || null
      });
      toast.success(lang === 'ar' ? 'تم إنشاء العهدة' : 'Custody created');
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="text-emerald-600" />
            {lang === 'ar' ? 'إنشاء عهدة جديدة' : 'Create New Custody'}
          </DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>{lang === 'ar' ? 'مبلغ العهدة *' : 'Custody Amount *'}</Label>
            <Input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              min="0"
              step="0.01"
              className="text-lg font-bold"
              required
            />
          </div>

          {surplus.custodies.length > 0 && (
            <div>
              <Label>{lang === 'ar' ? 'ترحيل فائض من عهدة سابقة' : 'Carry forward surplus'}</Label>
              <select
                value={carryForward}
                onChange={(e) => setCarryForward(e.target.value)}
                className="w-full p-2 border rounded-lg"
              >
                <option value="">{lang === 'ar' ? '-- بدون ترحيل --' : '-- No carry forward --'}</option>
                {surplus.custodies.map(c => (
                  <option key={c.id} value={c.custody_number}>
                    #{c.custody_number} - {lang === 'ar' ? 'فائض' : 'Surplus'}: {c.remaining.toLocaleString()}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <Label>{lang === 'ar' ? 'ملاحظات' : 'Notes'}</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={lang === 'ar' ? 'ملاحظات اختيارية...' : 'Optional notes...'}
              rows={2}
            />
          </div>

          <div className="flex gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button type="submit" disabled={submitting} className="flex-1 bg-emerald-600 hover:bg-emerald-700">
              {submitting ? '...' : (lang === 'ar' ? 'إنشاء' : 'Create')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Custody Detail Page ====================
function CustodyDetailPage({ custody, expenseCodes, lang, role, canCreate, canAudit, canExecute, onClose, onUpdate }) {
  const [expenses, setExpenses] = useState([]);
  const [localCustody, setLocalCustody] = useState(custody);
  const [loading, setLoading] = useState(true);
  const [newExpense, setNewExpense] = useState({ code: '', description: '', amount: '', custom_name: '' });
  const [codeInfo, setCodeInfo] = useState(null);
  const [auditComment, setAuditComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchCustodyDetails();
  }, [custody.id]);

  const fetchCustodyDetails = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/admin-custody/${custody.id}`);
      setLocalCustody(res.data);
      setExpenses(res.data.expenses || []);
    } catch (err) {
      toast.error('Failed to load');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => (num || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // البحث عن الكود عند الكتابة
  const handleCodeChange = useCallback((value) => {
    setNewExpense(prev => ({ ...prev, code: value }));
    const code = parseInt(value);
    if (code > 0) {
      const found = expenseCodes.find(c => c.code === code);
      setCodeInfo(found || (code > 60 ? { is_new: true } : null));
    } else {
      setCodeInfo(null);
    }
  }, [expenseCodes]);

  const handleAddExpense = async () => {
    const code = parseInt(newExpense.code);
    if (!code || !newExpense.description || !newExpense.amount) {
      toast.error(lang === 'ar' ? 'أكمل جميع الحقول' : 'Complete all fields');
      return;
    }
    
    if (parseFloat(newExpense.amount) > localCustody.remaining) {
      toast.error(lang === 'ar' ? 'المبلغ أكبر من المتبقي!' : 'Amount exceeds remaining!');
      return;
    }

    setSubmitting(true);
    try {
      await api.post(`/api/admin-custody/${custody.id}/expenses`, {
        code,
        description: newExpense.description,
        amount: parseFloat(newExpense.amount),
        custom_name: codeInfo?.is_new ? newExpense.custom_name : null
      });
      toast.success(lang === 'ar' ? 'تمت الإضافة' : 'Added');
      setNewExpense({ code: '', description: '', amount: '', custom_name: '' });
      setCodeInfo(null);
      fetchCustodyDetails();
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelExpense = async (expenseId) => {
    if (!confirm(lang === 'ar' ? 'إلغاء هذا المصروف؟' : 'Cancel this expense?')) return;
    try {
      await api.delete(`/api/admin-custody/${custody.id}/expenses/${expenseId}`);
      toast.success(lang === 'ar' ? 'تم الإلغاء' : 'Cancelled');
      fetchCustodyDetails();
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const handleSendForAudit = async () => {
    try {
      await api.post(`/api/admin-custody/${custody.id}/send-for-audit`);
      toast.success(lang === 'ar' ? 'تم الإرسال للتدقيق' : 'Sent for audit');
      fetchCustodyDetails();
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const handleAudit = async (action) => {
    try {
      await api.post(`/api/admin-custody/${custody.id}/audit`, { action, comment: auditComment });
      toast.success(action === 'approve' ? (lang === 'ar' ? 'تم الاعتماد' : 'Approved') : (lang === 'ar' ? 'تم الإرجاع' : 'Rejected'));
      setAuditComment('');
      fetchCustodyDetails();
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const handleExecute = async () => {
    try {
      await api.post(`/api/admin-custody/${custody.id}/execute`);
      toast.success(lang === 'ar' ? 'تم التنفيذ' : 'Executed');
      fetchCustodyDetails();
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const handleClose = async () => {
    try {
      await api.post(`/api/admin-custody/${custody.id}/close`);
      toast.success(lang === 'ar' ? 'تم الإغلاق' : 'Closed');
      fetchCustodyDetails();
      onUpdate();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const isEditable = localCustody.status === 'open' && canCreate;
  const activeExpenses = expenses.filter(e => e.status === 'active');

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[95vh] overflow-y-auto p-0">
        {/* Header */}
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white p-6 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">
                {lang === 'ar' ? 'العهدة رقم' : 'Custody #'} {localCustody.custody_number}
              </h2>
              <p className="text-emerald-100 text-sm">{localCustody.created_by_name}</p>
            </div>
            <div className="text-left">
              <p className="text-3xl font-bold">{formatNumber(localCustody.remaining)}</p>
              <p className="text-emerald-100 text-xs">{lang === 'ar' ? 'المتبقي' : 'Remaining'}</p>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mt-4">
            <div className="flex justify-between text-xs mb-1">
              <span>{lang === 'ar' ? 'المصروف' : 'Spent'}: {formatNumber(localCustody.spent)}</span>
              <span>{lang === 'ar' ? 'الإجمالي' : 'Total'}: {formatNumber(localCustody.total_amount)}</span>
            </div>
            <div className="w-full bg-emerald-800 rounded-full h-3">
              <div 
                className="h-3 rounded-full bg-white transition-all"
                style={{ width: `${(localCustody.spent / localCustody.total_amount) * 100}%` }}
              />
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Add Expense Form - Excel Style */}
          {isEditable && (
            <Card className="border-2 border-emerald-200">
              <CardHeader className="bg-emerald-50 py-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Plus size={18} />
                  {lang === 'ar' ? 'إضافة مصروف' : 'Add Expense'}
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <div className="grid grid-cols-12 gap-3 items-end">
                  {/* Code */}
                  <div className="col-span-2">
                    <Label className="text-xs">{lang === 'ar' ? 'الكود' : 'Code'}</Label>
                    <Input
                      type="number"
                      value={newExpense.code}
                      onChange={(e) => handleCodeChange(e.target.value)}
                      placeholder="1-60+"
                      className="font-mono text-center"
                      min="1"
                    />
                  </div>
                  
                  {/* Auto-filled Name */}
                  <div className="col-span-3">
                    <Label className="text-xs">{lang === 'ar' ? 'اسم المصروف' : 'Expense Name'}</Label>
                    {codeInfo?.is_new ? (
                      <Input
                        value={newExpense.custom_name}
                        onChange={(e) => setNewExpense(prev => ({ ...prev, custom_name: e.target.value }))}
                        placeholder={lang === 'ar' ? 'اسم جديد...' : 'New name...'}
                        className="bg-yellow-50 border-yellow-300"
                      />
                    ) : (
                      <div className="p-2 bg-slate-100 rounded-lg text-sm font-medium truncate">
                        {codeInfo ? (lang === 'ar' ? codeInfo.name_ar : codeInfo.name_en) : '-'}
                      </div>
                    )}
                  </div>

                  {/* Description */}
                  <div className="col-span-4">
                    <Label className="text-xs">{lang === 'ar' ? 'البيان' : 'Description'}</Label>
                    <Input
                      value={newExpense.description}
                      onChange={(e) => setNewExpense(prev => ({ ...prev, description: e.target.value }))}
                      placeholder={lang === 'ar' ? 'لماذا صُرف؟' : 'Why spent?'}
                    />
                  </div>

                  {/* Amount */}
                  <div className="col-span-2">
                    <Label className="text-xs">{lang === 'ar' ? 'المبلغ' : 'Amount'}</Label>
                    <Input
                      type="number"
                      value={newExpense.amount}
                      onChange={(e) => setNewExpense(prev => ({ ...prev, amount: e.target.value }))}
                      placeholder="0.00"
                      className="font-mono"
                      step="0.01"
                    />
                  </div>

                  {/* Add Button */}
                  <div className="col-span-1">
                    <Button 
                      onClick={handleAddExpense} 
                      disabled={submitting}
                      className="w-full bg-emerald-600 hover:bg-emerald-700"
                    >
                      <Plus size={18} />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Expenses Table - Excel Style */}
          <Card>
            <CardHeader className="bg-slate-800 text-white py-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileSpreadsheet size={18} />
                  {lang === 'ar' ? 'المصروفات' : 'Expenses'}
                </span>
                <span className="text-sm font-normal">{activeExpenses.length} {lang === 'ar' ? 'سجل' : 'records'}</span>
              </CardTitle>
            </CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="p-3 text-right w-16">{lang === 'ar' ? 'الكود' : 'Code'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'المصروف' : 'Expense'}</th>
                    <th className="p-3 text-right">{lang === 'ar' ? 'البيان' : 'Description'}</th>
                    <th className="p-3 text-left w-28">{lang === 'ar' ? 'المبلغ' : 'Amount'}</th>
                    {isEditable && <th className="p-3 w-12"></th>}
                  </tr>
                </thead>
                <tbody>
                  {activeExpenses.length === 0 ? (
                    <tr>
                      <td colSpan={isEditable ? 5 : 4} className="p-8 text-center text-slate-500">
                        {lang === 'ar' ? 'لا توجد مصروفات' : 'No expenses'}
                      </td>
                    </tr>
                  ) : (
                    activeExpenses.map((exp, idx) => (
                      <tr key={exp.id} className={`border-b ${idx % 2 ? 'bg-slate-50' : ''}`}>
                        <td className="p-3 font-mono font-bold text-emerald-700 text-center">{exp.code}</td>
                        <td className="p-3 font-medium">{lang === 'ar' ? exp.code_name_ar : exp.code_name_en}</td>
                        <td className="p-3 text-slate-600">{exp.description}</td>
                        <td className="p-3 font-mono font-bold text-red-600">{formatNumber(exp.amount)}</td>
                        {isEditable && (
                          <td className="p-3">
                            <Button size="sm" variant="ghost" onClick={() => handleCancelExpense(exp.id)}>
                              <Trash2 size={14} className="text-red-500" />
                            </Button>
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
                <tfoot className="bg-slate-800 text-white font-bold">
                  <tr>
                    <td colSpan={3} className="p-3 text-right">{lang === 'ar' ? 'الإجمالي' : 'Total'}</td>
                    <td className="p-3 font-mono">{formatNumber(localCustody.spent)}</td>
                    {isEditable && <td></td>}
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>

          {/* Actions */}
          <Card className="border-2">
            <CardContent className="p-4">
              <div className="flex flex-wrap gap-3">
                {/* Send for Audit */}
                {localCustody.status === 'open' && canCreate && (
                  <Button onClick={handleSendForAudit} className="bg-orange-500 hover:bg-orange-600 gap-2">
                    <Send size={16} />
                    {lang === 'ar' ? 'إرسال للتدقيق' : 'Send for Audit'}
                  </Button>
                )}

                {/* Audit Actions */}
                {localCustody.status === 'pending_audit' && canAudit && (
                  <div className="flex-1 space-y-3">
                    <Textarea
                      value={auditComment}
                      onChange={(e) => setAuditComment(e.target.value)}
                      placeholder={lang === 'ar' ? 'تعليق التدقيق...' : 'Audit comment...'}
                      rows={2}
                    />
                    <div className="flex gap-2">
                      <Button onClick={() => handleAudit('approve')} className="bg-green-600 hover:bg-green-700 gap-2 flex-1">
                        <CheckCircle size={16} />
                        {lang === 'ar' ? 'اعتماد' : 'Approve'}
                      </Button>
                      <Button onClick={() => handleAudit('reject')} variant="destructive" className="gap-2 flex-1">
                        <XCircle size={16} />
                        {lang === 'ar' ? 'إرجاع' : 'Reject'}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Execute */}
                {localCustody.status === 'approved' && canExecute && (
                  <Button onClick={handleExecute} className="bg-purple-600 hover:bg-purple-700 gap-2">
                    <Play size={16} />
                    {lang === 'ar' ? 'تنفيذ' : 'Execute'}
                  </Button>
                )}

                {/* Close */}
                {localCustody.status === 'executed' && (canCreate || canExecute) && (
                  <Button onClick={handleClose} className="bg-slate-700 hover:bg-slate-800 gap-2">
                    <Lock size={16} />
                    {lang === 'ar' ? 'إغلاق العهدة' : 'Close Custody'}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  );
}
