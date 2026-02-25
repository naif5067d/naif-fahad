import { useLanguage } from '@/contexts/LanguageContext';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Search, Eye, Edit, Play, XCircle, FileText, Trash2,
  AlertTriangle, Calendar
} from 'lucide-react';
import { CONTRACT_STATUS, CONTRACT_CATEGORIES, formatCurrency } from './contractConstants';

export default function ContractList({
  contracts,
  loading,
  searchQuery,
  setSearchQuery,
  statusFilter,
  setStatusFilter,
  onSearch,
  onView,
  onEdit,
  onExecute,
  onTerminate,
  onDelete,
  canEdit,
  canExecute,
  canTerminate,
  canDelete
}) {
  const { lang } = useLanguage();
  const isRTL = lang === 'ar';

  const getStatusBadge = (status) => {
    const s = CONTRACT_STATUS[status] || CONTRACT_STATUS.draft;
    return (
      <Badge className={`${s.color} text-white`}>
        {isRTL ? s.label : s.labelEn}
      </Badge>
    );
  };

  // تحديد إذا كان العقد قريب الانتهاء
  const isExpiringSoon = (contract) => {
    if (!contract.end_date) return false;
    const endDate = new Date(contract.end_date);
    const today = new Date();
    const daysRemaining = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
    return daysRemaining <= 90 && daysRemaining >= 0;
  };

  const getDaysRemaining = (contract) => {
    if (!contract.end_date) return null;
    const endDate = new Date(contract.end_date);
    const today = new Date();
    return Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">{isRTL ? 'جاري التحميل...' : 'Loading...'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-[200px] relative">
          <Search size={18} className="absolute top-1/2 -translate-y-1/2 start-3 text-muted-foreground" />
          <Input 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder={isRTL ? 'بحث بالاسم أو الرقم...' : 'Search by name or number...'}
            className="ps-10"
            onKeyDown={e => e.key === 'Enter' && onSearch?.()}
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder={isRTL ? 'الحالة' : 'Status'} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{isRTL ? 'الكل' : 'All'}</SelectItem>
            {Object.entries(CONTRACT_STATUS).map(([k, v]) => (
              <SelectItem key={k} value={k}>{isRTL ? v.label : v.labelEn}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={onSearch}>
          <Search size={16} className="me-1" />
          {isRTL ? 'بحث' : 'Search'}
        </Button>
      </div>

      {/* Contracts Grid */}
      {contracts.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <FileText size={48} className="mx-auto mb-4 opacity-50" />
          <p>{isRTL ? 'لا توجد عقود' : 'No contracts found'}</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {contracts.map(contract => {
            const expiringSoon = isExpiringSoon(contract);
            const daysRemaining = getDaysRemaining(contract);
            const category = CONTRACT_CATEGORIES[contract.contract_category];
            
            return (
              <Card 
                key={contract.id}
                className={`p-4 hover:shadow-md transition-all ${
                  expiringSoon ? 'border-2 border-warning bg-warning/5' : ''
                }`}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-mono text-xs text-muted-foreground">{contract.contract_serial}</p>
                    <h3 className="font-bold text-lg">
                      {isRTL ? contract.employee_name_ar : contract.employee_name}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {isRTL ? contract.job_title_ar : contract.job_title}
                    </p>
                  </div>
                  {getStatusBadge(contract.status)}
                </div>

                {/* Details */}
                <div className="space-y-2 text-sm mb-4">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{isRTL ? 'القسم' : 'Dept'}</span>
                    <span>{isRTL ? contract.department_ar : contract.department}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{isRTL ? 'الراتب' : 'Salary'}</span>
                    <span className="font-bold">{formatCurrency(contract.total_salary)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{isRTL ? 'البداية' : 'Start'}</span>
                    <span>{contract.start_date}</span>
                  </div>
                  {contract.end_date && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">{isRTL ? 'النهاية' : 'End'}</span>
                      <span className={expiringSoon ? 'text-warning font-bold' : ''}>
                        {contract.end_date}
                      </span>
                    </div>
                  )}
                  {contract.is_migrated && (
                    <Badge variant="outline" className="text-xs">
                      {isRTL ? 'مُهاجر' : 'Migrated'}
                    </Badge>
                  )}
                </div>

                {/* Expiry Warning */}
                {expiringSoon && contract.status === 'active' && (
                  <div className="flex items-center gap-2 p-2 bg-warning/10 rounded mb-3 text-warning text-sm">
                    <AlertTriangle size={16} />
                    <span>
                      {isRTL ? `ينتهي خلال ${daysRemaining} يوم` : `Expires in ${daysRemaining} days`}
                    </span>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-wrap gap-2 pt-3 border-t">
                  <Button size="sm" variant="ghost" onClick={() => onView(contract)}>
                    <Eye size={14} className="me-1" />
                    {isRTL ? 'عرض' : 'View'}
                  </Button>
                  
                  {canEdit && ['draft', 'draft_correction'].includes(contract.status) && (
                    <Button size="sm" variant="ghost" onClick={() => onEdit(contract)}>
                      <Edit size={14} className="me-1" />
                      {isRTL ? 'تعديل' : 'Edit'}
                    </Button>
                  )}
                  
                  {canExecute && contract.status === 'pending_stas' && (
                    <Button size="sm" variant="default" className="bg-success" onClick={() => onExecute(contract)}>
                      <Play size={14} className="me-1" />
                      {isRTL ? 'تنفيذ' : 'Execute'}
                    </Button>
                  )}
                  
                  {canTerminate && contract.status === 'active' && (
                    <Button size="sm" variant="destructive" onClick={() => onTerminate(contract)}>
                      <XCircle size={14} className="me-1" />
                      {isRTL ? 'إنهاء' : 'Terminate'}
                    </Button>
                  )}
                  
                  {canDelete && ['draft', 'draft_correction'].includes(contract.status) && (
                    <Button size="sm" variant="ghost" className="text-destructive" onClick={() => onDelete(contract)}>
                      <Trash2 size={14} />
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
