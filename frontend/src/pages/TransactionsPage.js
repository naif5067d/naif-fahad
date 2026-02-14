import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FileText, Download, Check, X as XIcon, Search, Eye, Loader2, Filter, ChevronLeft, ChevronRight, Clock, User } from 'lucide-react';
import { formatSaudiDateTime, formatRelativeTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

// Status configuration with colors
const STATUS_CONFIG = {
  executed: { bg: 'bg-emerald-500/10', text: 'text-emerald-600', border: 'border-emerald-500/20', labelAr: 'منفذة', labelEn: 'Executed' },
  rejected: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', labelAr: 'مرفوضة', labelEn: 'Rejected' },
  cancelled: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', labelAr: 'ملغاة', labelEn: 'Cancelled' },
  pending_supervisor: { bg: 'bg-blue-500/10', text: 'text-blue-600', border: 'border-blue-500/20', labelAr: 'بانتظار المشرف', labelEn: 'Pending Supervisor' },
  pending_ops: { bg: 'bg-orange-500/10', text: 'text-orange-600', border: 'border-orange-500/20', labelAr: 'بانتظار العمليات', labelEn: 'Pending Ops' },
  pending_finance: { bg: 'bg-teal-500/10', text: 'text-teal-600', border: 'border-teal-500/20', labelAr: 'بانتظار المالية', labelEn: 'Pending Finance' },
  pending_ceo: { bg: 'bg-red-600/10', text: 'text-red-700', border: 'border-red-600/20', labelAr: 'بانتظار الرئيس', labelEn: 'Pending CEO' },
  pending_stas: { bg: 'bg-violet-500/10', text: 'text-violet-600', border: 'border-violet-500/20', labelAr: 'بانتظار ستاس', labelEn: 'Pending STAS' },
  pending_employee_accept: { bg: 'bg-sky-500/10', text: 'text-sky-600', border: 'border-sky-500/20', labelAr: 'بانتظار الموظف', labelEn: 'Pending Employee' },
};

// Type icons config
const TYPE_CONFIG = {
  leave_request: { icon: '📅', labelAr: 'طلب إجازة', labelEn: 'Leave Request' },
  finance_60: { icon: '💰', labelAr: 'عهدة مالية', labelEn: 'Financial Custody' },
  settlement: { icon: '📊', labelAr: 'تسوية', labelEn: 'Settlement' },
  contract: { icon: '📋', labelAr: 'عقد', labelEn: 'Contract' },
  tangible_custody: { icon: '📦', labelAr: 'عهدة ملموسة', labelEn: 'Tangible Custody' },
  salary_advance: { icon: '💵', labelAr: 'سلفة راتب', labelEn: 'Salary Advance' },
  letter_request: { icon: '✉️', labelAr: 'طلب خطاب', labelEn: 'Letter Request' },
};

export default function TransactionsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [filter, setFilter] = useState({ status: '', type: '' });
  const [search, setSearch] = useState('');
  const [actionDialog, setActionDialog] = useState(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);

  const fetchTxs = async () => {
    setFetchLoading(true);
    try {
      const params = {};
      if (filter.status) params.status = filter.status;
      if (filter.type) params.tx_type = filter.type;
      const res = await api.get('/api/transactions', { params });
      setTransactions(res.data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setFetchLoading(false);
    }
  };

  useEffect(() => { fetchTxs(); }, [filter]);

  const filtered = transactions.filter(tx => {
    if (!search) return true;
    const s = search.toLowerCase();
    return tx.ref_no?.toLowerCase().includes(s) || 
           tx.data?.employee_name?.toLowerCase().includes(s) || 
           tx.data?.employee_name_ar?.includes(search) ||
           tx.type?.includes(s);
  });

  const handleAction = async (action) => {
    if (!actionDialog) return;
    setLoading(true);
    try {
      await api.post(`/api/transactions/${actionDialog.id}/action`, { action, note });
      const msg = action === 'approve' ? t('transactions.approve') : action === 'escalate' ? t('transactions.escalate') : t('transactions.reject');
      toast.success(msg);
      setActionDialog(null);
      setNote('');
      fetchTxs();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status) => STATUS_CONFIG[status] || STATUS_CONFIG.pending_ops;
  const getTypeConfig = (type) => TYPE_CONFIG[type] || { icon: '📄', labelAr: type, labelEn: type };
  
  const getStatusLabel = (status) => {
    const config = getStatusConfig(status);
    return lang === 'ar' ? config.labelAr : config.labelEn;
  };
  
  const getTypeLabel = (type) => {
    const config = getTypeConfig(type);
    return lang === 'ar' ? config.labelAr : config.labelEn;
  };
  
  const getStageLabel = (stage) => {
    if (stage === 'stas') return lang === 'ar' ? 'ستاس' : 'STAS';
    const stages = {
      supervisor: { ar: 'المشرف', en: 'Supervisor' },
      ops: { ar: 'العمليات', en: 'Operations' },
      finance: { ar: 'المالية', en: 'Finance' },
      ceo: { ar: 'الرئيس', en: 'CEO' },
      employee_accept: { ar: 'قبول الموظف', en: 'Employee Accept' },
    };
    return stages[stage] ? (lang === 'ar' ? stages[stage].ar : stages[stage].en) : stage;
  };

  const canApprove = (tx) => {
    // Check if user has already acted on this transaction
    const hasAlreadyActed = tx.approval_chain?.some(
      approval => approval.approver_id === user?.id
    );
    if (hasAlreadyActed) return false;
    
    const map = {
      pending_supervisor: ['supervisor', 'sultan', 'naif'],
      pending_ops: ['sultan', 'naif'],
      pending_finance: ['salah'],
      pending_ceo: ['mohammed'],
      pending_stas: ['stas'],
      pending_employee_accept: ['employee'],
    };
    return map[tx.status]?.includes(user?.role);
  };

  const canEscalate = (tx) => {
    // Check if user has already acted on this transaction
    const hasAlreadyActed = tx.approval_chain?.some(
      approval => approval.approver_id === user?.id
    );
    if (hasAlreadyActed) return false;
    
    if (user?.role !== 'sultan') return false;
    return ['pending_supervisor', 'pending_ops'].includes(tx.status);
  };

  // Get employee name based on language
  const getEmployeeName = (tx) => {
    if (lang === 'ar') {
      return tx.data?.employee_name_ar || tx.data?.employee_name || '-';
    }
    return tx.data?.employee_name || '-';
  };

  return (
    <div className="space-y-6" data-testid="transactions-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {lang === 'ar' ? 'المعاملات' : 'Transactions'}
          </h1>
          <p className="text-muted-foreground mt-1">
            {fetchLoading ? (lang === 'ar' ? 'جارٍ التحميل...' : 'Loading...') : `${filtered.length} ${lang === 'ar' ? 'معاملة' : 'transactions'}`}
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`p-3 rounded-xl border transition-all ${showFilters ? 'bg-primary text-primary-foreground border-primary shadow-lg' : 'border-border hover:bg-muted hover:border-primary/30'}`}
          data-testid="toggle-filters"
        >
          <Filter size={18} />
        </button>
      </div>

      {/* Search & Filters */}
      <div className="space-y-3">
        {/* Search */}
        <div className="relative">
          <Search size={18} className="absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            data-testid="search-input"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={lang === 'ar' ? 'البحث في المعاملات...' : 'Search transactions...'}
            className="ps-11 h-12 rounded-xl bg-muted/30 border-border/50 focus:border-primary text-base"
          />
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="flex flex-col sm:flex-row gap-3 p-4 bg-muted/30 rounded-xl border border-border/50 animate-fade-in">
            <Select value={filter.status || 'all'} onValueChange={v => setFilter({...filter, status: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="status-filter">
                <SelectValue placeholder={lang === 'ar' ? 'الحالة' : 'Status'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{lang === 'ar' ? 'جميع الحالات' : 'All Statuses'}</SelectItem>
                <SelectItem value="pending_supervisor">{lang === 'ar' ? 'بانتظار المشرف' : 'Pending Supervisor'}</SelectItem>
                <SelectItem value="pending_ops">{lang === 'ar' ? 'بانتظار العمليات' : 'Pending Ops'}</SelectItem>
                <SelectItem value="pending_finance">{lang === 'ar' ? 'بانتظار المالية' : 'Pending Finance'}</SelectItem>
                <SelectItem value="pending_stas">{lang === 'ar' ? 'بانتظار ستاس' : 'Pending STAS'}</SelectItem>
                <SelectItem value="executed">{lang === 'ar' ? 'منفذة' : 'Executed'}</SelectItem>
                <SelectItem value="rejected">{lang === 'ar' ? 'مرفوضة' : 'Rejected'}</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filter.type || 'all'} onValueChange={v => setFilter({...filter, type: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="type-filter">
                <SelectValue placeholder={lang === 'ar' ? 'النوع' : 'Type'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{lang === 'ar' ? 'جميع الأنواع' : 'All Types'}</SelectItem>
                <SelectItem value="leave_request">{lang === 'ar' ? 'طلب إجازة' : 'Leave Request'}</SelectItem>
                <SelectItem value="salary_advance">{lang === 'ar' ? 'سلفة راتب' : 'Salary Advance'}</SelectItem>
                <SelectItem value="letter_request">{lang === 'ar' ? 'طلب خطاب' : 'Letter Request'}</SelectItem>
                <SelectItem value="tangible_custody">{lang === 'ar' ? 'عهدة ملموسة' : 'Tangible Custody'}</SelectItem>
              </SelectContent>
            </Select>
            {(filter.status || filter.type) && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setFilter({ status: '', type: '' })}
                className="h-11 px-4"
              >
                {lang === 'ar' ? 'مسح' : 'Clear'}
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Transactions List */}
      <div className="space-y-3">
        {fetchLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 bg-muted/20 rounded-2xl border border-dashed border-border">
            <FileText size={48} className="mx-auto mb-4 text-muted-foreground/40" />
            <p className="text-lg font-medium text-muted-foreground">
              {lang === 'ar' ? 'لا توجد معاملات' : 'No transactions found'}
            </p>
            <p className="text-sm text-muted-foreground/70 mt-1">
              {lang === 'ar' ? 'جرب تغيير معايير البحث' : 'Try changing the search criteria'}
            </p>
          </div>
        ) : (
          filtered.map(tx => {
            const statusConfig = getStatusConfig(tx.status);
            const typeConfig = getTypeConfig(tx.type);
            const showActions = canApprove(tx);
            const showEscalate = canEscalate(tx);
            
            return (
              <div
                key={tx.id}
                className="group bg-card hover:bg-muted/30 rounded-2xl border border-border/60 hover:border-primary/30 transition-all duration-200 overflow-hidden"
                data-testid={`tx-row-${tx.ref_no}`}
              >
                {/* Main Content */}
                <div className="p-4 sm:p-5">
                  {/* Top Row - Type Badge & Status */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex items-center gap-3">
                      {/* Type Icon */}
                      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-xl flex-shrink-0">
                        {typeConfig.icon}
                      </div>
                      {/* Type & Ref */}
                      <div>
                        <h3 className="font-semibold text-base">{getTypeLabel(tx.type)}</h3>
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">{tx.ref_no}</p>
                      </div>
                    </div>
                    {/* Status Badge */}
                    <span className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-semibold border ${statusConfig.bg} ${statusConfig.text} ${statusConfig.border}`}>
                      {getStatusLabel(tx.status)}
                    </span>
                  </div>
                  
                  {/* Info Row */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm mb-4">
                    {/* Employee */}
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <User size={14} />
                      <span>{getEmployeeName(tx)}</span>
                    </div>
                    {/* Time */}
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Clock size={14} />
                      <span>{formatSaudiDateTime(tx.created_at)}</span>
                    </div>
                    {/* Stage */}
                    <div className="ms-auto text-xs bg-muted/50 px-2 py-1 rounded-md">
                      {lang === 'ar' ? 'المرحلة:' : 'Stage:'} {getStageLabel(tx.current_stage)}
                    </div>
                  </div>

                  {/* Actions Row */}
                  <div className="flex items-center gap-2 pt-3 border-t border-border/50">
                    {/* View Button */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/transactions/${tx.id}`)}
                      className="flex-1 h-10 rounded-xl hover:bg-primary/10 hover:text-primary"
                      data-testid={`view-tx-${tx.ref_no}`}
                    >
                      <Eye size={16} className="me-2" />
                      {lang === 'ar' ? 'عرض التفاصيل' : 'View Details'}
                    </Button>
                    
                    {/* Approve/Reject Buttons */}
                    {showActions && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => setActionDialog({ ...tx, action: 'approve' })}
                          className="h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
                          data-testid={`approve-tx-${tx.ref_no}`}
                        >
                          <Check size={16} className="me-1.5" />
                          {lang === 'ar' ? 'موافقة' : 'Approve'}
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => setActionDialog({ ...tx, action: 'reject' })}
                          className="h-10 w-10 rounded-xl p-0"
                          data-testid={`reject-tx-${tx.ref_no}`}
                        >
                          <XIcon size={16} />
                        </Button>
                      </>
                    )}
                    
                    {/* Escalate Button */}
                    {showEscalate && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setActionDialog({ ...tx, action: 'escalate' })}
                        className="h-10 rounded-xl border-orange-300 text-orange-600 hover:bg-orange-50 hover:border-orange-400"
                        data-testid={`escalate-tx-${tx.ref_no}`}
                      >
                        {lang === 'ar' ? 'تصعيد' : 'Escalate'}
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Action Dialog */}
      <Dialog open={!!actionDialog} onOpenChange={() => setActionDialog(null)}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-xl">
              {actionDialog?.action === 'approve' && (lang === 'ar' ? 'تأكيد الموافقة' : 'Confirm Approval')}
              {actionDialog?.action === 'reject' && (lang === 'ar' ? 'تأكيد الرفض' : 'Confirm Rejection')}
              {actionDialog?.action === 'escalate' && (lang === 'ar' ? 'تأكيد التصعيد' : 'Confirm Escalation')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 pt-2">
            {/* Transaction info */}
            <div className="bg-muted/30 rounded-xl p-4">
              <p className="text-sm font-mono text-muted-foreground">{actionDialog?.ref_no}</p>
              <p className="text-base font-medium mt-1">{getTypeLabel(actionDialog?.type)}</p>
            </div>
            
            {/* Note input */}
            <div>
              <label className="text-sm font-medium mb-2 block">
                {lang === 'ar' ? 'ملاحظة (اختياري)' : 'Note (optional)'}
              </label>
              <Input
                data-testid="action-note-input"
                placeholder={lang === 'ar' ? 'أضف ملاحظة...' : 'Add a note...'}
                value={note}
                onChange={e => setNote(e.target.value)}
                className="h-12 rounded-xl"
              />
            </div>
            
            {/* Action buttons */}
            <div className="flex gap-3 pt-2">
              <Button 
                variant="outline" 
                onClick={() => setActionDialog(null)} 
                className="flex-1 h-12 rounded-xl"
                data-testid="cancel-action"
              >
                {lang === 'ar' ? 'إلغاء' : 'Cancel'}
              </Button>
              <Button
                onClick={() => handleAction(actionDialog?.action)}
                disabled={loading}
                className={`flex-1 h-12 rounded-xl font-semibold ${
                  actionDialog?.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' :
                  actionDialog?.action === 'reject' ? 'bg-red-600 hover:bg-red-700' : 
                  'bg-orange-600 hover:bg-orange-700'
                } text-white`}
                data-testid="confirm-action"
              >
                {loading && <Loader2 size={18} className="animate-spin me-2" />}
                {lang === 'ar' ? 'تأكيد' : 'Confirm'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
