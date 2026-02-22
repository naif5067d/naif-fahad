/**
 * Policies Module - Smart Governance Booklet Engine
 * نظام السياسات والحوكمة - دفتر الحوكمة الذكي
 * 
 * تصميم رسمي واضح ومقروء
 */
import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { 
  Book, FileText, Plus, Edit2, Trash2, Save, 
  Eye, EyeOff, GripVertical, Check, X, 
  Lock, Globe, Shield, ChevronLeft, ChevronRight, Settings,
  AlertTriangle, BookOpen
} from 'lucide-react';
import SmartEditor from '@/components/SmartEditor';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function PoliciesPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const isRTL = lang === 'ar';
  
  // Check if user is admin
  const isAdmin = ['stas', 'sultan', 'naif'].includes(user?.role) || 
                  ['stas', 'sultan', 'naif'].includes(user?.username);
  const isStas = user?.role === 'stas' || user?.username === 'stas';

  // State
  const [activeSystem, setActiveSystem] = useState('private');
  const [chapters, setChapters] = useState([]);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [legalFooter, setLegalFooter] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Dialogs
  const [createDialog, setCreateDialog] = useState(false);
  const [editLegalDialog, setEditLegalDialog] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  
  // Edit state
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ title: '', title_ar: '', content: '' });
  const [newChapterForm, setNewChapterForm] = useState({ title: '', title_ar: '' });
  const [legalForm, setLegalForm] = useState({ text_ar: '', text_en: '' });

  // Fetch data
  const fetchChapters = useCallback(async () => {
    try {
      const res = await api.get(`/api/policies/chapters/${activeSystem}`);
      setChapters(res.data);
      
      if (res.data.length > 0 && !selectedChapter) {
        setSelectedChapter(res.data[0]);
      } else if (selectedChapter) {
        const updated = res.data.find(c => c.id === selectedChapter.id);
        if (updated) setSelectedChapter(updated);
        else if (res.data.length > 0) setSelectedChapter(res.data[0]);
        else setSelectedChapter(null);
      }
    } catch (err) {
      console.error('Failed to fetch chapters:', err);
    }
  }, [activeSystem]);

  const fetchLegalFooter = useCallback(async () => {
    try {
      const res = await api.get('/api/policies/legal-footer');
      setLegalFooter(res.data);
      setLegalForm({ text_ar: res.data.text_ar, text_en: res.data.text_en });
    } catch (err) {
      console.error('Failed to fetch legal footer:', err);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    setSelectedChapter(null);
    Promise.all([fetchChapters(), fetchLegalFooter()]).finally(() => setLoading(false));
  }, [activeSystem]);

  // Handlers
  const handleCreateChapter = async () => {
    if (!newChapterForm.title_ar.trim()) {
      toast.error(isRTL ? 'الرجاء إدخال عنوان الفصل' : 'Please enter chapter title');
      return;
    }
    
    try {
      const res = await api.post('/api/policies/chapters', {
        system_id: activeSystem,
        title: newChapterForm.title || newChapterForm.title_ar,
        title_ar: newChapterForm.title_ar,
        content: ''
      });
      
      toast.success(isRTL ? 'تم إنشاء الفصل' : 'Chapter created');
      setCreateDialog(false);
      setNewChapterForm({ title: '', title_ar: '' });
      await fetchChapters();
      setSelectedChapter(res.data);
      setIsEditing(true);
      setEditForm({ 
        title: res.data.title, 
        title_ar: res.data.title_ar, 
        content: res.data.content 
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create chapter');
    }
  };

  const handleSaveChapter = async () => {
    if (!selectedChapter) return;
    
    try {
      const res = await api.put(`/api/policies/chapter/${selectedChapter.id}`, {
        title: editForm.title,
        title_ar: editForm.title_ar,
        content: editForm.content
      });
      
      toast.success(isRTL ? 'تم حفظ التغييرات' : 'Changes saved');
      setIsEditing(false);
      
      if (res.data.action === 'new_draft_created') {
        await fetchChapters();
        setSelectedChapter(res.data.chapter);
      } else {
        await fetchChapters();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
    }
  };

  const handlePublish = async () => {
    if (!selectedChapter) return;
    
    try {
      await api.post(`/api/policies/chapter/${selectedChapter.id}/publish`);
      toast.success(isRTL ? 'تم نشر الفصل' : 'Chapter published');
      await fetchChapters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to publish');
    }
  };

  const handleUnpublish = async () => {
    if (!selectedChapter) return;
    
    try {
      await api.post(`/api/policies/chapter/${selectedChapter.id}/unpublish`);
      toast.success(isRTL ? 'تم إلغاء نشر الفصل' : 'Chapter unpublished');
      await fetchChapters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unpublish');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    
    try {
      await api.delete(`/api/policies/chapter/${deleteConfirm.id}`);
      toast.success(isRTL ? 'تم حذف الفصل' : 'Chapter deleted');
      setDeleteConfirm(null);
      setSelectedChapter(null);
      await fetchChapters();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleSaveLegalFooter = async () => {
    try {
      await api.put('/api/policies/legal-footer', legalForm);
      toast.success(isRTL ? 'تم حفظ التذييل القانوني' : 'Legal footer saved');
      setEditLegalDialog(false);
      await fetchLegalFooter();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
    }
  };

  const startEditing = () => {
    if (selectedChapter) {
      setEditForm({
        title: selectedChapter.title,
        title_ar: selectedChapter.title_ar,
        content: selectedChapter.content
      });
      setIsEditing(true);
    }
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setEditForm({ title: '', title_ar: '', content: '' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900" data-testid="policies-page">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-600/20">
                <BookOpen size={28} className="text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                  {isRTL ? 'دفتر السياسات والحوكمة' : 'Policies & Governance'}
                </h1>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                  {isRTL ? 'الإطار التنظيمي الرسمي للشركة' : 'Official Regulatory Framework'}
                </p>
              </div>
            </div>
            
            {isStas && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditLegalDialog(true)}
              >
                <Settings size={16} className="me-2" />
                {isRTL ? 'التذييل القانوني' : 'Legal Footer'}
              </Button>
            )}
          </div>

          {/* System Tabs */}
          <div className="mt-6">
            <div className="inline-flex p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
              <button
                onClick={() => setActiveSystem('public')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeSystem === 'public'
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
                data-testid="public-system-tab"
              >
                <Globe size={18} />
                {isRTL ? 'النظام العام' : 'Public System'}
              </button>
              <button
                onClick={() => setActiveSystem('private')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  activeSystem === 'private'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
                data-testid="private-system-tab"
              >
                <Shield size={18} />
                {isRTL ? 'النظام الخاص' : 'Private System'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6">
        <div className="flex gap-6 flex-col lg:flex-row">
          
          {/* Sidebar - Chapter List */}
          <div className="w-full lg:w-72 flex-shrink-0">
            <div className="bg-white dark:bg-slate-900 rounded-xl border shadow-sm overflow-hidden">
              <div className="p-4 border-b bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-white">
                    {isRTL ? 'الفصول' : 'Chapters'}
                  </h3>
                  {isAdmin && (
                    <Button 
                      size="sm" 
                      onClick={() => setCreateDialog(true)}
                      data-testid="create-chapter-btn"
                    >
                      <Plus size={16} className="me-1" />
                      {isRTL ? 'جديد' : 'New'}
                    </Button>
                  )}
                </div>
              </div>
              
              <div className="p-2 max-h-[500px] overflow-y-auto">
                {loading ? (
                  <div className="py-8 text-center text-slate-500">
                    <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                    {isRTL ? 'جاري التحميل...' : 'Loading...'}
                  </div>
                ) : chapters.length === 0 ? (
                  <div className="py-8 text-center">
                    <FileText size={40} className="mx-auto mb-2 text-slate-300 dark:text-slate-600" />
                    <p className="text-slate-500">{isRTL ? 'لا توجد فصول' : 'No chapters yet'}</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {chapters.map((chapter, index) => (
                      <button
                        key={chapter.id}
                        onClick={() => {
                          setSelectedChapter(chapter);
                          setIsEditing(false);
                        }}
                        className={`w-full flex items-center gap-3 p-3 rounded-lg text-start transition-all ${
                          selectedChapter?.id === chapter.id
                            ? 'bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-500'
                            : 'hover:bg-slate-50 dark:hover:bg-slate-800 border-2 border-transparent'
                        }`}
                        data-testid={`chapter-item-${chapter.id}`}
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                          selectedChapter?.id === chapter.id
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}>
                          {index + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`font-medium truncate text-sm ${
                            selectedChapter?.id === chapter.id
                              ? 'text-blue-700 dark:text-blue-400'
                              : 'text-slate-700 dark:text-slate-300'
                          }`}>
                            {isRTL ? chapter.title_ar : chapter.title}
                          </p>
                          <div className="flex items-center gap-1 mt-0.5">
                            {chapter.status === 'published' ? (
                              <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                                <Eye size={10} />
                                {isRTL ? 'منشور' : 'Published'}
                              </span>
                            ) : (
                              <span className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                                <Edit2 size={10} />
                                {isRTL ? 'مسودة' : 'Draft'}
                              </span>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main Content - Chapter View/Edit */}
          <div className="flex-1">
            {selectedChapter ? (
              <div className="bg-white dark:bg-slate-900 rounded-xl border shadow-sm overflow-hidden">
                {/* Chapter Header */}
                <div className="p-6 border-b bg-slate-50 dark:bg-slate-800/50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      {isEditing ? (
                        <div className="space-y-4">
                          <div>
                            <Label className="text-slate-700 dark:text-slate-300 text-sm font-medium">
                              {isRTL ? 'العنوان بالعربية' : 'Arabic Title'}
                            </Label>
                            <Input
                              value={editForm.title_ar}
                              onChange={e => setEditForm(f => ({ ...f, title_ar: e.target.value }))}
                              className="mt-1.5 text-lg font-semibold"
                              dir="rtl"
                            />
                          </div>
                          <div>
                            <Label className="text-slate-700 dark:text-slate-300 text-sm font-medium">
                              {isRTL ? 'العنوان بالإنجليزية' : 'English Title'}
                            </Label>
                            <Input
                              value={editForm.title}
                              onChange={e => setEditForm(f => ({ ...f, title: e.target.value }))}
                              className="mt-1.5"
                              dir="ltr"
                            />
                          </div>
                        </div>
                      ) : (
                        <>
                          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                            {isRTL ? selectedChapter.title_ar : selectedChapter.title}
                          </h2>
                          <p className="text-slate-500 dark:text-slate-400 mt-1">
                            {isRTL ? selectedChapter.title : selectedChapter.title_ar}
                          </p>
                        </>
                      )}
                      
                      {/* Status Badge */}
                      <div className="flex items-center gap-2 mt-4">
                        {selectedChapter.status === 'published' ? (
                          <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">
                            <Eye size={12} />
                            {isRTL ? 'منشور' : 'Published'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-medium">
                            <Edit2 size={12} />
                            {isRTL ? 'مسودة' : 'Draft'}
                          </span>
                        )}
                        {selectedChapter.version > 1 && (
                          <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full">
                            v{selectedChapter.version}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    {isAdmin && (
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {isEditing ? (
                          <>
                            <Button variant="ghost" size="sm" onClick={cancelEditing}>
                              <X size={16} className="me-1" />
                              {isRTL ? 'إلغاء' : 'Cancel'}
                            </Button>
                            <Button size="sm" onClick={handleSaveChapter} data-testid="save-chapter-btn">
                              <Save size={16} className="me-1" />
                              {isRTL ? 'حفظ' : 'Save'}
                            </Button>
                          </>
                        ) : (
                          <>
                            {selectedChapter.status === 'draft' && (
                              <Button size="sm" variant="outline" onClick={startEditing} data-testid="edit-chapter-btn">
                                <Edit2 size={16} className="me-1" />
                                {isRTL ? 'تحرير' : 'Edit'}
                              </Button>
                            )}
                            
                            {selectedChapter.status === 'draft' ? (
                              <Button size="sm" onClick={handlePublish} className="bg-emerald-600 hover:bg-emerald-700" data-testid="publish-btn">
                                <Eye size={16} className="me-1" />
                                {isRTL ? 'نشر' : 'Publish'}
                              </Button>
                            ) : (
                              <Button size="sm" variant="outline" onClick={handleUnpublish}>
                                <EyeOff size={16} className="me-1" />
                                {isRTL ? 'إلغاء النشر' : 'Unpublish'}
                              </Button>
                            )}
                            
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setDeleteConfirm(selectedChapter)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                            >
                              <Trash2 size={16} />
                            </Button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Chapter Content */}
                <div className="p-6">
                  {isEditing ? (
                    <SmartEditor
                      content={editForm.content}
                      onChange={content => setEditForm(f => ({ ...f, content }))}
                      placeholder={isRTL ? 'ابدأ كتابة محتوى الفصل...' : 'Start writing chapter content...'}
                    />
                  ) : (
                    <div 
                      className="prose prose-slate dark:prose-invert max-w-none min-h-[200px]"
                      dir={isRTL ? 'rtl' : 'ltr'}
                      dangerouslySetInnerHTML={{ 
                        __html: selectedChapter.content || 
                          `<p class="text-slate-400 italic">${isRTL ? 'لا يوجد محتوى بعد. انقر على "تحرير" لإضافة المحتوى.' : 'No content yet. Click "Edit" to add content.'}</p>` 
                      }}
                    />
                  )}
                </div>

                {/* Legal Footer */}
                <div className="mx-6 mb-6 p-5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border-2 border-slate-200 dark:border-slate-700">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                      <Lock size={18} className="text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">
                        {isRTL ? 'إخلاء المسؤولية القانوني' : 'Legal Disclaimer'}
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-line">
                        {legalFooter ? (isRTL ? legalFooter.text_ar : legalFooter.text_en) : ''}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-900 rounded-xl border shadow-sm p-12 text-center">
                <div className="w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-4">
                  <Book size={36} className="text-slate-400" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 dark:text-white">
                  {isRTL ? 'اختر فصلاً للقراءة' : 'Select a Chapter'}
                </h3>
                <p className="mt-2 text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                  {isRTL 
                    ? 'اختر فصلاً من القائمة الجانبية لعرض محتواه'
                    : 'Choose a chapter from the sidebar to view its content'
                  }
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Chapter Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isRTL ? 'إنشاء فصل جديد' : 'Create New Chapter'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>{isRTL ? 'العنوان بالعربية' : 'Arabic Title'}</Label>
              <Input
                value={newChapterForm.title_ar}
                onChange={e => setNewChapterForm(f => ({ ...f, title_ar: e.target.value }))}
                placeholder={isRTL ? 'أدخل عنوان الفصل بالعربية' : 'Enter Arabic title'}
                className="mt-1.5"
                dir="rtl"
                data-testid="new-chapter-title-ar"
              />
            </div>
            <div>
              <Label>{isRTL ? 'العنوان بالإنجليزية (اختياري)' : 'English Title (optional)'}</Label>
              <Input
                value={newChapterForm.title}
                onChange={e => setNewChapterForm(f => ({ ...f, title: e.target.value }))}
                placeholder={isRTL ? 'أدخل عنوان الفصل بالإنجليزية' : 'Enter English title'}
                className="mt-1.5"
                dir="ltr"
                data-testid="new-chapter-title-en"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialog(false)}>
              {isRTL ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button onClick={handleCreateChapter} data-testid="confirm-create-btn">
              <Plus size={16} className="me-1" />
              {isRTL ? 'إنشاء' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600 flex items-center gap-2">
              <AlertTriangle size={20} />
              {isRTL ? 'تأكيد الحذف' : 'Confirm Delete'}
            </DialogTitle>
          </DialogHeader>
          <p className="py-4 text-slate-600 dark:text-slate-400">
            {isRTL 
              ? `هل أنت متأكد من حذف فصل "${deleteConfirm?.title_ar}"؟ لا يمكن التراجع عن هذا الإجراء.`
              : `Are you sure you want to delete "${deleteConfirm?.title}"? This action cannot be undone.`
            }
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              {isRTL ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              <Trash2 size={16} className="me-1" />
              {isRTL ? 'حذف' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Legal Footer Dialog (STAS Only) */}
      <Dialog open={editLegalDialog} onOpenChange={setEditLegalDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lock size={20} className="text-blue-600" />
              {isRTL ? 'تعديل التذييل القانوني' : 'Edit Legal Footer'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>{isRTL ? 'النص العربي' : 'Arabic Text'}</Label>
              <textarea
                value={legalForm.text_ar}
                onChange={e => setLegalForm(f => ({ ...f, text_ar: e.target.value }))}
                className="mt-1.5 w-full h-32 p-3 rounded-lg border bg-background resize-none text-sm"
                dir="rtl"
              />
            </div>
            <div>
              <Label>{isRTL ? 'النص الإنجليزي' : 'English Text'}</Label>
              <textarea
                value={legalForm.text_en}
                onChange={e => setLegalForm(f => ({ ...f, text_en: e.target.value }))}
                className="mt-1.5 w-full h-32 p-3 rounded-lg border bg-background resize-none text-sm"
                dir="ltr"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditLegalDialog(false)}>
              {isRTL ? 'إلغاء' : 'Cancel'}
            </Button>
            <Button onClick={handleSaveLegalFooter}>
              <Save size={16} className="me-1" />
              {isRTL ? 'حفظ' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
