import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Sun, Moon, Globe, Pencil, Loader2 } from 'lucide-react';
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

  return (
    <div className="space-y-6 max-w-2xl" data-testid="settings-page">
      <h1 className="text-2xl font-bold tracking-tight">{t('settings.title')}</h1>

      <Card className="border border-border shadow-none">
        <CardHeader><CardTitle className="text-base">{t('settings.appearance')}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {theme === 'light' ? <Sun size={20} className="text-amber-500" /> : <Moon size={20} className="text-blue-400" />}
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
    </div>
  );
}
