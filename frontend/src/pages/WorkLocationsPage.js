import { useState, useEffect, useCallback, useRef } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { MapPin, Plus, Trash2, Edit2, Users, Clock, Calendar } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Circle, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '@/lib/api';
import { toast } from 'sonner';

// Fix for default marker icon in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Days of week configuration
const DAYS_CONFIG = [
  { key: 'saturday', en: 'Saturday', ar: 'السبت' },
  { key: 'sunday', en: 'Sunday', ar: 'الأحد' },
  { key: 'monday', en: 'Monday', ar: 'الإثنين' },
  { key: 'tuesday', en: 'Tuesday', ar: 'الثلاثاء' },
  { key: 'wednesday', en: 'Wednesday', ar: 'الأربعاء' },
  { key: 'thursday', en: 'Thursday', ar: 'الخميس' },
  { key: 'friday', en: 'Friday', ar: 'الجمعة' },
];

// Component to handle map click for setting location
function LocationPicker({ position, setPosition }) {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

// Component to center map when position changes
function MapCenterer({ position }) {
  const map = useMap();
  useEffect(() => {
    if (position) {
      map.setView(position, map.getZoom());
    }
  }, [position, map]);
  return null;
}

export default function WorkLocationsPage() {
  const { t, lang } = useLanguage();
  const { user } = useAuth();
  const [locations, setLocations] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    name_ar: '',
    latitude: 24.7136, // Default: Riyadh
    longitude: 46.6753,
    radius_meters: 500,
    work_start: '08:00',
    work_end: '17:00',
    work_days: {
      saturday: true,
      sunday: true,
      monday: true,
      tuesday: true,
      wednesday: true,
      thursday: true,
      friday: false,
    },
    assigned_employees: [],
  });

  const canEdit = ['sultan', 'naif', 'stas'].includes(user?.role);
  const canAssign = ['sultan', 'naif'].includes(user?.role);

  const fetchData = useCallback(async () => {
    try {
      const [locRes, empRes] = await Promise.all([
        api.get('/api/work-locations'),
        api.get('/api/employees')
      ]);
      setLocations(locRes.data.filter(l => l.is_active !== false));
      setEmployees(empRes.data);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingLocation) {
        await api.put(`/api/work-locations/${editingLocation.id}`, formData);
        toast.success(lang === 'ar' ? 'تم تحديث الموقع' : 'Location updated');
      } else {
        await api.post('/api/work-locations', formData);
        toast.success(lang === 'ar' ? 'تم إضافة الموقع' : 'Location added');
      }
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error saving location');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(lang === 'ar' ? 'هل أنت متأكد من حذف هذا الموقع؟' : 'Are you sure you want to delete this location?')) {
      return;
    }
    try {
      await api.delete(`/api/work-locations/${id}`);
      toast.success(lang === 'ar' ? 'تم حذف الموقع' : 'Location deleted');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error deleting location');
    }
  };

  const handleEdit = (location) => {
    setEditingLocation(location);
    setFormData({
      name: location.name,
      name_ar: location.name_ar,
      latitude: location.latitude,
      longitude: location.longitude,
      radius_meters: location.radius_meters,
      work_start: location.work_start,
      work_end: location.work_end,
      work_days: location.work_days,
      assigned_employees: location.assigned_employees || [],
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setEditingLocation(null);
    setFormData({
      name: '',
      name_ar: '',
      latitude: 24.7136,
      longitude: 46.6753,
      radius_meters: 500,
      work_start: '08:00',
      work_end: '17:00',
      work_days: {
        saturday: true,
        sunday: true,
        monday: true,
        tuesday: true,
        wednesday: true,
        thursday: true,
        friday: false,
      },
      assigned_employees: [],
    });
  };

  const handleEmployeeToggle = (empId) => {
    setFormData(prev => ({
      ...prev,
      assigned_employees: prev.assigned_employees.includes(empId)
        ? prev.assigned_employees.filter(id => id !== empId)
        : [...prev.assigned_employees, empId]
    }));
  };

  const handleDayToggle = (dayKey) => {
    setFormData(prev => ({
      ...prev,
      work_days: {
        ...prev.work_days,
        [dayKey]: !prev.work_days[dayKey]
      }
    }));
  };

  const getEmployeeName = (empId) => {
    const emp = employees.find(e => e.id === empId);
    if (!emp) return empId;
    return lang === 'ar' ? (emp.full_name_ar || emp.full_name) : emp.full_name;
  };

  return (
    <div className="space-y-6" data-testid="work-locations-page">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">
          {lang === 'ar' ? 'مواقع العمل' : 'Work Locations'}
        </h1>
        {canEdit && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-location-btn">
                <Plus size={16} className="me-1" />
                {lang === 'ar' ? 'إضافة موقع' : 'Add Location'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingLocation 
                    ? (lang === 'ar' ? 'تعديل موقع العمل' : 'Edit Work Location')
                    : (lang === 'ar' ? 'إضافة موقع عمل جديد' : 'Add New Work Location')
                  }
                </DialogTitle>
              </DialogHeader>
              
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Basic Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>{lang === 'ar' ? 'الاسم (إنجليزي)' : 'Name (English)'}</Label>
                    <Input
                      value={formData.name}
                      onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
                      placeholder="HQ Office"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>{lang === 'ar' ? 'الاسم (عربي)' : 'Name (Arabic)'}</Label>
                    <Input
                      value={formData.name_ar}
                      onChange={e => setFormData(p => ({ ...p, name_ar: e.target.value }))}
                      placeholder="المقر الرئيسي"
                      dir="rtl"
                      required
                    />
                  </div>
                </div>

                {/* Map */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2">
                      <MapPin size={16} />
                      {lang === 'ar' ? 'حدد الموقع على الخريطة' : 'Select Location on Map'}
                    </Label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (navigator.geolocation) {
                          navigator.geolocation.getCurrentPosition(
                            (pos) => {
                              setFormData(p => ({
                                ...p,
                                latitude: pos.coords.latitude,
                                longitude: pos.coords.longitude
                              }));
                              toast.success(lang === 'ar' ? 'تم تحديد موقعك' : 'Location set');
                            },
                            () => toast.error(lang === 'ar' ? 'فشل تحديد الموقع' : 'Failed to get location')
                          );
                        }
                      }}
                      data-testid="use-my-location-btn"
                    >
                      <MapPin size={14} className="me-1" />
                      {lang === 'ar' ? 'تحديد مكاني' : 'Use My Location'}
                    </Button>
                  </div>
                  <div className="h-64 rounded-lg overflow-hidden border border-border">
                    {dialogOpen && (
                      <MapContainer
                        key={`dialog-map-${editingLocation?.id || 'new'}-${dialogOpen}`}
                        center={[formData.latitude, formData.longitude]}
                        zoom={15}
                        style={{ height: '100%', width: '100%' }}
                      >
                        <TileLayer
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                          attribution='&copy; OpenStreetMap'
                        />
                        <LocationPicker 
                          position={[formData.latitude, formData.longitude]}
                          setPosition={([lat, lng]) => setFormData(p => ({ ...p, latitude: lat, longitude: lng }))}
                        />
                        <MapCenterer position={[formData.latitude, formData.longitude]} />
                        <Marker position={[formData.latitude, formData.longitude]} />
                        <Circle 
                          center={[formData.latitude, formData.longitude]} 
                          radius={formData.radius_meters}
                          pathOptions={{ color: '#F97316', fillColor: '#F97316', fillOpacity: 0.2 }}
                        />
                      </MapContainer>
                    )}
                  </div>
                  <div className="flex gap-4 text-sm text-muted-foreground">
                    <span>Lat: {formData.latitude.toFixed(6)}</span>
                    <span>Lng: {formData.longitude.toFixed(6)}</span>
                  </div>
                </div>

                {/* Radius */}
                <div className="space-y-2">
                  <Label>{lang === 'ar' ? 'نطاق الموقع (متر)' : 'Location Radius (meters)'}</Label>
                  <Input
                    type="number"
                    value={formData.radius_meters}
                    onChange={e => setFormData(p => ({ ...p, radius_meters: parseInt(e.target.value) || 500 }))}
                    min={50}
                    max={5000}
                  />
                  <p className="text-xs text-muted-foreground">
                    {lang === 'ar' ? 'الدائرة البرتقالية على الخريطة توضح النطاق' : 'Orange circle on map shows the radius'}
                  </p>
                </div>

                {/* Work Hours */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Clock size={16} />
                      {lang === 'ar' ? 'وقت البداية' : 'Start Time'}
                    </Label>
                    <Input
                      type="time"
                      value={formData.work_start}
                      onChange={e => setFormData(p => ({ ...p, work_start: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Clock size={16} />
                      {lang === 'ar' ? 'وقت النهاية' : 'End Time'}
                    </Label>
                    <Input
                      type="time"
                      value={formData.work_end}
                      onChange={e => setFormData(p => ({ ...p, work_end: e.target.value }))}
                    />
                  </div>
                </div>

                {/* Work Days */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Calendar size={16} />
                    {lang === 'ar' ? 'أيام العمل' : 'Work Days'}
                  </Label>
                  <div className="flex flex-wrap gap-3">
                    {DAYS_CONFIG.map(day => (
                      <label key={day.key} className="flex items-center gap-2 cursor-pointer">
                        <Checkbox
                          checked={formData.work_days[day.key]}
                          onCheckedChange={() => handleDayToggle(day.key)}
                        />
                        <span className="text-sm">{lang === 'ar' ? day.ar : day.en}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Assigned Employees */}
                {canAssign && (
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <Users size={16} />
                      {lang === 'ar' ? 'الموظفين المعينين' : 'Assigned Employees'}
                    </Label>
                    <div className="max-h-40 overflow-y-auto border border-border rounded-md p-3 space-y-2">
                      {employees.map(emp => (
                        <label key={emp.id} className="flex items-center gap-2 cursor-pointer">
                          <Checkbox
                            checked={formData.assigned_employees.includes(emp.id)}
                            onCheckedChange={() => handleEmployeeToggle(emp.id)}
                          />
                          <span className="text-sm">
                            {lang === 'ar' ? (emp.full_name_ar || emp.full_name) : emp.full_name}
                          </span>
                          <span className="text-xs text-muted-foreground">({emp.id})</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => { setDialogOpen(false); resetForm(); }}>
                    {lang === 'ar' ? 'إلغاء' : 'Cancel'}
                  </Button>
                  <Button type="submit">
                    {editingLocation 
                      ? (lang === 'ar' ? 'تحديث' : 'Update')
                      : (lang === 'ar' ? 'إضافة' : 'Add')
                    }
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Locations List */}
      {locations.length === 0 ? (
        <Card className="border border-border shadow-none">
          <CardContent className="py-12 text-center text-muted-foreground">
            <MapPin size={48} className="mx-auto mb-4 opacity-50" />
            <p>{lang === 'ar' ? 'لا توجد مواقع عمل' : 'No work locations'}</p>
            {canEdit && (
              <p className="text-sm mt-2">
                {lang === 'ar' ? 'اضغط على "إضافة موقع" للبدء' : 'Click "Add Location" to get started'}
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {locations.map(loc => (
            <Card key={loc.id} className="border border-border shadow-none" data-testid={`location-${loc.id}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <MapPin size={16} className="text-primary" />
                    {lang === 'ar' ? loc.name_ar : loc.name}
                  </span>
                  {canEdit && (
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => handleEdit(loc)}>
                        <Edit2 size={14} />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive" onClick={() => handleDelete(loc.id)}>
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Location Preview - Simple display without MapContainer to avoid conflicts */}
                <div className="h-24 rounded-md overflow-hidden border border-border bg-gradient-to-br from-slate-100 to-slate-200 flex flex-col items-center justify-center">
                  <MapPin size={24} className="text-primary mb-1" />
                  <div className="text-xs text-muted-foreground text-center">
                    <div>{loc.latitude.toFixed(4)}°, {loc.longitude.toFixed(4)}°</div>
                    <div className="text-primary font-medium">{loc.radius_meters}m</div>
                  </div>
                </div>

                {/* Info */}
                <div className="text-sm space-y-1">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock size={14} />
                    <span>{loc.work_start} - {loc.work_end}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Calendar size={14} />
                    <span className="text-xs">
                      {DAYS_CONFIG
                        .filter(d => loc.work_days?.[d.key])
                        .map(d => lang === 'ar' ? d.ar.slice(0, 2) : d.en.slice(0, 3))
                        .join(', ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Users size={14} />
                    <span>
                      {loc.assigned_employees?.length || 0} {lang === 'ar' ? 'موظف' : 'employees'}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {lang === 'ar' ? 'النطاق:' : 'Radius:'} {loc.radius_meters}m
                  </div>
                </div>

                {/* Assigned Employees */}
                {loc.assigned_employees?.length > 0 && (
                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-muted-foreground mb-1">
                      {lang === 'ar' ? 'الموظفين:' : 'Employees:'}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {loc.assigned_employees.slice(0, 5).map(empId => (
                        <span 
                          key={empId} 
                          className="text-xs px-2 py-0.5 bg-muted rounded-full"
                        >
                          {getEmployeeName(empId)}
                        </span>
                      ))}
                      {loc.assigned_employees.length > 5 && (
                        <span className="text-xs px-2 py-0.5 bg-muted rounded-full">
                          +{loc.assigned_employees.length - 5}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
