/**
 * Date/Time utilities for Saudi Arabia timezone
 * All times displayed to users should be in Asia/Riyadh (UTC+3)
 */

const SAUDI_TIMEZONE = 'Asia/Riyadh';

/**
 * Format ISO timestamp to Saudi Arabia local time
 * @param {string} isoString - ISO format timestamp
 * @param {object} options - Formatting options
 * @returns {string} Formatted date/time string
 */
export function formatSaudiDateTime(isoString, options = {}) {
  if (!isoString) return '-';
  
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '-';
    
    const defaultOptions = {
      timeZone: SAUDI_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      ...options
    };
    
    return new Intl.DateTimeFormat('en-GB', defaultOptions).format(date);
  } catch (e) {
    console.error('Date formatting error:', e);
    return isoString?.slice(0, 16) || '-';
  }
}

/**
 * Format date only (no time) in Saudi timezone
 */
export function formatSaudiDate(isoString) {
  if (!isoString) return '-';
  
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '-';
    
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: SAUDI_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(date);
  } catch (e) {
    return isoString?.slice(0, 10) || '-';
  }
}

/**
 * Format time only in Saudi timezone
 */
export function formatSaudiTime(isoString) {
  if (!isoString) return '-';
  
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '-';
    
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: SAUDI_TIMEZONE,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date);
  } catch (e) {
    return isoString?.slice(11, 16) || '-';
  }
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(isoString, lang = 'ar') {
  if (!isoString) return '-';
  
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '-';
    
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return lang === 'ar' ? 'الآن' : 'Just now';
    if (diffMins < 60) return lang === 'ar' ? `${diffMins} دقيقة` : `${diffMins}m ago`;
    if (diffHours < 24) return lang === 'ar' ? `${diffHours} ساعة` : `${diffHours}h ago`;
    if (diffDays < 7) return lang === 'ar' ? `${diffDays} يوم` : `${diffDays}d ago`;
    
    return formatSaudiDate(isoString);
  } catch (e) {
    return '-';
  }
}

/**
 * Get current Saudi date/time
 */
export function getSaudiNow() {
  return new Date().toLocaleString('en-GB', { timeZone: SAUDI_TIMEZONE });
}

/**
 * Convert Gregorian to Hijri date (approximate)
 * @param {Date|string} date - Date to convert
 * @param {string} lang - Language for formatting
 * @returns {string} Hijri date string
 */
export function toHijri(date, lang = 'ar') {
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return '';
    
    return new Intl.DateTimeFormat(`${lang}-SA-u-ca-islamic`, {
      timeZone: SAUDI_TIMEZONE,
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(d);
  } catch (e) {
    return '';
  }
}

/**
 * تنسيق التاريخ بالميلادي (أساسي) والهجري (ثانوي)
 * Format: "2025-12-31 (1447-06-09 هـ)"
 * @param {Date|string} date - التاريخ
 * @param {object} options - خيارات التنسيق
 * @returns {object} {primary: string, secondary: string, combined: string}
 */
export function formatGregorianHijri(date, options = {}) {
  const { showTime = false, lang = 'ar' } = options;
  
  if (!date) return { primary: '-', secondary: '', combined: '-' };
  
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (isNaN(d.getTime())) return { primary: '-', secondary: '', combined: '-' };
    
    // التاريخ الميلادي (الأساسي)
    const gregorianOptions = {
      timeZone: SAUDI_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      ...(showTime && { hour: '2-digit', minute: '2-digit', hour12: false })
    };
    const gregorian = new Intl.DateTimeFormat('en-GB', gregorianOptions).format(d);
    
    // التاريخ الهجري (الثانوي) - بدون أسماء الشهور للاختصار
    const hijriOptions = {
      timeZone: SAUDI_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    };
    
    // استخدام التقويم الهجري
    let hijri = '';
    try {
      hijri = new Intl.DateTimeFormat('en-SA-u-ca-islamic-nu-latn', hijriOptions).format(d);
    } catch (e) {
      hijri = '';
    }
    
    // تنسيق النتيجة
    const secondary = hijri ? `${hijri} هـ` : '';
    const combined = hijri ? `${gregorian} (${secondary})` : gregorian;
    
    return { primary: gregorian, secondary, combined };
  } catch (e) {
    console.error('Date formatting error:', e);
    return { primary: String(date).slice(0, 10), secondary: '', combined: String(date).slice(0, 10) };
  }
}

/**
 * تنسيق التاريخ والوقت بالميلادي والهجري
 */
export function formatGregorianHijriDateTime(date, lang = 'ar') {
  return formatGregorianHijri(date, { showTime: true, lang });
}

export default {
  formatSaudiDateTime,
  formatSaudiDate,
  formatSaudiTime,
  formatRelativeTime,
  getSaudiNow,
  toHijri,
};
