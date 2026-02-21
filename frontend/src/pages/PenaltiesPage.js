/**
 * Penalties Page - صفحة العقوبات
 * 
 * تعرض:
 * - تقرير الخصومات الشهري
 * - تفاصيل الغياب والتأخير
 * - الإنذارات
 */
import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog';
import {
  AlertTriangle,
  FileWarning,
  Clock,
  UserX,
  TrendingDown,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function PenaltiesPage() {
  const { lang } = useLanguage();
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7));
  const [expandedEmployee, setExpandedEmployee] = useState(null);
  const [detailsDialog, setDetailsDialog] = useState(null);

  useEffect(() => {
    fetchReport();
  }, [month]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const [year, mon] = month.split('-').map(Number);
      const res = await api.get('/api/penalties/monthly-report', {
        params: { year, month: mon }
      });
      setReport(res.data);
    } catch (err) {
      console.error('Error:', err);
      toast.error(lang === 'ar' ? 'خطأ في جلب التقرير' : 'Error fetching report');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', { style: 'currency', currency: 'SAR' }).format(amount);
  };

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="penalties-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileWarning className="text-primary" />
            {lang === 'ar' ? 'تقرير الخصومات والعقوبات' : 'Penalties Report'}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {lang === 'ar' ? 'تقرير شهري للغياب والتأخير والخصومات' : 'Monthly absence and lateness report'}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="w-auto"
          />
          <Button variant="outline" size="icon" onClick={fetchReport} disabled={loading}>
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {report?.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-blue-200">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-blue-600">{report.summary.total_employees}</p>
              <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'موظف' : 'Employees'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-red-200">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-red-600">{report.summary.total_absent_days}</p>
              <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'أيام غياب' : 'Absent Days'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-[hsl(var(--warning)/0.3)]">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-[hsl(var(--warning))]">{report.summary.total_deficit_hours?.toFixed(1)}</p>
              <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'ساعات نقص' : 'Deficit Hours'}</p>
            </CardContent>
          </Card>
          
          <Card className="border-violet-200">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-accent">{formatCurrency(report.summary.total_deduction_amount)}</p>
              <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'إجمالي الخصم' : 'Total Deduction'}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Rules Info */}
      <Card className="bg-[hsl(var(--warning)/0.1)] dark:bg-[hsl(var(--warning)/0.15)] border-[hsl(var(--warning)/0.3)]">
        <CardContent className="p-4">
          <h3 className="font-bold flex items-center gap-2 mb-3">
            <AlertTriangle className="text-[hsl(var(--warning))]" size={20} />
            {lang === 'ar' ? 'قواعد الخصم' : 'Deduction Rules'}
          </h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-[hsl(var(--warning))]">{lang === 'ar' ? 'الغياب:' : 'Absence:'}</p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1 mr-2">
                <li>{lang === 'ar' ? 'يوم غياب = خصم يوم' : '1 day absence = 1 day deduction'}</li>
                <li>{lang === 'ar' ? '3 أيام متصلة = إنذار أول' : '3 consecutive days = First warning'}</li>
                <li>{lang === 'ar' ? '5 أيام متصلة = إنذار ثاني' : '5 consecutive days = Second warning'}</li>
                <li>{lang === 'ar' ? '10 أيام متصلة = إنذار نهائي' : '10 consecutive days = Final warning'}</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-[hsl(var(--warning))]">{lang === 'ar' ? 'التأخير والخروج المبكر:' : 'Late & Early Leave:'}</p>
              <ul className="list-disc list-inside text-muted-foreground space-y-1 mr-2">
                <li>{lang === 'ar' ? 'يحسب بالدقائق' : 'Calculated in minutes'}</li>
                <li>{lang === 'ar' ? 'يجمع شهرياً' : 'Accumulated monthly'}</li>
                <li>{lang === 'ar' ? 'كل 8 ساعات نقص = خصم يوم' : 'Every 8 hours deficit = 1 day deduction'}</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Employees Table */}
      <Card>
        <CardHeader>
          <CardTitle>{lang === 'ar' ? 'تفاصيل الموظفين' : 'Employee Details'}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <RefreshCw className="animate-spin text-primary" size={32} />
            </div>
          ) : !report?.employees?.length ? (
            <div className="text-center py-8 text-muted-foreground">
              {lang === 'ar' ? 'لا توجد بيانات' : 'No data'}
            </div>
          ) : (
            <div className="space-y-3">
              {report.employees.map((emp) => (
                <div 
                  key={emp.employee_id}
                  className="border rounded-lg overflow-hidden"
                >
                  {/* Employee Row */}
                  <div 
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50"
                    onClick={() => setExpandedEmployee(expandedEmployee === emp.employee_id ? null : emp.employee_id)}
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                        {emp.employee_name_ar?.[0] || '?'}
                      </div>
                      <div>
                        <p className="font-medium">{emp.employee_name_ar}</p>
                        <p className="text-xs text-muted-foreground">{emp.employee_id}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      {/* Absence */}
                      {emp.absence?.total_days > 0 && (
                        <div className="text-center">
                          <Badge variant="destructive" className="text-xs">
                            <UserX size={12} className="mr-1" />
                            {emp.absence.total_days} {lang === 'ar' ? 'غياب' : 'absent'}
                          </Badge>
                        </div>
                      )}
                      
                      {/* Deficit */}
                      {emp.deficit?.total_deficit_hours > 0 && (
                        <div className="text-center">
                          <Badge variant="outline" className="text-xs text-[hsl(var(--warning))] border-[hsl(var(--warning)/0.3)]">
                            <Clock size={12} className="mr-1" />
                            {emp.deficit.total_deficit_hours} {lang === 'ar' ? 'ساعة' : 'hrs'}
                          </Badge>
                        </div>
                      )}
                      
                      {/* Total Deduction */}
                      {emp.total_deduction_days > 0 && (
                        <div className="text-center">
                          <Badge className="bg-accent/15 text-accent text-xs">
                            <TrendingDown size={12} className="mr-1" />
                            {emp.total_deduction_days} {lang === 'ar' ? 'يوم خصم' : 'days'}
                          </Badge>
                        </div>
                      )}
                      
                      {/* Warnings */}
                      {emp.absence?.warnings?.length > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          <AlertTriangle size={12} className="mr-1" />
                          {emp.absence.warnings[0].name_ar}
                        </Badge>
                      )}
                      
                      {expandedEmployee === emp.employee_id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </div>
                  </div>
                  
                  {/* Expanded Details */}
                  {expandedEmployee === emp.employee_id && (
                    <div className="p-4 pt-0 border-t bg-muted/30">
                      <div className="grid md:grid-cols-2 gap-4 mt-4">
                        {/* Absence Details */}
                        <div className="p-3 bg-red-50 dark:bg-red-900/10 rounded-lg">
                          <h4 className="font-medium text-red-700 mb-2 flex items-center gap-2">
                            <UserX size={16} />
                            {lang === 'ar' ? 'الغياب' : 'Absence'}
                          </h4>
                          <div className="text-sm space-y-1">
                            <p>{lang === 'ar' ? 'إجمالي أيام الغياب:' : 'Total absent days:'} <strong>{emp.absence?.total_days || 0}</strong></p>
                            <p>{lang === 'ar' ? 'خصم:' : 'Deduction:'} <strong>{emp.absence?.deduction_days || 0} {lang === 'ar' ? 'يوم' : 'days'}</strong></p>
                            
                            {emp.absence?.consecutive_streaks?.length > 0 && (
                              <div className="mt-2">
                                <p className="font-medium">{lang === 'ar' ? 'فترات الغياب المتصل:' : 'Consecutive periods:'}</p>
                                {emp.absence.consecutive_streaks.map((streak, idx) => (
                                  <p key={idx} className="text-xs text-muted-foreground">
                                    {streak.start} → {streak.end} ({streak.days} {lang === 'ar' ? 'أيام' : 'days'})
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {/* Deficit Details */}
                        <div className="p-3 bg-[hsl(var(--warning)/0.1)] dark:bg-[hsl(var(--warning)/0.15)] rounded-lg">
                          <h4 className="font-medium text-[hsl(var(--warning))] mb-2 flex items-center gap-2">
                            <Clock size={16} />
                            {lang === 'ar' ? 'نقص الساعات' : 'Hours Deficit'}
                          </h4>
                          <div className="text-sm space-y-1">
                            <p>{lang === 'ar' ? 'دقائق التأخير:' : 'Late minutes:'} <strong>{emp.deficit?.total_late_minutes || 0}</strong></p>
                            <p>{lang === 'ar' ? 'دقائق الخروج المبكر:' : 'Early leave minutes:'} <strong>{emp.deficit?.total_early_leave_minutes || 0}</strong></p>
                            <p>{lang === 'ar' ? 'إجمالي النقص:' : 'Total deficit:'} <strong>{emp.deficit?.total_deficit_hours || 0} {lang === 'ar' ? 'ساعة' : 'hours'}</strong></p>
                            <p>{lang === 'ar' ? 'خصم:' : 'Deduction:'} <strong>{emp.deficit?.deduction_days || 0} {lang === 'ar' ? 'يوم' : 'days'}</strong></p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Summary */}
                      <div className="mt-4 p-3 bg-accent/10 dark:bg-accent/15 rounded-lg">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-medium">{lang === 'ar' ? 'إجمالي الخصم:' : 'Total Deduction:'}</p>
                            <p className="text-2xl font-bold text-accent">
                              {emp.total_deduction_days} {lang === 'ar' ? 'يوم' : 'days'}
                            </p>
                          </div>
                          {emp.total_deduction_amount > 0 && (
                            <div className="text-left">
                              <p className="text-sm text-muted-foreground">{lang === 'ar' ? 'المبلغ:' : 'Amount:'}</p>
                              <p className="text-xl font-bold text-accent">
                                {formatCurrency(emp.total_deduction_amount)}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* View Details Button */}
                      <div className="mt-4 text-left">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDetailsDialog(emp);
                          }}
                        >
                          <Eye size={14} className="mr-2" />
                          {lang === 'ar' ? 'عرض التفاصيل اليومية' : 'View Daily Details'}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Details Dialog */}
      <Dialog open={!!detailsDialog} onOpenChange={() => setDetailsDialog(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {lang === 'ar' ? 'التفاصيل اليومية' : 'Daily Details'} - {detailsDialog?.employee_name_ar}
            </DialogTitle>
          </DialogHeader>
          
          {detailsDialog?.daily_details && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-start p-2">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                    <th className="text-center p-2">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                    <th className="text-center p-2">{lang === 'ar' ? 'تأخير' : 'Late'}</th>
                    <th className="text-center p-2">{lang === 'ar' ? 'خروج مبكر' : 'Early'}</th>
                  </tr>
                </thead>
                <tbody>
                  {detailsDialog.daily_details.map((day, idx) => (
                    <tr key={idx} className="border-b">
                      <td className="p-2 font-mono text-xs">{day.date}</td>
                      <td className="p-2 text-center">
                        <Badge variant={day.status === 'ABSENT' ? 'destructive' : 'secondary'}>
                          {day.status_ar || day.status}
                        </Badge>
                      </td>
                      <td className="p-2 text-center">
                        {day.late_minutes > 0 && (
                          <span className="text-[hsl(var(--warning))]">{day.late_minutes} {lang === 'ar' ? 'د' : 'min'}</span>
                        )}
                      </td>
                      <td className="p-2 text-center">
                        {day.early_leave_minutes > 0 && (
                          <span className="text-[hsl(var(--warning))]">{day.early_leave_minutes} {lang === 'ar' ? 'د' : 'min'}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
