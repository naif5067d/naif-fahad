/**
 * Professional Timeline Component
 * Clean, readable, and visually appealing timeline for transactions
 * Supports both vertical and horizontal layouts
 */
import { useLanguage } from '@/contexts/LanguageContext';
import { formatSaudiDateTime } from '@/lib/dateUtils';
import { CheckCircle2, XCircle, Circle, Clock, ArrowUpCircle } from 'lucide-react';

const EVENT_CONFIG = {
  created: {
    icon: Circle,
    color: 'bg-slate-400',
    borderColor: 'border-slate-400',
    labelEn: 'Created',
    labelAr: 'تم الإنشاء',
  },
  approved: {
    icon: CheckCircle2,
    color: 'bg-[hsl(var(--success)/0.1)]0',
    borderColor: 'border-emerald-500',
    labelEn: 'Approved',
    labelAr: 'تمت الموافقة',
  },
  rejected: {
    icon: XCircle,
    color: 'bg-red-500',
    borderColor: 'border-red-500',
    labelEn: 'Rejected',
    labelAr: 'تم الرفض',
  },
  cancelled: {
    icon: XCircle,
    color: 'bg-red-500',
    borderColor: 'border-red-500',
    labelEn: 'Cancelled',
    labelAr: 'تم الإلغاء',
  },
  executed: {
    icon: CheckCircle2,
    color: 'bg-violet-600',
    borderColor: 'border-violet-600',
    labelEn: 'Executed',
    labelAr: 'تم التنفيذ',
  },
  escalated: {
    icon: ArrowUpCircle,
    color: 'bg-[hsl(var(--warning)/0.1)]0',
    borderColor: 'border-orange-500',
    labelEn: 'Escalated',
    labelAr: 'تم التصعيد',
  },
  pending: {
    icon: Clock,
    color: 'bg-blue-400',
    borderColor: 'border-blue-400',
    labelEn: 'Pending',
    labelAr: 'معلق',
  },
};

export default function Timeline({ events = [], className = '', horizontal = false }) {
  const { lang } = useLanguage();
  
  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {lang === 'ar' ? 'لا توجد أحداث' : 'No events'}
      </div>
    );
  }

  // Horizontal Timeline for mobile/tablet friendly view
  if (horizontal) {
    return (
      <div className={`relative ${className}`}>
        {/* Horizontal scrollable container */}
        <div className="flex overflow-x-auto pb-4 gap-0 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
          {events.map((event, index) => {
            const config = EVENT_CONFIG[event.event] || EVENT_CONFIG.pending;
            const Icon = config.icon;
            const isLast = index === events.length - 1;
            
            // Get actor name - handle STAS specially
            let actorName = event.actor_name || '';
            if (actorName.toLowerCase() === 'stas' || event.actor === 'stas') {
              actorName = 'STAS';
            }
            
            // Get event label
            const eventLabel = lang === 'ar' ? config.labelAr : config.labelEn;
            
            return (
              <div 
                key={index} 
                className="flex items-start flex-shrink-0"
                data-testid={`timeline-event-${index}`}
              >
                {/* Card */}
                <div className={`relative flex flex-col items-center min-w-[140px] max-w-[180px] px-2`}>
                  {/* Icon */}
                  <div 
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${config.color} shadow-md z-10`}
                  >
                    <Icon size={18} className="text-white" strokeWidth={2.5} />
                  </div>
                  
                  {/* Content Card */}
                  <div className={`mt-3 w-full p-3 rounded-xl bg-card border-2 ${config.borderColor} border-opacity-30`}>
                    <p className="text-xs font-bold text-center mb-1">{eventLabel}</p>
                    {actorName && (
                      <p className="text-[10px] text-muted-foreground text-center truncate" title={actorName}>
                        {actorName}
                      </p>
                    )}
                    <p className="text-[9px] text-muted-foreground text-center mt-1 font-mono">
                      {formatSaudiDateTime(event.timestamp)?.split(',')[0]}
                    </p>
                  </div>
                </div>
                
                {/* Connector line */}
                {!isLast && (
                  <div className="flex items-center h-10 -mx-1">
                    <div className="w-8 h-0.5 bg-gradient-to-r from-primary/40 to-border"></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  
  // Original Vertical Timeline
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
