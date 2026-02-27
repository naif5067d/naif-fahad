/**
 * صفحة معاملات الخصم - لستاس ومحمد
 * 
 * عرض المعاملات بشكل رسمي مع:
 * - رقم مرجعي
 * - سلسلة الموافقات
 * - تفاصيل كاملة
 * - قابلة للطباعة
 */
import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogFooter 
} from '@/components/ui/dialog';
import { 
  FileText, 
  CheckCircle, 
  XCircle, 
  Clock, 
  User,
  DollarSign,
  Calendar,
  Printer,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Building
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

// حالات المعاملة
const STATUS_CONFIG = {
  'pending_ceo': { 
    bg: 'bg-amber-100 dark:bg-amber-900/30', 
    text: 'text-amber-700', 
    icon: Clock,
    label: 'بانتظار قرار محمد' 
  },
  'pending_execution': { 
    bg: 'bg-blue-100 dark:bg-blue-900/30', 
    text: 'text-blue-700', 
    icon: Clock,
    label: 'بانتظار التنفيذ' 
  },
  'executed': { 
    bg: 'bg-emerald-100 dark:bg-emerald-900/30', 
    text: 'text-emerald-700', 
    icon: CheckCircle,
    label: 'تم التنفيذ' 
  },
  'rejected': { 
    bg: 'bg-red-100 dark:bg-red-900/30', 
    text: 'text-red-700', 
    icon: XCircle,
    label: 'مرفوض' 
  }
};

export default function DeductionTransactionsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState([]);
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [actionNote, setActionNote] = useState('');
  const [processing, setProcessing] = useState(false);
  const [expandedTxn, setExpandedTxn] = useState(null);

  // جلب المعاملات
  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/deduction-transactions');
      setTransactions(res.data);
    } catch (err) {
      console.error('Error fetching transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  // قرار محمد
  const handleCeoDecision = async (refNo, action) => {
    setProcessing(true);
    try {
      await api.post(`/api/deduction-transactions/${refNo}/ceo-decision`, {
        action,
        note: actionNote
      });
      
      const msg = action === 'reject' ? 'تم رفض المعاملة' : 
                  action === 'approve_salary' ? 'تم اعتماد الخصم من الراتب' :
                  'تم ترحيل الخصم للمخالصة';
      toast.success(msg);
      
      setShowDetailDialog(false);
      setActionNote('');
      fetchTransactions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'خطأ في العملية');
    } finally {
      setProcessing(false);
    }
  };

  // تنفيذ ستاس
  const handleExecute = async (refNo) => {
    setProcessing(true);
    try {
      await api.post(`/api/deduction-transactions/${refNo}/execute`, {
        confirm: true,
        note: actionNote
      });
      
      toast.success('تم تنفيذ الخصم وإضافته للسجل المالي');
      setShowDetailDialog(false);
      setActionNote('');
      fetchTransactions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'خطأ في التنفيذ');
    } finally {
      setProcessing(false);
    }
  };

  // فتح تفاصيل المعاملة
  const openDetails = async (txn) => {
    try {
      const res = await api.get(`/api/deduction-transactions/${txn.ref_no}/summary`);
      setSelectedTxn(res.data);
      setShowDetailDialog(true);
    } catch (err) {
      toast.error('خطأ في جلب التفاصيل');
    }
  };

  const isMohammed = user?.role === 'mohammed';
  const isStas = user?.role === 'stas';

  return (
    <div className="space-y-4 p-4 md:p-6" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-[hsl(var(--navy))]">
            {lang === 'ar' ? 'معاملات الخصم' : 'Deduction Transactions'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {lang === 'ar' ? 'إدارة ومتابعة معاملات الخصم الرسمية' : 'Manage official deduction transactions'}
          </p>
        </div>
        <Button variant="outline" onClick={fetchTransactions}>
          <RefreshCw size={16} className="mr-1" />
          {lang === 'ar' ? 'تحديث' : 'Refresh'}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-amber-50 dark:bg-amber-900/20 border-amber-200">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-amber-600">{lang === 'ar' ? 'بانتظار محمد' : 'Pending CEO'}</p>
            <p className="text-2xl font-bold text-amber-700">
              {transactions.filter(t => t.status === 'pending_ceo').length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-blue-600">{lang === 'ar' ? 'بانتظار التنفيذ' : 'Pending Exec'}</p>
            <p className="text-2xl font-bold text-blue-700">
              {transactions.filter(t => t.status === 'pending_execution').length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-emerald-600">{lang === 'ar' ? 'منفذة' : 'Executed'}</p>
            <p className="text-2xl font-bold text-emerald-700">
              {transactions.filter(t => t.status === 'executed').length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-red-50 dark:bg-red-900/20 border-red-200">
          <CardContent className="p-4 text-center">
            <p className="text-xs text-red-600">{lang === 'ar' ? 'مرفوضة' : 'Rejected'}</p>
            <p className="text-2xl font-bold text-red-700">
              {transactions.filter(t => t.status === 'rejected').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Transactions List */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText size={20} className="text-[hsl(var(--navy))]" />
            {lang === 'ar' ? 'قائمة المعاملات' : 'Transactions List'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <RefreshCw className="animate-spin text-[hsl(var(--navy))]" size={32} />
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              {lang === 'ar' ? 'لا توجد معاملات' : 'No transactions'}
            </div>
          ) : (
            <div className="space-y-3">
              {transactions.map((txn) => {
                const config = STATUS_CONFIG[txn.status] || STATUS_CONFIG['pending_ceo'];
                const StatusIcon = config.icon;
                
                return (
                  <div 
                    key={txn.ref_no}
                    className={`border rounded-lg overflow-hidden ${config.bg}`}
                  >
                    {/* Transaction Header */}
                    <div 
                      className="flex items-center justify-between p-4 cursor-pointer"
                      onClick={() => setExpandedTxn(expandedTxn === txn.ref_no ? null : txn.ref_no)}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${config.bg}`}>
                          <StatusIcon size={24} className={config.text} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[hsl(var(--navy))]">{txn.ref_no}</span>
                            <Badge className={`${config.bg} ${config.text} text-xs`}>
                              {config.label}
                            </Badge>
                          </div>
                          <p className="text-sm">{txn.employee_name_ar}</p>
                          <p className="text-xs text-muted-foreground">
                            {txn.reason?.substring(0, 50)}{txn.reason?.length > 50 ? '...' : ''}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="text-left">
                          <p className="text-2xl font-bold text-[hsl(var(--navy))]">{txn.amount}</p>
                          <p className="text-xs text-muted-foreground">ر.س</p>
                        </div>
                        {expandedTxn === txn.ref_no ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </div>
                    </div>
                    
                    {/* Expanded Content */}
                    {expandedTxn === txn.ref_no && (
                      <div className="border-t bg-white dark:bg-background p-4 space-y-4">
                        {/* Info Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="p-3 bg-muted/50 rounded-lg">
                            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الموظف' : 'Employee'}</p>
                            <p className="font-medium">{txn.employee_name_ar}</p>
                          </div>
                          <div className="p-3 bg-muted/50 rounded-lg">
                            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الشهر' : 'Month'}</p>
                            <p className="font-medium">{txn.month}</p>
                          </div>
                          <div className="p-3 bg-muted/50 rounded-lg">
                            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'أنشأه' : 'Created By'}</p>
                            <p className="font-medium">{txn.created_by_name}</p>
                          </div>
                          <div className="p-3 bg-muted/50 rounded-lg">
                            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'التاريخ' : 'Date'}</p>
                            <p className="font-medium">{txn.created_at?.substring(0, 10)}</p>
                          </div>
                        </div>
                        
                        {/* السبب */}
                        <div className="p-3 bg-muted/50 rounded-lg">
                          <p className="text-xs text-muted-foreground mb-1">{lang === 'ar' ? 'السبب' : 'Reason'}</p>
                          <p className="font-medium">{txn.reason}</p>
                        </div>
                        
                        {/* سلسلة الموافقات */}
                        {txn.approval_chain && txn.approval_chain.length > 0 && (
                          <div className="p-3 bg-muted/50 rounded-lg">
                            <p className="text-xs text-muted-foreground mb-2">{lang === 'ar' ? 'سلسلة الموافقات' : 'Approval Chain'}</p>
                            <div className="flex flex-wrap items-center gap-2">
                              {txn.approval_chain.map((entry, idx) => (
                                <div key={idx} className="flex items-center gap-1">
                                  {idx > 0 && <ArrowRight size={14} className="text-muted-foreground" />}
                                  <Badge variant="outline" className="text-xs">
                                    {entry.actor_name} ({entry.action})
                                  </Badge>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* أين سينعكس */}
                        {txn.deduct_from && (
                          <div className={`p-3 rounded-lg ${txn.deduct_from === 'salary' ? 'bg-emerald-50' : 'bg-amber-50'}`}>
                            <p className="text-xs text-muted-foreground mb-1">{lang === 'ar' ? 'أين سينعكس' : 'Where Applied'}</p>
                            <p className={`font-bold ${txn.deduct_from === 'salary' ? 'text-emerald-700' : 'text-amber-700'}`}>
                              {txn.deduct_from === 'salary' 
                                ? (lang === 'ar' ? '💰 خصم من الراتب' : '💰 Deduct from Salary')
                                : (lang === 'ar' ? '📋 ترحيل للمخالصة' : '📋 Defer to Settlement')
                              }
                            </p>
                          </div>
                        )}
                        
                        {/* Actions */}
                        <div className="flex gap-2 flex-wrap">
                          <Button variant="outline" size="sm" onClick={() => openDetails(txn)}>
                            <FileText size={14} className="mr-1" />
                            {lang === 'ar' ? 'عرض كامل' : 'Full View'}
                          </Button>
                          
                          {/* محمد - قرار */}
                          {isMohammed && txn.status === 'pending_ceo' && (
                            <>
                              <Button 
                                size="sm" 
                                className="bg-emerald-600 hover:bg-emerald-700"
                                onClick={() => openDetails(txn)}
                              >
                                <CheckCircle size={14} className="mr-1" />
                                {lang === 'ar' ? 'اتخاذ قرار' : 'Decide'}
                              </Button>
                            </>
                          )}
                          
                          {/* ستاس - تنفيذ */}
                          {isStas && txn.status === 'pending_execution' && (
                            <Button 
                              size="sm" 
                              className="bg-blue-600 hover:bg-blue-700"
                              onClick={() => openDetails(txn)}
                            >
                              <CheckCircle size={14} className="mr-1" />
                              {lang === 'ar' ? 'تنفيذ' : 'Execute'}
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedTxn && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <FileText className="text-[hsl(var(--navy))]" size={24} />
                  معاملة خصم - {selectedTxn.transaction.ref_no}
                </DialogTitle>
              </DialogHeader>
              
              <div className="space-y-4">
                {/* بيانات الموظف */}
                <div className="p-4 bg-[hsl(var(--navy)/0.05)] rounded-lg">
                  <h3 className="font-bold mb-3 flex items-center gap-2">
                    <User size={18} />
                    بيانات الموظف
                  </h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">الاسم:</span>
                      <span className="font-medium mr-2">{selectedTxn.employee.name_ar}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">الرقم الوظيفي:</span>
                      <span className="font-medium mr-2">{selectedTxn.employee.employee_number}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">المسمى:</span>
                      <span className="font-medium mr-2">{selectedTxn.employee.job_title}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">القسم:</span>
                      <span className="font-medium mr-2">{selectedTxn.employee.department}</span>
                    </div>
                  </div>
                </div>
                
                {/* تفاصيل الخصم */}
                <div className="p-4 bg-red-50 dark:bg-red-900/10 rounded-lg">
                  <h3 className="font-bold mb-3 flex items-center gap-2 text-red-700">
                    <DollarSign size={18} />
                    تفاصيل الخصم
                  </h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">المبلغ:</span>
                      <span className="font-bold text-red-600 mr-2 text-lg">
                        {selectedTxn.transaction.amount} ر.س
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">الشهر:</span>
                      <span className="font-medium mr-2">{selectedTxn.transaction.month}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-muted-foreground">السبب:</span>
                      <p className="font-medium mt-1">{selectedTxn.transaction.reason}</p>
                    </div>
                  </div>
                </div>
                
                {/* سلسلة الموافقات */}
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h3 className="font-bold mb-3">سلسلة الموافقات</h3>
                  <div className="space-y-2">
                    {selectedTxn.transaction.approval_chain?.map((entry, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 bg-white dark:bg-background rounded border">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{entry.stage}</Badge>
                          <span className="font-medium">{entry.actor_name}</span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {entry.action} - {entry.timestamp?.substring(0, 10)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* أين سينعكس */}
                {selectedTxn.transaction.deduct_from && (
                  <div className={`p-4 rounded-lg ${selectedTxn.transaction.deduct_from === 'salary' ? 'bg-emerald-50' : 'bg-amber-50'}`}>
                    <h3 className="font-bold mb-2">أين سينعكس الخصم؟</h3>
                    <p className={`font-bold text-lg ${selectedTxn.transaction.deduct_from === 'salary' ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {selectedTxn.deduct_from_label.ar}
                    </p>
                    {selectedTxn.transaction.reflected_in_ledger && (
                      <Badge className="bg-emerald-600 mt-2">✓ تم الانعكاس في السجل المالي</Badge>
                    )}
                  </div>
                )}
                
                {/* Actions for Mohammed */}
                {isMohammed && selectedTxn.transaction.status === 'pending_ceo' && (
                  <div className="p-4 bg-amber-50 dark:bg-amber-900/10 rounded-lg">
                    <h3 className="font-bold mb-3 text-amber-700">اتخذ قرارك</h3>
                    <Textarea 
                      placeholder="ملاحظة (اختياري)..."
                      value={actionNote}
                      onChange={e => setActionNote(e.target.value)}
                      className="mb-3"
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button 
                        className="bg-emerald-600 hover:bg-emerald-700"
                        onClick={() => handleCeoDecision(selectedTxn.transaction.ref_no, 'approve_salary')}
                        disabled={processing}
                      >
                        💰 خصم من الراتب
                      </Button>
                      <Button 
                        variant="outline"
                        className="border-amber-500 text-amber-700 hover:bg-amber-50"
                        onClick={() => handleCeoDecision(selectedTxn.transaction.ref_no, 'approve_settlement')}
                        disabled={processing}
                      >
                        📋 ترحيل للمخالصة
                      </Button>
                      <Button 
                        variant="destructive"
                        onClick={() => handleCeoDecision(selectedTxn.transaction.ref_no, 'reject')}
                        disabled={processing}
                      >
                        ❌ رفض
                      </Button>
                    </div>
                  </div>
                )}
                
                {/* Actions for STAS */}
                {isStas && selectedTxn.transaction.status === 'pending_execution' && (
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg">
                    <h3 className="font-bold mb-3 text-blue-700">تنفيذ الخصم</h3>
                    <div className="mb-3 p-3 bg-white dark:bg-background rounded-lg border">
                      <p className="text-sm">
                        <strong>قرار محمد:</strong> {selectedTxn.transaction.ceo_decision === 'approve_salary' ? 'خصم من الراتب' : 'ترحيل للمخالصة'}
                      </p>
                      {selectedTxn.transaction.ceo_decision_note && (
                        <p className="text-sm mt-1">
                          <strong>ملاحظة محمد:</strong> {selectedTxn.transaction.ceo_decision_note}
                        </p>
                      )}
                    </div>
                    <Textarea 
                      placeholder="ملاحظة التنفيذ (اختياري)..."
                      value={actionNote}
                      onChange={e => setActionNote(e.target.value)}
                      className="mb-3"
                    />
                    <Button 
                      className="bg-blue-600 hover:bg-blue-700 w-full"
                      onClick={() => handleExecute(selectedTxn.transaction.ref_no)}
                      disabled={processing}
                    >
                      {processing ? <RefreshCw className="animate-spin mr-2" size={16} /> : <CheckCircle size={16} className="mr-2" />}
                      تأكيد التنفيذ وإضافة للسجل المالي
                    </Button>
                  </div>
                )}
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDetailDialog(false)}>
                  إغلاق
                </Button>
                <Button variant="outline">
                  <Printer size={16} className="mr-1" />
                  طباعة
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
