import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';
import api from '@/lib/api';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { 
  Receipt, Plus, Search, Eye, Play, XCircle, CheckCircle, Clock, FileText,
  Users, Building2, Calendar, DollarSign, AlertTriangle, RefreshCw,
  Calculator, Ban, Download, Wallet, TrendingUp, TrendingDown, Landmark,
  ClipboardCheck, Shield, FileCheck, AlertCircle, CheckCircle2, Info
} from 'lucide-react';

// أنواع إنهاء الخدمة
const TERMINATION_TYPES = {
  contract_expiry: { label: 'انتهاء العقد', label_en: 'Contract Expiry', color: 'bg-blue-500' },
  resignation: { label: 'استقالة', label_en: 'Resignation', color: 'bg-amber-500' },
  probation_termination: { label: 'إنهاء خلال التجربة', label_en: 'Probation Termination', color: 'bg-red-500' },
  mutual_agreement: { label: 'اتفاق طرفين', label_en: 'Mutual Agreement', color: 'bg-green-500' },
  termination: { label: 'إنهاء من الشركة', label_en: 'Termination by Company', color: 'bg-purple-500' },
};

// حالات المخالصة
const SETTLEMENT_STATUS = {
  pending_stas: { label: 'بانتظار التنفيذ', color: 'bg-amber-500', icon: Clock },
  executed: { label: 'منفذة', color: 'bg-emerald-500', icon: CheckCircle },
  cancelled: { label: 'ملغاة', color: 'bg-red-500', icon: XCircle },
};

export default function SettlementPage() {
  const { user } = useAuth();
  
  const [settlements, setSettlements] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewStep, setPreviewStep] = useState('form'); // form | preview | audit
  const [viewSettlement, setViewSettlement] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  
  // Editable preview data
  const [editablePreview, setEditablePreview] = useState(null);
  
  // Validation warnings
  const [warnings, setWarnings] = useState([]);
  
  // Form state
  const [formData, setFormData] = useState({
    employee_id: '',
    termination_type: 'resignation',
    last_working_day: '',
    note: '',
  });
  
  const canCreate = ['sultan', 'naif', 'stas'].includes(user?.role);
  const canExecute = user?.role === 'stas';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [settlementsRes, employeesRes, contractsRes] = await Promise.all([
        api.get('/api/settlement'),
        api.get('/api/employees'),
        api.get('/api/contracts-v2'),
      ]);
      setSettlements(settlementsRes.data || []);
      setEmployees(employeesRes.data || []);
      setContracts(contractsRes.data || []);
    } catch (err) {
      toast.error('فشل تحميل البيانات');
    }
    setLoading(false);
  };

  // جلب الموظفين الذين لديهم عقد نشط
  const eligibleEmployees = employees.filter(emp => {
    const contract = contracts.find(c => 
      c.employee_id === emp.id && 
      ['active', 'terminated'].includes(c.status)
    );
    return contract && emp.is_active !== false;
  });

  // Validation function
  const validateSettlement = (data) => {
    const warns = [];
    
    // تحقق من البنك
    if (!data.contract?.bank_name || !data.contract?.bank_iban) {
      warns.push({ type: 'error', message: 'معلومات البنك (الاسم والآيبان) مطلوبة للمخالصة', field: 'bank' });
    }
    
    // تحقق من الراتب
    if (!data.wages?.last_wage || data.wages.last_wage <= 0) {
      warns.push({ type: 'error', message: 'لا يوجد راتب محدد في العقد', field: 'salary' });
    }
    
    // تحذير إذا كان هناك خصومات كبيرة
    if (data.totals?.deductions?.total > data.totals?.entitlements?.total) {
      warns.push({ type: 'warning', message: 'إجمالي الاستقطاعات أكبر من الاستحقاقات', field: 'balance' });
    }
    
    // تحذير إذا كانت المكافأة صفر
    if (data.eos?.final_amount === 0 && data.service?.years >= 2) {
      warns.push({ type: 'info', message: `مكافأة نهاية الخدمة صفر بسبب: ${data.eos?.percentage_reason}`, field: 'eos' });
    }
    
    return warns;
  };

  const handlePreview = async () => {
    if (!formData.employee_id || !formData.last_working_day) {
      toast.error('يرجى اختيار الموظف وتحديد آخر يوم عمل');
      return;
    }
    
    setActionLoading(true);
    try {
      const res = await api.post('/api/settlement/preview', formData);
      setPreviewData(res.data);
      setEditablePreview(JSON.parse(JSON.stringify(res.data))); // Deep copy for editing
      
      // Validate
      const warns = validateSettlement(res.data);
      setWarnings(warns);
      
      setPreviewStep('preview');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل حساب المخالصة');
    }
    setActionLoading(false);
  };

  const handleCreateSettlement = async () => {
    // Check for blocking errors
    const blockingErrors = warnings.filter(w => w.type === 'error');
    if (blockingErrors.length > 0) {
      toast.error('يوجد أخطاء يجب إصلاحها قبل الإنشاء');
      return;
    }
    
    setActionLoading(true);
    try {
      const res = await api.post('/api/settlement', formData);
      toast.success(`تم إنشاء طلب المخالصة: ${res.data.transaction_number}`);
      setCreateDialogOpen(false);
      setPreviewData(null);
      setPreviewStep('form');
      resetForm();
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل إنشاء المخالصة');
    }
    setActionLoading(false);
  };

  const handleExecute = async (settlementId) => {
    if (!confirm('هل تريد تنفيذ هذه المخالصة؟\n\nهذا الإجراء نهائي ولا يمكن التراجع عنه.\nسيتم:\n- قفل حساب الموظف\n- إغلاق العقد\n- إنشاء PDF المخالصة')) return;
    
    setActionLoading(true);
    try {
      const res = await api.post(`/api/settlement/${settlementId}/execute`);
      toast.success(`تم تنفيذ المخالصة - الصافي: ${res.data.net_amount.toLocaleString()} ريال`);
      setViewSettlement(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل التنفيذ');
    }
    setActionLoading(false);
  };

  const handleCancel = async (settlementId) => {
    if (!confirm('هل تريد إلغاء هذه المخالصة؟')) return;
    
    try {
      await api.post(`/api/settlement/${settlementId}/cancel`);
      toast.success('تم إلغاء المخالصة');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل الإلغاء');
    }
  };

  const handleDownloadPDF = async (settlementId) => {
    try {
      const res = await api.get(`/api/settlement/${settlementId}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch (err) {
      toast.error('فشل تحميل PDF');
    }
  };

  const resetForm = () => {
    setFormData({
      employee_id: '',
      termination_type: 'resignation',
      last_working_day: '',
      note: '',
    });
    setPreviewData(null);
    setEditablePreview(null);
    setPreviewStep('form');
    setWarnings([]);
  };

  const formatCurrency = (amount) => `${(amount || 0).toLocaleString()} ريال`;
  const formatDate = (dateStr) => dateStr ? formatGregorianHijri(dateStr).primary : '-';

  const filteredSettlements = settlements.filter(s => {
    if (statusFilter !== 'all' && s.status !== statusFilter) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Audit Trail Component
  const AuditTrail = ({ data }) => {
    const auditItems = [];
    
    // Service calculation
    auditItems.push({
      icon: Calendar,
      title: 'مدة الخدمة',
      title_en: 'Service Period',
      detail: `${data.service?.formatted_ar} (${data.service?.total_days} يوم)`,
      status: 'success'
    });
    
    // Last wage calculation
    auditItems.push({
      icon: Wallet,
      title: 'آخر راتب شامل',
      title_en: 'Last Wage',
      detail: `${data.wages?.formula}`,
      value: formatCurrency(data.wages?.last_wage),
      status: 'success'
    });
    
    // EOS calculation
    auditItems.push({
      icon: TrendingUp,
      title: 'مكافأة نهاية الخدمة',
      title_en: 'End of Service',
      detail: data.eos?.formula,
      subdetail: data.eos?.percentage_reason,
      value: formatCurrency(data.eos?.final_amount),
      status: data.eos?.final_amount > 0 ? 'success' : 'info'
    });
    
    // Leave compensation
    auditItems.push({
      icon: Calendar,
      title: 'بدل الإجازات',
      title_en: 'Leave Compensation',
      detail: data.leave?.formula,
      value: formatCurrency(data.leave?.compensation),
      status: 'success'
    });
    
    // Deductions
    if (data.deductions?.total > 0) {
      auditItems.push({
        icon: TrendingDown,
        title: 'خصومات',
        title_en: 'Deductions',
        detail: `${data.deductions?.count} عملية خصم`,
        value: `-${formatCurrency(data.deductions?.total)}`,
        status: 'warning'
      });
    }
    
    // Loans
    if (data.loans?.total > 0) {
      auditItems.push({
        icon: Wallet,
        title: 'سلف',
        title_en: 'Loans',
        detail: `${data.loans?.count} سلفة`,
        value: `-${formatCurrency(data.loans?.total)}`,
        status: 'warning'
      });
    }
    
    // Bank info
    const hasBank = data.contract?.bank_name && data.contract?.bank_iban;
    auditItems.push({
      icon: Landmark,
      title: 'معلومات البنك',
      title_en: 'Bank Info',
      detail: hasBank ? `${data.contract?.bank_name} - ${data.contract?.bank_iban}` : 'غير محدد',
      status: hasBank ? 'success' : 'error'
    });
    
    // Final calculation
    auditItems.push({
      icon: Calculator,
      title: 'المعادلة النهائية',
      title_en: 'Final Calculation',
      detail: `${formatCurrency(data.totals?.entitlements?.total)} - ${formatCurrency(data.totals?.deductions?.total)}`,
      value: formatCurrency(data.totals?.net_amount),
      status: 'final'
    });
    
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-primary" />
          <h3 className="font-bold">مرآة التدقيق - Audit Mirror</h3>
        </div>
        
        {auditItems.map((item, idx) => {
          const Icon = item.icon;
          const statusColors = {
            success: 'border-emerald-200 bg-emerald-50',
            warning: 'border-amber-200 bg-amber-50',
            error: 'border-red-200 bg-red-50',
            info: 'border-blue-200 bg-blue-50',
            final: 'border-primary bg-primary/5'
          };
          
          return (
            <div key={idx} className={`p-3 rounded-lg border ${statusColors[item.status]}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-2">
                  <Icon className="w-4 h-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <div className="font-medium text-sm">{item.title}</div>
                    <div className="text-xs text-muted-foreground">{item.title_en}</div>
                    <div className="text-xs mt-1">{item.detail}</div>
                    {item.subdetail && <div className="text-xs text-muted-foreground">{item.subdetail}</div>}
                  </div>
                </div>
                {item.value && (
                  <div className={`font-bold text-sm ${item.status === 'final' ? 'text-primary text-lg' : ''}`}>
                    {item.value}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Preview Sheet Component (محاكاة شكل PDF)
  const PreviewSheet = ({ data }) => {
    const snapshot = data;
    
    return (
      <div className="border rounded-lg p-4 bg-white text-sm max-h-[60vh] overflow-y-auto" style={{ fontFamily: 'Arial, sans-serif' }}>
        {/* Header */}
        <div className="grid grid-cols-2 border-b pb-2 mb-3">
          <div className="text-left text-xs">
            <div>Kingdom of Saudi Arabia – Riyadh</div>
            <div className="font-bold">Dar Al Code Engineering Consultancy</div>
            <div className="text-muted-foreground">License No: 5110004935 – CR: 1010463476</div>
          </div>
          <div className="text-right text-xs" dir="rtl">
            <div>المملكة العربية السعودية – الرياض</div>
            <div className="font-bold">شركة دار الكود للاستشارات الهندسية</div>
            <div className="text-muted-foreground">ترخيص رقم: 5110004935 – سجل تجاري: 1010463476</div>
          </div>
        </div>
        
        {/* Employee Info */}
        <div className="mb-3">
          <div className="grid grid-cols-2 bg-primary text-white text-xs p-1">
            <div className="text-left">Employee Information</div>
            <div className="text-right" dir="rtl">بيانات الموظف</div>
          </div>
          <table className="w-full text-xs border">
            <tbody>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.employee?.name_ar}</td>
                <td className="p-1 text-left bg-gray-50">Employee Name</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">اسم الموظف</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.employee?.name_ar}</td>
              </tr>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.employee?.employee_number}</td>
                <td className="p-1 text-left bg-gray-50">Employee ID</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">الرقم الوظيفي</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.employee?.employee_number}</td>
              </tr>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.contract?.last_working_day}</td>
                <td className="p-1 text-left bg-gray-50">Last Working Day</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">آخر يوم عمل</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.contract?.last_working_day}</td>
              </tr>
              <tr>
                <td className="p-1 text-left">{TERMINATION_TYPES[snapshot.contract?.termination_type]?.label_en}</td>
                <td className="p-1 text-left bg-gray-50">Clearance Type</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">نوع المخالصة</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.contract?.termination_type_label}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        {/* Salary Details */}
        <div className="mb-3">
          <div className="grid grid-cols-2 bg-primary text-white text-xs p-1">
            <div className="text-left">Salary & Allowances Details</div>
            <div className="text-right" dir="rtl">تفاصيل الراتب والبدلات</div>
          </div>
          <table className="w-full text-xs border">
            <tbody>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.wages?.basic?.toLocaleString()}</td>
                <td className="p-1 text-left bg-gray-50">Basic Salary</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">الراتب الأساسي</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.wages?.basic?.toLocaleString()}</td>
              </tr>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.wages?.housing?.toLocaleString()}</td>
                <td className="p-1 text-left bg-gray-50">Housing Allowance</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">بدل السكن</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.wages?.housing?.toLocaleString()}</td>
              </tr>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.wages?.nature_of_work?.toLocaleString()}</td>
                <td className="p-1 text-left bg-gray-50">Nature of Work Allowance</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">بدل طبيعة العمل</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.wages?.nature_of_work?.toLocaleString()}</td>
              </tr>
              <tr className="border-b">
                <td className="p-1 text-left">{snapshot.wages?.transport?.toLocaleString()}</td>
                <td className="p-1 text-left bg-gray-50">Transportation Allowance</td>
                <td className="p-1 text-right bg-gray-50" dir="rtl">بدل نقل</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.wages?.transport?.toLocaleString()}</td>
              </tr>
              <tr className="bg-emerald-50 font-bold">
                <td className="p-1 text-left">{snapshot.wages?.last_wage?.toLocaleString()}</td>
                <td className="p-1 text-left">Total Salary</td>
                <td className="p-1 text-right" dir="rtl">إجمالي الراتب</td>
                <td className="p-1 text-right" dir="rtl">{snapshot.wages?.last_wage?.toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        {/* Entitlements & Deductions */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div>
            <div className="bg-emerald-600 text-white text-xs p-1 text-center">Entitlements / الاستحقاقات</div>
            <table className="w-full text-xs border">
              <tbody>
                <tr className="border-b">
                  <td className="p-1">End of Service</td>
                  <td className="p-1 text-right">{snapshot.eos?.final_amount?.toLocaleString()}</td>
                </tr>
                <tr className="border-b">
                  <td className="p-1">Leave Compensation</td>
                  <td className="p-1 text-right">{snapshot.leave?.compensation?.toLocaleString()}</td>
                </tr>
                <tr className="bg-emerald-50 font-bold">
                  <td className="p-1">Total</td>
                  <td className="p-1 text-right">{snapshot.totals?.entitlements?.total?.toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div>
            <div className="bg-red-600 text-white text-xs p-1 text-center">Deductions / الاستقطاعات</div>
            <table className="w-full text-xs border">
              <tbody>
                <tr className="border-b">
                  <td className="p-1">Loans</td>
                  <td className="p-1 text-right">{snapshot.totals?.deductions?.loans?.toLocaleString()}</td>
                </tr>
                <tr className="border-b">
                  <td className="p-1">Other</td>
                  <td className="p-1 text-right">{snapshot.totals?.deductions?.deductions?.toLocaleString()}</td>
                </tr>
                <tr className="bg-red-50 font-bold">
                  <td className="p-1">Total</td>
                  <td className="p-1 text-right">{snapshot.totals?.deductions?.total?.toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Net Amount */}
        <div className="border-2 border-primary p-3 text-center mb-3 bg-primary/5">
          <div className="text-xs text-muted-foreground">Net Amount Payable to Employee / الصافي النهائي المستحق للموظف</div>
          <div className="text-2xl font-bold text-primary">{snapshot.totals?.net_amount?.toLocaleString()} SAR</div>
        </div>
        
        {/* Signatures placeholder */}
        <div className="grid grid-cols-4 gap-2 text-center text-xs border-t pt-2">
          <div>
            <div className="h-12 border border-dashed flex items-center justify-center text-muted-foreground">QR</div>
            <div>STAS</div>
          </div>
          <div>
            <div className="h-12 border border-dashed flex items-center justify-center text-muted-foreground">QR</div>
            <div>CEO</div>
          </div>
          <div>
            <div className="h-12 border border-dashed flex items-center justify-center text-muted-foreground">QR</div>
            <div>HR</div>
          </div>
          <div>
            <div className="h-12 border border-dashed flex items-center justify-center text-muted-foreground">توقيع يدوي</div>
            <div>Employee</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="settlement-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-xl">
            <Receipt className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">المخالصات</h1>
            <p className="text-muted-foreground text-sm">نظام المخالصة النهائية للموظفين</p>
          </div>
        </div>
        
        {canCreate && (
          <Button onClick={() => setCreateDialogOpen(true)} data-testid="create-settlement-btn">
            <Plus className="w-4 h-4 ml-2" />
            إنشاء مخالصة
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(SETTLEMENT_STATUS).map(([key, status]) => {
          const count = settlements.filter(s => s.status === key).length;
          const StatusIcon = status.icon;
          return (
            <Card 
              key={key} 
              className={`cursor-pointer transition-all hover:shadow-md ${statusFilter === key ? 'ring-2 ring-primary' : ''}`}
              onClick={() => setStatusFilter(statusFilter === key ? 'all' : key)}
            >
              <CardContent className="pt-4 pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">{status.label}</p>
                    <p className="text-2xl font-bold">{count}</p>
                  </div>
                  <div className={`p-2 rounded-lg ${status.color}`}>
                    <StatusIcon className="w-4 h-4 text-white" />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">الإجمالي</p>
                <p className="text-2xl font-bold">{settlements.length}</p>
              </div>
              <div className="p-2 rounded-lg bg-slate-500">
                <Receipt className="w-4 h-4 text-white" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Settlements List */}
      <Card data-testid="settlements-list">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="w-5 h-5" />
            قائمة المخالصات ({filteredSettlements.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredSettlements.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Receipt className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>لا توجد مخالصات</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredSettlements.map(settlement => {
                const statusInfo = SETTLEMENT_STATUS[settlement.status] || SETTLEMENT_STATUS.pending_stas;
                const StatusIcon = statusInfo.icon;
                const snapshot = settlement.snapshot || {};
                
                return (
                  <div 
                    key={settlement.id}
                    className="border rounded-xl p-4 hover:shadow-sm transition-all"
                    data-testid={`settlement-${settlement.transaction_number}`}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono font-bold text-primary">{settlement.transaction_number}</span>
                          <Badge className={`${statusInfo.color} text-white`}>
                            <StatusIcon className="w-3 h-3 ml-1" />
                            {statusInfo.label}
                          </Badge>
                          <Badge variant="outline">
                            {TERMINATION_TYPES[settlement.termination_type]?.label}
                          </Badge>
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                          <span className="flex items-center gap-1">
                            <Users className="w-3.5 h-3.5 text-muted-foreground" />
                            {settlement.employee_name}
                          </span>
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <span className="font-mono text-xs">{settlement.contract_serial}</span>
                          </span>
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground mt-2">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            آخر يوم: {formatDate(settlement.last_working_day)}
                          </span>
                          <span className="flex items-center gap-1 font-bold text-emerald-600">
                            <DollarSign className="w-3 h-3" />
                            صافي: {formatCurrency(snapshot.totals?.net_amount)}
                          </span>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Button variant="ghost" size="sm" onClick={() => setViewSettlement(settlement)}>
                          <Eye className="w-4 h-4" />
                        </Button>
                        
                        {settlement.status === 'executed' && (
                          <Button variant="ghost" size="sm" onClick={() => handleDownloadPDF(settlement.id)}>
                            <Download className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {settlement.status === 'pending_stas' && canExecute && (
                          <Button 
                            variant="default" 
                            size="sm" 
                            onClick={() => handleExecute(settlement.id)}
                            className="bg-emerald-600 hover:bg-emerald-700"
                          >
                            <Play className="w-4 h-4 ml-1" />
                            تنفيذ
                          </Button>
                        )}
                        
                        {settlement.status === 'pending_stas' && canCreate && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleCancel(settlement.id)}
                          >
                            <Ban className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Settlement Dialog - Multi-step */}
      <Dialog open={createDialogOpen} onOpenChange={(open) => { setCreateDialogOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-5xl max-h-[95vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="w-5 h-5" />
              {previewStep === 'form' && 'إنشاء مخالصة جديدة'}
              {previewStep === 'preview' && 'معاينة المخالصة'}
              {previewStep === 'audit' && 'تدقيق قبل التنفيذ'}
            </DialogTitle>
            <DialogDescription>
              {previewStep === 'form' && 'اختر الموظف ونوع الإنهاء لحساب المخالصة'}
              {previewStep === 'preview' && 'راجع شكل الورقة قبل الإنشاء'}
              {previewStep === 'audit' && 'تفاصيل الحسابات والتحقق من البيانات'}
            </DialogDescription>
          </DialogHeader>
          
          {/* Progress Steps */}
          <div className="flex items-center justify-center gap-2 py-2">
            <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm ${previewStep === 'form' ? 'bg-primary text-white' : 'bg-muted'}`}>
              <span>1</span> البيانات
            </div>
            <div className="w-8 h-0.5 bg-muted" />
            <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm ${previewStep === 'preview' ? 'bg-primary text-white' : 'bg-muted'}`}>
              <span>2</span> المعاينة
            </div>
            <div className="w-8 h-0.5 bg-muted" />
            <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm ${previewStep === 'audit' ? 'bg-primary text-white' : 'bg-muted'}`}>
              <span>3</span> التدقيق
            </div>
          </div>
          
          <div className="py-4">
            {/* Step 1: Form */}
            {previewStep === 'form' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>اختيار الموظف *</Label>
                    <Select value={formData.employee_id} onValueChange={v => setFormData(p => ({ ...p, employee_id: v }))}>
                      <SelectTrigger data-testid="settlement-employee-select">
                        <SelectValue placeholder="اختر موظف" />
                      </SelectTrigger>
                      <SelectContent>
                        {eligibleEmployees.map(emp => (
                          <SelectItem key={emp.id} value={emp.id}>
                            {emp.full_name_ar || emp.full_name} ({emp.employee_number})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>نوع الإنهاء *</Label>
                    <Select value={formData.termination_type} onValueChange={v => setFormData(p => ({ ...p, termination_type: v }))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(TERMINATION_TYPES).map(([key, val]) => (
                          <SelectItem key={key} value={key}>{val.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>آخر يوم عمل *</Label>
                    <Input 
                      type="date"
                      value={formData.last_working_day}
                      onChange={e => setFormData(p => ({ ...p, last_working_day: e.target.value }))}
                      data-testid="last-working-day-input"
                    />
                  </div>
                  
                  <div>
                    <Label>ملاحظات</Label>
                    <Input 
                      value={formData.note}
                      onChange={e => setFormData(p => ({ ...p, note: e.target.value }))}
                      placeholder="ملاحظات اختيارية"
                    />
                  </div>
                </div>
              </div>
            )}
            
            {/* Step 2: Preview */}
            {previewStep === 'preview' && previewData && (
              <div className="space-y-4">
                {/* Warnings */}
                {warnings.length > 0 && (
                  <div className="space-y-2">
                    {warnings.map((w, idx) => (
                      <Alert key={idx} variant={w.type === 'error' ? 'destructive' : 'default'}>
                        {w.type === 'error' && <AlertCircle className="w-4 h-4" />}
                        {w.type === 'warning' && <AlertTriangle className="w-4 h-4" />}
                        {w.type === 'info' && <Info className="w-4 h-4" />}
                        <AlertDescription>{w.message}</AlertDescription>
                      </Alert>
                    ))}
                  </div>
                )}
                
                <PreviewSheet data={previewData} />
              </div>
            )}
            
            {/* Step 3: Audit */}
            {previewStep === 'audit' && previewData && (
              <AuditTrail data={previewData} />
            )}
          </div>
          
          <DialogFooter className="gap-2">
            {previewStep === 'form' && (
              <>
                <Button variant="outline" onClick={() => { setCreateDialogOpen(false); resetForm(); }}>
                  إلغاء
                </Button>
                <Button onClick={handlePreview} disabled={actionLoading || !formData.employee_id || !formData.last_working_day}>
                  {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Calculator className="w-4 h-4 ml-2" />}
                  حساب ومعاينة
                </Button>
              </>
            )}
            
            {previewStep === 'preview' && (
              <>
                <Button variant="outline" onClick={() => setPreviewStep('form')}>
                  رجوع
                </Button>
                <Button variant="outline" onClick={() => setPreviewStep('audit')}>
                  <Shield className="w-4 h-4 ml-2" />
                  عرض التدقيق
                </Button>
                <Button 
                  onClick={handleCreateSettlement} 
                  disabled={actionLoading || warnings.some(w => w.type === 'error')}
                  data-testid="submit-settlement-btn"
                >
                  {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <FileCheck className="w-4 h-4 ml-2" />}
                  إنشاء المخالصة
                </Button>
              </>
            )}
            
            {previewStep === 'audit' && (
              <>
                <Button variant="outline" onClick={() => setPreviewStep('preview')}>
                  رجوع للمعاينة
                </Button>
                <Button 
                  onClick={handleCreateSettlement} 
                  disabled={actionLoading || warnings.some(w => w.type === 'error')}
                >
                  {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <CheckCircle2 className="w-4 h-4 ml-2" />}
                  تأكيد وإنشاء
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Settlement Dialog */}
      <Dialog open={!!viewSettlement} onOpenChange={() => setViewSettlement(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="w-5 h-5" />
              تفاصيل المخالصة: {viewSettlement?.transaction_number}
            </DialogTitle>
          </DialogHeader>
          
          {viewSettlement && (
            <Tabs defaultValue="preview" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="preview">المعاينة</TabsTrigger>
                <TabsTrigger value="audit">التدقيق</TabsTrigger>
              </TabsList>
              
              <TabsContent value="preview" className="mt-4">
                <PreviewSheet data={viewSettlement.snapshot} />
              </TabsContent>
              
              <TabsContent value="audit" className="mt-4">
                <AuditTrail data={viewSettlement.snapshot} />
              </TabsContent>
            </Tabs>
          )}
          
          <DialogFooter>
            {viewSettlement?.status === 'executed' && (
              <Button variant="outline" onClick={() => handleDownloadPDF(viewSettlement.id)}>
                <Download className="w-4 h-4 ml-2" /> تحميل PDF
              </Button>
            )}
            {viewSettlement?.status === 'pending_stas' && canExecute && (
              <Button 
                className="bg-emerald-600 hover:bg-emerald-700"
                onClick={() => handleExecute(viewSettlement.id)}
                disabled={actionLoading}
              >
                {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Play className="w-4 h-4 ml-2" />}
                تنفيذ المخالصة
              </Button>
            )}
            <Button variant="outline" onClick={() => setViewSettlement(null)}>إغلاق</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
