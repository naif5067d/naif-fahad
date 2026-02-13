import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Sun, Moon, Globe } from 'lucide-react';

export default function SettingsPage() {
  const { t, lang, toggleLang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();

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
        <CardHeader><CardTitle className="text-base">{t('settings.profile')}</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
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
