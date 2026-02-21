/**
 * My Finances Page - صفحة ماليّاتي
 * 
 * تعرض للموظف:
 * - ملخص الخصومات
 * - تفاصيل كل خصم مع السبب ورقم المعاملة
 * - الإنذارات
 * - PDF للمعاملات
 */
import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Wallet, 
  TrendingDown, 
  AlertTriangle, 
  FileText,
  Calendar,
  Clock,
  ArrowUpRight,
  AlertCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import api from '@/lib/api';

export default function MyFinancesPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [deductions, setDeductions] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedDeduction, setExpandedDeduction] = useState(null);

  useEffect(() => {
    fetchData();
  }, [user]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [summaryRes, deductionsRes, warningsRes] = await Promise.all([
        api.get('/api/attendance-engine/my-finances/summary'),
        api.get('/api/attendance-engine/my-finances/deductions'),
        api.get('/api/attendance-engine/my-finances/warnings')
      ]);
      
      setSummary(summaryRes.data);
      setDeductions(deductionsRes.data);
      setWarnings(warningsRes.data);
    } catch (err) {
      console.error('Error fetching finances:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR'
    }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ar-EG');
  };

  const getDeductionTypeLabel = (type) => {
    const types = {
      'absence': { ar: 'غياب', en: 'Absence' },
      'late': { ar: 'تأخير', en: 'Late' },
      'early_leave': { ar: 'خروج مبكر', en: 'Early Leave' },
      'hours_deficit': { ar: 'نقص ساعات', en: 'Hours Deficit' }
    };
    return types[type]?.[lang] || type;
  };

  const getWarningTypeLabel = (type) => {
    const types = {
      'first_warning': { ar: 'إنذار أول', en: 'First Warning' },
      'second_warning': { ar: 'إنذار ثاني', en: 'Second Warning' },
      'third_warning': { ar: 'إنذار ثالث (نهائي)', en: 'Final Warning' },
      'termination_case': { ar: 'حالة إنهاء خدمات', en: 'Termination Case' }
    };
    return types[type]?.[lang] || type;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="my-finances-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Wallet className="text-primary" />
            {lang === 'ar' ? 'ماليّاتي' : 'My Finances'}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {lang === 'ar' ? 'سجل الخصومات والإنذارات' : 'Deductions and warnings record'}
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Monthly Deductions */}
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">
                {lang === 'ar' ? 'خصومات الشهر' : 'Monthly Deductions'}
              </span>
              <TrendingDown size={18} className="text-red-500" />
            </div>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {formatCurrency(summary?.monthly_deductions?.total)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {summary?.monthly_deductions?.count || 0} {lang === 'ar' ? 'خصم' : 'deductions'}
            </p>
          </CardContent>
        </Card>

        {/* Yearly Deductions */}
        <Card className="border-orange-200 dark:border-orange-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">
                {lang === 'ar' ? 'خصومات السنة' : 'Yearly Deductions'}
              </span>
              <Calendar size={18} className="text-[hsl(var(--warning))]" />
            </div>
            <p className="text-2xl font-bold text-[hsl(var(--warning))] dark:text-[hsl(var(--warning))]">
              {formatCurrency(summary?.yearly_deductions?.total)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {summary?.yearly_deductions?.count || 0} {lang === 'ar' ? 'خصم' : 'deductions'}
            </p>
          </CardContent>
        </Card>

        {/* Warnings */}
        <Card className="border-[hsl(var(--warning)/0.3)] dark:border-amber-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">
                {lang === 'ar' ? 'الإنذارات' : 'Warnings'}
              </span>
              <AlertTriangle size={18} className="text-[hsl(var(--warning))]" />
            </div>
            <p className="text-2xl font-bold text-[hsl(var(--warning))] dark:text-[hsl(var(--warning))]">
              {summary?.warnings_count || 0}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {lang === 'ar' ? 'إنذار هذه السنة' : 'warnings this year'}
            </p>
          </CardContent>
        </Card>

        {/* Absent Days */}
        <Card className="border-violet-200 dark:border-violet-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">
                {lang === 'ar' ? 'أيام الغياب' : 'Absent Days'}
              </span>
              <Clock size={18} className="text-violet-500" />
            </div>
            <p className="text-2xl font-bold text-accent dark:text-violet-400">
              {summary?.absence_summary?.total_absent_days || 0}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {lang === 'ar' ? `أقصى متصل: ${summary?.absence_summary?.max_consecutive || 0}` : `Max consecutive: ${summary?.absence_summary?.max_consecutive || 0}`}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Warning Alert */}
      {(summary?.absence_summary?.warning_15_days || summary?.absence_summary?.warning_30_days) && (
        <Card className="border-red-500 bg-red-50 dark:bg-red-950/20">
          <CardContent className="p-4 flex items-center gap-4">
            <AlertCircle className="text-red-500 flex-shrink-0" size={24} />
            <div>
              <p className="font-semibold text-red-700 dark:text-red-400">
                {lang === 'ar' ? 'تحذير هام!' : 'Important Warning!'}
              </p>
              <p className="text-sm text-red-600 dark:text-red-500">
                {summary?.absence_summary?.warning_15_days && (
                  <span>{lang === 'ar' ? 'تجاوزت 15 يوم غياب متصل - قد يؤدي لإنهاء الخدمات' : 'Exceeded 15 consecutive absent days'}</span>
                )}
                {summary?.absence_summary?.warning_30_days && (
                  <span>{lang === 'ar' ? 'تجاوزت 30 يوم غياب في السنة - قد يؤدي لإنهاء الخدمات' : 'Exceeded 30 scattered absent days'}</span>
                )}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Deductions List */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <TrendingDown size={18} className="text-red-500" />
            {lang === 'ar' ? 'سجل الخصومات' : 'Deductions Record'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {deductions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {lang === 'ar' ? 'لا توجد خصومات مسجلة' : 'No deductions recorded'}
            </div>
          ) : (
            <div className="space-y-3">
              {deductions.map((d, idx) => (
                <div 
                  key={d.id || idx}
                  className="border rounded-xl overflow-hidden"
                  data-testid={`deduction-${d.id}`}
                >
                  {/* Main Row */}
                  <div 
                    className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => setExpandedDeduction(expandedDeduction === d.id ? null : d.id)}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                        <TrendingDown size={18} className="text-red-500" />
                      </div>
                      <div>
                        <p className="font-semibold">{d.description_ar || d.description}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(d.executed_at)} • {d.month}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-end">
                        <p className="font-bold text-red-600 dark:text-red-400">
                          - {formatCurrency(d.amount)}
                        </p>
                        <Badge variant="outline" className="text-xs">
                          {getDeductionTypeLabel(d.deduction_type)}
                        </Badge>
                      </div>
                      {expandedDeduction === d.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedDeduction === d.id && (
                    <div className="border-t bg-muted/30 p-4 space-y-3">
                      {/* Explanation */}
                      {d.explanation && (
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-muted-foreground">
                            {lang === 'ar' ? 'تفاصيل القرار:' : 'Decision details:'}
                          </p>
                          <div className="bg-white dark:bg-gray-900 rounded-lg p-3 text-sm space-y-1">
                            {Object.entries(d.explanation).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="text-muted-foreground">{key}:</span>
                                <span className="font-medium">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Source Reference */}
                      <div className="flex items-center gap-2 text-sm">
                        <FileText size={14} className="text-muted-foreground" />
                        <span className="text-muted-foreground">
                          {lang === 'ar' ? 'رقم المرجع:' : 'Reference:'}
                        </span>
                        <span className="font-mono text-xs">{d.source_id?.slice(0, 8) || 'N/A'}</span>
                      </div>

                      {/* Executor */}
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted-foreground">
                          {lang === 'ar' ? 'نُفذ بواسطة:' : 'Executed by:'}
                        </span>
                        <Badge variant="secondary">STAS</Badge>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Warnings List */}
      {warnings.length > 0 && (
        <Card className="border-[hsl(var(--warning)/0.3)] dark:border-amber-800">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle size={18} className="text-[hsl(var(--warning))]" />
              {lang === 'ar' ? 'سجل الإنذارات' : 'Warnings Record'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {warnings.map((w, idx) => (
                <div 
                  key={w.id || idx}
                  className="p-4 border rounded-xl bg-[hsl(var(--warning)/0.1)] dark:bg-amber-950/20"
                  data-testid={`warning-${w.id}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-full bg-amber-200 dark:bg-amber-800 flex items-center justify-center mt-1">
                        <AlertTriangle size={14} className="text-[hsl(var(--warning))] dark:text-amber-300" />
                      </div>
                      <div>
                        <p className="font-semibold text-[hsl(var(--warning))] dark:text-amber-200">
                          {w.warning_type_ar || getWarningTypeLabel(w.warning_type)}
                        </p>
                        <p className="text-sm text-[hsl(var(--warning))] dark:text-amber-300 mt-1">
                          {w.reason_ar || w.reason}
                        </p>
                        <p className="text-xs text-[hsl(var(--warning))] dark:text-[hsl(var(--warning))] mt-2">
                          {formatDate(w.executed_at)}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="border-[hsl(var(--warning)/0.3)] text-[hsl(var(--warning))] dark:text-amber-300">
                      {w.violation_type_ar || w.violation_type}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
