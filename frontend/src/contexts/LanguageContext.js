import { createContext, useContext, useState, useEffect } from 'react';
import { translations } from '@/lib/translations';

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('hr_lang') || 'ar');

  useEffect(() => {
    document.documentElement.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', lang);
    localStorage.setItem('hr_lang', lang);
  }, [lang]);

  const t = (key) => {
    const keys = key.split('.');
    let val = translations[lang];
    for (const k of keys) {
      val = val?.[k];
    }
    return val || key;
  };

  const toggleLang = () => setLang(l => l === 'en' ? 'ar' : 'en');

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
