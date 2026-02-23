import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Users, Search, Edit2, UserCheck, Trash2, Key, Eye, EyeOff, User, AlertTriangle, Calendar, Briefcase, RefreshCw, Bell } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function EmployeesPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [employees, setEmployees] = useState([]);
  const [expiringContracts, setExpiringContracts] = useState([]);
  const [search, setSearch] = useState('');
  const [editDialog, setEditDialog] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [previewCard, setPreviewCard] = useState(null);
  const [cardSummary, setCardSummary] = useState(null);
  const [loadingCard, setLoadingCard] = useState(false);
  
  // حالات تعيين المشرف
  const [supervisorDialog, setSupervisorDialog] = useState(null);
  const [selectedSupervisor, setSelectedSupervisor] = useState('');
  const [savingSupervisor, setSavingSupervisor] = useState(false);
  
  // حالات تعيين موظفين متعددين للمشرف
  const [bulkSupervisorDialog, setBulkSupervisorDialog] = useState(null);
  const [selectedEmployeesForSupervisor, setSelectedEmployeesForSupervisor] = useState([]);
  
  // حالات بيانات الدخول
  const [credentialsDialog, setCredentialsDialog] = useState(null);
  const [credentialsForm, setCredentialsForm] = useState({ username: '', password: '' });
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  
  // حالة حذف الموظف
  const [deleteDialog, setDeleteDialog] = useState(null);
  const [deleting, setDeleting] = useState(false);
  
  // حالة الاستدعاء
  const [summonDialog, setSummonDialog] = useState(null);
  const [summonForm, setSummonForm] = useState({ priority: 'normal', comment: '' });
  const [sendingSummon, setSendingSummon] = useState(false);

  const isStas = user?.role === 'stas';
  const isOps = ['sultan', 'naif', 'stas', 'mohammed'].includes(user?.role);
  const isCEO = user?.role === 'mohammed';
  const canSummon = ['sultan', 'naif', 'stas', 'mohammed', 'salah'].includes(user?.role);
  const canAssignSupervisor = ['sultan', 'naif', 'stas'].includes(user?.role); // محمد لا يحتاج تعيين مشرف
  
  // حالة الاستدعاءات النشطة
  const [activeSummons, setActiveSummons] = useState([]);

  useEffect(() => {
    api.get('/api/employees').then(r => setEmployees(r.data)).catch((err) => {
      console.error('Failed to load employees:', err);
    });
    // جلب العقود المنتهية قريباً
    if (user?.role && ['sultan', 'naif', 'stas', 'mohammed'].includes(user.role)) {
      api.get('/api/notifications/expiring-contracts?days_ahead=90')
        .then(r => setExpiringContracts(r.data.employees || []))
        .catch(() => {});
    }
    // جلب الاستدعاءات النشطة
    if (user?.role && ['sultan', 'naif', 'stas', 'mohammed', 'salah'].includes(user.role)) {
      api.get('/api/notifications/summons')
        .then(r => setActiveSummons(r.data.summons || []))
        .catch(() => {});
    }
  }, [user?.role]);

  // التحقق إذا كان الموظف لديه استدعاء نشط
  const getActiveSummon = (employeeId) => {
    return activeSummons.find(s => 
      s.notification_type === 'summon' && 
      s.employee_id === employeeId && 
      !s.is_read
    );
  };

  // التحقق إذا كان الموظف لديه عقد ينتهي قريباً
  const getExpiryStatus = (employeeId) => {
    const expiring = expiringContracts.find(e => e.employee_id === employeeId);
    return expiring;
  };

  const filtered = employees.filter(e => {
    if (!search) return true;
    const s = search.toLowerCase();
    return e.full_name?.toLowerCase().includes(s) || e.employee_number?.includes(s) || e.department?.toLowerCase().includes(s);
  });

  const openEdit = (emp) => {
    setEditForm({ full_name: emp.full_name, full_name_ar: emp.full_name_ar, is_active: emp.is_active });
    setEditDialog(emp);
  };

  // فتح بطاقة الموظف Preview
  const openPreviewCard = async (emp) => {
    setPreviewCard(emp);
    setLoadingCard(true);
    setCardSummary(null);
    try {
      const res = await api.get(`/api/employees/${emp.id}/summary`);
      setCardSummary(res.data);
    } catch (err) {
      console.error('Failed to load employee summary');
    } finally {
      setLoadingCard(false);
    }
  };

  const handleSave = async () => {
    if (!editDialog) return;
    setSaving(true);
    try {
      await api.patch(`/api/employees/${editDialog.id}`, editForm);
      toast.success(lang === 'ar' ? 'تم تحديث الموظف' : 'Employee updated');
      setEditDialog(null);
      api.get('/api/employees').then(r => setEmployees(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSaving(false); }
  };

  // تعيين المشرف
  const openSupervisorDialog = (emp) => {
    setSelectedSupervisor(emp.supervisor_id || 'none');
    setSupervisorDialog(emp);
  };

  const handleSaveSupervisor = async () => {
    if (!supervisorDialog) return;
    setSavingSupervisor(true);
    try {
      const supervisorId = selectedSupervisor === 'none' ? null : selectedSupervisor;
      await api.put(`/api/employees/${supervisorDialog.id}/supervisor`, {
        supervisor_id: supervisorId
      });
      toast.success(lang === 'ar' ? 'تم تعيين المشرف' : 'Supervisor assigned');
      setSupervisorDialog(null);
      api.get('/api/employees').then(r => setEmployees(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSavingSupervisor(false); }
  };

  // فتح نافذة تعيين موظفين متعددين للمشرف
  const openBulkSupervisorDialog = (supervisor) => {
    // الموظفون الحاليون تحت هذا المشرف
    const currentEmployees = employees.filter(e => e.supervisor_id === supervisor.id).map(e => e.id);
    setSelectedEmployeesForSupervisor(currentEmployees);
    setBulkSupervisorDialog(supervisor);
  };

  // حفظ تعيين موظفين متعددين للمشرف
  const handleSaveBulkSupervisor = async () => {
    if (!bulkSupervisorDialog) return;
    setSavingSupervisor(true);
    try {
      await api.put(`/api/employees/bulk-supervisor`, {
        supervisor_id: bulkSupervisorDialog.id,
        employee_ids: selectedEmployeesForSupervisor
      });
      toast.success(lang === 'ar' ? `تم تعيين ${selectedEmployeesForSupervisor.length} موظف تحت المشرف` : `${selectedEmployeesForSupervisor.length} employees assigned to supervisor`);
      setBulkSupervisorDialog(null);
      api.get('/api/employees').then(r => setEmployees(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSavingSupervisor(false); }
  };

  // تبديل اختيار موظف للمشرف
  const toggleEmployeeForSupervisor = (empId) => {
    setSelectedEmployeesForSupervisor(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  // الحصول على اسم المشرف
  const getSupervisorName = (emp) => {
    if (!emp.supervisor_id) return '-';
    const supervisor = employees.find(e => e.id === emp.supervisor_id);
    return supervisor ? (lang === 'ar' ? supervisor.full_name_ar || supervisor.full_name : supervisor.full_name) : '-';
  };

  // الموظفون المتاحون كمشرفين (ليسوا الموظف نفسه)
  const availableSupervisors = employees.filter(e => 
    supervisorDialog && e.id !== supervisorDialog.id && e.is_active
  );

  // بيانات الدخول
  const openCredentialsDialog = async (emp) => {
    setCredentialsDialog(emp);
    setCredentialsForm({ username: '', password: '' });
    setShowPassword(false);
    setUserInfo(null);
    
    try {
      const res = await api.get(`/api/users/${emp.id}`);
      setUserInfo(res.data);
      setCredentialsForm(f => ({ 
        ...f, 
        username: res.data.username || '',
        password: res.data.plain_password || ''  // عرض كلمة المرور المُخزنة
      }));
    } catch (err) {
      // لا يوجد مستخدم - سيتم إنشاؤه
      setUserInfo(null);
    }
  };

  const handleSaveCredentials = async () => {
    if (!credentialsDialog) return;
    setSavingCredentials(true);
    
    try {
      if (userInfo) {
        // تحديث المستخدم الموجود
        const update = {};
        if (credentialsForm.username && credentialsForm.username !== userInfo.username) {
          update.username = credentialsForm.username;
        }
        if (credentialsForm.password) {
          update.password = credentialsForm.password;
        }
        
        if (Object.keys(update).length === 0) {
          toast.info(lang === 'ar' ? 'لا توجد تغييرات' : 'No changes');
          setSavingCredentials(false);
          return;
        }
        
        await api.put(`/api/users/${credentialsDialog.id}/credentials`, update);
        toast.success(lang === 'ar' ? 'تم تحديث بيانات الدخول' : 'Credentials updated');
      } else {
        // إنشاء مستخدم جديد
        if (!credentialsForm.username || !credentialsForm.password) {
          toast.error(lang === 'ar' ? 'اسم المستخدم وكلمة المرور مطلوبان' : 'Username and password required');
          setSavingCredentials(false);
          return;
        }
        
        await api.post('/api/users/create', {
          employee_id: credentialsDialog.id,
          username: credentialsForm.username,
          password: credentialsForm.password
        });
        toast.success(lang === 'ar' ? 'تم إنشاء بيانات الدخول' : 'Credentials created');
      }
      
      setCredentialsDialog(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setSavingCredentials(false);
    }
  };

  // حذف الموظف نهائياً
  const openDeleteDialog = (emp) => {
    setDeleteDialog(emp);
  };

  const handleDelete = async () => {
    if (!deleteDialog) return;
    setDeleting(true);
    
    try {
      // حذف نهائي من الجذور
      const res = await api.delete(`/api/employees/${deleteDialog.id}/permanent`);
      toast.success(
        lang === 'ar' 
          ? `تم حذف الموظف "${deleteDialog.full_name_ar || deleteDialog.full_name}" نهائياً` 
          : `Employee "${deleteDialog.full_name}" permanently deleted`,
        {
          description: lang === 'ar' 
            ? `تم حذف: ${Object.entries(res.data.deleted_counts || {}).map(([k,v]) => v > 0 ? `${k}: ${v}` : '').filter(Boolean).join(', ')}`
            : undefined
        }
      );
      setDeleteDialog(null);
      api.get('/api/employees').then(r => setEmployees(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setDeleting(false);
    }
  };

  // فتح dialog الاستدعاء
  const openSummonDialog = (emp) => {
    setSummonDialog(emp);
    setSummonForm({ priority: 'normal', comment: '' });
  };

  // إرسال الاستدعاء
  const handleSendSummon = async () => {
    if (!summonDialog) return;
    setSendingSummon(true);
    
    try {
      await api.post('/api/notifications/summon', {
        employee_id: summonDialog.id,
        employee_name: summonDialog.full_name_ar || summonDialog.full_name,
        priority: summonForm.priority,
        comment: summonForm.comment
      });
      
      const priorityText = {
        urgent: lang === 'ar' ? 'طارئ' : 'Urgent',
        normal: lang === 'ar' ? 'عادي' : 'Normal',
        medium: lang === 'ar' ? 'متوسط' : 'Medium'
      };
      
      toast.success(
        lang === 'ar' 
          ? `تم إرسال استدعاء ${priorityText[summonForm.priority]} للموظف "${summonDialog.full_name_ar || summonDialog.full_name}"` 
          : `${priorityText[summonForm.priority]} summon sent to "${summonDialog.full_name}"`
      );
      
      // تحديث قائمة الاستدعاءات
      api.get('/api/notifications/summons')
        .then(r => setActiveSummons(r.data.summons || []))
        .catch(() => {});
      
      setSummonDialog(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send summon');
    } finally {
      setSendingSummon(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="employees-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{lang === 'ar' ? 'الموظفين' : 'Employees'}</h1>
      </div>

      <div className="relative">
        <Search size={16} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input data-testid="employee-search" value={search} onChange={e => setSearch(e.target.value)} placeholder={lang === 'ar' ? 'بحث...' : 'Search...'} className="ps-9" />
      </div>

      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="hr-table" data-testid="employees-table">
            <thead>
              <tr>
                <th>{lang === 'ar' ? 'الرقم' : 'ID'}</th>
                <th>{lang === 'ar' ? 'الاسم' : 'Name'}</th>
                <th className="hidden sm:table-cell">{lang === 'ar' ? 'القسم' : 'Department'}</th>
                <th className="hidden md:table-cell">{lang === 'ar' ? 'سنوات الخدمة' : 'Service Years'}</th>
                <th className="hidden md:table-cell">{lang === 'ar' ? 'المشرف' : 'Supervisor'}</th>
                <th>{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                {isOps && <th>{lang === 'ar' ? 'الإجراءات' : 'Actions'}</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map(e => {
                const expiryStatus = getExpiryStatus(e.id);
                const isExpiring = expiryStatus && expiryStatus.days_remaining <= 90;
                const isCritical = expiryStatus && expiryStatus.days_remaining <= 30;
                
                // حساب سنوات الخدمة
                const calcServiceYears = () => {
                  const startDate = e.hire_date || e.start_date || e.created_at;
                  if (!startDate) return null;
                  const start = new Date(startDate);
                  const today = new Date();
                  if (start > today) return null;
                  const years = (today - start) / (365.25 * 24 * 60 * 60 * 1000);
                  return Math.round(years * 10) / 10;
                };
                const serviceYears = calcServiceYears();
                
                const activeSummon = getActiveSummon(e.id) || getActiveSummon(e.employee_number);
                
                return (
                <tr 
                  key={e.id} 
                  data-testid={`emp-row-${e.employee_number}`}
                  className={`${isExpiring ? (isCritical ? 'bg-red-50 animate-pulse' : 'bg-[hsl(var(--warning)/0.1)]') : ''} ${activeSummon ? 'border-l-4 border-l-orange-400' : ''}`}
                >
                  <td className="font-mono text-xs">{e.employee_number}</td>
                  <td className="text-sm font-medium">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={isCritical ? 'text-red-600 font-bold' : ''}>
                        {lang === 'ar' ? (e.full_name_ar || e.full_name) : e.full_name}
                      </span>
                      {/* عرض الاستدعاء النشط */}
                      {activeSummon && (
                        <span 
                          className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 ${
                            activeSummon.priority === 'urgent' ? 'bg-red-100 text-red-700' : 
                            activeSummon.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' : 
                            'bg-green-100 text-green-700'
                          }`}
                          title={activeSummon.comment || (lang === 'ar' ? 'استدعاء نشط' : 'Active summon')}
                        >
                          <Bell size={10} />
                          {lang === 'ar' 
                            ? (activeSummon.priority === 'urgent' ? 'مستدعى - طارئ' : activeSummon.priority === 'medium' ? 'مستدعى' : 'مستدعى')
                            : 'Summoned'
                          }
                        </span>
                      )}
                      {isExpiring && (
                        <span 
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            isCritical ? 'bg-red-100 text-red-700' : 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]'
                          }`}
                          title={lang === 'ar' ? `ينتهي العقد خلال ${expiryStatus.days_remaining} يوم` : `Contract expires in ${expiryStatus.days_remaining} days`}
                        >
                          <AlertTriangle size={10} className="inline me-0.5" />
                          {expiryStatus.days_remaining} {lang === 'ar' ? 'يوم' : 'd'}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="hidden sm:table-cell text-sm">{lang === 'ar' ? (e.department_ar || e.department) : e.department}</td>
                  {/* سنوات الخدمة */}
                  <td className="hidden md:table-cell text-center">
                    {serviceYears !== null ? (
                      <span className={`text-sm font-bold ${serviceYears >= 5 ? 'text-[hsl(var(--success))]' : 'text-blue-600'}`}>
                        {serviceYears} {lang === 'ar' ? 'سنة' : 'yr'}
                        <span className="text-[10px] text-muted-foreground block">
                          {serviceYears >= 5 ? '30 يوم' : '21 يوم'}
                        </span>
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="hidden md:table-cell text-sm">{getSupervisorName(e)}</td>
                  <td>
                    <span className={`status-badge ${e.is_active ? 'status-executed' : 'status-rejected'}`}>
                      {e.is_active ? (lang === 'ar' ? 'نشط' : 'Active') : (lang === 'ar' ? 'غير نشط' : 'Inactive')}
                    </span>
                  </td>
                  {isOps && (
                    <td>
                      <div className="flex gap-1">
                        {/* زر عرض البطاقة */}
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-7 w-7 p-0" 
                          onClick={() => openPreviewCard(e)} 
                          data-testid={`preview-card-${e.employee_number}`}
                          title={lang === 'ar' ? 'عرض البطاقة' : 'View Card'}
                        >
                          <User size={14} />
                        </Button>
                        {/* زر تعيين مشرف - ليس لمحمد */}
                        {canAssignSupervisor && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-7 w-7 p-0" 
                            onClick={() => openSupervisorDialog(e)} 
                            data-testid={`assign-supervisor-${e.employee_number}`}
                            title={lang === 'ar' ? 'تعيين مشرف له' : 'Assign Supervisor'}
                          >
                            <UserCheck size={14} />
                          </Button>
                        )}
                        {/* زر تعيين موظفين تحت هذا المشرف - ليس لمحمد */}
                        {canAssignSupervisor && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-7 w-7 p-0 text-blue-600 hover:text-blue-700" 
                            onClick={() => openBulkSupervisorDialog(e)} 
                            data-testid={`assign-employees-${e.employee_number}`}
                            title={lang === 'ar' ? 'تعيين موظفين تحت إشرافه' : 'Assign Employees Under'}
                          >
                            <Users size={14} />
                          </Button>
                        )}
                        {/* زر الاستدعاء */}
                        {canSummon && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-7 w-7 p-0 text-orange-600 hover:text-orange-700" 
                            onClick={() => openSummonDialog(e)} 
                            data-testid={`summon-${e.employee_number}`}
                            title={lang === 'ar' ? 'استدعاء' : 'Summon'}
                          >
                            <Bell size={14} />
                          </Button>
                        )}
                        {isStas && (
                          <>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-7 w-7 p-0" 
                              onClick={() => openCredentialsDialog(e)} 
                              data-testid={`credentials-${e.employee_number}`}
                              title={lang === 'ar' ? 'بيانات الدخول' : 'Login Credentials'}
                            >
                              <Key size={14} />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-7 w-7 p-0" 
                              onClick={() => openEdit(e)} 
                              data-testid={`edit-emp-${e.employee_number}`}
                              title={lang === 'ar' ? 'تعديل' : 'Edit'}
                            >
                              <Edit2 size={14} />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-7 w-7 p-0 text-destructive hover:text-destructive" 
                              onClick={() => openDeleteDialog(e)} 
                              data-testid={`delete-emp-${e.employee_number}`}
                              title={lang === 'ar' ? 'حذف' : 'Delete'}
                            >
                              <Trash2 size={14} />
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              );})}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Dialog (STAS only) */}
      <Dialog open={!!editDialog} onOpenChange={() => setEditDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{lang === 'ar' ? 'تعديل الموظف' : 'Edit Employee'}: {editDialog?.employee_number}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Full Name (EN)'}</Label>
              <Input data-testid="edit-name-en" value={editForm.full_name || ''} onChange={e => setEditForm(f => ({ ...f, full_name: e.target.value }))} />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Full Name (AR)'}</Label>
              <Input data-testid="edit-name-ar" value={editForm.full_name_ar || ''} onChange={e => setEditForm(f => ({ ...f, full_name_ar: e.target.value }))} dir="rtl" />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'المسمى الوظيفي (إنجليزي)' : 'Job Title (EN)'}</Label>
              <Input data-testid="edit-job-title-en" value={editForm.job_title || ''} onChange={e => setEditForm(f => ({ ...f, job_title: e.target.value }))} />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'المسمى الوظيفي (عربي)' : 'Job Title (AR)'}</Label>
              <Input data-testid="edit-job-title-ar" value={editForm.job_title_ar || ''} onChange={e => setEditForm(f => ({ ...f, job_title_ar: e.target.value }))} dir="rtl" />
            </div>
            <div className="flex items-center justify-between">
              <Label>{lang === 'ar' ? 'نشط' : 'Active'}</Label>
              <Switch data-testid="edit-active-toggle" checked={editForm.is_active} onCheckedChange={v => setEditForm(f => ({ ...f, is_active: v }))} />
            </div>
            <Button data-testid="save-employee" onClick={handleSave} className="w-full bg-primary text-primary-foreground" disabled={saving}>
              {saving ? (lang === 'ar' ? 'جاري الحفظ...' : 'Saving...') : (lang === 'ar' ? 'حفظ' : 'Save')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Supervisor Assignment Dialog */}
      <Dialog open={!!supervisorDialog} onOpenChange={() => setSupervisorDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{lang === 'ar' ? 'تعيين مشرف' : 'Assign Supervisor'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                {lang === 'ar' ? 'الموظف:' : 'Employee:'} {supervisorDialog && (lang === 'ar' ? supervisorDialog.full_name_ar : supervisorDialog.full_name)}
              </p>
            </div>
            <div>
              <Label>{lang === 'ar' ? 'المشرف' : 'Supervisor'}</Label>
              <Select value={selectedSupervisor || "none"} onValueChange={(v) => setSelectedSupervisor(v === "none" ? "" : v)}>
                <SelectTrigger className="mt-1" data-testid="select-supervisor">
                  <SelectValue placeholder={lang === 'ar' ? 'اختر مشرف...' : 'Select supervisor...'} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{lang === 'ar' ? 'بدون مشرف' : 'No supervisor'}</SelectItem>
                  {availableSupervisors.map(sup => (
                    <SelectItem key={sup.id} value={sup.id}>
                      {lang === 'ar' ? (sup.full_name_ar || sup.full_name) : sup.full_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button 
              data-testid="save-supervisor" 
              onClick={handleSaveSupervisor} 
              className="w-full bg-primary text-primary-foreground" 
              disabled={savingSupervisor}
            >
              {savingSupervisor ? (lang === 'ar' ? 'جاري الحفظ...' : 'Saving...') : (lang === 'ar' ? 'حفظ' : 'Save')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Bulk Supervisor Assignment Dialog - تعيين موظفين متعددين للمشرف */}
      <Dialog open={!!bulkSupervisorDialog} onOpenChange={() => setBulkSupervisorDialog(null)}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {lang === 'ar' ? 'تعيين موظفين للمشرف' : 'Assign Employees to Supervisor'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="p-3 bg-muted rounded-lg">
              <p className="font-medium">
                {lang === 'ar' ? 'المشرف:' : 'Supervisor:'} {bulkSupervisorDialog && (lang === 'ar' ? bulkSupervisorDialog.full_name_ar : bulkSupervisorDialog.full_name)}
              </p>
            </div>
            
            <div>
              <p className="text-sm text-muted-foreground mb-2">
                {lang === 'ar' 
                  ? `اختر الموظفين لوضعهم تحت إشراف ${bulkSupervisorDialog?.full_name_ar || ''}`
                  : `Select employees to place under ${bulkSupervisorDialog?.full_name || ''}`}
              </p>
              <div className="space-y-2 max-h-60 overflow-y-auto border rounded-lg p-2">
                {employees
                  .filter(e => e.is_active && e.id !== bulkSupervisorDialog?.id)
                  .map(emp => (
                    <label 
                      key={emp.id} 
                      className="flex items-center gap-3 p-2 hover:bg-muted rounded-lg cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedEmployeesForSupervisor.includes(emp.id)}
                        onChange={() => toggleEmployeeForSupervisor(emp.id)}
                        className="w-4 h-4 rounded"
                      />
                      <div className="flex-1">
                        <span className="font-medium">
                          {lang === 'ar' ? emp.full_name_ar || emp.full_name : emp.full_name}
                        </span>
                        <span className="text-xs text-muted-foreground ms-2">
                          {emp.job_title_ar || emp.job_title}
                        </span>
                      </div>
                      {emp.supervisor_id && (
                        <span className="text-xs text-[hsl(var(--warning))]">
                          {lang === 'ar' ? 'لديه مشرف' : 'Has supervisor'}
                        </span>
                      )}
                    </label>
                  ))}
              </div>
            </div>
            
            <div className="text-sm text-muted-foreground">
              {lang === 'ar' 
                ? `تم اختيار ${selectedEmployeesForSupervisor.length} موظف`
                : `${selectedEmployeesForSupervisor.length} employees selected`}
            </div>
            
            <Button 
              onClick={handleSaveBulkSupervisor} 
              className="w-full" 
              disabled={savingSupervisor}
            >
              {savingSupervisor 
                ? (lang === 'ar' ? 'جاري الحفظ...' : 'Saving...') 
                : (lang === 'ar' ? 'حفظ التعيينات' : 'Save Assignments')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Credentials Dialog (STAS only) */}
      <Dialog open={!!credentialsDialog} onOpenChange={() => setCredentialsDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{lang === 'ar' ? 'بيانات الدخول' : 'Login Credentials'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <p className="text-sm font-medium mb-1">
                {lang === 'ar' ? 'الموظف:' : 'Employee:'} {credentialsDialog && (lang === 'ar' ? credentialsDialog.full_name_ar : credentialsDialog.full_name)}
              </p>
              {userInfo ? (
                <p className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                  {lang === 'ar' ? 'يوجد حساب مستخدم' : 'User account exists'}
                </p>
              ) : (
                <p className="text-xs text-[hsl(var(--warning))] bg-[hsl(var(--warning)/0.1)] px-2 py-1 rounded">
                  {lang === 'ar' ? 'لا يوجد حساب - سيتم إنشاؤه' : 'No account - will be created'}
                </p>
              )}
            </div>
            
            <div>
              <Label>{lang === 'ar' ? 'اسم المستخدم' : 'Username'}</Label>
              <Input 
                data-testid="input-username"
                value={credentialsForm.username} 
                onChange={e => setCredentialsForm(f => ({ ...f, username: e.target.value }))}
                placeholder={lang === 'ar' ? 'اسم المستخدم' : 'Username'}
              />
            </div>
            
            <div>
              <Label>{lang === 'ar' ? 'كلمة المرور' : 'Password'} {userInfo && <span className="text-xs text-muted-foreground">({lang === 'ar' ? 'اتركه فارغاً للإبقاء على القديمة' : 'leave empty to keep current'})</span>}</Label>
              <div className="relative">
                <Input 
                  data-testid="input-password"
                  type={showPassword ? 'text' : 'password'}
                  value={credentialsForm.password} 
                  onChange={e => setCredentialsForm(f => ({ ...f, password: e.target.value }))}
                  placeholder={userInfo ? '••••••••' : (lang === 'ar' ? 'كلمة المرور' : 'Password')}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 rtl:right-auto rtl:left-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </Button>
              </div>
            </div>
            
            <Button 
              data-testid="save-credentials" 
              onClick={handleSaveCredentials} 
              className="w-full bg-primary text-primary-foreground" 
              disabled={savingCredentials}
            >
              {savingCredentials 
                ? (lang === 'ar' ? 'جاري الحفظ...' : 'Saving...') 
                : (userInfo 
                    ? (lang === 'ar' ? 'تحديث' : 'Update') 
                    : (lang === 'ar' ? 'إنشاء' : 'Create')
                  )
              }
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteDialog} onOpenChange={() => setDeleteDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <Trash2 size={20} />
              {lang === 'ar' ? 'حذف نهائي' : 'Permanent Delete'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm font-medium">
              {lang === 'ar' 
                ? `هل أنت متأكد من حذف الموظف "${deleteDialog?.full_name_ar || deleteDialog?.full_name}" نهائياً؟`
                : `Are you sure you want to permanently delete "${deleteDialog?.full_name}"?`
              }
            </p>
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 text-sm">
              <p className="font-medium text-destructive mb-2">
                {lang === 'ar' ? '⚠️ تحذير: سيتم حذف كل شيء:' : '⚠️ Warning: Everything will be deleted:'}
              </p>
              <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                <li>{lang === 'ar' ? 'العقود' : 'Contracts'}</li>
                <li>{lang === 'ar' ? 'سجلات الحضور' : 'Attendance records'}</li>
                <li>{lang === 'ar' ? 'الإجازات والمعاملات' : 'Leaves & transactions'}</li>
                <li>{lang === 'ar' ? 'حساب المستخدم' : 'User account'}</li>
              </ul>
              <p className="mt-2 text-xs text-destructive font-bold">
                {lang === 'ar' ? '❌ هذا الإجراء لا يمكن التراجع عنه!' : '❌ This action cannot be undone!'}
              </p>
            </div>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={() => setDeleteDialog(null)} 
                className="flex-1"
              >
                {lang === 'ar' ? 'إلغاء' : 'Cancel'}
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete} 
                className="flex-1"
                disabled={deleting}
                data-testid="confirm-delete-emp"
              >
                {deleting ? (lang === 'ar' ? 'جاري الحذف...' : 'Deleting...') : (lang === 'ar' ? 'حذف نهائي' : 'Delete Permanently')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Employee Preview Card Dialog */}
      <Dialog open={!!previewCard} onOpenChange={() => setPreviewCard(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <User size={20} />
              {lang === 'ar' ? 'بطاقة الموظف' : 'Employee Card'}
            </DialogTitle>
          </DialogHeader>
          {loadingCard ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : previewCard && (
            <div className="space-y-4">
              {/* Employee Header */}
              <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-primary/10 to-primary/5 rounded-xl">
                <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center text-2xl font-bold text-primary">
                  {(lang === 'ar' ? previewCard.full_name_ar : previewCard.full_name)?.[0] || 'U'}
                </div>
                <div>
                  <h3 className="text-lg font-bold">
                    {lang === 'ar' ? (previewCard.full_name_ar || previewCard.full_name) : previewCard.full_name}
                  </h3>
                  <p className="text-sm text-muted-foreground">{previewCard.employee_number}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${previewCard.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {previewCard.is_active ? (lang === 'ar' ? 'نشط' : 'Active') : (lang === 'ar' ? 'غير نشط' : 'Inactive')}
                  </span>
                </div>
              </div>

              {/* Quick Stats */}
              {cardSummary && (
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <Calendar size={18} className="mx-auto mb-1 text-muted-foreground" />
                    <p className="text-lg font-bold text-primary">{cardSummary.leave_details?.balance || 0}</p>
                    <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'رصيد الإجازة' : 'Leave'}</p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <Briefcase size={18} className="mx-auto mb-1 text-muted-foreground" />
                    <p className="text-lg font-bold text-primary">{cardSummary.service_info?.years_display || '0'}</p>
                    <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'سنوات الخدمة' : 'Service Yrs'}</p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <Calendar size={18} className="mx-auto mb-1 text-muted-foreground" />
                    <p className="text-lg font-bold text-primary">
                      {cardSummary.attendance?.today_status === 'present' ? '✓' : '—'}
                    </p>
                    <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'حضور اليوم' : 'Today'}</p>
                  </div>
                </div>
              )}

              {/* Contract Info */}
              {cardSummary?.contract && (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-muted-foreground">{lang === 'ar' ? 'المسمى' : 'Title'}</span>
                    <span className="font-medium">{lang === 'ar' ? cardSummary.contract.job_title_ar : cardSummary.contract.job_title}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b">
                    <span className="text-muted-foreground">{lang === 'ar' ? 'القسم' : 'Dept'}</span>
                    <span className="font-medium">{lang === 'ar' ? cardSummary.contract.department_ar : cardSummary.contract.department}</span>
                  </div>
                  {cardSummary.contract.end_date && (
                    <div className="flex justify-between py-2 border-b">
                      <span className="text-muted-foreground">{lang === 'ar' ? 'انتهاء العقد' : 'Contract End'}</span>
                      <span className="font-medium">{cardSummary.contract.end_date}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button 
                  variant="outline" 
                  className="flex-1"
                  onClick={() => setPreviewCard(null)}
                >
                  {lang === 'ar' ? 'إغلاق' : 'Close'}
                </Button>
                <Button 
                  className="flex-1"
                  onClick={() => { setPreviewCard(null); navigate(`/employees/${previewCard.id}`); }}
                  data-testid="view-full-profile-btn"
                >
                  {lang === 'ar' ? 'الملف الكامل' : 'Full Profile'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Summon Dialog - استدعاء الموظف */}
      <Dialog open={!!summonDialog} onOpenChange={() => setSummonDialog(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bell size={20} className="text-orange-500" />
              {lang === 'ar' ? 'استدعاء موظف' : 'Summon Employee'}
            </DialogTitle>
          </DialogHeader>
          {summonDialog && (
            <div className="space-y-4">
              {/* معلومات الموظف */}
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium">
                  {lang === 'ar' ? summonDialog.full_name_ar : summonDialog.full_name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {summonDialog.employee_number} • {summonDialog.department_ar || summonDialog.department}
                </p>
              </div>

              {/* اختيار الأولوية */}
              <div className="space-y-2">
                <Label>{lang === 'ar' ? 'نوع الاستدعاء' : 'Priority'}</Label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant={summonForm.priority === 'urgent' ? 'default' : 'outline'}
                    className={`flex-1 ${summonForm.priority === 'urgent' ? 'bg-red-500 hover:bg-red-600 text-white' : 'border-red-300 text-red-600 hover:bg-red-50'}`}
                    onClick={() => setSummonForm(f => ({ ...f, priority: 'urgent' }))}
                  >
                    🔴 {lang === 'ar' ? 'طارئ' : 'Urgent'}
                  </Button>
                  <Button
                    type="button"
                    variant={summonForm.priority === 'medium' ? 'default' : 'outline'}
                    className={`flex-1 ${summonForm.priority === 'medium' ? 'bg-yellow-500 hover:bg-yellow-600 text-white' : 'border-yellow-300 text-yellow-600 hover:bg-yellow-50'}`}
                    onClick={() => setSummonForm(f => ({ ...f, priority: 'medium' }))}
                  >
                    🟡 {lang === 'ar' ? 'متوسط' : 'Medium'}
                  </Button>
                  <Button
                    type="button"
                    variant={summonForm.priority === 'normal' ? 'default' : 'outline'}
                    className={`flex-1 ${summonForm.priority === 'normal' ? 'bg-green-500 hover:bg-green-600 text-white' : 'border-green-300 text-green-600 hover:bg-green-50'}`}
                    onClick={() => setSummonForm(f => ({ ...f, priority: 'normal' }))}
                  >
                    🟢 {lang === 'ar' ? 'عادي' : 'Normal'}
                  </Button>
                </div>
              </div>

              {/* التعليق */}
              <div className="space-y-2">
                <Label>{lang === 'ar' ? 'التعليق / السبب' : 'Comment / Reason'}</Label>
                <Textarea
                  value={summonForm.comment}
                  onChange={(e) => setSummonForm(f => ({ ...f, comment: e.target.value }))}
                  placeholder={lang === 'ar' ? 'أدخل سبب الاستدعاء (اختياري)...' : 'Enter reason for summon (optional)...'}
                  rows={3}
                />
              </div>

              {/* الأزرار */}
              <div className="flex gap-2 pt-2">
                <Button 
                  variant="outline" 
                  className="flex-1"
                  onClick={() => setSummonDialog(null)}
                >
                  {lang === 'ar' ? 'إلغاء' : 'Cancel'}
                </Button>
                <Button 
                  className="flex-1 bg-orange-500 hover:bg-orange-600 text-white"
                  onClick={handleSendSummon}
                  disabled={sendingSummon}
                  data-testid="send-summon-btn"
                >
                  {sendingSummon 
                    ? (lang === 'ar' ? 'جاري الإرسال...' : 'Sending...') 
                    : (lang === 'ar' ? 'إرسال الاستدعاء' : 'Send Summon')
                  }
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
