import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  FileText, Check, X as XIcon, Search, Eye, Loader2, Filter, Clock, User, Camera, QrCode,
  CalendarDays, Fingerprint, MapPin, ClockAlert, LogOut, Package, Wallet, FileSignature, AlertTriangle, Receipt
} from 'lucide-react';
import { formatSaudiDateTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';
import jsQR from 'jsqr';

// تكوين الحالات - ألوان الشركة
const STATUS_CONFIG = {
  // منفذة
  executed: { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-700 dark:text-slate-200', border: 'border-slate-300', label_ar: 'منفذة', label_en: 'Executed', color: 'slate' },
  
  // مرفوضة/ملغاة
  rejected: { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-600 dark:text-slate-300', border: 'border-slate-300', label_ar: 'مرفوضة', label_en: 'Rejected', color: 'slate' },
  cancelled: { bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-600 dark:text-slate-300', border: 'border-slate-300', label_ar: 'ملغاة', label_en: 'Cancelled', color: 'slate' },
  
  // معادة
  returned: { bg: 'bg-[hsl(var(--navy)/0.1)]', text: 'text-[hsl(var(--navy))]', border: 'border-[hsl(var(--navy)/0.2)]', label_ar: 'معادة', label_en: 'Returned', color: 'navy' },
  
  // معلقة - Lavender
  pending_supervisor: { bg: 'bg-[hsl(var(--lavender)/0.1)]', text: 'text-[hsl(var(--lavender))]', border: 'border-[hsl(var(--lavender)/0.2)]', label_ar: 'بانتظار المشرف', label_en: 'Pending Supervisor', color: 'lavender' },
  pending_ops: { bg: 'bg-[hsl(var(--lavender)/0.1)]', text: 'text-[hsl(var(--lavender))]', border: 'border-[hsl(var(--lavender)/0.2)]', label_ar: 'بانتظار العمليات', label_en: 'Pending Operations', color: 'lavender' },
  pending_finance: { bg: 'bg-[hsl(var(--lavender)/0.1)]', text: 'text-[hsl(var(--lavender))]', border: 'border-[hsl(var(--lavender)/0.2)]', label_ar: 'بانتظار المالية', label_en: 'Pending Finance', color: 'lavender' },
  pending_ceo: { bg: 'bg-[hsl(var(--lavender)/0.1)]', text: 'text-[hsl(var(--lavender))]', border: 'border-[hsl(var(--lavender)/0.2)]', label_ar: 'بانتظار CEO', label_en: 'Pending CEO', color: 'lavender' },
  stas: { bg: 'bg-[hsl(var(--navy)/0.1)]', text: 'text-[hsl(var(--navy))]', border: 'border-[hsl(var(--navy)/0.2)]', label_ar: 'بانتظار التنفيذ', label_en: 'Pending Execution', color: 'navy' },
  pending_employee_accept: { bg: 'bg-[hsl(var(--lavender)/0.1)]', text: 'text-[hsl(var(--lavender))]', border: 'border-[hsl(var(--lavender)/0.2)]', label_ar: 'بانتظار قبول الموظف', label_en: 'Pending Employee Accept', color: 'lavender' },
};

// تكوين أنواع المعاملات - مع أيقونات Lucide
const TYPE_CONFIG = {
  leave_request: { label_ar: 'طلب إجازة', label_en: 'Leave Request', Icon: CalendarDays },
  finance_60: { label_ar: 'عهدة مالية', label_en: 'Financial Custody', Icon: Wallet },
  settlement: { label_ar: 'مخالصة', label_en: 'Settlement', Icon: Receipt },
  contract: { label_ar: 'عقد', label_en: 'Contract', Icon: FileSignature },
  tangible_custody: { label_ar: 'عهدة ملموسة', label_en: 'Tangible Custody', Icon: Package },
  tangible_custody_return: { label_ar: 'إرجاع عهدة', label_en: 'Custody Return', Icon: Package },
  salary_advance: { label_ar: 'سلفة راتب', label_en: 'Salary Advance', Icon: Wallet },
  letter_request: { label_ar: 'طلب خطاب', label_en: 'Letter Request', Icon: FileText },
  forget_checkin: { label_ar: 'نسيان بصمة', label_en: 'Forgot Punch', Icon: Fingerprint },
  field_work: { label_ar: 'مهمة خارجية', label_en: 'Field Work', Icon: MapPin },
  early_leave_request: { label_ar: 'طلب خروج مبكر', label_en: 'Early Leave Request', Icon: LogOut },
  late_excuse: { label_ar: 'تبرير تأخير', label_en: 'Late Excuse', Icon: ClockAlert },
  add_finance_code: { label_ar: 'إضافة رمز مالي', label_en: 'Add Finance Code', Icon: Wallet },
  warning: { label_ar: 'إنذار', label_en: 'Warning', Icon: AlertTriangle },
};

// تكوين المراحل
const STAGE_CONFIG = {
  ar: {
    supervisor: 'المشرف',
    ops: 'العمليات',
    finance: 'المالية',
    ceo: 'المدير التنفيذي',
    stas: 'التنفيذ',
    employee_accept: 'قبول الموظف',
    completed: 'مكتملة',
    cancelled: 'ملغاة',
    returned: 'معادة',
  },
  en: {
    supervisor: 'Supervisor',
    ops: 'Operations',
    finance: 'Finance',
    ceo: 'CEO',
    stas: 'Execution',
    employee_accept: 'Employee Accept',
    completed: 'Completed',
    cancelled: 'Cancelled',
    returned: 'Returned',
  }
};

export default function TransactionsPage() {
  const { lang } = useLanguage();
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
  const [scannerOpen, setScannerOpen] = useState(false);
  const [scannerStream, setScannerStream] = useState(null);
  const videoRef = useRef(null);

  // فتح الكاميرا
  const startScanner = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      setScannerStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      toast.error(lang === 'ar' ? 'لا يمكن الوصول للكاميرا' : 'Cannot access camera');
      setScannerOpen(false);
    }
  };

  // إغلاق الكاميرا
  const stopScanner = () => {
    if (scannerStream) {
      scannerStream.getTracks().forEach(track => track.stop());
      setScannerStream(null);
    }
    setScannerOpen(false);
  };

  // البحث برقم المعاملة المدخل يدوياً
  const handleManualBarcodeSearch = (code) => {
    const cleanCode = code.trim().toUpperCase();
    if (cleanCode) {
      setSearch(cleanCode);
      stopScanner();
      toast.success(lang === 'ar' ? `جاري البحث عن: ${cleanCode}` : `Searching for: ${cleanCode}`);
    }
  };

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
      toast.success(action === 'approve' 
        ? (lang === 'ar' ? 'تمت الموافقة بنجاح' : 'Approved successfully')
        : action === 'escalate' 
        ? (lang === 'ar' ? 'تم التصعيد بنجاح' : 'Escalated successfully')
        : (lang === 'ar' ? 'تم الرفض' : 'Rejected'));
      setActionDialog(null);
      setNote('');
      fetchTxs();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'حدث خطأ' : 'Error occurred'));
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status) => {
    const config = STATUS_CONFIG[status] || { bg: 'bg-gray-500/10', text: 'text-gray-600', border: 'border-gray-500/20', label_ar: status, label_en: status };
    return { ...config, label: lang === 'ar' ? config.label_ar : config.label_en };
  };
  const getTypeConfig = (type) => {
    const config = TYPE_CONFIG[type] || { Icon: FileText, label_ar: type, label_en: type };
    return { ...config, label: lang === 'ar' ? config.label_ar : config.label_en };
  };
  const getStageLabel = (stage) => STAGE_CONFIG[lang]?.[stage] || stage;

  // التحقق من إمكانية الموافقة
  const canApprove = (tx) => {
    // التحقق من أن المستخدم لم يتخذ إجراءً مسبقاً
    const hasAlreadyActed = tx.approval_chain?.some(
      approval => approval.approver_id === user?.id
    );
    if (hasAlreadyActed) return false;
    
    const rolePermissions = {
      pending_supervisor: ['supervisor', 'sultan', 'naif'],
      pending_ops: ['sultan', 'naif'],
      pending_finance: ['salah'],
      pending_ceo: ['mohammed'],
      stas: ['stas'],
      pending_employee_accept: ['employee'],
    };
    return rolePermissions[tx.status]?.includes(user?.role);
  };

  // التحقق من إمكانية التصعيد
  const canEscalate = (tx) => {
    const hasAlreadyActed = tx.approval_chain?.some(
      approval => approval.approver_id === user?.id
    );
    if (hasAlreadyActed) return false;
    
    if (!['sultan', 'naif'].includes(user?.role)) return false;
    return ['pending_supervisor', 'pending_ops'].includes(tx.status);
  };

  // الحصول على اسم الموظف
  const getEmployeeName = (tx) => {
    return tx.data?.employee_name_ar || tx.data?.employee_name || '-';
  };

  return (
    <div className="space-y-6" data-testid="transactions-page">
      {/* الترويسة */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{lang === 'ar' ? 'المعاملات' : 'Transactions'}</h1>
          <p className="text-muted-foreground mt-1">
            {fetchLoading 
              ? (lang === 'ar' ? 'جارٍ التحميل...' : 'Loading...') 
              : (lang === 'ar' ? `${filtered.length} معاملة` : `${filtered.length} transactions`)}
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

      {/* البحث والفلاتر */}
      <div className="space-y-3">
        {/* حقل البحث + زر الكاميرا */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={18} className="absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              data-testid="search-input"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={lang === 'ar' ? 'البحث برقم المعاملة أو الموظف...' : 'Search by transaction number or employee...'}
              className="ps-11 h-12 rounded-xl bg-muted/30 border-border/50 focus:border-primary text-base"
            />
          </div>
          
          {/* زر الكاميرا للبحث السريع - للإدارة فقط */}
          {['stas', 'sultan', 'naif'].includes(user?.role) && (
            <Button
              variant="outline"
              size="lg"
              onClick={() => setScannerOpen(true)}
              className="h-12 px-4 rounded-xl border-primary/30 hover:bg-primary/5"
              title={lang === 'ar' ? 'مسح باركود المعاملة' : 'Scan transaction barcode'}
              data-testid="open-scanner-btn"
            >
              <Camera size={20} className="text-primary" />
            </Button>
          )}
        </div>

        {/* لوحة الفلاتر */}
        {showFilters && (
          <div className="flex flex-col sm:flex-row gap-3 p-4 bg-muted/30 rounded-xl border border-border/50 animate-fade-in">
            <Select value={filter.status || 'all'} onValueChange={v => setFilter({...filter, status: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="status-filter">
                <SelectValue placeholder={lang === 'ar' ? 'الحالة' : 'Status'} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{lang === 'ar' ? 'جميع الحالات' : 'All Statuses'}</SelectItem>
                <SelectItem value="pending_supervisor">{lang === 'ar' ? 'بانتظار المشرف' : 'Pending Supervisor'}</SelectItem>
                <SelectItem value="pending_ops">{lang === 'ar' ? 'بانتظار العمليات' : 'Pending Operations'}</SelectItem>
                <SelectItem value="pending_finance">{lang === 'ar' ? 'بانتظار المالية' : 'Pending Finance'}</SelectItem>
                <SelectItem value="stas">{lang === 'ar' ? 'بانتظار التنفيذ' : 'Pending Execution'}</SelectItem>
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
                <SelectItem value="forget_checkin">{lang === 'ar' ? 'نسيان بصمة' : 'Forgot Punch'}</SelectItem>
                <SelectItem value="field_work">{lang === 'ar' ? 'مهمة خارجية' : 'Field Work'}</SelectItem>
                <SelectItem value="late_excuse">{lang === 'ar' ? 'تبرير تأخير' : 'Late Excuse'}</SelectItem>
                <SelectItem value="early_leave_request">{lang === 'ar' ? 'خروج مبكر' : 'Early Leave'}</SelectItem>
                <SelectItem value="tangible_custody">{lang === 'ar' ? 'عهدة ملموسة' : 'Tangible Custody'}</SelectItem>
                <SelectItem value="finance_60">{lang === 'ar' ? 'عهدة مالية' : 'Financial Custody'}</SelectItem>
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

      {/* قائمة المعاملات */}
      <div className="space-y-3">
        {fetchLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 bg-muted/20 rounded-2xl border border-dashed border-border">
            <FileText size={48} className="mx-auto mb-4 text-muted-foreground/40" />
            <p className="text-lg font-medium text-muted-foreground">{lang === 'ar' ? 'لا توجد معاملات' : 'No transactions'}</p>
            <p className="text-sm text-muted-foreground/70 mt-1">{lang === 'ar' ? 'جرب تغيير معايير البحث' : 'Try changing search criteria'}</p>
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
                {/* المحتوى الرئيسي */}
                <div className="p-4 sm:p-5">
                  {/* الصف العلوي - نوع المعاملة والحالة */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div className="flex items-center gap-3">
                      {/* أيقونة النوع */}
                      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                        {typeConfig.Icon && <typeConfig.Icon size={24} className="text-primary" />}
                      </div>
                      {/* النوع والرقم المرجعي */}
                      <div>
                        <h3 className="font-semibold text-base">{typeConfig.label}</h3>
                        <p className="text-xs text-muted-foreground font-mono mt-0.5">{tx.ref_no}</p>
                      </div>
                    </div>
                    {/* شارة الحالة */}
                    <span className={`inline-flex items-center rounded-full px-3 py-1.5 text-xs font-semibold border ${statusConfig.bg} ${statusConfig.text} ${statusConfig.border}`}>
                      {statusConfig.label}
                    </span>
                  </div>
                  
                  {/* صف المعلومات */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm mb-4">
                    {/* الموظف */}
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <User size={14} />
                      <span>{getEmployeeName(tx)}</span>
                    </div>
                    {/* الوقت */}
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Clock size={14} />
                      <span>{formatSaudiDateTime(tx.created_at)}</span>
                    </div>
                    {/* المرحلة */}
                    <div className="ms-auto text-xs bg-muted/50 px-2 py-1 rounded-md">
                      المرحلة: {getStageLabel(tx.current_stage)}
                    </div>
                  </div>

                  {/* صف الإجراءات */}
                  <div className="flex items-center gap-2 pt-3 border-t border-border/50">
                    {/* زر العرض */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/transactions/${tx.id}`)}
                      className="flex-1 h-10 rounded-xl hover:bg-primary/10 hover:text-primary"
                      data-testid={`view-tx-${tx.ref_no}`}
                    >
                      <Eye size={16} className="me-2" />
                      عرض التفاصيل
                    </Button>
                    
                    {/* أزرار الموافقة/الرفض */}
                    {showActions && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => setActionDialog({ ...tx, action: 'approve' })}
                          className="h-10 px-5 rounded-xl bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))] text-white font-medium shadow-sm"
                          data-testid={`approve-tx-${tx.ref_no}`}
                        >
                          <Check size={16} className="me-1.5" />
                          موافقة
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
                    
                    {/* زر التصعيد */}
                    {showEscalate && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setActionDialog({ ...tx, action: 'escalate' })}
                        className="h-10 rounded-xl border-[hsl(var(--warning)/0.3)] text-[hsl(var(--warning))] hover:bg-[hsl(var(--warning)/0.1)] hover:border-[hsl(var(--warning)/0.4)]"
                        data-testid={`escalate-tx-${tx.ref_no}`}
                      >
                        تصعيد
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* نافذة الإجراء */}
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
            {/* معلومات المعاملة */}
            <div className="bg-muted/30 rounded-xl p-4">
              <p className="text-sm font-mono text-muted-foreground">{actionDialog?.ref_no}</p>
              <p className="text-base font-medium mt-1">{getTypeConfig(actionDialog?.type).label}</p>
            </div>
            
            {/* حقل الملاحظة */}
            <div>
              <label className="text-sm font-medium mb-2 block">{lang === 'ar' ? 'ملاحظة (اختياري)' : 'Note (optional)'}</label>
              <Input
                data-testid="action-note-input"
                placeholder={lang === 'ar' ? 'أضف ملاحظة...' : 'Add a note...'}
                value={note}
                onChange={e => setNote(e.target.value)}
                className="h-12 rounded-xl"
              />
            </div>
            
            {/* أزرار الإجراء */}
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
                  actionDialog?.action === 'approve' ? 'bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))]' :
                  actionDialog?.action === 'reject' ? 'bg-red-600 hover:bg-red-700' : 
                  'bg-[hsl(var(--warning))] hover:bg-[hsl(var(--warning))]'
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

      {/* نافذة الكاميرا للبحث السريع */}
      <Dialog open={scannerOpen} onOpenChange={(open) => { if (!open) stopScanner(); setScannerOpen(open); }}>
        <DialogContent className="max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode size={20} className="text-primary" />
              {lang === 'ar' ? 'مسح باركود المعاملة' : 'Scan Transaction Barcode'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              {lang === 'ar' 
                ? 'وجّه الكاميرا على باركود المعاملة أو أدخل رقم المعاملة يدوياً'
                : 'Point camera at transaction barcode or enter number manually'}
            </p>
            
            {/* عرض الكاميرا */}
            <div className="relative bg-black rounded-xl overflow-hidden aspect-video">
              {scannerOpen && !scannerStream && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <Button onClick={startScanner} variant="secondary">
                    <Camera size={18} className="me-2" />
                    {lang === 'ar' ? 'تشغيل الكاميرا' : 'Start Camera'}
                  </Button>
                </div>
              )}
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                className="w-full h-full object-cover"
                style={{ display: scannerStream ? 'block' : 'none' }}
              />
              {scannerStream && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-48 h-24 border-2 border-primary rounded-lg animate-pulse" />
                </div>
              )}
            </div>
            
            {/* إدخال يدوي */}
            <div className="flex gap-2">
              <Input
                placeholder="TXN-2026-001 أو رقم المعاملة..."
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleManualBarcodeSearch(e.target.value);
                  }
                }}
                data-testid="manual-barcode-input"
              />
              <Button 
                onClick={(e) => {
                  const input = e.target.closest('.flex').querySelector('input');
                  handleManualBarcodeSearch(input.value);
                }}
                data-testid="search-barcode-btn"
              >
                <Search size={18} />
              </Button>
            </div>
            
            <Button variant="outline" onClick={stopScanner} className="w-full">
              {lang === 'ar' ? 'إغلاق' : 'Close'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
