import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Lock, User, AlertCircle, Eye, EyeOff, Globe, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// ==================== موسيقى المكتب الهندسية ====================
let audioContext = null;

const getAudioContext = () => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }
  return audioContext;
};

// موسيقى خلفية فاخرة للمكتب الهندسي - Ambient Corporate
const playAmbientMusic = (stop = false) => {
  if (stop) {
    if (audioContext) {
      audioContext.close();
      audioContext = null;
    }
    return;
  }
  
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;
    
    // نغمة ambient هادئة ومهنية
    const playPad = (freq, startTime, duration, volume = 0.03) => {
      const osc = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();
      
      filter.type = 'lowpass';
      filter.frequency.value = 800;
      filter.Q.value = 0.5;
      
      osc.connect(filter);
      osc2.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      
      osc.type = 'sine';
      osc2.type = 'triangle';
      osc.frequency.value = freq;
      osc2.frequency.value = freq * 1.002; // Slight detune for richness
      
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(volume, startTime + 1);
      gain.gain.setValueAtTime(volume, startTime + duration - 1);
      gain.gain.linearRampToValueAtTime(0, startTime + duration);
      
      osc.start(startTime);
      osc2.start(startTime);
      osc.stop(startTime + duration);
      osc2.stop(startTime + duration);
    };
    
    // تناغم ambient - أكورد هادئ ومهدئ
    playPad(130.81, now, 8, 0.025);      // C3
    playPad(196.00, now + 0.5, 7.5, 0.02); // G3
    playPad(261.63, now + 1, 7, 0.015);    // C4
    playPad(329.63, now + 1.5, 6.5, 0.01); // E4
    
  } catch (e) {
    console.log('Audio not supported');
  }
};

// موسيقى ترحيبية عند تسجيل الدخول بنجاح
const playWelcomeMusic = () => {
  try {
    const ctx = getAudioContext();
    const now = ctx.currentTime;
    
    const playChime = (freq, startTime, duration, volume = 0.12) => {
      const osc = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();
      const reverb = ctx.createConvolver();
      
      filter.type = 'lowpass';
      filter.frequency.value = 3000;
      filter.Q.value = 1;
      
      osc.connect(filter);
      osc2.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      
      osc.type = 'sine';
      osc2.type = 'triangle';
      osc.frequency.value = freq;
      osc2.frequency.value = freq * 2; // Octave for brightness
      
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(volume, startTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(volume * 0.6, startTime + duration * 0.3);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
      
      osc.start(startTime);
      osc2.start(startTime);
      osc.stop(startTime + duration);
      osc2.stop(startTime + duration);
    };
    
    // نغمة ترحيبية فاخرة - مثل فنادق 5 نجوم
    // Ascending major chord with sparkle
    playChime(523.25, now, 0.5, 0.1);           // C5
    playChime(659.25, now + 0.12, 0.5, 0.12);   // E5
    playChime(783.99, now + 0.24, 0.6, 0.14);   // G5
    playChime(1046.50, now + 0.36, 0.8, 0.12);  // C6
    playChime(1318.51, now + 0.48, 1.0, 0.08);  // E6 (sparkle)
    
    // صدى نهائي راقي
    playChime(783.99, now + 0.7, 1.2, 0.05);    // G5 echo
    playChime(1046.50, now + 0.9, 1.5, 0.03);   // C6 final
    
  } catch (e) {
    console.log('Audio not supported');
  }
};

// ==================== رسائل الترحيب ====================
const getGreeting = (lang, userName) => {
  const hour = new Date().getHours();
  const name = userName || (lang === 'ar' ? 'ضيفنا الكريم' : 'Dear Guest');
  
  const greetings = {
    ar: {
      morning: [
        `صباح الخير ${name}`,
        `صباح النور ${name}`,
        `يسعد صباحك ${name}`,
        `صباح الورد ${name}`,
        `صباح السعادة ${name}`
      ],
      afternoon: [
        `مرحباً ${name}`,
        `أهلاً وسهلاً ${name}`,
        `سعداء بعودتك ${name}`,
        `نورت المكتب ${name}`
      ],
      evening: [
        `مساء الخير ${name}`,
        `مساء النور ${name}`,
        `مساء السعادة ${name}`,
        `طابت أوقاتك ${name}`
      ],
      night: [
        `مساء الخير ${name}`,
        `أهلاً بك ${name}`,
        `سهرة سعيدة ${name}`
      ]
    },
    en: {
      morning: [
        `Good morning, ${name}`,
        `Rise and shine, ${name}`,
        `A wonderful morning, ${name}`,
        `Morning sunshine, ${name}`
      ],
      afternoon: [
        `Good afternoon, ${name}`,
        `Welcome back, ${name}`,
        `Great to see you, ${name}`
      ],
      evening: [
        `Good evening, ${name}`,
        `Pleasant evening, ${name}`,
        `Welcome, ${name}`
      ],
      night: [
        `Good evening, ${name}`,
        `Welcome, ${name}`,
        `Hello, ${name}`
      ]
    }
  };
  
  let timeOfDay;
  if (hour >= 5 && hour < 12) timeOfDay = 'morning';
  else if (hour >= 12 && hour < 17) timeOfDay = 'afternoon';
  else if (hour >= 17 && hour < 21) timeOfDay = 'evening';
  else timeOfDay = 'night';
  
  const options = greetings[lang][timeOfDay];
  return options[Math.floor(Math.random() * options.length)];
};

const getSubGreeting = (lang) => {
  const messages = {
    ar: [
      'نتمنى لك يوماً مثمراً',
      'سعيدون بتواجدك معنا',
      'هيا نبدأ يوماً رائعاً',
      'نرحب بك في دار الكود',
      'استعد لإنجازات جديدة'
    ],
    en: [
      'Wishing you a productive day',
      'Glad to have you with us',
      "Let's make today great",
      'Welcome to Dar Al Code',
      'Ready for new achievements'
    ]
  };
  return messages[lang][Math.floor(Math.random() * messages[lang].length)];
};

export default function LoginPage() {
  const { login } = useAuth();
  const { t, lang, toggleLang } = useLanguage();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [greeting, setGreeting] = useState('');
  const [subGreeting, setSubGreeting] = useState('');
  const [mounted, setMounted] = useState(false);
  
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

  // Animation on mount
  useEffect(() => {
    setMounted(true);
    return () => {
      playAmbientMusic(true); // Stop music on unmount
    };
  }, []);

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
  useEffect(() => {
    const isDirectAccess = !document.referrer || 
                          !document.referrer.includes(window.location.host) ||
                          document.referrer.includes('/login');
    
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

  // تشغيل الموسيقى عند النقر
  const toggleMusic = () => {
    if (!musicEnabled) {
      playAmbientMusic();
      setMusicEnabled(true);
    } else {
      playAmbientMusic(true);
      setMusicEnabled(false);
    }
  };

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
      const userData = await login(username, password);
      
      // إيقاف موسيقى الخلفية
      playAmbientMusic(true);
      
      // تشغيل موسيقى الترحيب
      playWelcomeMusic();
      
      // إظهار رسالة الترحيب
      const userName = userData?.full_name_ar || userData?.full_name || username;
      setGreeting(getGreeting(lang, userName));
      setSubGreeting(getSubGreeting(lang));
      setShowWelcome(true);
      
      // الانتظار ثم التوجيه
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 2500);
      
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        setError(lang === 'ar' ? detail.message_ar : detail.message_en);
      } else {
        setError(detail || t('login.error'));
      }
      setLoading(false);
    }
  };

  // إذا كان في وضع الترحيب
  if (showWelcome) {
    return (
      <div 
        className="min-h-screen flex items-center justify-center overflow-hidden"
        style={{ 
          background: `linear-gradient(135deg, ${settings.primary_color}, ${settings.secondary_color})`
        }}
      >
        {/* Animated background elements */}
        <div className="absolute inset-0 overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute rounded-full bg-white/10 animate-float"
              style={{
                width: Math.random() * 100 + 50,
                height: Math.random() * 100 + 50,
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 5}s`,
                animationDuration: `${Math.random() * 10 + 10}s`
              }}
            />
          ))}
        </div>
        
        <div className="relative z-10 text-center px-6 animate-welcome-in">
          {/* Logo */}
          <div className="w-24 h-24 rounded-3xl bg-white/20 backdrop-blur-lg mx-auto mb-8 flex items-center justify-center border border-white/30 animate-logo-pulse">
            <span className="text-5xl font-bold text-white">د</span>
          </div>
          
          {/* Greeting */}
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 animate-text-reveal">
            {greeting}
          </h1>
          
          <p className="text-xl text-white/80 animate-text-reveal-delay">
            {subGreeting}
          </p>
          
          {/* Loading indicator */}
          <div className="mt-12 flex justify-center">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-3 h-3 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-3 h-3 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`min-h-screen flex bg-gradient-to-br from-slate-50 to-slate-100 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`} 
      data-testid="login-page"
    >
      {/* Left: Form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 relative">
        {/* Music Toggle */}
        <button
          onClick={toggleMusic}
          className={`absolute top-4 right-4 rtl:right-auto rtl:left-4 p-3 rounded-full transition-all duration-300 ${
            musicEnabled 
              ? 'bg-accent/20 text-accent' 
              : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
          }`}
          title={musicEnabled ? (lang === 'ar' ? 'إيقاف الموسيقى' : 'Mute') : (lang === 'ar' ? 'تشغيل الموسيقى' : 'Play music')}
        >
          {musicEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
        </button>
        
        <div className={`w-full max-w-sm transition-all duration-700 delay-200 ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
          {/* Logo & Company Name */}
          <div className="mb-10 text-center">
            {settings.logo_url ? (
              <img 
                src={settings.logo_url} 
                alt="Company Logo" 
                className="w-20 h-20 mx-auto mb-4 object-contain rounded-2xl animate-logo-float"
              />
            ) : (
              <div 
                className="w-20 h-20 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-lg animate-logo-float"
                style={{ 
                  background: `linear-gradient(135deg, ${settings.primary_color}, ${settings.secondary_color})`,
                  boxShadow: `0 10px 40px -10px ${settings.primary_color}66`
                }}
              >
                <span className="text-3xl font-bold text-white">د</span>
              </div>
            )}
            <h1 className="text-2xl font-bold text-slate-800 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              {lang === 'ar' ? settings.company_name_ar : settings.company_name_en}
            </h1>
            <p className="text-sm text-slate-500 mt-1 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
              {lang === 'ar' ? 'للاستشارات الهندسية' : 'Engineering Consultants'}
            </p>
          </div>

          {/* Login Form */}
          <div 
            className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 p-8 border border-slate-200/50 animate-fade-in-up"
            style={{ animationDelay: '0.5s' }}
          >
            <h2 className="text-lg font-semibold text-slate-700 mb-1" data-testid="login-title">
              {lang === 'ar' ? 'تسجيل الدخول' : 'Sign In'}
            </h2>
            <p className="text-sm text-slate-500 mb-6">
              {lang === 'ar' ? 'أدخل بيانات الدخول للوصول للنظام' : 'Enter your credentials to access the system'}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive animate-shake" data-testid="login-error">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="username" className="text-slate-600">
                  {lang === 'ar' ? 'اسم المستخدم' : 'Username'}
                </Label>
                <div className="relative group">
                  <User size={18} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-accent" />
                  <Input
                    id="username"
                    data-testid="login-username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    className="ps-10 h-12 border-slate-200 focus:border-accent focus:ring-accent transition-all"
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
                <div className="relative group">
                  <Lock size={18} className="absolute left-3 rtl:left-auto rtl:right-3 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-accent" />
                  <Input
                    id="password"
                    data-testid="login-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className="ps-10 pe-10 h-12 border-slate-200 focus:border-accent focus:ring-accent transition-all"
                    placeholder={lang === 'ar' ? 'أدخل كلمة المرور' : 'Enter password'}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 rtl:right-auto rtl:left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
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
                  className="border-slate-300 data-[state=checked]:bg-accent data-[state=checked]:border-accent"
                />
                <Label htmlFor="remember" className="text-sm text-slate-600 cursor-pointer">
                  {lang === 'ar' ? 'تذكرني' : 'Remember me'}
                </Label>
              </div>

              <Button 
                data-testid="login-submit" 
                type="submit" 
                className="w-full h-12 text-white font-medium shadow-lg transition-all duration-300 hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]" 
                style={{ 
                  background: `linear-gradient(135deg, ${settings.primary_color}, ${settings.secondary_color})`,
                  boxShadow: `0 10px 40px -10px ${settings.primary_color}66`
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
          <div className="mt-6 flex justify-center animate-fade-in-up" style={{ animationDelay: '0.6s' }}>
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
          <p className="text-xs text-center text-slate-400 mt-6 animate-fade-in-up" style={{ animationDelay: '0.7s' }}>
            {lang === 'ar' 
              ? '© 2026 دار الكود. جميع الحقوق محفوظة'
              : '© 2026 DAR AL CODE. All rights reserved'
            }
          </p>
        </div>
      </div>

      {/* Right: Decorative panel (desktop only) */}
      <div 
        className={`hidden lg:flex lg:flex-1 items-center justify-center p-12 relative overflow-hidden transition-all duration-1000 ${mounted ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-20'}`}
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
        
        {/* Animated Background Elements */}
        {!settings.side_image_url && (
          <>
            {/* Floating circles */}
            <div className="absolute inset-0 overflow-hidden">
              <div className="absolute top-10 left-10 w-32 h-32 border-2 border-white/20 rounded-full animate-float" />
              <div className="absolute bottom-20 right-20 w-48 h-48 border-2 border-white/20 rounded-full animate-float" style={{ animationDelay: '2s' }} />
              <div className="absolute top-1/2 left-1/4 w-24 h-24 border-2 border-white/20 rounded-full animate-float" style={{ animationDelay: '4s' }} />
              <div className="absolute top-1/4 right-1/4 w-16 h-16 bg-white/10 rounded-full animate-pulse-slow" />
              <div className="absolute bottom-1/3 left-1/3 w-20 h-20 bg-white/10 rounded-full animate-pulse-slow" style={{ animationDelay: '1s' }} />
            </div>
            
            {/* Gradient orbs */}
            <div className="absolute -top-1/4 -right-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl animate-pulse-slow" />
            <div className="absolute -bottom-1/4 -left-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '3s' }} />
            
            {/* Grid pattern */}
            <div className="absolute inset-0 opacity-10">
              <svg width="100%" height="100%">
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5"/>
                </pattern>
                <rect width="100%" height="100%" fill="url(#grid)" />
              </svg>
            </div>
          </>
        )}
        
        <div className="text-center max-w-md relative z-10">
          {!settings.side_image_url && (
            <>
              <div className="w-28 h-28 rounded-3xl bg-white/10 backdrop-blur-lg mx-auto mb-8 flex items-center justify-center border border-white/20 animate-logo-3d">
                <span className="text-5xl font-bold text-white">د</span>
              </div>
              <h2 className="text-3xl font-bold text-white mb-4 animate-fade-in-up" style={{ animationDelay: '0.8s' }}>
                {lang === 'ar' ? 'نظام الموارد البشرية' : 'HR Management System'}
              </h2>
            </>
          )}
          
          {/* Welcome Text */}
          <p className="text-white/90 leading-relaxed text-xl font-medium drop-shadow-lg animate-fade-in-up" style={{ animationDelay: '0.9s' }}>
            {lang === 'ar' ? settings.welcome_text_ar : settings.welcome_text_en}
          </p>
          
          {/* Features List (only if no side image) */}
          {!settings.side_image_url && (
            <div className="mt-10 grid grid-cols-2 gap-4 text-white/90 text-sm">
              {[
                { ar: 'إدارة الحضور', en: 'Attendance', delay: '1s' },
                { ar: 'المعاملات', en: 'Transactions', delay: '1.1s' },
                { ar: 'العقود', en: 'Contracts', delay: '1.2s' },
                { ar: 'التقارير', en: 'Reports', delay: '1.3s' }
              ].map((item, i) => (
                <div 
                  key={i} 
                  className="flex items-center gap-2 animate-fade-in-up"
                  style={{ animationDelay: item.delay }}
                >
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span>{lang === 'ar' ? item.ar : item.en}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      
      {/* Custom CSS for animations */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(5deg); }
        }
        
        @keyframes pulse-slow {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.1); }
        }
        
        @keyframes logo-float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
        
        @keyframes logo-3d {
          0%, 100% { transform: perspective(500px) rotateY(0deg); }
          25% { transform: perspective(500px) rotateY(5deg); }
          75% { transform: perspective(500px) rotateY(-5deg); }
        }
        
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }
        
        @keyframes welcome-in {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
        
        @keyframes text-reveal {
          from { opacity: 0; transform: translateY(30px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes logo-pulse {
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255,255,255,0.4); }
          50% { transform: scale(1.05); box-shadow: 0 0 0 20px rgba(255,255,255,0); }
        }
        
        .animate-float { animation: float 8s ease-in-out infinite; }
        .animate-pulse-slow { animation: pulse-slow 4s ease-in-out infinite; }
        .animate-logo-float { animation: logo-float 3s ease-in-out infinite; }
        .animate-logo-3d { animation: logo-3d 6s ease-in-out infinite; }
        .animate-fade-in-up { animation: fade-in-up 0.6s ease-out forwards; opacity: 0; }
        .animate-shake { animation: shake 0.5s ease-in-out; }
        .animate-welcome-in { animation: welcome-in 0.8s ease-out forwards; }
        .animate-text-reveal { animation: text-reveal 0.8s ease-out 0.3s forwards; opacity: 0; }
        .animate-text-reveal-delay { animation: text-reveal 0.8s ease-out 0.5s forwards; opacity: 0; }
        .animate-logo-pulse { animation: logo-pulse 2s ease-in-out infinite; }
      `}</style>
    </div>
  );
}
