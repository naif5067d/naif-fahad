import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FileText, Download, Check, X as XIcon, Search, Eye } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function TransactionsPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState([]);
  const [filter, setFilter] = useState({ status: '', type: '' });
  const [search, setSearch] = useState('');
  const [actionDialog, setActionDialog] = useState(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);

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
      toast.success(action === 'approve' ? 'Approved' : 'Rejected');
      setActionDialog(null);
      setNote('');
      fetchTxs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Action failed');
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
    } catch { toast.error('PDF download failed'); }
  };

  const canAct = (tx) => {
    const stageRoles = { supervisor: ['supervisor'], ops: ['sultan', 'naif'], finance: ['salah'], ceo: ['mohammed'], stas: ['stas'] };
    return stageRoles[tx.current_stage]?.includes(user?.role) && !['executed', 'rejected'].includes(tx.status);
  };

  const getStatusClass = (status) => {
    if (status === 'executed') return 'status-executed';
    if (status === 'rejected') return 'status-rejected';
    if (status?.startsWith('pending')) return 'status-pending';
    return 'status-created';
  };

  return (
    <div className="space-y-4" data-testid="transactions-page">
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
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="pending_supervisor">Pending Supervisor</SelectItem>
            <SelectItem value="pending_ops">Pending Ops</SelectItem>
            <SelectItem value="pending_finance">Pending Finance</SelectItem>
            <SelectItem value="pending_ceo">Pending CEO</SelectItem>
            <SelectItem value="pending_stas">Pending STAS</SelectItem>
            <SelectItem value="executed">Executed</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filter.type} onValueChange={v => setFilter(f => ({ ...f, type: v === 'all' ? '' : v }))}>
          <SelectTrigger className="w-full sm:w-44" data-testid="tx-filter-type"><SelectValue placeholder={t('transactions.type')} /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="leave_request">Leave Request</SelectItem>
            <SelectItem value="finance_60">Finance 60</SelectItem>
            <SelectItem value="settlement">Settlement</SelectItem>
            <SelectItem value="contract">Contract</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
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
                <tr key={tx.id} data-testid={`tx-row-${tx.ref_no}`}>
                  <td className="font-mono text-xs">{tx.ref_no}</td>
                  <td className="text-sm capitalize">{tx.type?.replace(/_/g, ' ')}</td>
                  <td className="hidden md:table-cell text-sm">{tx.data?.employee_name || '-'}</td>
                  <td><span className={`status-badge ${getStatusClass(tx.status)}`}>{t(`status.${tx.status}`) || tx.status}</span></td>
                  <td className="hidden sm:table-cell text-xs text-muted-foreground">{tx.current_stage}</td>
                  <td className="hidden md:table-cell text-xs text-muted-foreground">{tx.created_at?.slice(0, 10)}</td>
                  <td>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => navigate(`/transactions/${tx.id}`)} data-testid={`view-tx-${tx.ref_no}`}>
                        <Eye size={14} />
                      </Button>
                      {canAct(tx) && user?.role !== 'stas' && (
                        <>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-emerald-600" onClick={() => setActionDialog(tx)} data-testid={`approve-tx-${tx.ref_no}`}>
                            <Check size={14} />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive" onClick={() => { setActionDialog(tx); }} data-testid={`reject-tx-${tx.ref_no}`}>
                            <XIcon size={14} />
                          </Button>
                        </>
                      )}
                      {tx.status === 'executed' && (
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => downloadPdf(tx)} data-testid={`pdf-tx-${tx.ref_no}`}>
                          <Download size={14} />
                        </Button>
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
            <DialogTitle>Transaction Action: {actionDialog?.ref_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Note (optional)</label>
              <Input data-testid="action-note" value={note} onChange={e => setNote(e.target.value)} placeholder="Add a note..." />
            </div>
            <div className="flex gap-3">
              <Button data-testid="confirm-approve" onClick={() => handleAction('approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" disabled={loading}>
                <Check size={16} className="me-1" /> {t('transactions.approve')}
              </Button>
              <Button data-testid="confirm-reject" variant="destructive" onClick={() => handleAction('reject')} className="flex-1" disabled={loading}>
                <XIcon size={16} className="me-1" /> {t('transactions.reject')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
