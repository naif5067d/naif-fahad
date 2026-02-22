/**
 * Policies Module - Smart Governance Booklet Engine
 * نظام السياسات والحوكمة - دفتر الحوكمة الذكي
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
  Lock, Globe, Shield, ChevronRight, Settings,
  AlertTriangle
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
      
      // Select first chapter if none selected
      if (res.data.length > 0 && !selectedChapter) {
        setSelectedChapter(res.data[0]);
      } else if (selectedChapter) {
        // Update selected chapter with fresh data
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
      
      // Handle new draft creation
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

  // System styling
  const getSystemStyle = (systemId) => {
    if (systemId === 'private') {
      return {
        bg: 'bg-gradient-to-br from-slate-900 to-slate-800 dark:from-slate-950 dark:to-slate-900',
        border: 'border-amber-600/30',
        accent: 'text-amber-500',
        badge: 'bg-amber-600/20 text-amber-400 border-amber-600/30'
      };
    }
    return {
      bg: 'bg-gradient-to-br from-slate-100 to-white dark:from-slate-900 dark:to-slate-950',
      border: 'border-slate-300 dark:border-slate-700',
      accent: 'text-primary',
      badge: 'bg-primary/10 text-primary border-primary/20'
    };
  };

  const style = getSystemStyle(activeSystem);

  return (
    <div className="min-h-screen" data-testid="policies-page">
      {/* Header */}
      <div className={`${activeSystem === 'private' ? 'bg-slate-900 text-white' : 'bg-background'} py-8 px-6 border-b`}>
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${activeSystem === 'private' ? 'bg-amber-600/20' : 'bg-primary/10'}`}>
                <Book size={28} className={activeSystem === 'private' ? 'text-amber-500' : 'text-primary'} />
              </div>
              <div>
                <h1 className="text-2xl font-bold font-serif">
                  {isRTL ? 'دفتر السياسات والحوكمة' : 'Policies & Governance Booklet'}
                </h1>
                <p className={`text-sm ${activeSystem === 'private' ? 'text-slate-400' : 'text-muted-foreground'}`}>
                  {isRTL ? 'الإطار التنظيمي الرسمي للشركة' : 'Official Regulatory Framework'}
                </p>
              </div>
            </div>
            
            {/* Admin: Edit Legal Footer */}
            {isStas && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setEditLegalDialog(true)}
                className={activeSystem === 'private' ? 'border-slate-600 text-slate-300 hover:bg-slate-800' : ''}
              >
                <Settings size={16} className="me-2" />
                {isRTL ? 'تعديل التذييل القانوني' : 'Edit Legal Footer'}
              </Button>
            )}
          </div>

          {/* System Tabs */}
          <div className="mt-6">
            <Tabs value={activeSystem} onValueChange={setActiveSystem}>
              <TabsList className={`grid grid-cols-2 w-full max-w-md ${activeSystem === 'private' ? 'bg-slate-800' : ''}`}>
                <TabsTrigger 
                  value="public" 
                  className="flex items-center gap-2 data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700"
                  data-testid="public-system-tab"
                >
                  <Globe size={16} />
                  {isRTL ? 'النظام العام' : 'Public System'}
                </TabsTrigger>
                <TabsTrigger 
                  value="private" 
                  className="flex items-center gap-2 data-[state=active]:bg-amber-600 data-[state=active]:text-white"
                  data-testid="private-system-tab"
                >
                  <Shield size={16} />
                  {isRTL ? 'النظام الخاص' : 'Private System'}
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6">
        <div className="flex gap-6 flex-col lg:flex-row">
          
          {/* Sidebar - Chapter List */}
          <div className="w-full lg:w-80 flex-shrink-0">
            <Card className={`${activeSystem === 'private' ? 'bg-slate-900/50 border-slate-700' : ''}`}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className={`text-lg font-serif ${activeSystem === 'private' ? 'text-white' : ''}`}>
                    {isRTL ? 'الفصول' : 'Chapters'}
                  </CardTitle>
                  {isAdmin && (
                    <Button 
                      size="sm" 
                      onClick={() => setCreateDialog(true)}
                      className={activeSystem === 'private' ? 'bg-amber-600 hover:bg-amber-700' : ''}
                      data-testid="create-chapter-btn"
                    >
                      <Plus size={16} className="me-1" />
                      {isRTL ? 'جديد' : 'New'}
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-2">
                {loading ? (
                  <div className="py-8 text-center text-muted-foreground">
                    {isRTL ? 'جاري التحميل...' : 'Loading...'}
                  </div>
                ) : chapters.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground">
                    <FileText size={40} className="mx-auto mb-2 opacity-30" />
                    <p>{isRTL ? 'لا توجد فصول' : 'No chapters yet'}</p>
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
                            ? activeSystem === 'private' 
                              ? 'bg-amber-600/20 border border-amber-600/30' 
                              : 'bg-primary/10 border border-primary/20'
                            : activeSystem === 'private'
                              ? 'hover:bg-slate-800 text-slate-300'
                              : 'hover:bg-muted'
                        }`}
                        data-testid={`chapter-item-${chapter.id}`}
                      >
                        {isAdmin && (
                          <GripVertical size={16} className="text-muted-foreground cursor-grab" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                              activeSystem === 'private' ? 'bg-slate-700 text-slate-400' : 'bg-muted'
                            }`}>
                              {index + 1}
                            </span>
                            <span className="font-medium truncate text-sm">
                              {isRTL ? chapter.title_ar : chapter.title}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            {chapter.status === 'published' ? (
                              <span className="text-xs text-emerald-500 flex items-center gap-1">
                                <Eye size={12} />
                                {isRTL ? 'منشور' : 'Published'}
                              </span>
                            ) : (
                              <span className="text-xs text-amber-500 flex items-center gap-1">
                                <EyeOff size={12} />
                                {isRTL ? 'مسودة' : 'Draft'}
                              </span>
                            )}
                          </div>
                        </div>
                        <ChevronRight size={16} className={`${isRTL ? 'rotate-180' : ''} text-muted-foreground`} />
                      </button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Main Content - Chapter View/Edit */}
          <div className="flex-1">
            {selectedChapter ? (
              <Card className={`${activeSystem === 'private' ? 'bg-slate-900/50 border-slate-700' : ''} shadow-lg`}>
                {/* Chapter Header */}
                <CardHeader className={`border-b ${activeSystem === 'private' ? 'border-slate-700' : ''}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {isEditing ? (
                        <div className="space-y-3">
                          <div>
                            <Label className={activeSystem === 'private' ? 'text-slate-300' : ''}>
                              {isRTL ? 'العنوان بالعربية' : 'Arabic Title'}
                            </Label>
                            <Input
                              value={editForm.title_ar}
                              onChange={e => setEditForm(f => ({ ...f, title_ar: e.target.value }))}
                              className={`mt-1 font-serif text-lg ${activeSystem === 'private' ? 'bg-slate-800 border-slate-600 text-white' : ''}`}
                              dir="rtl"
                            />
                          </div>
                          <div>
                            <Label className={activeSystem === 'private' ? 'text-slate-300' : ''}>
                              {isRTL ? 'العنوان بالإنجليزية' : 'English Title'}
                            </Label>
                            <Input
                              value={editForm.title}
                              onChange={e => setEditForm(f => ({ ...f, title: e.target.value }))}
                              className={`mt-1 ${activeSystem === 'private' ? 'bg-slate-800 border-slate-600 text-white' : ''}`}
                              dir="ltr"
                            />
                          </div>
                        </div>
                      ) : (
                        <>
                          <h2 className={`text-2xl font-bold font-serif ${activeSystem === 'private' ? 'text-white' : ''}`}>
                            {isRTL ? selectedChapter.title_ar : selectedChapter.title}
                          </h2>
                          <p className={`text-sm mt-1 ${activeSystem === 'private' ? 'text-slate-400' : 'text-muted-foreground'}`}>
                            {isRTL ? selectedChapter.title : selectedChapter.title_ar}
                          </p>
                        </>
                      )}
                      
                      {/* Status Badge */}
                      <div className="flex items-center gap-2 mt-3">
                        {selectedChapter.status === 'published' ? (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                            <Eye size={12} />
                            {isRTL ? 'منشور' : 'Published'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
                            <Edit2 size={12} />
                            {isRTL ? 'مسودة' : 'Draft'}
                          </span>
                        )}
                        {selectedChapter.version > 1 && (
                          <span className={`text-xs ${activeSystem === 'private' ? 'text-slate-500' : 'text-muted-foreground'}`}>
                            v{selectedChapter.version}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    {isAdmin && (
                      <div className="flex items-center gap-2">
                        {isEditing ? (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={cancelEditing}
                              className={activeSystem === 'private' ? 'text-slate-400 hover:bg-slate-800' : ''}
                            >
                              <X size={16} className="me-1" />
                              {isRTL ? 'إلغاء' : 'Cancel'}
                            </Button>
                            <Button
                              size="sm"
                              onClick={handleSaveChapter}
                              className={activeSystem === 'private' ? 'bg-amber-600 hover:bg-amber-700' : ''}
                              data-testid="save-chapter-btn"
                            >
                              <Save size={16} className="me-1" />
                              {isRTL ? 'حفظ' : 'Save'}
                            </Button>
                          </>
                        ) : (
                          <>
                            {selectedChapter.status === 'draft' && (
                              <Button
                                size="sm"
                                onClick={startEditing}
                                variant="outline"
                                className={activeSystem === 'private' ? 'border-slate-600 text-slate-300 hover:bg-slate-800' : ''}
                                data-testid="edit-chapter-btn"
                              >
                                <Edit2 size={16} className="me-1" />
                                {isRTL ? 'تحرير' : 'Edit'}
                              </Button>
                            )}
                            
                            {selectedChapter.status === 'draft' ? (
                              <Button
                                size="sm"
                                onClick={handlePublish}
                                className="bg-emerald-600 hover:bg-emerald-700"
                                data-testid="publish-btn"
                              >
                                <Eye size={16} className="me-1" />
                                {isRTL ? 'نشر' : 'Publish'}
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={handleUnpublish}
                                className={activeSystem === 'private' ? 'border-slate-600 text-slate-300 hover:bg-slate-800' : ''}
                              >
                                <EyeOff size={16} className="me-1" />
                                {isRTL ? 'إلغاء النشر' : 'Unpublish'}
                              </Button>
                            )}
                            
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setDeleteConfirm(selectedChapter)}
                              className="text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 size={16} />
                            </Button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </CardHeader>

                {/* Chapter Content */}
                <CardContent className="p-0">
                  <div className={`min-h-[400px] ${activeSystem === 'private' ? 'bg-slate-950/50' : 'bg-background'}`}>
                    {isEditing ? (
                      <SmartEditor
                        content={editForm.content}
                        onChange={content => setEditForm(f => ({ ...f, content }))}
                        placeholder={isRTL ? 'ابدأ كتابة محتوى الفصل...' : 'Start writing chapter content...'}
                      />
                    ) : (
                      <div 
                        className={`prose prose-sm sm:prose max-w-none p-6 ${activeSystem === 'private' ? 'prose-invert' : ''}`}
                        dir={isRTL ? 'rtl' : 'ltr'}
                        dangerouslySetInnerHTML={{ __html: selectedChapter.content || `<p class="text-muted-foreground">${isRTL ? 'لا يوجد محتوى بعد' : 'No content yet'}</p>` }}
                      />
                    )}
                  </div>

                  {/* Legal Footer */}
                  <div className={`mt-4 mx-4 mb-4 p-4 rounded-lg border-2 ${
                    activeSystem === 'private' 
                      ? 'bg-slate-950 border-amber-600/30' 
                      : 'bg-slate-50 dark:bg-slate-900 border-primary/20'
                  }`}>
                    <div className="flex items-start gap-3">
                      <Lock size={18} className={activeSystem === 'private' ? 'text-amber-500 mt-1' : 'text-primary mt-1'} />
                      <div className="flex-1">
                        <p className={`text-sm font-medium mb-2 ${activeSystem === 'private' ? 'text-amber-500' : 'text-primary'}`}>
                          {isRTL ? 'إخلاء المسؤولية القانوني' : 'Legal Disclaimer'}
                        </p>
                        <p className={`text-xs leading-relaxed whitespace-pre-line ${
                          activeSystem === 'private' ? 'text-slate-400' : 'text-muted-foreground'
                        }`}>
                          {legalFooter ? (isRTL ? legalFooter.text_ar : legalFooter.text_en) : ''}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className={`${activeSystem === 'private' ? 'bg-slate-900/50 border-slate-700' : ''}`}>
                <CardContent className="py-20 text-center">
                  <Book size={60} className={`mx-auto mb-4 ${activeSystem === 'private' ? 'text-amber-500/30' : 'text-primary/30'}`} />
                  <h3 className={`text-xl font-serif ${activeSystem === 'private' ? 'text-white' : ''}`}>
                    {isRTL ? 'اختر فصلاً للقراءة' : 'Select a Chapter'}
                  </h3>
                  <p className={`mt-2 ${activeSystem === 'private' ? 'text-slate-400' : 'text-muted-foreground'}`}>
                    {isRTL 
                      ? 'اختر فصلاً من القائمة الجانبية لعرض محتواه'
                      : 'Choose a chapter from the sidebar to view its content'
                    }
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      {/* Create Chapter Dialog */}
      <Dialog open={createDialog} onOpenChange={setCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif">
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
                className="mt-1"
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
                className="mt-1"
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
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle size={20} />
              {isRTL ? 'تأكيد الحذف' : 'Confirm Delete'}
            </DialogTitle>
          </DialogHeader>
          <p className="py-4">
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
            <DialogTitle className="font-serif flex items-center gap-2">
              <Lock size={20} className="text-primary" />
              {isRTL ? 'تعديل التذييل القانوني' : 'Edit Legal Footer'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>{isRTL ? 'النص العربي' : 'Arabic Text'}</Label>
              <textarea
                value={legalForm.text_ar}
                onChange={e => setLegalForm(f => ({ ...f, text_ar: e.target.value }))}
                className="mt-1 w-full h-32 p-3 rounded-lg border bg-background resize-none text-sm"
                dir="rtl"
              />
            </div>
            <div>
              <Label>{isRTL ? 'النص الإنجليزي' : 'English Text'}</Label>
              <textarea
                value={legalForm.text_en}
                onChange={e => setLegalForm(f => ({ ...f, text_en: e.target.value }))}
                className="mt-1 w-full h-32 p-3 rounded-lg border bg-background resize-none text-sm"
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
