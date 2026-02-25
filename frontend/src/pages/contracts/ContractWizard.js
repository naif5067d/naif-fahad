import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import api from '@/lib/api';
import { 
  ChevronLeft, ChevronRight, User, Briefcase, DollarSign, Calendar,
  Building2, CheckCircle, AlertTriangle, Clock
} from 'lucide-react';
import {
  CONTRACT_CATEGORIES, EMPLOYMENT_TYPES, DEFAULT_CONTRACT_DATA,
  calculateServiceYears, formatCurrency, generateRefNo
} from './contractConstants';

const WIZARD_STEPS = [
  { id: 1, title: 'بيانات الموظف', titleEn: 'Employee Info', icon: User },
  { id: 2, title: 'الوظيفة والتواريخ', titleEn: 'Job & Dates', icon: Briefcase },
  { id: 3, title: 'الراتب والبنك', titleEn: 'Salary & Bank', icon: DollarSign },
  { id: 4, title: 'الإجازات والملاحظات', titleEn: 'Leave & Notes', icon: Calendar },
];

export default function ContractWizard({ 
  isOpen, 
  onClose, 
  editContract = null, 
  employees = [],
  onSuccess 
}) {
  const { lang } = useLanguage();
  const isRTL = lang === 'ar';
  
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState(DEFAULT_CONTRACT_DATA);
  
  // تهيئة البيانات عند فتح النموذج
  useEffect(() => {
    if (editContract) {
      setFormData({ ...DEFAULT_CONTRACT_DATA, ...editContract });
    } else {
      setFormData({ ...DEFAULT_CONTRACT_DATA, ref_no: generateRefNo() });
    }
    setStep(1);
  }, [editContract, isOpen]);

  // الموظفون بدون عقد نشط
  const availableEmployees = employees.filter(e => 
    !e.has_active_contract || (editContract && editContract.employee_id === e.id)
  );

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleStartDateChange = (value) => {
    setFormData(prev => {
      const info = calculateServiceYears(value);
      return {
        ...prev,
        start_date: value,
        annual_policy_days: info?.policyDays || 21
      };
    });
  };

  const nextStep = () => {
    // التحقق من البيانات المطلوبة
    if (step === 1) {
      if (formData.is_new_employee) {
        if (!formData.employee_name_ar) {
          toast.error(isRTL ? 'يرجى إدخال اسم الموظف' : 'Please enter employee name');
          return;
        }
      } else {
        if (!formData.employee_id) {
          toast.error(isRTL ? 'يرجى اختيار الموظف' : 'Please select employee');
          return;
        }
      }
    }
    if (step === 2 && !formData.start_date) {
      toast.error(isRTL ? 'يرجى إدخال تاريخ البداية' : 'Please enter start date');
      return;
    }
    if (step === 3 && formData.contract_category === 'employment') {
      if (!formData.bank_name || !formData.bank_iban) {
        toast.error(isRTL ? 'يرجى إدخال بيانات البنك' : 'Please enter bank details');
        return;
      }
    }
    
    if (step < 4) setStep(step + 1);
  };

  const prevStep = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      if (editContract) {
        await api.patch(`/api/contracts-v2/${editContract.id}`, formData);
        toast.success(isRTL ? 'تم تحديث العقد بنجاح' : 'Contract updated successfully');
      } else {
        await api.post('/api/contracts-v2', formData);
        toast.success(isRTL ? 'تم إنشاء العقد بنجاح' : 'Contract created successfully');
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const totalSalary = (formData.basic_salary || 0) + (formData.housing_allowance || 0) + 
    (formData.transport_allowance || 0) + (formData.nature_of_work_allowance || 0) + 
    (formData.other_allowances || 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div 
        className="bg-background rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        {/* Header */}
        <div className="bg-primary text-primary-foreground p-5">
          <h2 className="text-xl font-bold">
            {editContract 
              ? (isRTL ? 'تعديل العقد' : 'Edit Contract')
              : (isRTL ? 'عقد جديد' : 'New Contract')
            }
          </h2>
          
          {/* Progress Steps */}
          <div className="flex items-center justify-between mt-4">
            {WIZARD_STEPS.map((s, i) => {
              const Icon = s.icon;
              const isActive = step === s.id;
              const isComplete = step > s.id;
              return (
                <div key={s.id} className="flex items-center">
                  <div className={`
                    flex items-center justify-center w-10 h-10 rounded-full transition-all
                    ${isActive ? 'bg-white text-primary' : isComplete ? 'bg-white/30 text-white' : 'bg-white/10 text-white/50'}
                  `}>
                    {isComplete ? <CheckCircle size={20} /> : <Icon size={20} />}
                  </div>
                  <span className={`hidden md:block mx-2 text-sm ${isActive ? 'text-white font-bold' : 'text-white/70'}`}>
                    {isRTL ? s.title : s.titleEn}
                  </span>
                  {i < WIZARD_STEPS.length - 1 && (
                    <div className={`w-8 h-0.5 ${isComplete ? 'bg-white/50' : 'bg-white/20'}`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {/* الخطوة 1: بيانات الموظف */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex gap-4 p-3 bg-muted/50 rounded-lg">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    checked={formData.is_new_employee}
                    onChange={() => handleChange('is_new_employee', true)}
                  />
                  <span>{isRTL ? 'موظف جديد' : 'New Employee'}</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    checked={!formData.is_new_employee}
                    onChange={() => handleChange('is_new_employee', false)}
                  />
                  <span>{isRTL ? 'موظف موجود' : 'Existing Employee'}</span>
                </label>
              </div>

              {formData.is_new_employee ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <Label>{isRTL ? 'الاسم الكامل (عربي) *' : 'Full Name (Arabic) *'}</Label>
                    <Input 
                      value={formData.employee_name_ar}
                      onChange={e => handleChange('employee_name_ar', e.target.value)}
                      dir="rtl"
                      placeholder="محمد أحمد"
                    />
                  </div>
                  <div className="col-span-2">
                    <Label>{isRTL ? 'الاسم الكامل (إنجليزي)' : 'Full Name (English)'}</Label>
                    <Input 
                      value={formData.employee_name}
                      onChange={e => handleChange('employee_name', e.target.value)}
                      placeholder="Mohammed Ahmed"
                    />
                  </div>
                  <div>
                    <Label>{isRTL ? 'البريد الإلكتروني' : 'Email'}</Label>
                    <Input 
                      type="email"
                      value={formData.email}
                      onChange={e => handleChange('email', e.target.value)}
                      placeholder="email@company.com"
                    />
                  </div>
                  <div>
                    <Label>{isRTL ? 'رقم الجوال' : 'Phone'}</Label>
                    <Input 
                      value={formData.phone}
                      onChange={e => handleChange('phone', e.target.value)}
                      placeholder="05xxxxxxxx"
                    />
                  </div>
                  <div>
                    <Label>{isRTL ? 'الجنسية' : 'Nationality'}</Label>
                    <div className="flex gap-3 mt-1">
                      <label className="flex items-center gap-2">
                        <input 
                          type="radio" 
                          checked={formData.is_saudi === true}
                          onChange={() => handleChange('is_saudi', true)}
                        />
                        <span className={formData.is_saudi === true ? 'font-bold text-green-600' : ''}>{isRTL ? 'سعودي' : 'Saudi'}</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input 
                          type="radio" 
                          checked={formData.is_saudi === false}
                          onChange={() => handleChange('is_saudi', false)}
                        />
                        <span className={formData.is_saudi === false ? 'font-bold text-blue-600' : ''}>{isRTL ? 'أجنبي' : 'Non-Saudi'}</span>
                      </label>
                    </div>
                  </div>
                  
                  {/* بيانات الهوية للسعودي */}
                  {formData.is_saudi === true && (
                    <div>
                      <Label>{isRTL ? 'رقم الهوية الوطنية' : 'National ID'}</Label>
                      <Input 
                        value={formData.national_id || ''}
                        onChange={e => handleChange('national_id', e.target.value)}
                        placeholder="10xxxxxxxx"
                        dir="ltr"
                      />
                    </div>
                  )}
                  
                  {/* بيانات الإقامة للأجنبي */}
                  {formData.is_saudi === false && (
                    <>
                      <div>
                        <Label>{isRTL ? 'الجنسية' : 'Nationality'}</Label>
                        <Input 
                          value={formData.nationality || ''}
                          onChange={e => handleChange('nationality', e.target.value)}
                          placeholder={isRTL ? 'مثال: مصري، هندي' : 'e.g. Egyptian, Indian'}
                        />
                      </div>
                      <div>
                        <Label>{isRTL ? 'رقم الإقامة' : 'Iqama Number'}</Label>
                        <Input 
                          value={formData.iqama_number || ''}
                          onChange={e => handleChange('iqama_number', e.target.value)}
                          placeholder="2xxxxxxxxx"
                          dir="ltr"
                        />
                      </div>
                      <div>
                        <Label>{isRTL ? 'تاريخ انتهاء الإقامة *' : 'Iqama Expiry Date *'}</Label>
                        <Input 
                          type="date"
                          value={formData.iqama_expiry_date || ''}
                          onChange={e => handleChange('iqama_expiry_date', e.target.value)}
                        />
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div>
                  <Label>{isRTL ? 'اختر الموظف *' : 'Select Employee *'}</Label>
                  <Select value={formData.employee_id} onValueChange={v => {
                    const emp = employees.find(e => e.id === v);
                    handleChange('employee_id', v);
                    if (emp) {
                      handleChange('employee_name', emp.full_name);
                      handleChange('employee_name_ar', emp.full_name_ar);
                    }
                  }}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder={isRTL ? 'اختر...' : 'Select...'} />
                    </SelectTrigger>
                    <SelectContent>
                      {availableEmployees.map(emp => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {isRTL ? emp.full_name_ar : emp.full_name} ({emp.employee_number})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          {/* الخطوة 2: الوظيفة والتواريخ */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{isRTL ? 'فئة العقد' : 'Contract Category'}</Label>
                  <Select value={formData.contract_category} onValueChange={v => handleChange('contract_category', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(CONTRACT_CATEGORIES).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{isRTL ? v.label : v.labelEn}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{isRTL ? 'نوع العقد' : 'Employment Type'}</Label>
                  <Select value={formData.employment_type} onValueChange={v => handleChange('employment_type', v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(EMPLOYMENT_TYPES).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{isRTL ? v.label : v.labelEn}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{isRTL ? 'المسمى الوظيفي (عربي)' : 'Job Title (AR)'}</Label>
                  <Input 
                    value={formData.job_title_ar}
                    onChange={e => handleChange('job_title_ar', e.target.value)}
                    dir="rtl"
                    placeholder="مهندس برمجيات"
                  />
                </div>
                <div>
                  <Label>{isRTL ? 'المسمى الوظيفي (إنجليزي)' : 'Job Title (EN)'}</Label>
                  <Input 
                    value={formData.job_title}
                    onChange={e => handleChange('job_title', e.target.value)}
                    placeholder="Software Engineer"
                  />
                </div>
                <div>
                  <Label>{isRTL ? 'القسم (عربي)' : 'Department (AR)'}</Label>
                  <Input 
                    value={formData.department_ar}
                    onChange={e => handleChange('department_ar', e.target.value)}
                    dir="rtl"
                    placeholder="تقنية المعلومات"
                  />
                </div>
                <div>
                  <Label>{isRTL ? 'القسم (إنجليزي)' : 'Department (EN)'}</Label>
                  <Input 
                    value={formData.department}
                    onChange={e => handleChange('department', e.target.value)}
                    placeholder="IT"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{isRTL ? 'تاريخ التعيين *' : 'Start Date *'}</Label>
                  <Input 
                    type="date"
                    value={formData.start_date}
                    onChange={e => handleStartDateChange(e.target.value)}
                  />
                  {formData.start_date && (() => {
                    const info = calculateServiceYears(formData.start_date);
                    if (info?.future) return (
                      <p className="text-sm text-warning mt-1 flex items-center gap-1">
                        <Clock size={14} /> {isRTL ? 'تاريخ مستقبلي' : 'Future date'}
                      </p>
                    );
                    return (
                      <div className="text-sm mt-1 p-2 bg-primary/10 rounded">
                        <p className="font-bold">{info.years} {isRTL ? 'سنة' : 'years'} و {info.months} {isRTL ? 'شهر' : 'months'}</p>
                        <p className="text-xs text-muted-foreground">
                          → {info.policyDays} {isRTL ? 'يوم إجازة سنوية' : 'annual leave days'}
                        </p>
                      </div>
                    );
                  })()}
                </div>
                <div>
                  <Label>{isRTL ? 'تاريخ النهاية (اختياري)' : 'End Date (Optional)'}</Label>
                  <Input 
                    type="date"
                    value={formData.end_date}
                    onChange={e => handleChange('end_date', e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 p-3 bg-warning/10 rounded-lg border border-warning/30">
                <div>
                  <Label>{isRTL ? 'تاريخ المباشرة الفعلية' : 'Work Start Date'}</Label>
                  <Input 
                    type="date"
                    value={formData.work_start_date}
                    onChange={e => handleChange('work_start_date', e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {isRTL ? 'قبل هذا التاريخ لا يُحتسب حضور' : 'No attendance before this date'}
                  </p>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label>{isRTL ? 'وضع التجربة' : 'Sandbox Mode'}</Label>
                    <p className="text-xs text-muted-foreground">
                      {isRTL ? 'لا يُحتسب حضور أو غياب' : 'No attendance tracking'}
                    </p>
                  </div>
                  <Switch 
                    checked={formData.sandbox_mode}
                    onCheckedChange={v => handleChange('sandbox_mode', v)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{isRTL ? 'فترة التجربة (شهر)' : 'Probation (months)'}</Label>
                  <Input 
                    type="number"
                    value={formData.probation_months}
                    onChange={e => handleChange('probation_months', parseInt(e.target.value) || 0)}
                  />
                </div>
                <div>
                  <Label>{isRTL ? 'فترة الإنذار (يوم)' : 'Notice Period (days)'}</Label>
                  <Input 
                    type="number"
                    value={formData.notice_period_days}
                    onChange={e => handleChange('notice_period_days', parseInt(e.target.value) || 0)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* الخطوة 3: الراتب والبنك */}
          {step === 3 && (
            <div className="space-y-4">
              {formData.contract_category !== 'internship_unpaid' && formData.contract_category !== 'student_training' ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>{isRTL ? 'الراتب الأساسي' : 'Basic Salary'}</Label>
                      <Input 
                        type="number"
                        value={formData.basic_salary}
                        onChange={e => handleChange('basic_salary', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <Label>{isRTL ? 'بدل السكن' : 'Housing'}</Label>
                      <Input 
                        type="number"
                        value={formData.housing_allowance}
                        onChange={e => handleChange('housing_allowance', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <Label>{isRTL ? 'بدل النقل' : 'Transport'}</Label>
                      <Input 
                        type="number"
                        value={formData.transport_allowance}
                        onChange={e => handleChange('transport_allowance', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <Label>{isRTL ? 'بدل طبيعة العمل' : 'Nature of Work'}</Label>
                      <Input 
                        type="number"
                        value={formData.nature_of_work_allowance}
                        onChange={e => handleChange('nature_of_work_allowance', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div>
                      <Label>{isRTL ? 'بدلات أخرى' : 'Other Allowances'}</Label>
                      <Input 
                        type="number"
                        value={formData.other_allowances}
                        onChange={e => handleChange('other_allowances', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                  </div>
                  
                  <div className="p-3 bg-primary/10 rounded-lg text-center">
                    <p className="text-sm text-muted-foreground">{isRTL ? 'إجمالي الراتب' : 'Total Salary'}</p>
                    <p className="text-2xl font-bold text-primary">{formatCurrency(totalSalary)}</p>
                  </div>
                </>
              ) : (
                <div className="p-6 text-center bg-muted/50 rounded-lg">
                  <p className="text-muted-foreground">
                    {isRTL ? 'هذا النوع من العقود بدون راتب' : 'This contract type has no salary'}
                  </p>
                </div>
              )}

              <div className="border-t pt-4">
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <Building2 size={18} />
                  {isRTL ? 'معلومات البنك *' : 'Bank Details *'}
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>{isRTL ? 'اسم البنك' : 'Bank Name'}</Label>
                    <Input 
                      value={formData.bank_name}
                      onChange={e => handleChange('bank_name', e.target.value)}
                      placeholder={isRTL ? 'الراجحي، الأهلي...' : 'Al Rajhi, Al Ahli...'}
                    />
                  </div>
                  <div>
                    <Label>{isRTL ? 'رقم الآيبان' : 'IBAN'}</Label>
                    <Input 
                      value={formData.bank_iban}
                      onChange={e => handleChange('bank_iban', e.target.value)}
                      placeholder="SA..."
                      dir="ltr"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* الخطوة 4: الإجازات والملاحظات */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{isRTL ? 'سياسة الإجازة السنوية' : 'Annual Leave Policy'}</Label>
                  <Select 
                    value={String(formData.annual_policy_days)} 
                    onValueChange={v => handleChange('annual_policy_days', parseInt(v))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="21">21 {isRTL ? 'يوم (افتراضي)' : 'days (default)'}</SelectItem>
                      <SelectItem value="30">30 {isRTL ? 'يوم (بقرار إداري)' : 'days (by decision)'}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>{isRTL ? 'رصيد الاستئذان الشهري' : 'Monthly Permission Hours'}</Label>
                  <Select 
                    value={String(formData.monthly_permission_hours)} 
                    onValueChange={v => handleChange('monthly_permission_hours', parseInt(v))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">0</SelectItem>
                      <SelectItem value="1">1 {isRTL ? 'ساعة' : 'hour'}</SelectItem>
                      <SelectItem value="2">2 {isRTL ? 'ساعات (افتراضي)' : 'hours (default)'}</SelectItem>
                      <SelectItem value="3">3 {isRTL ? 'ساعات (الحد الأقصى)' : 'hours (max)'}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* عقد مُهاجر */}
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <Label>{isRTL ? 'عقد مُهاجر (موظف قديم)' : 'Migrated Contract'}</Label>
                  <p className="text-xs text-muted-foreground">
                    {isRTL ? 'لإضافة رصيد إجازات من النظام القديم' : 'To add leave balance from old system'}
                  </p>
                </div>
                <Switch 
                  checked={formData.is_migrated}
                  onCheckedChange={v => handleChange('is_migrated', v)}
                />
              </div>

              {formData.is_migrated && (
                <div className="p-4 bg-warning/10 rounded-lg border border-warning/30 space-y-4">
                  <div className="flex items-center gap-2 text-warning">
                    <AlertTriangle size={18} />
                    <span className="font-medium">{isRTL ? 'أرصدة من النظام القديم' : 'Balances from old system'}</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>{isRTL ? 'رصيد الإجازة السنوية المتبقي' : 'Remaining Annual Leave'}</Label>
                      <Input 
                        type="number"
                        step="0.5"
                        value={formData.leave_opening_balance?.annual || 0}
                        onChange={e => handleChange('leave_opening_balance', {
                          ...formData.leave_opening_balance,
                          annual: parseFloat(e.target.value) || 0
                        })}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {isRTL ? 'الرصيد المتبقي بعد خصم المستهلك' : 'Balance after consumed'}
                      </p>
                    </div>
                    <div>
                      <Label>{isRTL ? 'المستهلك (للتوثيق فقط)' : 'Consumed (for reference)'}</Label>
                      <Input 
                        type="number"
                        step="0.5"
                        value={formData.leave_consumed?.annual || 0}
                        onChange={e => handleChange('leave_consumed', {
                          ...formData.leave_consumed,
                          annual: parseFloat(e.target.value) || 0
                        })}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {isRTL ? 'لا يؤثر على الحساب' : 'Does not affect calculation'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <Label>{isRTL ? 'ملاحظات' : 'Notes'}</Label>
                <Textarea 
                  value={formData.notes}
                  onChange={e => handleChange('notes', e.target.value)}
                  rows={3}
                  placeholder={isRTL ? 'أي ملاحظات إضافية...' : 'Any additional notes...'}
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-4 flex items-center justify-between bg-muted/30">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            {isRTL ? 'إلغاء' : 'Cancel'}
          </Button>
          
          <div className="flex gap-2">
            {step > 1 && (
              <Button variant="outline" onClick={prevStep} disabled={loading}>
                {isRTL ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
                {isRTL ? 'السابق' : 'Previous'}
              </Button>
            )}
            
            {step < 4 ? (
              <Button onClick={nextStep}>
                {isRTL ? 'التالي' : 'Next'}
                {isRTL ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
              </Button>
            ) : (
              <Button onClick={handleSubmit} disabled={loading} className="bg-success hover:bg-success/90">
                {loading ? (
                  <span className="animate-spin">...</span>
                ) : (
                  <>
                    <CheckCircle size={18} className="me-1" />
                    {editContract 
                      ? (isRTL ? 'حفظ التعديلات' : 'Save Changes')
                      : (isRTL ? 'إنشاء العقد' : 'Create Contract')
                    }
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
