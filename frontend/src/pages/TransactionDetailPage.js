import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Download, Clock, CheckCircle, XCircle, Circle, Eye } from 'lucide-react';
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

export default function TransactionDetailPage() {
  const { id } = useParams();
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [tx, setTx] = useState(null);

  useEffect(() => {
    api.get(`/api/transactions/${id}`).then(r => setTx(r.data)).catch(() => navigate('/transactions'));
  }, [id, navigate]);

  if (!tx) return <div className="text-center py-12 text-muted-foreground">{t('common.loading')}</div>;

  const downloadPdf = async () => {
    try {
      const res = await api.get(`/api/transactions/${tx.id}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a'); a.href = url; a.download = `${tx.ref_no}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error(t('transactions.downloadPdf') + ' failed'); }
  };

  const previewPdf = async () => {
    try {
      const res = await api.get(`/api/transactions/${tx.id}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch { toast.error(t('transactions.previewPdf') + ' failed'); }
  };

  // Get status style with role-based colors
  const getStatusStyle = (status) => {
    if (status === 'executed' || status === 'approve') {
      return { backgroundColor: `${STATUS_COLORS.executed}15`, color: STATUS_COLORS.executed, borderColor: `${STATUS_COLORS.executed}30` };
    }
    if (status === 'rejected' || status === 'reject') {
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
  const getTranslatedStage = (stage) => t(`stages.${stage}`) || stage;

  // Translate data keys for display
  const getTranslatedKey = (key) => {
    const keyMap = {
      leave_type: lang === 'ar' ? 'نوع الإجازة' : 'Leave Type',
      start_date: lang === 'ar' ? 'تاريخ البداية' : 'Start Date',
      end_date: lang === 'ar' ? 'تاريخ النهاية' : 'End Date',
      adjusted_end_date: lang === 'ar' ? 'تاريخ النهاية المعدل' : 'Adjusted End Date',
      working_days: lang === 'ar' ? 'أيام العمل' : 'Working Days',
      reason: lang === 'ar' ? 'السبب' : 'Reason',
      employee_name: lang === 'ar' ? 'اسم الموظف' : 'Employee Name',
      employee_name_ar: lang === 'ar' ? 'اسم الموظف' : 'Employee Name (Arabic)',
      balance_before: lang === 'ar' ? 'الرصيد قبل' : 'Balance Before',
      balance_after: lang === 'ar' ? 'الرصيد بعد' : 'Balance After',
      amount: lang === 'ar' ? 'المبلغ' : 'Amount',
      description: lang === 'ar' ? 'الوصف' : 'Description',
    };
    return keyMap[key] || key.replace(/_/g, ' ');
  };

  // Translate leave types
  const getTranslatedValue = (key, val) => {
    if (key === 'leave_type') {
      const leaveTypes = { annual: lang === 'ar' ? 'سنوية' : 'Annual', sick: lang === 'ar' ? 'مرضية' : 'Sick', emergency: lang === 'ar' ? 'طارئة' : 'Emergency' };
      return leaveTypes[val] || val;
    }
    if (key === 'employee_name' && lang === 'ar' && tx.data?.employee_name_ar) {
      return tx.data.employee_name_ar;
    }
    return String(val);
  };

  const getTimelineIcon = (event) => {
    if (event === 'executed') return <CheckCircle size={16} className="text-emerald-500" />;
    if (event === 'rejected') return <XCircle size={16} className="text-red-500" />;
    if (event === 'approved') return <CheckCircle size={16} className="text-blue-500" />;
    return <Circle size={16} className="text-muted-foreground" />;
  };

  // Get translated event name
  const getTranslatedEvent = (event) => {
    const events = {
      created: lang === 'ar' ? 'تم الإنشاء' : 'Created',
      approved: lang === 'ar' ? 'تمت الموافقة' : 'Approved',
      rejected: lang === 'ar' ? 'تم الرفض' : 'Rejected',
      executed: lang === 'ar' ? 'تم التنفيذ' : 'Executed',
      escalated: lang === 'ar' ? 'تم التصعيد' : 'Escalated to CEO',
    };
    return events[event] || event;
  };

  return (
    <div className="space-y-6" data-testid="transaction-detail-page">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/transactions')} data-testid="back-btn">
          <ArrowLeft size={16} className="me-1" /> {t('common.back')}
        </Button>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight font-mono">{tx.ref_no}</h1>
          <p className="text-sm text-muted-foreground">{getTranslatedType(tx.type)}</p>
        </div>
        <div className="flex items-center gap-2">
          <span 
            className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset"
            style={getStatusStyle(tx.status)}
          >
            {t(`status.${tx.status}`) || tx.status}
          </span>
          <Button variant="outline" size="sm" onClick={previewPdf} data-testid="preview-pdf-btn">
            <Eye size={14} className="me-1" /> {t('common.preview')}
          </Button>
          <Button variant="outline" size="sm" onClick={downloadPdf} data-testid="download-pdf-btn">
            <Download size={14} className="me-1" /> PDF
          </Button>
        </div>
      </div>

      {/* Transaction Data */}
      <div className="border border-border rounded-lg p-4 md:p-6 space-y-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t('transactions.details')}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.entries(tx.data || {}).filter(([key]) => !(key === 'employee_name_ar' && lang !== 'ar') && !(key === 'employee_name' && lang === 'ar' && tx.data?.employee_name_ar)).map(([key, val]) => (
            <div key={key} className="flex flex-col">
              <span className="text-xs text-muted-foreground">{getTranslatedKey(key)}</span>
              <span className="text-sm font-medium">{getTranslatedValue(key, val)}</span>
            </div>
          ))}
        </div>
        {tx.pdf_hash && (
          <div className="pt-3 border-t border-border mt-3">
            <span className="text-xs text-muted-foreground">PDF Hash: </span>
            <span className="text-xs font-mono">{tx.pdf_hash}</span>
            <br />
            <span className="text-xs text-muted-foreground">Integrity ID: </span>
            <span className="text-xs font-mono">{tx.integrity_id}</span>
          </div>
        )}
      </div>

      {/* Timeline - Professional Vertical */}
      <div className="border border-border rounded-lg p-4 md:p-6">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">{t('transactions.timeline')}</h2>
        <div className="relative ms-2">
          <div className="absolute top-0 bottom-0 start-[7px] w-px bg-border" />
          <div className="space-y-0">
            {(tx.timeline || []).map((ev, i) => {
              const dotColor = ev.event === 'created' ? 'bg-slate-400' : ev.event === 'approved' ? 'bg-emerald-500' : ev.event === 'rejected' ? 'bg-red-500' : ev.event === 'executed' ? 'bg-purple-600' : ev.event === 'escalated' ? 'bg-orange-500' : 'bg-blue-400';
              return (
                <div key={i} className="relative flex gap-4 pb-4" data-testid={`timeline-event-${i}`}>
                  <div className={`relative z-10 w-[15px] h-[15px] rounded-full border-2 border-background ${dotColor} flex-shrink-0 mt-0.5`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="text-xs font-semibold">{getTranslatedEvent(ev.event)}</p>
                      <time className="text-[10px] text-muted-foreground font-mono whitespace-nowrap">{ev.timestamp?.slice(0, 16).replace('T', ' ')}</time>
                    </div>
                    <p className="text-xs text-muted-foreground">{ev.actor_name}</p>
                    {ev.note && <p className="text-xs text-muted-foreground/70 mt-0.5 italic">{ev.note}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Approval Chain */}
      {tx.approval_chain?.length > 0 && (
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="p-4 md:p-6 pb-0">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t('transactions.approvalChain')}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="hr-table">
              <thead><tr>
                <th>{t('transactions.stage')}</th>
                <th>{lang === 'ar' ? 'المعتمد' : 'Approver'}</th>
                <th>{t('transactions.status')}</th>
                <th>{t('transactions.date')}</th>
                <th>{lang === 'ar' ? 'ملاحظة' : 'Note'}</th>
              </tr></thead>
              <tbody>
                {tx.approval_chain.map((a, i) => (
                  <tr key={i}>
                    <td className="text-sm">{getTranslatedStage(a.stage)}</td>
                    <td className="text-sm">{a.approver_name}</td>
                    <td>
                      <span 
                        className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset"
                        style={getStatusStyle(a.status)}
                      >
                        {a.status === 'approve' ? (lang === 'ar' ? 'موافق' : 'Approved') : a.status === 'reject' ? (lang === 'ar' ? 'مرفوض' : 'Rejected') : a.status}
                      </span>
                    </td>
                    <td className="text-xs text-muted-foreground">{a.timestamp?.slice(0, 19)}</td>
                    <td className="text-xs">{a.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
