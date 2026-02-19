import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  Wrench, Plus, Search, AlertTriangle, CheckCircle, Clock, 
  Package, Car, Monitor, Settings, Trash2, Edit, X, Filter
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

const ASSET_TYPES = [
  { value: 'device', label_ar: 'جهاز', label_en: 'Device', icon: Monitor },
  { value: 'vehicle', label_ar: 'سيارة', label_en: 'Vehicle', icon: Car },
  { value: 'equipment', label_ar: 'معدة', label_en: 'Equipment', icon: Settings },
  { value: 'other', label_ar: 'أخرى', label_en: 'Other', icon: Package },
];

const STATUSES = [
  { value: 'new', label_ar: 'جديد', label_en: 'New', color: 'bg-blue-100 text-blue-700', icon: '🆕' },
  { value: 'in_progress', label_ar: 'تحت الصيانة', label_en: 'In Progress', color: 'bg-orange-100 text-orange-700', icon: '🔧' },
  { value: 'ready', label_ar: 'جاهز للاستلام', label_en: 'Ready', color: 'bg-green-100 text-green-700', icon: '✅' },
  { value: 'closed', label_ar: 'مغلق', label_en: 'Closed', color: 'bg-slate-100 text-slate-600', icon: '📦' },
];

export default function MaintenanceTrackingPage() {
  const { lang } = useLanguage();
  const [cards, setCards] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [editCard, setEditCard] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cardsRes, statsRes] = await Promise.all([
        api.get('/api/maintenance-tracking/all'),
        api.get('/api/maintenance-tracking/stats/summary')
      ]);
      setCards(cardsRes.data);
      setStats(statsRes.data);
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل تحميل البيانات' : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
  };

  const getStatusInfo = (status) => STATUSES.find(s => s.value === status) || STATUSES[0];
  const getAssetType = (type) => ASSET_TYPES.find(t => t.value === type) || ASSET_TYPES[3];

  const filteredCards = cards.filter(card => {
    const matchSearch = !search || 
      card.title?.toLowerCase().includes(search.toLowerCase()) ||
      card.department?.toLowerCase().includes(search.toLowerCase()) ||
      card.description?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filterStatus === 'all' || card.status === filterStatus;
    return matchSearch && matchStatus;
  });

  const handleDelete = async (cardId) => {
    if (!confirm(lang === 'ar' ? 'هل أنت متأكد من حذف هذه البطاقة؟' : 'Delete this card?')) return;
    try {
      await api.delete(`/api/maintenance-tracking/${cardId}`);
      toast.success(lang === 'ar' ? 'تم الحذف' : 'Deleted');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  const handleStatusChange = async (cardId, newStatus) => {
    try {
      await api.patch(`/api/maintenance-tracking/${cardId}/status?status=${newStatus}`);
      toast.success(lang === 'ar' ? 'تم تغيير الحالة' : 'Status updated');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6 pb-24" data-testid="maintenance-tracking-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
            <Wrench size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? 'متابعة الصيانة' : 'Maintenance Tracking'}
            </h1>
            <p className="text-sm text-slate-500">
              {lang === 'ar' ? 'بطاقات متابعة الأصول بالصيانة' : 'Track assets in maintenance'}
            </p>
          </div>
        </div>
        
        <Button onClick={() => setShowCreate(true)} className="bg-amber-600 hover:bg-amber-700 gap-2">
          <Plus size={18} />
          {lang === 'ar' ? 'بطاقة جديدة' : 'New Card'}
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
        <Card className="bg-slate-100">
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-slate-700">{stats.total || 0}</p>
            <p className="text-xs text-slate-500">{lang === 'ar' ? 'الكل' : 'Total'}</p>
          </CardContent>
        </Card>
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-blue-700">{stats.new || 0}</p>
            <p className="text-xs text-blue-600">{lang === 'ar' ? 'جديد' : 'New'}</p>
          </CardContent>
        </Card>
        <Card className="bg-orange-50 border-orange-200">
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-orange-700">{stats.in_progress || 0}</p>
            <p className="text-xs text-orange-600">{lang === 'ar' ? 'تحت الصيانة' : 'In Progress'}</p>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-green-700">{stats.ready || 0}</p>
            <p className="text-xs text-green-600">{lang === 'ar' ? 'جاهز' : 'Ready'}</p>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-red-700">{stats.delayed || 0}</p>
            <p className="text-xs text-red-600">{lang === 'ar' ? 'متأخر' : 'Delayed'}</p>
          </CardContent>
        </Card>
        <Card className="bg-purple-50 border-purple-200">
          <CardContent className="p-3 text-center">
            <p className="text-2xl font-bold text-purple-700">{(stats.total_cost || 0).toLocaleString()}</p>
            <p className="text-xs text-purple-600">{lang === 'ar' ? 'التكلفة' : 'Cost'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={lang === 'ar' ? 'بحث...' : 'Search...'}
                  className="pr-10"
                />
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant={filterStatus === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('all')}
              >
                {lang === 'ar' ? 'الكل' : 'All'}
              </Button>
              {STATUSES.filter(s => s.value !== 'closed').map(s => (
                <Button
                  key={s.value}
                  variant={filterStatus === s.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterStatus(s.value)}
                >
                  {s.icon} {lang === 'ar' ? s.label_ar : s.label_en}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cards Table */}
      <Card>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="py-12 text-center text-slate-500">جاري التحميل...</div>
          ) : filteredCards.length === 0 ? (
            <div className="py-12 text-center">
              <Wrench size={48} className="mx-auto text-slate-300 mb-4" />
              <p className="text-slate-500">{lang === 'ar' ? 'لا توجد بطاقات' : 'No cards'}</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-100 border-b">
                  <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'العنوان' : 'Title'}</th>
                  <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'النوع' : 'Type'}</th>
                  <th className="p-3 text-right font-semibold">{lang === 'ar' ? 'القسم' : 'Dept'}</th>
                  <th className="p-3 text-center font-semibold">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                  <th className="p-3 text-center font-semibold">{lang === 'ar' ? 'التاريخ المتوقع' : 'Expected'}</th>
                  <th className="p-3 text-center font-semibold">{lang === 'ar' ? 'متأخر؟' : 'Delayed?'}</th>
                  <th className="p-3 text-center font-semibold">{lang === 'ar' ? 'إجراءات' : 'Actions'}</th>
                </tr>
              </thead>
              <tbody>
                {filteredCards.map((card, idx) => {
                  const statusInfo = getStatusInfo(card.status);
                  const assetType = getAssetType(card.asset_type);
                  const AssetIcon = assetType.icon;
                  const isDelayed = card.delay_info?.is_delayed;
                  const alert = card.delay_info?.alert;
                  
                  return (
                    <tr key={card.id} className={`border-b hover:bg-slate-50 ${isDelayed ? 'bg-red-50' : ''}`}>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <AssetIcon size={18} className="text-slate-500" />
                          <div>
                            <p className="font-medium">{card.title}</p>
                            {card.description && (
                              <p className="text-xs text-slate-500 truncate max-w-[200px]">{card.description}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="p-3 text-slate-600">
                        {lang === 'ar' ? assetType.label_ar : assetType.label_en}
                      </td>
                      <td className="p-3 text-slate-600">{card.department || '-'}</td>
                      <td className="p-3 text-center">
                        <select
                          value={card.status}
                          onChange={(e) => handleStatusChange(card.id, e.target.value)}
                          className={`px-2 py-1 rounded-full text-xs font-bold border-0 cursor-pointer ${statusInfo.color}`}
                        >
                          {STATUSES.map(s => (
                            <option key={s.value} value={s.value}>
                              {s.icon} {lang === 'ar' ? s.label_ar : s.label_en}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="p-3 text-center text-slate-600">
                        {formatDate(card.expected_date)}
                      </td>
                      <td className="p-3 text-center">
                        {!card.delay_info?.has_expected ? (
                          <span className="text-slate-400">-</span>
                        ) : isDelayed ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-bold">
                            <AlertTriangle size={12} />
                            {lang === 'ar' ? 'نعم' : 'Yes'} ({Math.abs(card.delay_info.days_remaining)} {lang === 'ar' ? 'يوم' : 'd'})
                          </span>
                        ) : alert ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-bold">
                            <Clock size={12} />
                            {alert}
                          </span>
                        ) : (
                          <span className="text-green-600 text-xs">
                            <CheckCircle size={14} className="inline" /> {card.delay_info.days_remaining} {lang === 'ar' ? 'يوم' : 'd'}
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-center">
                        <div className="flex justify-center gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setEditCard(card)}>
                            <Edit size={14} className="text-blue-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleDelete(card.id)}>
                            <Trash2 size={14} className="text-red-600" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {/* Create/Edit Dialog */}
      <MaintenanceCardDialog
        open={showCreate || !!editCard}
        onClose={() => { setShowCreate(false); setEditCard(null); }}
        card={editCard}
        lang={lang}
        onSuccess={() => { setShowCreate(false); setEditCard(null); fetchData(); }}
      />
    </div>
  );
}

// ==================== Dialog Component ====================
function MaintenanceCardDialog({ open, onClose, card, lang, onSuccess }) {
  const [form, setForm] = useState({
    title: '', asset_type: '', department: '', description: '',
    sent_date: '', expected_date: '', invoice_number: '', cost: '', notes: ''
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (card) {
      setForm({
        title: card.title || '',
        asset_type: card.asset_type || '',
        department: card.department || '',
        description: card.description || '',
        sent_date: card.sent_date?.split('T')[0] || '',
        expected_date: card.expected_date?.split('T')[0] || '',
        invoice_number: card.invoice_number || '',
        cost: card.cost || '',
        notes: card.notes || ''
      });
    } else {
      setForm({
        title: '', asset_type: '', department: '', description: '',
        sent_date: '', expected_date: '', invoice_number: '', cost: '', notes: ''
      });
    }
  }, [card, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) {
      toast.error(lang === 'ar' ? 'العنوان مطلوب' : 'Title is required');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        cost: form.cost ? parseFloat(form.cost) : null,
        sent_date: form.sent_date || null,
        expected_date: form.expected_date || null
      };
      
      if (card) {
        await api.put(`/api/maintenance-tracking/${card.id}`, payload);
        toast.success(lang === 'ar' ? 'تم التحديث' : 'Updated');
      } else {
        await api.post('/api/maintenance-tracking/create', payload);
        toast.success(lang === 'ar' ? 'تم إنشاء البطاقة' : 'Card created');
      }
      onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wrench size={20} className="text-amber-600" />
            {card 
              ? (lang === 'ar' ? 'تعديل البطاقة' : 'Edit Card')
              : (lang === 'ar' ? 'بطاقة صيانة جديدة' : 'New Maintenance Card')
            }
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>{lang === 'ar' ? 'العنوان *' : 'Title *'}</Label>
            <Input
              value={form.title}
              onChange={(e) => setForm({...form, title: e.target.value})}
              placeholder={lang === 'ar' ? 'مثال: لابتوب قسم التصميم' : 'e.g., Design Dept Laptop'}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>{lang === 'ar' ? 'نوع الأصل' : 'Asset Type'}</Label>
              <select
                value={form.asset_type}
                onChange={(e) => setForm({...form, asset_type: e.target.value})}
                className="w-full p-2 border rounded-lg"
              >
                <option value="">{lang === 'ar' ? '-- اختر --' : '-- Select --'}</option>
                {ASSET_TYPES.map(t => (
                  <option key={t.value} value={t.value}>
                    {lang === 'ar' ? t.label_ar : t.label_en}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>{lang === 'ar' ? 'القسم / الجهة' : 'Department'}</Label>
              <Input
                value={form.department}
                onChange={(e) => setForm({...form, department: e.target.value})}
                placeholder={lang === 'ar' ? 'مثال: التصميم' : 'e.g., Design'}
              />
            </div>
          </div>

          <div>
            <Label>{lang === 'ar' ? 'الوصف' : 'Description'}</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({...form, description: e.target.value})}
              placeholder={lang === 'ar' ? 'وصف مختصر للمشكلة أو الصيانة...' : 'Brief description...'}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>{lang === 'ar' ? 'تاريخ الإرسال' : 'Sent Date'}</Label>
              <Input
                type="date"
                value={form.sent_date}
                onChange={(e) => setForm({...form, sent_date: e.target.value})}
              />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'التاريخ المتوقع للانتهاء' : 'Expected Date'}</Label>
              <Input
                type="date"
                value={form.expected_date}
                onChange={(e) => setForm({...form, expected_date: e.target.value})}
              />
              <p className="text-xs text-slate-500 mt-1">
                {lang === 'ar' ? 'للتنبيه قبل الموعد' : 'For alerts before due date'}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>{lang === 'ar' ? 'رقم الفاتورة' : 'Invoice #'}</Label>
              <Input
                value={form.invoice_number}
                onChange={(e) => setForm({...form, invoice_number: e.target.value})}
                placeholder="INV-001"
              />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'التكلفة' : 'Cost'}</Label>
              <Input
                type="number"
                value={form.cost}
                onChange={(e) => setForm({...form, cost: e.target.value})}
                placeholder="0"
              />
            </div>
          </div>

          <div>
            <Label>{lang === 'ar' ? 'ملاحظات' : 'Notes'}</Label>
            <Textarea
              value={form.notes}
              onChange={(e) => setForm({...form, notes: e.target.value})}
              placeholder={lang === 'ar' ? 'أي ملاحظات إضافية...' : 'Any additional notes...'}
              rows={2}
            />
          </div>

          <div className="flex gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button type="submit" disabled={submitting} className="flex-1 bg-amber-600 hover:bg-amber-700">
              {submitting ? '...' : (card ? (lang === 'ar' ? 'تحديث' : 'Update') : (lang === 'ar' ? 'إنشاء' : 'Create'))}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
