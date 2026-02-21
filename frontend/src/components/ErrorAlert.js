// Error Display Component for DAR AL CODE HR OS
// مكون عرض الأخطاء الموحد

import { AlertTriangle, Copy, CheckCircle } from 'lucide-react';
import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';

/**
 * عرض رسالة خطأ موحدة
 * @param {Object} error - كائن الخطأ من الـ API
 * @param {Function} onDismiss - دالة إغلاق الخطأ
 */
export function ErrorAlert({ error, onDismiss }) {
  const { lang } = useLanguage();
  const [copied, setCopied] = useState(false);

  if (!error) return null;

  // Handle different error formats
  const errorData = error.detail || error;
  const errorCode = errorData.error_code || 'E9999';
  const errorId = errorData.error_id || '';
  const message = lang === 'ar' ? errorData.message_ar : errorData.message;
  const details = lang === 'ar' ? errorData.details_ar : errorData.details;
  const supportMessage = lang === 'ar' ? errorData.support_message_ar : errorData.support_message;

  const copyErrorId = () => {
    if (errorId) {
      navigator.clipboard.writeText(errorId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
        </div>
        <div className="flex-1">
          {/* Error Code & ID */}
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 text-xs font-mono rounded">
              {errorCode}
            </span>
            {errorId && (
              <button
                onClick={copyErrorId}
                className="flex items-center gap-1 px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs font-mono rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                title={lang === 'ar' ? 'نسخ رقم المرجع' : 'Copy reference number'}
              >
                {copied ? (
                  <CheckCircle className="w-3 h-3 text-green-500" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
                <span className="truncate max-w-[120px]">{errorId}</span>
              </button>
            )}
          </div>

          {/* Message */}
          <p className="text-red-800 dark:text-red-200 font-medium">
            {message || (lang === 'ar' ? 'حدث خطأ' : 'An error occurred')}
          </p>

          {/* Details */}
          {details && (
            <p className="text-red-600 dark:text-red-400 text-sm mt-1">
              {details}
            </p>
          )}

          {/* Support Message */}
          {supportMessage && (
            <p className="text-red-500 dark:text-red-500 text-xs mt-2 opacity-80">
              {supportMessage}
            </p>
          )}
        </div>

        {/* Dismiss Button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-400 hover:text-red-600 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * عرض رسالة خطأ بسيطة
 */
export function SimpleError({ code, message, messageAr }) {
  const { lang } = useLanguage();
  
  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400">
      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
      <span className="text-sm">
        <span className="font-mono text-xs bg-red-100 dark:bg-red-900 px-1 rounded me-2">{code}</span>
        {lang === 'ar' ? messageAr : message}
      </span>
    </div>
  );
}

/**
 * تحويل خطأ API إلى نص للعرض في toast
 */
export function formatErrorForToast(error, lang = 'ar') {
  const errorData = error?.response?.data?.detail || error?.response?.data || error;
  
  if (typeof errorData === 'string') {
    return errorData;
  }
  
  const code = errorData.error_code || 'E9999';
  const message = lang === 'ar' ? errorData.message_ar : errorData.message;
  const errorId = errorData.error_id ? ` | Ref: ${errorData.error_id.slice(-10)}` : '';
  
  return `[${code}] ${message || 'Unknown error'}${errorId}`;
}

export default ErrorAlert;
