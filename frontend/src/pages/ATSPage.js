import { useState, useEffect, useCallback } from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import api from '../lib/api';
import { 
  Briefcase, Plus, Users, Eye, Link2, Trash2, Archive, 
  RefreshCw, ChevronLeft, Clock, FileText, Download,
  CheckCircle, XCircle, MessageSquare, Send, Star,
  AlertTriangle, TrendingUp, Shield, Target, Brain,
  Filter, Zap, Award, AlertOctagon
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';

export default function ATSPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  
  // State
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('jobs');
  const [selectedJob, setSelectedJob] = useState(null);
  const [applications, setApplications] = useState([]);
  const [tierCounts, setTierCounts] = useState({});
  const [selectedApp, setSelectedApp] = useState(null);
  const [showTierC, setShowTierC] = useState(false);
  const [tierFilter, setTierFilter] = useState('all');
  
  // Dialogs
  const [showJobDialog, setShowJobDialog] = useState(false);
  const [showAppDetails, setShowAppDetails] = useState(false);
  const [editJob, setEditJob] = useState(null);
  
  // Form state
  const [jobForm, setJobForm] = useState({
    title_ar: '',
    title_en: '',
    description: '',
    location: '',
    contract_type: 'full_time',
    experience_years: 0,
    required_languages: ['ar'],
    required_skills: ''
  });
  
  const [noteText, setNoteText] = useState('');
  const [showNuclearDialog, setShowNuclearDialog] = useState(false);
  const [nuclearLoading, setNuclearLoading] = useState(false);
  const [nuclearConfirmText, setNuclearConfirmText] = useState('');
  
  const isAdmin = user?.role === 'admin' || ['stas', 'naif'].includes(user?.username);
  const canAccess = isAdmin || user?.role === 'hr' || ['sultan', 'mohammed'].includes(user?.username);
  const canNuclearDelete = ['stas', 'sultan'].includes(user?.username);
  
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  
  // Load data
  const loadJobs = useCallback(async () => {
    try {
      const res = await api.get('/api/ats/admin/jobs');
      setJobs(res.data);
    } catch (err) {
      console.error('Error loading jobs:', err);
    }
  }, []);
  
  const loadStats = useCallback(async () => {
    try {
      const res = await api.get('/api/ats/admin/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  }, []);
  
  const loadApplications = useCallback(async (jobId, tier = null) => {
    try {
      let url = `/api/ats/admin/jobs/${jobId}/applications?show_tier_c=${showTierC}`;
      if (tier && tier !== 'all') url += `&tier=${tier}`;
      const res = await api.get(url);
      setSelectedJob(res.data.job);
      setApplications(res.data.applications);
      setTierCounts(res.data.tier_counts || {});
      setView('applications');
    } catch (err) {
      toast.error(lang === 'ar' ? 'خطأ في تحميل الطلبات' : 'Error loading applications');
    }
  }, [lang, showTierC]);
  
  useEffect(() => {
    if (canAccess) {
      setLoading(true);
      Promise.all([loadJobs(), loadStats()]).finally(() => setLoading(false));
    }
  }, [canAccess, loadJobs, loadStats]);
  
  // Job actions
  const handleSaveJob = async () => {
    try {
      if (editJob) {
        await api.put(`/api/ats/admin/jobs/${editJob.id}`, jobForm);
        toast.success(lang === 'ar' ? 'تم تحديث الوظيفة' : 'Job updated');
      } else {
        await api.post('/api/ats/admin/jobs', jobForm);
        toast.success(lang === 'ar' ? 'تم إنشاء الوظيفة' : 'Job created');
      }
      setShowJobDialog(false);
      setEditJob(null);
      resetJobForm();
      loadJobs();
      loadStats();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error saving job');
    }
  };
  
  const handleDeleteJob = async (jobId) => {
    if (!window.confirm(lang === 'ar' ? 'هل أنت متأكد من حذف هذه الوظيفة وجميع الطلبات؟' : 'Delete this job and all applications?')) return;
    try {
      await api.delete(`/api/ats/admin/jobs/${jobId}`);
      toast.success(lang === 'ar' ? 'تم الحذف' : 'Deleted');
      loadJobs();
      loadStats();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error deleting job');
    }
  };
  
  const handleArchiveJob = async (jobId) => {
    try {
      await api.post(`/api/ats/admin/jobs/${jobId}/archive`);
      toast.success(lang === 'ar' ? 'تم الأرشفة' : 'Archived');
      loadJobs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error archiving job');
    }
  };
  
  const handleCloseJob = async (jobId) => {
    try {
      await api.post(`/api/ats/admin/jobs/${jobId}/close`);
      toast.success(lang === 'ar' ? 'تم إغلاق الوظيفة' : 'Job closed');
      loadJobs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error closing job');
    }
  };
  
  const handleReopenJob = async (jobId) => {
    try {
      await api.post(`/api/ats/admin/jobs/${jobId}/reopen`);
      toast.success(lang === 'ar' ? 'تم إعادة فتح الوظيفة' : 'Job reopened');
      loadJobs();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error reopening job');
    }
  };
  
  const copyApplyLink = (slug) => {
    const link = `${baseUrl}/apply/${slug}`;
    navigator.clipboard.writeText(link);
    toast.success(lang === 'ar' ? 'تم نسخ الرابط' : 'Link copied');
  };
  
  // Application actions
  const handleUpdateStatus = async (appId, status) => {
    try {
      await api.put(`/api/ats/admin/applications/${appId}/status`, { status });
      toast.success(lang === 'ar' ? 'تم تحديث الحالة' : 'Status updated');
      if (selectedJob) loadApplications(selectedJob.id, tierFilter);
      if (selectedApp) {
        const res = await api.get(`/api/ats/admin/applications/${appId}`);
        setSelectedApp(res.data);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error updating status');
    }
  };
  
  const handleAddNote = async (appId) => {
    if (!noteText.trim()) return;
    try {
      await api.post(`/api/ats/admin/applications/${appId}/notes`, { note: noteText });
      setNoteText('');
      const res = await api.get(`/api/ats/admin/applications/${appId}`);
      setSelectedApp(res.data);
      toast.success(lang === 'ar' ? 'تمت إضافة الملاحظة' : 'Note added');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error adding note');
    }
  };
  
  const handleDeleteApplication = async (appId) => {
    if (!window.confirm(lang === 'ar' ? 'هل أنت متأكد من الحذف النهائي لهذا الطلب والملفات؟' : 'Permanently delete this application and files?')) return;
    try {
      await api.delete(`/api/ats/admin/applications/${appId}`);
      toast.success(lang === 'ar' ? 'تم الحذف النهائي' : 'Permanently deleted');
      setShowAppDetails(false);
      setSelectedApp(null);
      if (selectedJob) loadApplications(selectedJob.id, tierFilter);
      loadStats();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error deleting application');
    }
  };
  
  const resetJobForm = () => {
    setJobForm({
      title_ar: '',
      title_en: '',
      description: '',
      location: '',
      contract_type: 'full_time',
      experience_years: 0,
      required_languages: ['ar'],
      required_skills: ''
    });
  };
  
  const openEditJob = (job) => {
    setEditJob(job);
    setJobForm({
      title_ar: job.title_ar || '',
      title_en: job.title_en || '',
      description: job.description || '',
      location: job.location || '',
      contract_type: job.contract_type || 'full_time',
      experience_years: job.experience_years || 0,
      required_languages: job.required_languages || ['ar'],
      required_skills: job.required_skills || ''
    });
    setShowJobDialog(true);
  };
  
  const openAppDetails = async (app) => {
    try {
      const res = await api.get(`/api/ats/admin/applications/${app.id}`);
      setSelectedApp(res.data);
      setShowAppDetails(true);
    } catch (err) {
      toast.error('Error loading application details');
    }
  };
  
  const getStatusColor = (status) => {
    const colors = {
      new: 'bg-blue-100 text-blue-700',
      reviewed: 'bg-yellow-100 text-yellow-700',
      interview: 'bg-purple-100 text-purple-700',
      offer: 'bg-green-100 text-green-700',
      hired: 'bg-emerald-100 text-emerald-700',
      rejected: 'bg-red-100 text-red-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };
  
  const getStatusLabel = (status) => {
    const labels = {
      new: { ar: 'جديد', en: 'New' },
      reviewed: { ar: 'تمت المراجعة', en: 'Reviewed' },
      interview: { ar: 'مقابلة', en: 'Interview' },
      offer: { ar: 'عرض', en: 'Offer' },
      hired: { ar: 'تم التوظيف', en: 'Hired' },
      rejected: { ar: 'مرفوض', en: 'Rejected' }
    };
    return labels[status]?.[lang] || status;
  };
  
  const getTierColor = (tier) => {
    const colors = {
      A: 'bg-emerald-500 text-white',
      B: 'bg-blue-500 text-white',
      C: 'bg-slate-400 text-white'
    };
    return colors[tier] || 'bg-slate-300 text-white';
  };
  
  const getClassColor = (cls) => {
    const colors = {
      'Excellent': 'bg-emerald-100 text-emerald-700 border-emerald-200',
      'Strong': 'bg-blue-100 text-blue-700 border-blue-200',
      'Acceptable': 'bg-yellow-100 text-yellow-700 border-yellow-200',
      'Weak': 'bg-red-100 text-red-700 border-red-200',
      'Rejected (Unreadable)': 'bg-slate-100 text-slate-700 border-slate-200'
    };
    return colors[cls] || 'bg-slate-100 text-slate-700';
  };
  
  const getJobStatusColor = (status) => {
    const colors = {
      active: 'bg-green-100 text-green-700',
      closed: 'bg-gray-100 text-gray-700',
      archived: 'bg-orange-100 text-orange-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };
  
  if (!canAccess) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">{lang === 'ar' ? 'غير مصرح بالوصول' : 'Access denied'}</p>
      </div>
    );
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }
  
  return (
    <div className="space-y-4 pb-20" data-testid="ats-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {view !== 'jobs' && (
            <Button variant="ghost" size="sm" onClick={() => { setView('jobs'); setSelectedJob(null); }}>
              <ChevronLeft size={18} />
            </Button>
          )}
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-primary" />
            {view === 'jobs' ? 'ATS' : (lang === 'ar' ? selectedJob?.title_ar : selectedJob?.title_en)}
          </h1>
        </div>
        {view === 'jobs' && (
          <Button onClick={() => { resetJobForm(); setEditJob(null); setShowJobDialog(true); }} data-testid="add-job-btn">
            <Plus size={18} className="mr-1" />
            {lang === 'ar' ? 'إضافة وظيفة' : 'Add Job'}
          </Button>
        )}
      </div>
      
      {/* Stats */}
      {view === 'jobs' && stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="card-premium p-3 text-center">
            <p className="text-2xl font-bold text-primary">{stats.total_jobs}</p>
            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'إجمالي الوظائف' : 'Total Jobs'}</p>
          </div>
          <div className="card-premium p-3 text-center">
            <p className="text-2xl font-bold text-green-600">{stats.active_jobs}</p>
            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'وظائف نشطة' : 'Active Jobs'}</p>
          </div>
          <div className="card-premium p-3 text-center">
            <p className="text-2xl font-bold text-blue-600">{stats.total_applications}</p>
            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'إجمالي الطلبات' : 'Applications'}</p>
          </div>
          <div className="card-premium p-3 text-center">
            <p className="text-2xl font-bold text-orange-600">{stats.new_applications}</p>
            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'طلبات جديدة' : 'New'}</p>
          </div>
          <div className="card-premium p-3 text-center">
            <p className="text-2xl font-bold text-purple-600">{stats.high_potential || 0}</p>
            <p className="text-xs text-muted-foreground">{lang === 'ar' ? 'مواهب واعدة' : 'High Potential'}</p>
          </div>
        </div>
      )}
      
      {/* Jobs List */}
      {view === 'jobs' && (
        <div className="card-premium overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b text-xs">
                <th className="px-4 py-3 text-right font-semibold">{lang === 'ar' ? 'الوظيفة' : 'Job'}</th>
                <th className="px-4 py-3 text-center font-semibold w-28">{lang === 'ar' ? 'التاريخ' : 'Date'}</th>
                <th className="px-4 py-3 text-center font-semibold w-24">{lang === 'ar' ? 'الطلبات' : 'Apps'}</th>
                <th className="px-4 py-3 text-center font-semibold w-24">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                <th className="px-4 py-3 text-center font-semibold w-48">{lang === 'ar' ? 'الإجراءات' : 'Actions'}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-muted-foreground">
                    {lang === 'ar' ? 'لا توجد وظائف' : 'No jobs yet'}
                  </td>
                </tr>
              ) : jobs.map(job => (
                <tr key={job.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <p className="font-medium">{lang === 'ar' ? job.title_ar : job.title_en}</p>
                    <p className="text-xs text-muted-foreground">{job.location}</p>
                  </td>
                  <td className="px-4 py-3 text-center text-xs font-mono">
                    {job.created_at?.split('T')[0]}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-700 font-bold">
                      {job.applicants_count || 0}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getJobStatusColor(job.status)}`}>
                      {job.status === 'active' ? (lang === 'ar' ? 'نشط' : 'Active') : 
                       job.status === 'closed' ? (lang === 'ar' ? 'مغلق' : 'Closed') :
                       (lang === 'ar' ? 'مؤرشف' : 'Archived')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => loadApplications(job.id)} title={lang === 'ar' ? 'عرض الطلبات' : 'View Applications'}>
                        <Users size={16} />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => copyApplyLink(job.slug)} title={lang === 'ar' ? 'نسخ رابط التقديم' : 'Copy Apply Link'}>
                        <Link2 size={16} />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => openEditJob(job)} title={lang === 'ar' ? 'تعديل' : 'Edit'}>
                        <Eye size={16} />
                      </Button>
                      {job.status === 'active' && (
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-orange-600" onClick={() => handleCloseJob(job.id)} title={lang === 'ar' ? 'إغلاق' : 'Close'}>
                          <XCircle size={16} />
                        </Button>
                      )}
                      {job.status === 'closed' && (
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-green-600" onClick={() => handleReopenJob(job.id)} title={lang === 'ar' ? 'إعادة فتح' : 'Reopen'}>
                          <CheckCircle size={16} />
                        </Button>
                      )}
                      {isAdmin && (
                        <>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-yellow-600" onClick={() => handleArchiveJob(job.id)} title={lang === 'ar' ? 'أرشفة' : 'Archive'}>
                            <Archive size={16} />
                          </Button>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-destructive" onClick={() => handleDeleteJob(job.id)} title={lang === 'ar' ? 'حذف' : 'Delete'}>
                            <Trash2 size={16} />
                          </Button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {/* Applications List with Tier Filter */}
      {view === 'applications' && (
        <>
          {/* Tier Filter */}
          <div className="flex items-center justify-between bg-slate-50 p-3 rounded-lg">
            <div className="flex items-center gap-2">
              <Filter size={16} className="text-slate-500" />
              <span className="text-sm font-medium">{lang === 'ar' ? 'الفئة:' : 'Tier:'}</span>
              <div className="flex gap-1">
                {['all', 'A', 'B', 'C'].map(tier => (
                  <button
                    key={tier}
                    onClick={() => { setTierFilter(tier); loadApplications(selectedJob.id, tier); }}
                    className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                      tierFilter === tier 
                        ? 'bg-slate-900 text-white' 
                        : 'bg-white text-slate-600 hover:bg-slate-100 border'
                    }`}
                  >
                    {tier === 'all' ? (lang === 'ar' ? 'الكل' : 'All') : `Tier ${tier}`}
                    {tier !== 'all' && tierCounts[tier] !== undefined && ` (${tierCounts[tier]})`}
                  </button>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input 
                type="checkbox" 
                checked={showTierC} 
                onChange={e => { setShowTierC(e.target.checked); loadApplications(selectedJob.id, tierFilter); }}
                className="rounded"
              />
              {lang === 'ar' ? 'إظهار الفئة C' : 'Show Tier C'}
            </label>
          </div>
          
          <div className="card-premium overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b text-xs">
                  <th className="px-4 py-3 text-right font-semibold">{lang === 'ar' ? 'المتقدم' : 'Candidate'}</th>
                  <th className="px-4 py-3 text-center font-semibold w-20">{lang === 'ar' ? 'الفئة' : 'Tier'}</th>
                  <th className="px-4 py-3 text-center font-semibold w-24">{lang === 'ar' ? 'النتيجة' : 'Score'}</th>
                  <th className="px-4 py-3 text-center font-semibold w-28">{lang === 'ar' ? 'التصنيف' : 'Class'}</th>
                  <th className="px-4 py-3 text-center font-semibold w-24">{lang === 'ar' ? 'الحالة' : 'Status'}</th>
                  <th className="px-4 py-3 text-center font-semibold w-24">{lang === 'ar' ? 'التفاصيل' : 'Details'}</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {applications.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-muted-foreground">
                      {lang === 'ar' ? 'لا توجد طلبات' : 'No applications yet'}
                    </td>
                  </tr>
                ) : applications.map(app => (
                  <tr key={app.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div>
                          <p className="font-medium flex items-center gap-1">
                            {app.full_name}
                            {app.scoring?.high_potential && (
                              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-[10px] font-bold rounded">
                                <Zap size={10} />
                                HP
                              </span>
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground">{app.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${getTierColor(app.tier)}`}>
                        {app.tier || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-lg font-bold">{app.score ?? '-'}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${getClassColor(app.auto_class)}`}>
                        {app.auto_class || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(app.status)}`}>
                        {getStatusLabel(app.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button variant="ghost" size="sm" onClick={() => openAppDetails(app)}>
                        <Eye size={16} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      
      {/* Job Dialog */}
      <Dialog open={showJobDialog} onOpenChange={setShowJobDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editJob ? (lang === 'ar' ? 'تعديل الوظيفة' : 'Edit Job') : (lang === 'ar' ? 'إضافة وظيفة جديدة' : 'Add New Job')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>{lang === 'ar' ? 'المسمى (عربي)' : 'Title (Arabic)'}</Label>
                <Input value={jobForm.title_ar} onChange={e => setJobForm({...jobForm, title_ar: e.target.value})} dir="rtl" />
              </div>
              <div>
                <Label>{lang === 'ar' ? 'المسمى (إنجليزي)' : 'Title (English)'}</Label>
                <Input value={jobForm.title_en} onChange={e => setJobForm({...jobForm, title_en: e.target.value})} />
              </div>
            </div>
            
            <div>
              <Label>{lang === 'ar' ? 'الوصف' : 'Description'}</Label>
              <Textarea value={jobForm.description} onChange={e => setJobForm({...jobForm, description: e.target.value})} rows={3} />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>{lang === 'ar' ? 'الموقع' : 'Location'}</Label>
                <Input value={jobForm.location} onChange={e => setJobForm({...jobForm, location: e.target.value})} />
              </div>
              <div>
                <Label>{lang === 'ar' ? 'نوع العقد' : 'Contract Type'}</Label>
                <Select value={jobForm.contract_type} onValueChange={v => setJobForm({...jobForm, contract_type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full_time">{lang === 'ar' ? 'دوام كامل' : 'Full Time'}</SelectItem>
                    <SelectItem value="part_time">{lang === 'ar' ? 'دوام جزئي' : 'Part Time'}</SelectItem>
                    <SelectItem value="contract">{lang === 'ar' ? 'عقد مؤقت' : 'Contract'}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>{lang === 'ar' ? 'سنوات الخبرة' : 'Experience (years)'}</Label>
                <Input type="number" min="0" value={jobForm.experience_years} onChange={e => setJobForm({...jobForm, experience_years: parseInt(e.target.value) || 0})} />
              </div>
              <div>
                <Label>{lang === 'ar' ? 'اللغات المطلوبة' : 'Required Languages'}</Label>
                <Select value={jobForm.required_languages?.join(',') || 'ar'} onValueChange={v => setJobForm({...jobForm, required_languages: v.split(',')})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ar">{lang === 'ar' ? 'عربي فقط' : 'Arabic Only'}</SelectItem>
                    <SelectItem value="en">{lang === 'ar' ? 'إنجليزي فقط' : 'English Only'}</SelectItem>
                    <SelectItem value="ar,en">{lang === 'ar' ? 'عربي وإنجليزي' : 'Arabic & English'}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <Label>{lang === 'ar' ? 'المهارات المطلوبة (مفصولة بفاصلة)' : 'Required Skills (comma separated)'}</Label>
              <Input value={jobForm.required_skills} onChange={e => setJobForm({...jobForm, required_skills: e.target.value})} placeholder="Excel, Word, Communication" />
            </div>
            
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setShowJobDialog(false)}>{lang === 'ar' ? 'إلغاء' : 'Cancel'}</Button>
              <Button onClick={handleSaveJob}>{editJob ? (lang === 'ar' ? 'تحديث' : 'Update') : (lang === 'ar' ? 'إنشاء' : 'Create')}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Application Details Dialog - Enhanced with ATS Intelligence */}
      <Dialog open={showAppDetails} onOpenChange={setShowAppDetails}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-600" />
              {lang === 'ar' ? 'تحليل الطلب' : 'Application Analysis'}
            </DialogTitle>
          </DialogHeader>
          
          {selectedApp && (
            <div className="space-y-4 mt-4">
              {/* Candidate Info + Score Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h3 className="font-semibold mb-2">{selectedApp.full_name}</h3>
                  <p className="text-sm text-muted-foreground">{selectedApp.email}</p>
                  <p className="text-sm text-muted-foreground">{selectedApp.phone}</p>
                  <div className="flex items-center gap-2 mt-3">
                    {selectedApp.ats_readable ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                        <CheckCircle size={12} /> ATS Readable
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                        <XCircle size={12} /> Not Readable
                      </span>
                    )}
                    {selectedApp.scoring?.high_potential && (
                      <span className="inline-flex items-center gap-1 text-xs text-yellow-700 bg-yellow-100 px-2 py-1 rounded font-medium">
                        <Zap size={12} /> High Potential
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="p-4 bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg text-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-400">{lang === 'ar' ? 'النتيجة الإجمالية' : 'Overall Score'}</p>
                      <p className="text-4xl font-bold">{selectedApp.score ?? 0}</p>
                    </div>
                    <div className="text-right">
                      <span className={`inline-block px-3 py-1 rounded-lg text-sm font-bold ${getTierColor(selectedApp.tier)}`}>
                        Tier {selectedApp.tier || '-'}
                      </span>
                      <p className="text-xs text-slate-400 mt-1">{selectedApp.auto_class}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Scoring Details */}
              {selectedApp.scoring && (
                <>
                  {/* Score Breakdown */}
                  <div className="p-4 border rounded-lg">
                    <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Target size={16} className="text-blue-600" />
                      {lang === 'ar' ? 'تفاصيل التقييم' : 'Score Breakdown'}
                    </h4>
                    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
                      {[
                        { key: 'skill_match_score', label: lang === 'ar' ? 'المهارات' : 'Skills', icon: Target },
                        { key: 'experience_score', label: lang === 'ar' ? 'الخبرة' : 'Experience', icon: Clock },
                        { key: 'education_score', label: lang === 'ar' ? 'التعليم' : 'Education', icon: Award },
                        { key: 'language_score', label: lang === 'ar' ? 'اللغات' : 'Languages', icon: MessageSquare },
                        { key: 'stability_score', label: lang === 'ar' ? 'الاستقرار' : 'Stability', icon: Shield },
                        { key: 'evidence_score', label: lang === 'ar' ? 'الإنجازات' : 'Evidence', icon: TrendingUp },
                      ].map(item => (
                        <div key={item.key} className="text-center p-2 bg-slate-50 rounded-lg">
                          <item.icon size={14} className="mx-auto text-slate-400 mb-1" />
                          <p className="text-lg font-bold">{selectedApp.scoring[item.key] ?? 0}</p>
                          <p className="text-[10px] text-muted-foreground">{item.label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Risk Indicators */}
                  <div className="p-4 border rounded-lg">
                    <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <AlertTriangle size={16} className="text-orange-600" />
                      {lang === 'ar' ? 'مؤشرات المخاطر' : 'Risk Indicators'}
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { key: 'fluff_ratio', label: lang === 'ar' ? 'الحشو' : 'Fluff', color: 'orange' },
                        { key: 'ego_index', label: lang === 'ar' ? 'الأنا' : 'Ego', color: 'purple' },
                        { key: 'stuffing_risk', label: lang === 'ar' ? 'الحشو بالكلمات' : 'Stuffing', color: 'red' },
                        { key: 'stability_risk', label: lang === 'ar' ? 'عدم الاستقرار' : 'Instability', color: 'yellow' },
                      ].map(item => {
                        const value = selectedApp.scoring[item.key] ?? 0;
                        const percent = Math.round(value * 100);
                        const isHigh = percent > 50;
                        return (
                          <div key={item.key} className={`p-3 rounded-lg ${isHigh ? `bg-${item.color}-50` : 'bg-slate-50'}`}>
                            <p className="text-xs text-muted-foreground">{item.label}</p>
                            <p className={`text-xl font-bold ${isHigh ? `text-${item.color}-600` : 'text-slate-600'}`}>
                              {percent}%
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  
                  {/* Top Reasons & Risks */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 border border-green-200 bg-green-50 rounded-lg">
                      <h4 className="text-sm font-semibold text-green-700 mb-2 flex items-center gap-2">
                        <CheckCircle size={14} />
                        {lang === 'ar' ? 'نقاط القوة' : 'Strengths'}
                      </h4>
                      <ul className="space-y-1">
                        {(selectedApp.scoring.top_reasons || []).map((r, i) => (
                          <li key={i} className="text-sm text-green-800 flex items-start gap-2">
                            <span className="text-green-500">+</span> {r}
                          </li>
                        ))}
                        {(!selectedApp.scoring.top_reasons || selectedApp.scoring.top_reasons.length === 0) && (
                          <li className="text-sm text-green-600">-</li>
                        )}
                      </ul>
                    </div>
                    
                    <div className="p-4 border border-red-200 bg-red-50 rounded-lg">
                      <h4 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-2">
                        <AlertTriangle size={14} />
                        {lang === 'ar' ? 'المخاطر' : 'Risks'}
                      </h4>
                      <ul className="space-y-1">
                        {(selectedApp.scoring.risks || []).map((r, i) => (
                          <li key={i} className="text-sm text-red-800 flex items-start gap-2">
                            <span className="text-red-500">!</span> {r}
                          </li>
                        ))}
                        {(!selectedApp.scoring.risks || selectedApp.scoring.risks.length === 0) && (
                          <li className="text-sm text-red-600">-</li>
                        )}
                      </ul>
                    </div>
                  </div>
                  
                  {/* Skills Match */}
                  {(selectedApp.scoring.matched_skills?.length > 0 || selectedApp.scoring.missing_skills?.length > 0) && (
                    <div className="p-4 border rounded-lg">
                      <h4 className="text-sm font-semibold mb-2">{lang === 'ar' ? 'مطابقة المهارات' : 'Skills Match'}</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedApp.scoring.matched_skills?.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                            {s}
                          </span>
                        ))}
                        {selectedApp.scoring.missing_skills?.map((s, i) => (
                          <span key={i} className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full line-through">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {/* Files */}
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">{lang === 'ar' ? 'الملفات المرفقة' : 'Attached Files'}</p>
                <div className="space-y-2">
                  {selectedApp.files?.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                      <div className="flex items-center gap-2">
                        <FileText size={16} className="text-blue-600" />
                        <span className="text-sm">{file.original_name}</span>
                        <span className="text-xs text-muted-foreground">({(file.size / 1024).toFixed(1)} KB)</span>
                        {file.is_readable === false && (
                          <span className="text-xs text-red-500">(Unreadable)</span>
                        )}
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <a href={`${baseUrl}/api/upload/ats_cv/${file.saved_name}`} target="_blank" rel="noopener noreferrer">
                          <Download size={14} />
                        </a>
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Status Actions */}
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">{lang === 'ar' ? 'الحالة' : 'Status'}</p>
                <div className="flex flex-wrap gap-2">
                  {['new', 'reviewed', 'interview', 'offer', 'hired', 'rejected'].map(status => (
                    <Button
                      key={status}
                      variant={selectedApp.status === status ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handleUpdateStatus(selectedApp.id, status)}
                      className={selectedApp.status === status ? '' : 'opacity-60'}
                    >
                      {getStatusLabel(status)}
                    </Button>
                  ))}
                </div>
              </div>
              
              {/* Notes */}
              <div className="p-4 border rounded-lg">
                <p className="text-sm text-muted-foreground mb-2">{lang === 'ar' ? 'الملاحظات' : 'Notes'}</p>
                {selectedApp.notes?.length > 0 && (
                  <div className="space-y-2 mb-4">
                    {selectedApp.notes.map((note, idx) => (
                      <div key={idx} className="p-2 bg-slate-50 rounded text-sm">
                        <p>{note.text}</p>
                        <p className="text-xs text-muted-foreground mt-1">{note.created_by_name} - {note.created_at?.split('T')[0]}</p>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <Input value={noteText} onChange={e => setNoteText(e.target.value)} placeholder={lang === 'ar' ? 'أضف ملاحظة...' : 'Add a note...'} onKeyDown={e => e.key === 'Enter' && handleAddNote(selectedApp.id)} />
                  <Button size="sm" onClick={() => handleAddNote(selectedApp.id)}><Send size={14} /></Button>
                </div>
              </div>
              
              {/* Admin Actions */}
              {isAdmin && (
                <div className="flex justify-end pt-4 border-t">
                  <Button variant="destructive" size="sm" onClick={() => handleDeleteApplication(selectedApp.id)}>
                    <Trash2 size={14} className="mr-1" />
                    {lang === 'ar' ? 'حذف نهائي' : 'Permanent Delete'}
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
