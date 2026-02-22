import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2, Briefcase, MapPin, Clock, Send } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

// Public Apply Page - Completely isolated, no auth required
export default function PublicApplyPage() {
  const { slug } = useParams();
  
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitMessage, setSubmitMessage] = useState(null);
  
  // Form state
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [files, setFiles] = useState([]);
  const [fileErrors, setFileErrors] = useState([]);
  
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  
  // Detect language from browser
  const browserLang = navigator.language?.startsWith('ar') ? 'ar' : 'en';
  const [lang, setLang] = useState(browserLang);
  
  // Load job details
  useEffect(() => {
    const loadJob = async () => {
      try {
        const res = await fetch(`${baseUrl}/api/ats/public/jobs/${slug}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail?.[lang] || err.detail?.en || 'Job not found');
        }
        const data = await res.json();
        setJob(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    if (slug) loadJob();
  }, [slug, baseUrl, lang]);
  
  // File handling
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFileErrors([]);
    
    // Validate file count
    if (selectedFiles.length + files.length > 2) {
      setFileErrors([lang === 'ar' ? 'الحد الأقصى ملفين فقط' : 'Maximum 2 files allowed']);
      return;
    }
    
    const newFiles = [];
    const errors = [];
    
    for (const file of selectedFiles) {
      // Check extension
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!['pdf', 'doc', 'docx'].includes(ext)) {
        errors.push(lang === 'ar' 
          ? `${file.name}: نوع غير مدعوم. الأنواع المسموحة: PDF, DOC, DOCX` 
          : `${file.name}: Unsupported type. Allowed: PDF, DOC, DOCX`);
        continue;
      }
      
      // Check size (5MB)
      if (file.size > 5 * 1024 * 1024) {
        errors.push(lang === 'ar' 
          ? `${file.name}: حجم كبير جداً (الحد 5MB)` 
          : `${file.name}: Too large (max 5MB)`);
        continue;
      }
      
      newFiles.push(file);
    }
    
    if (errors.length > 0) {
      setFileErrors(errors);
    }
    
    if (newFiles.length > 0) {
      setFiles(prev => [...prev, ...newFiles].slice(0, 2));
    }
  };
  
  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setFileErrors([]);
  };
  
  // Submit application
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate
    if (!fullName.trim()) {
      setFileErrors([lang === 'ar' ? 'الرجاء إدخال الاسم الكامل' : 'Please enter your full name']);
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setFileErrors([lang === 'ar' ? 'الرجاء إدخال بريد إلكتروني صحيح' : 'Please enter a valid email']);
      return;
    }
    if (!phone.trim()) {
      setFileErrors([lang === 'ar' ? 'الرجاء إدخال رقم الهاتف' : 'Please enter your phone number']);
      return;
    }
    if (files.length === 0) {
      setFileErrors([lang === 'ar' ? 'الرجاء رفع السيرة الذاتية' : 'Please upload your CV']);
      return;
    }
    
    setSubmitting(true);
    setFileErrors([]);
    
    try {
      const formData = new FormData();
      formData.append('full_name', fullName.trim());
      formData.append('email', email.trim());
      formData.append('phone', phone.trim());
      files.forEach(file => formData.append('files', file));
      
      const res = await fetch(`${baseUrl}/api/ats/public/apply/${slug}`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail?.[lang] || data.detail?.en || data.detail || 'Error submitting application');
      }
      
      setSubmitted(true);
      setSubmitMessage(data.message);
    } catch (err) {
      setFileErrors([err.message]);
    } finally {
      setSubmitting(false);
    }
  };
  
  const contractTypes = {
    full_time: { ar: 'دوام كامل', en: 'Full Time' },
    part_time: { ar: 'دوام جزئي', en: 'Part Time' },
    contract: { ar: 'عقد مؤقت', en: 'Contract' }
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-slate-600">{lang === 'ar' ? 'جاري التحميل...' : 'Loading...'}</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-slate-800 mb-2">
            {lang === 'ar' ? 'عذراً' : 'Sorry'}
          </h1>
          <p className="text-slate-600">{error}</p>
        </div>
      </div>
    );
  }
  
  // Success state
  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-12 h-12 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 mb-4">
            {lang === 'ar' ? 'تم الإرسال بنجاح!' : 'Successfully Submitted!'}
          </h1>
          <p className="text-slate-600 leading-relaxed">
            {submitMessage?.[lang] || submitMessage?.en || (lang === 'ar' 
              ? 'شكراً، تم استلام السيرة الذاتية بنجاح. سيتم التواصل عبر بيانات الاتصال.'
              : 'Thank you, your CV has been received successfully. We will contact you via your contact details.'
            )}
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-8 px-4" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Language Toggle */}
      <div className="fixed top-4 right-4 z-50">
        <button 
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          className="px-3 py-1.5 bg-white rounded-full shadow text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          {lang === 'ar' ? 'English' : 'عربي'}
        </button>
      </div>
      
      <div className="max-w-xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Briefcase className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">
            {lang === 'ar' ? 'التقديم على وظيفة' : 'Job Application'}
          </h1>
          <p className="text-slate-500 mt-2">
            {lang === 'ar' ? 'مرحباً بك، يسعدنا انضمامك لفريقنا' : 'Welcome! We\'re excited to have you join our team'}
          </p>
        </div>
        
        {/* Job Card */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-slate-800 mb-3">
            {lang === 'ar' ? job?.title_ar : job?.title_en}
          </h2>
          
          {job?.description && (
            <p className="text-slate-600 text-sm mb-4 leading-relaxed">{job.description}</p>
          )}
          
          <div className="flex flex-wrap gap-3 text-sm">
            {job?.location && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 rounded-full text-slate-600">
                <MapPin size={14} />
                {job.location}
              </span>
            )}
            {job?.contract_type && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 rounded-full text-blue-700">
                <Clock size={14} />
                {contractTypes[job.contract_type]?.[lang] || job.contract_type}
              </span>
            )}
            {job?.experience_years > 0 && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 rounded-full text-green-700">
                {lang === 'ar' ? `${job.experience_years}+ سنوات خبرة` : `${job.experience_years}+ years exp.`}
              </span>
            )}
          </div>
        </div>
        
        {/* Application Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-lg p-6 space-y-5">
          <h3 className="font-semibold text-slate-800 border-b pb-3">
            {lang === 'ar' ? 'معلومات المتقدم' : 'Applicant Information'}
          </h3>
          
          {/* Full Name */}
          <div>
            <Label className="text-slate-700">{lang === 'ar' ? 'الاسم الكامل' : 'Full Name'} *</Label>
            <Input 
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder={lang === 'ar' ? 'أدخل اسمك الكامل' : 'Enter your full name'}
              className="mt-1"
              required
            />
          </div>
          
          {/* Email */}
          <div>
            <Label className="text-slate-700">{lang === 'ar' ? 'البريد الإلكتروني' : 'Email'} *</Label>
            <Input 
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="example@email.com"
              className="mt-1"
              dir="ltr"
              required
            />
          </div>
          
          {/* Phone */}
          <div>
            <Label className="text-slate-700">{lang === 'ar' ? 'رقم الهاتف' : 'Phone Number'} *</Label>
            <Input 
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="+966 5XX XXX XXXX"
              className="mt-1"
              dir="ltr"
              required
            />
          </div>
          
          {/* CV Upload */}
          <div>
            <Label className="text-slate-700">
              {lang === 'ar' ? 'السيرة الذاتية' : 'CV/Resume'} *
              <span className="text-xs text-slate-500 font-normal mr-2">
                ({lang === 'ar' ? 'PDF أو DOC - حد أقصى ملفين' : 'PDF or DOC - max 2 files'})
              </span>
            </Label>
            
            {/* Upload Area */}
            <div 
              className={`mt-2 border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                files.length >= 2 ? 'border-slate-200 bg-slate-50' : 'border-blue-200 hover:border-blue-400 cursor-pointer'
              }`}
              onClick={() => files.length < 2 && document.getElementById('cv-upload')?.click()}
            >
              <input 
                id="cv-upload"
                type="file"
                accept=".pdf,.doc,.docx"
                multiple
                className="hidden"
                onChange={handleFileChange}
                disabled={files.length >= 2}
              />
              <Upload className={`w-10 h-10 mx-auto mb-3 ${files.length >= 2 ? 'text-slate-300' : 'text-blue-400'}`} />
              <p className={`text-sm ${files.length >= 2 ? 'text-slate-400' : 'text-slate-600'}`}>
                {files.length >= 2 
                  ? (lang === 'ar' ? 'تم رفع الحد الأقصى من الملفات' : 'Maximum files uploaded')
                  : (lang === 'ar' ? 'اضغط لرفع السيرة الذاتية' : 'Click to upload your CV')
                }
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {lang === 'ar' ? 'سيرة عربية + سيرة إنجليزية (اختياري)' : 'Arabic CV + English CV (optional)'}
              </p>
            </div>
            
            {/* Uploaded Files */}
            {files.length > 0 && (
              <div className="mt-3 space-y-2">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                    <div className="flex items-center gap-2">
                      <FileText size={18} className="text-green-600" />
                      <span className="text-sm text-green-800 truncate max-w-[200px]">{file.name}</span>
                      <span className="text-xs text-green-600">({(file.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <button 
                      type="button"
                      onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                      className="p-1 hover:bg-green-100 rounded"
                    >
                      <X size={16} className="text-green-700" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Errors */}
          {fileErrors.length > 0 && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              {fileErrors.map((err, idx) => (
                <p key={idx} className="text-sm text-red-700 flex items-center gap-2">
                  <AlertCircle size={14} />
                  {err}
                </p>
              ))}
            </div>
          )}
          
          {/* Submit Button */}
          <Button 
            type="submit" 
            className="w-full h-12 text-base"
            disabled={submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                {lang === 'ar' ? 'جاري الإرسال...' : 'Submitting...'}
              </>
            ) : (
              <>
                <Send className="w-5 h-5 mr-2" />
                {lang === 'ar' ? 'إرسال الطلب' : 'Submit Application'}
              </>
            )}
          </Button>
          
          <p className="text-xs text-slate-400 text-center">
            {lang === 'ar' 
              ? 'بإرسال هذا النموذج، أوافق على معالجة بياناتي لغرض التوظيف'
              : 'By submitting, I agree to have my data processed for recruitment purposes'
            }
          </p>
        </form>
      </div>
    </div>
  );
}
