import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import api from '../api';
import { 
  Database, 
  Trash2, 
  Archive, 
  Download, 
  Upload, 
  HardDrive,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileArchive,
  RefreshCw,
  Info,
  Shield
} from 'lucide-react';

export default function SystemMaintenancePage() {
  const { t } = useTranslation();
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

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [storageRes, archivesRes, logsRes] = await Promise.all([
        api.get('/api/maintenance/storage-info'),
        api.get('/api/maintenance/archives'),
        api.get('/api/maintenance/logs?limit=20')
      ]);
      setStorageInfo(storageRes.data);
      setArchives(archivesRes.data.archives || []);
      setMaintenanceLogs(logsRes.data.logs || []);
    } catch (error) {
      toast.error('خطأ في تحميل البيانات');
    }
    setLoading(false);
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

  const formatBytes = (kb) => {
    if (kb < 1024) return `${kb} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('ar-SA', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
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
      <div className="flex items-center gap-3">
        <Shield className="w-8 h-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">صيانة النظام</h1>
          <p className="text-muted-foreground">إدارة الأرشفة والحذف ومعلومات التخزين</p>
        </div>
      </div>

      {/* Storage Info */}
      <Card data-testid="storage-info-card">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5" />
            <CardTitle>معلومات التخزين</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {storageInfo && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {storageInfo.totals.total_documents}
                </div>
                <div className="text-sm text-blue-700">إجمالي السجلات</div>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">
                  {storageInfo.totals.transaction_documents}
                </div>
                <div className="text-sm text-orange-700">سجلات المعاملات</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {storageInfo.totals.protected_documents}
                </div>
                <div className="text-sm text-green-700">سجلات محمية</div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {storageInfo.totals.total_collections}
                </div>
                <div className="text-sm text-purple-700">Collections</div>
              </div>
            </div>
          )}

          {/* Collections Details */}
          {storageInfo && (
            <div className="mt-6">
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Database className="w-4 h-4" />
                تفاصيل Collections
              </h3>
              <div className="grid gap-2">
                {Object.entries(storageInfo.collections).map(([name, info]) => (
                  <div 
                    key={name} 
                    className={`flex items-center justify-between p-2 rounded text-sm ${
                      info.is_protected ? 'bg-green-50' : 'bg-orange-50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {info.is_protected ? (
                        <Shield className="w-4 h-4 text-green-600" />
                      ) : (
                        <Database className="w-4 h-4 text-orange-600" />
                      )}
                      <span className="font-mono">{name}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span>{info.documents} سجل</span>
                      <span className="text-muted-foreground">
                        {formatBytes(info.estimated_size_kb || 0)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-xs text-muted-foreground flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <Shield className="w-3 h-3 text-green-600" /> محمية (لا تُحذف)
                </span>
                <span className="flex items-center gap-1">
                  <Database className="w-3 h-3 text-orange-600" /> معاملات (قابلة للحذف)
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions Row */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Archive Action */}
        <Card data-testid="archive-action-card">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Archive className="w-5 h-5 text-blue-600" />
              <CardTitle>أرشفة النظام</CardTitle>
            </div>
            <CardDescription>
              حفظ نسخة كاملة من النظام للرجوع إليها لاحقاً
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!showCreateArchive ? (
              <Button 
                onClick={() => setShowCreateArchive(true)}
                className="w-full"
                data-testid="create-archive-btn"
              >
                <FileArchive className="w-4 h-4 ml-2" />
                إنشاء أرشيف جديد
              </Button>
            ) : (
              <div className="space-y-3">
                <Input
                  placeholder="اسم الأرشيف (اختياري)"
                  value={archiveName}
                  onChange={(e) => setArchiveName(e.target.value)}
                />
                <Input
                  placeholder="وصف (اختياري)"
                  value={archiveDescription}
                  onChange={(e) => setArchiveDescription(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button 
                    onClick={handleCreateArchive}
                    disabled={actionLoading}
                    className="flex-1"
                  >
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'إنشاء'}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => setShowCreateArchive(false)}
                  >
                    إلغاء
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Purge Action */}
        <Card data-testid="purge-action-card" className="border-red-200">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-600" />
              <CardTitle className="text-red-600">حذف جميع المعاملات</CardTitle>
            </div>
            <CardDescription>
              حذف كل المعاملات والسجلات (لا يؤثر على المستخدمين والموظفين)
            </CardDescription>
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
                <div className="p-3 bg-red-50 rounded-lg text-red-700 text-sm">
                  <AlertTriangle className="w-4 h-4 inline ml-1" />
                  تحذير: سيتم حذف جميع المعاملات والسجلات بشكل نهائي!
                </div>
                <Input
                  placeholder="اكتب DELETE ALL للتأكيد"
                  value={purgeConfirmText}
                  onChange={(e) => setPurgeConfirmText(e.target.value)}
                  className="font-mono"
                />
                <div className="flex gap-2">
                  <Button 
                    variant="destructive"
                    onClick={handlePurgeAll}
                    disabled={actionLoading || purgeConfirmText !== 'DELETE ALL'}
                    className="flex-1"
                  >
                    {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'تأكيد الحذف'}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => {
                      setShowPurgeConfirm(false);
                      setPurgeConfirmText('');
                    }}
                  >
                    إلغاء
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Archives List */}
      <Card data-testid="archives-list-card">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileArchive className="w-5 h-5" />
              <CardTitle>الأرشيفات المحفوظة</CardTitle>
            </div>
            <Button variant="ghost" size="sm" onClick={loadData}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {archives.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              لا توجد أرشيفات محفوظة
            </div>
          ) : (
            <div className="space-y-3">
              {archives.map((archive) => (
                <div 
                  key={archive.id}
                  className="p-4 border rounded-lg"
                  data-testid={`archive-${archive.id}`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium">{archive.name}</h4>
                      <p className="text-sm text-muted-foreground">{archive.description}</p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatDate(archive.created_at)}
                        </span>
                        <span>{archive.stats?.total_documents} سجل</span>
                        <span>{formatBytes(archive.size_compressed_kb)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleDownloadArchive(archive.id)}
                        title="تحميل"
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                      {restoreArchiveId === archive.id ? (
                        <div className="flex items-center gap-1">
                          <Button 
                            variant="default" 
                            size="sm"
                            onClick={() => handleRestoreArchive(archive.id)}
                            disabled={actionLoading}
                          >
                            {actionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'تأكيد'}
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => setRestoreArchiveId(null)}
                          >
                            إلغاء
                          </Button>
                        </div>
                      ) : (
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => setRestoreArchiveId(archive.id)}
                          title="استعادة"
                        >
                          <Upload className="w-4 h-4" />
                        </Button>
                      )}
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleDeleteArchive(archive.id)}
                        className="text-red-600 hover:text-red-700"
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
            <Clock className="w-5 h-5" />
            <CardTitle>سجل العمليات</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {maintenanceLogs.length === 0 ? (
            <div className="text-center text-muted-foreground py-4">
              لا توجد عمليات مسجلة
            </div>
          ) : (
            <div className="space-y-2">
              {maintenanceLogs.map((log) => (
                <div 
                  key={log.id}
                  className="flex items-center justify-between p-2 bg-muted/50 rounded text-sm"
                >
                  <div className="flex items-center gap-2">
                    {log.type === 'purge' && <Trash2 className="w-4 h-4 text-red-600" />}
                    {log.type === 'archive' && <Archive className="w-4 h-4 text-blue-600" />}
                    {log.type === 'restore' && <Upload className="w-4 h-4 text-green-600" />}
                    <span>{log.action}</span>
                  </div>
                  <div className="flex items-center gap-4 text-muted-foreground">
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
