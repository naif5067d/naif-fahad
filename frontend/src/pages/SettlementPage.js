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
import { toast } from 'sonner';
import api from '@/lib/api';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { 
  Receipt, 
  Plus, 
  Search, 
  Eye, 
  Play, 
  XCircle, 
  CheckCircle, 
  Clock, 
  FileText,
  Users,
  Building2,
  Calendar,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Calculator,
  Ban,
  Download,
  Wallet,
  TrendingUp,
  TrendingDown,
  Landmark
} from 'lucide-react';

// أنواع إنهاء الخدمة
const TERMINATION_TYPES = {
  contract_expiry: { label: 'انتهاء العقد', color: 'bg-blue-500' },
  resignation: { label: 'استقالة', color: 'bg-amber-500' },
  probation_termination: { label: 'إنهاء خلال التجربة', color: 'bg-red-500' },
  mutual_agreement: { label: 'اتفاق طرفين', color: 'bg-green-500' },
  termination: { label: 'إنهاء من الشركة', color: 'bg-purple-500' },
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
  const [viewSettlement, setViewSettlement] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  
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

  // جلب الموظفين الذين لديهم عقد نشط أو منتهي (قابل للمخالصة)
  const eligibleEmployees = employees.filter(emp => {
    const contract = contracts.find(c => 
      c.employee_id === emp.id && 
      ['active', 'terminated'].includes(c.status)
    );
    return contract && emp.is_active !== false;
  });

  const handlePreview = async () => {
    if (!formData.employee_id || !formData.last_working_day) {
      toast.error('يرجى اختيار الموظف وتحديد آخر يوم عمل');
      return;
    }
    
    setActionLoading(true);
    try {
      const res = await api.post('/api/settlement/preview', formData);
      setPreviewData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل حساب المخالصة');
    }
    setActionLoading(false);
  };

  const handleCreateSettlement = async () => {
    if (!previewData) {
      toast.error('يرجى معاينة الحسابات أولاً');
      return;
    }
    
    setActionLoading(true);
    try {
      const res = await api.post('/api/settlement', formData);
      toast.success(`تم إنشاء طلب المخالصة: ${res.data.transaction_number}`);
      setCreateDialogOpen(false);
      setPreviewData(null);
      resetForm();
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل إنشاء المخالصة');
    }
    setActionLoading(false);
  };

  const handleExecute = async (settlementId) => {
    if (!confirm('هل تريد تنفيذ هذه المخالصة؟ هذا الإجراء نهائي ولا يمكن التراجع عنه.')) return;
    
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
  };

  const formatCurrency = (amount) => `${(amount || 0).toLocaleString()} ريال`;
  const formatDate = (dateStr) => formatGregorianHijri(dateStr).primary;

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

      {/* Create Settlement Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={(open) => { setCreateDialogOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>إنشاء مخالصة جديدة</DialogTitle>
            <DialogDescription>اختر الموظف ونوع الإنهاء لحساب المخالصة</DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* Step 1: Select Employee & Type */}
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
            
            {/* Preview Button */}
            <div className="flex justify-center">
              <Button onClick={handlePreview} disabled={actionLoading || !formData.employee_id || !formData.last_working_day}>
                {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Calculator className="w-4 h-4 ml-2" />}
                حساب المخالصة
              </Button>
            </div>
            
            {/* Preview Results */}
            {previewData && (
              <div className="space-y-4 border-t pt-4">
                <h3 className="font-bold text-lg flex items-center gap-2">
                  <Receipt className="w-5 h-5" />
                  معاينة المخالصة
                </h3>
                
                {/* Employee & Contract Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Users className="w-4 h-4" /> بيانات الموظف
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">الاسم:</span>
                        <span>{previewData.employee.name_ar}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">الرقم الوظيفي:</span>
                        <span className="font-mono">{previewData.employee.employee_number}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">رقم العقد:</span>
                        <span className="font-mono">{previewData.contract.serial}</span>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Landmark className="w-4 h-4" /> معلومات البنك
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">البنك:</span>
                        <span>{previewData.contract.bank_name || '-'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">IBAN:</span>
                        <span className="font-mono text-xs">{previewData.contract.bank_iban || '-'}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
                
                {/* Service & Wage Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Calendar className="w-4 h-4" /> مدة الخدمة
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">المدة:</span>
                        <span className="font-bold">{previewData.service.formatted_ar}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">إجمالي الأيام:</span>
                        <span>{previewData.service.total_days} يوم</span>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Wallet className="w-4 h-4" /> آخر راتب شامل
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <div className="flex justify-between font-bold text-primary">
                        <span>الإجمالي:</span>
                        <span>{formatCurrency(previewData.wages.last_wage)}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {previewData.wages.formula}
                      </p>
                    </CardContent>
                  </Card>
                </div>
                
                {/* Financial Summary */}
                <Card className="bg-emerald-50 border-emerald-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2 text-emerald-700">
                      <TrendingUp className="w-4 h-4" /> الاستحقاقات
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm space-y-2">
                    <div className="flex justify-between">
                      <span>مكافأة نهاية الخدمة:</span>
                      <span className="font-bold">{formatCurrency(previewData.eos.final_amount)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{previewData.eos.formula}</p>
                    <p className="text-xs text-muted-foreground">{previewData.eos.percentage_reason}</p>
                    
                    <div className="flex justify-between border-t pt-2">
                      <span>بدل الإجازات ({previewData.leave.balance.toFixed(2)} يوم):</span>
                      <span className="font-bold">{formatCurrency(previewData.leave.compensation)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{previewData.leave.formula}</p>
                    
                    {previewData.bonuses.total > 0 && (
                      <div className="flex justify-between border-t pt-2">
                        <span>مكافآت:</span>
                        <span className="font-bold">{formatCurrency(previewData.bonuses.total)}</span>
                      </div>
                    )}
                    
                    <div className="flex justify-between border-t pt-2 text-emerald-700 font-bold">
                      <span>إجمالي الاستحقاقات:</span>
                      <span>{formatCurrency(previewData.totals.entitlements.total)}</span>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="bg-red-50 border-red-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2 text-red-700">
                      <TrendingDown className="w-4 h-4" /> الاستقطاعات
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm space-y-2">
                    {previewData.deductions.total > 0 && (
                      <div className="flex justify-between">
                        <span>خصومات ({previewData.deductions.count}):</span>
                        <span className="font-bold text-red-600">-{formatCurrency(previewData.deductions.total)}</span>
                      </div>
                    )}
                    
                    {previewData.loans.total > 0 && (
                      <div className="flex justify-between">
                        <span>سلف ({previewData.loans.count}):</span>
                        <span className="font-bold text-red-600">-{formatCurrency(previewData.loans.total)}</span>
                      </div>
                    )}
                    
                    {previewData.totals.deductions.total === 0 && (
                      <p className="text-muted-foreground">لا توجد استقطاعات</p>
                    )}
                    
                    <div className="flex justify-between border-t pt-2 text-red-700 font-bold">
                      <span>إجمالي الاستقطاعات:</span>
                      <span>-{formatCurrency(previewData.totals.deductions.total)}</span>
                    </div>
                  </CardContent>
                </Card>
                
                {/* Net Amount */}
                <Card className="bg-primary text-white">
                  <CardContent className="py-4">
                    <div className="flex justify-between items-center text-lg">
                      <span className="font-bold">صافي المخالصة:</span>
                      <span className="text-2xl font-bold">{formatCurrency(previewData.totals.net_amount)}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => { setCreateDialogOpen(false); resetForm(); }}>
              إلغاء
            </Button>
            {previewData && (
              <Button onClick={handleCreateSettlement} disabled={actionLoading} data-testid="submit-settlement-btn">
                {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Plus className="w-4 h-4 ml-2" />}
                إنشاء طلب المخالصة
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Settlement Dialog */}
      <Dialog open={!!viewSettlement} onOpenChange={() => setViewSettlement(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Receipt className="w-5 h-5" />
              تفاصيل المخالصة: {viewSettlement?.transaction_number}
            </DialogTitle>
          </DialogHeader>
          
          {viewSettlement && (
            <div className="space-y-4">
              {/* Status */}
              <div className="flex items-center gap-2">
                <Badge className={`${SETTLEMENT_STATUS[viewSettlement.status]?.color} text-white`}>
                  {SETTLEMENT_STATUS[viewSettlement.status]?.label}
                </Badge>
                <Badge variant="outline">
                  {TERMINATION_TYPES[viewSettlement.termination_type]?.label}
                </Badge>
              </div>
              
              {/* Summary from Snapshot */}
              {viewSettlement.snapshot && (
                <>
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-sm">بيانات الموظف</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">الاسم:</span>
                        <span>{viewSettlement.snapshot.employee.name_ar}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">رقم العقد:</span>
                        <span className="font-mono">{viewSettlement.snapshot.contract.serial}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">آخر يوم عمل:</span>
                        <span>{formatDate(viewSettlement.snapshot.contract.last_working_day)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">مدة الخدمة:</span>
                        <span>{viewSettlement.snapshot.service.formatted_ar}</span>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-sm">ملخص مالي</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-2">
                      <div className="flex justify-between">
                        <span>مكافأة نهاية الخدمة:</span>
                        <span className="font-bold">{formatCurrency(viewSettlement.snapshot.eos.final_amount)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>بدل الإجازات:</span>
                        <span className="font-bold">{formatCurrency(viewSettlement.snapshot.leave.compensation)}</span>
                      </div>
                      <div className="flex justify-between text-emerald-600">
                        <span>إجمالي الاستحقاقات:</span>
                        <span className="font-bold">{formatCurrency(viewSettlement.snapshot.totals.entitlements.total)}</span>
                      </div>
                      <div className="flex justify-between text-red-600">
                        <span>إجمالي الاستقطاعات:</span>
                        <span className="font-bold">-{formatCurrency(viewSettlement.snapshot.totals.deductions.total)}</span>
                      </div>
                      <div className="flex justify-between border-t pt-2 text-primary font-bold text-lg">
                        <span>صافي المخالصة:</span>
                        <span>{formatCurrency(viewSettlement.snapshot.totals.net_amount)}</span>
                      </div>
                    </CardContent>
                  </Card>
                  
                  {/* Bank Info */}
                  {(viewSettlement.snapshot.contract.bank_name || viewSettlement.snapshot.contract.bank_iban) && (
                    <Card>
                      <CardHeader className="py-3">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <Landmark className="w-4 h-4" /> معلومات البنك
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="text-sm space-y-1">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">البنك:</span>
                          <span>{viewSettlement.snapshot.contract.bank_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">IBAN:</span>
                          <span className="font-mono">{viewSettlement.snapshot.contract.bank_iban}</span>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
              
              {/* Execution Info */}
              {viewSettlement.status === 'executed' && (
                <Card className="bg-emerald-50 border-emerald-200">
                  <CardContent className="py-3 text-sm">
                    <div className="flex items-center gap-2 text-emerald-700">
                      <CheckCircle className="w-4 h-4" />
                      <span>تم التنفيذ بتاريخ: {formatDate(viewSettlement.executed_at)}</span>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
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
