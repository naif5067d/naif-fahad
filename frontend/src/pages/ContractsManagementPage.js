import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import api from '@/lib/api';
import { formatGregorianHijri } from '@/lib/dateUtils';
import { 
  FileSignature, 
  Plus, 
  Search, 
  Eye, 
  Edit, 
  Send, 
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
  Trash2,
  RefreshCw,
  ChevronRight,
  FileCheck,
  Ban,
  Archive
} from 'lucide-react';

const CONTRACT_STATUS = {
  draft: { label: 'مسودة', labelEn: 'Draft', color: 'bg-slate-500', icon: Edit },
  pending_stas: { label: 'في انتظار STAS', labelEn: 'Pending STAS', color: 'bg-amber-500', icon: Clock },
  active: { label: 'نشط', labelEn: 'Active', color: 'bg-emerald-500', icon: CheckCircle },
  terminated: { label: 'منتهي', labelEn: 'Terminated', color: 'bg-red-500', icon: XCircle },
  closed: { label: 'مغلق', labelEn: 'Closed', color: 'bg-gray-600', icon: Archive },
};

const CONTRACT_CATEGORIES = {
  employment: { label: 'توظيف', labelEn: 'Employment' },
  internship_unpaid: { label: 'تدريب غير مدفوع', labelEn: 'Unpaid Internship' },
};

const EMPLOYMENT_TYPES = {
  unlimited: { label: 'غير محدد المدة', labelEn: 'Unlimited' },
  fixed_term: { label: 'محدد المدة', labelEn: 'Fixed Term' },
  trial_paid: { label: 'فترة تجربة مدفوعة', labelEn: 'Paid Trial' },
};

const TERMINATION_REASONS = {
  resignation: { label: 'استقالة', labelEn: 'Resignation' },
  termination: { label: 'إنهاء من الشركة', labelEn: 'Termination' },
  contract_expiry: { label: 'انتهاء العقد', labelEn: 'Contract Expiry' },
  retirement: { label: 'تقاعد', labelEn: 'Retirement' },
  death: { label: 'وفاة', labelEn: 'Death' },
  mutual_agreement: { label: 'اتفاق متبادل', labelEn: 'Mutual Agreement' },
};

export default function ContractsManagementPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  
  const [contracts, setContracts] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  
  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [viewContract, setViewContract] = useState(null);
  const [editContract, setEditContract] = useState(null);
  const [terminateContract, setTerminateContract] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    employee_id: '',
    employee_code: '',
    employee_name: '',
    employee_name_ar: '',
    contract_category: 'employment',
    employment_type: 'unlimited',
    job_title: '',
    job_title_ar: '',
    department: '',
    department_ar: '',
    start_date: '',
    end_date: '',
    probation_months: 3,
    notice_period_days: 30,
    basic_salary: 0,
    housing_allowance: 0,
    transport_allowance: 0,
    other_allowances: 0,
    wage_definition: 'basic_only',
    is_migrated: false,
    leave_opening_balance: { annual: 0, sick: 0, emergency: 0 },
    notes: '',
  });
  
  // Termination form
  const [terminationData, setTerminationData] = useState({
    termination_date: '',
    termination_reason: 'resignation',
    note: '',
  });
  
  const [actionLoading, setActionLoading] = useState(false);
  
  const canCreate = ['sultan', 'naif', 'stas'].includes(user?.role);
  const canExecute = user?.role === 'stas';
  const canTerminate = user?.role === 'stas';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [contractsRes, employeesRes] = await Promise.all([
        api.get('/api/contracts-v2'),
        api.get('/api/employees'),
      ]);
      setContracts(contractsRes.data || []);
      setEmployees(employeesRes.data || []);
    } catch (err) {
      toast.error('فشل تحميل البيانات');
    }
    setLoading(false);
  };

  const handleSearch = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (categoryFilter !== 'all') params.append('category', categoryFilter);
      
      const res = await api.get(`/api/contracts-v2/search?${params.toString()}`);
      setContracts(res.data || []);
    } catch (err) {
      toast.error('فشل البحث');
    }
  };

  const handleEmployeeSelect = (empId) => {
    const emp = employees.find(e => e.id === empId);
    if (emp) {
      setFormData(prev => ({
        ...prev,
        employee_id: emp.id,
        employee_code: emp.employee_number || emp.id,
        employee_name: emp.full_name,
        employee_name_ar: emp.full_name_ar || emp.full_name,
        job_title: emp.position || '',
        job_title_ar: emp.position_ar || '',
        department: emp.department || '',
        department_ar: emp.department_ar || '',
      }));
    }
  };

  const handleCreateContract = async () => {
    if (!formData.employee_id || !formData.start_date) {
      toast.error('يرجى ملء الحقول المطلوبة');
      return;
    }
    
    setActionLoading(true);
    try {
      const payload = { ...formData };
      
      // Clean up salary for unpaid internship
      if (formData.contract_category === 'internship_unpaid') {
        payload.basic_salary = 0;
        payload.housing_allowance = 0;
        payload.transport_allowance = 0;
        payload.other_allowances = 0;
      }
      
      const res = await api.post('/api/contracts-v2', payload);
      toast.success(`تم إنشاء العقد: ${res.data.contract_serial}`);
      setCreateDialogOpen(false);
      resetForm();
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل إنشاء العقد');
    }
    setActionLoading(false);
  };

  const handleUpdateContract = async () => {
    if (!editContract) return;
    
    setActionLoading(true);
    try {
      await api.put(`/api/contracts-v2/${editContract.id}`, formData);
      toast.success('تم تحديث العقد');
      setEditContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل التحديث');
    }
    setActionLoading(false);
  };

  const handleSubmitToSTAS = async (contractId) => {
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${contractId}/submit`);
      toast.success('تم إرسال العقد إلى STAS');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل الإرسال');
    }
    setActionLoading(false);
  };

  const handleExecuteContract = async (contractId) => {
    setActionLoading(true);
    try {
      const res = await api.post(`/api/contracts-v2/${contractId}/execute`);
      toast.success('تم تنفيذ وتفعيل العقد');
      setViewContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل التنفيذ');
    }
    setActionLoading(false);
  };

  const handleTerminateContract = async () => {
    if (!terminateContract || !terminationData.termination_date) {
      toast.error('يرجى ملء تاريخ الإنهاء');
      return;
    }
    
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${terminateContract.id}/terminate`, terminationData);
      toast.success('تم إنهاء العقد');
      setTerminateContract(null);
      setTerminationData({ termination_date: '', termination_reason: 'resignation', note: '' });
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل الإنهاء');
    }
    setActionLoading(false);
  };

  const handleDeleteContract = async (contractId) => {
    if (!confirm('هل تريد حذف هذا العقد؟')) return;
    
    try {
      await api.delete(`/api/contracts-v2/${contractId}`);
      toast.success('تم حذف العقد');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل الحذف');
    }
  };

  const handlePreviewPDF = async (contractId) => {
    try {
      const res = await api.get(`/api/contracts-v2/${contractId}/pdf?lang=ar`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      window.open(url, '_blank');
    } catch (err) {
      toast.error('فشل تحميل PDF');
    }
  };

  const resetForm = () => {
    setFormData({
      employee_id: '',
      employee_code: '',
      employee_name: '',
      employee_name_ar: '',
      contract_category: 'employment',
      employment_type: 'unlimited',
      job_title: '',
      job_title_ar: '',
      department: '',
      department_ar: '',
      start_date: '',
      end_date: '',
      probation_months: 3,
      notice_period_days: 30,
      basic_salary: 0,
      housing_allowance: 0,
      transport_allowance: 0,
      other_allowances: 0,
      wage_definition: 'basic_only',
      is_migrated: false,
      leave_opening_balance: { annual: 0, sick: 0, emergency: 0 },
      notes: '',
    });
  };

  const openEditDialog = (contract) => {
    setFormData({
      employee_id: contract.employee_id,
      employee_code: contract.employee_code,
      employee_name: contract.employee_name,
      employee_name_ar: contract.employee_name_ar,
      contract_category: contract.contract_category,
      employment_type: contract.employment_type,
      job_title: contract.job_title,
      job_title_ar: contract.job_title_ar,
      department: contract.department,
      department_ar: contract.department_ar,
      start_date: contract.start_date,
      end_date: contract.end_date || '',
      probation_months: contract.probation_months,
      notice_period_days: contract.notice_period_days,
      basic_salary: contract.basic_salary,
      housing_allowance: contract.housing_allowance,
      transport_allowance: contract.transport_allowance,
      other_allowances: contract.other_allowances,
      wage_definition: contract.wage_definition,
      is_migrated: contract.is_migrated,
      leave_opening_balance: contract.leave_opening_balance || { annual: 0, sick: 0, emergency: 0 },
      notes: contract.notes || '',
    });
    setEditContract(contract);
  };

  const formatDate = (dateStr) => {
    return formatGregorianHijri(dateStr).combined;
  };

  const formatCurrency = (amount) => {
    return `${(amount || 0).toLocaleString()} ريال`;
  };

  const getTotalSalary = (contract) => {
    return (contract.basic_salary || 0) + 
           (contract.housing_allowance || 0) + 
           (contract.transport_allowance || 0) + 
           (contract.other_allowances || 0);
  };

  const filteredContracts = contracts.filter(c => {
    if (statusFilter !== 'all' && c.status !== statusFilter) return false;
    if (categoryFilter !== 'all' && c.contract_category !== categoryFilter) return false;
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
    <div className="space-y-6 p-4 md:p-6" data-testid="contracts-management-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-xl">
            <FileSignature className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">إدارة العقود</h1>
            <p className="text-muted-foreground text-sm">نظام العقود الجديد - DAC-YYYY-XXX</p>
          </div>
        </div>
        
        {canCreate && (
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="create-contract-btn">
                <Plus className="w-4 h-4 ml-2" />
                إنشاء عقد جديد
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>إنشاء عقد جديد</DialogTitle>
                <DialogDescription>أدخل بيانات العقد الجديد</DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                {/* Employee Selection */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <Label>الموظف *</Label>
                    <Select value={formData.employee_id} onValueChange={handleEmployeeSelect}>
                      <SelectTrigger data-testid="employee-select">
                        <SelectValue placeholder="اختر موظف" />
                      </SelectTrigger>
                      <SelectContent>
                        {employees.map(emp => (
                          <SelectItem key={emp.id} value={emp.id}>
                            {emp.full_name_ar || emp.full_name} ({emp.employee_number || emp.id})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                {/* Contract Category & Type */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>فئة العقد</Label>
                    <Select 
                      value={formData.contract_category} 
                      onValueChange={v => setFormData(p => ({ ...p, contract_category: v }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(CONTRACT_CATEGORIES).map(([key, val]) => (
                          <SelectItem key={key} value={key}>{val.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>نوع العقد</Label>
                    <Select 
                      value={formData.employment_type} 
                      onValueChange={v => setFormData(p => ({ ...p, employment_type: v }))}
                      disabled={formData.contract_category === 'internship_unpaid'}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(EMPLOYMENT_TYPES).map(([key, val]) => (
                          <SelectItem key={key} value={key}>{val.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                {/* Dates */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>تاريخ البداية *</Label>
                    <Input 
                      type="date" 
                      value={formData.start_date}
                      onChange={e => setFormData(p => ({ ...p, start_date: e.target.value }))}
                      data-testid="start-date-input"
                    />
                  </div>
                  <div>
                    <Label>تاريخ النهاية (اختياري)</Label>
                    <Input 
                      type="date" 
                      value={formData.end_date}
                      onChange={e => setFormData(p => ({ ...p, end_date: e.target.value }))}
                    />
                  </div>
                </div>
                
                {/* Probation & Notice */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>فترة التجربة (شهر)</Label>
                    <Input 
                      type="number" 
                      value={formData.probation_months}
                      onChange={e => setFormData(p => ({ ...p, probation_months: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                  <div>
                    <Label>فترة الإنذار (يوم)</Label>
                    <Input 
                      type="number" 
                      value={formData.notice_period_days}
                      onChange={e => setFormData(p => ({ ...p, notice_period_days: parseInt(e.target.value) || 0 }))}
                    />
                  </div>
                </div>
                
                {/* Salary (hidden for unpaid internship) */}
                {formData.contract_category !== 'internship_unpaid' && (
                  <>
                    <div className="border-t pt-4">
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        <DollarSign className="w-4 h-4" /> تفاصيل الراتب
                      </h4>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>الراتب الأساسي</Label>
                        <Input 
                          type="number" 
                          value={formData.basic_salary}
                          onChange={e => setFormData(p => ({ ...p, basic_salary: parseFloat(e.target.value) || 0 }))}
                          data-testid="basic-salary-input"
                        />
                      </div>
                      <div>
                        <Label>بدل السكن</Label>
                        <Input 
                          type="number" 
                          value={formData.housing_allowance}
                          onChange={e => setFormData(p => ({ ...p, housing_allowance: parseFloat(e.target.value) || 0 }))}
                        />
                      </div>
                      <div>
                        <Label>بدل النقل</Label>
                        <Input 
                          type="number" 
                          value={formData.transport_allowance}
                          onChange={e => setFormData(p => ({ ...p, transport_allowance: parseFloat(e.target.value) || 0 }))}
                        />
                      </div>
                      <div>
                        <Label>بدلات أخرى</Label>
                        <Input 
                          type="number" 
                          value={formData.other_allowances}
                          onChange={e => setFormData(p => ({ ...p, other_allowances: parseFloat(e.target.value) || 0 }))}
                        />
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                      إجمالي الراتب: <span className="font-bold">{formatCurrency(
                        formData.basic_salary + formData.housing_allowance + formData.transport_allowance + formData.other_allowances
                      )}</span>
                    </div>
                  </>
                )}
                
                {/* Migration Toggle */}
                <div className="flex items-center justify-between border-t pt-4">
                  <div>
                    <Label>عقد مُهاجر (موظف قديم)</Label>
                    <p className="text-xs text-muted-foreground">تفعيل هذا الخيار لإضافة رصيد إجازات افتتاحي</p>
                  </div>
                  <Switch 
                    checked={formData.is_migrated}
                    onCheckedChange={v => setFormData(p => ({ ...p, is_migrated: v }))}
                  />
                </div>
                
                {formData.is_migrated && (
                  <div className="grid grid-cols-3 gap-4 bg-amber-50 p-3 rounded-lg">
                    <div>
                      <Label className="text-xs">رصيد سنوي افتتاحي</Label>
                      <Input 
                        type="number" 
                        value={formData.leave_opening_balance.annual}
                        onChange={e => setFormData(p => ({ 
                          ...p, 
                          leave_opening_balance: { ...p.leave_opening_balance, annual: parseInt(e.target.value) || 0 }
                        }))}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">رصيد مرضي افتتاحي</Label>
                      <Input 
                        type="number" 
                        value={formData.leave_opening_balance.sick}
                        onChange={e => setFormData(p => ({ 
                          ...p, 
                          leave_opening_balance: { ...p.leave_opening_balance, sick: parseInt(e.target.value) || 0 }
                        }))}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">رصيد طوارئ افتتاحي</Label>
                      <Input 
                        type="number" 
                        value={formData.leave_opening_balance.emergency}
                        onChange={e => setFormData(p => ({ 
                          ...p, 
                          leave_opening_balance: { ...p.leave_opening_balance, emergency: parseInt(e.target.value) || 0 }
                        }))}
                      />
                    </div>
                  </div>
                )}
                
                {/* Notes */}
                <div>
                  <Label>ملاحظات</Label>
                  <Textarea 
                    value={formData.notes}
                    onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))}
                    rows={2}
                  />
                </div>
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => { setCreateDialogOpen(false); resetForm(); }}>
                  إلغاء
                </Button>
                <Button onClick={handleCreateContract} disabled={actionLoading} data-testid="submit-contract-btn">
                  {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Plus className="w-4 h-4 ml-2" />}
                  إنشاء العقد
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Search & Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input 
                placeholder="بحث برقم العقد، كود الموظف، أو الاسم..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                className="pr-10"
                data-testid="search-input"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="الحالة" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">كل الحالات</SelectItem>
                {Object.entries(CONTRACT_STATUS).map(([key, val]) => (
                  <SelectItem key={key} value={key}>{val.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="الفئة" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">كل الفئات</SelectItem>
                {Object.entries(CONTRACT_CATEGORIES).map(([key, val]) => (
                  <SelectItem key={key} value={key}>{val.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={handleSearch}>
              <Search className="w-4 h-4 ml-1" /> بحث
            </Button>
            <Button variant="ghost" onClick={loadData}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(CONTRACT_STATUS).map(([key, status]) => {
          const count = contracts.filter(c => c.status === key).length;
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
      </div>

      {/* Contracts List */}
      <Card data-testid="contracts-list">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSignature className="w-5 h-5" />
            العقود ({filteredContracts.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredContracts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileSignature className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>لا توجد عقود</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredContracts.map(contract => {
                const statusInfo = CONTRACT_STATUS[contract.status] || CONTRACT_STATUS.draft;
                const StatusIcon = statusInfo.icon;
                
                return (
                  <div 
                    key={contract.id}
                    className="border rounded-xl p-4 hover:shadow-sm transition-all"
                    data-testid={`contract-${contract.contract_serial}`}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      {/* Contract Info */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono font-bold text-primary">{contract.contract_serial}</span>
                          <Badge className={`${statusInfo.color} text-white`}>
                            <StatusIcon className="w-3 h-3 ml-1" />
                            {statusInfo.label}
                          </Badge>
                          {contract.is_migrated && (
                            <Badge variant="outline" className="text-amber-600 border-amber-300">
                              مُهاجر
                            </Badge>
                          )}
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                          <span className="flex items-center gap-1">
                            <Users className="w-3.5 h-3.5 text-muted-foreground" />
                            {contract.employee_name_ar || contract.employee_name}
                          </span>
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <span className="font-mono text-xs">{contract.employee_code}</span>
                          </span>
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <Building2 className="w-3.5 h-3.5" />
                            {contract.department_ar || contract.department || '-'}
                          </span>
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground mt-2">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(contract.start_date)}
                            {contract.end_date && ` - ${formatDate(contract.end_date)}`}
                          </span>
                          {contract.contract_category !== 'internship_unpaid' && (
                            <span className="flex items-center gap-1">
                              <DollarSign className="w-3 h-3" />
                              {formatCurrency(getTotalSalary(contract))}
                            </span>
                          )}
                          <span>
                            {CONTRACT_CATEGORIES[contract.contract_category]?.label || contract.contract_category}
                          </span>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Button variant="ghost" size="sm" onClick={() => setViewContract(contract)}>
                          <Eye className="w-4 h-4" />
                        </Button>
                        
                        <Button variant="ghost" size="sm" onClick={() => handlePreviewPDF(contract.id)}>
                          <FileText className="w-4 h-4" />
                        </Button>
                        
                        {/* Edit - only draft/pending_stas */}
                        {['draft', 'pending_stas'].includes(contract.status) && canCreate && (
                          <Button variant="ghost" size="sm" onClick={() => openEditDialog(contract)}>
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Submit to STAS - only draft */}
                        {contract.status === 'draft' && canCreate && (
                          <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={() => handleSubmitToSTAS(contract.id)}
                            className="text-amber-600 border-amber-300 hover:bg-amber-50"
                          >
                            <Send className="w-4 h-4 ml-1" />
                            إرسال لـ STAS
                          </Button>
                        )}
                        
                        {/* Execute - only pending_stas & STAS role */}
                        {contract.status === 'pending_stas' && canExecute && (
                          <Button 
                            variant="default" 
                            size="sm" 
                            onClick={() => handleExecuteContract(contract.id)}
                            className="bg-emerald-600 hover:bg-emerald-700"
                          >
                            <Play className="w-4 h-4 ml-1" />
                            تنفيذ
                          </Button>
                        )}
                        
                        {/* Terminate - only active & STAS role */}
                        {contract.status === 'active' && canTerminate && (
                          <Button 
                            variant="destructive" 
                            size="sm" 
                            onClick={() => setTerminateContract(contract)}
                          >
                            <Ban className="w-4 h-4 ml-1" />
                            إنهاء
                          </Button>
                        )}
                        
                        {/* Delete - only draft/pending_stas */}
                        {['draft', 'pending_stas'].includes(contract.status) && canCreate && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleDeleteContract(contract.id)}
                          >
                            <Trash2 className="w-4 h-4" />
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

      {/* View Contract Dialog */}
      <Dialog open={!!viewContract} onOpenChange={() => setViewContract(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSignature className="w-5 h-5" />
              تفاصيل العقد: {viewContract?.contract_serial}
            </DialogTitle>
          </DialogHeader>
          
          {viewContract && (
            <div className="space-y-4">
              {/* Status */}
              <div className="flex items-center gap-2">
                <Badge className={`${CONTRACT_STATUS[viewContract.status]?.color} text-white`}>
                  {CONTRACT_STATUS[viewContract.status]?.label}
                </Badge>
                {viewContract.is_migrated && (
                  <Badge variant="outline" className="text-amber-600">مُهاجر</Badge>
                )}
                <Badge variant="outline">V{viewContract.version}</Badge>
              </div>
              
              {/* Employee Info */}
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Users className="w-4 h-4" /> بيانات الموظف
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">الاسم:</span>
                    <span>{viewContract.employee_name_ar || viewContract.employee_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">الكود:</span>
                    <span className="font-mono">{viewContract.employee_code}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">المسمى:</span>
                    <span>{viewContract.job_title_ar || viewContract.job_title || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">القسم:</span>
                    <span>{viewContract.department_ar || viewContract.department || '-'}</span>
                  </div>
                </CardContent>
              </Card>
              
              {/* Contract Details */}
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <FileCheck className="w-4 h-4" /> تفاصيل العقد
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">الفئة:</span>
                    <span>{CONTRACT_CATEGORIES[viewContract.contract_category]?.label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">النوع:</span>
                    <span>{EMPLOYMENT_TYPES[viewContract.employment_type]?.label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">تاريخ البداية:</span>
                    <span>{formatDate(viewContract.start_date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">تاريخ النهاية:</span>
                    <span>{viewContract.end_date ? formatDate(viewContract.end_date) : 'غير محدد'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">فترة التجربة:</span>
                    <span>{viewContract.probation_months} شهر</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">فترة الإنذار:</span>
                    <span>{viewContract.notice_period_days} يوم</span>
                  </div>
                </CardContent>
              </Card>
              
              {/* Salary (if applicable) */}
              {viewContract.contract_category !== 'internship_unpaid' && (
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <DollarSign className="w-4 h-4" /> تفاصيل الراتب
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="py-2 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">الراتب الأساسي:</span>
                      <span>{formatCurrency(viewContract.basic_salary)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">بدل السكن:</span>
                      <span>{formatCurrency(viewContract.housing_allowance)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">بدل النقل:</span>
                      <span>{formatCurrency(viewContract.transport_allowance)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">بدلات أخرى:</span>
                      <span>{formatCurrency(viewContract.other_allowances)}</span>
                    </div>
                    <div className="flex justify-between border-t pt-2 font-bold">
                      <span>الإجمالي:</span>
                      <span className="text-primary">{formatCurrency(getTotalSalary(viewContract))}</span>
                    </div>
                  </CardContent>
                </Card>
              )}
              
              {/* Termination Info (if terminated) */}
              {viewContract.termination_date && (
                <Card className="border-red-200 bg-red-50">
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm flex items-center gap-2 text-red-700">
                      <AlertTriangle className="w-4 h-4" /> معلومات الإنهاء
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="py-2 space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">تاريخ الإنهاء:</span>
                      <span>{formatDate(viewContract.termination_date)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">السبب:</span>
                      <span>{TERMINATION_REASONS[viewContract.termination_reason]?.label || viewContract.termination_reason}</span>
                    </div>
                  </CardContent>
                </Card>
              )}
              
              {/* Status History */}
              {viewContract.status_history?.length > 0 && (
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Clock className="w-4 h-4" /> سجل الحالات
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="py-2">
                    <div className="space-y-2">
                      {viewContract.status_history.map((h, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs">
                          <ChevronRight className="w-3 h-3 mt-0.5 text-muted-foreground" />
                          <div className="flex-1">
                            <span className="font-medium">{h.to_status}</span>
                            <span className="text-muted-foreground"> - {h.actor_name || h.actor_id}</span>
                            <p className="text-muted-foreground">{h.note}</p>
                            <p className="text-muted-foreground font-mono">{formatDate(h.timestamp)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => handlePreviewPDF(viewContract?.id)}>
              <FileText className="w-4 h-4 ml-2" /> عرض PDF
            </Button>
            <Button variant="outline" onClick={() => setViewContract(null)}>إغلاق</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Terminate Contract Dialog */}
      <Dialog open={!!terminateContract} onOpenChange={() => setTerminateContract(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" /> إنهاء العقد
            </DialogTitle>
            <DialogDescription>
              سيتم إنهاء العقد: {terminateContract?.contract_serial}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label>تاريخ الإنهاء *</Label>
              <Input 
                type="date"
                value={terminationData.termination_date}
                onChange={e => setTerminationData(p => ({ ...p, termination_date: e.target.value }))}
              />
            </div>
            <div>
              <Label>سبب الإنهاء</Label>
              <Select 
                value={terminationData.termination_reason}
                onValueChange={v => setTerminationData(p => ({ ...p, termination_reason: v }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TERMINATION_REASONS).map(([key, val]) => (
                    <SelectItem key={key} value={key}>{val.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>ملاحظات</Label>
              <Textarea 
                value={terminationData.note}
                onChange={e => setTerminationData(p => ({ ...p, note: e.target.value }))}
                rows={2}
              />
            </div>
            
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm">
              <p className="flex items-center gap-2 text-amber-700">
                <AlertTriangle className="w-4 h-4" />
                <strong>تنبيه:</strong>
              </p>
              <ul className="list-disc list-inside text-amber-600 mt-1 text-xs">
                <li>سيتم إيقاف الحضور والطلبات للموظف</li>
                <li>سيبقى الحساب نشطاً حتى إتمام المخالصة</li>
                <li>هذا الإجراء لا يمكن التراجع عنه</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setTerminateContract(null)}>إلغاء</Button>
            <Button 
              variant="destructive" 
              onClick={handleTerminateContract}
              disabled={actionLoading || !terminationData.termination_date}
            >
              {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Ban className="w-4 h-4 ml-2" />}
              تأكيد الإنهاء
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Contract Dialog */}
      <Dialog open={!!editContract} onOpenChange={() => setEditContract(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>تعديل العقد: {editContract?.contract_serial}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Same form fields as create, but for editing */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>تاريخ النهاية</Label>
                <Input 
                  type="date" 
                  value={formData.end_date}
                  onChange={e => setFormData(p => ({ ...p, end_date: e.target.value }))}
                />
              </div>
              <div>
                <Label>فترة التجربة (شهر)</Label>
                <Input 
                  type="number" 
                  value={formData.probation_months}
                  onChange={e => setFormData(p => ({ ...p, probation_months: parseInt(e.target.value) || 0 }))}
                />
              </div>
            </div>
            
            {formData.contract_category !== 'internship_unpaid' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>الراتب الأساسي</Label>
                  <Input 
                    type="number" 
                    value={formData.basic_salary}
                    onChange={e => setFormData(p => ({ ...p, basic_salary: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>بدل السكن</Label>
                  <Input 
                    type="number" 
                    value={formData.housing_allowance}
                    onChange={e => setFormData(p => ({ ...p, housing_allowance: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>بدل النقل</Label>
                  <Input 
                    type="number" 
                    value={formData.transport_allowance}
                    onChange={e => setFormData(p => ({ ...p, transport_allowance: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                <div>
                  <Label>بدلات أخرى</Label>
                  <Input 
                    type="number" 
                    value={formData.other_allowances}
                    onChange={e => setFormData(p => ({ ...p, other_allowances: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
              </div>
            )}
            
            <div>
              <Label>ملاحظات</Label>
              <Textarea 
                value={formData.notes}
                onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))}
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditContract(null)}>إلغاء</Button>
            <Button onClick={handleUpdateContract} disabled={actionLoading}>
              {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-2" /> : <Edit className="w-4 h-4 ml-2" />}
              حفظ التعديلات
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
