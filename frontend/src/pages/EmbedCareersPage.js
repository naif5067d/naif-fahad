import { useState, useEffect } from 'react';
import { Briefcase, MapPin, Clock, ChevronLeft, ArrowLeft } from 'lucide-react';

// Lightweight Embed Page for iframe - No complex React features
export default function EmbedCareersPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  const browserLang = navigator.language?.startsWith('ar') ? 'ar' : 'en';
  const [lang, setLang] = useState(browserLang);
  
  useEffect(() => {
    fetch(`${baseUrl}/api/ats/public/careers`)
      .then(res => res.json())
      .then(data => {
        setJobs(data.jobs || []);
        setLoading(false);
      })
      .catch(err => {
        setError(lang === 'ar' ? 'خطأ في تحميل الوظائف' : 'Error loading jobs');
        setLoading(false);
      });
  }, [baseUrl, lang]);
  
  const contractTypes = {
    full_time: { ar: 'دوام كامل', en: 'Full Time' },
    part_time: { ar: 'دوام جزئي', en: 'Part Time' },
    contract: { ar: 'عقد مؤقت', en: 'Contract' }
  };
  
  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: '#fff', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        <div style={{ textAlign: 'center', color: '#64748b' }}>
          {lang === 'ar' ? 'جاري التحميل...' : 'Loading...'}
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: '#fff', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        <div style={{ textAlign: 'center', color: '#ef4444' }}>{error}</div>
      </div>
    );
  }
  
  // If a job is selected, show the apply form
  if (selectedJob) {
    return (
      <EmbedApplyForm 
        job={selectedJob} 
        lang={lang} 
        baseUrl={baseUrl}
        onBack={() => setSelectedJob(null)}
        contractTypes={contractTypes}
      />
    );
  }
  
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#fff',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      direction: lang === 'ar' ? 'rtl' : 'ltr'
    }}>
      {/* Language Toggle */}
      <div style={{ position: 'absolute', top: '12px', right: '12px' }}>
        <button 
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          style={{
            padding: '6px 12px',
            fontSize: '12px',
            background: '#f1f5f9',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            color: '#64748b'
          }}
        >
          {lang === 'ar' ? 'EN' : 'عربي'}
        </button>
      </div>
      
      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px 20px' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{
            width: '64px',
            height: '64px',
            background: '#0f172a',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <Briefcase size={32} color="#fff" />
          </div>
          <h1 style={{ 
            fontSize: '28px', 
            fontWeight: '700', 
            color: '#0f172a',
            margin: '0 0 8px'
          }}>
            {lang === 'ar' ? 'الوظائف المتاحة' : 'Available Positions'}
          </h1>
          <p style={{ color: '#64748b', margin: 0, fontSize: '14px' }}>
            {lang === 'ar' ? 'انضم إلى فريقنا' : 'Join our team'}
          </p>
        </div>
        
        {/* Jobs Grid */}
        {jobs.length === 0 ? (
          <div style={{ 
            textAlign: 'center', 
            padding: '60px 20px',
            background: '#f8fafc',
            borderRadius: '16px'
          }}>
            <Briefcase size={48} color="#cbd5e1" style={{ marginBottom: '16px' }} />
            <p style={{ color: '#64748b', margin: 0 }}>
              {lang === 'ar' 
                ? 'لا توجد وظائف متاحة حالياً. تابعنا للفرص القادمة.'
                : 'No positions available at this time. Check back soon.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {jobs.map(job => (
              <div 
                key={job.id}
                onClick={() => setSelectedJob(job)}
                style={{
                  padding: '24px',
                  background: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '16px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  ':hover': { borderColor: '#0f172a' }
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#0f172a'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#e2e8f0'}
              >
                <h3 style={{ 
                  fontSize: '18px', 
                  fontWeight: '600', 
                  color: '#0f172a',
                  margin: '0 0 12px'
                }}>
                  {lang === 'ar' ? job.title_ar : job.title_en}
                </h3>
                
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                  {job.location && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 10px',
                      background: '#f1f5f9',
                      borderRadius: '6px',
                      fontSize: '13px',
                      color: '#475569'
                    }}>
                      <MapPin size={14} />
                      {job.location}
                    </span>
                  )}
                  {job.contract_type && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 10px',
                      background: '#f1f5f9',
                      borderRadius: '6px',
                      fontSize: '13px',
                      color: '#475569'
                    }}>
                      <Clock size={14} />
                      {contractTypes[job.contract_type]?.[lang] || job.contract_type}
                    </span>
                  )}
                </div>
                
                {job.description && (
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#64748b', 
                    margin: 0,
                    lineHeight: '1.6'
                  }}>
                    {job.description.substring(0, 150)}...
                  </p>
                )}
                
                <div style={{ marginTop: '16px' }}>
                  <span style={{
                    display: 'inline-block',
                    padding: '8px 20px',
                    background: '#0f172a',
                    color: '#fff',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontWeight: '500'
                  }}>
                    {lang === 'ar' ? 'تقديم الآن' : 'Apply Now'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Embedded Apply Form Component
function EmbedApplyForm({ job, lang, baseUrl, onBack, contractTypes }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 2) {
      setError(lang === 'ar' ? 'الحد الأقصى ملفين' : 'Maximum 2 files');
      return;
    }
    setFiles(selectedFiles.slice(0, 2));
    setError('');
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!fullName.trim()) {
      setError(lang === 'ar' ? 'أدخل الاسم' : 'Enter name');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setError(lang === 'ar' ? 'أدخل بريد صحيح' : 'Enter valid email');
      return;
    }
    if (!phone.trim()) {
      setError(lang === 'ar' ? 'أدخل رقم الهاتف' : 'Enter phone');
      return;
    }
    if (files.length === 0) {
      setError(lang === 'ar' ? 'ارفع السيرة الذاتية' : 'Upload CV');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const formData = new FormData();
      formData.append('full_name', fullName.trim());
      formData.append('email', email.trim());
      formData.append('phone', phone.trim());
      files.forEach(file => formData.append('files', file));
      
      const res = await fetch(`${baseUrl}/api/ats/public/apply/${job.slug}`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail?.[lang] || data.detail?.en || data.detail || 'Error');
      }
      
      setSubmitted(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };
  
  if (submitted) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        direction: lang === 'ar' ? 'rtl' : 'ltr'
      }}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{
            width: '80px',
            height: '80px',
            background: '#dcfce7',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
            fontSize: '40px'
          }}>
            ✓
          </div>
          <h2 style={{ color: '#0f172a', marginBottom: '12px' }}>
            {lang === 'ar' ? 'تم الإرسال بنجاح!' : 'Successfully Submitted!'}
          </h2>
          <p style={{ color: '#64748b', marginBottom: '24px' }}>
            {lang === 'ar' 
              ? 'شكراً، سيتم التواصل معك قريباً.'
              : 'Thank you, we will contact you soon.'}
          </p>
          <button
            onClick={onBack}
            style={{
              padding: '12px 24px',
              background: '#f1f5f9',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            {lang === 'ar' ? 'عرض وظائف أخرى' : 'View Other Jobs'}
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: '#fff',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      direction: lang === 'ar' ? 'rtl' : 'ltr'
    }}>
      <div style={{ maxWidth: '500px', margin: '0 auto', padding: '30px 20px' }}>
        {/* Back Button */}
        <button
          onClick={onBack}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#64748b',
            fontSize: '14px',
            marginBottom: '20px',
            padding: 0
          }}
        >
          <ArrowLeft size={16} />
          {lang === 'ar' ? 'رجوع' : 'Back'}
        </button>
        
        {/* Job Header */}
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ fontSize: '20px', color: '#0f172a', margin: '0 0 8px' }}>
            {lang === 'ar' ? job.title_ar : job.title_en}
          </h2>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {job.location && (
              <span style={{
                fontSize: '13px',
                color: '#64748b',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <MapPin size={14} /> {job.location}
              </span>
            )}
          </div>
        </div>
        
        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>
              {lang === 'ar' ? 'الاسم الكامل' : 'Full Name'} *
            </label>
            <input
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>
              {lang === 'ar' ? 'البريد الإلكتروني' : 'Email'} *
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              dir="ltr"
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>
              {lang === 'ar' ? 'رقم الهاتف' : 'Phone'} *
            </label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              dir="ltr"
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151' }}>
              {lang === 'ar' ? 'السيرة الذاتية (PDF/DOC)' : 'CV (PDF/DOC)'} *
            </label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              multiple
              onChange={handleFileChange}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px dashed #e2e8f0',
                borderRadius: '8px',
                fontSize: '14px',
                boxSizing: 'border-box',
                background: '#f8fafc'
              }}
            />
            {files.length > 0 && (
              <div style={{ marginTop: '8px', fontSize: '13px', color: '#10b981' }}>
                {files.map(f => f.name).join(', ')}
              </div>
            )}
          </div>
          
          {error && (
            <div style={{
              padding: '12px',
              background: '#fef2f2',
              color: '#dc2626',
              borderRadius: '8px',
              marginBottom: '16px',
              fontSize: '14px'
            }}>
              {error}
            </div>
          )}
          
          <button
            type="submit"
            disabled={submitting}
            style={{
              width: '100%',
              padding: '14px',
              background: submitting ? '#94a3b8' : '#0f172a',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: submitting ? 'not-allowed' : 'pointer'
            }}
          >
            {submitting 
              ? (lang === 'ar' ? 'جاري الإرسال...' : 'Submitting...') 
              : (lang === 'ar' ? 'إرسال الطلب' : 'Submit Application')}
          </button>
        </form>
      </div>
    </div>
  );
}
