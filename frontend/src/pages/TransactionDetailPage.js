import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Download, Eye, Loader2, Check, X as XIcon, RotateCcw } from 'lucide-react';
import { formatSaudiDateTime, toHijri } from '@/lib/dateUtils';
import Timeline from '@/components/Timeline';
import api from '@/lib/api';
import { toast } from 'sonner';

// Status configuration
const STATUS_CONFIG = {
  executed: { bg: 'bg-emerald-500/10', text: 'text-emerald-600', border: 'border-emerald-500/20' },
  rejected: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20' },
  cancelled: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20' },
  pending_supervisor: { bg: 'bg-blue-500/10', text: 'text-blue-600', border: 'border-blue-500/20' },
  pending_ops: { bg: 'bg-orange-500/10', text: 'text-orange-600', border: 'border-orange-500/20' },
  pending_finance: { bg: 'bg-teal-500/10', text: 'text-teal-600', border: 'border-teal-500/20' },
  pending_ceo: { bg: 'bg-red-600/10', text: 'text-red-700', border: 'border-red-600/20' },
  stas: { bg: 'bg-violet-500/10', text: 'text-violet-600', border: 'border-violet-500/20' },
  pending_employee_accept: { bg: 'bg-sky-500/10', text: 'text-sky-600', border: 'border-sky-500/20' },
  approve: { bg: 'bg-emerald-500/10', text: 'text-emerald-600', border: 'border-emerald-500/20' },
  approved: { bg: 'bg-emerald-500/10', text: 'text-emerald-600', border: 'border-emerald-500/20' },
  reject: { bg: 'bg-red-500/10', text: 'text-red-600', border: 'border-red-500/20' },
  pending: { bg: 'bg-amber-500/10', text: 'text-amber-600', border: 'border-amber-500/20' },
};

export default function TransactionDetailPage() {
  const { id } = useParams();
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tx, setTx] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    const fetchTx = async () => {
      setLoading(true);
      try {
        const res = await api.get(`/api/transactions/${id}`);
        setTx(res.data);
      } catch (err) {
        toast.error(lang === 'ar' ? 'فشل تحميل المعاملة' : 'Failed to load transaction');
        navigate('/transactions');
      } finally {
        setLoading(false);
      }
    };
    fetchTx();
  }, [id, navigate, lang]);

  const downloadPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await api.get(`/api/transactions/${tx.id}/pdf?lang=${lang}`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tx.ref_no}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error(lang === 'ar' ? 'فشل تحميل PDF' : 'Failed to download PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  const previewPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await api.get(`/api/transactions/${tx.id}/pdf?lang=${lang}`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch {
      toast.error(lang === 'ar' ? 'فشل معاينة PDF' : 'Failed to preview PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  // Handle STAS actions
  const handleAction = async (action) => {
    setActionLoading(true);
    try {
      await api.post(`/api/transactions/${tx.id}/action`, { action, note: '' });
      toast.success(lang === 'ar' ? 'تم بنجاح' : 'Success');
      // Refresh transaction
      const res = await api.get(`/api/transactions/${id}`);
      setTx(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل العملية' : 'Action failed'));
    } finally {
      setActionLoading(false);
    }
  };

  // Determine what actions STAS can take
  const getStasActions = () => {
    if (user?.role !== 'stas' || tx?.status !== 'stas') return null;
    
    const rejectionSource = tx?.rejection_source;
    const ceoRejected = tx?.ceo_rejected;
    const wasRejected = rejectionSource || ceoRejected;
    
    // If rejected by CEO, show return to CEO
    // If rejected by sultan/ops, show return to sultan
    // If not rejected (normal flow), show execute and cancel
    
    return {
      canExecute: !wasRejected,
      canCancel: true,
      returnTo: ceoRejected ? 'ceo' : (rejectionSource === 'ops' || rejectionSource === 'supervisor') ? 'sultan' : null
    };
  };

  const stasActions = tx ? getStasActions() : null;

  const getStatusStyle = (status) => STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  
  const getStatusLabel = (status) => {
    const labels = {
      executed: { ar: 'منفذة', en: 'Executed' },
      rejected: { ar: 'مرفوضة', en: 'Rejected' },
      cancelled: { ar: 'ملغاة', en: 'Cancelled' },
      pending_supervisor: { ar: 'بانتظار المشرف', en: 'Pending Supervisor' },
      pending_ops: { ar: 'بانتظار العمليات', en: 'Pending Ops' },
      pending_finance: { ar: 'بانتظار المالية', en: 'Pending Finance' },
      pending_ceo: { ar: 'بانتظار CEO', en: 'Pending CEO' },
      stas: { ar: 'STAS', en: 'STAS' },
      pending_employee_accept: { ar: 'بانتظار الموظف', en: 'Pending Employee' },
      approve: { ar: 'موافق', en: 'Approved' },
      approved: { ar: 'موافق', en: 'Approved' },
      reject: { ar: 'مرفوض', en: 'Rejected' },
      pending: { ar: 'معلق', en: 'Pending' },
    };
    return labels[status] ? (lang === 'ar' ? labels[status].ar : labels[status].en) : status;
  };

  const getTypeLabel = (type) => {
    const types = {
      leave_request: { ar: 'طلب إجازة', en: 'Leave Request' },
      finance_60: { ar: 'عهدة مالية', en: 'Financial Custody' },
      settlement: { ar: 'تسوية', en: 'Settlement' },
      contract: { ar: 'عقد', en: 'Contract' },
      tangible_custody: { ar: 'عهدة ملموسة', en: 'Tangible Custody' },
      tangible_custody_return: { ar: 'إرجاع عهدة', en: 'Custody Return' },
      salary_advance: { ar: 'سلفة راتب', en: 'Salary Advance' },
      letter_request: { ar: 'طلب خطاب', en: 'Letter Request' },
    };
    return types[type] ? (lang === 'ar' ? types[type].ar : types[type].en) : type?.replace(/_/g, ' ');
  };

  const getStageLabel = (stage) => {
    // STAS and CEO always show in English
    if (stage === 'stas') return 'STAS';
    if (stage === 'ceo') return 'CEO';
    const stages = {
      supervisor: { ar: 'المشرف', en: 'Supervisor' },
      ops: { ar: 'العمليات', en: 'Operations' },
      finance: { ar: 'المالية', en: 'Finance' },
      employee_accept: { ar: 'قبول الموظف', en: 'Employee Accept' },
    };
    return stages[stage] ? (lang === 'ar' ? stages[stage].ar : stages[stage].en) : stage;
  };

  const getDataKeyLabel = (key) => {
    const labels = {
      leave_type: { ar: 'نوع الإجازة', en: 'Leave Type' },
      start_date: { ar: 'تاريخ البداية', en: 'Start Date' },
      end_date: { ar: 'تاريخ النهاية', en: 'End Date' },
      adjusted_end_date: { ar: 'تاريخ النهاية المعدل', en: 'Adjusted End Date' },
      working_days: { ar: 'أيام العمل', en: 'Working Days' },
      reason: { ar: 'السبب', en: 'Reason' },
      employee_name: { ar: 'اسم الموظف', en: 'Employee Name' },
      employee_name_ar: { ar: 'اسم الموظف', en: 'Employee Name (AR)' },
      balance_before: { ar: 'الرصيد قبل', en: 'Balance Before' },
      balance_after: { ar: 'الرصيد بعد', en: 'Balance After' },
      amount: { ar: 'المبلغ', en: 'Amount' },
      description: { ar: 'الوصف', en: 'Description' },
      asset_name: { ar: 'اسم الأصل', en: 'Asset Name' },
      asset_serial: { ar: 'الرقم التسلسلي', en: 'Serial Number' },
      // Tangible custody fields
      itemname: { ar: 'اسم العنصر', en: 'Item Name' },
      itemnamear: { ar: 'اسم العنصر', en: 'Item Name (AR)' },
      serial_number: { ar: 'الرقم التسلسلي', en: 'Serial Number' },
      estimatedvalue: { ar: 'القيمة التقديرية', en: 'Estimated Value' },
      estimated_value: { ar: 'القيمة التقديرية', en: 'Estimated Value' },
    };
    return labels[key] ? (lang === 'ar' ? labels[key].ar : labels[key].en) : key.replace(/_/g, ' ');
  };

  const getDataValueLabel = (key, value) => {
    if (key === 'leave_type') {
      const types = {
        annual: { ar: 'سنوية', en: 'Annual' },
        sick: { ar: 'مرضية', en: 'Sick' },
        emergency: { ar: 'طارئة', en: 'Emergency' },
      };
      return types[value] ? (lang === 'ar' ? types[value].ar : types[value].en) : value;
    }
    if (key === 'employee_name' && lang === 'ar' && tx?.data?.employee_name_ar) {
      return tx.data.employee_name_ar;
    }
    if ((key === 'amount' || key === 'estimatedvalue' || key === 'estimated_value') && value) {
      return `${value} SAR`;
    }
    return String(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!tx) return null;

  const statusStyle = getStatusStyle(tx.status);

  return (
    <div className="space-y-6 max-w-4xl mx-auto" data-testid="transaction-detail-page">
      {/* Back Button */}
      <Button 
        variant="ghost" 
        size="sm" 
        onClick={() => navigate('/transactions')} 
        className="hover:bg-muted -ms-2"
        data-testid="back-btn"
      >
        <ArrowLeft size={18} className="me-2" />
        {lang === 'ar' ? 'رجوع' : 'Back'}
      </Button>

      {/* Header Card */}
      <div className="bg-card rounded-2xl border border-border p-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground font-mono">{tx.ref_no}</p>
            <h1 className="text-2xl font-bold mt-1">{getTypeLabel(tx.type)}</h1>
            <p className="text-muted-foreground mt-1">
              {formatSaudiDateTime(tx.created_at)}
            </p>
          </div>
          
          <div className="flex flex-col items-end gap-3">
            {/* Status Badge */}
            <span className={`inline-flex items-center rounded-full px-4 py-1.5 text-sm font-semibold border ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}>
              {getStatusLabel(tx.status)}
            </span>
            
            {/* PDF Buttons */}
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={previewPdf} 
                disabled={pdfLoading}
                className="rounded-xl"
                data-testid="preview-pdf-btn"
              >
                {pdfLoading ? <Loader2 size={14} className="animate-spin me-2" /> : <Eye size={14} className="me-2" />}
                {lang === 'ar' ? 'معاينة' : 'Preview'}
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={downloadPdf} 
                disabled={pdfLoading}
                className="rounded-xl"
                data-testid="download-pdf-btn"
              >
                <Download size={14} className="me-2" />
                PDF
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Transaction Details */}
      <div className="bg-card rounded-2xl border border-border p-6">
        <h2 className="text-lg font-semibold mb-4">
          {lang === 'ar' ? 'تفاصيل المعاملة' : 'Transaction Details'}
        </h2>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Object.entries(tx.data || {})
            .filter(([key]) => {
              // Skip Arabic name if showing English
              if (key === 'employee_name_ar' && lang !== 'ar') return false;
              // Skip English name if showing Arabic with AR name available
              if (key === 'employee_name' && lang === 'ar' && tx.data?.employee_name_ar) return false;
              return true;
            })
            .map(([key, value]) => (
              <div key={key} className="bg-muted/30 rounded-xl p-4">
                <p className="text-xs text-muted-foreground mb-1">{getDataKeyLabel(key)}</p>
                <p className="font-medium">{getDataValueLabel(key, value)}</p>
              </div>
            ))
          }
        </div>
        
        {/* PDF Hash Info */}
        {tx.pdf_hash && (
          <div className="mt-6 pt-4 border-t border-border">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted-foreground">{lang === 'ar' ? 'معرف السلامة:' : 'Integrity ID:'} </span>
                <span className="font-mono">{tx.integrity_id}</span>
              </div>
              <div>
                <span className="text-muted-foreground">{lang === 'ar' ? 'تجزئة PDF:' : 'PDF Hash:'} </span>
                <span className="font-mono text-[10px]">{tx.pdf_hash?.slice(0, 32)}...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      {tx.timeline?.length > 0 && (
        <div className="bg-card rounded-2xl border border-border p-6">
          <h2 className="text-lg font-semibold mb-6">
            {lang === 'ar' ? 'الجدول الزمني' : 'Timeline'}
          </h2>
          <Timeline events={tx.timeline} />
        </div>
      )}

      {/* Approval Chain */}
      {tx.approval_chain?.length > 0 && (
        <div className="bg-card rounded-2xl border border-border overflow-hidden">
          <div className="p-6 pb-4">
            <h2 className="text-lg font-semibold">
              {lang === 'ar' ? 'سلسلة الموافقات' : 'Approval Chain'}
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-muted/50 border-y border-border">
                  <th className="text-start px-6 py-3 text-sm font-semibold text-muted-foreground">
                    {lang === 'ar' ? 'المرحلة' : 'Stage'}
                  </th>
                  <th className="text-start px-6 py-3 text-sm font-semibold text-muted-foreground">
                    {lang === 'ar' ? 'المعتمد' : 'Approver'}
                  </th>
                  <th className="text-start px-6 py-3 text-sm font-semibold text-muted-foreground">
                    {lang === 'ar' ? 'الحالة' : 'Status'}
                  </th>
                  <th className="text-start px-6 py-3 text-sm font-semibold text-muted-foreground">
                    {lang === 'ar' ? 'التاريخ' : 'Date'}
                  </th>
                  <th className="text-start px-6 py-3 text-sm font-semibold text-muted-foreground">
                    {lang === 'ar' ? 'ملاحظة' : 'Note'}
                  </th>
                </tr>
              </thead>
              <tbody>
                {tx.approval_chain.map((a, i) => {
                  const aStatusStyle = getStatusStyle(a.status);
                  return (
                    <tr key={i} className="border-b border-border/50 last:border-0">
                      <td className="px-6 py-4 text-sm font-medium">{getStageLabel(a.stage)}</td>
                      <td className="px-6 py-4 text-sm">{a.approver_name}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium border ${aStatusStyle.bg} ${aStatusStyle.text} ${aStatusStyle.border}`}>
                          {getStatusLabel(a.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-muted-foreground">
                        {formatSaudiDateTime(a.timestamp)}
                      </td>
                      <td className="px-6 py-4 text-sm text-muted-foreground">{a.note || '-'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
