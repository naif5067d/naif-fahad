/**
 * PDF Preview Modal - نافذة معاينة PDF
 * تُستخدم في جميع صفحات التطبيق للمعاينة والطباعة والتحميل
 */
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Download, Printer, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export default function PdfPreviewModal({ 
  open, 
  onClose, 
  pdfUrl, 
  fileName = 'document.pdf',
  title = 'معاينة',
  lang = 'ar'
}) {
  const handleDownload = () => {
    if (pdfUrl) {
      const link = document.createElement('a');
      link.href = pdfUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success(lang === 'ar' ? 'تم تحميل الملف' : 'File downloaded');
    }
  };

  const handlePrint = () => {
    if (pdfUrl) {
      const printWindow = window.open(pdfUrl);
      if (printWindow) {
        printWindow.onload = () => printWindow.print();
      } else {
        // إذا حُظر، حمّل مباشرة
        handleDownload();
      }
    }
  };

  const handleClose = () => {
    if (pdfUrl) {
      window.URL.revokeObjectURL(pdfUrl);
    }
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="max-w-5xl h-[90vh] p-0 overflow-hidden">
        <DialogHeader className="p-4 border-b">
          <div className="flex items-center justify-between">
            <DialogTitle>{title}</DialogTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download size={16} className="me-2" />
                {lang === 'ar' ? 'تحميل' : 'Download'}
              </Button>
              <Button variant="outline" size="sm" onClick={handlePrint}>
                <Printer size={16} className="me-2" />
                {lang === 'ar' ? 'طباعة' : 'Print'}
              </Button>
              <Button variant="ghost" size="sm" onClick={handleClose}>
                <X size={20} />
              </Button>
            </div>
          </div>
        </DialogHeader>
        <div className="flex-1 h-full bg-slate-100">
          {pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-[calc(90vh-80px)] border-0"
              title="PDF Preview"
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <Loader2 size={40} className="animate-spin text-primary" />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Helper function to open PDF
 * استخدم هذه الدالة لفتح PDF مع fallback للتحميل
 */
export async function openPdfWithFallback(response, fileName, onPreview) {
  const blob = new Blob([response.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  
  // إذا تم توفير دالة المعاينة، استخدمها
  if (onPreview) {
    onPreview(url, fileName);
    return;
  }
  
  // محاولة فتح في تبويب جديد
  const newWindow = window.open(url, '_blank');
  if (!newWindow) {
    // إذا حُظر، حمّل مباشرة
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('تم تحميل الملف');
  }
  
  // تنظيف بعد 5 ثواني
  setTimeout(() => window.URL.revokeObjectURL(url), 5000);
}
