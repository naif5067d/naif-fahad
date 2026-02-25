// الثوابت المشتركة للعقود
export const CONTRACT_STATUS = {
  draft: { label: 'مسودة', labelEn: 'Draft', color: 'bg-slate-500' },
  draft_correction: { label: 'مسودة تصحيح', labelEn: 'Draft Correction', color: 'bg-warning' },
  pending_stas: { label: 'في انتظار STAS', labelEn: 'Pending STAS', color: 'bg-warning' },
  active: { label: 'نشط', labelEn: 'Active', color: 'bg-success' },
  terminated: { label: 'منتهي', labelEn: 'Terminated', color: 'bg-destructive' },
  closed: { label: 'مغلق', labelEn: 'Closed', color: 'bg-slate-500' },
};

export const CONTRACT_CATEGORIES = {
  employment: { label: 'توظيف', labelEn: 'Employment' },
  internship_unpaid: { label: 'تدريب غير مدفوع', labelEn: 'Unpaid Internship' },
  student_training: { label: 'تدريب طالب', labelEn: 'Student Training' },
};

export const EMPLOYMENT_TYPES = {
  unlimited: { label: 'غير محدد المدة', labelEn: 'Unlimited' },
  fixed_term: { label: 'محدد المدة', labelEn: 'Fixed Term' },
  trial_paid: { label: 'فترة تجربة مدفوعة', labelEn: 'Paid Trial' },
  part_time: { label: 'دوام جزئي', labelEn: 'Part Time' },
};

export const TERMINATION_REASONS = {
  resignation: { label: 'استقالة', labelEn: 'Resignation' },
  termination: { label: 'إنهاء من الشركة', labelEn: 'Termination' },
  contract_expiry: { label: 'انتهاء العقد', labelEn: 'Contract Expiry' },
  retirement: { label: 'تقاعد', labelEn: 'Retirement' },
  death: { label: 'وفاة', labelEn: 'Death' },
  mutual_agreement: { label: 'اتفاق متبادل', labelEn: 'Mutual Agreement' },
};

// البيانات الافتراضية للعقد الجديد
export const DEFAULT_CONTRACT_DATA = {
  // الخطوة 1: بيانات الموظف
  is_new_employee: true,
  employee_id: '',
  employee_code: '',
  employee_name: '',
  employee_name_ar: '',
  email: '',
  phone: '',
  // بيانات الهوية/الإقامة
  is_saudi: null,
  national_id: '',  // للسعودي
  iqama_number: '',  // للأجنبي
  iqama_expiry_date: '',  // للأجنبي
  nationality: '',  // للأجنبي
  
  // الخطوة 2: الوظيفة والتواريخ
  contract_category: 'employment',
  employment_type: 'unlimited',
  job_title: '',
  job_title_ar: '',
  department: '',
  department_ar: '',
  start_date: '',
  end_date: '',
  work_start_date: '',
  sandbox_mode: false,
  probation_months: 3,
  notice_period_days: 30,
  
  // الخطوة 3: الراتب والبنك
  basic_salary: 0,
  housing_allowance: 0,
  transport_allowance: 0,
  nature_of_work_allowance: 0,
  other_allowances: 0,
  bank_name: '',
  bank_iban: '',
  
  // الخطوة 4: الإجازات والأرصدة
  annual_policy_days: 21,
  monthly_permission_hours: 2,
  is_migrated: false,
  leave_opening_balance: { annual: 0, sick: 0, emergency: 0 },
  leave_consumed: { annual: 0, sick: 0, emergency: 0 },
  notes: '',
};

// حساب سنوات الخدمة
export const calculateServiceYears = (startDate) => {
  if (!startDate) return null;
  const start = new Date(startDate);
  const today = new Date();
  
  if (start > today) {
    return { future: true, years: 0, months: 0, totalYears: 0, policyDays: 21 };
  }
  
  const diffMs = today - start;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const years = Math.floor(diffDays / 365);
  const remainingDays = diffDays % 365;
  const months = Math.floor(remainingDays / 30);
  const totalYears = diffDays / 365;
  
  // سياسة الإجازة: 21 يوم لأقل من 5 سنوات، 30 يوم لـ 5 سنوات فأكثر
  const policyDays = totalYears >= 5 ? 30 : 21;
  
  return { years, months, totalYears: totalYears.toFixed(2), policyDays, future: false };
};

// تنسيق العملة
export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('ar-SA', { 
    style: 'currency', 
    currency: 'SAR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(amount || 0);
};

// توليد الرقم المرجعي
export const generateRefNo = () => {
  const year = new Date().getFullYear();
  const randomNum = String(Math.floor(Math.random() * 900) + 100).padStart(3, '0');
  return `DAC-${year}-${randomNum}`;
};
