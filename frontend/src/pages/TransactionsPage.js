import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FileText, Download, Check, X as XIcon, Search, Eye, Loader2, Filter, ChevronRight } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// Status colors
const STATUS_COLORS = {
  executed: { bg: '#10B98120', text: '#10B981' },
  rejected: { bg: '#EF444420', text: '#EF4444' },
  cancelled: { bg: '#EF444420', text: '#EF4444' },
  pending_supervisor: { bg: '#1D4ED820', text: '#1D4ED8' },
  pending_ops: { bg: '#F9731620', text: '#F97316' },
  pending_finance: { bg: '#14B8A620', text: '#14B8A6' },
  pending_ceo: { bg: '#DC262620', text: '#DC2626' },
  pending_stas: { bg: '#A78BFA20', text: '#A78BFA' },
  pending_employee_accept: { bg: '#3B82F620', text: '#3B82F6' },
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

  const fetchTxs = () => {
    const params = {};
    if (filter.status) params.status = filter.status;
    if (filter.type) params.tx_type = filter.type;
    api.get('/api/transactions', { params }).then(r => setTransactions(r.data)).catch(() => {});
  };

  useEffect(() => { fetchTxs(); }, [filter]);

  const filtered = transactions.filter(tx => {
    if (!search) return true;
    const s = search.toLowerCase();
    return tx.ref_no?.toLowerCase().includes(s) || tx.data?.employee_name?.toLowerCase().includes(s) || tx.type?.includes(s);
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

  const getStatusStyle = (status) => STATUS_COLORS[status] || STATUS_COLORS.pending_ops;
  const getTranslatedType = (type) => t(`txTypes.${type}`) || type?.replace(/_/g, ' ');
  const getTranslatedStage = (stage) => {
    if (stage === 'stas') return lang === 'ar' ? 'ستاس' : 'STAS';
    return t(`stages.${stage}`) || stage;
  };

  const canApprove = (tx) => {
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
    if (user?.role !== 'sultan') return false;
    return ['pending_supervisor', 'pending_ops'].includes(tx.status);
  };

  return (
    <div className="space-y-5" data-testid="transactions-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-bold">{t('nav.transactions')}</h1>
          <p className="text-sm text-muted-foreground mt-1">{filtered.length} {lang === 'ar' ? 'معاملة' : 'transactions'}</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`p-2.5 rounded-xl border transition-colors touch-target ${showFilters ? 'bg-primary text-primary-foreground border-primary' : 'border-border hover:bg-muted'}`}
          data-testid="toggle-filters"
        >
          <Filter size={18} />
        </button>
      </div>

      {/* Search & Filters */}
      <div className="space-y-3">
        <div className="relative">
          <Search size={18} className="absolute start-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            data-testid="search-input"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={t('transactions.search')}
            className="ps-10 h-12 rounded-xl bg-muted/50 border-0 text-base"
          />
        </div>

        {showFilters && (
          <div className="flex gap-3 animate-fade-in">
            <Select value={filter.status || 'all'} onValueChange={v => setFilter({...filter, status: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="status-filter">
                <SelectValue placeholder={t('transactions.status')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('transactions.allStatuses')}</SelectItem>
                <SelectItem value="pending_supervisor">{t('status.pending_supervisor')}</SelectItem>
                <SelectItem value="pending_ops">{t('status.pending_ops')}</SelectItem>
                <SelectItem value="pending_finance">{t('status.pending_finance')}</SelectItem>
                <SelectItem value="pending_stas">{t('status.pending_stas')}</SelectItem>
                <SelectItem value="executed">{t('status.executed')}</SelectItem>
                <SelectItem value="rejected">{t('status.rejected')}</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filter.type || 'all'} onValueChange={v => setFilter({...filter, type: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="type-filter">
                <SelectValue placeholder={t('transactions.type')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('transactions.allTypes')}</SelectItem>
                <SelectItem value="leave_request">{t('txTypes.leave_request')}</SelectItem>
                <SelectItem value="salary_advance">{t('txTypes.salary_advance')}</SelectItem>
                <SelectItem value="letter_request">{t('txTypes.letter_request')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Transactions List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="text-center py-16 bg-muted/30 rounded-2xl">
            <FileText size={40} className="mx-auto mb-3 opacity-40" />
            <p className="text-muted-foreground">{t('transactions.noTransactions')}</p>
          </div>
        ) : (
          filtered.map(tx => {
            const statusStyle = getStatusStyle(tx.status);
            const showActions = canApprove(tx);
            const showEscalate = canEscalate(tx);
            return (
              <div
                key={tx.id}
                className="card-premium p-4 space-y-3"
                data-testid={`tx-row-${tx.ref_no}`}
              >
                {/* Top row - Type & Status */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: statusStyle.bg }}
                    >
                      <FileText size={20} style={{ color: statusStyle.text }} />
                    </div>
                    <div>
                      <p className="font-semibold text-base">{getTranslatedType(tx.type)}</p>
                      <p className="text-xs text-muted-foreground font-mono">{tx.ref_no}</p>
                    </div>
                  </div>
                  <span 
                    className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
                    style={{ background: statusStyle.bg, color: statusStyle.text }}
                  >
                    {t(`status.${tx.status}`) || tx.status}
                  </span>
                </div>

                {/* Employee & Stage */}
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {lang === 'ar' ? (tx.data?.employee_name_ar || tx.data?.employee_name) : tx.data?.employee_name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {getTranslatedStage(tx.current_stage)}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t border-border">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate(`/transactions/${tx.id}`)}
                    className="flex-1 h-10 rounded-xl text-sm font-medium"
                    data-testid={`view-tx-${tx.ref_no}`}
                  >
                    <Eye size={16} className="me-2" />
                    {t('transactions.view')}
                  </Button>
                  
                  {showActions && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => setActionDialog({ ...tx, action: 'approve' })}
                        className="flex-1 h-10 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium"
                        data-testid={`approve-tx-${tx.ref_no}`}
                      >
                        <Check size={16} className="me-1" />
                        {t('transactions.approve')}
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
                  
                  {showEscalate && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setActionDialog({ ...tx, action: 'escalate' })}
                      className="h-10 rounded-xl text-sm font-medium"
                      data-testid={`escalate-tx-${tx.ref_no}`}
                    >
                      {t('transactions.escalate')}
                    </Button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Action Dialog */}
      <Dialog open={!!actionDialog} onOpenChange={() => setActionDialog(null)}>
        <DialogContent className="max-w-sm rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg">
              {actionDialog?.action === 'approve' && t('transactions.confirmApprove')}
              {actionDialog?.action === 'reject' && t('transactions.confirmReject')}
              {actionDialog?.action === 'escalate' && t('transactions.confirmEscalate')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{actionDialog?.ref_no}</p>
            <Input
              data-testid="action-note-input"
              placeholder={t('transactions.notePlaceholder')}
              value={note}
              onChange={e => setNote(e.target.value)}
              className="h-12 rounded-xl"
            />
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={() => setActionDialog(null)} 
                className="flex-1 h-11 rounded-xl"
                data-testid="cancel-action"
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={() => handleAction(actionDialog?.action)}
                disabled={loading}
                className={`flex-1 h-11 rounded-xl ${
                  actionDialog?.action === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' :
                  actionDialog?.action === 'reject' ? 'bg-red-600 hover:bg-red-700' : ''
                } text-white`}
                data-testid="confirm-action"
              >
                {loading && <Loader2 size={16} className="animate-spin me-2" />}
                {t('common.confirm')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
