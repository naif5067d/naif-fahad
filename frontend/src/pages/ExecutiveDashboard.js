import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { 
  TrendingUp, TrendingDown, Users, Clock, FileText, Wallet,
  AlertTriangle, Activity, BarChart3, Target, ArrowLeft,
  Maximize2, Minimize2, RefreshCw, Bell, Zap, Award,
  ChevronUp, ChevronDown as ChevronDownIcon, Brain, Star, Eye
} from 'lucide-react';
import api from '@/lib/api';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

// ==================== EXECUTIVE DESIGN SYSTEM ====================
const THEME = {
  // Core palette - Luxurious & Minimal
  bg: {
    primary: '#0A0A0B',      // Deep black
    secondary: '#111113',    // Elevated surface
    tertiary: '#18181B',     // Cards
    hover: '#1F1F23',        // Hover state
  },
  border: {
    subtle: 'rgba(255,255,255,0.06)',
    light: 'rgba(255,255,255,0.1)',
  },
  text: {
    primary: '#FAFAFA',      // White
    secondary: '#A1A1AA',    // Muted
    tertiary: '#71717A',     // Dim
    accent: '#E4E4E7',       // Subtle emphasis
  },
  accent: {
    blue: '#3B82F6',
    green: '#10B981',
    amber: '#F59E0B',
    red: '#EF4444',
    purple: '#8B5CF6',
    cyan: '#06B6D4',
  }
};

const CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6'];

// ==================== HELPER FUNCTIONS ====================
const getScoreColor = (score) => {
  if (score >= 85) return THEME.accent.green;
  if (score >= 70) return THEME.accent.blue;
  if (score >= 50) return THEME.accent.amber;
  return THEME.accent.red;
};

const getScoreLabel = (score) => {
  if (score >= 85) return 'ممتاز';
  if (score >= 70) return 'جيد';
  if (score >= 50) return 'مقبول';
  return 'يحتاج تحسين';
};

// ==================== COMPONENTS ====================

// Premium Score Ring - Clean & Elegant
const ScoreRing = ({ score, size = 240 }) => {
  const strokeWidth = size * 0.05;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score);
  
  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Background glow */}
      <div 
        className="absolute inset-0 rounded-full blur-3xl opacity-20"
        style={{ background: color }}
      />
      
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={THEME.border.subtle}
          strokeWidth={strokeWidth}
        />
        {/* Progress */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-[2000ms] ease-out"
          style={{ filter: `drop-shadow(0 0 12px ${color}40)` }}
        />
      </svg>
      
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span 
          className="font-extralight tracking-tight leading-none"
          style={{ 
            fontSize: size * 0.3,
            color: THEME.text.primary,
          }}
        >
          {Math.round(score)}
        </span>
        <span 
          className="text-xs uppercase tracking-[0.2em] mt-2"
          style={{ color: THEME.text.tertiary }}
        >
          من 100
        </span>
        <span 
          className="text-sm mt-3 px-3 py-1 rounded-full"
          style={{ 
            color: color,
            background: `${color}15`,
          }}
        >
          {getScoreLabel(score)}
        </span>
      </div>
    </div>
  );
};

// KPI Metric Card - Clean & Minimal
const MetricCard = ({ title, titleEn, score, icon: Icon, details }) => {
  const color = getScoreColor(score);
  
  return (
    <div 
      className="group relative p-5 sm:p-6 rounded-2xl transition-all duration-500 hover:translate-y-[-2px]"
      style={{ 
        background: THEME.bg.secondary,
        border: `1px solid ${THEME.border.subtle}`,
      }}
      data-testid={`metric-card-${titleEn?.toLowerCase().replace(/\s/g, '-')}`}
    >
      {/* Glow effect on hover */}
      <div 
        className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl"
        style={{ background: `${color}08` }}
      />
      
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div 
            className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center"
            style={{ background: `${color}12` }}
          >
            <Icon size={20} style={{ color }} />
          </div>
        </div>
        
        {/* Score */}
        <div className="mb-3">
          <div className="flex items-baseline gap-1">
            <span 
              className="text-3xl sm:text-4xl lg:text-5xl font-extralight"
              style={{ color }}
            >
              {Math.round(score)}
            </span>
            <span className="text-lg sm:text-xl" style={{ color: THEME.text.tertiary }}>%</span>
          </div>
          <p className="text-sm mt-1" style={{ color: THEME.text.secondary }}>
            {title}
          </p>
        </div>
        
        {/* Details */}
        {details && (
          <div 
            className="pt-4 border-t space-y-2"
            style={{ borderColor: THEME.border.subtle }}
          >
            {details}
          </div>
        )}
      </div>
    </div>
  );
};

// Quick Stat Badge
const QuickStat = ({ icon: Icon, label, value, color }) => (
  <div 
    className="flex items-center gap-3 px-4 py-3 rounded-xl"
    style={{ 
      background: THEME.bg.secondary,
      border: `1px solid ${THEME.border.subtle}`,
    }}
  >
    <div 
      className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
      style={{ background: `${color}12` }}
    >
      <Icon size={18} style={{ color }} />
    </div>
    <div className="min-w-0">
      <p className="text-lg sm:text-xl font-light" style={{ color: THEME.text.primary }}>
        {value}
      </p>
      <p className="text-xs" style={{ color: THEME.text.tertiary }}>
        {label}
      </p>
    </div>
  </div>
);

// Employee Rank Card
const RankCard = ({ employee, rank, type = 'top' }) => {
  const isTop = type === 'top';
  const color = isTop ? THEME.accent.green : THEME.accent.amber;
  const scoreColor = employee.score >= 70 ? THEME.accent.green : 
                     employee.score >= 50 ? THEME.accent.amber : THEME.accent.red;
  
  return (
    <div 
      className="flex items-center gap-3 p-3 rounded-xl transition-all duration-300 hover:scale-[1.02]"
      style={{ background: THEME.bg.primary }}
    >
      <div 
        className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0"
        style={{ 
          background: `${color}15`,
          color: color,
        }}
      >
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate" style={{ color: THEME.text.primary }}>
          {employee.name}
        </p>
        <p className="text-xs" style={{ color: THEME.text.tertiary }}>
          {employee.department || 'غير محدد'}
        </p>
      </div>
      <div 
        className="text-lg font-light"
        style={{ color: scoreColor }}
      >
        {Math.round(employee.score)}%
      </div>
    </div>
  );
};

// Alert Badge
const AlertItem = ({ alert }) => {
  const colors = {
    warning: THEME.accent.amber,
    danger: THEME.accent.red,
    info: THEME.accent.blue,
    alert: THEME.accent.amber,
  };
  const color = colors[alert.type] || colors.info;
  
  return (
    <div 
      className="flex items-start gap-3 p-4 rounded-xl"
      style={{ background: THEME.bg.primary }}
    >
      <div 
        className="w-2 h-2 rounded-full mt-2 flex-shrink-0"
        style={{ background: color }}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium" style={{ color: THEME.text.primary }}>
          {alert.title}
        </p>
        <p className="text-xs mt-1" style={{ color: THEME.text.tertiary }}>
          {alert.message}
        </p>
      </div>
      <span 
        className="px-2 py-0.5 rounded text-[10px] uppercase tracking-wider flex-shrink-0"
        style={{ 
          background: `${color}15`,
          color: color,
        }}
      >
        {alert.priority === 'high' ? 'عاجل' : 'متوسط'}
      </span>
    </div>
  );
};

// Detail Row
const DetailRow = ({ label, value }) => (
  <div className="flex items-center justify-between text-xs">
    <span style={{ color: THEME.text.tertiary }}>{label}</span>
    <span style={{ color: THEME.text.secondary }}>{value}</span>
  </div>
);

// ==================== MAIN DASHBOARD ====================
export default function ExecutiveDashboard() {
  const { user } = useAuth();
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showAlerts, setShowAlerts] = useState(false);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'smart-monitor'
  const [smartMonitorData, setSmartMonitorData] = useState(null);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [dashboardRes, alertsRes] = await Promise.all([
        api.get('/api/analytics/executive/dashboard'),
        api.get('/api/analytics/alerts')
      ]);
      setData(dashboardRes.data);
      setAlerts(alertsRes.data.alerts || []);
      setLastUpdate(new Date());
    } catch (e) {
      console.error('Dashboard fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSmartMonitor = useCallback(async () => {
    try {
      const res = await api.get('/api/analytics/ai/smart-monitor');
      setSmartMonitorData(res.data);
    } catch (e) {
      console.error('Smart monitor fetch error:', e);
    }
  }, []);

  const fetchEmployeeDetails = async (employeeId) => {
    try {
      const res = await api.get(`/api/analytics/ai/employee/${employeeId}`);
      setSelectedEmployee(res.data);
    } catch (e) {
      console.error('Employee details error:', e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      if (autoRefresh) fetchData();
    }, 60000);
    return () => clearInterval(interval);
  }, [fetchData, autoRefresh]);

  useEffect(() => {
    if (activeTab === 'smart-monitor' && !smartMonitorData) {
      fetchSmartMonitor();
    }
  }, [activeTab, smartMonitorData, fetchSmartMonitor]);

  // Fullscreen handlers
  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (err) {
      console.error('Fullscreen error:', err);
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  // Loading state
  if (loading) {
    return (
      <div 
        className="fixed inset-0 flex items-center justify-center"
        style={{ background: THEME.bg.primary }}
      >
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-6">
            <div 
              className="absolute inset-0 rounded-full animate-ping opacity-20"
              style={{ background: THEME.accent.blue }}
            />
            <div 
              className="absolute inset-2 rounded-full animate-spin"
              style={{ 
                border: `2px solid ${THEME.border.subtle}`,
                borderTopColor: THEME.accent.blue,
              }}
            />
          </div>
          <p className="text-sm" style={{ color: THEME.text.tertiary }}>
            جاري تحميل لوحة الحوكمة...
          </p>
        </div>
      </div>
    );
  }

  const { 
    metrics, 
    top_performers = [], 
    needs_attention = [], 
    monthly_trend = [], 
    executive_summary, 
    quick_stats, 
    health_score = 0 
  } = data || {};

  // Chart data
  const trendData = monthly_trend.map(m => ({
    name: m.month_name?.split(' ')[0] || m.month,
    score: m.health_score,
    attendance: m.attendance,
    tasks: m.tasks,
  }));

  const pieData = [
    { name: 'الحضور', value: metrics?.attendance?.score || 0, color: THEME.accent.blue },
    { name: 'المهام', value: metrics?.tasks?.score || 0, color: THEME.accent.green },
    { name: 'المالية', value: metrics?.financial?.score || 0, color: THEME.accent.purple },
    { name: 'الطلبات', value: metrics?.requests?.score || 0, color: THEME.accent.amber },
  ];

  return (
    <div 
      className={`min-h-screen transition-all duration-500 ${isFullscreen ? 'overflow-hidden' : ''}`}
      style={{ background: THEME.bg.primary }}
      dir="rtl"
      data-testid="executive-dashboard"
    >
      {/* ==================== HEADER ==================== */}
      <header 
        className="sticky top-0 z-50 backdrop-blur-xl"
        style={{ 
          background: `${THEME.bg.primary}E6`,
          borderBottom: `1px solid ${THEME.border.subtle}`,
        }}
      >
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Left - Title & Back */}
          <div className="flex items-center gap-4">
            {!isFullscreen && (
              <button
                onClick={() => navigate('/')}
                className="p-2 rounded-lg transition-colors"
                style={{ color: THEME.text.tertiary }}
                data-testid="back-btn"
              >
                <ArrowLeft size={20} />
              </button>
            )}
            <div>
              <h1 
                className="text-lg sm:text-xl font-light tracking-tight"
                style={{ color: THEME.text.primary }}
              >
                لوحة الحوكمة التنفيذية
              </h1>
              <p className="text-xs hidden sm:block" style={{ color: THEME.text.tertiary }}>
                آخر تحديث: {lastUpdate?.toLocaleTimeString('en-US', { hour12: true })}
              </p>
            </div>
            
            {/* Tabs */}
            <div className="flex items-center gap-1 ms-6 bg-[#18181B] rounded-lg p-1">
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-3 py-1.5 rounded-md text-xs transition-all ${
                  activeTab === 'overview' ? 'bg-[#3B82F6] text-white' : 'text-[#A1A1AA] hover:text-white'
                }`}
              >
                <Activity size={14} className="inline me-1" />
                نظرة عامة
              </button>
              <button
                onClick={() => setActiveTab('smart-monitor')}
                className={`px-3 py-1.5 rounded-md text-xs transition-all ${
                  activeTab === 'smart-monitor' ? 'bg-[#8B5CF6] text-white' : 'text-[#A1A1AA] hover:text-white'
                }`}
              >
                <Brain size={14} className="inline me-1" />
                المراقب الذكي
              </button>
            </div>
          </div>

          {/* Right - Controls */}
          <div className="flex items-center gap-2">
            {/* Alerts */}
            {alerts.length > 0 && (
              <button
                onClick={() => setShowAlerts(!showAlerts)}
                className="relative flex items-center gap-2 px-3 py-2 rounded-lg transition-colors"
                style={{ 
                  background: `${THEME.accent.amber}15`,
                  color: THEME.accent.amber,
                }}
                data-testid="alerts-toggle"
              >
                <Bell size={16} />
                <span className="text-sm hidden sm:inline">{alerts.length}</span>
                <span 
                  className="absolute -top-1 -left-1 w-2 h-2 rounded-full animate-pulse"
                  style={{ background: THEME.accent.amber }}
                />
              </button>
            )}

            {/* Auto Refresh */}
            <button
              onClick={() => { setAutoRefresh(!autoRefresh); if (!autoRefresh) fetchData(); }}
              className="p-2 rounded-lg transition-all"
              style={{ 
                background: autoRefresh ? `${THEME.accent.blue}15` : THEME.bg.secondary,
                color: autoRefresh ? THEME.accent.blue : THEME.text.tertiary,
              }}
              title={autoRefresh ? 'إيقاف التحديث التلقائي' : 'تفعيل التحديث التلقائي'}
              data-testid="refresh-toggle"
            >
              <RefreshCw 
                size={18} 
                className={autoRefresh ? 'animate-spin' : ''} 
                style={{ animationDuration: '3s' }} 
              />
            </button>

            {/* Fullscreen */}
            <button
              onClick={toggleFullscreen}
              className="p-2 rounded-lg transition-colors"
              style={{ 
                background: THEME.bg.secondary,
                color: THEME.text.tertiary,
              }}
              title="وضع العرض الكامل"
              data-testid="fullscreen-toggle"
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
          </div>
        </div>
      </header>

      {/* ==================== ALERTS PANEL ==================== */}
      {showAlerts && alerts.length > 0 && (
        <div 
          className="fixed inset-x-0 top-16 z-40 p-4 max-h-[50vh] overflow-y-auto"
          style={{ 
            background: `${THEME.bg.secondary}F5`,
            backdropFilter: 'blur(20px)',
            borderBottom: `1px solid ${THEME.border.subtle}`,
          }}
        >
          <div className="max-w-[1800px] mx-auto space-y-2">
            {alerts.map((alert, i) => (
              <AlertItem key={i} alert={alert} />
            ))}
          </div>
        </div>
      )}

      {/* ==================== MAIN CONTENT ==================== */}
      <main className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10">
        
        {activeTab === 'overview' ? (
        <>
        {/* ========== TOP SECTION: Health Score + KPIs ========== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 mb-8">
          
          {/* Health Score - Hero */}
          <div className="lg:col-span-4 xl:col-span-4 flex items-center justify-center order-first lg:order-last">
            <div 
              className="w-full p-6 sm:p-8 lg:p-10 rounded-3xl text-center relative overflow-hidden"
              style={{ 
                background: THEME.bg.secondary,
                border: `1px solid ${THEME.border.subtle}`,
              }}
              data-testid="health-score-card"
            >
              {/* Subtle background gradient */}
              <div 
                className="absolute inset-0 opacity-5"
                style={{ 
                  background: `radial-gradient(circle at 50% 30%, ${getScoreColor(health_score)}, transparent 70%)`
                }}
              />
              
              <p 
                className="relative text-xs uppercase tracking-[0.2em] mb-6"
                style={{ color: THEME.text.tertiary }}
              >
                مؤشر صحة الشركة
              </p>
              
              <div className="relative flex justify-center mb-6">
                <ScoreRing score={health_score} size={isFullscreen ? 260 : 200} />
              </div>
              
              <p 
                className="relative text-[10px] uppercase tracking-[0.15em]"
                style={{ color: THEME.text.tertiary }}
              >
                {lang === 'ar' ? 'مؤشر صحة الشركة' : 'Company Health Score'}
              </p>
            </div>
          </div>

          {/* KPI Cards Grid */}
          <div className="lg:col-span-8 xl:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4 order-last lg:order-first">
            <MetricCard
              title="الحضور والانضباط"
              titleEn="Attendance"
              score={metrics?.attendance?.score || 0}
              icon={Clock}
              details={
                <>
                  <DetailRow label="أيام الحضور" value={metrics?.attendance?.present_days || 0} />
                  <DetailRow label="دقائق التأخير" value={metrics?.attendance?.late_minutes || 0} />
                  <DetailRow label="أيام الغياب" value={metrics?.attendance?.absent_days || 0} />
                </>
              }
            />
            
            <MetricCard
              title="أداء المهام"
              titleEn="Tasks"
              score={metrics?.tasks?.score || 0}
              icon={Target}
              details={
                <>
                  <DetailRow label="المهام المنجزة" value={metrics?.tasks?.total_tasks || 0} />
                  <DetailRow label="في الموعد" value={metrics?.tasks?.completed_on_time || 0} />
                  <DetailRow label="متوسط التقييم" value={`${metrics?.tasks?.average_rating || 0}/5`} />
                </>
              }
            />
            
            <MetricCard
              title="الانضباط المالي"
              titleEn="Financial"
              score={metrics?.financial?.score || 0}
              icon={Wallet}
              details={
                <>
                  <DetailRow label="العهد" value={metrics?.financial?.total_custodies || 0} />
                  <DetailRow label="إجمالي المصروف" value={(metrics?.financial?.total_spent || 0).toLocaleString()} />
                  <DetailRow label="المُعاد" value={metrics?.financial?.returned || 0} />
                </>
              }
            />
            
            <MetricCard
              title="انضباط الطلبات"
              titleEn="Requests"
              score={metrics?.requests?.score || 0}
              icon={FileText}
              details={
                <>
                  <DetailRow label="الطلبات المقبولة" value={metrics?.requests?.approved || 0} />
                  <DetailRow label="المرفوضة" value={metrics?.requests?.rejected || 0} />
                  <DetailRow label="المعلقة" value={metrics?.requests?.pending || 0} />
                </>
              }
            />
          </div>
        </div>

        {/* ========== EXECUTIVE SUMMARY ========== */}
        <div 
          className="p-5 sm:p-6 rounded-2xl mb-8"
          style={{ 
            background: THEME.bg.secondary,
            border: `1px solid ${THEME.border.subtle}`,
          }}
          data-testid="executive-summary"
        >
          <div className="flex items-center gap-3 mb-4">
            <div 
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ background: `${THEME.accent.cyan}12` }}
            >
              <Zap size={16} style={{ color: THEME.accent.cyan }} />
            </div>
            <span 
              className="text-xs uppercase tracking-[0.15em]"
              style={{ color: THEME.text.tertiary }}
            >
              الملخص التنفيذي
            </span>
          </div>
          <p 
            className="text-base sm:text-lg font-light leading-relaxed"
            style={{ color: THEME.text.primary }}
          >
            {executive_summary || 'جاري تحليل البيانات...'}
          </p>
        </div>

        {/* ========== CHARTS SECTION ========== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
          
          {/* Trend Chart */}
          <div 
            className="lg:col-span-8 p-5 sm:p-6 rounded-2xl"
            style={{ 
              background: THEME.bg.secondary,
              border: `1px solid ${THEME.border.subtle}`,
            }}
            data-testid="trend-chart"
          >
            <div className="flex items-center gap-3 mb-6">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${THEME.accent.blue}12` }}
              >
                <BarChart3 size={16} style={{ color: THEME.accent.blue }} />
              </div>
              <span 
                className="text-xs uppercase tracking-[0.15em]"
                style={{ color: THEME.text.tertiary }}
              >
                اتجاه الأداء الشهري
              </span>
            </div>
            
            <div className="h-[250px] sm:h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={THEME.accent.blue} stopOpacity={0.25}/>
                      <stop offset="95%" stopColor={THEME.accent.blue} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={THEME.border.subtle} />
                  <XAxis 
                    dataKey="name" 
                    stroke={THEME.text.tertiary} 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke={THEME.text.tertiary} 
                    fontSize={11} 
                    domain={[0, 100]}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      background: THEME.bg.tertiary,
                      border: `1px solid ${THEME.border.light}`,
                      borderRadius: 12,
                      boxShadow: '0 20px 40px rgba(0,0,0,0.3)',
                    }}
                    labelStyle={{ color: THEME.text.primary }}
                    itemStyle={{ color: THEME.text.secondary }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="score" 
                    stroke={THEME.accent.blue} 
                    strokeWidth={2.5}
                    fill="url(#scoreGrad)"
                    name="الدرجة"
                    dot={{ fill: THEME.accent.blue, strokeWidth: 0, r: 4 }}
                    activeDot={{ r: 6, fill: THEME.accent.blue }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pie Chart */}
          <div 
            className="lg:col-span-4 p-5 sm:p-6 rounded-2xl"
            style={{ 
              background: THEME.bg.secondary,
              border: `1px solid ${THEME.border.subtle}`,
            }}
            data-testid="distribution-chart"
          >
            <div className="flex items-center gap-3 mb-6">
              <span 
                className="text-xs uppercase tracking-[0.15em]"
                style={{ color: THEME.text.tertiary }}
              >
                توزيع المؤشرات
              </span>
            </div>
            
            <div className="h-[180px] sm:h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius="45%"
                    outerRadius="75%"
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={entry.color}
                        stroke="none"
                      />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      background: THEME.bg.tertiary,
                      border: `1px solid ${THEME.border.light}`,
                      borderRadius: 12,
                    }}
                    formatter={(value) => [`${value}%`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            {/* Legend */}
            <div className="grid grid-cols-2 gap-2 mt-4">
              {pieData.map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div 
                    className="w-2 h-2 rounded-full"
                    style={{ background: item.color }}
                  />
                  <span 
                    className="text-xs"
                    style={{ color: THEME.text.tertiary }}
                  >
                    {item.name}
                  </span>
                  <span 
                    className="text-xs mr-auto"
                    style={{ color: THEME.text.secondary }}
                  >
                    {item.value}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ========== PERFORMERS SECTION ========== */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          
          {/* Top Performers */}
          <div 
            className="p-5 sm:p-6 rounded-2xl"
            style={{ 
              background: THEME.bg.secondary,
              border: `1px solid ${THEME.border.subtle}`,
            }}
            data-testid="top-performers"
          >
            <div className="flex items-center gap-3 mb-5">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${THEME.accent.green}12` }}
              >
                <Award size={16} style={{ color: THEME.accent.green }} />
              </div>
              <span 
                className="text-xs uppercase tracking-[0.15em]"
                style={{ color: THEME.text.tertiary }}
              >
                الأعلى أداءً
              </span>
            </div>
            
            <div className="space-y-2">
              {top_performers.length > 0 ? (
                top_performers.slice(0, 5).map((emp, i) => (
                  <RankCard key={i} employee={emp} rank={i + 1} type="top" />
                ))
              ) : (
                <p className="text-center py-8 text-sm" style={{ color: THEME.text.tertiary }}>
                  لا توجد بيانات كافية
                </p>
              )}
            </div>
          </div>

          {/* Needs Attention */}
          <div 
            className="p-5 sm:p-6 rounded-2xl"
            style={{ 
              background: THEME.bg.secondary,
              border: `1px solid ${THEME.border.subtle}`,
            }}
            data-testid="needs-attention"
          >
            <div className="flex items-center gap-3 mb-5">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${THEME.accent.amber}12` }}
              >
                <AlertTriangle size={16} style={{ color: THEME.accent.amber }} />
              </div>
              <span 
                className="text-xs uppercase tracking-[0.15em]"
                style={{ color: THEME.text.tertiary }}
              >
                يحتاج متابعة
              </span>
            </div>
            
            <div className="space-y-2">
              {needs_attention.length > 0 ? (
                needs_attention.slice(0, 5).map((emp, i) => (
                  <RankCard key={i} employee={emp} rank={i + 1} type="bottom" />
                ))
              ) : (
                <p className="text-center py-8 text-sm" style={{ color: THEME.text.tertiary }}>
                  جميع الموظفين بأداء جيد
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ========== QUICK STATS FOOTER ========== */}
        <div 
          className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4"
          data-testid="quick-stats"
        >
          <QuickStat 
            icon={Users} 
            label="الموظفين النشطين" 
            value={quick_stats?.total_employees || 0}
            color={THEME.accent.blue}
          />
          <QuickStat 
            icon={FileText} 
            label="الطلبات المعلقة" 
            value={quick_stats?.pending_requests || 0}
            color={THEME.accent.amber}
          />
          <QuickStat 
            icon={Wallet} 
            label="العهد المفتوحة" 
            value={quick_stats?.open_custodies || 0}
            color={THEME.accent.purple}
          />
          <QuickStat 
            icon={Target} 
            label="المهام الجارية" 
            value={quick_stats?.active_tasks || 0}
            color={THEME.accent.green}
          />
        </div>
        </>
        ) : (
        /* ==================== SMART MONITOR TAB ==================== */
        <div className="space-y-6" data-testid="smart-monitor-tab">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.border.subtle}` }}>
              <p className="text-xs mb-1" style={{ color: THEME.text.tertiary }}>المتوسط العام</p>
              <p className="text-2xl font-light" style={{ color: THEME.text.primary }}>{smartMonitorData?.company_average || 0}%</p>
            </div>
            <div className="p-4 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.accent.green}30` }}>
              <p className="text-xs mb-1" style={{ color: THEME.text.tertiary }}>ممتاز</p>
              <p className="text-2xl font-light" style={{ color: THEME.accent.green }}>{smartMonitorData?.distribution?.excellent || 0}</p>
            </div>
            <div className="p-4 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.accent.blue}30` }}>
              <p className="text-xs mb-1" style={{ color: THEME.text.tertiary }}>جيد</p>
              <p className="text-2xl font-light" style={{ color: THEME.accent.blue }}>{smartMonitorData?.distribution?.good || 0}</p>
            </div>
            <div className="p-4 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.accent.red}30` }}>
              <p className="text-xs mb-1" style={{ color: THEME.text.tertiary }}>يحتاج تحسين</p>
              <p className="text-2xl font-light" style={{ color: THEME.accent.red }}>{smartMonitorData?.distribution?.needs_improvement || 0}</p>
            </div>
          </div>

          {/* Alerts */}
          {smartMonitorData?.alerts?.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium flex items-center gap-2" style={{ color: THEME.text.primary }}>
                <Zap size={16} style={{ color: THEME.accent.amber }} />
                تنبيهات ذكية
              </h3>
              <div className="grid md:grid-cols-3 gap-3">
                {smartMonitorData.alerts.map((alert, i) => (
                  <div 
                    key={i} 
                    className="p-3 rounded-lg"
                    style={{ 
                      background: alert.type === 'success' ? `${THEME.accent.green}10` : 
                                  alert.type === 'warning' ? `${THEME.accent.amber}10` : `${THEME.accent.blue}10`,
                      border: `1px solid ${alert.type === 'success' ? THEME.accent.green : 
                              alert.type === 'warning' ? THEME.accent.amber : THEME.accent.blue}30`
                    }}
                  >
                    <p className="text-xs font-medium" style={{ color: alert.type === 'success' ? THEME.accent.green : 
                        alert.type === 'warning' ? THEME.accent.amber : THEME.accent.blue }}>{alert.title}</p>
                    <p className="text-[10px] mt-1" style={{ color: THEME.text.tertiary }}>{alert.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Main Grid */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Top Performers */}
            <div className="p-5 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.accent.green}30` }}>
              <h3 className="text-sm font-medium flex items-center gap-2 mb-4" style={{ color: THEME.accent.green }}>
                <Award size={16} />
                الموظفين المتميزين
              </h3>
              <div className="space-y-2">
                {smartMonitorData?.top_performers?.map((emp, i) => (
                  <div 
                    key={emp.employee_id}
                    className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors hover:bg-white/5"
                    onClick={() => fetchEmployeeDetails(emp.employee_id)}
                  >
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ background: `${THEME.accent.green}20`, color: THEME.accent.green }}>{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate" style={{ color: THEME.text.primary }}>{emp.employee_name}</p>
                      <div className="flex gap-0.5">
                        {[1,2,3,4,5].map(s => (
                          <Star key={s} size={10} className={s <= (emp.rating?.stars || 0) ? 'fill-amber-400 text-amber-400' : 'text-zinc-600'} />
                        ))}
                      </div>
                    </div>
                    <span className="text-sm font-bold" style={{ color: THEME.accent.green }}>{emp.overall_score}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Needs Attention */}
            <div className="p-5 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.accent.red}30` }}>
              <h3 className="text-sm font-medium flex items-center gap-2 mb-4" style={{ color: THEME.accent.red }}>
                <AlertTriangle size={16} />
                يحتاجون متابعة
              </h3>
              <div className="space-y-2">
                {smartMonitorData?.bottom_performers?.map((emp, i) => (
                  <div 
                    key={emp.employee_id}
                    className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors hover:bg-white/5"
                    onClick={() => fetchEmployeeDetails(emp.employee_id)}
                  >
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{ background: `${THEME.accent.red}20`, color: THEME.accent.red }}>{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate" style={{ color: THEME.text.primary }}>{emp.employee_name}</p>
                      <div className="flex gap-2 text-[10px]" style={{ color: THEME.text.tertiary }}>
                        {emp.forget_checkin_count > 0 && <span>نسيان: {emp.forget_checkin_count}</span>}
                        {emp.late_excuse_count > 0 && <span>تأخير: {emp.late_excuse_count}</span>}
                      </div>
                    </div>
                    <span className="text-sm font-bold" style={{ color: THEME.accent.red }}>{emp.overall_score}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Employee Details */}
            <div className="p-5 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.border.subtle}` }}>
              <h3 className="text-sm font-medium flex items-center gap-2 mb-4" style={{ color: THEME.text.primary }}>
                <Eye size={16} />
                تفاصيل الموظف
              </h3>
              {selectedEmployee ? (
                <div className="space-y-4">
                  <div className="text-center">
                    <p className="font-medium" style={{ color: THEME.text.primary }}>{selectedEmployee.employee_name}</p>
                    <p className="text-xs" style={{ color: THEME.text.tertiary }}>{selectedEmployee.job_title}</p>
                    <div className="flex justify-center mt-3">
                      <div className="relative w-20 h-20">
                        <svg width="80" height="80" className="transform -rotate-90">
                          <circle cx="40" cy="40" r="32" fill="none" stroke={THEME.border.subtle} strokeWidth="4" />
                          <circle cx="40" cy="40" r="32" fill="none" 
                            stroke={getScoreColor(selectedEmployee.evaluation?.overall_score || 0)} 
                            strokeWidth="4"
                            strokeDasharray={200}
                            strokeDashoffset={200 - (selectedEmployee.evaluation?.overall_score || 0) / 100 * 200}
                            strokeLinecap="round"
                          />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-lg font-bold" style={{ color: THEME.text.primary }}>
                            {Math.round(selectedEmployee.evaluation?.overall_score || 0)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex justify-center gap-0.5 mt-2">
                      {[1,2,3,4,5].map(s => (
                        <Star key={s} size={14} className={s <= (selectedEmployee.evaluation?.rating?.stars || 0) ? 'fill-amber-400 text-amber-400' : 'text-zinc-600'} />
                      ))}
                    </div>
                    <span className="inline-block mt-2 px-2 py-0.5 rounded text-xs"
                      style={{ background: `${selectedEmployee.evaluation?.rating?.color}20`, color: selectedEmployee.evaluation?.rating?.color }}>
                      {selectedEmployee.evaluation?.rating?.label}
                    </span>
                  </div>
                  
                  {/* Breakdown */}
                  <div className="space-y-2">
                    {selectedEmployee.evaluation?.breakdown && Object.entries(selectedEmployee.evaluation.breakdown).map(([key, val]) => (
                      <div key={key}>
                        <div className="flex justify-between text-[10px] mb-1">
                          <span style={{ color: THEME.text.tertiary }}>
                            {key === 'attendance' ? 'الحضور' : key === 'tasks' ? 'المهام' : key === 'excuses' ? 'الأعذار' : key === 'financial' ? 'المالية' : 'الطلبات'}
                          </span>
                          <span style={{ color: THEME.text.secondary }}>{val.score}%</span>
                        </div>
                        <div className="h-1 rounded-full" style={{ background: THEME.border.subtle }}>
                          <div className="h-1 rounded-full transition-all" style={{ width: `${val.score}%`, background: getScoreColor(val.score) }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Strengths & Weaknesses */}
                  {selectedEmployee.evaluation?.strengths?.length > 0 && (
                    <div>
                      <p className="text-[10px] font-medium mb-1" style={{ color: THEME.accent.green }}>نقاط القوة:</p>
                      {selectedEmployee.evaluation.strengths.slice(0, 3).map((s, i) => (
                        <p key={i} className="text-[10px]" style={{ color: THEME.text.tertiary }}>✓ {s}</p>
                      ))}
                    </div>
                  )}
                  {selectedEmployee.evaluation?.weaknesses?.length > 0 && (
                    <div>
                      <p className="text-[10px] font-medium mb-1" style={{ color: THEME.accent.red }}>يحتاج تحسين:</p>
                      {selectedEmployee.evaluation.weaknesses.slice(0, 3).map((w, i) => (
                        <p key={i} className="text-[10px]" style={{ color: THEME.text.tertiary }}>• {w}</p>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-10">
                  <Eye size={32} className="mx-auto mb-2 opacity-20" style={{ color: THEME.text.tertiary }} />
                  <p className="text-xs" style={{ color: THEME.text.tertiary }}>اختر موظف لعرض التفاصيل</p>
                </div>
              )}
            </div>
          </div>

          {/* All Employees Table */}
          <div className="p-5 rounded-xl" style={{ background: THEME.bg.secondary, border: `1px solid ${THEME.border.subtle}` }}>
            <h3 className="text-sm font-medium flex items-center gap-2 mb-4" style={{ color: THEME.text.primary }}>
              <Users size={16} />
              جميع الموظفين ({smartMonitorData?.total_employees || 0})
            </h3>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {smartMonitorData?.all_evaluations?.map(emp => (
                <div 
                  key={emp.employee_id}
                  className="flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors hover:bg-white/5"
                  style={{ border: `1px solid ${THEME.border.subtle}` }}
                  onClick={() => fetchEmployeeDetails(emp.employee_id)}
                >
                  <div className="relative w-10 h-10 flex-shrink-0">
                    <svg width="40" height="40" className="transform -rotate-90">
                      <circle cx="20" cy="20" r="16" fill="none" stroke={THEME.border.subtle} strokeWidth="3" />
                      <circle cx="20" cy="20" r="16" fill="none" 
                        stroke={getScoreColor(emp.overall_score)} 
                        strokeWidth="3"
                        strokeDasharray={100}
                        strokeDashoffset={100 - emp.overall_score}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-[10px] font-bold" style={{ color: getScoreColor(emp.overall_score) }}>{Math.round(emp.overall_score)}</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate" style={{ color: THEME.text.primary }}>{emp.employee_name}</p>
                    <div className="flex gap-0.5 mt-0.5">
                      {[1,2,3,4,5].map(s => (
                        <Star key={s} size={8} className={s <= (emp.rating?.stars || 0) ? 'fill-amber-400 text-amber-400' : 'text-zinc-700'} />
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        )}

      </main>

      {/* ==================== FOOTER ==================== */}
      <footer 
        className="text-center py-6 mt-8"
        style={{ borderTop: `1px solid ${THEME.border.subtle}` }}
      >
        <p 
          className="text-[10px] uppercase tracking-[0.2em]"
          style={{ color: THEME.text.tertiary }}
        >
          DAR AL CODE • نظام الحوكمة الذكية • {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
}
