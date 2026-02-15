import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Users, Search, Edit2, UserCheck } from 'lucide-react';
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
      toast.success('Employee updated');
      setEditDialog(null);
      api.get('/api/employees').then(r => setEmployees(r.data));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setSaving(false); }
  };

  // تعيين المشرف
  const openSupervisorDialog = (emp) => {
    setSelectedSupervisor(emp.supervisor_id || '');
    setSupervisorDialog(emp);
  };

  const handleSaveSupervisor = async () => {
    if (!supervisorDialog) return;
    setSavingSupervisor(true);
    try {
      await api.put(`/api/employees/${supervisorDialog.id}/supervisor`, {
        supervisor_id: selectedSupervisor || null
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

  return (
    <div className="space-y-4" data-testid="employees-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{t('employees.title')}</h1>
      </div>

      <div className="relative">
        <Search size={16} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input data-testid="employee-search" value={search} onChange={e => setSearch(e.target.value)} placeholder={t('common.search')} className="ps-9" />
      </div>

      <div className="border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="hr-table" data-testid="employees-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>{t('employees.name')}</th>
                <th className="hidden sm:table-cell">{t('employees.department')}</th>
                <th className="hidden md:table-cell">{lang === 'ar' ? 'المشرف' : 'Supervisor'}</th>
                <th>{t('employees.status')}</th>
                {isOps && <th>{t('transactions.actions')}</th>}
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
                      {e.is_active ? t('employees.active') : t('employees.inactive')}
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
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(e)} data-testid={`edit-emp-${e.employee_number}`}>
                            <Edit2 size={14} />
                          </Button>
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
          <DialogHeader><DialogTitle>Edit Employee: {editDialog?.employee_number}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div><Label>Full Name (EN)</Label><Input data-testid="edit-name-en" value={editForm.full_name || ''} onChange={e => setEditForm(f => ({ ...f, full_name: e.target.value }))} /></div>
            <div><Label>Full Name (AR)</Label><Input data-testid="edit-name-ar" value={editForm.full_name_ar || ''} onChange={e => setEditForm(f => ({ ...f, full_name_ar: e.target.value }))} dir="rtl" /></div>
            <div className="flex items-center justify-between">
              <Label>Active</Label>
              <Switch data-testid="edit-active-toggle" checked={editForm.is_active} onCheckedChange={v => setEditForm(f => ({ ...f, is_active: v }))} />
            </div>
            <Button data-testid="save-employee" onClick={handleSave} className="w-full bg-primary text-primary-foreground" disabled={saving}>
              {saving ? t('common.loading') : t('common.save')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
