import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '@/lib/api';
import { FileSignature, Plus, Clock, CheckCircle, Archive, XCircle, Send, Play } from 'lucide-react';

import ContractWizard from './ContractWizard';
import ContractList from './ContractList';
import { CONTRACT_STATUS, TERMINATION_REASONS, formatCurrency } from './contractConstants';

export default function ContractsManagementPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const isRTL = lang === 'ar';
  
  const [contracts, setContracts] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('all');
  
  // Dialogs
  const [wizardOpen, setWizardOpen] = useState(false);
  const [editContract, setEditContract] = useState(null);
  const [viewContract, setViewContract] = useState(null);
  const [terminateContract, setTerminateContract] = useState(null);
  const [deleteContract, setDeleteContract] = useState(null);
  
  // Termination form
  const [terminationData, setTerminationData] = useState({
    termination_date: new Date().toISOString().split('T')[0],
    termination_reason: 'resignation',
    note: ''
  });
  
  const [actionLoading, setActionLoading] = useState(false);
  
  // Permissions
  const isAdmin = ['sultan', 'naif', 'stas'].includes(user?.role);
  const canCreate = isAdmin;
  const canEdit = isAdmin;
  const canExecute = isAdmin;
  const canTerminate = isAdmin;
  const canDelete = user?.role === 'stas';

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
      toast.error(isRTL ? 'فشل تحميل البيانات' : 'Failed to load data');
    }
    setLoading(false);
  };

  const handleSearch = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('q', searchQuery);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      
      const res = await api.get(`/api/contracts-v2/search?${params.toString()}`);
      setContracts(res.data || []);
    } catch (err) {
      toast.error(isRTL ? 'فشل البحث' : 'Search failed');
    }
  };

  // فلترة العقود حسب التبويب
  const filteredContracts = contracts.filter(c => {
    if (activeTab === 'all') return true;
    if (activeTab === 'pending') return ['draft', 'draft_correction', 'pending_stas'].includes(c.status);
    if (activeTab === 'active') return c.status === 'active';
    if (activeTab === 'closed') return ['terminated', 'closed'].includes(c.status);
    return true;
  });

  // إحصائيات سريعة
  const stats = {
    pending: contracts.filter(c => ['draft', 'draft_correction', 'pending_stas'].includes(c.status)).length,
    active: contracts.filter(c => c.status === 'active').length,
    closed: contracts.filter(c => ['terminated', 'closed'].includes(c.status)).length,
  };

  // إرسال للتنفيذ
  const handleSendToStas = async (contract) => {
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${contract.id}/submit`);
      toast.success(isRTL ? 'تم إرسال العقد لـ STAS' : 'Contract sent to STAS');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
    setActionLoading(false);
  };

  // تنفيذ العقد
  const handleExecute = async (contract) => {
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${contract.id}/execute`);
      toast.success(isRTL ? 'تم تنفيذ العقد بنجاح' : 'Contract executed successfully');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
    setActionLoading(false);
  };

  // إنهاء العقد
  const handleTerminate = async () => {
    if (!terminateContract) return;
    setActionLoading(true);
    try {
      await api.post(`/api/contracts-v2/${terminateContract.id}/terminate`, terminationData);
      toast.success(isRTL ? 'تم إنهاء العقد' : 'Contract terminated');
      setTerminateContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
    setActionLoading(false);
  };

  // حذف العقد
  const handleDelete = async () => {
    if (!deleteContract) return;
    setActionLoading(true);
    try {
      await api.delete(`/api/contracts-v2/${deleteContract.id}`);
      toast.success(isRTL ? 'تم حذف العقد' : 'Contract deleted');
      setDeleteContract(null);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
    setActionLoading(false);
  };

  return (
    <div className="space-y-6" dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <FileSignature size={24} className="text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{isRTL ? 'إدارة العقود' : 'Contracts Management'}</h1>
            <p className="text-sm text-muted-foreground">
              {isRTL ? 'إنشاء وإدارة عقود الموظفين' : 'Create and manage employee contracts'}
            </p>
          </div>
        </div>
        
        {canCreate && (
          <Button onClick={() => { setEditContract(null); setWizardOpen(true); }}>
            <Plus size={18} className="me-1" />
            {isRTL ? 'عقد جديد' : 'New Contract'}
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card-premium p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
            <Clock size={20} className="text-warning" />
          </div>
          <div>
            <p className="text-2xl font-bold">{stats.pending}</p>
            <p className="text-xs text-muted-foreground">{isRTL ? 'معلقة' : 'Pending'}</p>
          </div>
        </div>
        <div className="card-premium p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
            <CheckCircle size={20} className="text-success" />
          </div>
          <div>
            <p className="text-2xl font-bold">{stats.active}</p>
            <p className="text-xs text-muted-foreground">{isRTL ? 'نشطة' : 'Active'}</p>
          </div>
        </div>
        <div className="card-premium p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
            <Archive size={20} className="text-muted-foreground" />
          </div>
          <div>
            <p className="text-2xl font-bold">{stats.closed}</p>
            <p className="text-xs text-muted-foreground">{isRTL ? 'مغلقة' : 'Closed'}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="all">{isRTL ? 'الكل' : 'All'} ({contracts.length})</TabsTrigger>
          <TabsTrigger value="pending">{isRTL ? 'معلقة' : 'Pending'} ({stats.pending})</TabsTrigger>
          <TabsTrigger value="active">{isRTL ? 'نشطة' : 'Active'} ({stats.active})</TabsTrigger>
          <TabsTrigger value="closed">{isRTL ? 'مغلقة' : 'Closed'} ({stats.closed})</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          <ContractList
            contracts={filteredContracts}
            loading={loading}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            onSearch={handleSearch}
            onView={setViewContract}
            onEdit={(c) => { setEditContract(c); setWizardOpen(true); }}
            onExecute={handleExecute}
            onTerminate={setTerminateContract}
            onDelete={setDeleteContract}
            canEdit={canEdit}
            canExecute={canExecute}
            canTerminate={canTerminate}
            canDelete={canDelete}
          />
        </TabsContent>
      </Tabs>

      {/* Contract Wizard */}
      <ContractWizard
        isOpen={wizardOpen}
        onClose={() => { setWizardOpen(false); setEditContract(null); }}
        editContract={editContract}
        employees={employees}
        onSuccess={loadData}
      />

      {/* View Contract Dialog */}
      <Dialog open={!!viewContract} onOpenChange={() => setViewContract(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isRTL ? 'تفاصيل العقد' : 'Contract Details'}</DialogTitle>
          </DialogHeader>
          {viewContract && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'الرقم المرجعي' : 'Reference'}</p>
                  <p className="font-mono font-bold">{viewContract.contract_serial}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'الحالة' : 'Status'}</p>
                  <p className="font-bold">{isRTL ? CONTRACT_STATUS[viewContract.status]?.label : CONTRACT_STATUS[viewContract.status]?.labelEn}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'الموظف' : 'Employee'}</p>
                  <p className="font-bold">{isRTL ? viewContract.employee_name_ar : viewContract.employee_name}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'المسمى الوظيفي' : 'Job Title'}</p>
                  <p>{isRTL ? viewContract.job_title_ar : viewContract.job_title}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'القسم' : 'Department'}</p>
                  <p>{isRTL ? viewContract.department_ar : viewContract.department}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'تاريخ البداية' : 'Start Date'}</p>
                  <p>{viewContract.start_date}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'إجمالي الراتب' : 'Total Salary'}</p>
                  <p className="font-bold text-lg text-primary">{formatCurrency(viewContract.total_salary)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{isRTL ? 'البنك' : 'Bank'}</p>
                  <p>{viewContract.bank_name}</p>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-2 pt-4 border-t">
                {canEdit && ['draft', 'draft_correction'].includes(viewContract.status) && (
                  <>
                    <Button onClick={() => { setViewContract(null); setEditContract(viewContract); setWizardOpen(true); }}>
                      {isRTL ? 'تعديل' : 'Edit'}
                    </Button>
                    <Button variant="outline" onClick={() => handleSendToStas(viewContract)} disabled={actionLoading}>
                      <Send size={16} className="me-1" />
                      {isRTL ? 'إرسال لـ STAS' : 'Send to STAS'}
                    </Button>
                  </>
                )}
                {canExecute && viewContract.status === 'pending_stas' && (
                  <Button className="bg-success" onClick={() => handleExecute(viewContract)} disabled={actionLoading}>
                    <Play size={16} className="me-1" />
                    {isRTL ? 'تنفيذ' : 'Execute'}
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Terminate Dialog */}
      <Dialog open={!!terminateContract} onOpenChange={() => setTerminateContract(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{isRTL ? 'إنهاء العقد' : 'Terminate Contract'}</DialogTitle>
            <DialogDescription>
              {isRTL ? 'هذا الإجراء نهائي ولا يمكن التراجع عنه' : 'This action is permanent'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>{isRTL ? 'تاريخ الإنهاء' : 'Termination Date'}</Label>
              <Input 
                type="date"
                value={terminationData.termination_date}
                onChange={e => setTerminationData(d => ({ ...d, termination_date: e.target.value }))}
              />
            </div>
            <div>
              <Label>{isRTL ? 'سبب الإنهاء' : 'Reason'}</Label>
              <Select value={terminationData.termination_reason} onValueChange={v => setTerminationData(d => ({ ...d, termination_reason: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(TERMINATION_REASONS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{isRTL ? v.label : v.labelEn}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{isRTL ? 'ملاحظات' : 'Notes'}</Label>
              <Textarea 
                value={terminationData.note}
                onChange={e => setTerminationData(d => ({ ...d, note: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTerminateContract(null)}>
              {isRTL ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button variant="destructive" onClick={handleTerminate} disabled={actionLoading}>
              <XCircle size={16} className="me-1" />
              {isRTL ? 'تأكيد الإنهاء' : 'Confirm Termination'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteContract} onOpenChange={() => setDeleteContract(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{isRTL ? 'حذف العقد' : 'Delete Contract'}</DialogTitle>
            <DialogDescription>
              {isRTL ? 'هل أنت متأكد من حذف هذا العقد نهائياً؟' : 'Are you sure you want to permanently delete this contract?'}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteContract(null)}>
              {isRTL ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={actionLoading}>
              {isRTL ? 'حذف' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
