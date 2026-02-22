import { useState, useEffect } from 'react';
import { Briefcase, MapPin, ArrowLeft } from 'lucide-react';

// Lightweight Embed Apply Page for iframe - Direct job application
export default function EmbedApplyPage() {
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Form state
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [files, setFiles] = useState([]);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  const browserLang = navigator.language?.startsWith('ar') ? 'ar' : 'en';
  const [lang, setLang] = useState(browserLang);
  
  // Get slug from URL
  const slug = window.location.pathname.split('/').pop();
  
  useEffect(() => {
    if (!slug) {
      setError(lang === 'ar' ? 'رابط غير صحيح' : 'Invalid URL');
      setLoading(false);
      return;
    }
    
    fetch(`${baseUrl}/api/ats/public/jobs/${slug}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then(data => {
        setJob(data);
        setLoading(false);
      })
      .catch(err => {
        setError(lang === 'ar' ? 'الوظيفة غير متاحة' : 'Job not available');
        setLoading(false);
      });
  }, [baseUrl, slug, lang]);
  
  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length > 2) {
      setFormError(lang === 'ar' ? 'الحد الأقصى ملفين' : 'Maximum 2 files');
      return;
    }
    setFiles(selectedFiles.slice(0, 2));
    setFormError('');
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    
    if (!fullName.trim()) {
      setFormError(lang === 'ar' ? 'أدخل الاسم' : 'Enter name');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setFormError(lang === 'ar' ? 'أدخل بريد صحيح' : 'Enter valid email');
      return;
    }
    if (!phone.trim()) {
      setFormError(lang === 'ar' ? 'أدخل رقم الهاتف' : 'Enter phone');
      return;
    }
    if (files.length === 0) {
      setFormError(lang === 'ar' ? 'ارفع السيرة الذاتية' : 'Upload CV');
      return;
    }
    
    setSubmitting(true);
    
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
        throw new Error(data.detail?.[lang] || data.detail?.en || data.detail || 'Error');
      }
      
      setSubmitted(true);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  };
  
  // Common styles
  const pageStyle = {
    minHeight: '100vh',
    background: '#fff',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    direction: lang === 'ar' ? 'rtl' : 'ltr'
  };
  
  const centerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh'
  };
  
  if (loading) {
    return (
      <div style={{ ...pageStyle, ...centerStyle }}>
        <div style={{ textAlign: 'center', color: '#64748b' }}>
          {lang === 'ar' ? 'جاري التحميل...' : 'Loading...'}
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={{ ...pageStyle, ...centerStyle }}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Briefcase size={48} color="#cbd5e1" style={{ marginBottom: '16px' }} />
          <p style={{ color: '#64748b' }}>{error}</p>
        </div>
      </div>
    );
  }
  
  if (submitted) {
    return (
      <div style={{ ...pageStyle, ...centerStyle }}>
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
            fontSize: '40px',
            color: '#16a34a'
          }}>
            ✓
          </div>
          <h2 style={{ color: '#0f172a', marginBottom: '12px', fontSize: '24px' }}>
            {lang === 'ar' ? 'تم الإرسال بنجاح!' : 'Successfully Submitted!'}
          </h2>
          <p style={{ color: '#64748b' }}>
            {lang === 'ar' 
              ? 'شكراً، سيتم التواصل معك قريباً.'
              : 'Thank you, we will contact you soon.'}
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div style={pageStyle}>
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
      
      <div style={{ maxWidth: '500px', margin: '0 auto', padding: '40px 20px' }}>
        {/* Job Header */}
        <div style={{ marginBottom: '30px', textAlign: 'center' }}>
          <div style={{
            width: '56px',
            height: '56px',
            background: '#0f172a',
            borderRadius: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <Briefcase size={28} color="#fff" />
          </div>
          <h1 style={{ fontSize: '22px', color: '#0f172a', margin: '0 0 8px' }}>
            {lang === 'ar' ? job?.title_ar : job?.title_en}
          </h1>
          {job?.location && (
            <p style={{ 
              color: '#64748b', 
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              margin: 0
            }}>
              <MapPin size={14} /> {job.location}
            </p>
          )}
        </div>
        
        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151', fontWeight: '500' }}>
              {lang === 'ar' ? 'الاسم الكامل' : 'Full Name'} *
            </label>
            <input
              type="text"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder={lang === 'ar' ? 'أدخل اسمك الكامل' : 'Enter your full name'}
              style={{
                width: '100%',
                padding: '14px',
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                fontSize: '15px',
                boxSizing: 'border-box',
                outline: 'none'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151', fontWeight: '500' }}>
              {lang === 'ar' ? 'البريد الإلكتروني' : 'Email'} *
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="example@email.com"
              dir="ltr"
              style={{
                width: '100%',
                padding: '14px',
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                fontSize: '15px',
                boxSizing: 'border-box',
                outline: 'none'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151', fontWeight: '500' }}>
              {lang === 'ar' ? 'رقم الهاتف' : 'Phone'} *
            </label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="+966 5XX XXX XXXX"
              dir="ltr"
              style={{
                width: '100%',
                padding: '14px',
                border: '1px solid #e2e8f0',
                borderRadius: '10px',
                fontSize: '15px',
                boxSizing: 'border-box',
                outline: 'none'
              }}
            />
          </div>
          
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '14px', color: '#374151', fontWeight: '500' }}>
              {lang === 'ar' ? 'السيرة الذاتية' : 'CV / Resume'} *
              <span style={{ fontWeight: '400', color: '#94a3b8', marginRight: '8px', marginLeft: '8px' }}>
                (PDF, DOC)
              </span>
            </label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              multiple
              onChange={handleFileChange}
              style={{
                width: '100%',
                padding: '16px',
                border: '2px dashed #e2e8f0',
                borderRadius: '10px',
                fontSize: '14px',
                boxSizing: 'border-box',
                background: '#f8fafc',
                cursor: 'pointer'
              }}
            />
            {files.length > 0 && (
              <div style={{ marginTop: '10px', fontSize: '13px', color: '#10b981' }}>
                ✓ {files.map(f => f.name).join(', ')}
              </div>
            )}
            <p style={{ fontSize: '12px', color: '#94a3b8', marginTop: '6px' }}>
              {lang === 'ar' ? 'الحد الأقصى: ملفين، 5MB لكل ملف' : 'Max: 2 files, 5MB each'}
            </p>
          </div>
          
          {formError && (
            <div style={{
              padding: '14px',
              background: '#fef2f2',
              color: '#dc2626',
              borderRadius: '10px',
              marginBottom: '20px',
              fontSize: '14px',
              textAlign: 'center'
            }}>
              {formError}
            </div>
          )}
          
          <button
            type="submit"
            disabled={submitting}
            style={{
              width: '100%',
              padding: '16px',
              background: submitting ? '#94a3b8' : '#0f172a',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: submitting ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s'
            }}
          >
            {submitting 
              ? (lang === 'ar' ? 'جاري الإرسال...' : 'Submitting...') 
              : (lang === 'ar' ? 'إرسال الطلب' : 'Submit Application')}
          </button>
          
          <p style={{ 
            fontSize: '12px', 
            color: '#94a3b8', 
            textAlign: 'center',
            marginTop: '16px'
          }}>
            {lang === 'ar' 
              ? 'بإرسال هذا النموذج، أوافق على معالجة بياناتي لغرض التوظيف'
              : 'By submitting, I agree to have my data processed for recruitment'}
          </p>
        </form>
      </div>
    </div>
  );
}
