import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, CalendarDays, Users, Shield, DollarSign, Clock } from 'lucide-react';
import api from '@/lib/api';

// Status colors based on the role required for approval
const STATUS_COLORS = {
  executed: '#16A34A',      // Green - completed
  rejected: '#DC2626',      // Red - rejected/cancelled
  cancelled: '#DC2626',     // Red - cancelled
  pending_supervisor: '#1D4ED8', // Supervisor blue
  pending_ops: '#F97316',   // Sultan orange
  pending_finance: '#0D9488', // Salah teal
  pending_ceo: '#B91C1C',   // Mohammed red
  pending_stas: '#7C3AED',  // STAS purple
  pending_employee_accept: '#3B82F6', // Employee blue
};

const STAT_CONFIG = {
  employee: [
    { key: 'leave_balance', icon: CalendarDays, label: 'dashboard.leaveBalance', suffix: 'dashboard.days', color: 'text-blue-600 dark:text-blue-400' },
    { key: 'pending_transactions', icon: FileText, label: 'dashboard.pendingApprovals', color: 'text-amber-600 dark:text-amber-400' },
  ],
  supervisor: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', color: 'text-amber-600 dark:text-amber-400' },
    { key: 'team_size', icon: Users, label: 'dashboard.teamSize', color: 'text-blue-600 dark:text-blue-400' },
  ],
  sultan: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', color: 'text-amber-600 dark:text-amber-400' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees', color: 'text-blue-600 dark:text-blue-400' },
    { key: 'total_transactions', icon: Clock, label: 'dashboard.totalTransactions', color: 'text-emerald-600 dark:text-emerald-400' },
  ],
  naif: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', color: 'text-amber-600 dark:text-amber-400' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees', color: 'text-blue-600 dark:text-blue-400' },
  ],
  salah: [
    { key: 'pending_approvals', icon: DollarSign, label: 'dashboard.pendingFinance', color: 'text-amber-600 dark:text-amber-400' },
    { key: 'total_finance_entries', icon: FileText, label: 'dashboard.totalTransactions', color: 'text-emerald-600 dark:text-emerald-400' },
  ],
  mohammed: [
    { key: 'pending_approvals', icon: FileText, label: 'dashboard.pendingApprovals', color: 'text-amber-600 dark:text-amber-400' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees', color: 'text-blue-600 dark:text-blue-400' },
  ],
  stas: [
    { key: 'pending_execution', icon: Shield, label: 'dashboard.pendingExecution', color: 'text-red-600 dark:text-red-400' },
    { key: 'total_transactions', icon: FileText, label: 'dashboard.totalTransactions', color: 'text-blue-600 dark:text-blue-400' },
    { key: 'total_employees', icon: Users, label: 'dashboard.totalEmployees', color: 'text-emerald-600 dark:text-emerald-400' },
  ],
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { t, lang } = useLanguage();
  const navigate = useNavigate();
  const [stats, setStats] = useState({});
  const [recentTxs, setRecentTxs] = useState([]);

  useEffect(() => {
    api.get('/api/dashboard/stats').then(r => setStats(r.data)).catch(() => {});
    api.get('/api/transactions').then(r => setRecentTxs(r.data.slice(0, 8))).catch(() => {});
  }, []);

  const role = user?.role || 'employee';
  const statCards = STAT_CONFIG[role] || STAT_CONFIG.employee;
  const displayName = role === 'stas' ? 'STAS' : (lang === 'ar' ? (user?.full_name_ar || user?.full_name) : user?.full_name);

  // Get status style with role-based colors
  const getStatusStyle = (status) => {
    if (status === 'executed') {
      return { backgroundColor: `${STATUS_COLORS.executed}15`, color: STATUS_COLORS.executed, borderColor: `${STATUS_COLORS.executed}30` };
    }
    if (status === 'rejected') {
      return { backgroundColor: `${STATUS_COLORS.rejected}15`, color: STATUS_COLORS.rejected, borderColor: `${STATUS_COLORS.rejected}30` };
    }
    // For pending statuses, use the specific role color
    if (STATUS_COLORS[status]) {
      return { backgroundColor: `${STATUS_COLORS[status]}15`, color: STATUS_COLORS[status], borderColor: `${STATUS_COLORS[status]}30` };
    }
    // Default fallback
    return { backgroundColor: '#F9731615', color: '#F97316', borderColor: '#F9731630' };
  };

  // Get translated type
  const getTranslatedType = (type) => t(`txTypes.${type}`) || type?.replace(/_/g, ' ');
  
  // Get translated stage
  const getTranslatedStage = (stage) => t(`stages.${stage}`) || stage;

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('dashboard.welcome')}, {displayName}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t(`roles.${role}`)}</p>
      </div>

      {/* Summary Cards - max 3 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map(sc => {
          const Icon = sc.icon;
          return (
            <Card key={sc.key} className="border border-border shadow-none" data-testid={`stat-${sc.key}`}>
              <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t(sc.label)}</CardTitle>
                <Icon size={18} className={sc.color} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats[sc.key] ?? 0}
                  {sc.suffix && <span className="text-sm font-normal text-muted-foreground ms-1">{t(sc.suffix)}</span>}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Recent Transactions Table */}
      <div>
        <h2 className="text-lg font-semibold mb-3">{t('dashboard.recentTransactions')}</h2>
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="hr-table" data-testid="recent-transactions-table">
              <thead>
                <tr>
                  <th>{t('transactions.refNo')}</th>
                  <th>{t('transactions.type')}</th>
                  <th className="hidden sm:table-cell">{t('transactions.employee')}</th>
                  <th>{t('transactions.status')}</th>
                  <th>{t('transactions.stage')}</th>
                </tr>
              </thead>
              <tbody>
                {recentTxs.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-8 text-muted-foreground">{t('transactions.noTransactions')}</td></tr>
                ) : recentTxs.map(tx => (
                  <tr key={tx.id} className="cursor-pointer" onClick={() => navigate(`/transactions/${tx.id}`)} data-testid={`tx-row-${tx.ref_no}`}>
                    <td className="font-mono text-xs">{tx.ref_no}</td>
                    <td className="text-sm">{getTranslatedType(tx.type)}</td>
                    <td className="hidden sm:table-cell text-sm">{lang === 'ar' ? (tx.data?.employee_name_ar || tx.data?.employee_name) : tx.data?.employee_name || '-'}</td>
                    <td>
                      <span 
                        className="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset"
                        style={getStatusStyle(tx.status)}
                      >
                        {t(`status.${tx.status}`) || tx.status}
                      </span>
                    </td>
                    <td className="text-xs text-muted-foreground">{getTranslatedStage(tx.current_stage)}</td>
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
