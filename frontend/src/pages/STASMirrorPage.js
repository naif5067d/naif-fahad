import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Shield, CheckCircle, XCircle, Link2, ArrowRight, Loader2, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function STASMirrorPage() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  const [mirror, setMirror] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [loadingMirror, setLoadingMirror] = useState(false);

  useEffect(() => {
    api.get('/api/stas/pending').then(r => setPending(r.data)).catch(() => {});
  }, []);

  const loadMirror = async (txId) => {
    setLoadingMirror(true);
    try {
      const res = await api.get(`/api/stas/mirror/${txId}`);
      setMirror(res.data);
      setSelectedTx(txId);
    } catch (err) {
      toast.error('Failed to load mirror');
    } finally { setLoadingMirror(false); }
  };

  const handleExecute = async () => {
    if (!selectedTx || executing) return;
    setExecuting(true);
    try {
      const res = await api.post(`/api/stas/execute/${selectedTx}`);
      toast.success(`${res.data.ref_no} executed. Hash: ${res.data.pdf_hash?.slice(0, 12)}...`);
      setMirror(null);
      setSelectedTx(null);
      api.get('/api/stas/pending').then(r => setPending(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Execution failed');
    } finally { setExecuting(false); }
  };

  const getStatusClass = (status) => {
    if (status === 'executed') return 'status-executed';
    if (status === 'rejected') return 'status-rejected';
    return 'status-pending';
  };

  return (
    <div className="space-y-6" data-testid="stas-mirror-page">
      <div className="flex items-center gap-3">
        <Shield size={24} className="text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">{t('stas.mirror')}</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending List */}
        <div className="lg:col-span-1">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">Pending Execution</h2>
          <div className="space-y-2">
            {pending.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">{t('common.noData')}</p>
            ) : pending.map(tx => (
              <button
                key={tx.id}
                data-testid={`stas-tx-${tx.ref_no}`}
                onClick={() => loadMirror(tx.id)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedTx === tx.id ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-medium">{tx.ref_no}</span>
                  <span className={`status-badge ${getStatusClass(tx.status)}`}>{tx.status?.replace(/_/g, ' ')}</span>
                </div>
                <p className="text-sm mt-1 capitalize">{tx.type?.replace(/_/g, ' ')}</p>
                <p className="text-xs text-muted-foreground">{tx.data?.employee_name}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Mirror Detail */}
        <div className="lg:col-span-2">
          {loadingMirror ? (
            <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin text-muted-foreground" size={24} /></div>
          ) : !mirror ? (
            <div className="text-center py-12 text-muted-foreground">
              <Shield size={48} className="mx-auto mb-3 opacity-30" />
              <p>Select a transaction to view its mirror</p>
            </div>
          ) : (
            <div className="space-y-4 animate-fade-in">
              {/* Transaction Summary */}
              <Card className="border border-border shadow-none">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-mono">{mirror.transaction?.ref_no}</CardTitle>
                    <Button variant="ghost" size="sm" onClick={() => navigate(`/transactions/${mirror.transaction?.id}`)} data-testid="mirror-view-detail">
                      <Eye size={14} className="me-1" /> Detail
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><span className="text-muted-foreground">Type:</span> <span className="capitalize">{mirror.transaction?.type?.replace(/_/g, ' ')}</span></div>
                    <div><span className="text-muted-foreground">Employee:</span> {mirror.employee?.full_name || '-'}</div>
                  </div>
                </CardContent>
              </Card>

              {/* Pre-Checks */}
              <Card className="border border-border shadow-none" data-testid="pre-checks-card">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    {mirror.all_checks_pass ? <CheckCircle size={16} className="text-emerald-500" /> : <XCircle size={16} className="text-red-500" />}
                    {t('stas.preChecks')}
                    <span className={`ms-auto text-xs ${mirror.all_checks_pass ? 'text-emerald-600' : 'text-red-600'}`}>
                      {mirror.all_checks_pass ? t('stas.allPass') : t('stas.hasFails')}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {mirror.pre_checks?.map((c, i) => (
                      <div key={i} className="flex items-center justify-between p-2 rounded-md bg-muted/50" data-testid={`check-${i}`}>
                        <div className="flex items-center gap-2">
                          {c.status === 'PASS' ? <CheckCircle size={14} className="text-emerald-500" /> : <XCircle size={14} className="text-red-500" />}
                          <span className="text-sm">{c.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{c.detail}</span>
                          <span className={`text-xs font-bold ${c.status === 'PASS' ? 'text-emerald-600' : 'text-red-600'}`}>{c.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Before/After */}
              <Card className="border border-border shadow-none" data-testid="before-after-card">
                <CardHeader className="pb-2"><CardTitle className="text-sm">{t('stas.beforeAfter')}</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-muted/50">
                      <p className="text-xs font-semibold text-muted-foreground mb-2">BEFORE</p>
                      {Object.entries(mirror.before_after?.before || {}).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-sm"><span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span><span className="font-medium">{String(v)}</span></div>
                      ))}
                    </div>
                    <div className="p-3 rounded-lg bg-primary/5 border border-primary/10">
                      <p className="text-xs font-semibold text-primary mb-2">AFTER</p>
                      {Object.entries(mirror.before_after?.after || {}).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-sm"><span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span><span className="font-bold">{String(v)}</span></div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Trace Links */}
              <Card className="border border-border shadow-none" data-testid="trace-links-card">
                <CardHeader className="pb-2"><CardTitle className="text-sm">{t('stas.traceLinks')}</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {mirror.trace_links?.map((link, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm p-1.5">
                        <Link2 size={14} className="text-muted-foreground" />
                        <span>{link.label}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Execute Button */}
              <Button
                data-testid="stas-execute-btn"
                onClick={handleExecute}
                disabled={!mirror.all_checks_pass || executing}
                className={`w-full h-12 text-base font-semibold ${mirror.all_checks_pass ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-muted text-muted-foreground cursor-not-allowed'}`}
              >
                {executing ? <><Loader2 size={18} className="me-2 animate-spin" /> {t('stas.executing')}</> : <><Shield size={18} className="me-2" /> {t('stas.execute')}</>}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
