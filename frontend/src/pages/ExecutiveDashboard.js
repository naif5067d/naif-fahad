import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { 
  TrendingUp, TrendingDown, Users, Clock, FileText, Wallet,
  AlertTriangle, CheckCircle, Activity, BarChart3, Target,
  Maximize2, Minimize2, RefreshCw, Bell
} from 'lucide-react';
import api from '@/lib/api';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';

// ==================== PREMIUM COLORS ====================
const COLORS = {
  bg: '#0a0a0b',
  bgCard: '#111113',
  bgHover: '#1a1a1d',
  border: '#222225',
  borderLight: '#2a2a2d',
  text: '#fafafa',
  textMuted: '#71717a',
  textDim: '#52525b',
  accent: '#3b82f6',
  accentLight: '#60a5fa',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  purple: '#8b5cf6',
};

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];

// ==================== COMPONENTS ====================

const ScoreRing = ({ score, size = 200, strokeWidth = 12 }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;
  
  const getColor = (s) => {
    if (s >= 85) return COLORS.success;
    if (s >= 70) return COLORS.accent;
    if (s >= 50) return COLORS.warning;
    return COLORS.danger;
  };
  
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={COLORS.border}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor(score)}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-6xl font-light tracking-tight" style={{ color: COLORS.text }}>
          {score}
        </span>
        <span className="text-sm uppercase tracking-widest mt-1" style={{ color: COLORS.textMuted }}>
          من 100
        </span>
      </div>
    </div>
  );
};

const MetricCard = ({ title, score, icon: Icon, details, trend }) => {
  const getColor = (s) => {
    if (s >= 85) return COLORS.success;
    if (s >= 70) return COLORS.accent;
    if (s >= 50) return COLORS.warning;
    return COLORS.danger;
  };
  
  return (
    <div 
      className="p-6 rounded-2xl border transition-all duration-300 hover:border-opacity-50"
      style={{ 
        backgroundColor: COLORS.bgCard, 
        borderColor: COLORS.border,
      }}
    >
      <div className="flex items-start justify-between mb-4">
        <div 
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: `${getColor(score)}15` }}
        >
          <Icon size={20} style={{ color: getColor(score) }} />
        </div>
        {trend !== undefined && (
          <div className="flex items-center gap-1 text-xs" style={{ color: trend >= 0 ? COLORS.success : COLORS.danger }}>
            {trend >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      
      <div className="mb-3">
        <div className="text-4xl font-light mb-1" style={{ color: getColor(score) }}>
          {score}<span className="text-lg">%</span>
        </div>
        <div className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
          {title}
        </div>
      </div>
      
      {details && (
        <div className="pt-3 border-t" style={{ borderColor: COLORS.border }}>
          <div className="text-xs space-y-1" style={{ color: COLORS.textDim }}>
            {details}
          </div>
        </div>
      )}
    </div>
  );
};

const AlertBadge = ({ type, children }) => {
  const colors = {
    warning: { bg: `${COLORS.warning}15`, text: COLORS.warning },
    danger: { bg: `${COLORS.danger}15`, text: COLORS.danger },
    info: { bg: `${COLORS.accent}15`, text: COLORS.accent },
  };
  const c = colors[type] || colors.info;
  
  return (
    <span 
      className="px-2 py-1 rounded-md text-xs font-medium"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {children}
    </span>
  );
};

// ==================== MAIN DASHBOARD ====================

export default function ExecutiveDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
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
      console.error('Error fetching dashboard:', e);
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchData();
    
    // Auto refresh every 60 seconds
    const interval = setInterval(() => {
      if (autoRefresh) fetchData();
    }, 60000);
    
    return () => clearInterval(interval);
  }, [fetchData, autoRefresh]);
  
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setFullscreen(true);
    } else {
      document.exitFullscreen();
      setFullscreen(false);
    }
  };
  
  if (loading) {
    return (
      <div 
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: COLORS.bg }}
      >
        <div className="text-center">
          <div 
            className="w-16 h-16 rounded-full border-2 border-t-transparent animate-spin mx-auto mb-4"
            style={{ borderColor: COLORS.accent, borderTopColor: 'transparent' }}
          />
          <p style={{ color: COLORS.textMuted }}>جاري تحميل لوحة الحوكمة...</p>
        </div>
      </div>
    );
  }
  
  const { metrics, top_performers, needs_attention, monthly_trend, executive_summary, quick_stats, health_score } = data || {};
  
  // Prepare chart data
  const trendData = monthly_trend?.map(m => ({
    name: m.month_name,
    score: m.health_score,
    attendance: m.attendance,
    tasks: m.tasks,
  })) || [];
  
  const performerData = top_performers?.slice(0, 5).map(p => ({
    name: p.name?.split(' ')[0] || 'N/A',
    score: p.score,
  })) || [];
  
  const pieData = [
    { name: 'الحضور', value: metrics?.attendance?.score || 0, color: COLORS.accent },
    { name: 'المهام', value: metrics?.tasks?.score || 0, color: COLORS.success },
    { name: 'المالية', value: metrics?.financial?.score || 0, color: COLORS.purple },
    { name: 'الطلبات', value: metrics?.requests?.score || 0, color: COLORS.warning },
  ];
  
  return (
    <div 
      className="min-h-screen p-6 lg:p-8"
      style={{ backgroundColor: COLORS.bg }}
      data-testid="executive-dashboard"
    >
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 
            className="text-2xl lg:text-3xl font-light tracking-tight mb-1"
            style={{ color: COLORS.text }}
          >
            لوحة الحوكمة التنفيذية
          </h1>
          <p className="text-sm" style={{ color: COLORS.textMuted }}>
            {data?.month} • آخر تحديث: {lastUpdate?.toLocaleTimeString('ar-EG')}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {alerts.length > 0 && (
            <div 
              className="flex items-center gap-2 px-3 py-2 rounded-lg"
              style={{ backgroundColor: `${COLORS.warning}15` }}
            >
              <Bell size={16} style={{ color: COLORS.warning }} />
              <span className="text-sm" style={{ color: COLORS.warning }}>
                {alerts.length} تنبيه
              </span>
            </div>
          )}
          
          <button
            onClick={() => { setAutoRefresh(!autoRefresh); fetchData(); }}
            className="p-2 rounded-lg transition-colors"
            style={{ 
              backgroundColor: autoRefresh ? `${COLORS.accent}15` : COLORS.bgCard,
              color: autoRefresh ? COLORS.accent : COLORS.textMuted
            }}
            title={autoRefresh ? 'إيقاف التحديث التلقائي' : 'تفعيل التحديث التلقائي'}
          >
            <RefreshCw size={18} className={autoRefresh ? 'animate-spin' : ''} style={{ animationDuration: '3s' }} />
          </button>
          
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg transition-colors"
            style={{ backgroundColor: COLORS.bgCard, color: COLORS.textMuted }}
            title="وضع ملء الشاشة"
          >
            {fullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
      </header>
      
      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-6">
        
        {/* Health Score - Center */}
        <div className="col-span-12 lg:col-span-4 flex flex-col items-center justify-center">
          <div 
            className="p-8 rounded-3xl border text-center"
            style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
          >
            <p 
              className="text-sm uppercase tracking-widest mb-6"
              style={{ color: COLORS.textMuted }}
            >
              مؤشر صحة الشركة
            </p>
            <ScoreRing score={health_score || 0} size={220} />
            <p 
              className="mt-6 text-sm"
              style={{ color: COLORS.textDim }}
            >
              Company Health Score
            </p>
          </div>
        </div>
        
        {/* Metrics Grid */}
        <div className="col-span-12 lg:col-span-8 grid grid-cols-2 gap-4">
          <MetricCard
            title="الحضور والانضباط"
            score={metrics?.attendance?.score || 0}
            icon={Clock}
            details={
              <>
                <div className="flex justify-between">
                  <span>أيام الحضور</span>
                  <span>{metrics?.attendance?.present_days || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>دقائق التأخير</span>
                  <span>{metrics?.attendance?.late_minutes || 0}</span>
                </div>
              </>
            }
          />
          
          <MetricCard
            title="أداء المهام"
            score={metrics?.tasks?.score || 0}
            icon={Target}
            details={
              <>
                <div className="flex justify-between">
                  <span>المهام المنجزة</span>
                  <span>{metrics?.tasks?.total_tasks || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>متوسط التقييم</span>
                  <span>{metrics?.tasks?.average_rating || 0}/5</span>
                </div>
              </>
            }
          />
          
          <MetricCard
            title="الانضباط المالي"
            score={metrics?.financial?.score || 0}
            icon={Wallet}
            details={
              <>
                <div className="flex justify-between">
                  <span>إجمالي المصروف</span>
                  <span>{(metrics?.financial?.total_spent || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>المُعاد للتدقيق</span>
                  <span>{metrics?.financial?.returned || 0}</span>
                </div>
              </>
            }
          />
          
          <MetricCard
            title="انضباط الطلبات"
            score={metrics?.requests?.score || 0}
            icon={FileText}
            details={
              <>
                <div className="flex justify-between">
                  <span>الطلبات المقبولة</span>
                  <span>{metrics?.requests?.approved || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>المعلقة</span>
                  <span>{metrics?.requests?.pending || 0}</span>
                </div>
              </>
            }
          />
        </div>
        
        {/* Executive Summary */}
        <div className="col-span-12">
          <div 
            className="p-6 rounded-2xl border"
            style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
          >
            <div className="flex items-center gap-3 mb-4">
              <Activity size={20} style={{ color: COLORS.accent }} />
              <span className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                الملخص التنفيذي
              </span>
            </div>
            <p 
              className="text-lg font-light leading-relaxed"
              style={{ color: COLORS.text }}
            >
              {executive_summary || 'جاري تحليل البيانات...'}
            </p>
          </div>
        </div>
        
        {/* Charts Row */}
        <div className="col-span-12 lg:col-span-8">
          <div 
            className="p-6 rounded-2xl border h-full"
            style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <BarChart3 size={20} style={{ color: COLORS.accent }} />
                <span className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                  اتجاه الأداء الشهري
                </span>
              </div>
            </div>
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={COLORS.accent} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={COLORS.accent} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                  <XAxis dataKey="name" stroke={COLORS.textDim} fontSize={12} />
                  <YAxis stroke={COLORS.textDim} fontSize={12} domain={[0, 100]} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: COLORS.bgCard, 
                      border: `1px solid ${COLORS.border}`,
                      borderRadius: 8,
                      color: COLORS.text
                    }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="score" 
                    stroke={COLORS.accent} 
                    strokeWidth={2}
                    fill="url(#scoreGradient)" 
                    name="الدرجة"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        
        {/* Distribution Pie */}
        <div className="col-span-12 lg:col-span-4">
          <div 
            className="p-6 rounded-2xl border h-full"
            style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
          >
            <div className="flex items-center gap-3 mb-6">
              <span className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                توزيع المؤشرات
              </span>
            </div>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: COLORS.bgCard, 
                      border: `1px solid ${COLORS.border}`,
                      borderRadius: 8,
                      color: COLORS.text
                    }}
                    formatter={(value) => [`${value}%`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {pieData.map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                  <span style={{ color: COLORS.textMuted }}>{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Top Performers */}
        <div className="col-span-12 lg:col-span-6">
          <div 
            className="p-6 rounded-2xl border"
            style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
          >
            <div className="flex items-center gap-3 mb-6">
              <TrendingUp size={20} style={{ color: COLORS.success }} />
              <span className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                الأعلى أداءً
              </span>
            </div>
            <div className="space-y-3">
              {top_performers?.slice(0, 5).map((emp, i) => (
                <div 
                  key={i}
                  className="flex items-center justify-between p-3 rounded-lg"
                  style={{ backgroundColor: COLORS.bg }}
                >
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
                      style={{ backgroundColor: `${COLORS.success}20`, color: COLORS.success }}
                    >
                      {i + 1}
                    </div>
                    <div>
                      <div className="text-sm" style={{ color: COLORS.text }}>{emp.name}</div>
                      <div className="text-xs" style={{ color: COLORS.textDim }}>{emp.department}</div>
                    </div>
                  </div>
                  <div 
                    className="text-lg font-light"
                    style={{ color: COLORS.success }}
                  >
                    {emp.score}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Needs Attention */}
        <div className="col-span-12 lg:col-span-6">
          <div 
            className="p-6 rounded-2xl border"
            style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
          >
            <div className="flex items-center gap-3 mb-6">
              <AlertTriangle size={20} style={{ color: COLORS.warning }} />
              <span className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                يحتاج متابعة
              </span>
            </div>
            <div className="space-y-3">
              {needs_attention?.slice(0, 5).map((emp, i) => (
                <div 
                  key={i}
                  className="flex items-center justify-between p-3 rounded-lg"
                  style={{ backgroundColor: COLORS.bg }}
                >
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
                      style={{ backgroundColor: `${COLORS.warning}20`, color: COLORS.warning }}
                    >
                      {i + 1}
                    </div>
                    <div>
                      <div className="text-sm" style={{ color: COLORS.text }}>{emp.name}</div>
                      <div className="text-xs" style={{ color: COLORS.textDim }}>{emp.department}</div>
                    </div>
                  </div>
                  <div 
                    className="text-lg font-light"
                    style={{ color: emp.score < 50 ? COLORS.danger : COLORS.warning }}
                  >
                    {emp.score}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Quick Stats */}
        <div className="col-span-12">
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'الموظفين النشطين', value: quick_stats?.total_employees, icon: Users, color: COLORS.accent },
              { label: 'الطلبات المعلقة', value: quick_stats?.pending_requests, icon: FileText, color: COLORS.warning },
              { label: 'العهد المفتوحة', value: quick_stats?.open_custodies, icon: Wallet, color: COLORS.purple },
              { label: 'المهام الجارية', value: quick_stats?.active_tasks, icon: Target, color: COLORS.success },
            ].map((stat, i) => (
              <div 
                key={i}
                className="p-4 rounded-xl border flex items-center gap-4"
                style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
              >
                <div 
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${stat.color}10` }}
                >
                  <stat.icon size={22} style={{ color: stat.color }} />
                </div>
                <div>
                  <div className="text-2xl font-light" style={{ color: COLORS.text }}>
                    {stat.value || 0}
                  </div>
                  <div className="text-xs" style={{ color: COLORS.textMuted }}>
                    {stat.label}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Alerts Section */}
        {alerts.length > 0 && (
          <div className="col-span-12">
            <div 
              className="p-6 rounded-2xl border"
              style={{ backgroundColor: COLORS.bgCard, borderColor: COLORS.border }}
            >
              <div className="flex items-center gap-3 mb-4">
                <Bell size={20} style={{ color: COLORS.warning }} />
                <span className="text-sm uppercase tracking-wider" style={{ color: COLORS.textMuted }}>
                  التنبيهات
                </span>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {alerts.map((alert, i) => (
                  <div 
                    key={i}
                    className="flex items-center gap-4 p-4 rounded-lg"
                    style={{ backgroundColor: COLORS.bg }}
                  >
                    <AlertBadge type={alert.type}>{alert.priority === 'high' ? 'عاجل' : 'متوسط'}</AlertBadge>
                    <div>
                      <div className="text-sm font-medium" style={{ color: COLORS.text }}>{alert.title}</div>
                      <div className="text-xs" style={{ color: COLORS.textDim }}>{alert.message}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        
      </div>
      
      {/* Footer */}
      <footer className="mt-8 text-center">
        <p className="text-xs" style={{ color: COLORS.textDim }}>
          DAR AL CODE • نظام الحوكمة الذكية • {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
}
