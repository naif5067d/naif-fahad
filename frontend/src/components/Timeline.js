/**
 * Professional Timeline Component
 * Clean, readable, and visually appealing timeline for transactions
 */
import { useLanguage } from '@/contexts/LanguageContext';
import { formatSaudiDateTime } from '@/lib/dateUtils';
import { CheckCircle2, XCircle, Circle, Clock, ArrowUpCircle } from 'lucide-react';

const EVENT_CONFIG = {
  created: {
    icon: Circle,
    color: 'bg-slate-400',
    labelEn: 'Created',
    labelAr: 'تم الإنشاء',
  },
  approved: {
    icon: CheckCircle2,
    color: 'bg-emerald-500',
    labelEn: 'Approved',
    labelAr: 'تمت الموافقة',
  },
  rejected: {
    icon: XCircle,
    color: 'bg-red-500',
    labelEn: 'Rejected',
    labelAr: 'تم الرفض',
  },
  executed: {
    icon: CheckCircle2,
    color: 'bg-violet-600',
    labelEn: 'Executed',
    labelAr: 'تم التنفيذ',
  },
  escalated: {
    icon: ArrowUpCircle,
    color: 'bg-orange-500',
    labelEn: 'Escalated',
    labelAr: 'تم التصعيد',
  },
  pending: {
    icon: Clock,
    color: 'bg-blue-400',
    labelEn: 'Pending',
    labelAr: 'معلق',
  },
};

export default function Timeline({ events = [], className = '' }) {
  const { lang } = useLanguage();
  
  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {lang === 'ar' ? 'لا توجد أحداث' : 'No events'}
      </div>
    );
  }
  
  return (
    <div className={`relative ${className}`}>
      {/* Vertical line */}
      <div className="absolute top-0 bottom-0 start-[19px] w-[2px] bg-gradient-to-b from-primary/40 via-border to-border" />
      
      <div className="space-y-1">
        {events.map((event, index) => {
          const config = EVENT_CONFIG[event.event] || EVENT_CONFIG.pending;
          const Icon = config.icon;
          const isLast = index === events.length - 1;
          const isFirst = index === 0;
          
          // Get actor name - handle STAS specially
          let actorName = event.actor_name || '';
          if (actorName.toLowerCase() === 'stas' || event.actor === 'stas') {
            actorName = lang === 'ar' ? 'ستاس' : 'STAS';
          }
          
          // Get event label
          const eventLabel = lang === 'ar' ? config.labelAr : config.labelEn;
          
          return (
            <div 
              key={index} 
              className={`relative flex gap-4 ${isLast ? 'pb-0' : 'pb-5'}`}
              data-testid={`timeline-event-${index}`}
            >
              {/* Dot/Icon */}
              <div className={`relative z-10 flex-shrink-0 ${isFirst ? 'mt-0' : 'mt-0.5'}`}>
                <div 
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${config.color} shadow-sm`}
                >
                  <Icon size={18} className="text-white" strokeWidth={2.5} />
                </div>
              </div>
              
              {/* Content */}
              <div className="flex-1 min-w-0 pt-1">
                {/* Event name & Time - same row */}
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h4 className="text-base font-semibold text-foreground">
                    {eventLabel}
                  </h4>
                  <time className="text-xs text-muted-foreground font-mono whitespace-nowrap">
                    {formatSaudiDateTime(event.timestamp)}
                  </time>
                </div>
                
                {/* Actor */}
                {actorName && (
                  <p className="text-sm text-muted-foreground mb-1">
                    {lang === 'ar' ? 'بواسطة' : 'By'}: <span className="font-medium text-foreground">{actorName}</span>
                  </p>
                )}
                
                {/* Note */}
                {event.note && (
                  <p className="text-sm text-muted-foreground/80 mt-2 bg-muted/40 rounded-lg px-3 py-2 border-s-2 border-primary/30">
                    {event.note}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
