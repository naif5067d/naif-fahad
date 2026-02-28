/**
 * MobileDataView - عرض البيانات بشكل مناسب للجوال
 * يعرض الجداول كـ cards على الشاشات الصغيرة
 * وجدول عادي على الشاشات الكبيرة
 */
import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, ChevronLeft } from 'lucide-react';

// Hook لكشف حجم الشاشة
export function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < breakpoint);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [breakpoint]);

  return isMobile;
}

// Component للصف القابل للنقر
export function MobileCard({ 
  children, 
  onClick, 
  expanded = false,
  expandable = true,
  className = '',
  statusColor = 'bg-muted',
  ...props 
}) {
  const [isExpanded, setIsExpanded] = useState(expanded);

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (expandable) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div 
      className={`
        bg-card border border-border rounded-xl mb-2 overflow-hidden
        active:bg-muted/50 transition-colors cursor-pointer
        ${className}
      `}
      onClick={handleClick}
      {...props}
    >
      {/* شريط الحالة الملون */}
      <div className={`h-1 ${statusColor}`} />
      
      <div className="p-3">
        {children}
      </div>
      
      {/* سهم التوسيع */}
      {expandable && !onClick && (
        <div className="flex justify-center pb-2 text-muted-foreground">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      )}
    </div>
  );
}

// Component للصف في الـ card
export function MobileCardRow({ label, value, icon: Icon, className = '' }) {
  return (
    <div className={`flex items-center justify-between py-1.5 ${className}`}>
      <span className="text-xs text-muted-foreground flex items-center gap-1.5">
        {Icon && <Icon size={12} />}
        {label}
      </span>
      <span className="text-sm font-medium">{value || '-'}</span>
    </div>
  );
}

// Component لهيدر الـ card
export function MobileCardHeader({ 
  title, 
  subtitle, 
  badge, 
  badgeColor = 'bg-primary',
  icon: Icon,
  iconColor = 'text-primary'
}) {
  return (
    <div className="flex items-start justify-between mb-2">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {Icon && (
          <div className={`w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0 ${iconColor}`}>
            <Icon size={16} />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm truncate">{title}</p>
          {subtitle && <p className="text-xs text-muted-foreground truncate">{subtitle}</p>}
        </div>
      </div>
      {badge && (
        <span className={`text-[10px] px-2 py-0.5 rounded-full text-white flex-shrink-0 ${badgeColor}`}>
          {badge}
        </span>
      )}
    </div>
  );
}

// Component لعرض قائمة cards
export function MobileCardList({ children, className = '' }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {children}
    </div>
  );
}

// Component للتبديل بين الجدول والـ cards
export function ResponsiveDataView({
  data = [],
  tableView,
  cardView,
  emptyMessage = 'لا توجد بيانات',
  loading = false,
  loadingComponent
}) {
  const isMobile = useIsMobile();

  if (loading) {
    return loadingComponent || (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  // على الجوال: عرض cards
  if (isMobile) {
    return (
      <MobileCardList>
        {data.map((item, index) => cardView(item, index))}
      </MobileCardList>
    );
  }

  // على الشاشات الكبيرة: عرض جدول
  return tableView(data);
}

// Component للصف القابل للنقر في الجدول (للشاشات الكبيرة)
export function ClickableTableRow({ children, onClick, className = '' }) {
  return (
    <tr 
      className={`border-b hover:bg-muted/50 cursor-pointer active:bg-muted/70 transition-colors ${className}`}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

// Component للقائمة القابلة للسحب (Pull to refresh style)
export function MobileList({ 
  items, 
  renderItem, 
  onItemClick,
  keyExtractor,
  emptyMessage = 'لا توجد عناصر',
  className = ''
}) {
  const isMobile = useIsMobile();

  if (!items || items.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {items.map((item, index) => (
        <div 
          key={keyExtractor ? keyExtractor(item, index) : index}
          onClick={() => onItemClick?.(item, index)}
          className={onItemClick ? 'cursor-pointer' : ''}
        >
          {renderItem(item, index, isMobile)}
        </div>
      ))}
    </div>
  );
}

// Status colors helper
export const STATUS_CARD_COLORS = {
  'PRESENT': 'bg-green-500',
  'ABSENT': 'bg-red-500',
  'LATE': 'bg-amber-500',
  'ON_LEAVE': 'bg-blue-500',
  'ON_ADMIN_LEAVE': 'bg-blue-400',
  'GIFT_LEAVE': 'bg-emerald-500',
  'EXEMPTED': 'bg-teal-500',
  'WEEKEND': 'bg-slate-400',
  'HOLIDAY': 'bg-purple-500',
  'ON_MISSION': 'bg-indigo-500',
  'NOT_REGISTERED': 'bg-slate-300',
  'UNKNOWN': 'bg-slate-300',
  'NOT_PROCESSED': 'bg-amber-400',
  'PERMISSION': 'bg-cyan-500',
  'pending': 'bg-amber-500',
  'approved': 'bg-green-500',
  'rejected': 'bg-red-500',
  'completed': 'bg-green-500',
  'active': 'bg-green-500',
  'inactive': 'bg-slate-400',
  'suspended': 'bg-red-500'
};

export default {
  useIsMobile,
  MobileCard,
  MobileCardRow,
  MobileCardHeader,
  MobileCardList,
  ResponsiveDataView,
  ClickableTableRow,
  MobileList,
  STATUS_CARD_COLORS
};
