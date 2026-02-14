import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Upload, Trash2, Save, Loader2, Building2, Image as ImageIcon } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function CompanySettingsPage() {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [settings, setSettings] = useState({
    company_name_en: '',
    company_name_ar: '',
    slogan_en: '',
    slogan_ar: '',
    logo_data: null,
  });

  // Check if user is STAS
  useEffect(() => {
    if (user && user.role !== 'stas') {
      toast.error(lang === 'ar' ? 'غير مصرح لك بالوصول لهذه الصفحة' : 'You are not authorized to access this page');
      navigate('/dashboard');
    }
  }, [user, navigate, lang]);

  // Fetch current settings
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await api.get('/api/settings/branding');
        setSettings({
          company_name_en: res.data.company_name_en || '',
          company_name_ar: res.data.company_name_ar || '',
          slogan_en: res.data.slogan_en || '',
          slogan_ar: res.data.slogan_ar || '',
          logo_data: res.data.logo_data || null,
        });
      } catch (err) {
        console.error('Failed to fetch settings:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/api/settings/branding', {
        company_name_en: settings.company_name_en,
        company_name_ar: settings.company_name_ar,
        slogan_en: settings.slogan_en,
        slogan_ar: settings.slogan_ar,
      });
      toast.success(lang === 'ar' ? 'تم حفظ الإعدادات بنجاح' : 'Settings saved successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل حفظ الإعدادات' : 'Failed to save settings'));
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error(lang === 'ar' ? 'يرجى اختيار ملف صورة' : 'Please select an image file');
      return;
    }

    setUploadingLogo(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await api.post('/api/settings/branding/logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // Refresh settings to get new logo
      const settingsRes = await api.get('/api/settings/branding');
      setSettings(prev => ({
        ...prev,
        logo_data: settingsRes.data.logo_data,
      }));

      toast.success(lang === 'ar' ? 'تم رفع الشعار بنجاح' : 'Logo uploaded successfully');
    } catch (err) {
      toast.error(err.response?.data?.detail || (lang === 'ar' ? 'فشل رفع الشعار' : 'Failed to upload logo'));
    } finally {
      setUploadingLogo(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteLogo = async () => {
    if (!window.confirm(lang === 'ar' ? 'هل تريد حذف الشعار؟' : 'Delete logo?')) return;

    try {
      await api.delete('/api/settings/branding/logo');
      setSettings(prev => ({ ...prev, logo_data: null }));
      toast.success(lang === 'ar' ? 'تم حذف الشعار' : 'Logo deleted');
    } catch (err) {
      toast.error(lang === 'ar' ? 'فشل حذف الشعار' : 'Failed to delete logo');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto" data-testid="company-settings-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/dashboard')}
          className="rounded-xl"
          data-testid="back-btn"
        >
          <ArrowLeft size={20} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">
            {lang === 'ar' ? 'إعدادات الشركة' : 'Company Settings'}
          </h1>
          <p className="text-muted-foreground">
            {lang === 'ar' ? 'إدارة الشعار والعلامة التجارية' : 'Manage logo and branding'}
          </p>
        </div>
      </div>

      {/* Logo Section */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon size={20} className="text-primary" />
            {lang === 'ar' ? 'شعار الشركة' : 'Company Logo'}
          </CardTitle>
          <CardDescription>
            {lang === 'ar' 
              ? 'سيظهر الشعار في جميع المستندات والتقارير'
              : 'The logo will appear on all documents and reports'
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Logo Preview */}
          <div className="flex items-center gap-6">
            <div className="w-32 h-32 rounded-xl border-2 border-dashed border-border flex items-center justify-center bg-muted/30 overflow-hidden">
              {settings.logo_data ? (
                <img 
                  src={settings.logo_data} 
                  alt="Company Logo" 
                  className="max-w-full max-h-full object-contain"
                  data-testid="logo-preview"
                />
              ) : (
                <Building2 size={40} className="text-muted-foreground/40" />
              )}
            </div>
            
            <div className="flex flex-col gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleLogoUpload}
                className="hidden"
                data-testid="logo-input"
              />
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingLogo}
                className="rounded-xl"
                data-testid="upload-logo-btn"
              >
                {uploadingLogo ? (
                  <Loader2 size={16} className="animate-spin me-2" />
                ) : (
                  <Upload size={16} className="me-2" />
                )}
                {lang === 'ar' ? 'رفع شعار' : 'Upload Logo'}
              </Button>
              
              {settings.logo_data && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDeleteLogo}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  data-testid="delete-logo-btn"
                >
                  <Trash2 size={14} className="me-2" />
                  {lang === 'ar' ? 'حذف الشعار' : 'Delete Logo'}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Company Name & Slogan */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 size={20} className="text-primary" />
            {lang === 'ar' ? 'معلومات الشركة' : 'Company Information'}
          </CardTitle>
          <CardDescription>
            {lang === 'ar'
              ? 'أدخل اسم الشركة والشعار باللغتين'
              : 'Enter company name and slogan in both languages'
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Arabic Fields */}
          <div className="space-y-4 p-4 bg-muted/30 rounded-xl">
            <h3 className="font-semibold text-sm text-muted-foreground">
              {lang === 'ar' ? 'العربية' : 'Arabic'}
            </h3>
            <div className="space-y-2">
              <Label htmlFor="company_name_ar">
                {lang === 'ar' ? 'اسم الشركة (عربي)' : 'Company Name (Arabic)'}
              </Label>
              <Input
                id="company_name_ar"
                value={settings.company_name_ar}
                onChange={(e) => setSettings(prev => ({ ...prev, company_name_ar: e.target.value }))}
                placeholder="شركة دار الكود للاستشارات الهندسية"
                className="h-11 rounded-xl text-right"
                dir="rtl"
                data-testid="company-name-ar"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="slogan_ar">
                {lang === 'ar' ? 'الشعار (عربي)' : 'Slogan (Arabic)'}
              </Label>
              <Input
                id="slogan_ar"
                value={settings.slogan_ar}
                onChange={(e) => setSettings(prev => ({ ...prev, slogan_ar: e.target.value }))}
                placeholder="التميز الهندسي"
                className="h-11 rounded-xl text-right"
                dir="rtl"
                data-testid="slogan-ar"
              />
            </div>
          </div>

          {/* English Fields */}
          <div className="space-y-4 p-4 bg-muted/30 rounded-xl">
            <h3 className="font-semibold text-sm text-muted-foreground">
              {lang === 'ar' ? 'الإنجليزية' : 'English'}
            </h3>
            <div className="space-y-2">
              <Label htmlFor="company_name_en">
                {lang === 'ar' ? 'اسم الشركة (إنجليزي)' : 'Company Name (English)'}
              </Label>
              <Input
                id="company_name_en"
                value={settings.company_name_en}
                onChange={(e) => setSettings(prev => ({ ...prev, company_name_en: e.target.value }))}
                placeholder="DAR AL CODE ENGINEERING CONSULTANCY"
                className="h-11 rounded-xl"
                data-testid="company-name-en"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="slogan_en">
                {lang === 'ar' ? 'الشعار (إنجليزي)' : 'Slogan (English)'}
              </Label>
              <Input
                id="slogan_en"
                value={settings.slogan_en}
                onChange={(e) => setSettings(prev => ({ ...prev, slogan_en: e.target.value }))}
                placeholder="Engineering Excellence"
                className="h-11 rounded-xl"
                data-testid="slogan-en"
              />
            </div>
          </div>

          {/* Save Button */}
          <Button
            onClick={handleSave}
            disabled={saving}
            className="w-full h-12 rounded-xl text-base font-semibold"
            data-testid="save-settings-btn"
          >
            {saving ? (
              <Loader2 size={18} className="animate-spin me-2" />
            ) : (
              <Save size={18} className="me-2" />
            )}
            {lang === 'ar' ? 'حفظ الإعدادات' : 'Save Settings'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
