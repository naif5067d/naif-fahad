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
  
  // Cancel/Reject state
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelling, setCancelling] = useState(false);
  
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

  // إلغاء المعاملة - يتطلب تعليق
  const handleCancelTransaction = async () => {
    if (!selectedTx || cancelling) return;
    
    if (!cancelReason || cancelReason.trim().length < 5) {
      toast.error(lang === 'ar' ? 'يجب كتابة سبب الإلغاء (5 أحرف على الأقل)' : 'Cancellation reason is required (at least 5 characters)');
      return;
    }
    
    setCancelling(true);
    try {
      await api.post(`/api/transactions/${selectedTx}/action`, {
        action: 'reject',
        note: cancelReason.trim()
      });
      toast.success(lang === 'ar' ? 'تم إلغاء المعاملة بنجاح' : 'Transaction cancelled successfully');
      setCancelDialogOpen(false);
      setCancelReason('');
      setMirror(null);
      setSelectedTx(null);
      fetchPending();
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'object') {
        toast.error(lang === 'ar' ? errorDetail.message_ar : errorDetail.message_en);
      } else {
        toast.error(errorDetail || (lang === 'ar' ? 'فشل إلغاء المعاملة' : 'Failed to cancel transaction'));
      }
    } finally {
      setCancelling(false);
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

  // ترجمة مفاتيح الـ Before/After
  const translateKey = (key) => {
    const keyTranslations = {
      'total_entitlement': lang === 'ar' ? 'الاستحقاق الكلي' : 'Total Entitlement',
      'used': lang === 'ar' ? 'المستخدم' : 'Used',
      'remaining': lang === 'ar' ? 'المتبقي' : 'Remaining',
      'earned_to_date': lang === 'ar' ? 'المكتسب' : 'Earned to Date',
      'daily_accrual': lang === 'ar' ? 'الاستحقاق اليومي' : 'Daily Accrual',
      'days_worked': lang === 'ar' ? 'أيام العمل' : 'Days Worked',
      'annual_policy': lang === 'ar' ? 'سياسة الإجازة' : 'Annual Policy',
      'balance': lang === 'ar' ? 'الرصيد' : 'Balance',
      'amount': lang === 'ar' ? 'المبلغ' : 'Amount',
      'code': lang === 'ar' ? 'الكود' : 'Code',
      'type': lang === 'ar' ? 'النوع' : 'Type',
      'days': lang === 'ar' ? 'الأيام' : 'Days',
      'leave_type': lang === 'ar' ? 'نوع الإجازة' : 'Leave Type',
      'description': lang === 'ar' ? 'الوصف' : 'Description',
    };
    return keyTranslations[key] || key.replace(/_/g, ' ');
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
                          <div key={i} className={`p-2 rounded-md ${c.status === 'WARN' ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200' : 'bg-muted/50'}`} data-testid={`check-${i}`}>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                {c.status === 'PASS' ? <CheckCircle size={14} className="text-emerald-500" /> : c.status === 'WARN' ? <AlertTriangle size={14} className="text-amber-500" /> : <XCircle size={14} className="text-red-500" />}
                                <span className="text-sm">{lang === 'ar' ? c.name_ar : c.name}</span>
                              </div>
                              <span className={`text-xs font-bold ${c.status === 'PASS' ? 'text-emerald-600' : c.status === 'WARN' ? 'text-amber-600' : 'text-red-600'}`}>
                                {c.status === 'PASS' ? (lang === 'ar' ? 'نجح' : 'PASS') : c.status === 'WARN' ? (lang === 'ar' ? 'تحذير' : 'WARN') : (lang === 'ar' ? 'فشل' : 'FAIL')}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">{c.detail}</p>
                            
                            {/* عرض تفاصيل الإجازة المرضية */}
                            {c.sick_leave_info && (
                              <div className="mt-2 p-2 bg-amber-100 dark:bg-amber-900/30 rounded text-xs space-y-1">
                                <div className="flex justify-between">
                                  <span>{lang === 'ar' ? 'الاستهلاك الحالي:' : 'Current usage:'}</span>
                                  <span className="font-bold">{c.sick_leave_info.current_used} / 120 {lang === 'ar' ? 'يوم' : 'days'}</span>
                                </div>
                                {c.sick_leave_info.tier_distribution?.map((tier, ti) => (
                                  <div key={ti} className={`p-1 rounded ${tier.salary_percent === 100 ? 'bg-emerald-100 text-emerald-800' : tier.salary_percent === 50 ? 'bg-amber-200 text-amber-900' : 'bg-red-100 text-red-800'}`}>
                                    {tier.days} {lang === 'ar' ? 'يوم' : 'days'} → {tier.salary_percent === 100 ? (lang === 'ar' ? 'براتب كامل' : 'Full pay') : tier.salary_percent === 50 ? (lang === 'ar' ? 'نصف راتب' : 'Half pay') : (lang === 'ar' ? 'بدون راتب' : 'No pay')}
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* زر عرض الملف الطبي */}
                            {c.medical_file_url && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => window.open(c.medical_file_url, '_blank')}
                                className="mt-2 text-xs h-7 border-red-300 text-red-600"
                              >
                                <FileText size={12} className="me-1" />
                                {lang === 'ar' ? 'معاينة التقرير' : 'Preview Report'}
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Leave Calculation Details - سجل الإجازات - STAS فقط */}
                  {mirror.transaction?.type === 'leave_request' && mirror.transaction?.data?.calculation_details && (
                    <Card className="border-2 border-violet-500/30 shadow-none" data-testid="leave-calculation-card">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm flex items-center gap-2 text-violet-700 dark:text-violet-300">
                            <Calendar size={16} />
                            {lang === 'ar' ? 'سجل حساب الإجازة' : 'Leave Calculation Record'}
                          </CardTitle>
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                            mirror.transaction.data.calculation_details.calculation_valid 
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' 
                              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          }`}>
                            {mirror.transaction.data.calculation_details.calculation_valid 
                              ? (lang === 'ar' ? 'صحيح' : 'Valid')
                              : (lang === 'ar' ? 'خطأ' : 'Error')
                            }
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Summary */}
                        <div className="bg-violet-50 dark:bg-violet-900/20 rounded-lg p-3 border border-violet-200 dark:border-violet-800">
                          <p className="text-violet-800 dark:text-violet-200 text-sm font-medium text-center">
                            {mirror.transaction.data.calculation_details.calculation_summary_ar}
                          </p>
                        </div>

                        {/* Numbers Grid - Horizontal */}
                        <div className="flex gap-2 overflow-x-auto pb-2">
                          <div className="flex-1 min-w-[80px] bg-muted/50 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold">{mirror.transaction.data.calculation_details.total_calendar_days}</p>
                            <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'تقويمي' : 'Calendar'}</p>
                          </div>
                          <div className="flex-1 min-w-[80px] bg-emerald-100 dark:bg-emerald-900/30 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-emerald-700 dark:text-emerald-400">{mirror.transaction.data.calculation_details.working_days}</p>
                            <p className="text-[10px] text-emerald-600">{lang === 'ar' ? 'عمل' : 'Work'}</p>
                          </div>
                          <div className="flex-1 min-w-[80px] bg-amber-100 dark:bg-amber-900/30 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-amber-700 dark:text-amber-400">{mirror.transaction.data.calculation_details.excluded_fridays?.length || 0}</p>
                            <p className="text-[10px] text-amber-600">{lang === 'ar' ? 'جمعة' : 'Fri'}</p>
                          </div>
                          <div className="flex-1 min-w-[80px] bg-red-100 dark:bg-red-900/30 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-red-700 dark:text-red-400">{mirror.transaction.data.calculation_details.excluded_holidays?.length || 0}</p>
                            <p className="text-[10px] text-red-600">{lang === 'ar' ? 'إجازة' : 'Holiday'}</p>
                          </div>
                        </div>

                        {/* Excluded Holidays */}
                        {mirror.transaction.data.calculation_details.excluded_holidays?.length > 0 && (
                          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 border border-red-200 dark:border-red-800">
                            <h4 className="text-xs font-semibold text-red-800 dark:text-red-200 mb-2 flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                              {lang === 'ar' ? 'الإجازات الرسمية المستثناة:' : 'Excluded Holidays:'}
                            </h4>
                            <div className="space-y-1">
                              {mirror.transaction.data.calculation_details.excluded_holidays.map((h, idx) => (
                                <div key={idx} className="flex items-center justify-between bg-white dark:bg-red-950/30 rounded px-2 py-1.5 text-xs">
                                  <span className="font-medium text-red-700 dark:text-red-300">{h.name}</span>
                                  <span className="text-red-600 dark:text-red-400 font-mono">{h.date}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* No holidays */}
                        {(!mirror.transaction.data.calculation_details.excluded_holidays || mirror.transaction.data.calculation_details.excluded_holidays.length === 0) && (
                          <div className="text-center text-xs text-emerald-600 py-2">
                            {lang === 'ar' ? 'لا توجد إجازات رسمية ضمن الفترة' : 'No public holidays in period'}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Before/After */}
                  <Card className="border border-border shadow-none" data-testid="before-after-card">
                    <CardHeader className="pb-2"><CardTitle className="text-sm">{t('stas.beforeAfter')}</CardTitle></CardHeader>
                    <CardContent>
                      {/* عرض المعادلة والسياسة إذا كانت موجودة */}
                      {mirror.before_after?.formula && (
                        <div className="mb-4 p-3 rounded-lg bg-blue-50 border border-blue-100">
                          <p className="text-xs font-semibold text-blue-700 mb-1">{lang === 'ar' ? 'المعادلة' : 'Formula'}</p>
                          <p className="font-mono text-sm text-blue-900">{mirror.before_after.formula}</p>
                        </div>
                      )}
                      {mirror.before_after?.policy && (
                        <div className="mb-4 p-2 rounded bg-muted/50 text-sm">
                          <span className="text-muted-foreground">{lang === 'ar' ? 'السياسة:' : 'Policy:'}</span> 
                          <span className="font-bold ms-2">{mirror.before_after.policy.days} {lang === 'ar' ? 'يوم' : 'days'}</span>
                          <span className="text-xs text-muted-foreground ms-2">({mirror.before_after.policy.source_ar || mirror.before_after.policy.source})</span>
                        </div>
                      )}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-3 rounded-lg bg-muted/50">
                          <p className="text-xs font-semibold text-muted-foreground mb-2">{lang === 'ar' ? 'قبل' : 'BEFORE'}</p>
                          {Object.entries(mirror.before_after?.before || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between text-sm">
                              <span className="text-muted-foreground">{translateKey(k)}</span>
                              <span className="font-medium">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                            </div>
                          ))}
                        </div>
                        <div className="p-3 rounded-lg bg-primary/5 border border-primary/10">
                          <p className="text-xs font-semibold text-primary mb-2">{lang === 'ar' ? 'بعد' : 'AFTER'}</p>
                          {Object.entries(mirror.before_after?.after || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between text-sm">
                              <span className="text-muted-foreground">{translateKey(k)}</span>
                              <span className="font-bold">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      {mirror.before_after?.note_ar && (
                        <p className="text-xs text-muted-foreground mt-3 text-center">{mirror.before_after.note_ar}</p>
                      )}
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

                  {/* Medical File - التقرير الطبي */}
                  {mirror.transaction?.data?.medical_file_url && (
                    <Card className="border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 shadow-none" data-testid="medical-file-card">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-red-800 dark:text-red-200 flex items-center gap-2">
                          <FileText size={16} />
                          {lang === 'ar' ? 'التقرير الطبي المرفق' : 'Attached Medical Report'}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {/* معاينة PDF inline */}
                        <div className="border border-red-200 rounded overflow-hidden bg-white">
                          <iframe
                            src={`${mirror.transaction.data.medical_file_url}#toolbar=0&navpanes=0`}
                            className="w-full h-64"
                            title="Medical Report Preview"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(mirror.transaction.data.medical_file_url, '_blank')}
                            className="flex-1 border-red-300 text-red-600 hover:bg-red-100"
                            data-testid="view-medical-file-fullscreen"
                          >
                            <Eye size={14} className="me-2" />
                            {lang === 'ar' ? 'فتح في نافذة جديدة' : 'Open in New Tab'}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const link = document.createElement('a');
                              link.href = mirror.transaction.data.medical_file_url;
                              link.download = 'medical_report.pdf';
                              link.click();
                            }}
                            className="border-red-300 text-red-600 hover:bg-red-100"
                            data-testid="download-medical-file"
                          >
                            {lang === 'ar' ? 'تحميل' : 'Download'}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Desktop Execute Button - منع التنفيذ المكرر */}
                  <div className="hidden md:block space-y-2">
                    {mirror.transaction?.status === 'executed' ? (
                      <div className="w-full h-12 text-base font-semibold bg-emerald-100 text-emerald-700 rounded-md flex items-center justify-center gap-2">
                        <CheckCircle size={18} /> {lang === 'ar' ? 'تم التنفيذ مسبقاً' : 'Already Executed'}
                      </div>
                    ) : (
                      <>
                        <Button
                          data-testid="stas-execute-btn-desktop"
                          onClick={handleExecute}
                          disabled={!mirror.all_checks_pass || executing}
                          className={`w-full h-12 text-base font-semibold ${mirror.all_checks_pass && !executing ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-muted text-muted-foreground cursor-not-allowed'}`}
                        >
                          {executing ? <><Loader2 size={18} className="me-2 animate-spin" /> {t('stas.executing')}</> : <><Shield size={18} className="me-2" /> {t('stas.execute')}</>}
                        </Button>
                        
                        {/* زر الإلغاء */}
                        <Button
                          data-testid="stas-cancel-btn-desktop"
                          variant="outline"
                          onClick={() => setCancelDialogOpen(true)}
                          disabled={executing || cancelling}
                          className="w-full h-10 border-red-300 text-red-600 hover:bg-red-50"
                        >
                          <XCircle size={16} className="me-2" />
                          {lang === 'ar' ? 'إلغاء المعاملة' : 'Cancel Transaction'}
                        </Button>
                      </>
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
              <div className="flex gap-2 flex-1">
                <Button
                  data-testid="stas-execute-btn-mobile"
                  onClick={handleExecute}
                  disabled={!mirror.all_checks_pass || executing}
                  className={`flex-1 ${mirror.all_checks_pass && !executing ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'bg-muted text-muted-foreground'}`}
                >
                  {executing ? <Loader2 size={16} className="me-1 animate-spin" /> : <Shield size={16} className="me-1" />}
                  {t('stas.execute')}
                </Button>
                <Button
                  data-testid="stas-cancel-btn-mobile"
                  variant="outline"
                  onClick={() => setCancelDialogOpen(true)}
                  disabled={executing || cancelling}
                  className="border-red-300 text-red-600"
                >
                  <XCircle size={16} />
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cancel Transaction Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              {lang === 'ar' ? 'إلغاء المعاملة' : 'Cancel Transaction'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-800 dark:text-red-200">
                {lang === 'ar' 
                  ? 'سيتم إلغاء هذه المعاملة نهائياً. يمكن للموظف تقديم طلب جديد بعد الإلغاء.'
                  : 'This transaction will be permanently cancelled. The employee can submit a new request after cancellation.'
                }
              </p>
            </div>
            
            <div>
              <Label className="text-red-600">
                {lang === 'ar' ? '* سبب الإلغاء (مطلوب)' : '* Cancellation Reason (Required)'}
              </Label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder={lang === 'ar' ? 'اكتب سبب إلغاء المعاملة...' : 'Write the reason for cancellation...'}
                className="w-full mt-2 p-3 border border-red-200 rounded-lg min-h-[100px] focus:outline-none focus:ring-2 focus:ring-red-500"
                data-testid="cancel-reason-input"
              />
              <p className="text-xs text-muted-foreground mt-1">
                {lang === 'ar' ? `${cancelReason.length}/5 أحرف على الأقل` : `${cancelReason.length}/5 characters minimum`}
              </p>
            </div>
          </div>
          
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => { setCancelDialogOpen(false); setCancelReason(''); }}>
              {lang === 'ar' ? 'إغلاق' : 'Close'}
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleCancelTransaction}
              disabled={cancelling || cancelReason.trim().length < 5}
              data-testid="confirm-cancel-btn"
            >
              {cancelling ? <Loader2 size={16} className="me-2 animate-spin" /> : <XCircle size={16} className="me-2" />}
              {lang === 'ar' ? 'تأكيد الإلغاء' : 'Confirm Cancel'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
