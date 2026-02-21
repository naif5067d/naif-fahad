from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from utils.attendance_rules import validate_check_in, validate_check_out
from services.punch_validator import validate_full_punch, haversine_distance
from services.device_service import check_account_blocked, validate_device
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import uuid

router = APIRouter(prefix="/api/attendance", tags=["attendance"])

# توقيت الرياض
RIYADH_TZ = ZoneInfo("Asia/Riyadh")

def get_riyadh_now():
    """الحصول على الوقت الحالي بتوقيت الرياض"""
    return datetime.now(RIYADH_TZ)

def utc_to_riyadh(dt):
    """تحويل UTC إلى توقيت الرياض"""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(RIYADH_TZ)


class CheckInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_available: bool = False
    work_location: str = "HQ"
    # Device fingerprint
    fingerprint: Optional[dict] = None


class CheckOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_available: bool = False
    work_location: Optional[str] = None
    fingerprint: Optional[dict] = None


# المستخدمين المسموح لهم تجاوز قيود GPS والجهاز
BYPASS_ROLES = ['stas', 'sultan', 'naif']
BYPASS_GPS_ROLES = BYPASS_ROLES


@router.post("/check-in")
async def check_in(req: CheckInRequest, user=Depends(get_current_user)):
    """
    Check-in with server-side validation:
    - Account not blocked
    - Device validated (or first device)
    - Employee must be active with contract
    - GPS location validated (must be within geofence)
    - Working hours validated (cannot check-in after grace + max late)
    """
    # التحقق من أن المستخدم له employee_id
    employee_id = user.get('employee_id')
    if not employee_id:
        raise HTTPException(400, "لا يوجد حساب موظف مرتبط")
    
    # هل المستخدم مدير يمكنه تجاوز القيود؟
    bypass_all = user.get('role') in BYPASS_ROLES
    bypass_gps = bypass_all
    
    # 1. التحقق من أن الحساب غير محجوب
    if not bypass_all:
        block_status = await check_account_blocked(employee_id)
        if block_status['is_blocked']:
            raise HTTPException(403, block_status['message_ar'])
    
    # 2. التحقق من الجهاز (إذا تم إرسال fingerprint)
    if req.fingerprint and not bypass_all:
        device_result = await validate_device(employee_id, req.fingerprint)
        if not device_result['valid']:
            raise HTTPException(403, device_result['error']['message_ar'])
    
    # 3. التحقق الكامل من التبصيم (الوقت + الموقع)
    punch_validation = await validate_full_punch(
        employee_id=employee_id,
        punch_type='checkin',
        latitude=req.latitude,
        longitude=req.longitude,
        gps_available=req.gps_available,
        bypass_gps=bypass_gps
    )
    
    if not punch_validation['valid']:
        # جمع رسائل الأخطاء
        error_messages = [e.get('message_ar', e.get('message')) for e in punch_validation['errors']]
        raise HTTPException(400, " | ".join(error_messages))
    
    # التحقق من الموظف والعقد
    validation = await validate_check_in(user['user_id'], req.work_location)
    
    if not validation['valid']:
        error = validation['error']
        raise HTTPException(status_code=400, detail=error.get('message_ar', error['message']))
    
    emp = validation['employee']
    
    # استخدام توقيت الرياض
    riyadh_now = get_riyadh_now()
    today = riyadh_now.strftime("%Y-%m-%d")

    # استخدام نتائج التحقق الجديدة
    work_location = punch_validation.get('work_location')
    gps_valid = punch_validation.get('gps_valid', False)
    distance = punch_validation.get('distance_km')

    entry = {
        "id": str(uuid.uuid4()),
        "employee_id": emp['id'],
        "transaction_id": None,
        "type": "check_in",
        "timestamp": riyadh_now.isoformat(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "date": today,
        "time": riyadh_now.strftime("%H:%M:%S"),
        "location": {"lat": req.latitude, "lng": req.longitude} if req.gps_available else None,
        "gps_available": req.gps_available,
        "gps_valid": gps_valid,
        "distance_km": round(distance, 3) if distance else None,
        "work_location": work_location.get('name_ar', req.work_location) if work_location else req.work_location,
        "work_location_id": work_location.get('id') if work_location else None,
        "warnings": validation.get('warnings', []) + punch_validation.get('warnings', []),
        "created_at": riyadh_now.isoformat(),
        "source": "self_checkin"
    }
    
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    return entry


@router.post("/check-out")
async def check_out(req: CheckOutRequest, user=Depends(get_current_user)):
    """
    Check-out with server-side validation:
    - Account not blocked
    - Device validated
    - Must have checked in today
    - Cannot checkout twice
    - GPS location validated
    """
    # التحقق من أن المستخدم له employee_id
    employee_id = user.get('employee_id')
    if not employee_id:
        raise HTTPException(400, "لا يوجد حساب موظف مرتبط")
    
    # هل المستخدم مدير يمكنه تجاوز القيود؟
    bypass_all = user.get('role') in BYPASS_ROLES
    bypass_gps = bypass_all
    
    # 1. التحقق من أن الحساب غير محجوب
    if not bypass_all:
        block_status = await check_account_blocked(employee_id)
        if block_status['is_blocked']:
            raise HTTPException(403, block_status['message_ar'])
    
    # 2. التحقق من الجهاز
    if req.fingerprint and not bypass_all:
        device_result = await validate_device(employee_id, req.fingerprint)
        if not device_result['valid']:
            raise HTTPException(403, device_result['error']['message_ar'])
    
    # 3. التحقق الكامل من التبصيم
    punch_validation = await validate_full_punch(
        employee_id=employee_id,
        punch_type='checkout',
        latitude=req.latitude,
        longitude=req.longitude,
        gps_available=req.gps_available,
        bypass_gps=bypass_gps
    )
    
    if not punch_validation['valid']:
        error_messages = [e.get('message_ar', e.get('message')) for e in punch_validation['errors']]
        raise HTTPException(400, " | ".join(error_messages))
    
    # Validate using attendance rules
    validation = await validate_check_out(user['user_id'])
    
    if not validation['valid']:
        error = validation['error']
        raise HTTPException(status_code=400, detail=error.get('message_ar', error['message']))
    
    emp = validation['employee']
    checkin = validation['checkin']
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # استخدام نتائج التحقق الجديدة
    work_location = punch_validation.get('work_location')
    gps_valid = punch_validation.get('gps_valid', False)
    distance = punch_validation.get('distance_km')

    entry = {
        "id": str(uuid.uuid4()),
        "employee_id": emp['id'],
        "transaction_id": None,
        "type": "check_out",
        "timestamp": now.isoformat(),
        "date": today,
        "location": {"lat": req.latitude, "lng": req.longitude} if req.gps_available else None,
        "gps_available": req.gps_available,
        "gps_valid": gps_valid,
        "distance_km": round(distance, 3) if distance else None,
        "work_location": work_location.get('name_ar') if work_location else checkin.get('work_location', 'HQ'),
        "work_location_id": work_location.get('id') if work_location else None,
        "warnings": punch_validation.get('warnings', []),
        "created_at": now.isoformat(),
        "source": "self_checkout"
    }
    
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    return entry


@router.get("/today")
async def get_today_attendance(user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        return {"check_in": None, "check_out": None, "check_in_source": None}
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # البحث عن التسجيل الذاتي أولاً (الأصل)
    checkin = await db.attendance_ledger.find_one(
        {"employee_id": emp['id'], "date": today, "type": "check_in", "source": "self_checkin"}, 
        {"_id": 0}
    )
    
    # إذا لم يوجد ذاتي، نبحث عن التحضير الإداري
    if not checkin:
        checkin = await db.attendance_ledger.find_one(
            {"employee_id": emp['id'], "date": today, "type": "check_in", "source": "admin_checkin"}, 
            {"_id": 0}
        )
    
    # إذا لم يوجد أي منهما، نبحث بدون فلتر source (للتوافق مع البيانات القديمة)
    if not checkin:
        checkin = await db.attendance_ledger.find_one(
            {"employee_id": emp['id'], "date": today, "type": "check_in"}, 
            {"_id": 0}
        )
    
    checkout = await db.attendance_ledger.find_one(
        {"employee_id": emp['id'], "date": today, "type": "check_out"}, {"_id": 0}
    )
    
    return {
        "check_in": checkin, 
        "check_out": checkout,
        "check_in_source": checkin.get('source', 'self_checkin') if checkin else None
    }


@router.get("/history")
async def get_attendance_history(user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        return []
    entries = await db.attendance_ledger.find(
        {"employee_id": emp['id']}, {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    return entries


@router.get("/admin")
async def get_admin_attendance(
    period: str = "daily",
    date: str = None,
    user=Depends(get_current_user)
):
    """Admin view of all employee attendance. period: daily/weekly/monthly/yearly"""
    role = user.get('role')
    if role not in ('sultan', 'naif', 'salah', 'mohammed', 'stas'):
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    target_date = date or now.strftime("%Y-%m-%d")
    
    if period == "daily":
        query = {"date": target_date}
    elif period == "weekly":
        # Get current week (last 7 days from target)
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        end = (dt - timedelta(days=dt.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")
        query = {"date": {"$gte": start, "$lte": end}}
    elif period == "monthly":
        month_start = target_date[:7] + "-01"
        # Calculate month end
        dt = datetime.strptime(month_start, "%Y-%m-%d")
        if dt.month == 12:
            month_end = f"{dt.year + 1}-01-01"
        else:
            month_end = f"{dt.year}-{dt.month + 1:02d}-01"
        query = {"date": {"$gte": month_start, "$lt": month_end}}
    elif period == "yearly":
        year = target_date[:4]
        query = {"date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}}
    else:
        query = {"date": target_date}
    
    entries = await db.attendance_ledger.find(query, {"_id": 0}).sort("date", -1).to_list(5000)
    
    # Group by employee and date
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(200)
    emp_map = {e['id']: e for e in employees}
    
    # Build summary
    grouped = {}
    for entry in entries:
        emp_id = entry['employee_id']
        date_key = entry['date']
        key = f"{emp_id}_{date_key}"
        if key not in grouped:
            emp = emp_map.get(emp_id, {})
            grouped[key] = {
                "employee_id": emp_id,
                "employee_name": emp.get('full_name', ''),
                "employee_name_ar": emp.get('full_name_ar', ''),
                "employee_number": emp.get('employee_number', ''),
                "date": date_key,
                "check_in": None,
                "check_out": None,
                "check_in_time": None,
                "check_out_time": None,
                "gps_valid_in": None,
                "gps_valid_out": None,
                "work_location": None,
                "location_name": None,
                "location_name_ar": None,
                "checkout_location_name": None,
            }
        if entry['type'] == 'check_in':
            grouped[key]['check_in'] = entry['timestamp']
            grouped[key]['check_in_time'] = entry['timestamp'][11:19] if entry.get('timestamp') else None
            grouped[key]['gps_valid_in'] = entry.get('gps_valid')
            grouped[key]['work_location'] = entry.get('work_location')
            grouped[key]['location_name'] = entry.get('work_location')
            grouped[key]['location_name_ar'] = entry.get('work_location')
        elif entry['type'] == 'check_out':
            grouped[key]['check_out'] = entry['timestamp']
            grouped[key]['check_out_time'] = entry['timestamp'][11:19] if entry.get('timestamp') else None
            grouped[key]['gps_valid_out'] = entry.get('gps_valid')
            grouped[key]['checkout_location_name'] = entry.get('work_location')
    
    result = sorted(grouped.values(), key=lambda x: (x['date'], x['employee_name']), reverse=True)
    return result



# ==================== طلبات الحضور والبصمة ====================

class AttendanceRequestCreate(BaseModel):
    request_type: str  # forget_checkin, field_work, early_leave_request, late_excuse
    date: str  # YYYY-MM-DD
    reason: str
    from_time: Optional[str] = None  # للمهمة الخارجية والخروج المبكر
    to_time: Optional[str] = None


ATTENDANCE_REQUEST_TYPES = {
    'forget_checkin': {'name_ar': 'نسيان بصمة', 'name_en': 'Forgot Check-in'},
    'field_work': {'name_ar': 'مهمة خارجية', 'name_en': 'Field Work'},
    'early_leave_request': {'name_ar': 'طلب خروج مبكر', 'name_en': 'Early Leave Request'},
    'late_excuse': {'name_ar': 'تبرير تأخير', 'name_en': 'Late Excuse'},
    'admin_edit': {'name_ar': 'تعديل حضور إداري', 'name_en': 'Admin Edit Attendance'},
}


@router.post("/request")
async def create_attendance_request(req: AttendanceRequestCreate, user=Depends(get_current_user)):
    """إنشاء طلب حضور (نسيان بصمة / مهمة خارجية / الخ)"""
    if req.request_type not in ATTENDANCE_REQUEST_TYPES:
        raise HTTPException(status_code=400, detail="نوع الطلب غير صالح")
    
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # جلب المعاملات للرقم المرجعي
    from routes.transactions import get_next_ref_no
    ref_no = await get_next_ref_no()
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديد workflow
    workflow = ['ops', 'stas']
    if emp.get('supervisor_id'):
        supervisor = await db.employees.find_one({"id": emp['supervisor_id']}, {"_id": 0})
        if supervisor:
            supervisor_user = await db.users.find_one({"id": supervisor.get('user_id')}, {"_id": 0})
            if supervisor_user and supervisor_user.get('role') == 'supervisor':
                workflow = ['supervisor'] + workflow
    
    req_type_info = ATTENDANCE_REQUEST_TYPES[req.request_type]
    
    transaction = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": req.request_type,
        "category": "attendance",  # تصنيف: حضور
        "employee_id": emp['id'],
        "employee_name": emp.get('full_name', ''),
        "employee_name_ar": emp.get('full_name_ar', ''),
        "employee_number": emp.get('employee_number', ''),
        "created_by": user['user_id'],
        "data": {
            "request_type": req.request_type,
            "request_type_ar": req_type_info['name_ar'],
            "request_type_en": req_type_info['name_en'],
            "date": req.date,
            "reason": req.reason,
            "from_time": req.from_time,
            "to_time": req.to_time,
        },
        "status": f"pending_{workflow[0]}",
        "current_stage": workflow[0],
        "workflow": workflow,
        "approval_chain": [],
        "timeline": [{
            "action": "created",
            "actor_id": user['user_id'],
            "actor_name": user.get('username', ''),
            "timestamp": now,
            "note": f"طلب {req_type_info['name_ar']}"
        }],
        "created_at": now,
        "updated_at": now
    }
    
    await db.transactions.insert_one(transaction)
    
    # إزالة _id من الإرجاع
    transaction.pop('_id', None)
    
    return transaction


@router.get("/requests")
async def get_attendance_requests(user=Depends(get_current_user)):
    """جلب طلبات الحضور"""
    role = user.get('role')
    query = {"category": "attendance"}
    
    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if emp:
            query["employee_id"] = emp['id']
        else:
            return []
    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if emp:
            reports = await db.employees.find({"supervisor_id": emp['id']}, {"_id": 0}).to_list(100)
            report_ids = [r['id'] for r in reports] + [emp['id']]
            query["employee_id"] = {"$in": report_ids}
    # admins see all
    
    reqs = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return reqs


class AdminEditRequest(BaseModel):
    date: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    note: Optional[str] = ""


@router.post("/admin-edit/{employee_id}")
async def admin_edit_attendance(
    employee_id: str,
    req: AdminEditRequest,
    user=Depends(get_current_user)
):
    """تعديل حضور موظف إدارياً (STAS فقط)"""
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث أو إضافة سجل الحضور
    if req.check_in_time:
        check_in_ts = f"{req.date}T{req.check_in_time}:00+03:00"
        existing = await db.attendance_ledger.find_one({
            "employee_id": employee_id,
            "date": req.date,
            "type": "check_in"
        })
        if existing:
            await db.attendance_ledger.update_one(
                {"_id": existing['_id']},
                {"$set": {"timestamp": check_in_ts, "admin_edited": True, "edited_by": user['user_id'], "edited_at": now, "edit_note": req.note}}
            )
        else:
            await db.attendance_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "date": req.date,
                "type": "check_in",
                "timestamp": check_in_ts,
                "admin_edited": True,
                "edited_by": user['user_id'],
                "edited_at": now,
                "edit_note": req.note,
                "gps_valid": False,
                "work_location": "admin_edit"
            })
    
    if req.check_out_time:
        check_out_ts = f"{req.date}T{req.check_out_time}:00+03:00"
        existing = await db.attendance_ledger.find_one({
            "employee_id": employee_id,
            "date": req.date,
            "type": "check_out"
        })
        if existing:
            await db.attendance_ledger.update_one(
                {"_id": existing['_id']},
                {"$set": {"timestamp": check_out_ts, "admin_edited": True, "edited_by": user['user_id'], "edited_at": now, "edit_note": req.note}}
            )
        else:
            await db.attendance_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "date": req.date,
                "type": "check_out",
                "timestamp": check_out_ts,
                "admin_edited": True,
                "edited_by": user['user_id'],
                "edited_at": now,
                "edit_note": req.note,
                "gps_valid": False,
                "work_location": "admin_edit"
            })
    
    return {"message": "تم تعديل الحضور بنجاح", "employee_id": employee_id, "date": req.date}



# ==================== التحقق من حالة الحضور ====================

@router.get("/employee-status/{employee_id}")
async def get_employee_attendance_status(
    employee_id: str,
    date: str = None,
    user=Depends(get_current_user)
):
    """
    التحقق من حالة حضور موظف لتاريخ معين
    
    يُرجع:
    - هل الموظف في إجازة معتمدة؟
    - هل لديه إذن معتمد؟
    - هل اليوم عطلة رسمية؟
    - هل يجب تسجيل غياب؟
    
    مفيد قبل:
    - حساب الغياب التلقائي
    - فرض خصومات التأخير
    """
    from utils.attendance_rules import check_employee_attendance_status
    
    # التحقق من الصلاحيات
    role = user.get('role')
    if role not in ('sultan', 'naif', 'salah', 'mohammed', 'stas', 'supervisor'):
        # الموظف يمكنه التحقق من حالته فقط
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp or emp['id'] != employee_id:
            raise HTTPException(status_code=403, detail="غير مصرح")
    
    # التأكد من وجود الموظف
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # جلب الحالة
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    status = await check_employee_attendance_status(employee_id, date)
    
    # إضافة معلومات الموظف
    status["employee_name"] = emp.get("full_name", "")
    status["employee_name_ar"] = emp.get("full_name_ar", "")
    
    return status


@router.post("/calculate-daily")
async def trigger_daily_attendance_calculation(
    date: str = None,
    user=Depends(get_current_user)
):
    """
    تشغيل حساب الحضور اليومي يدوياً
    
    STAS فقط
    يُشغّل عادةً تلقائياً نهاية كل يوم عمل
    """
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    from services.attendance_service import calculate_daily_attendance
    
    result = await calculate_daily_attendance(date)
    
    return {
        "message_ar": "تم حساب الحضور اليومي",
        "result": result
    }
