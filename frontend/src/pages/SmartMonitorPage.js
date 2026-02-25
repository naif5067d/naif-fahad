import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { 
  Brain, TrendingUp, TrendingDown, Users, Clock, 
  AlertTriangle, Award, Star, ChevronDown, ChevronUp,
  RefreshCw, Eye, BarChart3, Target, Zap, User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import { toast } from 'sonner';

// ==================== THEME ====================
const THEME = {
  excellent: { bg: 'bg-emerald-500/10', text: 'text-emerald-500', border: 'border-emerald-500/20' },
  good: { bg: 'bg-blue-500/10', text: 'text-blue-500', border: 'border-blue-500/20' },
  acceptable: { bg: 'bg-amber-500/10', text: 'text-amber-500', border: 'border-amber-500/20' },
  poor: { bg: 'bg-red-500/10', text: 'text-red-500', border: 'border-red-500/20' },
};

const getScoreTheme = (score) => {
  if (score >= 90) return THEME.excellent;
  if (score >= 70) return THEME.good;
  if (score >= 50) return THEME.acceptable;
  return THEME.poor;
};

// ==================== COMPONENTS ====================

const ScoreCircle = ({ score, size = 60 }) => {
  const theme = getScoreTheme(score);
  const circumference = 2 * Math.PI * 24;
  const offset = circumference - (score / 100) * circumference;
  
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size/2} cy={size/2} r={24} fill="none" stroke="currentColor" strokeWidth="4" className="text-muted/20" />
        <circle 
          cx={size/2} cy={size/2} r={24} fill="none" 
          stroke="currentColor" strokeWidth="4"
          strokeDasharray={circumference} strokeDashoffset={offset}
          className={theme.text}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`text-sm font-bold ${theme.text}`}>{Math.round(score)}</span>
      </div>
    </div>
  );
};

const StarRating = ({ stars }) => (
  <div className="flex gap-0.5">
    {[1,2,3,4,5].map(i => (
      <Star 
        key={i} 
        size={14} 
        className={i <= stars ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground/30'} 
      />
    ))}
  </div>
);

const EmployeeCard = ({ employee, onClick }) => {
  const theme = getScoreTheme(employee.overall_score);
  
  return (
    <Card 
      className={`cursor-pointer hover:shadow-lg transition-all ${theme.border} border`}
      onClick={() => onClick(employee.employee_id)}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <ScoreCircle score={employee.overall_score} />
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold truncate">{employee.employee_name}</h4>
            <p className="text-xs text-muted-foreground">{employee.department || 'غير محدد'}</p>
            <div className="flex items-center gap-2 mt-1">
              <StarRating stars={employee.rating?.stars || 0} />
              <Badge variant="outline" className={`text-[10px] ${theme.text} ${theme.bg}`}>
                {employee.rating?.label}
              </Badge>
            </div>
          </div>
          <div className="text-left text-xs space-y-1">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock size={10} />
              <span>حضور: {employee.attendance_score}%</span>
            </div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <Target size={10} />
              <span>مهام: {employee.tasks_score}%</span>
            </div>
            {employee.forget_checkin_count > 0 && (
              <div className="flex items-center gap-1 text-amber-500">
                <AlertTriangle size={10} />
                <span>نسيان: {employee.forget_checkin_count}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const AlertCard = ({ alert }) => {
  const typeConfig = {
    success: { icon: Award, bg: 'bg-emerald-500/10', text: 'text-emerald-500', border: 'border-emerald-500/30' },
    warning: { icon: AlertTriangle, bg: 'bg-amber-500/10', text: 'text-amber-500', border: 'border-amber-500/30' },
    info: { icon: Zap, bg: 'bg-blue-500/10', text: 'text-blue-500', border: 'border-blue-500/30' },
  };
  const config = typeConfig[alert.type] || typeConfig.info;
  const Icon = config.icon;
  
  return (
    <div className={`p-3 rounded-lg border ${config.bg} ${config.border}`}>
      <div className="flex items-start gap-3">
        <Icon size={18} className={config.text} />
        <div className="flex-1">
          <h4 className={`font-medium text-sm ${config.text}`}>{alert.title}</h4>
          <p className="text-xs text-muted-foreground mt-0.5">{alert.message}</p>
          {alert.employees && alert.employees.length > 0 && (
            <p className="text-xs text-muted-foreground mt-1">
              {alert.employees.join('، ')}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// ==================== MAIN COMPONENT ====================

export default function SmartMonitorPage() {
  const { user } = useAuth();
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [employeeDetails, setEmployeeDetails] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/analytics/ai/smart-monitor?month=${month}`);
      setData(res.data);
    } catch (err) {
      toast.error('فشل تحميل البيانات');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const fetchEmployeeDetails = async (employeeId) => {
    try {
      const res = await api.get(`/api/analytics/ai/employee/${employeeId}?month=${month}`);
      setEmployeeDetails(res.data);
      setSelectedEmployee(employeeId);
    } catch (err) {
      toast.error('فشل تحميل تفاصيل الموظف');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Brain className="w-12 h-12 mx-auto mb-4 text-primary animate-pulse" />
          <p className="text-muted-foreground">جاري تحليل البيانات بالذكاء الاصطناعي...</p>
        </div>
      </div>
    );
  }

  const displayedEmployees = showAll ? data?.all_evaluations : data?.all_evaluations?.slice(0, 10);

  return (
    <div className="space-y-6 p-4 md:p-6" dir="rtl" data-testid="smart-monitor-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="text-primary" />
            المراقب الذكي
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            تقييم شامل للموظفين بالذكاء الاصطناعي
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background text-sm"
          />
          <Button variant="outline" size="icon" onClick={fetchData}>
            <RefreshCw size={16} />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">المتوسط العام</p>
                <p className="text-2xl font-bold">{data?.company_average || 0}%</p>
              </div>
              <BarChart3 className="text-primary" size={24} />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-emerald-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">ممتاز</p>
                <p className="text-2xl font-bold text-emerald-500">{data?.distribution?.excellent || 0}</p>
              </div>
              <Award className="text-emerald-500" size={24} />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-blue-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">جيد</p>
                <p className="text-2xl font-bold text-blue-500">{data?.distribution?.good || 0}</p>
              </div>
              <TrendingUp className="text-blue-500" size={24} />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-red-500/30">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">يحتاج تحسين</p>
                <p className="text-2xl font-bold text-red-500">{data?.distribution?.needs_improvement || 0}</p>
              </div>
              <TrendingDown className="text-red-500" size={24} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts */}
      {data?.alerts && data.alerts.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-semibold flex items-center gap-2">
            <Zap size={18} className="text-amber-500" />
            تنبيهات ذكية
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.alerts.map((alert, i) => (
              <AlertCard key={i} alert={alert} />
            ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Top Performers */}
        <Card className="border-emerald-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Award className="text-emerald-500" size={18} />
              الموظفين المتميزين
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data?.top_performers?.map((emp, i) => (
              <div 
                key={emp.employee_id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => fetchEmployeeDetails(emp.employee_id)}
              >
                <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-xs font-bold">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{emp.employee_name}</p>
                  <StarRating stars={emp.rating?.stars || 0} />
                </div>
                <span className="text-emerald-500 font-bold">{emp.overall_score}%</span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Bottom Performers */}
        <Card className="border-red-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="text-red-500" size={18} />
              يحتاجون متابعة
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data?.bottom_performers?.map((emp, i) => (
              <div 
                key={emp.employee_id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                onClick={() => fetchEmployeeDetails(emp.employee_id)}
              >
                <span className="w-6 h-6 rounded-full bg-red-500/20 text-red-500 flex items-center justify-center text-xs font-bold">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{emp.employee_name}</p>
                  <div className="flex gap-2 text-[10px] text-muted-foreground">
                    {emp.forget_checkin_count > 0 && <span>نسيان: {emp.forget_checkin_count}</span>}
                    {emp.late_excuse_count > 0 && <span>تأخير: {emp.late_excuse_count}</span>}
                  </div>
                </div>
                <span className="text-red-500 font-bold">{emp.overall_score}%</span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Employee Details */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <User size={18} />
              تفاصيل الموظف
            </CardTitle>
          </CardHeader>
          <CardContent>
            {employeeDetails ? (
              <div className="space-y-4">
                <div className="text-center">
                  <h3 className="font-bold">{employeeDetails.employee_name}</h3>
                  <p className="text-xs text-muted-foreground">{employeeDetails.job_title}</p>
                  <div className="flex justify-center mt-2">
                    <ScoreCircle score={employeeDetails.evaluation.overall_score} size={80} />
                  </div>
                  <div className="flex justify-center mt-2">
                    <StarRating stars={employeeDetails.evaluation.rating.stars} />
                  </div>
                  <Badge 
                    className="mt-2"
                    style={{ backgroundColor: employeeDetails.evaluation.rating.color + '20', color: employeeDetails.evaluation.rating.color }}
                  >
                    {employeeDetails.evaluation.rating.label}
                  </Badge>
                </div>
                
                {/* Breakdown */}
                <div className="space-y-2">
                  {Object.entries(employeeDetails.evaluation.breakdown).map(([key, val]) => (
                    <div key={key} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">
                          {key === 'attendance' ? 'الحضور' : 
                           key === 'tasks' ? 'المهام' :
                           key === 'excuses' ? 'الأعذار' :
                           key === 'financial' ? 'المالية' : 'الطلبات'}
                        </span>
                        <span className="font-medium">{val.score}%</span>
                      </div>
                      <Progress value={val.score} className="h-1.5" />
                    </div>
                  ))}
                </div>
                
                {/* Strengths & Weaknesses */}
                {employeeDetails.evaluation.strengths.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-emerald-500 mb-1">نقاط القوة:</p>
                    <ul className="text-xs text-muted-foreground space-y-0.5">
                      {employeeDetails.evaluation.strengths.map((s, i) => (
                        <li key={i}>✓ {s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {employeeDetails.evaluation.weaknesses.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-red-500 mb-1">يحتاج تحسين:</p>
                    <ul className="text-xs text-muted-foreground space-y-0.5">
                      {employeeDetails.evaluation.weaknesses.map((w, i) => (
                        <li key={i}>• {w}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full"
                  onClick={() => navigate(`/employees/${employeeDetails.employee_id}`)}
                >
                  <Eye size={14} className="me-2" />
                  عرض الملف الكامل
                </Button>
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <User size={40} className="mx-auto mb-2 opacity-30" />
                <p className="text-sm">اختر موظف لعرض التفاصيل</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* All Employees */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Users size={18} />
              جميع الموظفين ({data?.total_employees || 0})
            </span>
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              {showAll ? 'عرض أقل' : 'عرض الكل'}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {displayedEmployees?.map(emp => (
              <EmployeeCard 
                key={emp.employee_id} 
                employee={emp} 
                onClick={fetchEmployeeDetails}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
