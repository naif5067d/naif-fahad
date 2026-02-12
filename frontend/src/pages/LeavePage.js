import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { CalendarDays, Plus } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function LeavePage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [balance, setBalance] = useState({});
  const [holidays, setHolidays] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ leave_type: 'annual', start_date: '', end_date: '', reason: '' });
  const [submitting, setSubmitting] = useState(false);

  const fetchData = () => {
    api.get('/api/leave/balance').then(r => setBalance(r.data)).catch(() => {});
    api.get('/api/leave/holidays').then(r => setHolidays(r.data)).catch(() => {});
  };
  useEffect(() => { fetchData(); }, []);

  const isEmployee = ['employee', 'supervisor', 'sultan', 'salah'].includes(user?.role);

  const handleSubmit = async () => {
    if (!form.start_date || !form.end_date || !form.reason) {
      toast.error('Please fill all fields');
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/api/leave/request', form);
      toast.success(`Leave request created: ${res.data.ref_no}`);
      setDialogOpen(false);
      setForm({ leave_type: 'annual', start_date: '', end_date: '', reason: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="leave-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">{t('leave.title')}</h1>
        {isEmployee && user?.employee_id && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="request-leave-btn" className="bg-primary text-primary-foreground">
                <Plus size={16} className="me-1" /> {t('leave.requestLeave')}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>{t('leave.requestLeave')}</DialogTitle></DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>{t('leave.type')}</Label>
                  <Select value={form.leave_type} onValueChange={v => setForm(f => ({ ...f, leave_type: v }))}>
                    <SelectTrigger data-testid="leave-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="annual">{t('leave.annual')}</SelectItem>
                      <SelectItem value="sick">{t('leave.sick')}</SelectItem>
                      <SelectItem value="emergency">{t('leave.emergency')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>{t('leave.startDate')}</Label>
                    <Input data-testid="leave-start-date" type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
                  </div>
                  <div>
                    <Label>{t('leave.endDate')}</Label>
                    <Input data-testid="leave-end-date" type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <Label>{t('leave.reason')}</Label>
                  <Input data-testid="leave-reason" value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} placeholder={t('leave.reason')} />
                </div>
                <Button data-testid="submit-leave" onClick={handleSubmit} className="w-full bg-primary text-primary-foreground" disabled={submitting}>
                  {submitting ? t('common.loading') : t('leave.submit')}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {['annual', 'sick', 'emergency'].map(lt => (
          <Card key={lt} className="border border-border shadow-none" data-testid={`balance-${lt}`}>
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium text-muted-foreground capitalize">{t(`leave.${lt}`)}</CardTitle>
              <CalendarDays size={18} className="text-blue-600 dark:text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{balance[lt] ?? 0} <span className="text-sm font-normal text-muted-foreground">{t('dashboard.days')}</span></div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Public Holidays */}
      <div>
        <h2 className="text-lg font-semibold mb-3">{t('leave.holidays')}</h2>
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="hr-table" data-testid="holidays-table">
              <thead><tr><th>Date</th><th>Holiday</th></tr></thead>
              <tbody>
                {holidays.map(h => (
                  <tr key={h.id}>
                    <td className="font-mono text-xs">{h.date}</td>
                    <td className="text-sm">{h.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
