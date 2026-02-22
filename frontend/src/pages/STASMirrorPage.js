import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Shield, CheckCircle, XCircle, Link2, Loader2, Eye, Calendar, Trash2, AlertTriangle, Settings, UserX, RotateCcw, FileText, DollarSign, Clock, User, ChevronDown, ChevronUp, RefreshCw, Smartphone, Tablet, Monitor, Laptop, Download, X, Maximize2, ExternalLink, Tag, History } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { toast } from 'sonner';

// Theme colors for STAS Mirror
const THEME = {
  primary: '#6366f1',
  primaryLight: '#818cf8',
  primaryDark: '#4f46e5',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  dark: '#0f172a',
  darkSecondary: '#1e293b',
  muted: '#64748b',
};

export default function STASMirrorPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState([]);
  const [selectedTx, setSelectedTx] = useState(null);
  const [mirror, setMirror] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [loadingMirror, setLoadingMirror] = useState(false);
  
  // Cancel/Reject state
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelling, setCancelling] = useState(false);
  
  // Holiday management
  const [holidays, setHolidays] = useState([]);
  const [newHoliday, setNewHoliday] = useState({ name: '', name_ar: '', date: '' });
  const [holidayDialogOpen, setHolidayDialogOpen] = useState(false);
  
  // Maintenance
  const [purgeConfirm, setPurgeConfirm] = useState('');
  const [purging, setPurging] = useState(false);
  const [archivedUsers, setArchivedUsers] = useState([]);

  // === Deductions State ===
  const [pendingDeductions, setPendingDeductions] = useState([]);
  const [approvedDeductions, setApprovedDeductions] = useState([]);
  const [selectedDeduction, setSelectedDeduction] = useState(null);
  const [deductionTrace, setDeductionTrace] = useState(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewingDeduction, setReviewingDeduction] = useState(false);
  const [executingDeduction, setExecutingDeduction] = useState(false);
  const [expandedDeduction, setExpandedDeduction] = useState(null);

  // === Devices State ===
  const [devices, setDevices] = useState([]);
  const [pendingDevices, setPendingDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceAction, setDeviceAction] = useState(false);
  const [securityLogs, setSecurityLogs] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedEmployeeFilter, setSelectedEmployeeFilter] = useState('all');
  const [blockReason, setBlockReason] = useState('');

  // === My Transactions State ===
  const [myTransactions, setMyTransactions] = useState([]);
  const [deletingTransaction, setDeletingTransaction] = useState(null);

  // === PDF Preview State ===
  const [pdfPreviewOpen, setPdfPreviewOpen] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  // === Version Management State ===
  const [versionInfo, setVersionInfo] = useState(null);
  const [newVersion, setNewVersion] = useState('');
  const [releaseNotesAr, setReleaseNotesAr] = useState('');
  const [releaseNotesEn, setReleaseNotesEn] = useState('');
  const [updatingVersion, setUpdatingVersion] = useState(false);
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);

  // === Company Settings State ===
  const [companySettings, setCompanySettings] = useState({
    logo_url: null,
    side_image_url: null,
    pwa_icon_url: null,
    welcome_text_ar: 'أنتم الدار ونحن الكود',
    welcome_text_en: 'You are the Home, We are the Code',
    primary_color: '#1E3A5F',
    secondary_color: '#A78BFA',
    company_name_ar: 'شركة دار الأركان',
    company_name_en: 'Dar Al Arkan'
  });
  const [savingSettings, setSavingSettings] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingSideImage, setUploadingSideImage] = useState(false);
  const [uploadingPwaIcon, setUploadingPwaIcon] = useState(false);

  useEffect(() => {
    fetchPending();
    fetchHolidays();
    fetchArchivedUsers();
    fetchDeductions();
    fetchDevices();
    fetchEmployees();
    fetchMyTransactions();
    fetchVersion();
    fetchCompanySettings();
  }, []);

  const fetchPending = () => {
    api.get('/api/stas/pending').then(r => setPending(r.data)).catch(() => {});
  };

  const fetchHolidays = () => {
    api.get('/api/stas/holidays').then(r => setHolidays(r.data)).catch(() => {});
  };

  const fetchArchivedUsers = () => {
    api.get('/api/stas/users/archived').then(r => setArchivedUsers(r.data)).catch(() => {});
  };

  // === Version Management Functions ===
  const fetchVersion = async () => {
    try {
      const res = await api.get('/api/settings/version');
      setVersionInfo(res.data);
      setNewVersion(res.data.version || '1.0.0');
      setReleaseNotesAr(res.data.release_notes_ar || '');
      setReleaseNotesEn(res.data.release_notes_en || '');
    } catch (err) {
      console.error('Failed to fetch version:', err);
    }
  };

  const handleUpdateVersion = async () => {
    if (!newVersion.trim()) {
      toast.error(lang === 'ar' ? 'يرجى إدخال رقم الإصدار' : 'Please enter version number');
      return;
    }
    
    setUpdatingVersion(true);
    try {
      await api.put('/api/settings/version', {
        version: newVersion.trim(),
        release_notes_ar: releaseNotesAr.trim(),
        release_notes_en: releaseNotesEn.trim()
      });
      toast.success(lang === 'ar' ? 'تم تحديث الإصدار بنجاح' : 'Version updated successfully');
      setVersionDialogOpen(false);
      fetchVersion();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل تحديث الإصدار' : 'Failed to update version'));
    } finally {
      setUpdatingVersion(false);
    }
  };

  // === Company Settings Functions ===
  const fetchCompanySettings = async () => {
    try {
      const res = await api.get('/api/company-settings');
      setCompanySettings(prev => ({ ...prev, ...res.data }));
    } catch (err) {
      console.error('Failed to fetch company settings:', err);
    }
  };

  const handleSaveCompanySettings = async () => {
    setSavingSettings(true);
    try {
      await api.put('/api/company-settings', {
        welcome_text_ar: companySettings.welcome_text_ar,
        welcome_text_en: companySettings.welcome_text_en,
        primary_color: companySettings.primary_color,
        secondary_color: companySettings.secondary_color,
        company_name_ar: companySettings.company_name_ar,
        company_name_en: companySettings.company_name_en
      });
      toast.success(lang === 'ar' ? 'تم حفظ الإعدادات بنجاح' : 'Settings saved successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل حفظ الإعدادات' : 'Failed to save settings'));
    } finally {
      setSavingSettings(false);
    }
  };

  const handleUploadLogo = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadingLogo(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/api/company-settings/upload-logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCompanySettings(prev => ({ ...prev, logo_url: res.data.logo_url }));
      toast.success(lang === 'ar' ? 'تم رفع الشعار بنجاح' : 'Logo uploaded successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل رفع الشعار' : 'Failed to upload logo'));
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleUploadSideImage = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadingSideImage(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/api/company-settings/upload-side-image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCompanySettings(prev => ({ ...prev, side_image_url: res.data.side_image_url }));
      toast.success(lang === 'ar' ? 'تم رفع الصورة الجانبية بنجاح' : 'Side image uploaded successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل رفع الصورة' : 'Failed to upload image'));
    } finally {
      setUploadingSideImage(false);
    }
  };

  const handleDeleteLogo = async () => {
    try {
      await api.delete('/api/company-settings/logo');
      setCompanySettings(prev => ({ ...prev, logo_url: null }));
      toast.success(lang === 'ar' ? 'تم حذف الشعار' : 'Logo deleted');
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل حذف الشعار' : 'Failed to delete logo');
    }
  };

  const handleDeleteSideImage = async () => {
    try {
      await api.delete('/api/company-settings/side-image');
      setCompanySettings(prev => ({ ...prev, side_image_url: null }));
      toast.success(lang === 'ar' ? 'تم حذف الصورة' : 'Image deleted');
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل حذف الصورة' : 'Failed to delete image');
    }
  };

  // === PWA Icon Functions ===
  const handleUploadPwaIcon = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadingPwaIcon(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await api.post('/api/company-settings/upload-pwa-icon', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setCompanySettings(prev => ({ ...prev, pwa_icon_url: res.data.pwa_icon_url }));
      toast.success(lang === 'ar' ? 'تم رفع أيقونة التطبيق بنجاح! سيتم تحديثها تلقائياً.' : 'App icon uploaded! It will update automatically.');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل رفع الأيقونة' : 'Failed to upload icon'));
    } finally {
      setUploadingPwaIcon(false);
    }
  };

  const handleDeletePwaIcon = async () => {
    try {
      await api.delete('/api/company-settings/pwa-icon');
      setCompanySettings(prev => ({ ...prev, pwa_icon_url: null }));
      toast.success(lang === 'ar' ? 'تم حذف أيقونة التطبيق' : 'App icon deleted');
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل حذف الأيقونة' : 'Failed to delete icon');
    }
  };

  // === My Transactions Functions ===
  const fetchMyTransactions = async () => {
    try {
      // جلب معاملات STAS (EMP-STAS)
      const res = await api.get('/api/transactions');
      // فلترة المعاملات الخاصة بـ STAS
      const stasTransactions = res.data.filter(tx => 
        tx.employee_id === 'EMP-STAS' || 
        tx.created_by === 'stas' ||
        tx.requester_id === 'stas'
      );
      setMyTransactions(stasTransactions);
    } catch (err) {
      console.error('Failed to fetch my transactions:', err);
    }
  };

  const handleDeleteTransaction = async (transactionId) => {
    if (!confirm(lang === 'ar' ? 'هل أنت متأكد من حذف هذه المعاملة؟' : 'Are you sure you want to delete this transaction?')) return;
    
    setDeletingTransaction(transactionId);
    try {
      await api.delete(`/api/transactions/${transactionId}`);
      toast.success(lang === 'ar' ? 'تم حذف المعاملة بنجاح' : 'Transaction deleted successfully');
      fetchMyTransactions();
      fetchPending();
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'object') {
        toast.error(lang === 'ar' ? errorDetail.message_ar : errorDetail.message_en);
      } else {
        toast.error(errorDetail || (lang === 'ar' ? 'فشل حذف المعاملة' : 'Failed to delete transaction'));
      }
    } finally {
      setDeletingTransaction(null);
    }
  };

  const fetchEmployees = () => {
    api.get('/api/employees').then(r => {
      // عرض جميع الموظفين بما فيهم المدراء
      setEmployees(r.data);
    }).catch(() => {});
  };

  // === Devices Functions ===
  const fetchDevices = async () => {
    try {
      const [allRes, pendingRes, logsRes] = await Promise.all([
        api.get('/api/devices/all'),
        api.get('/api/devices/pending'),
        api.get('/api/devices/security-logs?limit=50')
      ]);
      setDevices(allRes.data);
      setPendingDevices(pendingRes.data);
      setSecurityLogs(logsRes.data);
    } catch (err) {
      console.error('Failed to fetch devices:', err);
    }
  };

  const handleApproveDevice = async (deviceId) => {
    setDeviceAction(true);
    try {
      await api.post(`/api/devices/${deviceId}/approve`);
      toast.success(lang === 'ar' ? 'تم اعتماد الجهاز' : 'Device approved');
      fetchDevices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve device');
    } finally {
      setDeviceAction(false);
    }
  };

  const handleBlockDevice = async (deviceId) => {
    setDeviceAction(true);
    try {
      await api.post(`/api/devices/${deviceId}/block`, { reason: blockReason });
      toast.success(lang === 'ar' ? 'تم حظر الجهاز' : 'Device blocked');
      setBlockReason('');
      fetchDevices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to block device');
    } finally {
      setDeviceAction(false);
    }
  };

  const handleDeleteDevice = async (deviceId) => {
    if (!confirm(lang === 'ar' ? 'هل أنت متأكد من حذف هذا الجهاز؟' : 'Are you sure you want to delete this device?')) return;
    setDeviceAction(true);
    try {
      await api.delete(`/api/devices/${deviceId}`);
      toast.success(lang === 'ar' ? 'تم حذف الجهاز' : 'Device deleted');
      fetchDevices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete device');
    } finally {
      setDeviceAction(false);
    }
  };

  const handleBlockAccount = async (employeeId) => {
    if (!confirm(lang === 'ar' ? 'هل أنت متأكد من إيقاف هذا الحساب؟' : 'Are you sure you want to block this account?')) return;
    setDeviceAction(true);
    try {
      await api.post(`/api/devices/account/${employeeId}/block`, { reason: blockReason });
      toast.success(lang === 'ar' ? 'تم إيقاف الحساب' : 'Account blocked');
      setBlockReason('');
      fetchDevices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to block account');
    } finally {
      setDeviceAction(false);
    }
  };

  const handleUnblockAccount = async (employeeId) => {
    setDeviceAction(true);
    try {
      await api.post(`/api/devices/account/${employeeId}/unblock`);
      toast.success(lang === 'ar' ? 'تم إلغاء إيقاف الحساب' : 'Account unblocked');
      fetchDevices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unblock account');
    } finally {
      setDeviceAction(false);
    }
  };

  const handleResetDevices = async (employeeId) => {
    if (!confirm(lang === 'ar' 
      ? 'هل أنت متأكد؟ سيتم حذف جميع أجهزة هذا الموظف وسيحتاج للتسجيل من جديد' 
      : 'Are you sure? All devices for this employee will be deleted')) return;
    setDeviceAction(true);
    try {
      const res = await api.post(`/api/devices/employee/${employeeId}/reset-devices`);
      toast.success(res.data.message_ar || 'Devices reset successfully');
      fetchDevices();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset devices');
    } finally {
      setDeviceAction(false);
    }
  };

  // === Deductions Functions ===
  const fetchDeductions = async () => {
    try {
      const [pendingRes, approvedRes] = await Promise.all([
        api.get('/api/attendance-engine/deductions/pending'),
        api.get('/api/attendance-engine/deductions/approved')
      ]);
      setPendingDeductions(pendingRes.data);
      setApprovedDeductions(approvedRes.data);
    } catch (err) {
      console.error('Failed to fetch deductions:', err);
    }
  };

  const loadDeductionTrace = async (deduction) => {
    setSelectedDeduction(deduction);
    setLoadingTrace(true);
    setDeductionTrace([]);
    try {
      // جلب العروق من daily_status
      const res = await api.get(`/api/attendance-engine/daily-status/${deduction.employee_id}/${deduction.period_start}`);
      if (res.data?.trace_log && Array.isArray(res.data.trace_log)) {
        setDeductionTrace(res.data.trace_log);
      }
    } catch (err) {
      console.error('Failed to load trace:', err);
      setDeductionTrace([]);
    } finally {
      setLoadingTrace(false);
    }
  };

  const executeDeduction = async (deduction) => {
    setExecutingDeduction(deduction.id);
    try {
      await api.post(`/api/attendance-engine/deductions/${deduction.id}/execute`, {
        note: reviewNote
      });
      toast.success(lang === 'ar' ? 'تم تنفيذ الخصم بنجاح' : 'Deduction executed successfully');
      setReviewNote('');
      setSelectedDeduction(null);
      fetchDeductions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to execute deduction');
    } finally {
      setExecutingDeduction(null);
    }
  };

  const handleReviewDeduction = async (proposalId, approved) => {
    setReviewingDeduction(true);
    try {
      await api.post(`/api/attendance-engine/deductions/${proposalId}/review`, {
        approved,
        note: reviewNote
      });
      toast.success(approved 
        ? (lang === 'ar' ? 'تمت الموافقة على مقترح الخصم' : 'Deduction proposal approved')
        : (lang === 'ar' ? 'تم رفض مقترح الخصم' : 'Deduction proposal rejected')
      );
      setReviewNote('');
      setSelectedDeduction(null);
      fetchDeductions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to review deduction');
    } finally {
      setReviewingDeduction(false);
    }
  };

  const handleExecuteDeduction = async (proposalId) => {
    setExecutingDeduction(true);
    try {
      await api.post(`/api/attendance-engine/deductions/${proposalId}/execute`, {
        note: reviewNote
      });
      toast.success(lang === 'ar' ? 'تم تنفيذ الخصم بنجاح' : 'Deduction executed successfully');
      setReviewNote('');
      setSelectedDeduction(null);
      fetchDeductions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to execute deduction');
    } finally {
      setExecutingDeduction(false);
    }
  };

  const loadMirror = async (txId) => {
    setLoadingMirror(true);
    try {
      const res = await api.get(`/api/stas/mirror/${txId}`);
      setMirror(res.data);
      setSelectedTx(txId);
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل تحميل المرآة' : 'Failed to load mirror');
    } finally { setLoadingMirror(false); }
  };

  const handleExecute = async () => {
    // منع التنفيذ المكرر
    if (!selectedTx || executing) return;
    
    // تحقق إضافي من حالة المعاملة
    if (mirror?.transaction?.status === 'executed') {
      toast.error(lang === 'ar' ? 'تم تنفيذ هذه المعاملة مسبقاً' : 'Transaction already executed');
      return;
    }
    
    setExecuting(true);
    try {
      const res = await api.post(`/api/stas/execute/${selectedTx}`);
      toast.success(`${res.data.ref_no} ${lang === 'ar' ? 'تم التنفيذ بنجاح' : 'executed successfully'}. Hash: ${res.data.pdf_hash?.slice(0, 12)}...`);
      // إعادة تعيين الحالة ومنع أي ضغط آخر
      setMirror(null);
      setSelectedTx(null);
      fetchPending();
    } catch (err) {
      // عرض رسالة الخطأ بشكل واضح
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'object') {
        toast.error(lang === 'ar' ? errorDetail.message_ar : errorDetail.message_en);
      } else {
        toast.error(errorDetail || (lang === 'ar' ? 'فشل التنفيذ' : 'Execution failed'));
      }
    } finally { 
      setExecuting(false); 
    }
  };

  // إلغاء المعاملة - يتطلب تعليق
  const handleCancelTransaction = async () => {
    if (!selectedTx || cancelling) return;
    
    if (!cancelReason || cancelReason.trim().length < 5) {
      toast.error(lang === 'ar' ? 'يجب كتابة سبب الإلغاء (5 أحرف على الأقل)' : 'Cancellation reason is required (at least 5 characters)');
      return;
    }
    
    setCancelling(true);
    try {
      await api.post(`/api/transactions/${selectedTx}/action`, {
        action: 'reject',
        note: cancelReason.trim()
      });
      toast.success(lang === 'ar' ? 'تم إلغاء المعاملة بنجاح' : 'Transaction cancelled successfully');
      setCancelDialogOpen(false);
      setCancelReason('');
      setMirror(null);
      setSelectedTx(null);
      fetchPending();
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      if (typeof errorDetail === 'object') {
        toast.error(lang === 'ar' ? errorDetail.message_ar : errorDetail.message_en);
      } else {
        toast.error(errorDetail || (lang === 'ar' ? 'فشل إلغاء المعاملة' : 'Failed to cancel transaction'));
      }
    } finally {
      setCancelling(false);
    }
  };

  const previewPdf = async (txId = null) => {
    const transactionId = txId || selectedTx;
    if (!transactionId) return;
    
    setPdfLoading(true);
    try {
      const res = await api.get(`/api/transactions/${transactionId}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      setPdfUrl(url);
      setPdfPreviewOpen(true);
    } catch {
      toast.error(lang === 'ar' ? 'فشل تحميل PDF' : 'PDF preview failed');
    } finally {
      setPdfLoading(false);
    }
  };

  const downloadPdf = () => {
    if (!pdfUrl) return;
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = `transaction_${selectedTx || 'document'}.pdf`;
    link.click();
  };

  const closePdfPreview = () => {
    setPdfPreviewOpen(false);
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
      setPdfUrl(null);
    }
  };

  const addHoliday = async () => {
    if (!newHoliday.name || !newHoliday.name_ar || !newHoliday.date) {
      toast.error(lang === 'ar' ? 'يرجى ملء جميع الحقول' : 'Please fill all fields');
      return;
    }
    try {
      await api.post('/api/stas/holidays', newHoliday);
      toast.success(lang === 'ar' ? 'تمت إضافة العطلة' : 'Holiday added');
      setNewHoliday({ name: '', name_ar: '', date: '' });
      setHolidayDialogOpen(false);
      fetchHolidays();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل الإضافة' : 'Failed to add'));
    }
  };

  const deleteHoliday = async (id) => {
    try {
      await api.delete(`/api/stas/holidays/${id}`);
      toast.success(lang === 'ar' ? 'تم حذف العطلة' : 'Holiday deleted');
      fetchHolidays();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل الحذف' : 'Failed to delete'));
    }
  };

  const purgeTransactions = async () => {
    if (purgeConfirm !== 'CONFIRM') {
      toast.error(t('stas.confirmPurge'));
      return;
    }
    setPurging(true);
    try {
      const res = await api.post('/api/stas/maintenance/purge-transactions', { confirm: true });
      toast.success(`${lang === 'ar' ? 'تم حذف المعاملات' : 'Transactions purged'}: ${res.data.deleted.transactions}`);
      setPurgeConfirm('');
      fetchPending();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    } finally { setPurging(false); }
  };

  const restoreUser = async (userId) => {
    try {
      await api.post(`/api/stas/users/${userId}/restore`);
      toast.success(lang === 'ar' ? 'تم استعادة المستخدم' : 'User restored');
      fetchArchivedUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const getStatusClass = (status) => {
    if (status === 'executed') return 'status-executed';
    if (status === 'rejected') return 'status-rejected';
    return 'status-pending';
  };

  // ترجمة مفاتيح الـ Before/After
  const translateKey = (key) => {
    const keyTranslations = {
      'total_entitlement': lang === 'ar' ? 'الاستحقاق الكلي' : 'Total Entitlement',
      'used': lang === 'ar' ? 'المستخدم' : 'Used',
      'remaining': lang === 'ar' ? 'المتبقي' : 'Remaining',
      'earned_to_date': lang === 'ar' ? 'المكتسب' : 'Earned to Date',
      'daily_accrual': lang === 'ar' ? 'الاستحقاق اليومي' : 'Daily Accrual',
      'days_worked': lang === 'ar' ? 'أيام العمل' : 'Days Worked',
      'annual_policy': lang === 'ar' ? 'سياسة الإجازة' : 'Annual Policy',
      'balance': lang === 'ar' ? 'الرصيد' : 'Balance',
      'amount': lang === 'ar' ? 'المبلغ' : 'Amount',
      'code': lang === 'ar' ? 'الكود' : 'Code',
      'type': lang === 'ar' ? 'النوع' : 'Type',
      'days': lang === 'ar' ? 'الأيام' : 'Days',
      'leave_type': lang === 'ar' ? 'نوع الإجازة' : 'Leave Type',
      'description': lang === 'ar' ? 'الوصف' : 'Description',
    };
    return keyTranslations[key] || key.replace(/_/g, ' ');
  };

  return (
    <div className="min-h-screen pb-24 md:pb-6" data-testid="stas-mirror-page">
      {/* Hero Header */}
      <div className="relative mb-8 rounded-2xl overflow-hidden" style={{ background: `linear-gradient(135deg, ${THEME.primaryDark} 0%, ${THEME.primary} 50%, ${THEME.primaryLight} 100%)` }}>
        <div className="absolute inset-0 bg-grid-white/[0.05]" />
        <div className="relative px-6 py-8 md:py-10">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shadow-lg">
              <Shield size={28} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
                {lang === 'ar' ? 'مرآة العمليات' : 'Operations Mirror'}
              </h1>
              <p className="text-white/70 text-sm mt-1">
                {lang === 'ar' ? 'مركز التحكم في العمليات والمعاملات' : 'Operations & Transactions Control Center'}
              </p>
            </div>
          </div>
          
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/20">
              <div className="flex items-center gap-2 text-white/70 text-xs mb-1">
                <DollarSign size={14} />
                {lang === 'ar' ? 'الخصومات المعلقة' : 'Pending Deductions'}
              </div>
              <p className="text-white text-xl font-bold">{pendingDeductions.length}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/20">
              <div className="flex items-center gap-2 text-white/70 text-xs mb-1">
                <Smartphone size={14} />
                {lang === 'ar' ? 'أجهزة جديدة' : 'New Devices'}
              </div>
              <p className="text-white text-xl font-bold">{pendingDevices.length}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/20">
              <div className="flex items-center gap-2 text-white/70 text-xs mb-1">
                <Clock size={14} />
                {lang === 'ar' ? 'معاملات معلقة' : 'Pending Transactions'}
              </div>
              <p className="text-white text-xl font-bold">{pending.length}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl px-4 py-3 border border-white/20">
              <div className="flex items-center gap-2 text-white/70 text-xs mb-1">
                <Calendar size={14} />
                {lang === 'ar' ? 'العطل' : 'Holidays'}
              </div>
              <p className="text-white text-xl font-bold">{holidays.length}</p>
            </div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="deductions" className="w-full">
        <TabsList className="grid w-full grid-cols-7 h-12 p-1 bg-slate-100 rounded-xl mb-6">
          <TabsTrigger value="deductions" data-testid="tab-deductions" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <DollarSign size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'الخصومات' : 'Deductions'}</span>
            {(pendingDeductions.length + approvedDeductions.length) > 0 && (
              <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                {pendingDeductions.length + approvedDeductions.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="devices" data-testid="tab-devices" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <Smartphone size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'الأجهزة' : 'Devices'}</span>
            {pendingDevices.length > 0 && (
              <span className="bg-warning text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                {pendingDevices.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="my-transactions" data-testid="tab-my-transactions" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <FileText size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'معاملاتي' : 'My Trans'}</span>
            {myTransactions.length > 0 && (
              <span className="bg-blue-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                {myTransactions.length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="mirror" data-testid="tab-mirror" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <Eye size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'المرآة' : 'Mirror'}</span>
          </TabsTrigger>
          <TabsTrigger value="holidays" data-testid="tab-holidays" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <Calendar size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'العطل' : 'Holidays'}</span>
          </TabsTrigger>
          <TabsTrigger value="company-settings" data-testid="tab-company-settings" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <Shield size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'الهوية' : 'Branding'}</span>
          </TabsTrigger>
          <TabsTrigger value="maintenance" data-testid="tab-maintenance" className="rounded-lg flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-md transition-all">
            <Settings size={16} />
            <span className="hidden sm:inline">{lang === 'ar' ? 'صيانة' : 'Maintenance'}</span>
          </TabsTrigger>
        </TabsList>

        {/* === Devices Tab === */}
        <TabsContent value="devices" className="mt-4">
          <div className="space-y-6">
            {/* Pending Devices Alert - تنبيه الأجهزة المعلقة */}
            {pendingDevices.length > 0 && (
              <div className="bg-gradient-to-r from-[hsl(var(--warning)/0.1)] to-[hsl(var(--warning)/0.1)] border-2 border-[hsl(var(--warning)/0.3)] rounded-xl p-5 shadow-sm">
                <h3 className="font-bold text-[hsl(var(--warning))] flex items-center gap-2 mb-4 text-lg">
                  <AlertTriangle size={22} className="text-[hsl(var(--warning))]" />
                  {lang === 'ar' ? 'أجهزة تحتاج موافقتك' : 'Devices Need Your Approval'}
                  <span className="bg-[hsl(var(--warning))] text-white text-sm px-2 py-0.5 rounded-full mr-2">
                    {pendingDevices.length}
                  </span>
                </h3>
                <div className="grid gap-3">
                  {pendingDevices.map(device => {
                    const DeviceIcon = device.is_mobile ? Smartphone : device.is_tablet ? Tablet : Monitor;
                    return (
                      <div key={device.id} className="flex items-center justify-between bg-white p-4 rounded-xl border-2 border-[hsl(var(--warning)/0.3)] hover:border-[hsl(var(--warning)/0.4)] transition-all shadow-sm">
                        <div className="flex items-center gap-4">
                          <div className="w-14 h-14 rounded-xl bg-[hsl(var(--warning)/0.15)] flex items-center justify-center">
                            <DeviceIcon size={28} className="text-[hsl(var(--warning))]" />
                          </div>
                          <div>
                            <p className="font-bold text-lg text-slate-800">{device.employee_name_ar || device.employee_id}</p>
                            <p className="text-base font-medium text-[hsl(var(--warning))]">
                              {device.friendly_name || `${device.browser} - ${device.os}`}
                            </p>
                            <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
                              <Calendar size={14} />
                              {new Date(device.registered_at).toLocaleString('ar-EG')}
                            </p>
                          </div>
                        </div>
                        <div className="flex gap-3">
                          <Button
                            size="lg"
                            onClick={() => handleApproveDevice(device.id)}
                            disabled={deviceAction}
                            className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 text-base font-bold rounded-xl shadow-md hover:shadow-lg transition-all"
                            data-testid={`approve-device-${device.id}`}
                          >
                            <CheckCircle size={20} className="ml-2" />
                            {lang === 'ar' ? 'موافقة' : 'Approve'}
                          </Button>
                          <Button
                            size="lg"
                            variant="destructive"
                            onClick={() => handleBlockDevice(device.id)}
                            disabled={deviceAction}
                            className="px-6 py-3 text-base font-bold rounded-xl shadow-md hover:shadow-lg transition-all"
                            data-testid={`reject-device-${device.id}`}
                          >
                            <XCircle size={20} className="ml-2" />
                            {lang === 'ar' ? 'رفض' : 'Reject'}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Employee Filter & Device Controls */}
            <Card className="border-2 border-slate-200">
              <CardHeader className="bg-slate-50">
                <CardTitle className="flex items-center gap-2">
                  <User size={22} />
                  {lang === 'ar' ? 'إدارة الموظفين والأجهزة' : 'Employee & Device Management'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-base font-semibold">{lang === 'ar' ? 'اختر موظف' : 'Select Employee'}</Label>
                    <select
                      className="w-full mt-2 p-3 border-2 rounded-xl text-base focus:border-blue-500 focus:outline-none"
                      value={selectedEmployeeFilter}
                      onChange={(e) => setSelectedEmployeeFilter(e.target.value)}
                      data-testid="employee-filter-select"
                    >
                      <option value="all">{lang === 'ar' ? 'جميع الموظفين' : 'All Employees'}</option>
                      {employees.map(emp => (
                        <option key={emp.id} value={emp.id}>{emp.full_name_ar || emp.full_name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-base font-semibold">{lang === 'ar' ? 'سبب الإجراء (اختياري)' : 'Action Reason (optional)'}</Label>
                    <Input
                      value={blockReason}
                      onChange={(e) => setBlockReason(e.target.value)}
                      placeholder={lang === 'ar' ? 'أدخل السبب...' : 'Enter reason...'}
                      className="mt-2 p-3 text-base"
                    />
                  </div>
                </div>
                
                {/* Action Buttons Grid */}
                {selectedEmployeeFilter !== 'all' && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t">
                    <Button
                      variant="destructive"
                      onClick={() => handleBlockAccount(selectedEmployeeFilter)}
                      disabled={deviceAction}
                      className="h-12 text-base font-bold"
                      data-testid="block-account-btn"
                    >
                      <UserX size={18} className="ml-2" />
                      {lang === 'ar' ? 'إيقاف الحساب' : 'Block Account'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleUnblockAccount(selectedEmployeeFilter)}
                      disabled={deviceAction}
                      className="h-12 text-base font-bold border-green-300 text-green-700 hover:bg-green-50"
                      data-testid="unblock-account-btn"
                    >
                      <CheckCircle size={18} className="ml-2" />
                      {lang === 'ar' ? 'تفعيل الحساب' : 'Activate'}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleResetDevices(selectedEmployeeFilter)}
                      disabled={deviceAction}
                      className="h-12 text-base font-bold border-[hsl(var(--warning)/0.3)] text-[hsl(var(--warning))] hover:bg-[hsl(var(--warning)/0.1)]"
                      data-testid="reset-devices-btn"
                    >
                      <RotateCcw size={18} className="ml-2" />
                      {lang === 'ar' ? 'إعادة تعيين الأجهزة' : 'Reset Devices'}
                    </Button>
                  </div>
                )}
                
                {selectedEmployeeFilter === 'all' && (
                  <div className="text-center py-4 text-slate-500 bg-slate-50 rounded-lg">
                                        {lang === 'ar' ? 'اختر موظفاً لإدارة حسابه وأجهزته' : 'Select an employee to manage their account and devices'}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Devices Grid - عرض الأجهزة ككروت */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Laptop size={22} />
                    {lang === 'ar' ? 'أجهزة الموظفين' : 'Employee Devices'}
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-normal bg-slate-100 px-3 py-1 rounded-full">
                      {devices.filter(d => selectedEmployeeFilter === 'all' || d.employee_id === selectedEmployeeFilter).length} {lang === 'ar' ? 'جهاز' : 'devices'}
                    </span>
                    <Button variant="outline" size="sm" onClick={() => fetchDevices()} data-testid="refresh-devices-btn">
                      <RefreshCw size={14} className="ml-1" />
                      {lang === 'ar' ? 'تحديث' : 'Refresh'}
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {devices.length === 0 ? (
                  <div className="text-center py-12 space-y-4">
                    <div className="w-20 h-20 mx-auto bg-slate-100 rounded-full flex items-center justify-center">
                      <Smartphone size={40} className="text-slate-400" />
                    </div>
                    <p className="text-lg font-medium text-slate-600">
                      {lang === 'ar' ? 'لا توجد أجهزة مسجلة حالياً' : 'No devices registered yet'}
                    </p>
                    <p className="text-sm text-slate-500 max-w-md mx-auto">
                      {lang === 'ar' 
                        ? 'يتم تسجيل الأجهزة تلقائياً عند أول تسجيل دخول لكل موظف'
                        : 'Devices are registered automatically on first login'}
                    </p>
                  </div>
                ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {devices
                    .filter(d => selectedEmployeeFilter === 'all' || d.employee_id === selectedEmployeeFilter)
                    .map(device => {
                      const DeviceIcon = device.is_mobile ? Smartphone : device.is_tablet ? Tablet : Monitor;
                      const statusColors = {
                        trusted: 'border-green-400 bg-green-50',
                        pending: 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)]',
                        blocked: 'border-red-400 bg-red-50'
                      };
                      const statusBadge = {
                        trusted: 'bg-green-500 text-white',
                        pending: 'bg-warning text-white',
                        blocked: 'bg-red-500 text-white'
                      };
                      const statusText = {
                        trusted: lang === 'ar' ? 'موثوق' : 'Trusted',
                        pending: lang === 'ar' ? 'معلق' : 'Pending',
                        blocked: lang === 'ar' ? 'محظور' : 'Blocked'
                      };
                      
                      return (
                        <div 
                          key={device.id} 
                          className={`rounded-xl border-2 p-4 transition-all hover:shadow-md ${statusColors[device.status] || 'border-slate-200'}`}
                          data-testid={`device-card-${device.id}`}
                        >
                          {/* Header */}
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                                device.status === 'trusted' ? 'bg-green-100' :
                                device.status === 'pending' ? 'bg-[hsl(var(--warning)/0.15)]' : 'bg-red-100'
                              }`}>
                                <DeviceIcon size={24} className={
                                  device.status === 'trusted' ? 'text-green-600' :
                                  device.status === 'pending' ? 'text-[hsl(var(--warning))]' : 'text-red-600'
                                } />
                              </div>
                              <div>
                                <p className="font-bold text-slate-800">{device.employee_name_ar || device.employee_id}</p>
                                <p className="text-xs text-slate-500">#{device.employee_number || '-'}</p>
                              </div>
                            </div>
                            <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${statusBadge[device.status]}`}>
                              {statusText[device.status]}
                            </span>
                          </div>
                          
                          {/* Device Info */}
                          <div className="space-y-2 mb-4">
                            <div className="bg-white/70 rounded-lg p-3">
                              <p className="text-base font-semibold text-slate-700">
                                {device.friendly_name || device.device_type}
                              </p>
                              <p className="text-sm text-slate-500">
                                {device.browser} • {device.os_display || device.os}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                              <Clock size={12} />
                              <span>{lang === 'ar' ? 'آخر استخدام:' : 'Last used:'}</span>
                              <span className="font-medium">{new Date(device.last_used_at).toLocaleDateString('ar-EG')}</span>
                            </div>
                          </div>
                          
                          {/* Actions */}
                          <div className="flex gap-2 pt-3 border-t border-slate-200">
                            {device.status === 'pending' && (
                              <Button 
                                size="sm" 
                                onClick={() => handleApproveDevice(device.id)}
                                disabled={deviceAction}
                                className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                                data-testid={`approve-btn-${device.id}`}
                              >
                                <CheckCircle size={14} className="ml-1" />
                                {lang === 'ar' ? 'موافقة' : 'Approve'}
                              </Button>
                            )}
                            {device.status !== 'blocked' && (
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => handleBlockDevice(device.id)}
                                disabled={deviceAction}
                                className="flex-1 border-[hsl(var(--warning)/0.3)] text-[hsl(var(--warning))] hover:bg-[hsl(var(--warning)/0.1)]"
                                data-testid={`block-btn-${device.id}`}
                              >
                                <XCircle size={14} className="ml-1" />
                                {lang === 'ar' ? 'حظر' : 'Block'}
                              </Button>
                            )}
                            {device.status === 'blocked' && (
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => handleApproveDevice(device.id)}
                                disabled={deviceAction}
                                className="flex-1 border-green-300 text-green-600 hover:bg-green-50"
                              >
                                <RotateCcw size={14} className="ml-1" />
                                {lang === 'ar' ? 'إلغاء الحظر' : 'Unblock'}
                              </Button>
                            )}
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => handleDeleteDevice(device.id)}
                              disabled={deviceAction}
                              className="text-red-500 hover:bg-red-50"
                              data-testid={`delete-btn-${device.id}`}
                            >
                              <Trash2 size={14} />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                </div>
                )}
              </CardContent>
            </Card>

            {/* Security Audit Log */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText size={20} />
                  {lang === 'ar' ? 'سجل الأمان' : 'Security Audit Log'}
                  <span className="text-sm font-normal text-muted-foreground">({securityLogs.length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {securityLogs.length === 0 ? (
                  <p className="text-center text-muted-foreground py-4">
                    {lang === 'ar' ? 'لا توجد سجلات أمان' : 'No security logs'}
                  </p>
                ) : (
                  <div className="max-h-[400px] overflow-y-auto space-y-2">
                    {securityLogs.map(log => {
                      const emp = employees.find(e => e.id === log.employee_id);
                      const empName = emp ? (emp.full_name_ar || emp.full_name) : log.employee_id;
                      return (
                        <div key={log.id} className="p-3 bg-slate-50 rounded-lg text-sm border-r-4" style={{
                          borderRightColor: log.action.includes('block') ? '#dc2626' : 
                                           log.action.includes('unblock') ? '#16a34a' :
                                           log.action.includes('approve') ? '#2563eb' : '#9ca3af'
                        }}>
                          <div className="flex items-center justify-between">
                            <span className={`font-medium ${
                              log.action.includes('block') && !log.action.includes('unblock') ? 'text-red-600' :
                              log.action.includes('unblock') ? 'text-green-600' :
                              log.action.includes('approve') ? 'text-blue-600' :
                              'text-gray-600'
                            }`}>
                              {log.action === 'account_blocked' ? (lang === 'ar' ? 'إيقاف حساب' : 'Account Blocked') :
                               log.action === 'account_unblocked' ? (lang === 'ar' ? 'إلغاء إيقاف' : 'Account Unblocked') :
                               log.action === 'device_approved' ? (lang === 'ar' ? 'اعتماد جهاز' : 'Device Approved') :
                               log.action === 'device_blocked' ? (lang === 'ar' ? 'حظر جهاز' : 'Device Blocked') :
                               log.action.replace(/_/g, ' ')}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {new Date(log.timestamp).toLocaleString('ar-EG')}
                            </span>
                          </div>
                          <p className="text-muted-foreground mt-1">
                            <span className="font-medium">{empName}</span>
                            {log.details?.reason && <span className="mx-2">|</span>}
                            {log.details?.reason && <span className="text-xs">{log.details.reason}</span>}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* === My Transactions Tab - معاملاتي === */}
        <TabsContent value="my-transactions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileText size={20} />
                  {lang === 'ar' ? 'معاملاتي الخاصة' : 'My Transactions'}
                </span>
                <span className="text-sm font-normal text-muted-foreground">
                  {myTransactions.length} {lang === 'ar' ? 'معاملة' : 'transactions'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {myTransactions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText size={48} className="mx-auto mb-3 opacity-30" />
                  <p>{lang === 'ar' ? 'لا توجد معاملات خاصة بك' : 'No transactions found'}</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-slate-50">
                        <th className="p-3 text-right">{lang === 'ar' ? 'الرقم المرجعي' : 'Ref No'}</th>
                        <th className="p-3 text-right">{lang === 'ar' ? 'النوع' : 'Type'}</th>
                        <th className="p-3 text-right">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                        <th className="p-3 text-right">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                        <th className="p-3 text-center">{lang === 'ar' ? 'إجراءات' : 'Actions'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {myTransactions.map(tx => (
                        <tr key={tx.id} className="border-b hover:bg-slate-50">
                          <td className="p-3 font-mono text-xs">{tx.ref_no}</td>
                          <td className="p-3 capitalize">{tx.type?.replace(/_/g, ' ')}</td>
                          <td className="p-3">
                            <span className={`px-2 py-1 rounded-full text-xs ${
                              tx.status === 'executed' ? 'bg-green-100 text-green-700' :
                              tx.status === 'rejected' || tx.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                              'bg-blue-100 text-blue-700'
                            }`}>
                              {tx.status === 'executed' ? (lang === 'ar' ? 'منفذة' : 'Executed') :
                               tx.status === 'rejected' ? (lang === 'ar' ? 'مرفوضة' : 'Rejected') :
                               tx.status === 'cancelled' ? (lang === 'ar' ? 'ملغاة' : 'Cancelled') :
                               (lang === 'ar' ? 'معلقة' : 'Pending')}
                            </span>
                          </td>
                          <td className="p-3 text-xs text-muted-foreground">
                            {new Date(tx.created_at).toLocaleDateString('ar-EG')}
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex justify-center gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => navigate(`/transactions/${tx.id}`)}
                                data-testid={`view-tx-${tx.ref_no}`}
                              >
                                <Eye size={14} />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteTransaction(tx.id)}
                                disabled={deletingTransaction === tx.id}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                data-testid={`delete-tx-${tx.ref_no}`}
                              >
                                {deletingTransaction === tx.id ? (
                                  <Loader2 size={14} className="animate-spin" />
                                ) : (
                                  <Trash2 size={14} />
                                )}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === Deductions Tab === */}
        <TabsContent value="deductions" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <DollarSign size={20} className="text-red-500" />
                  {lang === 'ar' ? 'الخصومات المقترحة' : 'Deduction Proposals'}
                </CardTitle>
                <div className="flex gap-2">
                  <span className="px-3 py-1 bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] rounded-full text-sm">
                    {lang === 'ar' ? 'معلقة' : 'Pending'}: {pendingDeductions.length}
                  </span>
                  <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                    {lang === 'ar' ? 'موافق عليها' : 'Approved'}: {approvedDeductions.length}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Deductions Table */}
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'الموظف' : 'Employee'}</th>
                      <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'النوع' : 'Type'}</th>
                      <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'المبلغ' : 'Amount'}</th>
                      <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                      <th className="p-3 text-center font-semibold">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                      <th className="p-3 text-center font-semibold">{lang === 'ar' ? 'إجراءات' : 'Actions'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...pendingDeductions, ...approvedDeductions].length === 0 ? (
                      <tr>
                        <td colSpan={6} className="p-8 text-center text-muted-foreground">
                          <DollarSign size={40} className="mx-auto mb-2 opacity-30" />
                          {lang === 'ar' ? 'لا توجد خصومات مقترحة' : 'No deduction proposals'}
                        </td>
                      </tr>
                    ) : (
                      [...pendingDeductions, ...approvedDeductions].map(d => (
                        <tr 
                          key={d.id} 
                          className={`border-b hover:bg-slate-50 cursor-pointer transition-colors ${
                            selectedDeduction?.id === d.id ? 'bg-blue-50' : ''
                          }`}
                          onClick={() => loadDeductionTrace(d)}
                        >
                          <td className="p-3">
                            <div className="font-medium">{d.employee_name || d.employee_name_ar || d.employee_id}</div>
                          </td>
                          <td className="p-3">
                            <span className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs">
                              {d.deduction_type_ar || d.deduction_type}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className="font-bold text-red-600">{d.amount?.toFixed(2)} ر.س</span>
                          </td>
                          <td className="p-3 text-muted-foreground text-xs">{d.period_start}</td>
                          <td className="p-3 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs ${
                              d.status === 'pending' 
                                ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]' 
                                : 'bg-green-100 text-green-700'
                            }`}>
                              {d.status === 'pending' 
                                ? (lang === 'ar' ? 'معلق' : 'Pending')
                                : (lang === 'ar' ? 'موافق' : 'Approved')}
                            </span>
                          </td>
                          <td className="p-3 text-center">
                            <div className="flex justify-center gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={(e) => { e.stopPropagation(); loadDeductionTrace(d); }}
                                className="h-8 w-8 p-0"
                                title={lang === 'ar' ? 'عرض التفاصيل' : 'View Details'}
                              >
                                <Eye size={14} />
                              </Button>
                              {d.status === 'approved' && (
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={(e) => { e.stopPropagation(); executeDeduction(d); }}
                                  disabled={executingDeduction === d.id}
                                  className="h-8 bg-green-600 hover:bg-green-700"
                                  title={lang === 'ar' ? 'تنفيذ' : 'Execute'}
                                >
                                  {executingDeduction === d.id ? (
                                    <Loader2 size={14} className="animate-spin" />
                                  ) : (
                                    <CheckCircle size={14} />
                                  )}
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Selected Deduction Details Panel */}
              {selectedDeduction && (
                <div className="mt-6 p-4 bg-slate-50 rounded-lg border">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold flex items-center gap-2">
                      <DollarSign size={18} className="text-red-500" />
                      {lang === 'ar' ? 'تفاصيل الخصم' : 'Deduction Details'}
                    </h3>
                    <Button variant="ghost" size="sm" onClick={() => setSelectedDeduction(null)}>
                      <XCircle size={16} />
                    </Button>
                  </div>
                  
                  {/* Info Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="p-3 bg-white rounded border">
                      <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الموظف' : 'Employee'}</p>
                      <p className="font-medium">{selectedDeduction.employee_name || selectedDeduction.employee_name_ar}</p>
                    </div>
                    <div className="p-3 bg-white rounded border">
                      <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'النوع' : 'Type'}</p>
                      <p className="font-medium">{selectedDeduction.deduction_type_ar}</p>
                    </div>
                    <div className="p-3 bg-white rounded border">
                      <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'المبلغ' : 'Amount'}</p>
                      <p className="font-bold text-red-600 text-lg">{selectedDeduction.amount?.toFixed(2)} ر.س</p>
                    </div>
                    <div className="p-3 bg-white rounded border">
                      <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'الفترة' : 'Period'}</p>
                      <p className="font-medium">{selectedDeduction.period_start}</p>
                    </div>
                  </div>

                  {/* Reason */}
                  <div className="p-3 bg-red-50 rounded border border-red-200 mb-4">
                    <p className="text-xs font-semibold text-red-700 mb-1">{lang === 'ar' ? 'السبب' : 'Reason'}</p>
                    <p className="text-sm">{selectedDeduction.reason_ar || selectedDeduction.reason}</p>
                  </div>

                  {/* Trace Log Toggle */}
                  <button
                    onClick={() => setExpandedDeduction(expandedDeduction === selectedDeduction.id ? null : selectedDeduction.id)}
                    className="w-full p-3 bg-accent/10 rounded flex items-center justify-between hover:bg-accent/15 transition-colors"
                  >
                    <span className="font-semibold text-accent flex items-center gap-2">
                      <Eye size={16} />
                      {lang === 'ar' ? 'العروق - سجل الفحوصات' : 'Trace Log'}
                      {deductionTrace.length > 0 && <span className="text-xs">({deductionTrace.length})</span>}
                    </span>
                    {expandedDeduction === selectedDeduction.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  
                  {expandedDeduction === selectedDeduction.id && (
                    <div className="mt-3 space-y-2 max-h-[300px] overflow-y-auto">
                      {loadingTrace ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="animate-spin" size={20} />
                        </div>
                      ) : deductionTrace.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-4">
                          {lang === 'ar' ? 'لا يوجد سجل فحوصات' : 'No trace log available'}
                        </p>
                      ) : (
                        deductionTrace.map((check, i) => (
                          <div 
                            key={i} 
                            className={`p-3 rounded-lg border ${
                              check.found 
                                ? 'bg-green-50 border-green-200' 
                                : check.checked 
                                  ? 'bg-slate-50 border-slate-200'
                                  : 'bg-gray-50 border-gray-200'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-sm flex items-center gap-2">
                                {check.found ? (
                                  <CheckCircle className="text-green-500" size={14} />
                                ) : check.checked ? (
                                  <XCircle className="text-slate-400" size={14} />
                                ) : (
                                  <Clock className="text-gray-400" size={14} />
                                )}
                                {check.step_ar || check.step}
                              </span>
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                check.found 
                                  ? 'bg-green-100 text-green-700' 
                                  : check.checked 
                                    ? 'bg-slate-100 text-slate-600'
                                    : 'bg-gray-100 text-gray-500'
                              }`}>
                                {check.found 
                                  ? (lang === 'ar' ? 'وُجد' : 'Found')
                                  : check.checked 
                                    ? (lang === 'ar' ? 'لم يُوجد' : 'Not found')
                                    : (lang === 'ar' ? 'لم يُفحص' : 'Not checked')}
                              </span>
                            </div>
                            {check.details && (
                              <div className="mt-2 text-xs text-muted-foreground">
                                {typeof check.details === 'object' 
                                  ? Object.entries(check.details).slice(0, 4).map(([k, v]) => (
                                      <span key={k} className="mr-3 inline-block">{k}: <strong>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</strong></span>
                                    ))
                                  : check.details}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="mt-4 pt-4 border-t space-y-3">
                    <div>
                      <Label>{lang === 'ar' ? 'ملاحظة (اختياري)' : 'Note (optional)'}</Label>
                      <Input
                        value={reviewNote}
                        onChange={(e) => setReviewNote(e.target.value)}
                        placeholder={lang === 'ar' ? 'أضف ملاحظة...' : 'Add a note...'}
                        className="mt-1"
                      />
                    </div>
                    
                    {/* أزرار المراجعة - sultan/naif فقط */}
                    {selectedDeduction.status === 'pending' && ['sultan', 'naif'].includes(user?.role) && (
                      <div className="flex gap-3">
                        <Button
                          onClick={() => handleReviewDeduction(selectedDeduction.id, true)}
                          disabled={reviewingDeduction}
                          className="flex-1 bg-green-600 hover:bg-green-700"
                        >
                          {reviewingDeduction ? <Loader2 className="animate-spin mr-2" size={16} /> : <CheckCircle size={16} className="mr-2" />}
                          {lang === 'ar' ? 'موافقة' : 'Approve'}
                        </Button>
                        <Button
                          onClick={() => handleReviewDeduction(selectedDeduction.id, false)}
                          disabled={reviewingDeduction}
                          variant="destructive"
                          className="flex-1"
                        >
                          {reviewingDeduction ? <Loader2 className="animate-spin mr-2" size={16} /> : <XCircle size={16} className="mr-2" />}
                          {lang === 'ar' ? 'رفض' : 'Reject'}
                        </Button>
                      </div>
                    )}
                    
                    {/* رسالة للـ STAS عندما يكون الخصم معلق */}
                    {selectedDeduction.status === 'pending' && user?.role === 'stas' && (
                      <div className="p-3 bg-[hsl(var(--warning)/0.1)] rounded-lg border border-[hsl(var(--warning)/0.3)] text-center">
                        <p className="text-sm text-[hsl(var(--warning))]">
                          {lang === 'ar' ? 'بانتظار مراجعة المدير (سلطان/نايف)' : 'Waiting for manager review (Sultan/Naif)'}
                        </p>
                      </div>
                    )}
                    
                    {/* زر التنفيذ - STAS فقط للموافق عليها */}
                    {selectedDeduction.status === 'approved' && user?.role === 'stas' && (
                      <Button
                        onClick={() => executeDeduction(selectedDeduction)}
                        disabled={executingDeduction === selectedDeduction.id}
                        className="w-full bg-accent hover:bg-accent"
                      >
                        {executingDeduction === selectedDeduction.id ? (
                          <><Loader2 className="animate-spin mr-2" size={16} /> {lang === 'ar' ? 'جاري التنفيذ...' : 'Executing...'}</>
                        ) : (
                          <><CheckCircle size={16} className="mr-2" /> {lang === 'ar' ? 'تنفيذ الخصم' : 'Execute Deduction'}</>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Mirror Tab */}
        <TabsContent value="mirror" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Pending List */}
            <div className="lg:col-span-1">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">{t('stas.pendingExecution')}</h2>
              <div className="space-y-2">
                {pending.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">{t('common.noData')}</p>
                ) : pending.map(tx => (
                  <button
                    key={tx.id}
                    data-testid={`stas-tx-${tx.ref_no}`}
                    onClick={() => loadMirror(tx.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedTx === tx.id ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-medium">{tx.ref_no}</span>
                      <span className={`status-badge ${getStatusClass(tx.status)}`}>{tx.status?.replace(/_/g, ' ')}</span>
                    </div>
                    <p className="text-sm mt-1 capitalize">{tx.type?.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-muted-foreground">{tx.data?.employee_name}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Mirror Detail */}
            <div className="lg:col-span-2">
              {loadingMirror ? (
                <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin text-muted-foreground" size={24} /></div>
              ) : !mirror ? (
                <div className="text-center py-12 text-muted-foreground">
                  <Shield size={48} className="mx-auto mb-3 opacity-30" />
                  <p>{t('stas.selectTransaction')}</p>
                </div>
              ) : (
                <div className="space-y-4 animate-fade-in">
                  {/* Transaction Summary */}
                  <Card className="border border-border shadow-none">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-mono">{mirror.transaction?.ref_no}</CardTitle>
                        <div className="flex gap-2">
                          <Button variant="ghost" size="sm" onClick={previewPdf} data-testid="mirror-preview-pdf">
                            <FileText size={14} className="me-1" /> {t('common.preview')}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/transactions/${mirror.transaction?.id}`)} data-testid="mirror-view-detail">
                            <Eye size={14} className="me-1" /> {t('transactions.viewDetail')}
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div><span className="text-muted-foreground">{t('transactions.type')}:</span> <span className="capitalize">{mirror.transaction?.type?.replace(/_/g, ' ')}</span></div>
                        <div><span className="text-muted-foreground">{t('transactions.employee')}:</span> {mirror.employee?.full_name || '-'}</div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Pre-Checks */}
                  <Card className="border border-border shadow-none" data-testid="pre-checks-card">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        {mirror.all_checks_pass ? <CheckCircle size={16} className="text-[hsl(var(--success))]" /> : <XCircle size={16} className="text-red-500" />}
                        {t('stas.preChecks')}
                        <span className={`ms-auto text-xs ${mirror.all_checks_pass ? 'text-[hsl(var(--success))]' : 'text-red-600'}`}>
                          {mirror.all_checks_pass ? t('stas.allPass') : t('stas.hasFails')}
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {mirror.pre_checks?.map((c, i) => (
                          <div key={i} className={`p-2 rounded-md ${c.status === 'WARN' ? 'bg-[hsl(var(--warning)/0.1)] dark:bg-[hsl(var(--warning)/0.15)] border border-[hsl(var(--warning)/0.3)]' : 'bg-muted/50'}`} data-testid={`check-${i}`}>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                {c.status === 'PASS' ? <CheckCircle size={14} className="text-[hsl(var(--success))]" /> : c.status === 'WARN' ? <AlertTriangle size={14} className="text-[hsl(var(--warning))]" /> : <XCircle size={14} className="text-red-500" />}
                                <span className="text-sm">{lang === 'ar' ? c.name_ar : c.name}</span>
                              </div>
                              <span className={`text-xs font-bold ${c.status === 'PASS' ? 'text-[hsl(var(--success))]' : c.status === 'WARN' ? 'text-[hsl(var(--warning))]' : 'text-red-600'}`}>
                                {c.status === 'PASS' ? (lang === 'ar' ? 'نجح' : 'PASS') : c.status === 'WARN' ? (lang === 'ar' ? 'تحذير' : 'WARN') : (lang === 'ar' ? 'فشل' : 'FAIL')}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1">{c.detail}</p>
                            
                            {/* عرض تفاصيل الإجازة المرضية */}
                            {c.sick_leave_info && (
                              <div className="mt-2 p-2 bg-[hsl(var(--warning)/0.15)] dark:bg-[hsl(var(--warning)/0.2)] rounded text-xs space-y-1">
                                <div className="flex justify-between">
                                  <span>{lang === 'ar' ? 'الاستهلاك الحالي:' : 'Current usage:'}</span>
                                  <span className="font-bold">{c.sick_leave_info.current_used} / 120 {lang === 'ar' ? 'يوم' : 'days'}</span>
                                </div>
                                {c.sick_leave_info.tier_distribution?.map((tier, ti) => (
                                  <div key={ti} className={`p-1 rounded ${tier.salary_percent === 100 ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]' : tier.salary_percent === 50 ? 'bg-[hsl(var(--warning)/0.3)] text-[hsl(var(--warning))]' : 'bg-red-100 text-red-800'}`}>
                                    {tier.days} {lang === 'ar' ? 'يوم' : 'days'} → {tier.salary_percent === 100 ? (lang === 'ar' ? 'براتب كامل' : 'Full pay') : tier.salary_percent === 50 ? (lang === 'ar' ? 'نصف راتب' : 'Half pay') : (lang === 'ar' ? 'بدون راتب' : 'No pay')}
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* زر عرض الملف الطبي */}
                            {c.medical_file_url && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => window.open(c.medical_file_url, '_blank')}
                                className="mt-2 text-xs h-7 border-red-300 text-red-600"
                              >
                                <FileText size={12} className="me-1" />
                                {lang === 'ar' ? 'معاينة التقرير' : 'Preview Report'}
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Leave Calculation Details - سجل الإجازات - STAS فقط */}
                  {mirror.transaction?.type === 'leave_request' && mirror.transaction?.data?.calculation_details && (
                    <Card className="border-2 border-accent/30 shadow-none" data-testid="leave-calculation-card">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm flex items-center gap-2 text-accent dark:text-accent">
                            <Calendar size={16} />
                            {lang === 'ar' ? 'سجل حساب الإجازة' : 'Leave Calculation Record'}
                          </CardTitle>
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                            mirror.transaction.data.calculation_details.calculation_valid 
                              ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))] dark:bg-[hsl(var(--success)/0.2)] dark:text-[hsl(var(--success))]' 
                              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          }`}>
                            {mirror.transaction.data.calculation_details.calculation_valid 
                              ? (lang === 'ar' ? 'صحيح' : 'Valid')
                              : (lang === 'ar' ? 'خطأ' : 'Error')
                            }
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {/* Summary */}
                        <div className="bg-accent/10 dark:bg-accent/15 rounded-lg p-3 border border-accent/30 dark:border-accent/30">
                          <p className="text-accent dark:text-accent text-sm font-medium text-center">
                            {mirror.transaction.data.calculation_details.calculation_summary_ar}
                          </p>
                        </div>

                        {/* Numbers Grid - Horizontal */}
                        <div className="flex gap-2 overflow-x-auto pb-2">
                          <div className="flex-1 min-w-[80px] bg-muted/50 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold">{mirror.transaction.data.calculation_details.total_calendar_days}</p>
                            <p className="text-[10px] text-muted-foreground">{lang === 'ar' ? 'تقويمي' : 'Calendar'}</p>
                          </div>
                          <div className="flex-1 min-w-[80px] bg-[hsl(var(--success)/0.15)] dark:bg-[hsl(var(--success)/0.2)] rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-[hsl(var(--success))] dark:text-[hsl(var(--success))]">{mirror.transaction.data.calculation_details.working_days}</p>
                            <p className="text-[10px] text-[hsl(var(--success))]">{lang === 'ar' ? 'عمل' : 'Work'}</p>
                          </div>
                          <div className="flex-1 min-w-[80px] bg-[hsl(var(--warning)/0.15)] dark:bg-[hsl(var(--warning)/0.2)] rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-[hsl(var(--warning))] dark:text-[hsl(var(--warning))]">{mirror.transaction.data.calculation_details.excluded_fridays?.length || 0}</p>
                            <p className="text-[10px] text-[hsl(var(--warning))]">{lang === 'ar' ? 'جمعة' : 'Fri'}</p>
                          </div>
                          <div className="flex-1 min-w-[80px] bg-red-100 dark:bg-red-900/30 rounded-lg p-3 text-center">
                            <p className="text-xl font-bold text-red-700 dark:text-red-400">{mirror.transaction.data.calculation_details.excluded_holidays?.length || 0}</p>
                            <p className="text-[10px] text-red-600">{lang === 'ar' ? 'إجازة' : 'Holiday'}</p>
                          </div>
                        </div>

                        {/* Excluded Holidays */}
                        {mirror.transaction.data.calculation_details.excluded_holidays?.length > 0 && (
                          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 border border-red-200 dark:border-red-800">
                            <h4 className="text-xs font-semibold text-red-800 dark:text-red-200 mb-2 flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                              {lang === 'ar' ? 'الإجازات الرسمية المستثناة:' : 'Excluded Holidays:'}
                            </h4>
                            <div className="space-y-1">
                              {mirror.transaction.data.calculation_details.excluded_holidays.map((h, idx) => (
                                <div key={idx} className="flex items-center justify-between bg-white dark:bg-red-950/30 rounded px-2 py-1.5 text-xs">
                                  <span className="font-medium text-red-700 dark:text-red-300">{h.name}</span>
                                  <span className="text-red-600 dark:text-red-400 font-mono">{h.date}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* No holidays */}
                        {(!mirror.transaction.data.calculation_details.excluded_holidays || mirror.transaction.data.calculation_details.excluded_holidays.length === 0) && (
                          <div className="text-center text-xs text-[hsl(var(--success))] py-2">
                            {lang === 'ar' ? 'لا توجد إجازات رسمية ضمن الفترة' : 'No public holidays in period'}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Before/After */}
                  <Card className="border border-border shadow-none" data-testid="before-after-card">
                    <CardHeader className="pb-2"><CardTitle className="text-sm">{t('stas.beforeAfter')}</CardTitle></CardHeader>
                    <CardContent>
                      {/* عرض المعادلة والسياسة إذا كانت موجودة */}
                      {mirror.before_after?.formula && (
                        <div className="mb-4 p-3 rounded-lg bg-blue-50 border border-blue-100">
                          <p className="text-xs font-semibold text-blue-700 mb-1">{lang === 'ar' ? 'المعادلة' : 'Formula'}</p>
                          <p className="font-mono text-sm text-blue-900">{mirror.before_after.formula}</p>
                        </div>
                      )}
                      {mirror.before_after?.policy && (
                        <div className="mb-4 p-2 rounded bg-muted/50 text-sm">
                          <span className="text-muted-foreground">{lang === 'ar' ? 'السياسة:' : 'Policy:'}</span> 
                          <span className="font-bold ms-2">{mirror.before_after.policy.days} {lang === 'ar' ? 'يوم' : 'days'}</span>
                          <span className="text-xs text-muted-foreground ms-2">({mirror.before_after.policy.source_ar || mirror.before_after.policy.source})</span>
                        </div>
                      )}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-3 rounded-lg bg-muted/50">
                          <p className="text-xs font-semibold text-muted-foreground mb-2">{lang === 'ar' ? 'قبل' : 'BEFORE'}</p>
                          {Object.entries(mirror.before_after?.before || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between text-sm">
                              <span className="text-muted-foreground">{translateKey(k)}</span>
                              <span className="font-medium">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                            </div>
                          ))}
                        </div>
                        <div className="p-3 rounded-lg bg-primary/5 border border-primary/10">
                          <p className="text-xs font-semibold text-primary mb-2">{lang === 'ar' ? 'بعد' : 'AFTER'}</p>
                          {Object.entries(mirror.before_after?.after || {}).map(([k, v]) => (
                            <div key={k} className="flex justify-between text-sm">
                              <span className="text-muted-foreground">{translateKey(k)}</span>
                              <span className="font-bold">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      {mirror.before_after?.note_ar && (
                        <p className="text-xs text-muted-foreground mt-3 text-center">{mirror.before_after.note_ar}</p>
                      )}
                    </CardContent>
                  </Card>

                  {/* Trace Links */}
                  <Card className="border border-border shadow-none" data-testid="trace-links-card">
                    <CardHeader className="pb-2"><CardTitle className="text-sm">{t('stas.traceLinks')}</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-1">
                        {mirror.trace_links?.map((link, i) => (
                          <div key={i} className="flex items-center gap-2 text-sm p-1.5">
                            <Link2 size={14} className="text-muted-foreground" />
                            <span>{link.label}</span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Medical File - التقرير الطبي */}
                  {mirror.transaction?.data?.medical_file_url && (
                    <Card className="border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 shadow-none" data-testid="medical-file-card">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-red-800 dark:text-red-200 flex items-center gap-2">
                          <FileText size={16} />
                          {lang === 'ar' ? 'التقرير الطبي المرفق' : 'Attached Medical Report'}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        {/* معاينة PDF inline */}
                        <div className="border border-red-200 rounded overflow-hidden bg-white">
                          <iframe
                            src={`${mirror.transaction.data.medical_file_url}#toolbar=0&navpanes=0`}
                            className="w-full h-64"
                            title="Medical Report Preview"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => window.open(mirror.transaction.data.medical_file_url, '_blank')}
                            className="flex-1 border-red-300 text-red-600 hover:bg-red-100"
                            data-testid="view-medical-file-fullscreen"
                          >
                            <Eye size={14} className="me-2" />
                            {lang === 'ar' ? 'فتح في نافذة جديدة' : 'Open in New Tab'}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const link = document.createElement('a');
                              link.href = mirror.transaction.data.medical_file_url;
                              link.download = 'medical_report.pdf';
                              link.click();
                            }}
                            className="border-red-300 text-red-600 hover:bg-red-100"
                            data-testid="download-medical-file"
                          >
                            {lang === 'ar' ? 'تحميل' : 'Download'}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Desktop Execute Button - منع التنفيذ المكرر */}
                  <div className="hidden md:block space-y-2">
                    {mirror.transaction?.status === 'executed' ? (
                      <div className="w-full h-12 text-base font-semibold bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))] rounded-md flex items-center justify-center gap-2">
                        <CheckCircle size={18} /> {lang === 'ar' ? 'تم التنفيذ مسبقاً' : 'Already Executed'}
                      </div>
                    ) : (
                      <>
                        <Button
                          data-testid="stas-execute-btn-desktop"
                          onClick={handleExecute}
                          disabled={!mirror.all_checks_pass || executing}
                          className={`w-full h-12 text-base font-semibold ${mirror.all_checks_pass && !executing ? 'bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))] text-white' : 'bg-muted text-muted-foreground cursor-not-allowed'}`}
                        >
                          {executing ? <><Loader2 size={18} className="me-2 animate-spin" /> {t('stas.executing')}</> : <><Shield size={18} className="me-2" /> {t('stas.execute')}</>}
                        </Button>
                        
                        {/* زر الإلغاء */}
                        <Button
                          data-testid="stas-cancel-btn-desktop"
                          variant="outline"
                          onClick={() => setCancelDialogOpen(true)}
                          disabled={executing || cancelling}
                          className="w-full h-10 border-red-300 text-red-600 hover:bg-red-50"
                        >
                          <XCircle size={16} className="me-2" />
                          {lang === 'ar' ? 'إلغاء المعاملة' : 'Cancel Transaction'}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Holidays Tab */}
        <TabsContent value="holidays" className="mt-4">
          <Card className="border border-border shadow-none">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Calendar size={18} />
                {t('stas.holidayManagement')}
              </CardTitle>
              <Dialog open={holidayDialogOpen} onOpenChange={setHolidayDialogOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" data-testid="add-holiday-btn">{t('stas.addHoliday')}</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader><DialogTitle>{t('stas.addHoliday')}</DialogTitle></DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label>{t('stas.holidayNameEn')}</Label>
                      <Input 
                        data-testid="holiday-name-en"
                        value={newHoliday.name} 
                        onChange={e => setNewHoliday(h => ({ ...h, name: e.target.value }))} 
                      />
                    </div>
                    <div>
                      <Label>{t('stas.holidayNameAr')}</Label>
                      <Input 
                        data-testid="holiday-name-ar"
                        value={newHoliday.name_ar} 
                        onChange={e => setNewHoliday(h => ({ ...h, name_ar: e.target.value }))} 
                        dir="rtl"
                      />
                    </div>
                    <div>
                      <Label>{t('stas.holidayDate')}</Label>
                      <Input 
                        data-testid="holiday-date"
                        type="date" 
                        value={newHoliday.date} 
                        onChange={e => setNewHoliday(h => ({ ...h, date: e.target.value }))} 
                      />
                    </div>
                    <Button onClick={addHoliday} className="w-full" data-testid="submit-holiday">
                      {t('common.add')}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="border border-border rounded-lg overflow-hidden">
                <table className="w-full text-sm" data-testid="holidays-table">
                  <thead>
                    <tr className="bg-slate-50 border-b">
                      <th className="px-4 py-3 text-right font-semibold">{lang === 'ar' ? 'الإجازة' : 'Holiday'}</th>
                      <th className="px-4 py-3 text-center font-semibold w-32">{lang === 'ar' ? 'من' : 'From'}</th>
                      <th className="px-4 py-3 text-center font-semibold w-32">{lang === 'ar' ? 'إلى' : 'To'}</th>
                      <th className="px-4 py-3 text-center font-semibold w-20">{lang === 'ar' ? 'الأيام' : 'Days'}</th>
                      <th className="px-4 py-3 text-center font-semibold w-20">{t('common.actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {holidays.length === 0 ? (
                      <tr><td colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
                    ) : (() => {
                      // Group consecutive holidays by name
                      const groups = {};
                      holidays.forEach(h => {
                        const baseName = (h.name_ar || h.name || '').replace(/\s*\d+\s*$/, '').trim() || h.name;
                        if (!groups[baseName]) {
                          groups[baseName] = [];
                        }
                        groups[baseName].push(h);
                      });
                      
                      // Convert to range format and sort by first date
                      const sortedGroups = Object.entries(groups)
                        .map(([name, days]) => {
                          days.sort((a, b) => (a.date || '').localeCompare(b.date || ''));
                          return { name, days };
                        })
                        .sort((a, b) => (a.days[0]?.date || '').localeCompare(b.days[0]?.date || ''));
                      
                      return sortedGroups.map(({ name, days }) => {
                        const startDate = days[0]?.date;
                        const endDate = days[days.length - 1]?.date;
                        const nameAr = days[0]?.name_ar?.replace(/\s*\d+\s*$/, '').trim() || name;
                        const nameEn = days[0]?.name?.replace(/\s*\d+\s*$/, '').trim() || name;
                        const firstDayId = days[0]?.id;
                        
                        return (
                          <tr key={name} className="hover:bg-slate-50">
                            <td className="px-4 py-3 font-medium">
                              {lang === 'ar' ? nameAr : nameEn}
                            </td>
                            <td className="px-4 py-3 text-center font-mono text-xs">{startDate}</td>
                            <td className="px-4 py-3 text-center font-mono text-xs">{endDate}</td>
                            <td className="px-4 py-3 text-center">
                              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-100 text-green-700 text-sm font-bold">
                                {days.length}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 w-8 p-0 text-destructive hover:bg-red-50" 
                                onClick={() => {
                                  if (confirm(lang === 'ar' ? `هل تريد حذف جميع أيام ${nameAr}؟` : `Delete all ${nameEn} days?`)) {
                                    Promise.all(days.map(d => deleteHoliday(d.id)));
                                  }
                                }}
                                data-testid={`delete-holiday-${firstDayId}`}
                              >
                                <Trash2 size={16} />
                              </Button>
                            </td>
                          </tr>
                        );
                      });
                    })()}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Maintenance Tab */}
        <TabsContent value="maintenance" className="mt-4 space-y-4">
          {/* Version Management */}
          <Card className="border-2 border-accent/30 shadow-sm">
            <CardHeader className="bg-gradient-to-r from-accent/10 to-accent/5">
              <CardTitle className="text-base flex items-center justify-between">
                <span className="flex items-center gap-2 text-accent">
                  <Tag size={20} />
                  {lang === 'ar' ? 'إدارة إصدار التطبيق' : 'App Version Management'}
                </span>
                <span className="px-3 py-1.5 bg-accent text-white rounded-full text-sm font-bold">
                  v{versionInfo?.version || '1.0.0'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {/* Current Version Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-xl border">
                  <p className="text-xs text-muted-foreground mb-1">{lang === 'ar' ? 'الإصدار الحالي' : 'Current Version'}</p>
                  <p className="text-2xl font-bold text-accent">{versionInfo?.version || '1.0.0'}</p>
                  {versionInfo?.updated_at && (
                    <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                      <Clock size={12} />
                      {new Date(versionInfo.updated_at).toLocaleString('ar-EG')}
                    </p>
                  )}
                </div>
                <div className="p-4 bg-slate-50 rounded-xl border">
                  <p className="text-xs text-muted-foreground mb-1">{lang === 'ar' ? 'ملاحظات الإصدار' : 'Release Notes'}</p>
                  <p className="text-sm">{lang === 'ar' ? versionInfo?.release_notes_ar : versionInfo?.release_notes_en || '-'}</p>
                </div>
              </div>
              
              {/* Version History */}
              {versionInfo?.version_history && versionInfo.version_history.length > 0 && (
                <div className="p-4 bg-slate-50 rounded-xl border">
                  <p className="text-sm font-semibold mb-2 flex items-center gap-2">
                    <History size={14} />
                    {lang === 'ar' ? 'سجل الإصدارات' : 'Version History'}
                  </p>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {versionInfo.version_history.slice().reverse().map((v, i) => (
                      <div key={i} className="flex items-center justify-between text-sm px-3 py-2 bg-white rounded border">
                        <span className="font-mono text-xs">v{v.version}</span>
                        <span className="text-xs text-muted-foreground">
                          {v.updated_at ? new Date(v.updated_at).toLocaleDateString('ar-EG') : '-'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Update Version Dialog */}
              <Dialog open={versionDialogOpen} onOpenChange={setVersionDialogOpen}>
                <DialogTrigger asChild>
                  <Button 
                    className="w-full h-12 bg-accent hover:bg-accent text-white font-bold"
                    data-testid="open-version-dialog-btn"
                  >
                    <RefreshCw size={18} className="ml-2" />
                    {lang === 'ar' ? 'تحديث الإصدار' : 'Update Version'}
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <Tag size={20} className="text-accent" />
                      {lang === 'ar' ? 'تحديث إصدار التطبيق' : 'Update App Version'}
                    </DialogTitle>
                    <DialogDescription>
                      {lang === 'ar' 
                        ? 'أدخل رقم الإصدار الجديد وملاحظات التحديث'
                        : 'Enter the new version number and release notes'}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div>
                      <Label className="text-base font-semibold">{lang === 'ar' ? 'رقم الإصدار' : 'Version Number'}</Label>
                      <Input
                        value={newVersion}
                        onChange={(e) => setNewVersion(e.target.value)}
                        placeholder="1.2.0"
                        className="mt-2 text-lg font-mono"
                        data-testid="version-number-input"
                        dir="ltr"
                      />
                    </div>
                    <div>
                      <Label className="text-base font-semibold">{lang === 'ar' ? 'ملاحظات التحديث (عربي)' : 'Release Notes (Arabic)'}</Label>
                      <Input
                        value={releaseNotesAr}
                        onChange={(e) => setReleaseNotesAr(e.target.value)}
                        placeholder={lang === 'ar' ? 'ما الجديد في هذا الإصدار؟' : 'What\'s new in Arabic?'}
                        className="mt-2"
                        data-testid="release-notes-ar-input"
                      />
                    </div>
                    <div>
                      <Label className="text-base font-semibold">{lang === 'ar' ? 'ملاحظات التحديث (إنجليزي)' : 'Release Notes (English)'}</Label>
                      <Input
                        value={releaseNotesEn}
                        onChange={(e) => setReleaseNotesEn(e.target.value)}
                        placeholder={lang === 'ar' ? 'What\'s new?' : 'What\'s new in this version?'}
                        className="mt-2"
                        dir="ltr"
                        data-testid="release-notes-en-input"
                      />
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      onClick={() => setVersionDialogOpen(false)}
                      className="flex-1"
                    >
                      {lang === 'ar' ? 'إلغاء' : 'Cancel'}
                    </Button>
                    <Button
                      onClick={handleUpdateVersion}
                      disabled={updatingVersion || !newVersion.trim()}
                      className="flex-1 bg-accent hover:bg-accent"
                      data-testid="save-version-btn"
                    >
                      {updatingVersion ? (
                        <Loader2 size={16} className="animate-spin ml-2" />
                      ) : (
                        <CheckCircle size={16} className="ml-2" />
                      )}
                      {lang === 'ar' ? 'حفظ' : 'Save'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>

          {/* Archived Users */}
          <Card className="border border-border shadow-none">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <UserX size={18} />
                {t('stas.archivedUsers')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {archivedUsers.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">{t('stas.noArchivedUsers')}</p>
              ) : (
                <div className="space-y-2">
                  {archivedUsers.map(u => (
                    <div key={u.id} className="flex items-center justify-between p-3 rounded-lg border border-border">
                      <div>
                        <p className="text-sm font-medium">{u.full_name}</p>
                        <p className="text-xs text-muted-foreground">{u.username} - {u.role}</p>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => restoreUser(u.id)}
                        data-testid={`restore-user-${u.id}`}
                      >
                        <RotateCcw size={14} className="me-1" /> {t('stas.restoreUser')}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* === Company Settings Tab === */}
        <TabsContent value="company-settings" className="mt-4">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Logo Upload */}
            <Card className="border border-border shadow-none">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield size={18} className="text-accent" />
                  {lang === 'ar' ? 'شعار الشركة' : 'Company Logo'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  {companySettings.logo_url ? (
                    <div className="relative">
                      <img 
                        src={companySettings.logo_url} 
                        alt="Logo" 
                        className="w-24 h-24 object-contain rounded-xl border border-border"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeleteLogo}
                        className="absolute -top-2 -right-2 w-6 h-6 p-0 rounded-full bg-destructive text-white hover:bg-destructive"
                      >
                        <X size={12} />
                      </Button>
                    </div>
                  ) : (
                    <div className="w-24 h-24 rounded-xl border-2 border-dashed border-muted-foreground/30 flex items-center justify-center text-muted-foreground">
                      <Shield size={32} />
                    </div>
                  )}
                  <div>
                    <input
                      type="file"
                      accept="image/png,image/svg+xml,image/jpeg"
                      onChange={handleUploadLogo}
                      className="hidden"
                      id="logo-upload"
                    />
                    <Button
                      variant="outline"
                      onClick={() => document.getElementById('logo-upload')?.click()}
                      disabled={uploadingLogo}
                    >
                      {uploadingLogo ? <Loader2 size={16} className="animate-spin ml-2" /> : null}
                      {lang === 'ar' ? 'رفع شعار' : 'Upload Logo'}
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2">
                      PNG, SVG, JPG - {lang === 'ar' ? 'حد أقصى 2MB' : 'Max 2MB'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Side Image Upload */}
            <Card className="border border-border shadow-none">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Maximize2 size={18} className="text-accent" />
                  {lang === 'ar' ? 'الصورة الجانبية' : 'Side Image'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  {companySettings.side_image_url ? (
                    <div className="relative">
                      <img 
                        src={companySettings.side_image_url} 
                        alt="Side" 
                        className="w-32 h-24 object-cover rounded-xl border border-border"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeleteSideImage}
                        className="absolute -top-2 -right-2 w-6 h-6 p-0 rounded-full bg-destructive text-white hover:bg-destructive"
                      >
                        <X size={12} />
                      </Button>
                    </div>
                  ) : (
                    <div className="w-32 h-24 rounded-xl border-2 border-dashed border-muted-foreground/30 flex items-center justify-center text-muted-foreground">
                      <Maximize2 size={32} />
                    </div>
                  )}
                  <div>
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={handleUploadSideImage}
                      className="hidden"
                      id="side-image-upload"
                    />
                    <Button
                      variant="outline"
                      onClick={() => document.getElementById('side-image-upload')?.click()}
                      disabled={uploadingSideImage}
                    >
                      {uploadingSideImage ? <Loader2 size={16} className="animate-spin ml-2" /> : null}
                      {lang === 'ar' ? 'رفع صورة' : 'Upload Image'}
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2">
                      PNG, JPG, WEBP - {lang === 'ar' ? 'حد أقصى 5MB' : 'Max 5MB'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* PWA Icon Upload - أيقونة التطبيق */}
            <Card className="border border-border shadow-none md:col-span-2 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Smartphone size={18} className="text-blue-600" />
                  {lang === 'ar' ? 'أيقونة التطبيق (PWA)' : 'App Icon (PWA)'}
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                    {lang === 'ar' ? 'جديد' : 'New'}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  {lang === 'ar' 
                    ? 'هذه الأيقونة ستظهر على أجهزة المستخدمين (آيفون، أندرويد، الكمبيوتر) عند تثبيت التطبيق. يُنصح باستخدام صورة مربعة 512×512 بكسل.'
                    : 'This icon will appear on user devices (iPhone, Android, Desktop) when installing the app. Recommended size: 512x512 pixels.'}
                </p>
                <div className="flex items-center gap-4">
                  {companySettings.pwa_icon_url ? (
                    <div className="relative">
                      <img 
                        src={companySettings.pwa_icon_url} 
                        alt="PWA Icon" 
                        className="w-24 h-24 object-contain rounded-xl border-2 border-blue-200 shadow-md"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeletePwaIcon}
                        className="absolute -top-2 -right-2 w-6 h-6 p-0 rounded-full bg-destructive text-white hover:bg-destructive"
                      >
                        <X size={12} />
                      </Button>
                    </div>
                  ) : companySettings.logo_url ? (
                    <div className="relative">
                      <img 
                        src={companySettings.logo_url} 
                        alt="Logo as Icon" 
                        className="w-24 h-24 object-contain rounded-xl border-2 border-dashed border-blue-300 opacity-60"
                      />
                      <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 text-[10px] bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full whitespace-nowrap">
                        {lang === 'ar' ? 'من الشعار' : 'From Logo'}
                      </span>
                    </div>
                  ) : (
                    <div className="w-24 h-24 rounded-xl border-2 border-dashed border-blue-300 flex items-center justify-center text-blue-400">
                      <Smartphone size={32} />
                    </div>
                  )}
                  <div>
                    <input
                      type="file"
                      accept="image/png,image/jpeg"
                      onChange={handleUploadPwaIcon}
                      className="hidden"
                      id="pwa-icon-upload"
                    />
                    <Button
                      variant="outline"
                      onClick={() => document.getElementById('pwa-icon-upload')?.click()}
                      disabled={uploadingPwaIcon}
                      className="border-blue-300 text-blue-700 hover:bg-blue-50"
                    >
                      {uploadingPwaIcon ? <Loader2 size={16} className="animate-spin ml-2" /> : <Smartphone size={16} className="ml-2" />}
                      {lang === 'ar' ? 'رفع أيقونة التطبيق' : 'Upload App Icon'}
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2">
                      PNG, JPG - 512×512 {lang === 'ar' ? 'بكسل مُوصى' : 'px recommended'}
                    </p>
                    {!companySettings.pwa_icon_url && companySettings.logo_url && (
                      <p className="text-xs text-blue-600 mt-1">
                        {lang === 'ar' ? '💡 حالياً يتم استخدام الشعار كأيقونة' : '💡 Currently using logo as icon'}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Welcome Text */}
            <Card className="border border-border shadow-none md:col-span-2">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText size={18} className="text-accent" />
                  {lang === 'ar' ? 'عبارة الترحيب' : 'Welcome Message'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label>{lang === 'ar' ? 'العبارة بالعربية' : 'Arabic Text'}</Label>
                    <Input
                      value={companySettings.welcome_text_ar}
                      onChange={(e) => setCompanySettings(prev => ({ ...prev, welcome_text_ar: e.target.value }))}
                      placeholder="أنتم الدار ونحن الكود"
                      className="mt-2"
                      dir="rtl"
                    />
                  </div>
                  <div>
                    <Label>{lang === 'ar' ? 'العبارة بالإنجليزية' : 'English Text'}</Label>
                    <Input
                      value={companySettings.welcome_text_en}
                      onChange={(e) => setCompanySettings(prev => ({ ...prev, welcome_text_en: e.target.value }))}
                      placeholder="You are the Home, We are the Code"
                      className="mt-2"
                      dir="ltr"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Company Name */}
            <Card className="border border-border shadow-none md:col-span-2">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield size={18} className="text-accent" />
                  {lang === 'ar' ? 'اسم الشركة' : 'Company Name'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label>{lang === 'ar' ? 'الاسم بالعربية' : 'Arabic Name'}</Label>
                    <Input
                      value={companySettings.company_name_ar}
                      onChange={(e) => setCompanySettings(prev => ({ ...prev, company_name_ar: e.target.value }))}
                      placeholder="شركة دار الأركان"
                      className="mt-2"
                      dir="rtl"
                    />
                  </div>
                  <div>
                    <Label>{lang === 'ar' ? 'الاسم بالإنجليزية' : 'English Name'}</Label>
                    <Input
                      value={companySettings.company_name_en}
                      onChange={(e) => setCompanySettings(prev => ({ ...prev, company_name_en: e.target.value }))}
                      placeholder="Dar Al Arkan"
                      className="mt-2"
                      dir="ltr"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Colors */}
            <Card className="border border-border shadow-none md:col-span-2">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Settings size={18} className="text-accent" />
                  {lang === 'ar' ? 'ألوان صفحة الدخول' : 'Login Page Colors'}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label>{lang === 'ar' ? 'اللون الأساسي (Navy)' : 'Primary Color (Navy)'}</Label>
                    <div className="flex items-center gap-3 mt-2">
                      <input
                        type="color"
                        value={companySettings.primary_color}
                        onChange={(e) => setCompanySettings(prev => ({ ...prev, primary_color: e.target.value }))}
                        className="w-12 h-12 rounded-lg border border-border cursor-pointer"
                      />
                      <Input
                        value={companySettings.primary_color}
                        onChange={(e) => setCompanySettings(prev => ({ ...prev, primary_color: e.target.value }))}
                        placeholder="#1E3A5F"
                        className="flex-1 font-mono"
                        dir="ltr"
                      />
                    </div>
                  </div>
                  <div>
                    <Label>{lang === 'ar' ? 'اللون الثانوي (Lavender)' : 'Secondary Color (Lavender)'}</Label>
                    <div className="flex items-center gap-3 mt-2">
                      <input
                        type="color"
                        value={companySettings.secondary_color}
                        onChange={(e) => setCompanySettings(prev => ({ ...prev, secondary_color: e.target.value }))}
                        className="w-12 h-12 rounded-lg border border-border cursor-pointer"
                      />
                      <Input
                        value={companySettings.secondary_color}
                        onChange={(e) => setCompanySettings(prev => ({ ...prev, secondary_color: e.target.value }))}
                        placeholder="#A78BFA"
                        className="flex-1 font-mono"
                        dir="ltr"
                      />
                    </div>
                  </div>
                </div>
                
                {/* Preview */}
                <div className="mt-4 p-4 rounded-xl border border-border">
                  <p className="text-sm text-muted-foreground mb-3">{lang === 'ar' ? 'معاينة:' : 'Preview:'}</p>
                  <div 
                    className="h-16 rounded-lg flex items-center justify-center text-white font-bold"
                    style={{ background: `linear-gradient(135deg, ${companySettings.primary_color}, ${companySettings.secondary_color})` }}
                  >
                    {companySettings.welcome_text_ar}
                  </div>
                </div>
                
                <Button
                  onClick={handleSaveCompanySettings}
                  disabled={savingSettings}
                  className="w-full mt-4"
                >
                  {savingSettings ? <Loader2 size={16} className="animate-spin ml-2" /> : <CheckCircle size={16} className="ml-2" />}
                  {lang === 'ar' ? 'حفظ الإعدادات' : 'Save Settings'}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Mobile Decision Bar - Fixed at bottom - منع التنفيذ المكرر */}
      {mirror && (
        <div className="fixed bottom-0 left-0 right-0 md:hidden bg-background border-t border-border p-4 shadow-lg z-40" data-testid="mobile-decision-bar">
          <div className="flex gap-3 max-w-lg mx-auto">
            <Button 
              variant="outline" 
              className="flex-1"
              onClick={previewPdf}
              data-testid="mobile-preview-btn"
            >
              <FileText size={16} className="me-1" /> {t('common.preview')}
            </Button>
            {mirror.transaction?.status === 'executed' ? (
              <div className="flex-1 h-10 bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))] rounded-md flex items-center justify-center gap-1 text-sm font-medium">
                <CheckCircle size={14} /> {lang === 'ar' ? 'تم التنفيذ' : 'Executed'}
              </div>
            ) : (
              <div className="flex gap-2 flex-1">
                <Button
                  data-testid="stas-execute-btn-mobile"
                  onClick={handleExecute}
                  disabled={!mirror.all_checks_pass || executing}
                  className={`flex-1 ${mirror.all_checks_pass && !executing ? 'bg-[hsl(var(--success))] hover:bg-[hsl(var(--success))] text-white' : 'bg-muted text-muted-foreground'}`}
                >
                  {executing ? <Loader2 size={16} className="me-1 animate-spin" /> : <Shield size={16} className="me-1" />}
                  {t('stas.execute')}
                </Button>
                <Button
                  data-testid="stas-cancel-btn-mobile"
                  variant="outline"
                  onClick={() => setCancelDialogOpen(true)}
                  disabled={executing || cancelling}
                  className="border-red-300 text-red-600"
                >
                  <XCircle size={16} />
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cancel Transaction Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              {lang === 'ar' ? 'إلغاء المعاملة' : 'Cancel Transaction'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <p className="text-sm text-red-800 dark:text-red-200">
                {lang === 'ar' 
                  ? 'سيتم إلغاء هذه المعاملة نهائياً. يمكن للموظف تقديم طلب جديد بعد الإلغاء.'
                  : 'This transaction will be permanently cancelled. The employee can submit a new request after cancellation.'
                }
              </p>
            </div>
            
            <div>
              <Label className="text-red-600">
                {lang === 'ar' ? '* سبب الإلغاء (مطلوب)' : '* Cancellation Reason (Required)'}
              </Label>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder={lang === 'ar' ? 'اكتب سبب إلغاء المعاملة...' : 'Write the reason for cancellation...'}
                className="w-full mt-2 p-3 border border-red-200 rounded-lg min-h-[100px] focus:outline-none focus:ring-2 focus:ring-red-500"
                data-testid="cancel-reason-input"
              />
              <p className="text-xs text-muted-foreground mt-1">
                {lang === 'ar' ? `${cancelReason.length}/5 أحرف على الأقل` : `${cancelReason.length}/5 characters minimum`}
              </p>
            </div>
          </div>
          
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => { setCancelDialogOpen(false); setCancelReason(''); }}>
              {lang === 'ar' ? 'إغلاق' : 'Close'}
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleCancelTransaction}
              disabled={cancelling || cancelReason.trim().length < 5}
              data-testid="confirm-cancel-btn"
            >
              {cancelling ? <Loader2 size={16} className="me-2 animate-spin" /> : <XCircle size={16} className="me-2" />}
              {lang === 'ar' ? 'تأكيد الإلغاء' : 'Confirm Cancel'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* PDF Preview Modal - Full Screen */}
      <Dialog open={pdfPreviewOpen} onOpenChange={closePdfPreview}>
        <DialogContent className="max-w-6xl w-[95vw] h-[90vh] p-0 overflow-hidden">
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b bg-slate-50">
              <div className="flex items-center gap-3">
                <FileText size={20} className="text-primary" />
                <span className="font-semibold text-slate-800">
                  {lang === 'ar' ? 'معاينة المستند' : 'Document Preview'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={downloadPdf}
                  className="gap-2"
                >
                  <Download size={16} />
                  {lang === 'ar' ? 'تحميل' : 'Download'}
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => pdfUrl && window.open(pdfUrl, '_blank')}
                  className="gap-2"
                >
                  <ExternalLink size={16} />
                  {lang === 'ar' ? 'فتح في نافذة جديدة' : 'Open in new tab'}
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={closePdfPreview}
                >
                  <X size={20} />
                </Button>
              </div>
            </div>
            
            {/* PDF Viewer */}
            <div className="flex-1 bg-slate-100 overflow-hidden">
              {pdfLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 size={40} className="animate-spin text-primary" />
                </div>
              ) : pdfUrl ? (
                <iframe 
                  src={pdfUrl} 
                  className="w-full h-full border-0"
                  title="PDF Preview"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  {lang === 'ar' ? 'لا يوجد مستند للعرض' : 'No document to display'}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
