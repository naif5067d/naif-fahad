import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Lock, User, AlertCircle, Eye, EyeOff, Globe, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function LoginPage() {
  const { login } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  // إعدادات الشركة - دار الكود
  const [settings, setSettings] = useState({
    logo_url: null,
    side_image_url: null,
    welcome_text_ar: 'أنتم الدار ونحن الكود',
    welcome_text_en: 'You are the Home, We are the Code',
    primary_color: '#1E3A5F',
    secondary_color: '#A78BFA',
    company_name_ar: 'شركة دار الكود للاستشارات الهندسية',
    company_name_en: 'Dar Al Code Engineering Consultancy'
  });

  // تحميل إعدادات الشركة (بدون مصادقة)
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const res = await fetch(`${API_URL}/api/company-settings/public`);
        if (res.ok) {
          const data = await res.json();
          setSettings(prev => ({ ...prev, ...data }));
        }
      } catch (err) {
        console.log('Using default settings');
      }
    };
    loadSettings();
  }, []);

  // مسح الجلسة السابقة عند فتح صفحة تسجيل الدخول مباشرة
  // هذا يضمن أن صفحة /login مستقلة تماماً
  useEffect(() => {
    // تحقق من أن المستخدم وصل لصفحة login مباشرة (ليس redirect)
    const isDirectAccess = !document.referrer || 
                          !document.referrer.includes(window.location.host) ||
                          document.referrer.includes('/login');
    
    // مسح بيانات الجلسة القديمة (ما عدا remember me)
    if (isDirectAccess) {
      localStorage.removeItem('hr_token');
      localStorage.removeItem('hr_user');
      localStorage.removeItem('dar_token');
      localStorage.removeItem('dar_user');
      sessionStorage.clear();
    }
  }, []);

  // تحميل بيانات "تذكرني" من localStorage
  useEffect(() => {
    const savedUsername = localStorage.getItem('dar_remember_username');
    const savedRemember = localStorage.getItem('dar_remember_me');
    if (savedRemember === 'true' && savedUsername) {
      setUsername(savedUsername);
      setRememberMe(true);
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    // حفظ "تذكرني"
    if (rememberMe) {
      localStorage.setItem('dar_remember_username', username);
      localStorage.setItem('dar_remember_me', 'true');
    } else {
      localStorage.removeItem('dar_remember_username');
      localStorage.removeItem('dar_remember_me');
    }
    
    try {
      await login(username, password);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        setError(lang === 'ar' ? detail.message_ar : detail.message_en);
      } else {
        setError(detail || t('login.error'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-slate-50 to-slate-100" data-testid="login-page">
      {/* Left: Form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-sm">
          {/* Logo & Company Name */}
          <div className="mb-10 text-center">
            {settings.logo_url ? (
              <img 
                src={settings.logo_url} 
                alt="Company Logo" 
                className="w-20 h-20 mx-auto mb-4 object-contain rounded-2xl"
              />
            ) : (
              <div 
                className="w-20 h-20 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-lg"
                style={{ 
                  background: `linear-gradient(135deg, ${settings.primary_color}, ${settings.secondary_color})`,
                  boxShadow: `0 10px 15px -3px ${settings.primary_color}33`
                }}
              >
                <span className="text-3xl font-bold text-white">د</span>
              </div>
            )}
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? settings.company_name_ar : settings.company_name_en}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              {lang === 'ar' ? 'للاستشارات الهندسية' : 'Engineering Consultants'}
            </p>
          </div>

          {/* Login Form */}
          <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 p-8 border border-slate-200/50">
            <h2 className="text-lg font-semibold text-slate-700 mb-1" data-testid="login-title">
              {lang === 'ar' ? 'تسجيل الدخول' : 'Sign In'}
            </h2>
            <p className="text-sm text-slate-500 mb-6">
              {lang === 'ar' ? 'أدخل بيانات الدخول للوصول للنظام' : 'Enter your credentials to access the system'}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive" data-testid="login-error">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="username" className="text-slate-600">
                  {lang === 'ar' ? 'اسم المستخدم' : 'Username'}
                </Label>
                <div className="relative">
                  <User size={18} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="username"
                    data-testid="login-username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    className="ps-10 h-11 border-border focus:border-accent focus:ring-accent"
                    placeholder={lang === 'ar' ? 'أدخل اسم المستخدم' : 'Enter username'}
                    autoComplete="username"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-600">
                  {lang === 'ar' ? 'كلمة المرور' : 'Password'}
                </Label>
                <div className="relative">
                  <Lock size={18} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="password"
                    data-testid="login-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="ps-10 pe-10 h-11 border-border focus:border-accent focus:ring-accent"
                    placeholder={lang === 'ar' ? 'أدخل كلمة المرور' : 'Enter password'}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 rtl:right-auto rtl:left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Remember Me */}
              <div className="flex items-center gap-2">
                <Checkbox 
                  id="remember" 
                  checked={rememberMe} 
                  onCheckedChange={setRememberMe}
                  className="border-border data-[state=checked]:bg-accent"
                />
                <Label htmlFor="remember" className="text-sm text-slate-600 cursor-pointer">
                  {lang === 'ar' ? 'تذكرني' : 'Remember me'}
                </Label>
              </div>

              <Button 
                data-testid="login-submit" 
                type="submit" 
                className="w-full h-11 text-white font-medium shadow-lg" 
                style={{ 
                  background: `linear-gradient(135deg, ${settings.primary_color}, ${settings.secondary_color})`,
                  boxShadow: `0 10px 15px -3px ${settings.primary_color}33`
                }}
                disabled={loading}
              >
                {loading ? (
                  <><Loader2 size={18} className="animate-spin mr-2" /> {lang === 'ar' ? 'جاري الدخول...' : 'Signing in...'}</>
                ) : (
                  lang === 'ar' ? 'دخول' : 'Sign In'
                )}
              </Button>
            </form>
          </div>

          {/* Language Toggle */}
          <div className="mt-6 flex justify-center">
            <button 
              data-testid="login-lang-toggle" 
              onClick={toggleLang} 
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-accent transition-colors"
            >
              <Globe size={16} />
              {lang === 'ar' ? 'English' : 'العربية'}
            </button>
          </div>

          {/* Footer */}
          <p className="text-xs text-center text-slate-400 mt-6">
            {lang === 'ar' 
              ? '© 2026 دار الكود. جميع الحقوق محفوظة'
              : '© 2026 DAR AL CODE. All rights reserved'
            }
          </p>
        </div>
      </div>

      {/* Right: Decorative panel (desktop only) */}
      <div 
        className="hidden lg:flex lg:flex-1 items-center justify-center p-12 relative overflow-hidden"
        style={{ 
          background: settings.side_image_url 
            ? `url(${settings.side_image_url}) center/cover no-repeat`
            : `linear-gradient(135deg, ${settings.primary_color}, ${settings.secondary_color})`
        }}
      >
        {/* Overlay for side image */}
        {settings.side_image_url && (
          <div className="absolute inset-0 bg-black/40" />
        )}
        
        {/* Background Pattern (only if no side image) */}
        {!settings.side_image_url && (
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-10 left-10 w-32 h-32 border-4 border-white rounded-full" />
            <div className="absolute bottom-20 right-20 w-48 h-48 border-4 border-white rounded-full" />
            <div className="absolute top-1/2 left-1/3 w-24 h-24 border-4 border-white rounded-full" />
          </div>
        )}
        
        <div className="text-center max-w-md relative z-10">
          {!settings.side_image_url && (
            <>
              <div className="w-24 h-24 rounded-3xl bg-white/10 backdrop-blur mx-auto mb-8 flex items-center justify-center border border-white/20">
                <span className="text-4xl font-bold text-white">د</span>
              </div>
              <h2 className="text-3xl font-bold text-white mb-4">
                {lang === 'ar' ? 'نظام الموارد البشرية' : 'HR Management System'}
              </h2>
            </>
          )}
          
          {/* Welcome Text */}
          <p className="text-white/90 leading-relaxed text-xl font-medium drop-shadow-lg">
            {lang === 'ar' ? settings.welcome_text_ar : settings.welcome_text_en}
          </p>
          
          {/* Features List (only if no side image) */}
          {!settings.side_image_url && (
            <div className="mt-8 grid grid-cols-2 gap-4 text-white/90 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400" />
                <span>{lang === 'ar' ? 'إدارة الحضور' : 'Attendance'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400" />
                <span>{lang === 'ar' ? 'المعاملات' : 'Transactions'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400" />
                <span>{lang === 'ar' ? 'العقود' : 'Contracts'}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-400" />
                <span>{lang === 'ar' ? 'التقارير' : 'Reports'}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
