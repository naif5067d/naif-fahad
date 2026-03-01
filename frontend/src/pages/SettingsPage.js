import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Sun, Moon, Globe, Pencil, Loader2, AlertTriangle, Trash2, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';
import api from '@/lib/api';

export default function SettingsPage() {
  const { t, lang, toggleLang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();
  
  const [editNameOpen, setEditNameOpen] = useState(false);
  const [nameForm, setNameForm] = useState({
    full_name: user?.full_name || '',
    full_name_ar: user?.full_name_ar || ''
  });
  const [saving, setSaving] = useState(false);
  
  // Nuclear Reset State
  const [nuclearOpen, setNuclearOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [nuclearLoading, setNuclearLoading] = useState(false);
  
  const canNuclearReset = user?.role === 'stas' || user?.role === 'sultan';

  const handleSaveName = async () => {
    if (!nameForm.full_name && !nameForm.full_name_ar) {
      toast.error(lang === 'ar' ? 'أدخل الاسم' : 'Enter name');
      return;
    }
    
    setSaving(true);
    try {
      await api.patch(`/api/employees/${user.employee_id}`, {
        full_name: nameForm.full_name,
        full_name_ar: nameForm.full_name_ar
      });
      toast.success(lang === 'ar' ? 'تم تحديث الاسم بنجاح' : 'Name updated successfully');
      setEditNameOpen(false);
      // Refresh page to update user context
      window.location.reload();
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل تحديث الاسم' : 'Failed to update name'));
    } finally {
      setSaving(false);
    }
  };
  
  // Nuclear Reset Handler
  const handleNuclearReset = async () => {
    if (confirmText !== 'تصفير نووي') {
      toast.error(lang === 'ar' ? 'يجب كتابة "تصفير نووي" بالضبط' : 'You must type "تصفير نووي" exactly');
      return;
    }
    
    setNuclearLoading(true);
    try {
      const res = await api.post('/api/admin/nuclear-reset', {
        confirm_text: confirmText
      });
      toast.success(res.data.message_ar || 'تم التصفير بنجاح');
      setNuclearOpen(false);
      setConfirmText('');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل التصفير' : 'Reset failed'));
    } finally {
      setNuclearLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl" data-testid="settings-page">
      <h1 className="text-2xl font-bold tracking-tight">{t('settings.title')}</h1>

      <Card className="border border-border shadow-none">
        <CardHeader><CardTitle className="text-base">{t('settings.appearance')}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {theme === 'light' ? <Sun size={20} className="text-[hsl(var(--warning))]" /> : <Moon size={20} className="text-blue-400" />}
              <span className="text-sm">{theme === 'light' ? t('theme.light') : t('theme.dark')}</span>
            </div>
            <Button data-testid="settings-theme-toggle" variant="outline" size="sm" onClick={toggleTheme}>
              {theme === 'light' ? <Moon size={14} className="me-1" /> : <Sun size={14} className="me-1" />}
              {t('theme.toggle')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border shadow-none">
        <CardHeader><CardTitle className="text-base">{t('settings.language')}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Globe size={20} className="text-primary" />
              <span className="text-sm">{t('lang.current')}</span>
            </div>
            <Button data-testid="settings-lang-toggle" variant="outline" size="sm" onClick={toggleLang}>
              {t('lang.toggle')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border border-border shadow-none">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{t('settings.profile')}</CardTitle>
            {user?.employee_id && (
              <Dialog open={editNameOpen} onOpenChange={setEditNameOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8">
                    <Pencil size={14} className="me-1" />
                    {lang === 'ar' ? 'تعديل الاسم' : 'Edit Name'}
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{lang === 'ar' ? 'تعديل الاسم' : 'Edit Name'}</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-2">
                    <div>
                      <Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Name (English)'}</Label>
                      <Input 
                        value={nameForm.full_name}
                        onChange={e => setNameForm(p => ({ ...p, full_name: e.target.value }))}
                        placeholder="Sultan Al-Zamil"
                        data-testid="edit-name-en"
                      />
                    </div>
                    <div>
                      <Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Name (Arabic)'}</Label>
                      <Input 
                        value={nameForm.full_name_ar}
                        onChange={e => setNameForm(p => ({ ...p, full_name_ar: e.target.value }))}
                        placeholder="سلطان الزامل"
                        dir="rtl"
                        data-testid="edit-name-ar"
                      />
                    </div>
                    <Button onClick={handleSaveName} disabled={saving} className="w-full" data-testid="save-name-btn">
                      {saving && <Loader2 size={14} className="me-2 animate-spin" />}
                      {lang === 'ar' ? 'حفظ' : 'Save'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{lang === 'ar' ? 'الاسم' : 'Name'}</span>
              <span className="font-medium">{lang === 'ar' ? user?.full_name_ar : user?.full_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('settings.username')}</span>
              <span className="font-medium">{user?.username}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('settings.role')}</span>
              <span className="font-medium">{user?.role === 'stas' ? 'STAS' : t(`roles.${user?.role}`)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t('settings.employeeId')}</span>
              <span className="font-medium">{user?.employee_id || '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Nuclear Reset Section - Only for STAS/Sultan */}
      {canNuclearReset && (
        <Card className="border-2 border-red-500/30 bg-red-500/5 shadow-none">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-red-500" />
              <CardTitle className="text-base text-red-600 dark:text-red-400">
                {lang === 'ar' ? 'منطقة الخطر' : 'Danger Zone'}
              </CardTitle>
            </div>
            <CardDescription className="text-red-600/70 dark:text-red-400/70">
              {lang === 'ar' 
                ? 'إجراءات لا يمكن التراجع عنها - استخدم بحذر شديد'
                : 'Irreversible actions - Use with extreme caution'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Dialog open={nuclearOpen} onOpenChange={setNuclearOpen}>
              <DialogTrigger asChild>
                <Button 
                  variant="destructive" 
                  className="w-full gap-2"
                  data-testid="nuclear-reset-btn"
                >
                  <Trash2 className="h-4 w-4" />
                  {lang === 'ar' ? 'تصفير نووي' : 'Nuclear Reset'}
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-full bg-red-100 dark:bg-red-900/30">
                      <AlertTriangle className="h-6 w-6 text-red-600" />
                    </div>
                    <DialogTitle className="text-red-600">
                      {lang === 'ar' ? '⚠️ تحذير: حذف نووي!' : '⚠️ Warning: Nuclear Delete!'}
                    </DialogTitle>
                  </div>
                  <DialogDescription className="text-right space-y-3 pt-2">
                    <p className="font-semibold text-foreground">
                      {lang === 'ar' 
                        ? 'هذا الإجراء سيحذف جميع البيانات التجريبية نهائياً!'
                        : 'This action will permanently delete all test data!'}
                    </p>
                    <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg text-sm">
                      <p className="font-medium mb-2 text-red-700 dark:text-red-400">
                        {lang === 'ar' ? 'سيتم حذف:' : 'Will be deleted:'}
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-red-600/80 dark:text-red-400/80">
                        <li>{lang === 'ar' ? 'جميع سجلات الحضور والبصمات' : 'All attendance records'}</li>
                        <li>{lang === 'ar' ? 'جميع المعاملات والطلبات' : 'All transactions and requests'}</li>
                        <li>{lang === 'ar' ? 'جميع سجلات الإجازات' : 'All leave records'}</li>
                        <li>{lang === 'ar' ? 'جميع العقوبات والخصومات' : 'All penalties and deductions'}</li>
                        <li>{lang === 'ar' ? 'جميع الإشعارات والإعلانات' : 'All notifications'}</li>
                      </ul>
                    </div>
                    <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg text-sm">
                      <p className="font-medium mb-2 text-green-700 dark:text-green-400">
                        {lang === 'ar' ? 'سيبقى:' : 'Will remain:'}
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-green-600/80 dark:text-green-400/80">
                        <li>{lang === 'ar' ? 'الموظفين والمستخدمين' : 'Employees and users'}</li>
                        <li>{lang === 'ar' ? 'العقود' : 'Contracts'}</li>
                        <li>{lang === 'ar' ? 'مواقع العمل' : 'Work locations'}</li>
                        <li>{lang === 'ar' ? 'إعدادات الشركة' : 'Company settings'}</li>
                      </ul>
                    </div>
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label className="text-sm font-medium">
                      {lang === 'ar' 
                        ? 'للتأكيد، اكتب "تصفير نووي":'
                        : 'To confirm, type "تصفير نووي":'}
                    </Label>
                    <Input
                      value={confirmText}
                      onChange={(e) => setConfirmText(e.target.value)}
                      placeholder="تصفير نووي"
                      className="mt-2 text-center font-bold"
                      dir="rtl"
                      data-testid="nuclear-confirm-input"
                    />
                  </div>
                </div>
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setNuclearOpen(false);
                      setConfirmText('');
                    }}
                  >
                    {lang === 'ar' ? 'إلغاء' : 'Cancel'}
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleNuclearReset}
                    disabled={confirmText !== 'تصفير نووي' || nuclearLoading}
                    data-testid="nuclear-confirm-btn"
                  >
                    {nuclearLoading && <Loader2 className="h-4 w-4 me-2 animate-spin" />}
                    {lang === 'ar' ? 'تنفيذ التصفير' : 'Execute Reset'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
