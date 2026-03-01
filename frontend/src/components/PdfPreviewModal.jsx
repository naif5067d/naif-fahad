/**
 * مكوّن معاينة وتحميل PDF
 * يحل مشكلة ERR_BLOCKED_BY_CLIENT من AdBlock
 * 
 * بدلاً من window.open الذي يُحظر، نستخدم:
 * 1. عرض PDF داخل modal (iframe)
 * 2. زر تحميل مباشر كبديل
 */
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Printer, Download, X, Loader2, ExternalLink, AlertTriangle } from 'lucide-react';

export default function PdfPreviewModal({ 
  open, 
  onClose, 
  pdfUrl, 
  title = 'معاينة PDF',
  loading = false 
}) {
  const [iframeError, setIframeError] = useState(false);
  
  const handleDownload = () => {
    if (!pdfUrl) return;
    
    // إنشاء رابط تحميل مباشر
    const link = document.createElement('a');
    link.href = pdfUrl;
    link.download = `${title.replace(/\s/g, '_')}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  const handleOpenInNewTab = () => {
    if (!pdfUrl) return;
    // محاولة فتح في تبويب جديد
    const newWindow = window.open(pdfUrl, '_blank');
    if (!newWindow || newWindow.closed) {
      // إذا فشل (بسبب AdBlock)، نحمّل مباشرة
      handleDownload();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl w-[95vw] h-[90vh] flex flex-col p-0 gap-0">
        <DialogHeader className="p-4 border-b flex-shrink-0">
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Printer className="text-[hsl(var(--navy))]" size={20} />
              {title}
            </DialogTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleOpenInNewTab}
                className="gap-1"
              >
                <ExternalLink size={14} />
                <span className="hidden sm:inline">فتح بتبويب جديد</span>
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleDownload}
                className="gap-1 bg-[hsl(var(--navy))] hover:bg-[hsl(var(--navy-dark))]"
              >
                <Download size={14} />
                <span className="hidden sm:inline">تحميل</span>
              </Button>
            </div>
          </div>
        </DialogHeader>
        
        <div className="flex-1 overflow-hidden bg-slate-100 relative">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white">
              <div className="text-center">
                <Loader2 className="w-10 h-10 animate-spin text-[hsl(var(--navy))] mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">جاري تحميل المستند...</p>
              </div>
            </div>
          ) : pdfUrl ? (
            <>
              {iframeError ? (
                <div className="absolute inset-0 flex items-center justify-center bg-white">
                  <div className="text-center p-6 max-w-md">
                    <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
                    <h3 className="font-semibold text-lg mb-2">تعذّر عرض المستند</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      قد يكون المتصفح أو إضافة AdBlock تمنع عرض الملف. 
                      يمكنك تحميل المستند مباشرة.
                    </p>
                    <Button
                      onClick={handleDownload}
                      className="gap-2 bg-[hsl(var(--navy))] hover:bg-[hsl(var(--navy-dark))]"
                    >
                      <Download size={16} />
                      تحميل المستند
                    </Button>
                  </div>
                </div>
              ) : (
                <iframe
                  src={pdfUrl}
                  className="w-full h-full border-0"
                  title={title}
                  onError={() => setIframeError(true)}
                />
              )}
            </>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="text-muted-foreground">لا يوجد مستند للعرض</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Hook لاستخدام معاينة PDF
 * يسهّل استخدام المكوّن في أي صفحة
 */
export function usePdfPreview() {
  const [pdfState, setPdfState] = useState({
    open: false,
    url: null,
    title: 'معاينة PDF',
    loading: false
  });
  
  const openPdf = async (fetchFn, title = 'معاينة PDF') => {
    setPdfState({ open: true, url: null, title, loading: true });
    
    try {
      const blob = await fetchFn();
      const url = URL.createObjectURL(blob);
      setPdfState({ open: true, url, title, loading: false });
      
      // تنظيف URL عند الإغلاق
      return () => URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error loading PDF:', error);
      setPdfState({ open: false, url: null, title, loading: false });
      throw error;
    }
  };
  
  const closePdf = () => {
    if (pdfState.url) {
      URL.revokeObjectURL(pdfState.url);
    }
    setPdfState({ open: false, url: null, title: 'معاينة PDF', loading: false });
  };
  
  return {
    pdfState,
    openPdf,
    closePdf,
    PdfModal: () => (
      <PdfPreviewModal
        open={pdfState.open}
        onClose={closePdf}
        pdfUrl={pdfState.url}
        title={pdfState.title}
        loading={pdfState.loading}
      />
    )
  };
}
