import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Shield, CheckCircle, XCircle, Link2, Loader2, Eye, Calendar, Trash2, AlertTriangle, Settings, UserX, RotateCcw, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function STASMirrorPage() {
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  const [mirror, setMirror] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [loadingMirror, setLoadingMirror] = useState(false);
  
  // Holiday management
  const [holidays, setHolidays] = useState([]);
  const [newHoliday, setNewHoliday] = useState({ name: '', name_ar: '', date: '' });
  const [holidayDialogOpen, setHolidayDialogOpen] = useState(false);
  
  // Maintenance
  const [purgeConfirm, setPurgeConfirm] = useState('');
  const [purging, setPurging] = useState(false);
  const [archivedUsers, setArchivedUsers] = useState([]);

  useEffect(() => {
    fetchPending();
    fetchHolidays();
    fetchArchivedUsers();
  }, []);

  const fetchPending = () => {
    api.get('/api/stas/pending').then(r => setPending(r.data)).catch(() => {});
  };

  const fetchHolidays = () => {
    api.get('/api/stas/holidays').then(r => setHolidays(r.data)).catch(() => {});
  };

  const fetchArchivedUsers = () => {
    api.get('/api/stas/users/archived').then(r => setArchivedUsers(r.data)).catch(() => {});
  };

  const loadMirror = async (txId) => {
    setLoadingMirror(true);
    try {
      const res = await api.get(`/api/stas/mirror/${txId}`);
      setMirror(res.data);
      setSelectedTx(txId);
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل تحميل المرآة' : 'Failed to load mirror');
    } finally { setLoadingMirror(false); }
  };

  const handleExecute = async () => {
    // منع التنفيذ المكرر
    if (!selectedTx || executing) return;
    
    // تحقق إضافي من حالة المعاملة
    if (mirror?.transaction?.status === 'executed') {
      toast.error(lang === 'ar' ? 'تم تنفيذ هذه المعاملة مسبقاً' : 'Transaction already executed');
      return;
    }
    
    setExecuting(true);
    try {
      const res = await api.post(`/api/stas/execute/${selectedTx}`);
      toast.success(`${res.data.ref_no} ${lang === 'ar' ? 'تم التنفيذ بنجاح' : 'executed successfully'}. Hash: ${res.data.pdf_hash?.slice(0, 12)}...`);
      // إعادة تعيين الحالة ومنع أي ضغط آخر
      setMirror(null);
      setSelectedTx(null);
      fetchPending();
    } catch (err) {
      // عرض رسالة الخطأ بشكل واضح
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'object') {
        toast.error(lang === 'ar' ? errorDetail.message_ar : errorDetail.message_en);
      } else {
        toast.error(errorDetail || (lang === 'ar' ? 'فشل التنفيذ' : 'Execution failed'));
      }
    } finally { 
      setExecuting(false); 
    }
  };

  const previewPdf = async () => {
    if (!selectedTx) return;
    try {
      const res = await api.get(`/api/transactions/${selectedTx}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch {
      toast.error(lang === 'ar' ? 'فشل تحميل PDF' : 'PDF preview failed');
    }
  };

  const addHoliday = async () => {
    if (!newHoliday.name || !newHoliday.name_ar || !newHoliday.date) {
      toast.error(lang === 'ar' ? 'يرجى ملء جميع الحقول' : 'Please fill all fields');
      return;
    }
    try {
      await api.post('/api/stas/holidays', newHoliday);
      toast.success(lang === 'ar' ? 'تمت إضافة العطلة' : 'Holiday added');
      setNewHoliday({ name: '', name_ar: '', date: '' });
      setHolidayDialogOpen(false);
      fetchHolidays();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل الإضافة' : 'Failed to add'));
    }
  };

  const deleteHoliday = async (id) => {
    try {
      await api.delete(`/api/stas/holidays/${id}`);
      toast.success(lang === 'ar' ? 'تم حذف العطلة' : 'Holiday deleted');
      fetchHolidays();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل الحذف' : 'Failed to delete'));
    }
  };

  const purgeTransactions = async () => {
    if (purgeConfirm !== 'CONFIRM') {
      toast.error(t('stas.confirmPurge'));
      return;
    }
    setPurging(true);
    try {
      const res = await api.post('/api/stas/maintenance/purge-transactions', { confirm: true });
      toast.success(`${lang === 'ar' ? 'تم حذف المعاملات' : 'Transactions purged'}: ${res.data.deleted.transactions}`);
      setPurgeConfirm('');
      fetchPending();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setPurging(false); }
  };

  const restoreUser = async (userId) => {
    try {
      await api.post(`/api/stas/users/${userId}/restore`);
      toast.success(lang === 'ar' ? 'تم استعادة المستخدم' : 'User restored');
      fetchArchivedUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const getStatusClass = (status) => {
    if (status === 'executed') return 'status-executed';
    if (status === 'rejected') return 'status-rejected';
    return 'status-pending';
  };

  return (
    <div className="space-y-6 pb-24 md:pb-6" data-testid="stas-mirror-page">
      <div className="flex items-center gap-3">
        <Shield size={24} className="text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">{t('stas.mirror')}</h1>
      </div>

      <Tabs defaultValue="mirror" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="mirror" data-testid="tab-mirror">{t('stas.mirror')}</TabsTrigger>
          <TabsTrigger value="holidays" data-testid="tab-holidays">{t('stas.holidayManagement')}</TabsTrigger>
          <TabsTrigger value="maintenance" data-testid="tab-maintenance">{t('stas.maintenance')}</TabsTrigger>
        </TabsList>

        {/* Mirror Tab */}
        <TabsContent value="mirror" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Pending List */}
            <div className="lg:col-span-1">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t('stas.pendingExecution')}</h2>
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
                  <p>{t('stas.selectTransaction')}</p>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in">
                  {/* Transaction Summary */}
                  <Card className="border border-border shadow-none">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-mono">{mirror.transaction?.ref_no}</CardTitle>
                        <div className="flex gap-2">
                          <Button variant="ghost" size="sm" onClick={previewPdf} data-testid="mirror-preview-pdf">
                            <FileText size={14} className="me-1" /> {t('common.preview')}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/transactions/${mirror.transaction?.id}`)} data-testid="mirror-view-detail">
                            <Eye size={14} className="me-1" /> {t('transactions.viewDetail')}
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div><span className="text-muted-foreground">{t('transactions.type')}:</span> <span className="capitalize">{mirror.transaction?.type?.replace(/_/g, ' ')}</span></div>
                        <div><span className="text-muted-foreground">{t('transactions.employee')}:</span> {mirror.employee?.full_name || '-'}</div>
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
                              <span className="text-sm">{lang === 'ar' ? c.name_ar : c.name}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-muted-foreground">{lang === 'ar' ? c.detail : c.detail}</span>
                              <span className={`text-xs font-bold ${c.status === 'PASS' ? 'text-emerald-600' : 'text-red-600'}`}>
                                {c.status === 'PASS' ? (lang === 'ar' ? 'نجح' : 'PASS') : (lang === 'ar' ? 'فشل' : 'FAIL')}
                              </span>
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
                          <p className="text-xs font-semibold text-muted-foreground mb-2">{lang === 'ar' ? 'قبل' : 'BEFORE'}</p>
                          {Object.entries(mirror.before_after?.before || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between text-sm"><span className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</span><span className="font-medium">{String(v)}</span></div>
                          ))}
                        </div>
                        <div className="p-3 rounded-lg bg-primary/5 border border-primary/10">
                          <p className="text-xs font-semibold text-primary mb-2">{lang === 'ar' ? 'بعد' : 'AFTER'}</p>
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

                  {/* Desktop Execute Button - منع التنفيذ المكرر */}
                  <div className="hidden md:block">
                    {mirror.transaction?.status === 'executed' ? (
                      <div className="w-full h-12 text-base font-semibold bg-emerald-100 text-emerald-700 rounded-md flex items-center justify-center gap-2">
                        <CheckCircle size={18} /> {lang === 'ar' ? 'تم التنفيذ مسبقاً' : 'Already Executed'}
                      </div>
                    ) : (
                      <Button
                        data-testid="stas-execute-btn-desktop"
                        onClick={handleExecute}
                        disabled={!mirror.all_checks_pass || executing}
                        className={`w-full h-12 text-base font-semibold ${mirror.all_checks_pass && !executing ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-muted text-muted-foreground cursor-not-allowed'}`}
                      >
                        {executing ? <><Loader2 size={18} className="me-2 animate-spin" /> {t('stas.executing')}</> : <><Shield size={18} className="me-2" /> {t('stas.execute')}</>}
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Holidays Tab */}
        <TabsContent value="holidays" className="mt-4">
          <Card className="border border-border shadow-none">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar size={18} />
                {t('stas.holidayManagement')}
              </CardTitle>
              <Dialog open={holidayDialogOpen} onOpenChange={setHolidayDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" data-testid="add-holiday-btn">{t('stas.addHoliday')}</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>{t('stas.addHoliday')}</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label>{t('stas.holidayNameEn')}</Label>
                      <Input 
                        data-testid="holiday-name-en"
                        value={newHoliday.name} 
                        onChange={e => setNewHoliday(h => ({ ...h, name: e.target.value }))} 
                      />
                    </div>
                    <div>
                      <Label>{t('stas.holidayNameAr')}</Label>
                      <Input 
                        data-testid="holiday-name-ar"
                        value={newHoliday.name_ar} 
                        onChange={e => setNewHoliday(h => ({ ...h, name_ar: e.target.value }))} 
                        dir="rtl"
                      />
                    </div>
                    <div>
                      <Label>{t('stas.holidayDate')}</Label>
                      <Input 
                        data-testid="holiday-date"
                        type="date" 
                        value={newHoliday.date} 
                        onChange={e => setNewHoliday(h => ({ ...h, date: e.target.value }))} 
                      />
                    </div>
                    <Button onClick={addHoliday} className="w-full" data-testid="submit-holiday">
                      {t('common.add')}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="border border-border rounded-lg overflow-hidden">
                <table className="hr-table" data-testid="holidays-table">
                  <thead>
                    <tr>
                      <th>{t('stas.holidayDate')}</th>
                      <th>{t('stas.holidayNameEn')}</th>
                      <th>{t('stas.holidayNameAr')}</th>
                      <th>{t('common.actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holidays.length === 0 ? (
                      <tr><td colSpan={4} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
                    ) : holidays.map(h => (
                      <tr key={h.id}>
                        <td className="font-mono text-xs">{h.date}</td>
                        <td className="text-sm">{h.name}</td>
                        <td className="text-sm" dir="rtl">{h.name_ar}</td>
                        <td>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-7 w-7 p-0 text-destructive" 
                            onClick={() => deleteHoliday(h.id)}
                            data-testid={`delete-holiday-${h.id}`}
                          >
                            <Trash2 size={14} />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Maintenance Tab */}
        <TabsContent value="maintenance" className="mt-4 space-y-4">
          {/* Purge Transactions */}
          <Card className="border border-destructive/30 shadow-none">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2 text-destructive">
                <AlertTriangle size={18} />
                {t('stas.purgeTransactions')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">{t('stas.purgeWarning')}</p>
              <div className="flex gap-3">
                <Input 
                  data-testid="purge-confirm-input"
                  placeholder={t('stas.confirmPurge')}
                  value={purgeConfirm}
                  onChange={e => setPurgeConfirm(e.target.value)}
                  className="flex-1"
                />
                <Button 
                  variant="destructive" 
                  onClick={purgeTransactions}
                  disabled={purging || purgeConfirm !== 'CONFIRM'}
                  data-testid="purge-transactions-btn"
                >
                  {purging ? <Loader2 size={14} className="animate-spin me-1" /> : <Trash2 size={14} className="me-1" />}
                  {t('stas.purgeTransactions')}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Archived Users */}
          <Card className="border border-border shadow-none">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <UserX size={18} />
                {t('stas.archivedUsers')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {archivedUsers.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">{t('stas.noArchivedUsers')}</p>
              ) : (
                <div className="space-y-2">
                  {archivedUsers.map(u => (
                    <div key={u.id} className="flex items-center justify-between p-3 rounded-lg border border-border">
                      <div>
                        <p className="text-sm font-medium">{u.full_name}</p>
                        <p className="text-xs text-muted-foreground">{u.username} - {u.role}</p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => restoreUser(u.id)}
                        data-testid={`restore-user-${u.id}`}
                      >
                        <RotateCcw size={14} className="me-1" /> {t('stas.restoreUser')}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Mobile Decision Bar - Fixed at bottom - منع التنفيذ المكرر */}
      {mirror && (
        <div className="fixed bottom-0 left-0 right-0 md:hidden bg-background border-t border-border p-4 shadow-lg z-40" data-testid="mobile-decision-bar">
          <div className="flex gap-3 max-w-lg mx-auto">
            <Button 
              variant="outline" 
              className="flex-1"
              onClick={previewPdf}
              data-testid="mobile-preview-btn"
            >
              <FileText size={16} className="me-1" /> {t('common.preview')}
            </Button>
            {mirror.transaction?.status === 'executed' ? (
              <div className="flex-1 h-10 bg-emerald-100 text-emerald-700 rounded-md flex items-center justify-center gap-1 text-sm font-medium">
                <CheckCircle size={14} /> {lang === 'ar' ? 'تم التنفيذ' : 'Executed'}
              </div>
            ) : (
              <Button
                data-testid="stas-execute-btn-mobile"
                onClick={handleExecute}
                disabled={!mirror.all_checks_pass || executing}
                className={`flex-1 ${mirror.all_checks_pass && !executing ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-muted text-muted-foreground'}`}
              >
                {executing ? <Loader2 size={16} className="me-1 animate-spin" /> : <Shield size={16} className="me-1" />}
                {t('stas.execute')}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
