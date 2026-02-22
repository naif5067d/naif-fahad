import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, MapPin, Clock, ArrowLeft, Loader2, Building2, Users } from 'lucide-react';

// Public Careers Portal - Single embed for all jobs
// Clean, white, modern grid design
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
      <div className="min-h-[400px] bg-white flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-slate-300 mx-auto mb-3" />
          <p className="text-slate-400 text-sm">{lang === 'ar' ? 'جاري التحميل...' : 'Loading...'}</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="min-h-[400px] bg-white flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Building2 className="w-7 h-7 text-slate-300" />
          </div>
          <p className="text-slate-500 text-sm leading-relaxed">
            {lang === 'ar' 
              ? 'يرجى المحاولة مرة أخرى لاحقاً'
              : 'Please try again later'
            }
          </p>
        </div>
      </div>
    );
  }
  
  const jobs = data?.jobs || [];
  const hasJobs = jobs.length > 0;
  
  return (
    <div className="min-h-[400px] bg-white" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Language Toggle - Minimal corner */}
      <div className="absolute top-2 right-2 z-50">
        <button 
          onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')}
          className="px-2 py-0.5 text-[10px] font-medium text-slate-400 hover:text-slate-600 bg-slate-50 hover:bg-slate-100 rounded transition-colors"
        >
          {lang === 'ar' ? 'EN' : 'ع'}
        </button>
      </div>
      
      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Header - Compact */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-900 rounded-xl flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-900">
                {lang === 'ar' ? 'الوظائف المتاحة' : 'Open Positions'}
              </h1>
              {hasJobs && (
                <p className="text-xs text-slate-400">
                  {lang === 'ar' ? `${jobs.length} شاغر متاح` : `${jobs.length} position${jobs.length > 1 ? 's' : ''} available`}
                </p>
              )}
            </div>
          </div>
        </div>
        
        {/* No Jobs - Polite Message */}
        {!hasJobs && (
          <div className="text-center py-12 px-4">
            <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
              <Users className="w-8 h-8 text-slate-300" />
            </div>
            <h2 className="text-base font-medium text-slate-700 mb-2">
              {lang === 'ar' ? 'لا توجد شواغر حالياً' : 'No Open Positions'}
            </h2>
            <p className="text-slate-400 text-sm max-w-md mx-auto leading-relaxed">
              {lang === 'ar' 
                ? 'نشكرك على اهتمامك بالانضمام إلى فريقنا. لا توجد شواغر متاحة في الوقت الحالي، ولكننا ندعوك لزيارة هذه الصفحة بشكل دوري للاطلاع على الفرص الوظيفية الجديدة.'
                : 'Thank you for your interest in joining our team. There are no vacancies available at the moment. Please check back regularly for new opportunities.'
              }
            </p>
          </div>
        )}
        
        {/* Jobs Grid - 2 columns on desktop */}
        {hasJobs && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {jobs.map(job => (
              <div 
                key={job.id}
                onClick={() => navigate(`/apply/${job.slug}`)}
                className="group p-5 bg-white border border-slate-200 rounded-2xl hover:border-slate-300 hover:shadow-md transition-all cursor-pointer"
              >
                {/* Job Title */}
                <h3 className="font-semibold text-slate-900 group-hover:text-slate-700 mb-2 text-base">
                  {lang === 'ar' ? job.title_ar : job.title_en}
                </h3>
                
                {/* Description - Truncated */}
                {job.description && (
                  <p className="text-sm text-slate-500 mb-4 line-clamp-2 leading-relaxed">{job.description}</p>
                )}
                
                {/* Tags */}
                <div className="flex flex-wrap gap-2">
                  {job.location && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-50 rounded-lg text-xs text-slate-600 border border-slate-100">
                      <MapPin size={11} className="text-slate-400" />
                      {job.location}
                    </span>
                  )}
                  {job.contract_type && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-50 rounded-lg text-xs text-slate-600 border border-slate-100">
                      <Clock size={11} className="text-slate-400" />
                      {contractTypes[job.contract_type]?.[lang] || job.contract_type}
                    </span>
                  )}
                  {job.experience_years > 0 && (
                    <span className="inline-flex items-center px-2.5 py-1 bg-slate-50 rounded-lg text-xs text-slate-600 border border-slate-100">
                      {lang === 'ar' ? `${job.experience_years}+ سنة` : `${job.experience_years}+ yr`}
                    </span>
                  )}
                </div>
                
                {/* Apply Button */}
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-900 group-hover:text-slate-600 transition-colors">
                    {lang === 'ar' ? 'تقديم الآن' : 'Apply Now'}
                    <ArrowLeft size={14} className={lang === 'ar' ? '' : 'rotate-180'} />
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
