import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import api from '@/lib/api';
import { formatGregorianHijriDateTime } from '@/lib/dateUtils';
import { 
  Database, 
  Trash2, 
  Archive, 
  Download, 
  Upload, 
  HardDrive,
  AlertTriangle,
  Clock,
  FileArchive,
  RefreshCw,
  Shield,
  Server,
  FileUp,
  CheckCircle2,
  XCircle,
  RotateCcw,
  FileJson,
  Bell,
  Pin,
  Send,
  Megaphone
} from 'lucide-react';

export default function SystemMaintenancePage() {
  const { t } = useLanguage();
  const [storageInfo, setStorageInfo] = useState(null);
  const [archives, setArchives] = useState([]);
  const [maintenanceLogs, setMaintenanceLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  
  // Purge confirmation
  const [showPurgeConfirm, setShowPurgeConfirm] = useState(false);
  const [purgeConfirmText, setPurgeConfirmText] = useState('');
  
  // Archive creation
  const [showCreateArchive, setShowCreateArchive] = useState(false);
  const [archiveName, setArchiveName] = useState('');
  const [archiveDescription, setArchiveDescription] = useState('');
  
  // Restore confirmation
  const [restoreArchiveId, setRestoreArchiveId] = useState(null);
  
  // File upload
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  
  // Announcements
  const [announcements, setAnnouncements] = useState([]);
  const [announcementForm, setAnnouncementForm] = useState({
    message_ar: '',
    message_en: '',
    is_pinned: false
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [storageRes, archivesRes, logsRes, announcementsRes] = await Promise.all([
        api.get('/api/maintenance/storage-info'),
        api.get('/api/maintenance/archives'),
        api.get('/api/maintenance/logs?limit=20'),
        api.get('/api/announcements/all').catch(() => ({ data: [] }))
      ]);
      setStorageInfo(storageRes.data);
      setArchives(archivesRes.data.archives || []);
      setMaintenanceLogs(logsRes.data.logs || []);
      setAnnouncements(announcementsRes.data || []);
    } catch (error) {
      toast.error('خطأ في تحميل البيانات');
    }
    setLoading(false);
  };

  const handleCreateAnnouncement = async () => {
    if (!announcementForm.message_ar.trim()) {
      toast.error('يرجى كتابة الرسالة بالعربي');
      return;
    }
    
    setActionLoading(true);
    try {
      await api.post('/api/announcements', announcementForm);
      toast.success('تم إرسال الإشعار بنجاح');
      setAnnouncementForm({ message_ar: '', message_en: '', is_pinned: false });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'خطأ في الإرسال');
    }
    setActionLoading(false);
  };

  const handleDeleteAnnouncement = async (id) => {
    try {
      await api.delete(`/api/announcements/${id}`);
      toast.success('تم حذف الإشعار');
      loadData();
    } catch (error) {
      toast.error('خطأ في الحذف');
    }
  };

  const handlePurgeAll = async () => {
    if (purgeConfirmText !== 'DELETE ALL') {
      toast.error('يجب كتابة DELETE ALL للتأكيد');
      return;
    }
    
    setActionLoading(true);
    try {
      const res = await api.post('/api/maintenance/purge-all-transactions', {
        confirm: true,
        confirm_text: 'DELETE ALL'
      });
      toast.success(`تم حذف ${res.data.total_deleted} سجل بنجاح`);
      setShowPurgeConfirm(false);
      setPurgeConfirmText('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'خطأ في الحذف');
    }
    setActionLoading(false);
  };

  const handleCreateArchive = async () => {
    setActionLoading(true);
    try {
      const res = await api.post('/api/maintenance/archive-full', {
        name: archiveName || undefined,
        description: archiveDescription || undefined
      });
      toast.success(`تم إنشاء الأرشيف: ${res.data.archive_id}`);
      setShowCreateArchive(false);
      setArchiveName('');
      setArchiveDescription('');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'خطأ في إنشاء الأرشيف');
    }
    setActionLoading(false);
  };

  const handleRestoreArchive = async (archiveId) => {
    setActionLoading(true);
    try {
      const res = await api.post(`/api/maintenance/archives/${archiveId}/restore`, {
        archive_id: archiveId,
        confirm: true
      });
      toast.success(`تم استعادة ${res.data.total_documents_restored} سجل`);
      setRestoreArchiveId(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'خطأ في الاستعادة');
    }
    setActionLoading(false);
  };

  const handleDownloadArchive = async (archiveId) => {
    try {
      const res = await api.get(`/api/maintenance/archives/${archiveId}/download`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${archiveId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('تم تحميل الأرشيف');
    } catch (error) {
      toast.error('خطأ في التحميل');
    }
  };

  const handleDeleteArchive = async (archiveId) => {
    if (!confirm('هل تريد حذف هذا الأرشيف؟')) return;
    
    try {
      await api.delete(`/api/maintenance/archives/${archiveId}`);
      toast.success('تم حذف الأرشيف');
      loadData();
    } catch (error) {
      toast.error('خطأ في الحذف');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.json')) {
        toast.error('يجب اختيار ملف JSON');
        return;
      }
      setUploadFile(file);
    }
  };

  const handleUploadRestore = async () => {
    if (!uploadFile) {
      toast.error('يرجى اختيار ملف أولاً');
      return;
    }
    
    setActionLoading(true);
    setUploadProgress(10);
    
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      setUploadProgress(30);
      
      const res = await api.post('/api/maintenance/archives/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 60) / progressEvent.total) + 30;
          setUploadProgress(progress);
        }
      });
      
      setUploadProgress(100);
      toast.success(`تم استعادة ${res.data.total_documents_restored} سجل بنجاح`);
      setUploadFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'خطأ في رفع واستعادة الأرشيف');
    }
    
    setActionLoading(false);
    setUploadProgress(0);
  };

  const formatBytes = (kb) => {
    if (!kb || kb === 0) return '0 KB';
    if (kb < 1024) return `${kb.toFixed(2)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  const formatDate = (dateStr) => {
    const formatted = formatGregorianHijriDateTime(dateStr);
    return formatted.combined;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="system-maintenance-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-xl">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">صيانة النظام</h1>
            <p className="text-muted-foreground text-sm">إدارة الأرشفة والحذف ومعلومات التخزين</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} data-testid="refresh-btn">
          <RefreshCw className="w-4 h-4 ml-2" />
          تحديث
        </Button>
      </div>

      {/* Total Storage Summary */}
      {storageInfo && (
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white border-0" data-testid="total-storage-card">
          <CardContent className="pt-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {/* Total Size */}
              <div className="col-span-2 md:col-span-1 bg-white/10 rounded-xl p-4 text-center">
                <Server className="w-8 h-8 mx-auto mb-2 text-blue-300" />
                <div className="text-3xl font-bold">{formatBytes(storageInfo.totals.total_size_kb)}</div>
                <div className="text-sm text-slate-300">الحجم الكلي</div>
              </div>
              
              {/* Total Documents */}
              <div className="bg-white/10 rounded-xl p-4 text-center">
                <Database className="w-6 h-6 mx-auto mb-2 text-green-300" />
                <div className="text-2xl font-bold">{storageInfo.totals.total_documents}</div>
                <div className="text-xs text-slate-300">إجمالي السجلات</div>
              </div>
              
              {/* Transaction Docs */}
              <div className="bg-orange-500/20 rounded-xl p-4 text-center">
                <FileJson className="w-6 h-6 mx-auto mb-2 text-orange-300" />
                <div className="text-2xl font-bold">{storageInfo.totals.transaction_documents}</div>
                <div className="text-xs text-orange-200">سجلات معاملات</div>
                <div className="text-xs text-orange-300">{formatBytes(storageInfo.totals.transaction_size_kb)}</div>
              </div>
              
              {/* Protected Docs */}
              <div className="bg-green-500/20 rounded-xl p-4 text-center">
                <Shield className="w-6 h-6 mx-auto mb-2 text-green-300" />
                <div className="text-2xl font-bold">{storageInfo.totals.protected_documents}</div>
                <div className="text-xs text-green-200">سجلات محمية</div>
                <div className="text-xs text-green-300">{formatBytes(storageInfo.totals.protected_size_kb)}</div>
              </div>
              
              {/* Collections Count */}
              <div className="bg-white/10 rounded-xl p-4 text-center">
                <HardDrive className="w-6 h-6 mx-auto mb-2 text-purple-300" />
                <div className="text-2xl font-bold">{storageInfo.totals.total_collections}</div>
                <div className="text-xs text-slate-300">Collections</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions Grid */}
      <div className="grid md:grid-cols-3 gap-4">
        {/* Create Archive */}
        <Card className="border-blue-200 bg-blue-50/50" data-testid="archive-action-card">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Archive className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <CardTitle className="text-lg">إنشاء أرشيف</CardTitle>
                <CardDescription className="text-xs">حفظ نسخة كاملة من النظام</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {!showCreateArchive ? (
              <Button 
                onClick={() => setShowCreateArchive(true)}
                className="w-full bg-blue-600 hover:bg-blue-700"
                data-testid="create-archive-btn"
              >
                <FileArchive className="w-4 h-4 ml-2" />
                أرشفة الآن
              </Button>
            ) : (
              <div className="space-y-3">
                <Input
                  placeholder="اسم الأرشيف (اختياري)"
                  value={archiveName}
                  onChange={(e) => setArchiveName(e.target.value)}
                  className="text-sm"
                />
                <Input
                  placeholder="وصف (اختياري)"
                  value={archiveDescription}
                  onChange={(e) => setArchiveDescription(e.target.value)}
                  className="text-sm"
                />
                <div className="flex gap-2">
                  <Button 
                    onClick={handleCreateArchive}
                    disabled={actionLoading}
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                    size="sm"
                  >
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'إنشاء'}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => setShowCreateArchive(false)}
                    size="sm"
                  >
                    إلغاء
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Upload & Restore */}
        <Card className="border-green-200 bg-green-50/50" data-testid="upload-restore-card">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-green-100 rounded-lg">
                <FileUp className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <CardTitle className="text-lg">رفع واستعادة</CardTitle>
                <CardDescription className="text-xs">استعادة من ملف أرشيف خارجي</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div 
                className="border-2 border-dashed border-green-300 rounded-lg p-4 text-center cursor-pointer hover:bg-green-100/50 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleFileSelect}
                  className="hidden"
                  data-testid="file-input"
                />
                {uploadFile ? (
                  <div className="flex items-center justify-center gap-2 text-green-700">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="text-sm font-medium truncate max-w-[150px]">{uploadFile.name}</span>
                  </div>
                ) : (
                  <div className="text-green-600">
                    <Upload className="w-6 h-6 mx-auto mb-1" />
                    <span className="text-sm">اختر ملف JSON</span>
                  </div>
                )}
              </div>
              
              {uploadProgress > 0 && (
                <Progress value={uploadProgress} className="h-2" />
              )}
              
              <Button 
                onClick={handleUploadRestore}
                disabled={!uploadFile || actionLoading}
                className="w-full bg-green-600 hover:bg-green-700"
                data-testid="upload-restore-btn"
              >
                {actionLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin ml-2" />
                ) : (
                  <RotateCcw className="w-4 h-4 ml-2" />
                )}
                استعادة النظام
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Purge Transactions */}
        <Card className="border-red-200 bg-red-50/50" data-testid="purge-action-card">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="p-2 bg-red-100 rounded-lg">
                <Trash2 className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <CardTitle className="text-lg text-red-700">حذف المعاملات</CardTitle>
                <CardDescription className="text-xs">حذف كل المعاملات والسجلات</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {!showPurgeConfirm ? (
              <Button 
                variant="destructive"
                onClick={() => setShowPurgeConfirm(true)}
                className="w-full"
                data-testid="purge-all-btn"
              >
                <AlertTriangle className="w-4 h-4 ml-2" />
                حذف جميع المعاملات
              </Button>
            ) : (
              <div className="space-y-3">
                <div className="p-2 bg-red-100 rounded-lg text-red-700 text-xs flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>تحذير: سيتم حذف جميع المعاملات والسجلات بشكل نهائي! لن يمس المستخدمين والموظفين.</span>
                </div>
                <Input
                  placeholder="اكتب DELETE ALL"
                  value={purgeConfirmText}
                  onChange={(e) => setPurgeConfirmText(e.target.value)}
                  className="font-mono text-sm"
                />
                <div className="flex gap-2">
                  <Button 
                    variant="destructive"
                    onClick={handlePurgeAll}
                    disabled={actionLoading || purgeConfirmText !== 'DELETE ALL'}
                    className="flex-1"
                    size="sm"
                  >
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'تأكيد'}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => {
                      setShowPurgeConfirm(false);
                      setPurgeConfirmText('');
                    }}
                    size="sm"
                  >
                    إلغاء
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Collections Details */}
      {storageInfo && (
        <Card data-testid="collections-detail-card">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-primary" />
              <CardTitle>تفاصيل Collections</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              {/* Transaction Collections */}
              <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2 text-orange-700">
                  <FileJson className="w-4 h-4" />
                  سجلات المعاملات (قابلة للحذف)
                </h4>
                <div className="space-y-1">
                  {Object.entries(storageInfo.collections)
                    .filter(([_, info]) => info.is_transaction_data)
                    .map(([name, info]) => (
                      <div 
                        key={name} 
                        className="flex items-center justify-between p-2 bg-orange-50 rounded text-sm"
                      >
                        <span className="font-mono text-xs">{name}</span>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{info.documents} سجل</span>
                          <span>{formatBytes(info.estimated_size_kb)}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
              
              {/* Protected Collections */}
              <div>
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2 text-green-700">
                  <Shield className="w-4 h-4" />
                  سجلات محمية (لا تُحذف)
                </h4>
                <div className="space-y-1">
                  {Object.entries(storageInfo.collections)
                    .filter(([_, info]) => info.is_protected)
                    .map(([name, info]) => (
                      <div 
                        key={name} 
                        className="flex items-center justify-between p-2 bg-green-50 rounded text-sm"
                      >
                        <span className="font-mono text-xs">{name}</span>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>{info.documents} سجل</span>
                          <span>{formatBytes(info.estimated_size_kb)}</span>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Archives List */}
      <Card data-testid="archives-list-card">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileArchive className="w-5 h-5 text-primary" />
              <CardTitle>الأرشيفات المحفوظة</CardTitle>
              <Badge variant="secondary">{archives.length}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {archives.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <Archive className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>لا توجد أرشيفات محفوظة</p>
            </div>
          ) : (
            <div className="space-y-3">
              {archives.map((archive) => (
                <div 
                  key={archive.id}
                  className="p-4 border rounded-xl hover:shadow-sm transition-shadow"
                  data-testid={`archive-${archive.id}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium truncate">{archive.name}</h4>
                        {archive.source === 'uploaded' && (
                          <Badge variant="outline" className="text-xs">مرفوع</Badge>
                        )}
                      </div>
                      {archive.description && (
                        <p className="text-sm text-muted-foreground truncate">{archive.description}</p>
                      )}
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(archive.created_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Database className="w-3 h-3" />
                          {archive.stats?.total_documents} سجل
                        </span>
                        <span className="flex items-center gap-1">
                          <HardDrive className="w-3 h-3" />
                          {formatBytes(archive.size_compressed_kb)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {archive.source !== 'uploaded' && (
                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => handleDownloadArchive(archive.id)}
                          title="تحميل"
                          className="h-8 w-8"
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      )}
                      {restoreArchiveId === archive.id ? (
                        <div className="flex items-center gap-1">
                          <Button 
                            variant="default" 
                            size="sm"
                            onClick={() => handleRestoreArchive(archive.id)}
                            disabled={actionLoading}
                            className="h-8"
                          >
                            {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'تأكيد'}
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => setRestoreArchiveId(null)}
                            className="h-8"
                          >
                            <XCircle className="w-4 h-4" />
                          </Button>
                        </div>
                      ) : archive.source !== 'uploaded' ? (
                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => setRestoreArchiveId(archive.id)}
                          title="استعادة"
                          className="h-8 w-8"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </Button>
                      ) : null}
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={() => handleDeleteArchive(archive.id)}
                        className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                        title="حذف"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Maintenance Logs */}
      <Card data-testid="maintenance-logs-card">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary" />
            <CardTitle>سجل العمليات</CardTitle>
            <Badge variant="secondary">{maintenanceLogs.length}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {maintenanceLogs.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">
              <Clock className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p>لا توجد عمليات مسجلة</p>
            </div>
          ) : (
            <div className="space-y-2">
              {maintenanceLogs.map((log) => (
                <div 
                  key={log.id}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg text-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-1.5 rounded-lg ${
                      log.type === 'purge' ? 'bg-red-100' : 
                      log.type === 'archive' ? 'bg-blue-100' : 'bg-green-100'
                    }`}>
                      {log.type === 'purge' && <Trash2 className="w-4 h-4 text-red-600" />}
                      {log.type === 'archive' && <Archive className="w-4 h-4 text-blue-600" />}
                      {log.type === 'restore' && <RotateCcw className="w-4 h-4 text-green-600" />}
                    </div>
                    <div>
                      <span className="font-medium">{
                        log.action === 'purge_all_transactions' ? 'حذف جميع المعاملات' :
                        log.action === 'create_full_archive' ? 'إنشاء أرشيف' :
                        log.action === 'restore_from_archive' ? 'استعادة من أرشيف' :
                        log.action === 'restore_from_uploaded_file' ? 'استعادة من ملف مرفوع' :
                        log.action === 'delete_archive' ? 'حذف أرشيف' :
                        log.action
                      }</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-muted-foreground text-xs">
                    <span>{log.performed_by_name}</span>
                    <span>{formatDate(log.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
