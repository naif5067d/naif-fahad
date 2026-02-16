import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { FileText, Check, X as XIcon, Search, Eye, Loader2, Filter, Clock, User } from 'lucide-react';
import { formatSaudiDateTime } from '@/lib/dateUtils';
import api from '@/lib/api';
import { toast } from 'sonner';

// تكوين الحالات بالعربية - ألوان حسب نوع القرار
const STATUS_CONFIG = {
  executed: { bg: 'bg-emerald-500/10', text: 'text-emerald-600', border: 'border-emerald-500/20', label: 'منفذة ✓' },
  rejected: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', label: 'مرفوضة ✗' },
  cancelled: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20', label: 'ملغاة' },
  returned: { bg: 'bg-blue-500/10', text: 'text-blue-600', border: 'border-blue-500/20', label: 'معادة' },
  pending_supervisor: { bg: 'bg-amber-500/10', text: 'text-amber-600', border: 'border-amber-500/20', label: 'بانتظار المشرف' },
  pending_ops: { bg: 'bg-orange-500/10', text: 'text-orange-600', border: 'border-orange-500/20', label: 'بانتظار العمليات' },
  pending_finance: { bg: 'bg-teal-500/10', text: 'text-teal-600', border: 'border-teal-500/20', label: 'بانتظار المالية' },
  pending_ceo: { bg: 'bg-purple-600/10', text: 'text-purple-700', border: 'border-purple-600/20', label: 'بانتظار المدير التنفيذي' },
  stas: { bg: 'bg-violet-500/10', text: 'text-violet-600', border: 'border-violet-500/20', label: 'بانتظار التنفيذ' },
  pending_employee_accept: { bg: 'bg-sky-500/10', text: 'text-sky-600', border: 'border-sky-500/20', label: 'بانتظار قبول الموظف' },
};

// تكوين أنواع المعاملات بالعربية
const TYPE_CONFIG = {
  leave_request: { icon: '📅', label: 'طلب إجازة' },
  finance_60: { icon: '💰', label: 'عهدة مالية' },
  settlement: { icon: '📊', label: 'مخالصة' },
  contract: { icon: '📋', label: 'عقد' },
  tangible_custody: { icon: '📦', label: 'عهدة ملموسة' },
  tangible_custody_return: { icon: '📦', label: 'إرجاع عهدة' },
  salary_advance: { icon: '💵', label: 'سلفة راتب' },
  letter_request: { icon: '✉️', label: 'طلب خطاب' },
  // أنواع طلبات الحضور
  forget_checkin: { icon: '⏰', label: 'نسيان بصمة' },
  field_work: { icon: '🚗', label: 'مهمة خارجية' },
  early_leave_request: { icon: '🚪', label: 'طلب خروج مبكر' },
  late_excuse: { icon: '⏱️', label: 'تبرير تأخير' },
  add_finance_code: { icon: '🔢', label: 'إضافة رمز مالي' },
  warning: { icon: '⚠️', label: 'إنذار' },
};

// تكوين المراحل بالعربية
const STAGE_CONFIG = {
  supervisor: 'المشرف',
  ops: 'العمليات',
  finance: 'المالية',
  ceo: 'المدير التنفيذي',
  stas: 'التنفيذ',
  employee_accept: 'قبول الموظف',
  completed: 'مكتملة',
  cancelled: 'ملغاة',
  returned: 'معادة',
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
      toast.success(action === 'approve' ? 'تمت الموافقة بنجاح' : action === 'escalate' ? 'تم التصعيد بنجاح' : 'تم الرفض');
      setActionDialog(null);
      setNote('');
      fetchTxs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'حدث خطأ');
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status) => STATUS_CONFIG[status] || { bg: 'bg-gray-500/10', text: 'text-gray-600', border: 'border-gray-500/20', label: status };
  const getTypeConfig = (type) => TYPE_CONFIG[type] || { icon: '📄', label: type };
  const getStageLabel = (stage) => STAGE_CONFIG[stage] || stage;

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
          <h1 className="text-2xl font-bold tracking-tight">المعاملات</h1>
          <p className="text-muted-foreground mt-1">
            {fetchLoading ? 'جارٍ التحميل...' : `${filtered.length} معاملة`}
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
        {/* حقل البحث */}
        <div className="relative">
          <Search size={18} className="absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            data-testid="search-input"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="البحث في المعاملات..."
            className="ps-11 h-12 rounded-xl bg-muted/30 border-border/50 focus:border-primary text-base"
          />
        </div>

        {/* لوحة الفلاتر */}
        {showFilters && (
          <div className="flex flex-col sm:flex-row gap-3 p-4 bg-muted/30 rounded-xl border border-border/50 animate-fade-in">
            <Select value={filter.status || 'all'} onValueChange={v => setFilter({...filter, status: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="status-filter">
                <SelectValue placeholder="الحالة" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع الحالات</SelectItem>
                <SelectItem value="pending_supervisor">بانتظار المشرف</SelectItem>
                <SelectItem value="pending_ops">بانتظار العمليات</SelectItem>
                <SelectItem value="pending_finance">بانتظار المالية</SelectItem>
                <SelectItem value="stas">بانتظار التنفيذ</SelectItem>
                <SelectItem value="executed">منفذة</SelectItem>
                <SelectItem value="rejected">مرفوضة</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filter.type || 'all'} onValueChange={v => setFilter({...filter, type: v === 'all' ? '' : v})}>
              <SelectTrigger className="h-11 rounded-xl flex-1" data-testid="type-filter">
                <SelectValue placeholder="النوع" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">جميع الأنواع</SelectItem>
                <SelectItem value="leave_request">طلب إجازة</SelectItem>
                <SelectItem value="forget_checkin">نسيان بصمة</SelectItem>
                <SelectItem value="field_work">مهمة خارجية</SelectItem>
                <SelectItem value="late_excuse">تبرير تأخير</SelectItem>
                <SelectItem value="early_leave_request">خروج مبكر</SelectItem>
                <SelectItem value="tangible_custody">عهدة ملموسة</SelectItem>
                <SelectItem value="finance_60">عهدة مالية</SelectItem>
              </SelectContent>
            </Select>
            {(filter.status || filter.type) && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setFilter({ status: '', type: '' })}
                className="h-11 px-4"
              >
                مسح
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
            <p className="text-lg font-medium text-muted-foreground">لا توجد معاملات</p>
            <p className="text-sm text-muted-foreground/70 mt-1">جرب تغيير معايير البحث</p>
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
                      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-xl flex-shrink-0">
                        {typeConfig.icon}
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
                          className="h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
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
                        className="h-10 rounded-xl border-orange-300 text-orange-600 hover:bg-orange-50 hover:border-orange-400"
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
              {actionDialog?.action === 'approve' && 'تأكيد الموافقة'}
              {actionDialog?.action === 'reject' && 'تأكيد الرفض'}
              {actionDialog?.action === 'escalate' && 'تأكيد التصعيد'}
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
              <label className="text-sm font-medium mb-2 block">ملاحظة (اختياري)</label>
              <Input
                data-testid="action-note-input"
                placeholder="أضف ملاحظة..."
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
                إلغاء
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
                تأكيد
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
