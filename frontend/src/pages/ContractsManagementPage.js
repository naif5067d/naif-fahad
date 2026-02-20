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
  Archive,
  RotateCcw,
  Pause
} from 'lucide-react';

const CONTRACT_STATUS = {
  draft: { label: 'مسودة', labelEn: 'Draft', color: 'bg-slate-500', icon: Edit },
  draft_correction: { label: 'مسودة تصحيح', labelEn: 'Draft Correction', color: 'bg-orange-500', icon: Edit },
  pending_stas: { label: 'في انتظار STAS', labelEn: 'Pending STAS', color: 'bg-amber-500', icon: Clock },
  active: { label: 'نشط', labelEn: 'Active', color: 'bg-emerald-500', icon: CheckCircle },
  terminated: { label: 'منتهي', labelEn: 'Terminated', color: 'bg-red-500', icon: XCircle },
  closed: { label: 'مغلق', labelEn: 'Closed', color: 'bg-gray-600', icon: Archive },
};

const CONTRACT_CATEGORIES = {
  employment: { label: 'توظيف', labelEn: 'Employment' },
  internship_unpaid: { label: 'تدريب غير مدفوع', labelEn: 'Unpaid Internship' },
  student_training: { label: 'تدريب طالب', labelEn: 'Student Training' },
};

const EMPLOYMENT_TYPES = {
  unlimited: { label: 'غير محدد المدة', labelEn: 'Unlimited' },
  fixed_term: { label: 'محدد المدة', labelEn: 'Fixed Term' },
  trial_paid: { label: 'فترة تجربة مدفوعة', labelEn: 'Paid Trial' },
  part_time: { label: 'دوام جزئي', labelEn: 'Part Time' },
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
    // هل موظف جديد أو اختيار من القائمة
    is_new_employee: true,
    employee_id: '',
    employee_code: '',
    employee_name: '',
    employee_name_ar: '',
    email: '',
    phone: '',
    national_id: '',
    contract_category: 'employment',
    employment_type: 'unlimited',
    job_title: '',
    job_title_ar: '',
    department: '',
    department_ar: '',
    start_date: '',
    end_date: '',
    // تاريخ المباشرة الفعلية - متى يبدأ احتساب الحضور
    work_start_date: '',
    // وضع التجربة - الموظف يدخل النظام لكن لا يُحتسب حضور
    sandbox_mode: false,
    probation_months: 3,
    notice_period_days: 30,
    basic_salary: 0,
    housing_allowance: 0,
    transport_allowance: 0,
    other_allowances: 0,
    wage_definition: 'basic_only',
    // الإجازة السنوية: 21 أو 30 يوم (تُحسب تلقائياً من سنوات الخدمة)
    annual_leave_days: 21,
    annual_policy_days: 21,  // السياسة الرسمية - 21 أو 30
    // رصيد الاستئذان الشهري (3 ساعات كحد أقصى)
    monthly_permission_hours: 2,
    // خيار عقد مُهاجر للموظفين القدامى
    is_migrated: false,
    leave_opening_balance: { annual: 0, sick: 0, emergency: 0 },
    leave_consumed: { annual: 0, sick: 0, emergency: 0 },
    // رصيد الساعات (الاستئذان)
    permission_hours_balance: 24,  // 2 ساعة × 12 شهر
    permission_hours_consumed: 0,
    notes: '',
    // معلومات البنك
    bank_name: '',
    bank_iban: '',
    // بدل طبيعة العمل
    nature_of_work_allowance: 0,
  });
  
  // Termination form
  const [terminationData, setTerminationData] = useState({
    termination_date: '',
    termination_reason: 'resignation',
    note: '',
  });
  
  const [actionLoading, setActionLoading] = useState(false);
  
  // صلاحيات كاملة لسلطان و STAS
  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);
  const canCreate = isAdmin;
  const canEdit = isAdmin;
  const canExecute = isAdmin;  // سلطان و STAS يستطيعون تنفيذ العقود
  const canTerminate = isAdmin;  // سلطان و STAS يستطيعون إنهاء العقود

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
    // التحقق من البيانات المطلوبة
    if (formData.is_new_employee) {
      if (!formData.employee_name_ar || !formData.start_date) {
        toast.error('يرجى إدخال اسم الموظف وتاريخ البداية');
        return;
      }
    } else {
      if (!formData.employee_id || !formData.start_date) {
        toast.error('يرجى اختيار موظف وتاريخ البداية');
        return;
      }
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

  // إعادة العقد للمسودة للتعديل الكامل
  const handleRevertToDraft = async (contractId) => {
    if (!confirm('هل تريد إعادة العقد لوضع المسودة؟ سيتمكن المسؤولون من تعديله بالكامل.')) return;
    
    try {
      await api.post(`/api/contracts-v2/${contractId}/revert-to-draft`);
      toast.success('تم إعادة العقد لوضع المسودة');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل إعادة العقد للمسودة');
    }
  };

  // تفعيل/إلغاء وضع التجربة (Sandbox)
  const handleToggleSandbox = async (contractId, currentMode) => {
    const newMode = !currentMode;
    const action = newMode ? 'تفعيل' : 'إلغاء';
    
    if (!confirm(`هل تريد ${action} وضع التجربة لهذا العقد؟`)) return;
    
    setActionLoading(true);
    try {
      const payload = {
        sandbox_mode: newMode,
        work_start_date: newMode ? null : new Date().toISOString().split('T')[0]
      };
      await api.post(`/api/contracts-v2/${contractId}/sandbox-mode`, payload);
      toast.success(`تم ${action} وضع التجربة`);
      setViewContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || `فشل ${action} وضع التجربة`);
    }
    setActionLoading(false);
  };

  // إعادة تفعيل العقد من مسودة التصحيح
  const handleReactivateContract = async (contractId) => {
    if (!confirm('هل تريد إعادة تفعيل هذا العقد؟')) return;
    
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${contractId}/reactivate`);
      toast.success('تم إعادة تفعيل العقد بنجاح');
      setViewContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل إعادة التفعيل');
    }
    setActionLoading(false);
  };

  // تحديد تاريخ المباشرة
  const handleSetWorkStartDate = async (contractId) => {
    const date = prompt('أدخل تاريخ المباشرة (YYYY-MM-DD):', new Date().toISOString().split('T')[0]);
    if (!date) return;
    
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${contractId}/set-work-start-date?work_start_date=${date}`);
      toast.success(`تم تحديد تاريخ المباشرة: ${date}`);
      setViewContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'فشل تحديد تاريخ المباشرة');
    }
    setActionLoading(false);
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
      is_new_employee: true,
      employee_id: '',
      employee_code: '',
      employee_name: '',
      employee_name_ar: '',
      email: '',
      phone: '',
      national_id: '',
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
      nature_of_work_allowance: 0,
      other_allowances: 0,
      wage_definition: 'basic_only',
      annual_leave_days: 21,
      annual_policy_days: 21,
      monthly_permission_hours: 2,
      is_migrated: false,
      leave_opening_balance: { annual: 0, sick: 0, emergency: 0, permission_hours: 0 },
      notes: '',
      bank_name: '',
      bank_iban: '',
    });
  };

  const openEditDialog = (contract) => {
    setFormData({
      is_new_employee: false,
      employee_id: contract.employee_id,
      employee_code: contract.employee_code,
      employee_name: contract.employee_name,
      employee_name_ar: contract.employee_name_ar,
      email: '',
      phone: '',
      national_id: '',
      contract_category: contract.contract_category,
      employment_type: contract.employment_type,
      job_title: contract.job_title,
      job_title_ar: contract.job_title_ar,
      department: contract.department,
      department_ar: contract.department_ar,
      start_date: contract.start_date,
      end_date: contract.end_date || '',
      // تاريخ المباشرة ووضع التجربة
      work_start_date: contract.work_start_date || contract.start_date || '',
      sandbox_mode: contract.sandbox_mode || false,
      probation_months: contract.probation_months,
      notice_period_days: contract.notice_period_days,
      basic_salary: contract.basic_salary,
      housing_allowance: contract.housing_allowance,
      transport_allowance: contract.transport_allowance,
      nature_of_work_allowance: contract.nature_of_work_allowance || 0,
      other_allowances: contract.other_allowances,
      wage_definition: contract.wage_definition,
      annual_leave_days: contract.annual_leave_days || 21,
      annual_policy_days: contract.annual_policy_days || 21,
      monthly_permission_hours: contract.monthly_permission_hours || 2,
      is_migrated: contract.is_migrated,
      // أرصدة الإجازات
      leave_opening_balance: contract.leave_opening_balance || { annual: 0, sick: 0, emergency: 0 },
      leave_consumed: contract.leave_consumed || { annual: 0, sick: 0, emergency: 0 },
      // رصيد الساعات
      permission_hours_balance: contract.permission_hours_balance || 0,
      permission_hours_consumed: contract.permission_hours_consumed || 0,
      notes: contract.notes || '',
      bank_name: contract.bank_name || '',
      bank_iban: contract.bank_iban || '',
    });
    setEditContract(contract);
  };

  // حساب سنوات الخدمة من تاريخ التعيين
  const calculateServiceYears = (startDate) => {
    if (!startDate) return { years: 0, months: 0, days: 0, totalYears: 0, policyDays: 21 };
    
    const start = new Date(startDate);
    const today = new Date();
    
    if (start > today) {
      return { years: 0, months: 0, days: 0, totalYears: 0, policyDays: 21, future: true };
    }
    
    let years = today.getFullYear() - start.getFullYear();
    let months = today.getMonth() - start.getMonth();
    let days = today.getDate() - start.getDate();
    
    if (days < 0) {
      months--;
      days += new Date(today.getFullYear(), today.getMonth(), 0).getDate();
    }
    if (months < 0) {
      years--;
      months += 12;
    }
    
    const totalYears = years + (months / 12) + (days / 365);
    const policyDays = totalYears >= 5 ? 30 : 21;
    
    return { years, months, days, totalYears: Math.round(totalYears * 100) / 100, policyDays };
  };

  // معالجة تغيير تاريخ البداية
  const handleStartDateChange = (dateValue) => {
    const serviceInfo = calculateServiceYears(dateValue);
    setFormData(p => ({ 
      ...p, 
      start_date: dateValue,
      annual_policy_days: serviceInfo.policyDays,
      annual_leave_days: serviceInfo.policyDays
    }));
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
           (contract.nature_of_work_allowance || 0) +
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
                {/* اختيار نوع الموظف: جديد أو قديم */}
                {/* بيانات الموظف الجديد - الخيار الوحيد */}
                <div className="space-y-4 p-4 border rounded-lg bg-blue-50/50">
                  <h4 className="font-medium text-sm flex items-center gap-2">
                    <Users className="w-4 h-4" /> بيانات الموظف الجديد
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>الاسم بالعربي *</Label>
                      <Input 
                        value={formData.employee_name_ar}
                        onChange={e => setFormData(p => ({ ...p, employee_name_ar: e.target.value }))}
                        placeholder="أحمد محمد"
                        dir="rtl"
                        data-testid="employee-name-ar"
                      />
                    </div>
                    <div>
                      <Label>الاسم بالإنجليزي</Label>
                      <Input 
                        value={formData.employee_name}
                        onChange={e => setFormData(p => ({ ...p, employee_name: e.target.value }))}
                        placeholder="Ahmed Mohammed"
                        dir="ltr"
                      />
                    </div>
                    <div>
                      <Label>رقم الهوية / الإقامة</Label>
                      <Input 
                        value={formData.national_id}
                        onChange={e => setFormData(p => ({ ...p, national_id: e.target.value }))}
                        placeholder="1234567890"
                      />
                    </div>
                    <div>
                      <Label>البريد الإلكتروني</Label>
                      <Input 
                        type="email"
                        value={formData.email}
                        onChange={e => setFormData(p => ({ ...p, email: e.target.value }))}
                        placeholder="ahmed@company.com"
                      />
                    </div>
                    <div>
                      <Label>رقم الجوال</Label>
                      <Input 
                        value={formData.phone}
                        onChange={e => setFormData(p => ({ ...p, phone: e.target.value }))}
                        placeholder="05xxxxxxxx"
                      />
                    </div>
                    <div>
                      <Label>الرقم الوظيفي</Label>
                      <Input 
                        value={formData.employee_code}
                        onChange={e => setFormData(p => ({ ...p, employee_code: e.target.value }))}
                        placeholder="EMP-001"
                      />
                    </div>
                  </div>
                </div>
                
                {/* المسمى الوظيفي والقسم */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>المسمى الوظيفي (عربي)</Label>
                    <Input 
                      value={formData.job_title_ar}
                      onChange={e => setFormData(p => ({ ...p, job_title_ar: e.target.value }))}
                      placeholder="مهندس برمجيات"
                      dir="rtl"
                    />
                  </div>
                  <div>
                    <Label>المسمى الوظيفي (إنجليزي)</Label>
                    <Input 
                      value={formData.job_title}
                      onChange={e => setFormData(p => ({ ...p, job_title: e.target.value }))}
                      placeholder="Software Engineer"
                    />
                  </div>
                  <div>
                    <Label>القسم (عربي)</Label>
                    <Input 
                      value={formData.department_ar}
                      onChange={e => setFormData(p => ({ ...p, department_ar: e.target.value }))}
                      placeholder="تقنية المعلومات"
                      dir="rtl"
                    />
                  </div>
                  <div>
                    <Label>القسم (إنجليزي)</Label>
                    <Input 
                      value={formData.department}
                      onChange={e => setFormData(p => ({ ...p, department: e.target.value }))}
                      placeholder="IT"
                    />
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
                {/* تاريخ البداية مع حساب سنوات الخدمة */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>تاريخ التعيين / البداية *</Label>
                    <Input 
                      type="date" 
                      value={formData.start_date}
                      onChange={e => handleStartDateChange(e.target.value)}
                      data-testid="start-date-input"
                    />
                    {/* عرض سنوات الخدمة */}
                    {formData.start_date && (
                      <div className="mt-2 p-2 bg-primary/10 rounded-lg">
                        {(() => {
                          const info = calculateServiceYears(formData.start_date);
                          if (info.future) {
                            return (
                              <p className="text-sm text-amber-600">
                                ⏳ تاريخ مستقبلي - لم تبدأ الخدمة بعد
                              </p>
                            );
                          }
                          return (
                            <>
                              <p className="text-sm font-bold text-primary">
                                📅 مدة الخدمة: {info.years} سنة و {info.months} شهر
                              </p>
                              <p className="text-xs text-muted-foreground mt-1">
                                إجمالي: {info.totalYears} سنة → 
                                <span className={`font-bold mr-1 ${info.policyDays === 30 ? 'text-emerald-600' : 'text-blue-600'}`}>
                                  {info.policyDays} يوم إجازة سنوية
                                </span>
                              </p>
                            </>
                          );
                        })()}
                      </div>
                    )}
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
                
                {/* تاريخ المباشرة ووضع التجربة */}
                <div className="grid grid-cols-2 gap-4 p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800">
                  <div>
                    <Label className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-amber-600" />
                      تاريخ المباشرة الفعلية
                    </Label>
                    <Input 
                      type="date" 
                      value={formData.work_start_date}
                      onChange={e => setFormData(p => ({ ...p, work_start_date: e.target.value }))}
                      placeholder="إذا فارغ = تاريخ البداية"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      قبل هذا التاريخ لا يُحتسب حضور أو غياب
                    </p>
                  </div>
                  <div className="flex flex-col justify-center">
                    <Label className="flex items-center gap-2 mb-2">
                      وضع التجربة (Sandbox)
                    </Label>
                    <div className="flex items-center gap-3">
                      <Switch
                        checked={formData.sandbox_mode}
                        onCheckedChange={checked => setFormData(p => ({ ...p, sandbox_mode: checked }))}
                      />
                      <span className="text-sm text-muted-foreground">
                        {formData.sandbox_mode ? 'مفعّل - لا يُحتسب حضور' : 'غير مفعّل'}
                      </span>
                    </div>
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
                {formData.contract_category !== 'internship_unpaid' && formData.contract_category !== 'student_training' && (
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
                      <div>
                        <Label>بدل طبيعة العمل</Label>
                        <Input 
                          type="number" 
                          value={formData.nature_of_work_allowance}
                          onChange={e => setFormData(p => ({ ...p, nature_of_work_allowance: parseFloat(e.target.value) || 0 }))}
                        />
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                      إجمالي الراتب: <span className="font-bold">{formatCurrency(
                        formData.basic_salary + formData.housing_allowance + formData.transport_allowance + formData.nature_of_work_allowance + formData.other_allowances
                      )}</span>
                    </div>
                  </>
                )}
                
                {/* معلومات البنك - إلزامية */}
                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Building2 className="w-4 h-4" /> معلومات البنك
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>اسم البنك *</Label>
                      <Input 
                        value={formData.bank_name}
                        onChange={e => setFormData(p => ({ ...p, bank_name: e.target.value }))}
                        placeholder="مثال: الراجحي، الأهلي"
                        dir="rtl"
                        data-testid="bank-name-input"
                      />
                    </div>
                    <div>
                      <Label>رقم الآيبان (IBAN) *</Label>
                      <Input 
                        value={formData.bank_iban}
                        onChange={e => setFormData(p => ({ ...p, bank_iban: e.target.value }))}
                        placeholder="SA..."
                        dir="ltr"
                        data-testid="bank-iban-input"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    معلومات البنك مطلوبة للمخالصة - يمكن تعديلها في أي وقت
                  </p>
                </div>
                
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
                
                {/* الإجازة السنوية - سياسة 21 أو 30 يوم */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>سياسة الإجازة السنوية *</Label>
                    <Select 
                      value={String(formData.annual_policy_days || formData.annual_leave_days || 21)} 
                      onValueChange={v => setFormData(p => ({ 
                        ...p, 
                        annual_policy_days: parseInt(v),
                        annual_leave_days: parseInt(v)  // للتوافق مع الكود القديم
                      }))}
                    >
                      <SelectTrigger data-testid="annual-policy-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="21">21 يوم (الافتراضي)</SelectItem>
                        <SelectItem value="30">30 يوم (بقرار إداري)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">
                      يُحسب الرصيد بنظام Pro-Rata (تدريجي يومي)
                    </p>
                  </div>
                  <div>
                    <Label>رصيد الاستئذان الشهري (ساعات)</Label>
                    <Select 
                      value={String(formData.monthly_permission_hours)} 
                      onValueChange={v => setFormData(p => ({ ...p, monthly_permission_hours: parseInt(v) }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">0 ساعات</SelectItem>
                        <SelectItem value="1">1 ساعة</SelectItem>
                        <SelectItem value="2">2 ساعات (افتراضي)</SelectItem>
                        <SelectItem value="3">3 ساعات (الحد الأقصى)</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">الحد الأقصى 3 ساعات شهرياً</p>
                  </div>
                </div>
                
                {formData.is_migrated && (
                  <div className="space-y-3 bg-amber-50 p-4 rounded-lg border border-amber-200">
                    <h4 className="font-medium text-sm text-amber-800">أرصدة افتتاحية (للموظف المُهاجر)</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label className="text-xs">رصيد الإجازة السنوية (بالكسور)</Label>
                        <Input 
                          type="number" 
                          step="0.5"
                          value={formData.leave_opening_balance.annual}
                          onChange={e => setFormData(p => ({ 
                            ...p, 
                            leave_opening_balance: { ...p.leave_opening_balance, annual: parseFloat(e.target.value) || 0 }
                          }))}
                          placeholder="مثال: 15.5"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">رصيد الاستئذان المتبقي (ساعات)</Label>
                        <Input 
                          type="number" 
                          step="0.5"
                          max="3"
                          value={formData.leave_opening_balance.permission_hours || 0}
                          onChange={e => setFormData(p => ({ 
                            ...p, 
                            leave_opening_balance: { ...p.leave_opening_balance, permission_hours: parseFloat(e.target.value) || 0 }
                          }))}
                          placeholder="0-3"
                        />
                      </div>
                      <div>
                        <Label className="text-xs">رصيد الإجازة المرضية</Label>
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
                        <Label className="text-xs">رصيد الطوارئ</Label>
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
                    
                    {/* الأرصدة المستهلكة - للتعديل الكامل */}
                    <h4 className="font-medium text-sm text-amber-800 mt-4">الأرصدة المستهلكة (للتصحيح)</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <Label className="text-xs">سنوية مستهلكة</Label>
                        <Input 
                          type="number" 
                          step="0.5"
                          value={formData.leave_consumed?.annual || 0}
                          onChange={e => setFormData(p => ({ 
                            ...p, 
                            leave_consumed: { ...p.leave_consumed, annual: parseFloat(e.target.value) || 0 }
                          }))}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">مرضية مستهلكة</Label>
                        <Input 
                          type="number" 
                          value={formData.leave_consumed?.sick || 0}
                          onChange={e => setFormData(p => ({ 
                            ...p, 
                            leave_consumed: { ...p.leave_consumed, sick: parseInt(e.target.value) || 0 }
                          }))}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">ساعات استئذان مستهلكة</Label>
                        <Input 
                          type="number" 
                          step="0.5"
                          value={formData.permission_hours_consumed || 0}
                          onChange={e => setFormData(p => ({ 
                            ...p, 
                            permission_hours_consumed: parseFloat(e.target.value) || 0
                          }))}
                        />
                      </div>
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
                placeholder="بحث: رقم العقد (001) أو رقم الموظف (40) أو الاسم (مؤمن)..."
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
                        
                        {/* Edit - للمسؤولين (سلطان/نايف/STAS) يمكنهم تعديل أي عقد */}
                        {isAdmin && (
                          <Button variant="ghost" size="sm" onClick={() => openEditDialog(contract)} data-testid={`edit-contract-${contract.id}`}>
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* إعادة للمسودة - للسماح بالتعديل الكامل */}
                        {['pending_stas', 'active'].includes(contract.status) && ['stas', 'sultan'].includes(user?.role) && (
                          <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={() => handleRevertToDraft(contract.id)}
                            className="text-blue-600 border-blue-300 hover:bg-blue-50"
                            data-testid={`revert-draft-${contract.id}`}
                          >
                            <RotateCcw className="w-4 h-4 ml-1" />
                            إعادة للمسودة
                          </Button>
                        )}
                        
                        {/* Submit to STAS - only draft */}
                        {contract.status === 'draft' && isAdmin && (
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
                        
                        {/* Execute - للمسؤولين فقط عند انتظار STAS */}
                        {contract.status === 'pending_stas' && isAdmin && (
                          <Button 
                            variant="default" 
                            size="sm" 
                            onClick={() => handleExecuteContract(contract.id)}
                            className="bg-emerald-600 hover:bg-emerald-700"
                            data-testid={`execute-contract-${contract.id}`}
                          >
                            <Play className="w-4 h-4 ml-1" />
                            تنفيذ
                          </Button>
                        )}
                        
                        {/* Terminate - للمسؤولين فقط للعقود النشطة */}
                        {contract.status === 'active' && isAdmin && (
                          <Button 
                            variant="destructive" 
                            size="sm" 
                            onClick={() => setTerminateContract(contract)}
                            data-testid={`terminate-contract-${contract.id}`}
                          >
                            <Ban className="w-4 h-4 ml-1" />
                            إنهاء
                          </Button>
                        )}
                        
                        {/* Delete - للمسؤولين فقط للمسودات */}
                        {['draft', 'pending_stas'].includes(contract.status) && isAdmin && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            onClick={() => handleDeleteContract(contract.id)}
                            data-testid={`delete-contract-${contract.id}`}
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
                    <span className="text-muted-foreground">تاريخ المباشرة:</span>
                    <span>{viewContract.work_start_date ? formatDate(viewContract.work_start_date) : formatDate(viewContract.start_date)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">تاريخ النهاية:</span>
                    <span>{viewContract.end_date ? formatDate(viewContract.end_date) : 'غير محدد'}</span>
                  </div>
                  {/* وضع التجربة */}
                  <div className="flex justify-between items-center py-1 border-t border-b">
                    <span className="text-muted-foreground">وضع التجربة:</span>
                    <Badge variant={viewContract.sandbox_mode ? "destructive" : "secondary"}>
                      {viewContract.sandbox_mode ? 'مفعّل - لا يُحتسب حضور' : 'غير مفعّل'}
                    </Badge>
                  </div>
                  {/* سنوات الخدمة */}
                  {viewContract.service_years !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">سنوات الخدمة:</span>
                      <span className="font-bold text-primary">{viewContract.service_years?.toFixed(1)} سنة</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">فترة التجربة:</span>
                    <span>{viewContract.probation_months} شهر</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">فترة الإنذار:</span>
                    <span>{viewContract.notice_period_days} يوم</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">سياسة الإجازة السنوية:</span>
                    <span className="font-bold text-primary">{viewContract.annual_policy_days || viewContract.annual_leave_days || 21} يوم</span>
                  </div>
                </CardContent>
              </Card>
              
              {/* أرصدة الإجازات */}
              <Card className="border-emerald-200 bg-emerald-50/50">
                <CardHeader className="py-3">
                  <CardTitle className="text-sm flex items-center gap-2 text-emerald-700">
                    <Calendar className="w-4 h-4" /> أرصدة الإجازات والساعات
                  </CardTitle>
                </CardHeader>
                <CardContent className="py-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">الإجازة السنوية (افتتاحي):</span>
                    <span>{viewContract.leave_opening_balance?.annual || 0} يوم</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">الإجازة السنوية (مستهلك):</span>
                    <span className="text-red-600">{viewContract.leave_consumed?.annual || 0} يوم</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">الإجازة المرضية (مستهلك):</span>
                    <span className="text-red-600">{viewContract.leave_consumed?.sick || 0} يوم</span>
                  </div>
                  <div className="flex justify-between border-t pt-1">
                    <span className="text-muted-foreground">ساعات الاستئذان (رصيد):</span>
                    <span className="font-bold">{viewContract.permission_hours_balance || 0} ساعة</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ساعات الاستئذان (مستهلك):</span>
                    <span className="text-red-600">{viewContract.permission_hours_consumed || 0} ساعة</span>
                  </div>
                </CardContent>
              </Card>
              
              {/* Salary (if applicable) */}
              {viewContract.contract_category !== 'internship_unpaid' && viewContract.contract_category !== 'student_training' && (
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
          
          <DialogFooter className="flex-col sm:flex-row gap-2">
            {/* أزرار التحكم في وضع التجربة والتفعيل */}
            <div className="flex flex-wrap gap-2">
              {/* زر تفعيل/إلغاء وضع التجربة */}
              {viewContract?.status === 'active' && (
                <Button 
                  variant={viewContract.sandbox_mode ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleToggleSandbox(viewContract.id, viewContract.sandbox_mode)}
                  disabled={actionLoading}
                  className={viewContract.sandbox_mode ? "bg-amber-600 hover:bg-amber-700" : ""}
                >
                  {viewContract.sandbox_mode ? (
                    <>
                      <Play className="w-4 h-4 ml-1" /> بدء العمل الرسمي
                    </>
                  ) : (
                    <>
                      <Pause className="w-4 h-4 ml-1" /> تفعيل وضع التجربة
                    </>
                  )}
                </Button>
              )}
              
              {/* زر تحديد تاريخ المباشرة */}
              {viewContract?.status === 'active' && (
                <Button 
                  variant="outline"
                  size="sm"
                  onClick={() => handleSetWorkStartDate(viewContract.id)}
                  disabled={actionLoading}
                >
                  <Calendar className="w-4 h-4 ml-1" /> تاريخ المباشرة
                </Button>
              )}
              
              {/* زر إعادة تفعيل من مسودة التصحيح */}
              {viewContract?.status === 'draft_correction' && (
                <Button 
                  variant="default"
                  size="sm"
                  onClick={() => handleReactivateContract(viewContract.id)}
                  disabled={actionLoading}
                  className="bg-emerald-600 hover:bg-emerald-700"
                >
                  {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin ml-1" /> : <CheckCircle className="w-4 h-4 ml-1" />}
                  إعادة التفعيل
                </Button>
              )}
            </div>
            
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => handlePreviewPDF(viewContract?.id)}>
                <FileText className="w-4 h-4 ml-2" /> عرض PDF
              </Button>
              <Button variant="outline" onClick={() => setViewContract(null)}>إغلاق</Button>
            </div>
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

      {/* Edit Contract Dialog - تعديل شامل للعقد */}
      <Dialog open={!!editContract} onOpenChange={() => setEditContract(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>تعديل العقد: {editContract?.contract_serial}</DialogTitle>
            <DialogDescription>
              {editContract?.status === 'active' ? 'تعديل عقد نشط - سيتم حفظ التغييرات فوراً' : 'تعديل مسودة العقد'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* معلومات الموظف - للقراءة فقط إذا كان نشط */}
            <div className="p-4 bg-muted/40 rounded-lg">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" />
                بيانات الموظف
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label>كود الموظف</Label>
                  <Input 
                    value={formData.employee_code} 
                    onChange={e => setFormData(p => ({ ...p, employee_code: e.target.value }))}
                    className={['stas', 'sultan'].includes(user?.role) ? '' : 'bg-muted'}
                    disabled={!['stas', 'sultan'].includes(user?.role)}
                  />
                </div>
                <div>
                  <Label>الاسم بالعربي</Label>
                  <Input 
                    value={formData.employee_name_ar} 
                    onChange={e => setFormData(p => ({ ...p, employee_name_ar: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>الاسم بالإنجليزي</Label>
                  <Input 
                    value={formData.employee_name} 
                    onChange={e => setFormData(p => ({ ...p, employee_name: e.target.value }))}
                  />
                </div>
              </div>
            </div>

            {/* معلومات الوظيفة */}
            <div className="p-4 bg-muted/40 rounded-lg">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                معلومات الوظيفة
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>المسمى الوظيفي (عربي)</Label>
                  <Input 
                    value={formData.job_title_ar} 
                    onChange={e => setFormData(p => ({ ...p, job_title_ar: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>المسمى الوظيفي (إنجليزي)</Label>
                  <Input 
                    value={formData.job_title} 
                    onChange={e => setFormData(p => ({ ...p, job_title: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>القسم (عربي)</Label>
                  <Input 
                    value={formData.department_ar} 
                    onChange={e => setFormData(p => ({ ...p, department_ar: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>القسم (إنجليزي)</Label>
                  <Input 
                    value={formData.department} 
                    onChange={e => setFormData(p => ({ ...p, department: e.target.value }))}
                  />
                </div>
              </div>
            </div>

            {/* تواريخ العقد */}
            <div className="p-4 bg-muted/40 rounded-lg">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                فترة العقد
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <Label>تاريخ التعيين / البداية</Label>
                  <Input 
                    type="date" 
                    value={formData.start_date}
                    onChange={e => handleStartDateChange(e.target.value)}
                  />
                  {/* عرض سنوات الخدمة */}
                  {formData.start_date && (
                    <div className="mt-2 p-2 bg-primary/10 rounded text-xs">
                      {(() => {
                        const info = calculateServiceYears(formData.start_date);
                        if (info.future) return <span className="text-amber-600">⏳ مستقبلي</span>;
                        return (
                          <span className="font-bold text-primary">
                            {info.years} سنة → {info.policyDays} يوم
                          </span>
                        );
                      })()}
                    </div>
                  )}
                </div>
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
                <div>
                  <Label>فترة الإشعار (يوم)</Label>
                  <Input 
                    type="number" 
                    value={formData.notice_period_days}
                    onChange={e => setFormData(p => ({ ...p, notice_period_days: parseInt(e.target.value) || 30 }))}
                  />
                </div>
              </div>
            </div>

            {/* المالية */}
            {formData.contract_category !== 'internship_unpaid' && (
              <div className="p-4 bg-muted/40 rounded-lg">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <DollarSign className="w-4 h-4" />
                  البيانات المالية
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                    <Label>بدل طبيعة العمل</Label>
                    <Input 
                      type="number" 
                      value={formData.nature_of_work_allowance}
                      onChange={e => setFormData(p => ({ ...p, nature_of_work_allowance: parseFloat(e.target.value) || 0 }))}
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
                <div className="mt-3 p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded text-sm">
                  <span className="font-semibold">إجمالي الراتب: </span>
                  {((formData.basic_salary || 0) + (formData.housing_allowance || 0) + (formData.transport_allowance || 0) + (formData.nature_of_work_allowance || 0) + (formData.other_allowances || 0)).toLocaleString()} ريال
                </div>
              </div>
            )}

            {/* معلومات البنك - قابلة للتعديل دائماً */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-blue-700 dark:text-blue-300">
                <Building2 className="w-4 h-4" />
                معلومات البنك (للمخالصة)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>اسم البنك *</Label>
                  <Input 
                    value={formData.bank_name}
                    onChange={e => setFormData(p => ({ ...p, bank_name: e.target.value }))}
                    placeholder="مثال: الراجحي، الأهلي"
                    dir="rtl"
                    data-testid="edit-bank-name-input"
                  />
                </div>
                <div>
                  <Label>رقم الآيبان (IBAN) *</Label>
                  <Input 
                    value={formData.bank_iban}
                    onChange={e => setFormData(p => ({ ...p, bank_iban: e.target.value }))}
                    placeholder="SA..."
                    dir="ltr"
                    data-testid="edit-bank-iban-input"
                  />
                </div>
              </div>
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                ⚠️ معلومات البنك مطلوبة للمخالصة - يمكن تعديلها في أي وقت حتى للعقود النشطة
              </p>
            </div>

            {/* سياسات الإجازات */}
            <div className="p-4 bg-muted/40 rounded-lg">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                سياسات الإجازات
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label>أيام الإجازة السنوية</Label>
                  <Select 
                    value={String(formData.annual_policy_days || 21)}
                    onValueChange={v => setFormData(p => ({ ...p, annual_policy_days: parseInt(v), annual_leave_days: parseInt(v) }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="21">21 يوم (أقل من 5 سنوات)</SelectItem>
                      <SelectItem value="30">30 يوم (5 سنوات فأكثر)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>ساعات الاستئذان الشهرية</Label>
                  <Input 
                    type="number" 
                    value={formData.monthly_permission_hours || 2}
                    onChange={e => setFormData(p => ({ ...p, monthly_permission_hours: parseInt(e.target.value) || 2 }))}
                    max={3}
                    min={0}
                  />
                </div>
                <div>
                  <Label>نوع احتساب الأجر</Label>
                  <Select 
                    value={formData.wage_definition || 'basic_only'}
                    onValueChange={v => setFormData(p => ({ ...p, wage_definition: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="basic_only">الراتب الأساسي فقط</SelectItem>
                      <SelectItem value="basic_housing">الأساسي + السكن</SelectItem>
                      <SelectItem value="total">إجمالي الراتب</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* أرصدة الإجازات والساعات - تعديل كامل */}
            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                <Calendar className="w-4 h-4" />
                أرصدة الإجازات والساعات (تعديل مباشر)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <Label className="text-xs">رصيد سنوية (افتتاحي)</Label>
                  <Input 
                    type="number"
                    step="0.5"
                    value={formData.leave_opening_balance?.annual || 0}
                    onChange={e => setFormData(p => ({ 
                      ...p, 
                      leave_opening_balance: { 
                        ...(p.leave_opening_balance || {}), 
                        annual: parseFloat(e.target.value) || 0 
                      }
                    }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">سنوية مستهلكة</Label>
                  <Input 
                    type="number"
                    step="0.5"
                    value={formData.leave_consumed?.annual || 0}
                    onChange={e => setFormData(p => ({ 
                      ...p, 
                      leave_consumed: { 
                        ...(p.leave_consumed || {}), 
                        annual: parseFloat(e.target.value) || 0 
                      }
                    }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">رصيد مرضية (افتتاحي)</Label>
                  <Input 
                    type="number"
                    value={formData.leave_opening_balance?.sick || 0}
                    onChange={e => setFormData(p => ({ 
                      ...p, 
                      leave_opening_balance: { 
                        ...(p.leave_opening_balance || {}), 
                        sick: parseInt(e.target.value) || 0 
                      }
                    }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">مرضية مستهلكة</Label>
                  <Input 
                    type="number"
                    value={formData.leave_consumed?.sick || 0}
                    onChange={e => setFormData(p => ({ 
                      ...p, 
                      leave_consumed: { 
                        ...(p.leave_consumed || {}), 
                        sick: parseInt(e.target.value) || 0 
                      }
                    }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">رصيد ساعات الاستئذان</Label>
                  <Input 
                    type="number"
                    step="0.5"
                    value={formData.permission_hours_balance || 0}
                    onChange={e => setFormData(p => ({ 
                      ...p, 
                      permission_hours_balance: parseFloat(e.target.value) || 0 
                    }))}
                  />
                </div>
                <div>
                  <Label className="text-xs">ساعات مستهلكة</Label>
                  <Input 
                    type="number"
                    step="0.5"
                    value={formData.permission_hours_consumed || 0}
                    onChange={e => setFormData(p => ({ 
                      ...p, 
                      permission_hours_consumed: parseFloat(e.target.value) || 0 
                    }))}
                  />
                </div>
              </div>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2">
                ⚠️ هذه الأرصدة تُعدّل مباشرة على العقد - استخدم بحذر
              </p>
            </div>

            {/* تاريخ المباشرة ووضع التجربة */}
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
              <h3 className="font-semibold mb-3 flex items-center gap-2 text-amber-700 dark:text-amber-300">
                <Clock className="w-4 h-4" />
                تاريخ المباشرة ووضع التجربة
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>تاريخ المباشرة الفعلية</Label>
                  <Input 
                    type="date"
                    value={formData.work_start_date || formData.start_date || ''}
                    onChange={e => setFormData(p => ({ ...p, work_start_date: e.target.value }))}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    قبل هذا التاريخ لا يُحتسب حضور أو غياب
                  </p>
                </div>
                <div className="flex flex-col justify-center">
                  <Label className="mb-2">وضع التجربة (Sandbox)</Label>
                  <div className="flex items-center gap-3">
                    <Switch
                      checked={formData.sandbox_mode || false}
                      onCheckedChange={checked => setFormData(p => ({ ...p, sandbox_mode: checked }))}
                    />
                    <span className="text-sm">
                      {formData.sandbox_mode ? (
                        <Badge variant="destructive">مفعّل - لا يُحتسب حضور</Badge>
                      ) : (
                        <Badge variant="secondary">غير مفعّل</Badge>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* ملاحظات */}
            <div>
              <Label>ملاحظات</Label>
              <Textarea 
                value={formData.notes}
                onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))}
                rows={3}
                placeholder="أي ملاحظات إضافية على العقد..."
              />
            </div>
          </div>
          
          <DialogFooter className="gap-2">
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
