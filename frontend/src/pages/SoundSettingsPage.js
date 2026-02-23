/**
 * صفحة إعدادات الأصوات
 * Sound Settings Page
 */
import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { 
  Volume2, Play, Check, Music, Bell, Save
} from 'lucide-react';
import { 
  WELCOME_SOUNDS, 
  NOTIFICATION_SOUNDS, 
  playWelcomeSound, 
  playNotificationSound,
  getWelcomeSoundsList,
  getNotificationSoundsList
} from '@/utils/soundLibrary';

export default function SoundSettingsPage() {
  const { lang } = useLanguage();
  const [selectedWelcome, setSelectedWelcome] = useState('dar_classic');
  const [selectedNotification, setSelectedNotification] = useState('dar_notification');
  const [saved, setSaved] = useState(false);

  // تحميل الإعدادات المحفوظة
  useEffect(() => {
    const savedWelcome = localStorage.getItem('dar_welcome_sound');
    const savedNotification = localStorage.getItem('dar_notification_sound');
    if (savedWelcome) setSelectedWelcome(savedWelcome);
    if (savedNotification) setSelectedNotification(savedNotification);
  }, []);

  // حفظ الإعدادات
  const handleSave = () => {
    localStorage.setItem('dar_welcome_sound', selectedWelcome);
    localStorage.setItem('dar_notification_sound', selectedNotification);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const welcomeSounds = getWelcomeSoundsList();
  const notificationSounds = getNotificationSoundsList();

  return (
    <div className="space-y-6 p-6" data-testid="sound-settings-page">
      {/* العنوان */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            {lang === 'ar' ? 'إعدادات الأصوات' : 'Sound Settings'}
          </h1>
          <p className="text-muted-foreground">
            {lang === 'ar' 
              ? 'اختر أصوات الترحيب والإشعارات المفضلة لديك'
              : 'Choose your preferred welcome and notification sounds'
            }
          </p>
        </div>
        <Button onClick={handleSave} className="gap-2">
          {saved ? <Check size={18} /> : <Save size={18} />}
          {saved 
            ? (lang === 'ar' ? 'تم الحفظ!' : 'Saved!') 
            : (lang === 'ar' ? 'حفظ' : 'Save')
          }
        </Button>
      </div>

      {/* أصوات الترحيب */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Music size={20} className="text-primary" />
            {lang === 'ar' ? 'أصوات الترحيب (20 نغمة)' : 'Welcome Sounds (20 tones)'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {welcomeSounds.map((sound) => (
              <div
                key={sound.key}
                className={`
                  flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all
                  ${selectedWelcome === sound.key 
                    ? 'border-primary bg-primary/10' 
                    : 'border-border hover:border-primary/50'
                  }
                `}
                onClick={() => setSelectedWelcome(sound.key)}
              >
                <div className="flex items-center gap-2">
                  {selectedWelcome === sound.key && (
                    <Check size={16} className="text-primary" />
                  )}
                  <span className="text-sm font-medium">
                    {lang === 'ar' ? sound.name_ar : sound.name_en}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    playWelcomeSound(sound.key);
                  }}
                >
                  <Play size={14} />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* أصوات الإشعارات */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell size={20} className="text-primary" />
            {lang === 'ar' ? 'أصوات الإشعارات (20 نغمة)' : 'Notification Sounds (20 tones)'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {notificationSounds.map((sound) => (
              <div
                key={sound.key}
                className={`
                  flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all
                  ${selectedNotification === sound.key 
                    ? 'border-primary bg-primary/10' 
                    : 'border-border hover:border-primary/50'
                  }
                `}
                onClick={() => setSelectedNotification(sound.key)}
              >
                <div className="flex items-center gap-2">
                  {selectedNotification === sound.key && (
                    <Check size={16} className="text-primary" />
                  )}
                  <span className="text-sm font-medium">
                    {lang === 'ar' ? sound.name_ar : sound.name_en}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    playNotificationSound(sound.key);
                  }}
                >
                  <Play size={14} />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* معاينة */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Volume2 size={20} className="text-primary" />
            {lang === 'ar' ? 'معاينة الأصوات المختارة' : 'Preview Selected Sounds'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Button 
              variant="outline" 
              className="gap-2"
              onClick={() => playWelcomeSound(selectedWelcome)}
            >
              <Music size={18} />
              {lang === 'ar' ? 'تشغيل صوت الترحيب' : 'Play Welcome Sound'}
            </Button>
            <Button 
              variant="outline" 
              className="gap-2"
              onClick={() => playNotificationSound(selectedNotification)}
            >
              <Bell size={18} />
              {lang === 'ar' ? 'تشغيل صوت الإشعار' : 'Play Notification Sound'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
