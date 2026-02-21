import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Lock, User, AlertCircle, Eye, EyeOff, Globe, Loader2 } from 'lucide-react';

export default function LoginPage() {
  const { login } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-700 mx-auto mb-4 flex items-center justify-center shadow-lg shadow-violet-200">
              <span className="text-3xl font-bold text-white">د</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? 'دار الكود' : 'DAR AL CODE'}
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
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-600" data-testid="login-error">
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
                    className="ps-10 h-11 border-slate-200 focus:border-violet-500 focus:ring-violet-500"
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
                    className="ps-10 pe-10 h-11 border-slate-200 focus:border-violet-500 focus:ring-violet-500"
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
                  className="border-slate-300 data-[state=checked]:bg-violet-600"
                />
                <Label htmlFor="remember" className="text-sm text-slate-600 cursor-pointer">
                  {lang === 'ar' ? 'تذكرني' : 'Remember me'}
                </Label>
              </div>

              <Button 
                data-testid="login-submit" 
                type="submit" 
                className="w-full h-11 bg-gradient-to-r from-violet-600 to-accent hover:from-violet-700 hover:to-indigo-700 text-white font-medium shadow-lg shadow-violet-200" 
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
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-violet-600 transition-colors"
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
      <div className="hidden lg:flex lg:flex-1 bg-gradient-to-br from-violet-600 to-indigo-700 items-center justify-center p-12 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-32 h-32 border-4 border-white rounded-full" />
          <div className="absolute bottom-20 right-20 w-48 h-48 border-4 border-white rounded-full" />
          <div className="absolute top-1/2 left-1/3 w-24 h-24 border-4 border-white rounded-full" />
        </div>
        
        <div className="text-center max-w-md relative z-10">
          <div className="w-24 h-24 rounded-3xl bg-white/10 backdrop-blur mx-auto mb-8 flex items-center justify-center border border-white/20">
            <span className="text-4xl font-bold text-white">د</span>
          </div>
          <h2 className="text-3xl font-bold text-white mb-4">
            {lang === 'ar' ? 'نظام الموارد البشرية' : 'HR Management System'}
          </h2>
          <p className="text-white/80 leading-relaxed text-lg">
            {lang === 'ar'
              ? 'نظام متكامل لإدارة الموظفين والحضور والمعاملات المالية مع أعلى معايير الأمان والموثوقية'
              : 'Comprehensive employee management system with attendance tracking, financial transactions, and enterprise-grade security'
            }
          </p>
          
          {/* Features List */}
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
        </div>
      </div>
    </div>
  );
}
