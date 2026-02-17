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
import { Users, Search, Edit2, UserCheck, Trash2, Key, Eye, EyeOff, User, AlertTriangle, Calendar, Briefcase, RefreshCw } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function EmployeesPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [employees, setEmployees] = useState([]);
  const [search, setSearch] = useState('');
  const [editDialog, setEditDialog] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);
  
  // حالات تعيين المشرف
  const [supervisorDialog, setSupervisorDialog] = useState(null);
  const [selectedSupervisor, setSelectedSupervisor] = useState('');
  const [savingSupervisor, setSavingSupervisor] = useState(false);
  
  // حالات بيانات الدخول
  const [credentialsDialog, setCredentialsDialog] = useState(null);
  const [credentialsForm, setCredentialsForm] = useState({ username: '', password: '' });
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  
  // حالة حذف الموظف
  const [deleteDialog, setDeleteDialog] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const isStas = user?.role === 'stas';
  const isOps = ['sultan', 'naif', 'stas'].includes(user?.role);

  useEffect(() => {
    api.get('/api/employees').then(r => setEmployees(r.data)).catch(() => {});
  }, []);

  const filtered = employees.filter(e => {
    if (!search) return true;
    const s = search.toLowerCase();
    return e.full_name?.toLowerCase().includes(s) || e.employee_number?.includes(s) || e.department?.toLowerCase().includes(s);
  });

  const openEdit = (emp) => {
    setEditForm({ full_name: emp.full_name, full_name_ar: emp.full_name_ar, is_active: emp.is_active });
    setEditDialog(emp);
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
      setCredentialsForm(f => ({ ...f, username: res.data.username || '' }));
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

  // حذف الموظف
  const openDeleteDialog = (emp) => {
    setDeleteDialog(emp);
  };

  const handleDelete = async () => {
    if (!deleteDialog) return;
    setDeleting(true);
    
    try {
      await api.delete(`/api/employees/${deleteDialog.id}`);
      toast.success(lang === 'ar' ? 'تم حذف الموظف' : 'Employee deleted');
      setDeleteDialog(null);
      api.get('/api/employees').then(r => setEmployees(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally {
      setDeleting(false);
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
                <th>ID</th>
                <th>{lang === 'ar' ? 'الاسم' : 'Name'}</th>
                <th className="hidden sm:table-cell">{lang === 'ar' ? 'القسم' : 'Department'}</th>
                <th className="hidden md:table-cell">{lang === 'ar' ? 'المشرف' : 'Supervisor'}</th>
                <th>{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                {isOps && <th>{lang === 'ar' ? 'الإجراءات' : 'Actions'}</th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map(e => (
                <tr key={e.id} data-testid={`emp-row-${e.employee_number}`}>
                  <td className="font-mono text-xs">{e.employee_number}</td>
                  <td className="text-sm font-medium">{lang === 'ar' ? (e.full_name_ar || e.full_name) : e.full_name}</td>
                  <td className="hidden sm:table-cell text-sm">{lang === 'ar' ? (e.department_ar || e.department) : e.department}</td>
                  <td className="hidden md:table-cell text-sm">{getSupervisorName(e)}</td>
                  <td>
                    <span className={`status-badge ${e.is_active ? 'status-executed' : 'status-rejected'}`}>
                      {e.is_active ? (lang === 'ar' ? 'نشط' : 'Active') : (lang === 'ar' ? 'غير نشط' : 'Inactive')}
                    </span>
                  </td>
                  {isOps && (
                    <td>
                      <div className="flex gap-1">
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-7 w-7 p-0" 
                          onClick={() => openSupervisorDialog(e)} 
                          data-testid={`assign-supervisor-${e.employee_number}`}
                          title={lang === 'ar' ? 'تعيين مشرف' : 'Assign Supervisor'}
                        >
                          <UserCheck size={14} />
                        </Button>
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
              ))}
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
                <p className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
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
            <DialogTitle className="text-destructive">{lang === 'ar' ? 'تأكيد الحذف' : 'Confirm Delete'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm">
              {lang === 'ar' 
                ? `هل أنت متأكد من حذف الموظف "${deleteDialog?.full_name_ar || deleteDialog?.full_name}"؟`
                : `Are you sure you want to delete employee "${deleteDialog?.full_name}"?`
              }
            </p>
            <p className="text-xs text-muted-foreground">
              {lang === 'ar' 
                ? 'ملاحظة: لا يمكن حذف موظف لديه عقد نشط. يجب إنهاء العقد أولاً.'
                : 'Note: Cannot delete employee with active contract. Must terminate contract first.'
              }
            </p>
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
                {deleting ? (lang === 'ar' ? 'جاري الحذف...' : 'Deleting...') : (lang === 'ar' ? 'حذف' : 'Delete')}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
