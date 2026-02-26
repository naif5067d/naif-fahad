import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Upload, History, RefreshCw, Check, AlertCircle, Edit2, Rocket } from 'lucide-react';
import { toast } from 'sonner';
import api from '@/lib/api';

export default function VersionManagementPage() {
  const { lang } = useLanguage();
  const isRTL = lang === 'ar';
  
  const [currentVersion, setCurrentVersion] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [formData, setFormData] = useState({
    version: '',
    release_notes: '',
    force_refresh: true
  });

  // جلب البيانات
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [versionRes, historyRes] = await Promise.all([
        api.get('/api/admin/app-version'),
        api.get('/api/admin/app-version/history')
      ]);
      setCurrentVersion(versionRes.data);
      setHistory(historyRes.data.history || []);
    } catch (err) {
      toast.error(isRTL ? 'خطأ في جلب البيانات' : 'Error fetching data');
    } finally {
      setLoading(false);
    }
  };

  // تحديث تلقائي (زيادة رقم واحد)
  const handleQuickUpdate = async () => {
    setUpdating(true);
    try {
      const res = await api.post('/api/admin/app-version/update', {
        force_refresh: true
      });
      toast.success(res.data.message);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || (isRTL ? 'حدث خطأ' : 'Error occurred'));
    } finally {
      setUpdating(false);
    }
  };

  // تحديث يدوي
  const handleManualUpdate = async (e) => {
    e.preventDefault();
    setUpdating(true);
    try {
      const res = await api.post('/api/admin/app-version/update', formData);
      toast.success(res.data.message);
      setShowEditModal(false);
      setFormData({ version: '', release_notes: '', force_refresh: true });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || (isRTL ? 'حدث خطأ' : 'Error occurred'));
    } finally {
      setUpdating(false);
    }
  };

  // فتح نافذة التعديل اليدوي
  const openEditModal = () => {
    if (currentVersion) {
      setFormData({
        version: currentVersion.version || '1.0.0',
        release_notes: '',
        force_refresh: true
      });
    }
    setShowEditModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Rocket size={24} className="text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold" data-testid="version-management-title">
              {isRTL ? 'إدارة إصدار التطبيق' : 'App Version Management'}
            </h1>
            <p className="text-sm text-muted-foreground">
              {isRTL ? 'تحديث التطبيق وإجبار جميع المستخدمين على التحديث' : 'Update app and force all users to refresh'}
            </p>
          </div>
        </div>
      </div>

      {/* Current Version Card */}
      <div className="card-premium p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Check size={20} className="text-green-500" />
            {isRTL ? 'الإصدار الحالي' : 'Current Version'}
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={openEditModal}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
              data-testid="manual-update-btn"
            >
              <Edit2 size={16} />
              {isRTL ? 'تعديل يدوي' : 'Manual Edit'}
            </button>
            <button
              onClick={handleQuickUpdate}
              disabled={updating}
              className="flex items-center gap-2 px-5 py-2.5 text-sm bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50"
              data-testid="quick-update-btn"
            >
              {updating ? (
                <RefreshCw size={16} className="animate-spin" />
              ) : (
                <Upload size={16} />
              )}
              {isRTL ? 'نشر تحديث فوري' : 'Deploy Update Now'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Version Number */}
          <div className="bg-muted/50 rounded-xl p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">
              {isRTL ? 'رقم الإصدار' : 'Version'}
            </p>
            <p className="text-3xl font-bold text-primary" data-testid="current-version">
              {currentVersion?.version || '1.0.0'}
            </p>
          </div>

          {/* Build Number */}
          <div className="bg-muted/50 rounded-xl p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">
              {isRTL ? 'رقم البناء' : 'Build'}
            </p>
            <p className="text-3xl font-bold" data-testid="current-build">
              #{currentVersion?.build || 1}
            </p>
          </div>

          {/* Last Update */}
          <div className="bg-muted/50 rounded-xl p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">
              {isRTL ? 'آخر تحديث' : 'Last Update'}
            </p>
            <p className="text-sm font-medium">
              {currentVersion?.updated_at 
                ? new Date(currentVersion.updated_at).toLocaleDateString(isRTL ? 'ar-SA' : 'en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : (isRTL ? 'لم يتم التحديث' : 'Not updated yet')
              }
            </p>
          </div>

          {/* Updated By */}
          <div className="bg-muted/50 rounded-xl p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">
              {isRTL ? 'بواسطة' : 'Updated By'}
            </p>
            <p className="text-sm font-medium">
              {currentVersion?.updated_by || '-'}
            </p>
          </div>
        </div>

        {/* Release Notes */}
        {currentVersion?.release_notes && (
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 rounded-xl border border-blue-200 dark:border-blue-800">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
              {isRTL ? 'ملاحظات الإصدار:' : 'Release Notes:'}
            </p>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              {currentVersion.release_notes}
            </p>
          </div>
        )}

        {/* How it works */}
        <div className="mt-6 p-4 bg-amber-50 dark:bg-amber-950/30 rounded-xl border border-amber-200 dark:border-amber-800">
          <div className="flex items-start gap-3">
            <AlertCircle size={20} className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                {isRTL ? 'كيف يعمل؟' : 'How does it work?'}
              </p>
              <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                {isRTL 
                  ? 'عند الضغط على "نشر تحديث فوري"، سيتم إشعار جميع المستخدمين المتصلين بوجود تحديث جديد. سيُطلب منهم تحديث الصفحة للحصول على آخر نسخة.'
                  : 'When you click "Deploy Update Now", all connected users will be notified about the new update. They will be prompted to refresh the page to get the latest version.'
                }
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Version History */}
      <div className="card-premium p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <History size={20} />
          {isRTL ? 'سجل الإصدارات' : 'Version History'}
        </h2>

        {history.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <History size={40} className="mx-auto mb-3 opacity-30" />
            <p>{isRTL ? 'لا يوجد سجل إصدارات بعد' : 'No version history yet'}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((item, idx) => (
              <div 
                key={item.id || idx} 
                className="flex items-center justify-between p-4 bg-muted/30 rounded-xl hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <span className="text-sm font-bold text-primary">v{item.new_version}</span>
                  </div>
                  <div>
                    <p className="font-medium">
                      {item.old_version} → {item.new_version}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Build #{item.build} • {isRTL ? 'بواسطة' : 'by'} {item.updated_by}
                    </p>
                  </div>
                </div>
                <div className="text-end">
                  <p className="text-sm text-muted-foreground">
                    {new Date(item.created_at).toLocaleDateString(isRTL ? 'ar-SA' : 'en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleTimeString(isRTL ? 'ar-SA' : 'en-US', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-fade-in">
            <h3 className="text-lg font-bold mb-4">
              {isRTL ? 'تعديل رقم الإصدار يدوياً' : 'Manual Version Edit'}
            </h3>
            
            <form onSubmit={handleManualUpdate} className="space-y-4">
              {/* Version Input */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  {isRTL ? 'رقم الإصدار' : 'Version Number'}
                </label>
                <input
                  type="text"
                  value={formData.version}
                  onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                  placeholder="e.g., 2.0.0"
                  className="w-full px-4 py-2.5 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                  data-testid="version-input"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {isRTL ? 'مثال: 1.0.0 أو 2.5.1' : 'Example: 1.0.0 or 2.5.1'}
                </p>
              </div>

              {/* Release Notes */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  {isRTL ? 'ملاحظات الإصدار (اختياري)' : 'Release Notes (optional)'}
                </label>
                <textarea
                  value={formData.release_notes}
                  onChange={(e) => setFormData({ ...formData, release_notes: e.target.value })}
                  placeholder={isRTL ? 'وصف التحديث...' : 'Describe the update...'}
                  rows={3}
                  className="w-full px-4 py-2.5 rounded-lg border border-border bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none resize-none"
                  data-testid="release-notes-input"
                />
              </div>

              {/* Force Refresh Toggle */}
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div>
                  <p className="text-sm font-medium">
                    {isRTL ? 'إجبار المستخدمين على التحديث' : 'Force users to update'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {isRTL ? 'سيظهر إشعار للمستخدمين' : 'Users will see update notification'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, force_refresh: !formData.force_refresh })}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    formData.force_refresh ? 'bg-primary' : 'bg-muted'
                  }`}
                  data-testid="force-refresh-toggle"
                >
                  <div className={`w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    formData.force_refresh ? (isRTL ? '-translate-x-6' : 'translate-x-6') : (isRTL ? '-translate-x-0.5' : 'translate-x-0.5')
                  }`} />
                </button>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="flex-1 px-4 py-2.5 rounded-lg border border-border hover:bg-muted transition-colors"
                  data-testid="cancel-edit-btn"
                >
                  {isRTL ? 'إلغاء' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="flex-1 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  data-testid="save-version-btn"
                >
                  {updating ? (
                    <RefreshCw size={16} className="animate-spin" />
                  ) : (
                    <Check size={16} />
                  )}
                  {isRTL ? 'حفظ ونشر' : 'Save & Deploy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
