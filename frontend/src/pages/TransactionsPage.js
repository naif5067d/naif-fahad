import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FileText, Download, Check, X as XIcon, Search, Eye, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// Status colors based on the role required for approval
const STATUS_COLORS = {
  executed: '#16A34A',      // Green - completed
  rejected: '#DC2626',      // Red - rejected/cancelled
  cancelled: '#DC2626',     // Red - cancelled
  pending_supervisor: '#1D4ED8', // Supervisor blue
  pending_ops: '#F97316',   // Sultan orange
  pending_finance: '#0D9488', // Salah teal
  pending_ceo: '#B91C1C',   // Mohammed red
  pending_stas: '#7C3AED',  // STAS purple
  pending_employee_accept: '#3B82F6', // Employee blue
};

// Fixed role colors as per requirements
const ROLE_COLORS = {
  employee: '#3B82F6',
  supervisor: '#1D4ED8',
  sultan: '#F97316',
  mohammed: '#B91C1C',
  stas: '#7C3AED',
  naif: '#4D7C0F',
  salah: '#0D9488',
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
  const [selectedForAction, setSelectedForAction] = useState(null);

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
      setSelectedForAction(null);
      fetchTxs();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const downloadPdf = async (tx) => {
    try {
      const res = await api.get(`/api/transactions/${tx.id}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url; a.download = `${tx.ref_no}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error(t('transactions.downloadPdf') + ' failed'); }
  };

  const previewPdf = async (tx) => {
    try {
      const res = await api.get(`/api/transactions/${tx.id}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch { toast.error(t('transactions.previewPdf') + ' failed'); }
  };

  const canAct = (tx) => {
    const stageRoles = { supervisor: ['supervisor'], ops: ['sultan', 'naif'], finance: ['salah'], ceo: ['mohammed'], stas: ['stas'] };
    // Employee can act on employee_accept stage if they are the assigned employee
    if (tx.current_stage === 'employee_accept' && user?.role === 'employee') return true;
    return stageRoles[tx.current_stage]?.includes(user?.role) && !['executed', 'rejected', 'cancelled'].includes(tx.status);
  };

  const canEscalate = (tx) => {
    return tx.current_stage === 'ops' && ['sultan', 'naif'].includes(user?.role) && !['executed', 'rejected', 'cancelled'].includes(tx.status);
  };

  // Get status style with role-based colors
  const getStatusStyle = (status) => {
    const color = STATUS_COLORS[status] || STATUS_COLORS.pending_ops;
    if (status === 'executed') {
      return { backgroundColor: `${STATUS_COLORS.executed}15`, color: STATUS_COLORS.executed, borderColor: `${STATUS_COLORS.executed}30` };
    }
    if (status === 'rejected') {
      return { backgroundColor: `${STATUS_COLORS.rejected}15`, color: STATUS_COLORS.rejected, borderColor: `${STATUS_COLORS.rejected}30` };
    }
    // For pending statuses, use the specific role color
    if (STATUS_COLORS[status]) {
      return { backgroundColor: `${STATUS_COLORS[status]}15`, color: STATUS_COLORS[status], borderColor: `${STATUS_COLORS[status]}30` };
    }
    // Default fallback
    return { backgroundColor: '#F9731615', color: '#F97316', borderColor: '#F9731630' };
  };

  // Get translated type
  const getTranslatedType = (type) => t(`txTypes.${type}`) || type?.replace(/_/g, ' ');
  
  // Get translated stage
  const getTranslatedStage = (stage) => {
    // Handle STAS specifically
    if (stage === 'stas') return lang === 'ar' ? 'ستاس' : 'STAS';
    return t(`stages.${stage}`) || stage;
  };

  // Get actionable transactions for mobile bar
  const actionableTx = selectedForAction ? transactions.find(tx => tx.id === selectedForAction && canAct(tx)) : null;

  return (
    <div className={`space-y-4 ${actionableTx ? 'pb-24 md:pb-4' : ''}`} data-testid="transactions-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">{t('transactions.title')}</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input data-testid="tx-search" value={search} onChange={e => setSearch(e.target.value)} placeholder={t('common.search')} className="ps-9" />
        </div>
        <Select value={filter.status} onValueChange={v => setFilter(f => ({ ...f, status: v === 'all' ? '' : v }))}>
          <SelectTrigger className="w-full sm:w-44" data-testid="tx-filter-status"><SelectValue placeholder={t('transactions.status')} /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('common.all')}</SelectItem>
            <SelectItem value="pending_supervisor">{t('status.pending_supervisor')}</SelectItem>
            <SelectItem value="pending_ops">{t('status.pending_ops')}</SelectItem>
            <SelectItem value="pending_finance">{t('status.pending_finance')}</SelectItem>
            <SelectItem value="pending_ceo">{t('status.pending_ceo')}</SelectItem>
            <SelectItem value="pending_employee_accept">{t('status.pending_employee_accept')}</SelectItem>
            <SelectItem value="pending_stas">{t('status.pending_stas')}</SelectItem>
            <SelectItem value="executed">{t('status.executed')}</SelectItem>
            <SelectItem value="rejected">{t('status.rejected')}</SelectItem>
            <SelectItem value="cancelled">{t('status.cancelled')}</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filter.type} onValueChange={v => setFilter(f => ({ ...f, type: v === 'all' ? '' : v }))}>
          <SelectTrigger className="w-full sm:w-44" data-testid="tx-filter-type"><SelectValue placeholder={t('transactions.type')} /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('common.all')}</SelectItem>
            <SelectItem value="leave_request">{t('txTypes.leave_request')}</SelectItem>
            <SelectItem value="finance_60">{t('txTypes.finance_60')}</SelectItem>
            <SelectItem value="tangible_custody">{t('txTypes.tangible_custody')}</SelectItem>
            <SelectItem value="tangible_custody_return">{t('txTypes.tangible_custody_return')}</SelectItem>
            <SelectItem value="settlement">{t('txTypes.settlement')}</SelectItem>
            <SelectItem value="contract">{t('txTypes.contract')}</SelectItem>
            <SelectItem value="warning">{t('txTypes.warning')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="hr-table" data-testid="transactions-table">
            <thead>
              <tr>
                <th>{t('transactions.refNo')}</th>
                <th>{t('transactions.type')}</th>
                <th className="hidden md:table-cell">{t('transactions.employee')}</th>
                <th>{t('transactions.status')}</th>
                <th className="hidden sm:table-cell">{t('transactions.stage')}</th>
                <th className="hidden md:table-cell">{t('transactions.date')}</th>
                <th>{t('transactions.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-muted-foreground">{t('transactions.noTransactions')}</td></tr>
              ) : filtered.map(tx => (
                <tr 
                  key={tx.id} 
                  data-testid={`tx-row-${tx.ref_no}`}
                  className={selectedForAction === tx.id ? 'bg-primary/5' : ''}
                  onClick={() => canAct(tx) && setSelectedForAction(tx.id)}
                >
                  <td className="font-mono text-xs">{tx.ref_no}</td>
                  <td className="text-sm">{getTranslatedType(tx.type)}</td>
                  <td className="hidden md:table-cell text-sm">{lang === 'ar' ? (tx.data?.employee_name_ar || tx.data?.employee_name) : tx.data?.employee_name || '-'}</td>
                  <td>
                    <span 
                      className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset"
                      style={getStatusStyle(tx.status)}
                    >
                      {t(`status.${tx.status}`) || tx.status}
                    </span>
                  </td>
                  <td className="hidden sm:table-cell text-xs text-muted-foreground">{getTranslatedStage(tx.current_stage)}</td>
                  <td className="hidden md:table-cell text-xs text-muted-foreground">{tx.created_at?.slice(0, 10)}</td>
                  <td>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); navigate(`/transactions/${tx.id}`); }} data-testid={`view-tx-${tx.ref_no}`}>
                        <Eye size={14} />
                      </Button>
                      {canAct(tx) && user?.role !== 'stas' && (
                        <>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-emerald-600 hidden sm:flex" onClick={(e) => { e.stopPropagation(); setActionDialog(tx); }} data-testid={`approve-tx-${tx.ref_no}`}>
                            <Check size={14} />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive hidden sm:flex" onClick={(e) => { e.stopPropagation(); setActionDialog(tx); }} data-testid={`reject-tx-${tx.ref_no}`}>
                            <XIcon size={14} />
                          </Button>
                        </>
                      )}
                      {tx.status === 'executed' && (
                        <>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); previewPdf(tx); }} data-testid={`preview-tx-${tx.ref_no}`}>
                            <FileText size={14} />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); downloadPdf(tx); }} data-testid={`pdf-tx-${tx.ref_no}`}>
                            <Download size={14} />
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Dialog */}
      <Dialog open={!!actionDialog} onOpenChange={() => { setActionDialog(null); setNote(''); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('transactions.transactionAction')}: {actionDialog?.ref_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {actionDialog?.escalated && (
              <div className="bg-orange-50 dark:bg-orange-950/20 border border-orange-200 dark:border-orange-800 rounded-lg p-2">
                <p className="text-xs text-orange-700 dark:text-orange-300 font-medium">{t('transactions.escalated')}</p>
              </div>
            )}
            <div>
              <label className="text-sm font-medium">{t('transactions.actionNote')}</label>
              <Input data-testid="action-note" value={note} onChange={e => setNote(e.target.value)} placeholder={t('transactions.actionNote')} />
            </div>
            <div className="flex gap-3">
              <Button data-testid="confirm-approve" onClick={() => handleAction('approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" disabled={loading}>
                {loading ? <Loader2 size={16} className="me-1 animate-spin" /> : <Check size={16} className="me-1" />} {t('transactions.approve')}
              </Button>
              <Button data-testid="confirm-reject" variant="destructive" onClick={() => handleAction('reject')} className="flex-1" disabled={loading}>
                {loading ? <Loader2 size={16} className="me-1 animate-spin" /> : <XIcon size={16} className="me-1" />} {t('transactions.reject')}
              </Button>
            </div>
            {canEscalate(actionDialog || {}) && (
              <Button data-testid="confirm-escalate" variant="outline" onClick={() => handleAction('escalate')} className="w-full border-orange-400 text-orange-600 hover:bg-orange-50" disabled={loading}>
                {t('transactions.escalate')}
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Mobile Decision Bar */}
      {actionableTx && user?.role !== 'stas' && (
        <div className="fixed bottom-0 left-0 right-0 md:hidden bg-background border-t border-border p-4 shadow-lg z-40" data-testid="mobile-decision-bar">
          <div className="text-center mb-2">
            <p className="text-sm font-medium">{actionableTx.ref_no}</p>
            <p className="text-xs text-muted-foreground">{actionableTx.data?.employee_name}</p>
          </div>
          <div className="flex gap-3 max-w-lg mx-auto">
            <Button 
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => setActionDialog(actionableTx)}
              data-testid="mobile-approve-btn"
            >
              <Check size={16} className="me-1" /> {t('transactions.approve')}
            </Button>
            <Button 
              variant="destructive"
              className="flex-1"
              onClick={() => setActionDialog(actionableTx)}
              data-testid="mobile-reject-btn"
            >
              <XIcon size={16} className="me-1" /> {t('transactions.reject')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
