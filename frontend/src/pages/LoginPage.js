import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Lock, User, AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.response?.data?.detail || t('login.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left: Form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-sm">
          <div className="mb-10">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center mb-6">
              <Lock className="text-primary-foreground" size={20} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground" data-testid="login-title">
              {t('login.title')}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">{t('login.subtitle')}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 border border-destructive/20 text-sm text-destructive" data-testid="login-error">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="username">{t('login.username')}</Label>
              <div className="relative">
                <User size={16} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="username"
                  data-testid="login-username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="ps-9"
                  placeholder={t('login.username')}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('login.password')}</Label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  data-testid="login-password"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="ps-9"
                  placeholder={t('login.password')}
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            <Button data-testid="login-submit" type="submit" className="w-full bg-primary text-primary-foreground hover:bg-primary/90" disabled={loading}>
              {loading ? t('common.loading') : t('login.submit')}
            </Button>

            <p className="text-xs text-center text-muted-foreground mt-4">{t('login.noSignup')}</p>
          </form>

          <div className="mt-8 flex justify-center">
            <button data-testid="login-lang-toggle" onClick={toggleLang} className="text-xs text-muted-foreground hover:text-foreground transition-colors">
              {t('lang.toggle')}
            </button>
          </div>
        </div>
      </div>

      {/* Right: Decorative panel (desktop only) */}
      <div className="hidden lg:flex lg:flex-1 bg-primary/5 items-center justify-center p-12 border-s border-border">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 rounded-2xl bg-primary/10 mx-auto mb-6 flex items-center justify-center">
            <Lock size={32} className="text-primary" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">
            {lang === 'ar' ? 'نظام الموارد البشرية' : 'HR Operating System'}
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {lang === 'ar'
              ? 'نظام متكامل لإدارة المعاملات والموارد البشرية مع مسارات موافقة آمنة وسجلات غير قابلة للتعديل'
              : 'Enterprise-grade transaction management with secure approval workflows and immutable audit trails'
            }
          </p>
        </div>
      </div>
    </div>
  );
}
