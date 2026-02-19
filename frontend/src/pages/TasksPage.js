import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  ClipboardList, Plus, CheckCircle, Clock, Star, User, Calendar,
  AlertTriangle, ChevronRight, X, Send, Award, Target, TrendingUp
} from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function TasksPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showTaskDetail, setShowTaskDetail] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  const isManager = ['sultan', 'naif', 'mohammed', 'stas'].includes(user?.role);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (isManager) {
        const [tasksRes, empRes] = await Promise.all([
          api.get('/api/tasks/all'),
          api.get('/api/employees')
        ]);
        setTasks(tasksRes.data);
        setEmployees(empRes.data);
      } else {
        const res = await api.get('/api/tasks/my-tasks');
        setTasks(res.data);
      }
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل تحميل المهام' : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
  };

  const getStatusBadge = (task) => {
    const statusMap = {
      active: { label: lang === 'ar' ? 'قيد العمل' : 'Active', color: 'bg-blue-100 text-blue-700' },
      pending_review: { label: lang === 'ar' ? 'بانتظار التقييم' : 'Pending Review', color: 'bg-orange-100 text-orange-700' },
      completed: { label: lang === 'ar' ? 'تم الإنجاز' : 'Completed', color: 'bg-green-100 text-green-700' },
      closed: { label: lang === 'ar' ? 'مغلقة' : 'Closed', color: 'bg-slate-100 text-slate-700' }
    };
    const s = statusMap[task.status] || statusMap.active;
    return <span className={`px-3 py-1 rounded-full text-xs font-bold ${s.color}`}>{s.label}</span>;
  };

  const filteredTasks = tasks.filter(t => {
    if (activeTab === 'all') return true;
    if (activeTab === 'active') return t.status === 'active' || t.status === 'pending_review';
    if (activeTab === 'completed') return t.status === 'completed' || t.status === 'closed';
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-6 pb-24" data-testid="tasks-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <ClipboardList size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              {lang === 'ar' ? 'المهام' : 'Tasks'}
            </h1>
            <p className="text-sm text-slate-500">
              {isManager 
                ? (lang === 'ar' ? 'إدارة مهام الموظفين' : 'Manage employee tasks')
                : (lang === 'ar' ? 'مهامي المكلّف بها' : 'My assigned tasks')
              }
            </p>
          </div>
        </div>
        
        {isManager && (
          <Button 
            onClick={() => setShowCreateDialog(true)}
            className="bg-violet-600 hover:bg-violet-700 gap-2"
          >
            <Plus size={18} />
            {lang === 'ar' ? 'مهمة جديدة' : 'New Task'}
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-blue-700">{tasks.length}</p>
            <p className="text-sm text-blue-600">{lang === 'ar' ? 'إجمالي المهام' : 'Total Tasks'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-orange-700">
              {tasks.filter(t => t.status === 'active' || t.status === 'pending_review').length}
            </p>
            <p className="text-sm text-orange-600">{lang === 'ar' ? 'قيد العمل' : 'In Progress'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-green-700">
              {tasks.filter(t => t.status === 'closed').length}
            </p>
            <p className="text-sm text-green-600">{lang === 'ar' ? 'مكتملة' : 'Completed'}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-purple-700">
              {tasks.filter(t => t.status === 'pending_review').length}
            </p>
            <p className="text-sm text-purple-600">{lang === 'ar' ? 'بانتظار التقييم' : 'Pending Review'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mb-4">
        <TabsList>
          <TabsTrigger value="all">{lang === 'ar' ? 'الكل' : 'All'}</TabsTrigger>
          <TabsTrigger value="active">{lang === 'ar' ? 'قيد العمل' : 'Active'}</TabsTrigger>
          <TabsTrigger value="completed">{lang === 'ar' ? 'مكتملة' : 'Completed'}</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Tasks List */}
      <div className="space-y-4">
        {loading ? (
          <Card><CardContent className="py-12 text-center text-slate-500">جاري التحميل...</CardContent></Card>
        ) : filteredTasks.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <ClipboardList size={48} className="mx-auto text-slate-300 mb-4" />
              <p className="text-slate-500">{lang === 'ar' ? 'لا توجد مهام' : 'No tasks'}</p>
            </CardContent>
          </Card>
        ) : (
          filteredTasks.map(task => (
            <TaskCard 
              key={task.id} 
              task={task} 
              lang={lang} 
              isManager={isManager}
              onSelect={() => { setSelectedTask(task); setShowTaskDetail(true); }}
              getStatusBadge={getStatusBadge}
              formatDate={formatDate}
            />
          ))
        )}
      </div>

      {/* Create Task Dialog */}
      {isManager && (
        <CreateTaskDialog 
          open={showCreateDialog}
          onClose={() => setShowCreateDialog(false)}
          employees={employees}
          lang={lang}
          onSuccess={() => { setShowCreateDialog(false); fetchData(); }}
        />
      )}

      {/* Task Detail Dialog */}
      {selectedTask && (
        <TaskDetailDialog
          open={showTaskDetail}
          onClose={() => { setShowTaskDetail(false); setSelectedTask(null); }}
          task={selectedTask}
          lang={lang}
          isManager={isManager}
          onUpdate={fetchData}
        />
      )}
    </div>
  );
}

// ==================== Task Card Component ====================
function TaskCard({ task, lang, isManager, onSelect, getStatusBadge, formatDate }) {
  const progress = task.progress || 0;
  
  return (
    <Card 
      className="cursor-pointer hover:shadow-lg transition-all border-2 hover:border-violet-300"
      onClick={onSelect}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="font-bold text-lg text-slate-800">{lang === 'ar' ? task.title : task.title_en}</h3>
            {isManager && (
              <p className="text-sm text-slate-500 flex items-center gap-1 mt-1">
                <User size={14} />
                {task.employee_name}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            {getStatusBadge(task)}
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Calendar size={12} />
              {formatDate(task.due_date)}
            </span>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-slate-600">{lang === 'ar' ? 'نسبة الإنجاز' : 'Progress'}</span>
            <span className="font-bold text-violet-600">{progress}%</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-3">
            <div 
              className={`h-3 rounded-full transition-all ${
                progress === 100 ? 'bg-green-500' : 'bg-violet-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Stages Indicators */}
        <div className="flex items-center gap-2">
          {[1, 2, 3, 4].map(stage => {
            const s = task.stages?.[stage - 1] || {};
            return (
              <div 
                key={stage}
                className={`flex-1 h-2 rounded-full ${
                  s.evaluated ? 'bg-green-500' :
                  s.completed ? 'bg-orange-400' :
                  'bg-slate-200'
                }`}
                title={`${lang === 'ar' ? 'المرحلة' : 'Stage'} ${stage}`}
              />
            );
          })}
        </div>

        {/* Weight Badge */}
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
            <Target size={12} className="inline ml-1" />
            {lang === 'ar' ? `الوزن: ${task.weight}%` : `Weight: ${task.weight}%`}
          </span>
          {task.final_score && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full flex items-center gap-1">
              <Star size={12} />
              {task.final_score.final_score}/5
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ==================== Create Task Dialog ====================
function CreateTaskDialog({ open, onClose, employees, lang, onSuccess }) {
  const [form, setForm] = useState({
    title: '', title_en: '', description: '', description_en: '',
    employee_id: '', due_date: '', weight: 10
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title || !form.description || !form.employee_id || !form.due_date) {
      toast.error(lang === 'ar' ? 'يرجى ملء جميع الحقول المطلوبة' : 'Please fill all required fields');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/api/tasks/create', form);
      toast.success(lang === 'ar' ? 'تم إنشاء المهمة بنجاح' : 'Task created successfully');
      setForm({ title: '', title_en: '', description: '', description_en: '', employee_id: '', due_date: '', weight: 10 });
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
            <Plus size={20} className="text-violet-600" />
            {lang === 'ar' ? 'إنشاء مهمة جديدة' : 'Create New Task'}
          </DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>{lang === 'ar' ? 'العنوان (عربي) *' : 'Title (Arabic) *'}</Label>
              <Input
                value={form.title}
                onChange={(e) => setForm({...form, title: e.target.value})}
                placeholder="عنوان المهمة"
                required
              />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'العنوان (إنجليزي)' : 'Title (English)'}</Label>
              <Input
                value={form.title_en}
                onChange={(e) => setForm({...form, title_en: e.target.value})}
                placeholder="Task title"
              />
            </div>
          </div>

          <div>
            <Label>{lang === 'ar' ? 'الوصف (عربي) *' : 'Description (Arabic) *'}</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({...form, description: e.target.value})}
              placeholder="وصف تفصيلي للمهمة..."
              rows={3}
              required
            />
          </div>

          <div>
            <Label>{lang === 'ar' ? 'الوصف (إنجليزي)' : 'Description (English)'}</Label>
            <Textarea
              value={form.description_en}
              onChange={(e) => setForm({...form, description_en: e.target.value})}
              placeholder="Detailed task description..."
              rows={2}
            />
          </div>

          <div>
            <Label>{lang === 'ar' ? 'الموظف المكلّف *' : 'Assigned Employee *'}</Label>
            <select
              value={form.employee_id}
              onChange={(e) => setForm({...form, employee_id: e.target.value})}
              className="w-full p-2 border rounded-lg"
              required
            >
              <option value="">{lang === 'ar' ? '-- اختر موظف --' : '-- Select Employee --'}</option>
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>{emp.full_name_ar}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>{lang === 'ar' ? 'تاريخ التسليم *' : 'Due Date *'}</Label>
              <Input
                type="date"
                value={form.due_date}
                onChange={(e) => setForm({...form, due_date: e.target.value})}
                required
              />
            </div>
            <div>
              <Label>{lang === 'ar' ? 'الوزن التقييمي (%)' : 'Evaluation Weight (%)'}</Label>
              <Input
                type="number"
                min={1}
                max={100}
                value={form.weight}
                onChange={(e) => setForm({...form, weight: parseInt(e.target.value) || 10})}
              />
              <p className="text-xs text-slate-500 mt-1">
                {lang === 'ar' ? 'نسبة من التقييم السنوي' : 'Percentage of annual evaluation'}
              </p>
            </div>
          </div>

          <div className="flex gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              {lang === 'ar' ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button type="submit" disabled={submitting} className="flex-1 bg-violet-600 hover:bg-violet-700">
              {submitting ? '...' : (lang === 'ar' ? 'إنشاء المهمة' : 'Create Task')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ==================== Task Detail Dialog ====================
function TaskDetailDialog({ open, onClose, task, lang, isManager, onUpdate }) {
  const [evaluating, setEvaluating] = useState(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return `${d.getFullYear()}/${(d.getMonth()+1).toString().padStart(2,'0')}/${d.getDate().toString().padStart(2,'0')}`;
  };

  const handleCompleteStage = async (stage) => {
    setSubmitting(true);
    try {
      await api.post(`/api/tasks/${task.id}/complete-stage`, { stage });
      toast.success(lang === 'ar' ? 'تم إنهاء المرحلة' : 'Stage completed');
      onUpdate();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEvaluateStage = async () => {
    if (rating === 0) {
      toast.error(lang === 'ar' ? 'يرجى اختيار التقييم' : 'Please select a rating');
      return;
    }
    setSubmitting(true);
    try {
      await api.post(`/api/tasks/${task.id}/evaluate-stage`, {
        stage: evaluating,
        rating,
        comment
      });
      toast.success(lang === 'ar' ? 'تم التقييم بنجاح' : 'Evaluation saved');
      setEvaluating(null);
      setRating(0);
      setComment('');
      onUpdate();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseTask = async () => {
    setSubmitting(true);
    try {
      const res = await api.post(`/api/tasks/${task.id}/close`, {});
      toast.success(
        <div>
          <p className="font-bold">{lang === 'ar' ? 'تم إغلاق المهمة!' : 'Task Closed!'}</p>
          <p>{lang === 'ar' ? `الدرجة النهائية: ${res.data.final_score?.final_score}/5` : `Final Score: ${res.data.final_score?.final_score}/5`}</p>
          <p className="text-xs mt-1">{res.data.weight_info?.message_ar}</p>
        </div>
      );
      onUpdate();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error');
    } finally {
      setSubmitting(false);
    }
  };

  const nextStageToComplete = task.stages?.findIndex(s => !s.completed) + 1 || 0;
  const nextStageToEvaluate = task.stages?.findIndex(s => s.completed && !s.evaluated) + 1 || 0;

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardList size={20} className="text-violet-600" />
            {lang === 'ar' ? task.title : task.title_en}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Task Info */}
          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-slate-700">{lang === 'ar' ? task.description : task.description_en}</p>
            <div className="flex flex-wrap gap-4 mt-4 text-sm">
              <span className="flex items-center gap-1 text-slate-600">
                <User size={14} />
                {task.employee_name}
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <Calendar size={14} />
                {formatDate(task.due_date)}
              </span>
              <span className="flex items-center gap-1 text-purple-600 font-medium">
                <Target size={14} />
                {lang === 'ar' ? `الوزن: ${task.weight}%` : `Weight: ${task.weight}%`}
              </span>
            </div>
          </div>

          {/* Progress */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">{lang === 'ar' ? 'نسبة الإنجاز' : 'Progress'}</span>
              <span className="text-xl font-bold text-violet-600">{task.progress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-4">
              <div 
                className="h-4 rounded-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all"
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>

          {/* Stages */}
          <div className="space-y-3">
            <h4 className="font-bold text-slate-800">{lang === 'ar' ? 'المراحل' : 'Stages'}</h4>
            {[1, 2, 3, 4].map(stage => {
              const s = task.stages?.[stage - 1] || {};
              const canComplete = !isManager && !s.completed && stage === nextStageToComplete && task.status !== 'closed';
              const canEvaluate = isManager && s.completed && !s.evaluated;
              
              return (
                <div 
                  key={stage}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    s.evaluated ? 'bg-green-50 border-green-200' :
                    s.completed ? 'bg-orange-50 border-orange-200' :
                    'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                        s.evaluated ? 'bg-green-500 text-white' :
                        s.completed ? 'bg-orange-400 text-white' :
                        'bg-slate-300 text-slate-600'
                      }`}>
                        {s.evaluated ? <CheckCircle size={20} /> : stage}
                      </div>
                      <div>
                        <p className="font-medium">
                          {lang === 'ar' ? `المرحلة ${stage}` : `Stage ${stage}`} (25%)
                        </p>
                        {s.evaluated && (
                          <div className="flex items-center gap-2 mt-1">
                            <div className="flex">
                              {[1,2,3,4,5].map(star => (
                                <Star 
                                  key={star} 
                                  size={16} 
                                  className={star <= s.rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-300'}
                                />
                              ))}
                            </div>
                            {s.comment && (
                              <span className="text-xs text-slate-500">"{s.comment}"</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Actions */}
                    {canComplete && (
                      <Button 
                        size="sm" 
                        onClick={() => handleCompleteStage(stage)}
                        disabled={submitting}
                        className="bg-violet-600 hover:bg-violet-700"
                      >
                        <CheckCircle size={16} className="ml-1" />
                        {lang === 'ar' ? 'تم الإنجاز' : 'Complete'}
                      </Button>
                    )}
                    {canEvaluate && (
                      <Button 
                        size="sm" 
                        onClick={() => { setEvaluating(stage); setRating(0); setComment(''); }}
                        className="bg-orange-500 hover:bg-orange-600"
                      >
                        <Star size={16} className="ml-1" />
                        {lang === 'ar' ? 'تقييم' : 'Evaluate'}
                      </Button>
                    )}
                    {s.completed && !s.evaluated && !isManager && (
                      <span className="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
                        {lang === 'ar' ? 'بانتظار التقييم' : 'Awaiting Review'}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Evaluation Form */}
          {evaluating && (
            <div className="bg-violet-50 border-2 border-violet-200 rounded-lg p-4">
              <h4 className="font-bold text-violet-800 mb-3">
                {lang === 'ar' ? `تقييم المرحلة ${evaluating}` : `Evaluate Stage ${evaluating}`}
              </h4>
              <div className="space-y-3">
                <div>
                  <Label>{lang === 'ar' ? 'التقييم (1-5) *' : 'Rating (1-5) *'}</Label>
                  <div className="flex gap-2 mt-2">
                    {[1, 2, 3, 4, 5].map(r => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setRating(r)}
                        className={`w-12 h-12 rounded-lg border-2 font-bold text-lg transition-all ${
                          rating === r 
                            ? 'bg-yellow-400 border-yellow-500 text-white' 
                            : 'bg-white border-slate-200 hover:border-yellow-300'
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <Label>{lang === 'ar' ? 'تعليق (اختياري)' : 'Comment (optional)'}</Label>
                  <Textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder={lang === 'ar' ? 'تعليق على الأداء...' : 'Performance comment...'}
                    rows={2}
                  />
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setEvaluating(null)} className="flex-1">
                    {lang === 'ar' ? 'إلغاء' : 'Cancel'}
                  </Button>
                  <Button onClick={handleEvaluateStage} disabled={submitting} className="flex-1 bg-violet-600 hover:bg-violet-700">
                    {lang === 'ar' ? 'حفظ التقييم' : 'Save Evaluation'}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Close Task Button */}
          {isManager && task.status === 'completed' && (
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-green-800">
                    {lang === 'ar' ? 'المهمة جاهزة للإغلاق' : 'Task Ready to Close'}
                  </h4>
                  <p className="text-sm text-green-600 mt-1">
                    {lang === 'ar' 
                      ? `هذه المهمة تمثل ${task.weight}% من معيار إنجاز المهام في التقييم السنوي`
                      : `This task represents ${task.weight}% of task completion in annual evaluation`
                    }
                  </p>
                </div>
                <Button onClick={handleCloseTask} disabled={submitting} className="bg-green-600 hover:bg-green-700">
                  <Award size={18} className="ml-2" />
                  {lang === 'ar' ? 'استلام نهائي' : 'Final Acceptance'}
                </Button>
              </div>
            </div>
          )}

          {/* Final Score (if closed) */}
          {task.status === 'closed' && task.final_score && (
            <div className="bg-slate-800 text-white rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold">{lang === 'ar' ? 'الدرجة النهائية' : 'Final Score'}</h4>
                  {task.delay_info?.delayed && (
                    <p className="text-sm text-orange-300 mt-1">
                      {lang === 'ar' 
                        ? `تأخير ${task.delay_info.days} يوم (-${task.delay_info.penalty}%)`
                        : `Delayed ${task.delay_info.days} days (-${task.delay_info.penalty}%)`
                      }
                    </p>
                  )}
                </div>
                <div className="text-center">
                  <p className="text-4xl font-bold">{task.final_score.final_score}</p>
                  <p className="text-sm text-slate-300">{lang === 'ar' ? 'من 5' : 'out of 5'}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
