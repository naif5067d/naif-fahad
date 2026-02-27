import { useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useNavigate } from 'react-router-dom';
import { 
  Settings, Wrench, History, Volume2, Building2, 
  ChevronRight, Shield, Database, Users, Bell
} from 'lucide-react';

const CONTROL_ITEMS = [
  {
    id: 'systemMaintenance',
    icon: Wrench,
    path: '/system-maintenance',
    color: 'bg-blue-500',
    titleAr: 'صيانة النظام',
    titleEn: 'System Maintenance',
    descAr: 'إدارة قاعدة البيانات، التنظيف، الصيانة الدورية',
    descEn: 'Database management, cleanup, periodic maintenance'
  },
  {
    id: 'companySettings',
    icon: Building2,
    path: '/company-settings',
    color: 'bg-purple-500',
    titleAr: 'هوية الشركة',
    titleEn: 'Company Identity',
    descAr: 'اسم الشركة، الشعار، البيانات الأساسية',
    descEn: 'Company name, logo, basic information'
  },
  {
    id: 'soundSettings',
    icon: Volume2,
    path: '/sound-settings',
    color: 'bg-green-500',
    titleAr: 'إعدادات الأصوات',
    titleEn: 'Sound Settings',
    descAr: 'أصوات الإشعارات والتنبيهات',
    descEn: 'Notification and alert sounds'
  },
];

export default function ControlPanelPage() {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const isRTL = lang === 'ar';

  return (
    <div className="space-y-6" dir={isRTL ? 'rtl' : 'ltr'}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
          <Settings size={24} className="text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" data-testid="control-panel-title">
            {isRTL ? 'لوحة التحكم' : 'Control Panel'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isRTL ? 'إدارة إعدادات النظام والصيانة' : 'System settings and maintenance management'}
          </p>
        </div>
      </div>

      {/* Control Items Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {CONTROL_ITEMS.map(item => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.path)}
              className="card-premium p-5 text-start hover:shadow-lg transition-all group"
              data-testid={`control-${item.id}`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-xl ${item.color} flex items-center justify-center flex-shrink-0`}>
                  <Icon size={24} className="text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-lg group-hover:text-primary transition-colors">
                    {isRTL ? item.titleAr : item.titleEn}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isRTL ? item.descAr : item.descEn}
                  </p>
                </div>
                <ChevronRight size={20} className={`text-muted-foreground group-hover:text-primary transition-colors ${isRTL ? 'rotate-180' : ''}`} />
              </div>
            </button>
          );
        })}
      </div>

      {/* Quick Stats */}
      <div className="card-premium p-5">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Database size={18} />
          {isRTL ? 'حالة النظام' : 'System Status'}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="w-3 h-3 rounded-full bg-green-500 mx-auto mb-2 animate-pulse" />
            <p className="text-xs text-muted-foreground">{isRTL ? 'الخادم' : 'Server'}</p>
            <p className="font-semibold text-green-600">{isRTL ? 'يعمل' : 'Online'}</p>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="w-3 h-3 rounded-full bg-green-500 mx-auto mb-2 animate-pulse" />
            <p className="text-xs text-muted-foreground">{isRTL ? 'قاعدة البيانات' : 'Database'}</p>
            <p className="font-semibold text-green-600">{isRTL ? 'متصل' : 'Connected'}</p>
          </div>
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <Shield size={16} className="mx-auto mb-2 text-blue-500" />
            <p className="text-xs text-muted-foreground">{isRTL ? 'الأمان' : 'Security'}</p>
            <p className="font-semibold text-blue-600">{isRTL ? 'محمي' : 'Secure'}</p>
          </div>
          <div className="text-center p-3 bg-purple-50 rounded-lg">
            <Bell size={16} className="mx-auto mb-2 text-purple-500" />
            <p className="text-xs text-muted-foreground">{isRTL ? 'الإشعارات' : 'Notifications'}</p>
            <p className="font-semibold text-purple-600">{isRTL ? 'مفعّل' : 'Active'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
