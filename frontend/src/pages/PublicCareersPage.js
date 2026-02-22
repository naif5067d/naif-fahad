import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, MapPin, Clock, ChevronLeft, Loader2, Search } from 'lucide-react';

// Public Careers Page - List all available jobs
// Clean, white, modern design for embedding
export default function PublicCareersPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  
  // Detect language from browser
  const browserLang = navigator.language?.startsWith('ar') ? 'ar' : 'en';
  const [lang, setLang] = useState(browserLang);
  
  // Load careers
  useEffect(() => {
    const loadCareers = async () => {
      try {
        const res = await fetch(`${baseUrl}/api/ats/public/careers`);
        if (!res.ok) throw new Error('Failed to load');
        const result = await res.json();
        setData(result);
      } catch (err) {
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    
    loadCareers();
  }, [baseUrl]);
  
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
  
  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Briefcase className="w-8 h-8 text-slate-400" />
          </div>
          <h1 className="text-lg font-semibold text-slate-800 mb-2">
            {lang === 'ar' ? 'عذراً' : 'Sorry'}
          </h1>
          <p className="text-slate-500 text-sm leading-relaxed">
            {lang === 'ar' 
              ? 'حدث خطأ في تحميل الصفحة. يرجى المحاولة مرة أخرى لاحقاً.'
              : 'An error occurred while loading the page. Please try again later.'
            }
          </p>
        </div>
      </div>
    );
  }
  
  const jobs = data?.jobs || [];
  const hasJobs = jobs.length > 0;
  
  return (
    <div className="min-h-screen bg-white" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Language Toggle */}
      <div className="absolute top-3 right-3 z-50">
        <button 
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          className="px-2.5 py-1 text-xs font-medium text-slate-500 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-md transition-colors"
        >
          {lang === 'ar' ? 'EN' : 'عربي'}
        </button>
      </div>
      
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-slate-900 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Briefcase className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-900 mb-2">
            {lang === 'ar' ? 'الوظائف المتاحة' : 'Available Positions'}
          </h1>
          <p className="text-slate-500 text-sm">
            {data?.message?.[lang] || (lang === 'ar' ? 'انضم إلى فريقنا' : 'Join our team')}
          </p>
        </div>
        
        {/* No Jobs Message */}
        {!hasJobs && (
          <div className="text-center py-16">
            <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6">
              <Search className="w-10 h-10 text-slate-300" />
            </div>
            <h2 className="text-lg font-medium text-slate-700 mb-3">
              {lang === 'ar' ? 'لا توجد شواغر حالياً' : 'No Vacancies Available'}
            </h2>
            <p className="text-slate-500 text-sm max-w-sm mx-auto leading-relaxed">
              {lang === 'ar' 
                ? 'نشكرك على اهتمامك بالانضمام إلى فريقنا. لا توجد شواغر متاحة في الوقت الحالي، ولكننا ندعوك لزيارة هذه الصفحة بشكل دوري للاطلاع على الفرص الوظيفية الجديدة.'
                : 'Thank you for your interest in joining our team. There are no vacancies available at the moment, but we invite you to check back regularly for new opportunities.'
              }
            </p>
          </div>
        )}
        
        {/* Jobs List */}
        {hasJobs && (
          <div className="space-y-4">
            {jobs.map(job => (
              <div 
                key={job.id}
                onClick={() => navigate(`/apply/${job.slug}`)}
                className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 hover:shadow-sm transition-all cursor-pointer group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-900 group-hover:text-slate-700 mb-2">
                      {lang === 'ar' ? job.title_ar : job.title_en}
                    </h3>
                    
                    {job.description && (
                      <p className="text-sm text-slate-500 mb-3 line-clamp-2">{job.description}</p>
                    )}
                    
                    <div className="flex flex-wrap gap-2">
                      {job.location && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-50 rounded-md text-xs text-slate-600">
                          <MapPin size={12} className="text-slate-400" />
                          {job.location}
                        </span>
                      )}
                      {job.contract_type && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-50 rounded-md text-xs text-slate-600">
                          <Clock size={12} className="text-slate-400" />
                          {contractTypes[job.contract_type]?.[lang] || job.contract_type}
                        </span>
                      )}
                      {job.experience_years > 0 && (
                        <span className="inline-flex items-center px-2.5 py-1 bg-slate-50 rounded-md text-xs text-slate-600">
                          {lang === 'ar' ? `${job.experience_years}+ سنوات` : `${job.experience_years}+ yrs`}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex-shrink-0">
                    <ChevronLeft size={20} className={`text-slate-400 group-hover:text-slate-600 transition-colors ${lang === 'ar' ? '' : 'rotate-180'}`} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Footer */}
        {hasJobs && (
          <p className="text-center text-xs text-slate-400 mt-8">
            {lang === 'ar' 
              ? `${jobs.length} ${jobs.length === 1 ? 'وظيفة متاحة' : 'وظائف متاحة'}`
              : `${jobs.length} ${jobs.length === 1 ? 'position available' : 'positions available'}`
            }
          </p>
        )}
      </div>
    </div>
  );
}
