import { useState, useEffect } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MapPin, Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import api from '@/lib/api';
import { toast } from 'sonner';

export default function AttendancePage() {
  const { t, lang } = useLanguage();
  const [today, setToday] = useState({ check_in: null, check_out: null });
  const [history, setHistory] = useState([]);
  const [gpsState, setGpsState] = useState({ available: false, lat: null, lng: null, checking: true });
  const [loading, setLoading] = useState(false);

  const fetchData = () => {
    api.get('/api/attendance/today').then(r => setToday(r.data)).catch(() => {});
    api.get('/api/attendance/history').then(r => setHistory(r.data)).catch(() => {});
  };
  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        pos => setGpsState({ available: true, lat: pos.coords.latitude, lng: pos.coords.longitude, checking: false }),
        () => setGpsState({ available: false, lat: null, lng: null, checking: false }),
        { timeout: 10000 }
      );
    } else {
      setGpsState({ available: false, lat: null, lng: null, checking: false });
    }
  }, []);

  const handleCheckIn = async () => {
    setLoading(true);
    try {
      await api.post('/api/attendance/check-in', {
        latitude: gpsState.lat, longitude: gpsState.lng, gps_available: gpsState.available
      });
      toast.success(t('attendance.checkedIn'));
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Check-in failed');
    } finally { setLoading(false); }
  };

  const handleCheckOut = async () => {
    setLoading(true);
    try {
      await api.post('/api/attendance/check-out', {
        latitude: gpsState.lat, longitude: gpsState.lng, gps_available: gpsState.available
      });
      toast.success(t('attendance.checkedOut'));
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Check-out failed');
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-6" data-testid="attendance-page">
      <h1 className="text-2xl font-bold tracking-tight">{t('attendance.title')}</h1>

      {/* GPS Banner */}
      {!gpsState.checking && !gpsState.available && (
        <div className="flex items-center gap-2 p-3 rounded-md bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-sm" data-testid="no-gps-banner">
          <AlertTriangle size={16} className="text-amber-600 flex-shrink-0" />
          <span className="text-amber-800 dark:text-amber-300">
            {lang === 'ar' ? 'GPS غير متوفر - تسجيل الحضور يتطلب تحديد الموقع' : 'GPS not available - Attendance check-in requires location access'}
          </span>
        </div>
      )}

      {/* Today Status */}
      <Card className="border border-border shadow-none" data-testid="today-status-card">
        <CardHeader><CardTitle className="text-base">{t('attendance.todayStatus')}</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
              {today.check_in ? <CheckCircle size={20} className="text-emerald-500" /> : <Clock size={20} className="text-muted-foreground" />}
              <div>
                <p className="text-sm font-medium">{t('attendance.checkIn')}</p>
                <p className="text-xs text-muted-foreground">
                  {today.check_in ? today.check_in.timestamp?.slice(11, 19) : t('attendance.notCheckedIn')}
                </p>
                {today.check_in?.gps_valid === false && today.check_in?.gps_available && (
                  <p className="text-xs text-amber-600">Outside geofence ({today.check_in.distance_km} km)</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
              {today.check_out ? <CheckCircle size={20} className="text-emerald-500" /> : <XCircle size={20} className="text-muted-foreground" />}
              <div>
                <p className="text-sm font-medium">{t('attendance.checkOut')}</p>
                <p className="text-xs text-muted-foreground">
                  {today.check_out ? today.check_out.timestamp?.slice(11, 19) : '-'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex gap-3 mt-4">
            <Button
              data-testid="check-in-btn"
              onClick={handleCheckIn}
              disabled={loading || !!today.check_in || (!gpsState.available && !gpsState.checking)}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
              title={!gpsState.available ? t('attendance.gpsRequired') : ''}
            >
              <MapPin size={16} className="me-1" /> {t('attendance.checkIn')}
            </Button>
            <Button
              data-testid="check-out-btn"
              onClick={handleCheckOut}
              disabled={loading || !today.check_in || !!today.check_out}
              variant="outline"
              className="flex-1"
            >
              <Clock size={16} className="me-1" /> {t('attendance.checkOut')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* History */}
      <div>
        <h2 className="text-lg font-semibold mb-3">{t('attendance.history')}</h2>
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="hr-table" data-testid="attendance-history-table">
              <thead><tr><th>Date</th><th>Type</th><th>Time</th><th>GPS</th><th className="hidden sm:table-cell">Distance</th></tr></thead>
              <tbody>
                {history.length === 0 ? (
                  <tr><td colSpan={5} className="text-center py-8 text-muted-foreground">{t('common.noData')}</td></tr>
                ) : history.map(e => (
                  <tr key={e.id}>
                    <td className="font-mono text-xs">{e.date}</td>
                    <td className="text-sm capitalize">{e.type?.replace('_', ' ')}</td>
                    <td className="text-xs">{e.timestamp?.slice(11, 19)}</td>
                    <td>{e.gps_valid ? <CheckCircle size={14} className="text-emerald-500" /> : <XCircle size={14} className="text-red-500" />}</td>
                    <td className="hidden sm:table-cell text-xs text-muted-foreground">{e.distance_km ? `${e.distance_km} km` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
