import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2, Briefcase, MapPin, Clock, Send, User, Mail, Phone } from 'lucide-react';

// Public Apply Page - Completely isolated, no auth required
// Clean, modern, white design for embedding
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
          // Handle error without parsing JSON twice
          let errorMsg = lang === 'ar' 
            ? 'عذراً، الوظيفة التي تبحث عنها غير متاحة حالياً أو أن باب التقديم قد أُغلق.'
            : 'Sorry, the position you are looking for is not available or applications have been closed.';
          
          try {
            const errData = await res.json();
            if (errData.detail) {
              errorMsg = errData.detail[lang] || errData.detail.ar || errData.detail.en || errorMsg;
            }
          } catch {
            // If JSON parsing fails, use default message
          }
          
          throw new Error(errorMsg);
        }
        const data = await res.json();
        setJob(data);
      } catch (err) {
        setError(err.message || (lang === 'ar' 
          ? 'عذراً، حدث خطأ في تحميل بيانات الوظيفة.'
          : 'Sorry, an error occurred while loading the job details.'
        ));
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
    
    if (selectedFiles.length + files.length > 2) {
      setFileErrors([lang === 'ar' ? 'الحد الأقصى ملفين فقط' : 'Maximum 2 files allowed']);
      return;
    }
    
    const newFiles = [];
    const errors = [];
    
    for (const file of selectedFiles) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (!['pdf', 'doc', 'docx'].includes(ext)) {
        errors.push(lang === 'ar' 
          ? `${file.name}: نوع غير مدعوم. الأنواع المسموحة: PDF, DOC, DOCX` 
          : `${file.name}: Unsupported type. Allowed: PDF, DOC, DOCX`);
        continue;
      }
      
      if (file.size > 5 * 1024 * 1024) {
        errors.push(lang === 'ar' 
          ? `${file.name}: حجم كبير جداً (الحد 5MB)` 
          : `${file.name}: Too large (max 5MB)`);
        continue;
      }
      
      newFiles.push(file);
    }
    
    if (errors.length > 0) setFileErrors(errors);
    if (newFiles.length > 0) setFiles(prev => [...prev, ...newFiles].slice(0, 2));
  };
  
  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setFileErrors([]);
  };
  
  // Submit application
  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log('=== Starting form submission ===');
    
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
      
      console.log('Sending to:', `${baseUrl}/api/ats/public/apply/${slug}`);
      console.log('Files count:', files.length);
      
      const res = await fetch(`${baseUrl}/api/ats/public/apply/${slug}`, {
        method: 'POST',
        body: formData
      });
      
      console.log('Response status:', res.status);
      
      const data = await res.json();
      console.log('Response data:', data);
      
      if (!res.ok) {
        throw new Error(data.detail?.[lang] || data.detail?.en || data.detail || 'Error submitting application');
      }
      
      setSubmitted(true);
      setSubmitMessage(data.message);
    } catch (err) {
      console.error('Submit error:', err);
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
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-slate-400 mx-auto mb-4" />
          <p className="text-slate-500 text-sm">{lang === 'ar' ? 'جاري التحميل...' : 'Loading...'}</p>
        </div>
      </div>
    );
  }
  
  // Error state - Professional polite message
  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
        {/* Language Toggle */}
        <div className="absolute top-3 right-3 z-50">
          <button 
            onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
            className="px-2.5 py-1 text-xs font-medium text-slate-500 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors"
          >
            {lang === 'ar' ? 'EN' : 'عربي'}
          </button>
        </div>
        
        <div className="text-center max-w-md px-6">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-5">
            <Briefcase className="w-8 h-8 text-slate-400" />
          </div>
          <h1 className="text-xl font-semibold text-slate-800 mb-3">
            {lang === 'ar' ? 'الوظيفة غير متاحة' : 'Position Not Available'}
          </h1>
          <p className="text-slate-500 text-sm leading-relaxed mb-6">{error}</p>
          <p className="text-slate-400 text-xs">
            {lang === 'ar' 
              ? 'ندعوك لزيارة صفحة الوظائف للاطلاع على الفرص المتاحة الأخرى.'
              : 'We invite you to visit our careers page to explore other available opportunities.'
            }
          </p>
        </div>
      </div>
    );
  }
  
  // Success state
  if (submitted) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-emerald-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-emerald-500" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-800 mb-3">
            {lang === 'ar' ? 'تم الإرسال بنجاح!' : 'Successfully Submitted!'}
          </h1>
          <p className="text-slate-500 leading-relaxed">
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
    <div className="min-h-screen bg-white" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Language Toggle - Minimal */}
      <div className="absolute top-3 right-3 z-50">
        <button 
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          className="px-2.5 py-1 text-xs font-medium text-slate-500 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors"
        >
          {lang === 'ar' ? 'EN' : 'عربي'}
        </button>
      </div>
      
      <div className="max-w-lg mx-auto px-4 py-8">
        {/* Job Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-slate-900 rounded-xl flex items-center justify-center flex-shrink-0">
              <Briefcase className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">
                {lang === 'ar' ? job?.title_ar : job?.title_en}
              </h1>
              <p className="text-sm text-slate-500">
                {lang === 'ar' ? 'التقديم على الوظيفة' : 'Job Application'}
              </p>
            </div>
          </div>
          
          {/* Job Details Pills */}
          <div className="flex flex-wrap gap-2">
            {job?.location && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-lg text-sm text-slate-600 border border-slate-100">
                <MapPin size={14} className="text-slate-400" />
                {job.location}
              </span>
            )}
            {job?.contract_type && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-lg text-sm text-slate-600 border border-slate-100">
                <Clock size={14} className="text-slate-400" />
                {contractTypes[job.contract_type]?.[lang] || job.contract_type}
              </span>
            )}
            {job?.experience_years > 0 && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-lg text-sm text-slate-600 border border-slate-100">
                {lang === 'ar' ? `${job.experience_years}+ سنوات` : `${job.experience_years}+ yrs`}
              </span>
            )}
          </div>
          
          {job?.description && (
            <p className="mt-4 text-sm text-slate-600 leading-relaxed">{job.description}</p>
          )}
        </div>
        
        {/* Divider */}
        <div className="border-t border-slate-100 mb-6"></div>
        
        {/* Application Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Full Name */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <User size={14} className="text-slate-400" />
              {lang === 'ar' ? 'الاسم الكامل' : 'Full Name'}
            </label>
            <input 
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder={lang === 'ar' ? 'أدخل اسمك الكامل' : 'Enter your full name'}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent transition-all"
              required
            />
          </div>
          
          {/* Email */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <Mail size={14} className="text-slate-400" />
              {lang === 'ar' ? 'البريد الإلكتروني' : 'Email'}
            </label>
            <input 
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="example@email.com"
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent transition-all"
              dir="ltr"
              required
            />
          </div>
          
          {/* Phone */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <Phone size={14} className="text-slate-400" />
              {lang === 'ar' ? 'رقم الهاتف' : 'Phone Number'}
            </label>
            <input 
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="+966 5XX XXX XXXX"
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent transition-all"
              dir="ltr"
              required
            />
          </div>
          
          {/* CV Upload */}
          <div>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700 mb-2">
              <FileText size={14} className="text-slate-400" />
              {lang === 'ar' ? 'السيرة الذاتية' : 'CV / Resume'}
              <span className="text-xs text-slate-400 font-normal">
                ({lang === 'ar' ? 'PDF أو DOC' : 'PDF or DOC'})
              </span>
            </label>
            
            {/* Upload Area */}
            <div 
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer ${
                files.length >= 2 
                  ? 'border-slate-200 bg-slate-50 cursor-not-allowed' 
                  : 'border-slate-200 hover:border-slate-400 hover:bg-slate-50'
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
              <Upload className={`w-8 h-8 mx-auto mb-2 ${files.length >= 2 ? 'text-slate-300' : 'text-slate-400'}`} />
              <p className={`text-sm ${files.length >= 2 ? 'text-slate-400' : 'text-slate-600'}`}>
                {files.length >= 2 
                  ? (lang === 'ar' ? 'تم رفع الحد الأقصى' : 'Maximum files uploaded')
                  : (lang === 'ar' ? 'اضغط لرفع الملفات' : 'Click to upload')
                }
              </p>
              <p className="text-xs text-slate-400 mt-1">
                {lang === 'ar' ? 'حد أقصى ملفين • 5MB لكل ملف' : 'Max 2 files • 5MB each'}
              </p>
            </div>
            
            {/* Uploaded Files */}
            {files.length > 0 && (
              <div className="mt-3 space-y-2">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText size={16} className="text-emerald-600 flex-shrink-0" />
                      <span className="text-sm text-emerald-800 truncate">{file.name}</span>
                      <span className="text-xs text-emerald-500 flex-shrink-0">({(file.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <button 
                      type="button"
                      onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                      className="p-1.5 hover:bg-emerald-100 rounded-lg transition-colors flex-shrink-0"
                    >
                      <X size={14} className="text-emerald-700" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Errors */}
          {fileErrors.length > 0 && (
            <div className="p-3 bg-red-50 border border-red-100 rounded-xl">
              {fileErrors.map((err, idx) => (
                <p key={idx} className="text-sm text-red-600 flex items-center gap-2">
                  <AlertCircle size={14} />
                  {err}
                </p>
              ))}
            </div>
          )}
          
          {/* Submit Button */}
          <button 
            type="submit" 
            disabled={submitting}
            className="w-full py-3.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-400 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {lang === 'ar' ? 'جاري الإرسال...' : 'Submitting...'}
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                {lang === 'ar' ? 'إرسال الطلب' : 'Submit Application'}
              </>
            )}
          </button>
          
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
