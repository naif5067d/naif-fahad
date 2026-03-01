"""
STAS System Maintenance API
نظام صيانة STAS - أرشفة + حذف + إحصائيات

القواعد:
- STAS فقط يمكنه الوصول
- الأرشفة تحفظ كل شيء
- الحذف يمسح المعاملات فقط (لا يمس المستخدمين)
- أي collection جديدة يجب إضافتها هنا
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import require_roles
from datetime import datetime, timezone
import uuid
import json
import gzip
import base64
import zipfile
import io
import os
import psutil
import time

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


# ============================================================
# قائمة الـ Collections المصنفة
# أي collection جديدة يجب إضافتها هنا!
# ============================================================

# Collections التي تُحذف عند حذف المعاملات
TRANSACTION_COLLECTIONS = [
    "transactions",
    "leave_ledger",
    "finance_ledger", 
    "attendance_ledger",
    "custody_ledger",
    "custody_financial",
    "warning_ledger",
    "asset_ledger",
    "contract_audit_log",     # سجل تدقيق العقود
    "contract_snapshots",     # لقطات العقود
]

# Collections التي لا تُحذف (بيانات أساسية)
PROTECTED_COLLECTIONS = [
    "users",
    "employees", 
    "contracts",
    "contracts_v2",           # نظام العقود الجديد
    "finance_codes",
    "public_holidays",
    "holidays",
    "work_locations",
    "settings",
    "counters",
    "system_archives",        # أرشيفات النظام
    "maintenance_log",        # سجل الصيانة
]

# كل الـ Collections في النظام (للأرشفة)
ALL_COLLECTIONS = TRANSACTION_COLLECTIONS + PROTECTED_COLLECTIONS

# Collections تحتاج إعادة تهيئة بعد الحذف
RESET_AFTER_DELETE = {
    "counters": [{"id": "transaction_ref", "seq": 0}],
    "leave_ledger": "RESTORE_INITIAL_BALANCES",  # علامة خاصة
}


class PurgeRequest(BaseModel):
    confirm: bool = False
    confirm_text: str = ""  # يجب أن يكتب "DELETE ALL"


class ArchiveRequest(BaseModel):
    name: str = ""
    description: str = ""


class RestoreRequest(BaseModel):
    archive_id: str
    confirm: bool = False


# ============================================================
# إحصائيات التخزين
# ============================================================

@router.get("/storage-info")
async def get_storage_info(user=Depends(require_roles('stas'))):
    """
    الحصول على معلومات التخزين وحجم البيانات
    متاح لـ STAS فقط
    """
    storage_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "collections": {},
        "totals": {
            "total_documents": 0,
            "total_collections": 0,
            "transaction_documents": 0,
            "protected_documents": 0,
            "total_size_kb": 0,
            "transaction_size_kb": 0,
            "protected_size_kb": 0,
        },
        "categories": {
            "transactions": {"collections": [], "total_docs": 0, "total_size_kb": 0},
            "protected": {"collections": [], "total_docs": 0, "total_size_kb": 0},
        }
    }
    
    # جمع إحصائيات كل collection
    for coll_name in ALL_COLLECTIONS:
        try:
            coll = db[coll_name]
            count = await coll.count_documents({})
            
            # حساب حجم تقريبي (عدد المستندات * متوسط الحجم)
            sample = await coll.find_one()
            avg_size = len(json.dumps(sample, default=str)) if sample else 0
            estimated_size = count * avg_size
            estimated_size_kb = round(estimated_size / 1024, 2)
            
            coll_info = {
                "name": coll_name,
                "documents": count,
                "estimated_size_bytes": estimated_size,
                "estimated_size_kb": estimated_size_kb,
                "is_protected": coll_name in PROTECTED_COLLECTIONS,
                "is_transaction_data": coll_name in TRANSACTION_COLLECTIONS,
            }
            
            storage_info["collections"][coll_name] = coll_info
            storage_info["totals"]["total_documents"] += count
            storage_info["totals"]["total_collections"] += 1
            storage_info["totals"]["total_size_kb"] += estimated_size_kb
            
            if coll_name in TRANSACTION_COLLECTIONS:
                storage_info["totals"]["transaction_documents"] += count
                storage_info["totals"]["transaction_size_kb"] += estimated_size_kb
                storage_info["categories"]["transactions"]["collections"].append(coll_name)
                storage_info["categories"]["transactions"]["total_docs"] += count
                storage_info["categories"]["transactions"]["total_size_kb"] += estimated_size_kb
            else:
                storage_info["totals"]["protected_documents"] += count
                storage_info["totals"]["protected_size_kb"] += estimated_size_kb
                storage_info["categories"]["protected"]["collections"].append(coll_name)
                storage_info["categories"]["protected"]["total_docs"] += count
                storage_info["categories"]["protected"]["total_size_kb"] += estimated_size_kb
                
        except Exception as e:
            storage_info["collections"][coll_name] = {
                "name": coll_name,
                "error": str(e),
                "documents": 0
            }
    
    # تقريب الأحجام الكلية
    storage_info["totals"]["total_size_kb"] = round(storage_info["totals"]["total_size_kb"], 2)
    storage_info["totals"]["transaction_size_kb"] = round(storage_info["totals"]["transaction_size_kb"], 2)
    storage_info["totals"]["protected_size_kb"] = round(storage_info["totals"]["protected_size_kb"], 2)
    
    return storage_info


# ============================================================
# حذف جميع المعاملات
# ============================================================

@router.post("/purge-all-transactions")
async def purge_all_transactions(req: PurgeRequest, user=Depends(require_roles('stas'))):
    """
    حذف جميع المعاملات والسجلات المرتبطة
    لا يمس: المستخدمين، الموظفين، العقود، الأكواد المالية
    
    يتطلب:
    - confirm: true
    - confirm_text: "DELETE ALL"
    """
    if not req.confirm:
        raise HTTPException(status_code=400, detail="يجب تأكيد الحذف (confirm=true)")
    
    if req.confirm_text != "DELETE ALL":
        raise HTTPException(
            status_code=400, 
            detail="يجب كتابة 'DELETE ALL' للتأكيد النهائي"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    results = {
        "timestamp": now,
        "deleted_by": user['user_id'],
        "collections_purged": {},
        "collections_reset": {},
        "total_deleted": 0,
        "status": "success"
    }
    
    try:
        # 1. حذف كل collection المعاملات
        for coll_name in TRANSACTION_COLLECTIONS:
            try:
                coll = db[coll_name]
                count_before = await coll.count_documents({})
                
                if count_before > 0:
                    delete_result = await coll.delete_many({})
                    results["collections_purged"][coll_name] = {
                        "documents_deleted": delete_result.deleted_count,
                        "was_empty": False
                    }
                    results["total_deleted"] += delete_result.deleted_count
                else:
                    results["collections_purged"][coll_name] = {
                        "documents_deleted": 0,
                        "was_empty": True
                    }
            except Exception as e:
                results["collections_purged"][coll_name] = {
                    "error": str(e)
                }
        
        # 2. إعادة تهيئة العدادات
        await db.counters.delete_many({"id": "transaction_ref"})
        await db.counters.insert_one({"id": "transaction_ref", "seq": 0})
        results["collections_reset"]["counters"] = "تمت إعادة تهيئة عداد المعاملات"
        
        # 3. إعادة أرصدة الإجازات الأولية للموظفين (حسب العقد: 21 أو 30 يوم)
        employees = await db.employees.find({}, {"_id": 0}).to_list(500)
        initial_balances_added = 0
        
        for emp in employees:
            # جلب العقد النشط للموظف
            contract = await db.contracts_v2.find_one(
                {"employee_id": emp["id"], "status": "active"},
                {"_id": 0, "annual_leave_days": 1}
            )
            
            # استخدام أيام الإجازة من العقد أو 21 كافتراضي
            annual_days = contract.get("annual_leave_days", 21) if contract else 21
            
            ent = {
                "annual": annual_days,  # 21 أو 30 حسب العقد
                "sick": 30,
                "emergency": 5
            }
            
            for leave_type, days in ent.items():
                await db.leave_ledger.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": emp["id"],
                    "transaction_id": None,
                    "type": "credit",
                    "leave_type": leave_type,
                    "days": days,
                    "note": f"Initial entitlement (after purge) - {annual_days} days annual",
                    "date": now,
                    "created_at": now
                })
                initial_balances_added += 1
        
        results["collections_reset"]["leave_ledger"] = f"تمت إعادة {initial_balances_added} رصيد إجازة أولي (21/30 يوم حسب العقد)"
        
        # 4. تسجيل عملية الحذف في سجل الصيانة
        await db.maintenance_log.insert_one({
            "id": str(uuid.uuid4()),
            "type": "purge",
            "action": "purge_all_transactions",
            "performed_by": user['user_id'],
            "performed_by_name": user.get('full_name', 'STAS'),
            "timestamp": now,
            "details": results
        })
        
        return results
        
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"خطأ في الحذف: {str(e)}")


# ============================================================
# الأرشفة الكاملة
# ============================================================

@router.post("/archive-full")
async def create_full_archive(req: ArchiveRequest, user=Depends(require_roles('stas'))):
    """
    إنشاء أرشيف كامل للنظام
    يحفظ جميع الـ Collections في سجل واحد
    """
    now = datetime.now(timezone.utc)
    archive_id = f"ARCHIVE-{now.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
    
    archive_data = {
        "id": archive_id,
        "name": req.name or f"Full Archive {now.strftime('%Y-%m-%d %H:%M')}",
        "description": req.description or "Full system archive",
        "created_at": now.isoformat(),
        "created_by": user['user_id'],
        "created_by_name": user.get('full_name', 'STAS'),
        "version": "1.0",
        "collections": {},
        "stats": {
            "total_documents": 0,
            "collections_archived": 0,
        }
    }
    
    # جمع بيانات كل collection
    for coll_name in ALL_COLLECTIONS:
        try:
            coll = db[coll_name]
            documents = await coll.find({}, {"_id": 0}).to_list(100000)
            
            archive_data["collections"][coll_name] = {
                "count": len(documents),
                "data": documents
            }
            archive_data["stats"]["total_documents"] += len(documents)
            archive_data["stats"]["collections_archived"] += 1
            
        except Exception as e:
            archive_data["collections"][coll_name] = {
                "error": str(e),
                "count": 0,
                "data": []
            }
    
    # ضغط البيانات وتحويلها إلى base64
    json_data = json.dumps(archive_data, default=str, ensure_ascii=False)
    compressed = gzip.compress(json_data.encode('utf-8'))
    compressed_b64 = base64.b64encode(compressed).decode('ascii')
    
    # حفظ الأرشيف في قاعدة البيانات
    archive_record = {
        "id": archive_id,
        "name": archive_data["name"],
        "description": archive_data["description"],
        "created_at": now.isoformat(),
        "created_by": user['user_id'],
        "created_by_name": user.get('full_name', 'STAS'),
        "stats": archive_data["stats"],
        "compressed_data": compressed_b64,
        "size_original_kb": round(len(json_data) / 1024, 2),
        "size_compressed_kb": round(len(compressed) / 1024, 2),
        "compression_ratio": round(len(compressed) / len(json_data) * 100, 1),
    }
    
    await db.system_archives.insert_one(archive_record)
    
    # تسجيل في سجل الصيانة
    await db.maintenance_log.insert_one({
        "id": str(uuid.uuid4()),
        "type": "archive",
        "action": "create_full_archive",
        "archive_id": archive_id,
        "performed_by": user['user_id'],
        "performed_by_name": user.get('full_name', 'STAS'),
        "timestamp": now.isoformat(),
        "details": {
            "name": archive_data["name"],
            "stats": archive_data["stats"],
            "size_kb": archive_record["size_compressed_kb"]
        }
    })
    
    return {
        "message": "تم إنشاء الأرشيف بنجاح",
        "archive_id": archive_id,
        "name": archive_data["name"],
        "stats": archive_data["stats"],
        "size_original_kb": archive_record["size_original_kb"],
        "size_compressed_kb": archive_record["size_compressed_kb"],
        "compression_ratio": f"{archive_record['compression_ratio']}%"
    }


@router.get("/archives")
async def list_archives(user=Depends(require_roles('stas'))):
    """
    عرض قائمة الأرشيفات المحفوظة
    """
    archives = await db.system_archives.find(
        {}, 
        {"_id": 0, "compressed_data": 0}  # لا نرسل البيانات المضغوطة
    ).sort("created_at", -1).to_list(100)
    
    return {
        "total": len(archives),
        "archives": archives
    }


@router.get("/archives/{archive_id}")
async def get_archive_details(archive_id: str, user=Depends(require_roles('stas'))):
    """
    عرض تفاصيل أرشيف محدد (بدون البيانات)
    """
    archive = await db.system_archives.find_one(
        {"id": archive_id},
        {"_id": 0, "compressed_data": 0}
    )
    
    if not archive:
        raise HTTPException(status_code=404, detail="الأرشيف غير موجود")
    
    return archive


@router.get("/archives/{archive_id}/download")
async def download_archive(archive_id: str, user=Depends(require_roles('stas'))):
    """
    تحميل بيانات الأرشيف كاملة (JSON مضغوط)
    """
    archive = await db.system_archives.find_one({"id": archive_id}, {"_id": 0})
    
    if not archive:
        raise HTTPException(status_code=404, detail="الأرشيف غير موجود")
    
    # فك الضغط وإرجاع البيانات
    compressed = base64.b64decode(archive["compressed_data"])
    decompressed = gzip.decompress(compressed)
    data = json.loads(decompressed.decode('utf-8'))
    
    return data


@router.post("/archives/{archive_id}/restore")
async def restore_archive(archive_id: str, req: RestoreRequest, user=Depends(require_roles('stas'))):
    """
    استعادة النظام من أرشيف محدد
    ⚠️ تحذير: هذا يحذف جميع البيانات الحالية ويستبدلها بالأرشيف
    """
    if not req.confirm:
        raise HTTPException(
            status_code=400, 
            detail="يجب تأكيد الاستعادة (confirm=true). تحذير: سيتم حذف جميع البيانات الحالية!"
        )
    
    archive = await db.system_archives.find_one({"id": archive_id}, {"_id": 0})
    
    if not archive:
        raise HTTPException(status_code=404, detail="الأرشيف غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        # فك ضغط البيانات
        compressed = base64.b64decode(archive["compressed_data"])
        decompressed = gzip.decompress(compressed)
        archive_data = json.loads(decompressed.decode('utf-8'))
        
        results = {
            "timestamp": now,
            "archive_id": archive_id,
            "archive_name": archive["name"],
            "restored_by": user['user_id'],
            "collections_restored": {},
            "total_documents_restored": 0,
            "status": "success"
        }
        
        # حذف واستعادة كل collection
        for coll_name in ALL_COLLECTIONS:
            if coll_name in archive_data.get("collections", {}):
                coll_data = archive_data["collections"][coll_name]
                documents = coll_data.get("data", [])
                
                try:
                    coll = db[coll_name]
                    
                    # حذف البيانات الحالية
                    delete_result = await coll.delete_many({})
                    
                    # استعادة البيانات من الأرشيف
                    if documents:
                        await coll.insert_many(documents)
                    
                    results["collections_restored"][coll_name] = {
                        "deleted": delete_result.deleted_count,
                        "restored": len(documents)
                    }
                    results["total_documents_restored"] += len(documents)
                    
                except Exception as e:
                    results["collections_restored"][coll_name] = {
                        "error": str(e)
                    }
        
        # تسجيل في سجل الصيانة
        await db.maintenance_log.insert_one({
            "id": str(uuid.uuid4()),
            "type": "restore",
            "action": "restore_from_archive",
            "archive_id": archive_id,
            "performed_by": user['user_id'],
            "performed_by_name": user.get('full_name', 'STAS'),
            "timestamp": now,
            "details": results
        })
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في الاستعادة: {str(e)}")


@router.delete("/archives/{archive_id}")
async def delete_archive(archive_id: str, user=Depends(require_roles('stas'))):
    """
    حذف أرشيف محدد
    """
    archive = await db.system_archives.find_one({"id": archive_id})
    
    if not archive:
        raise HTTPException(status_code=404, detail="الأرشيف غير موجود")
    
    await db.system_archives.delete_one({"id": archive_id})
    
    # تسجيل في سجل الصيانة
    await db.maintenance_log.insert_one({
        "id": str(uuid.uuid4()),
        "type": "archive",
        "action": "delete_archive",
        "archive_id": archive_id,
        "performed_by": user['user_id'],
        "performed_by_name": user.get('full_name', 'STAS'),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"archive_name": archive.get("name")}
    })
    
    return {"message": "تم حذف الأرشيف بنجاح", "archive_id": archive_id}


# ============================================================
# سجل الصيانة
# ============================================================

@router.get("/logs")
async def get_maintenance_logs(limit: int = 50, user=Depends(require_roles('stas'))):
    """
    عرض سجل عمليات الصيانة
    """
    logs = await db.maintenance_log.find(
        {}, 
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    
    return {
        "total": len(logs),
        "logs": logs
    }


# ============================================================
# معلومات Collections (للتوثيق)
# ============================================================

@router.get("/collections-info")
async def get_collections_info(user=Depends(require_roles('stas'))):
    """
    عرض معلومات عن تصنيف الـ Collections
    مفيد لفهم ما سيُحذف وما سيبقى
    """
    return {
        "transaction_collections": {
            "description": "هذه الـ Collections تُحذف عند حذف المعاملات",
            "description_ar": "سجلات المعاملات والعمليات اليومية",
            "collections": TRANSACTION_COLLECTIONS,
            "count": len(TRANSACTION_COLLECTIONS)
        },
        "protected_collections": {
            "description": "هذه الـ Collections لا تُحذف (بيانات أساسية)",
            "description_ar": "بيانات المستخدمين والموظفين والإعدادات",
            "collections": PROTECTED_COLLECTIONS,
            "count": len(PROTECTED_COLLECTIONS)
        },
        "all_collections": {
            "description": "جميع الـ Collections في النظام",
            "collections": ALL_COLLECTIONS,
            "count": len(ALL_COLLECTIONS)
        },
        "note": "⚠️ أي collection جديدة يجب إضافتها في ملف maintenance.py"
    }


# ============================================================
# رفع واستعادة أرشيف من ملف
# ============================================================

@router.post("/archives/upload")
async def upload_and_restore_archive(
    file: UploadFile = File(...),
    user=Depends(require_roles('stas'))
):
    """
    رفع ملف أرشيف JSON واستعادة النظام منه
    ⚠️ تحذير: هذا يحذف جميع البيانات الحالية ويستبدلها بالأرشيف المرفوع
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # التحقق من نوع الملف
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=400, 
            detail="نوع الملف غير مدعوم. يجب أن يكون ملف JSON"
        )
    
    try:
        # قراءة محتوى الملف
        content = await file.read()
        archive_data = json.loads(content.decode('utf-8'))
        
        # التحقق من صحة بنية الأرشيف
        if "collections" not in archive_data:
            raise HTTPException(
                status_code=400, 
                detail="بنية الأرشيف غير صحيحة - لا يوجد حقل collections"
            )
        
        results = {
            "timestamp": now,
            "archive_name": archive_data.get("name", file.filename),
            "archive_id": archive_data.get("id", "UPLOADED"),
            "restored_by": user['user_id'],
            "file_name": file.filename,
            "collections_restored": {},
            "total_documents_restored": 0,
            "status": "success"
        }
        
        # حذف واستعادة كل collection
        for coll_name in ALL_COLLECTIONS:
            if coll_name in archive_data.get("collections", {}):
                coll_data = archive_data["collections"][coll_name]
                documents = coll_data.get("data", [])
                
                try:
                    coll = db[coll_name]
                    
                    # حذف البيانات الحالية
                    delete_result = await coll.delete_many({})
                    
                    # استعادة البيانات من الأرشيف
                    if documents:
                        await coll.insert_many(documents)
                    
                    results["collections_restored"][coll_name] = {
                        "deleted": delete_result.deleted_count,
                        "restored": len(documents)
                    }
                    results["total_documents_restored"] += len(documents)
                    
                except Exception as e:
                    results["collections_restored"][coll_name] = {
                        "error": str(e)
                    }
        
        # حفظ سجل للأرشيف المرفوع
        uploaded_archive_id = f"UPLOADED-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"
        
        await db.system_archives.insert_one({
            "id": uploaded_archive_id,
            "name": f"Restored: {archive_data.get('name', file.filename)}",
            "description": f"استعادة من ملف مرفوع: {file.filename}",
            "created_at": now,
            "created_by": user['user_id'],
            "created_by_name": user.get('full_name', 'STAS'),
            "stats": {
                "total_documents": results["total_documents_restored"],
                "collections_archived": len(results["collections_restored"])
            },
            "compressed_data": "",  # لا نحفظ البيانات مرة أخرى
            "size_original_kb": round(len(content) / 1024, 2),
            "size_compressed_kb": 0,
            "source": "uploaded",
            "original_archive_id": archive_data.get("id")
        })
        
        # تسجيل في سجل الصيانة
        await db.maintenance_log.insert_one({
            "id": str(uuid.uuid4()),
            "type": "restore",
            "action": "restore_from_uploaded_file",
            "archive_id": uploaded_archive_id,
            "performed_by": user['user_id'],
            "performed_by_name": user.get('full_name', 'STAS'),
            "timestamp": now,
            "details": {
                "file_name": file.filename,
                "original_archive_name": archive_data.get("name"),
                "total_restored": results["total_documents_restored"]
            }
        })
        
        return results
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, 
            detail="ملف JSON غير صالح"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"خطأ في الاستعادة: {str(e)}"
        )



# ============================================================
# معلومات تشغيل السيرفر (System Metrics)
# ============================================================

# Store server start time at module load
_SERVER_START_TIME = time.time()

def _read_cgroup_file(path: str, default=None):
    """قراءة ملف cgroup بأمان"""
    try:
        with open(path, 'r') as f:
            content = f.read().strip()
            if content == 'max':
                return None  # unlimited
            return content
    except:
        return default

def _get_kubernetes_limits():
    """
    الحصول على حدود Kubernetes الفعلية من cgroup v2
    مع fallback لـ psutil في حالة عدم توفر cgroup (بيئات أخرى)
    """
    limits = {}
    is_kubernetes = os.path.exists('/sys/fs/cgroup/memory.max')
    
    # Memory Limits
    try:
        mem_max = _read_cgroup_file('/sys/fs/cgroup/memory.max')
        mem_current = _read_cgroup_file('/sys/fs/cgroup/memory.current')
        mem_peak = _read_cgroup_file('/sys/fs/cgroup/memory.peak')
        mem_swap_max = _read_cgroup_file('/sys/fs/cgroup/memory.swap.max')
        
        if mem_max and mem_max != 'max':
            mem_max_bytes = int(mem_max)
            limits['memory'] = {
                'limit_bytes': mem_max_bytes,
                'limit_gb': round(mem_max_bytes / (1024**3), 2),
                'limit_mb': round(mem_max_bytes / (1024**2), 0),
                'current_bytes': int(mem_current) if mem_current else 0,
                'current_mb': round(int(mem_current) / (1024**2), 2) if mem_current else 0,
                'peak_mb': round(int(mem_peak) / (1024**2), 2) if mem_peak else 0,
                'usage_percent': round((int(mem_current) / mem_max_bytes) * 100, 1) if mem_current else 0,
                'swap_max_bytes': int(mem_swap_max) if mem_swap_max and mem_swap_max != '0' else 0,
                'oom_behavior': 'Pod يُقتل (OOMKilled) عند تجاوز الحد'
            }
        else:
            # Fallback to psutil for non-Kubernetes environments
            vm = psutil.virtual_memory()
            limits['memory'] = {
                'limit_bytes': vm.total,
                'limit_gb': round(vm.total / (1024**3), 2),
                'limit_mb': round(vm.total / (1024**2), 0),
                'current_bytes': vm.used,
                'current_mb': round(vm.used / (1024**2), 2),
                'peak_mb': round(vm.used / (1024**2), 2),
                'usage_percent': vm.percent,
                'swap_max_bytes': psutil.swap_memory().total,
                'oom_behavior': 'System RAM limit (not containerized)',
                'source': 'psutil'
            }
    except Exception as e:
        # Final fallback
        try:
            vm = psutil.virtual_memory()
            limits['memory'] = {
                'limit_gb': round(vm.total / (1024**3), 2),
                'limit_mb': round(vm.total / (1024**2), 0),
                'current_mb': round(vm.used / (1024**2), 2),
                'usage_percent': vm.percent,
                'source': 'psutil_fallback',
                'error': str(e)
            }
        except:
            limits['memory'] = {'error': str(e)}
    
    # CPU Limits
    try:
        cpu_max = _read_cgroup_file('/sys/fs/cgroup/cpu.max')
        if cpu_max:
            parts = cpu_max.split()
            if len(parts) == 2:
                quota = int(parts[0]) if parts[0] != 'max' else None
                period = int(parts[1])
                
                if quota:
                    # Calculate CPU cores equivalent
                    cpu_cores = quota / period
                    cpu_millicores = int(cpu_cores * 1000)
                    
                    # Get CPU stats for throttling info
                    cpu_stat = _read_cgroup_file('/sys/fs/cgroup/cpu.stat')
                    throttled_periods = 0
                    total_periods = 0
                    if cpu_stat:
                        for line in cpu_stat.split('\n'):
                            if 'nr_throttled' in line:
                                throttled_periods = int(line.split()[1])
                            if 'nr_periods' in line:
                                total_periods = int(line.split()[1])
                    
                    limits['cpu'] = {
                        'limit_cores': round(cpu_cores, 2),
                        'limit_millicores': cpu_millicores,
                        'quota_us': quota,
                        'period_us': period,
                        'throttled_periods': throttled_periods,
                        'total_periods': total_periods,
                        'throttle_percent': round((throttled_periods / total_periods) * 100, 2) if total_periods > 0 else 0,
                        'throttle_behavior': 'العملية تُبطأ (Throttled) عند تجاوز الحد'
                    }
                else:
                    limits['cpu'] = {'limit_cores': 'unlimited'}
    except Exception as e:
        limits['cpu'] = {'error': str(e)}
    
    # Storage Limits (Ephemeral)
    try:
        # Check /app partition (usually ephemeral storage for the app)
        app_disk = psutil.disk_usage('/app')
        limits['ephemeral_storage'] = {
            'limit_gb': round(app_disk.total / (1024**3), 2),
            'used_gb': round(app_disk.used / (1024**3), 2),
            'available_gb': round(app_disk.free / (1024**3), 2),
            'usage_percent': round(app_disk.percent, 1),
            'reject_behavior': 'رفض الكتابة عند امتلاء القرص'
        }
    except:
        limits['ephemeral_storage'] = {'error': 'Cannot read /app disk'}
    
    # Database Storage
    try:
        db_path = '/data/db'
        if os.path.exists(db_path):
            db_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(db_path)
                for filename in filenames
            )
            db_disk = psutil.disk_usage(db_path)
            limits['database_storage'] = {
                'db_used_mb': round(db_size / (1024**2), 2),
                'partition_limit_gb': round(db_disk.total / (1024**3), 2),
                'partition_available_gb': round(db_disk.free / (1024**3), 2),
                'usage_percent': round((db_size / db_disk.total) * 100, 2)
            }
    except Exception as e:
        limits['database_storage'] = {'error': str(e)}
    
    # PIDs Limit
    try:
        pids_max = _read_cgroup_file('/sys/fs/cgroup/pids.max')
        pids_current = _read_cgroup_file('/sys/fs/cgroup/pids.current')
        limits['pids'] = {
            'limit': int(pids_max) if pids_max and pids_max != 'max' else 'unlimited',
            'current': int(pids_current) if pids_current else 0
        }
    except Exception as e:
        limits['pids'] = {'error': str(e)}
    
    # File Upload Limit (check common locations)
    upload_limit_mb = 100  # Default assumption
    try:
        # Check nginx config
        for conf_path in ['/etc/nginx/nginx.conf', '/etc/nginx/conf.d/default.conf']:
            if os.path.exists(conf_path):
                with open(conf_path, 'r') as f:
                    content = f.read()
                    if 'client_max_body_size' in content:
                        # Extract value
                        import re
                        match = re.search(r'client_max_body_size\s+(\d+)([mMgGkK])?', content)
                        if match:
                            val = int(match.group(1))
                            unit = match.group(2).lower() if match.group(2) else 'm'
                            if unit == 'g':
                                upload_limit_mb = val * 1024
                            elif unit == 'k':
                                upload_limit_mb = val / 1024
                            else:
                                upload_limit_mb = val
                        break
    except:
        pass
    
    limits['file_upload'] = {
        'max_size_mb': upload_limit_mb,
        'reject_behavior': 'رفض الرفع مع خطأ 413 Request Entity Too Large'
    }
    
    return limits

@router.get("/system-metrics")
async def get_system_metrics(user=Depends(require_roles('stas'))):
    """
    الحصول على معلومات تشغيل السيرفر الحقيقية
    - RAM usage (الذاكرة)
    - CPU usage (المعالج)
    - Storage usage (التخزين)
    - File storage breakdown (ملفات ATS والمعاملات)
    - Uptime (مدة التشغيل)
    """
    try:
        # Get Kubernetes/Container Limits (the actual allocated limits)
        k8s_limits = _get_kubernetes_limits()
        
        # Current RAM Usage (within the container limit)
        mem_limit_bytes = k8s_limits.get('memory', {}).get('limit_bytes', 0)
        mem_current_bytes = k8s_limits.get('memory', {}).get('current_bytes', 0)
        
        ram_info = {
            "limit_gb": k8s_limits.get('memory', {}).get('limit_gb', 'N/A'),
            "limit_mb": k8s_limits.get('memory', {}).get('limit_mb', 'N/A'),
            "used_mb": k8s_limits.get('memory', {}).get('current_mb', 0),
            "peak_mb": k8s_limits.get('memory', {}).get('peak_mb', 0),
            "percentage": k8s_limits.get('memory', {}).get('usage_percent', 0),
            "swap_enabled": k8s_limits.get('memory', {}).get('swap_max_bytes', 0) > 0,
            "oom_behavior": k8s_limits.get('memory', {}).get('oom_behavior', '')
        }
        
        # CPU Info (within container limit)
        cpu_info = {
            "limit_cores": k8s_limits.get('cpu', {}).get('limit_cores', 'N/A'),
            "limit_millicores": k8s_limits.get('cpu', {}).get('limit_millicores', 'N/A'),
            "percentage": psutil.cpu_percent(interval=0.5),
            "throttled_percent": k8s_limits.get('cpu', {}).get('throttle_percent', 0),
            "throttle_behavior": k8s_limits.get('cpu', {}).get('throttle_behavior', '')
        }
        
        # Storage Info (ephemeral storage for /app)
        storage_info = k8s_limits.get('ephemeral_storage', {})
        storage_info['behavior'] = storage_info.pop('reject_behavior', 'رفض الكتابة')
        
        # Database Storage
        db_storage = k8s_limits.get('database_storage', {})
        
        # File Upload Limit
        file_upload = k8s_limits.get('file_upload', {})
        
        # File Storage Analysis
        file_storage = await _analyze_file_storage()
        
        # Uptime
        uptime_seconds = time.time() - _SERVER_START_TIME
        uptime_info = _format_uptime(uptime_seconds)
        
        # Process Info
        process = psutil.Process()
        process_info = {
            "memory_mb": round(process.memory_info().rss / (1024 ** 2), 2),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads()
        }
        
        # PIDs
        pids_info = k8s_limits.get('pids', {})
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "Kubernetes Pod",
            "limits": {
                "memory": {
                    "limit": f"{ram_info['limit_gb']} GB ({ram_info['limit_mb']} MB)",
                    "used": f"{ram_info['used_mb']} MB",
                    "peak": f"{ram_info['peak_mb']} MB",
                    "percentage": ram_info['percentage'],
                    "on_exceed": ram_info['oom_behavior']
                },
                "cpu": {
                    "limit": f"{cpu_info['limit_cores']} cores ({cpu_info['limit_millicores']}m)",
                    "current_usage": f"{cpu_info['percentage']}%",
                    "throttled": f"{cpu_info['throttled_percent']}%",
                    "on_exceed": cpu_info['throttle_behavior']
                },
                "ephemeral_storage": {
                    "limit": f"{storage_info.get('limit_gb', 'N/A')} GB",
                    "used": f"{storage_info.get('used_gb', 'N/A')} GB",
                    "available": f"{storage_info.get('available_gb', 'N/A')} GB",
                    "percentage": storage_info.get('usage_percent', 0),
                    "on_exceed": storage_info.get('behavior', '')
                },
                "database_storage": {
                    "used": f"{db_storage.get('db_used_mb', 'N/A')} MB",
                    "partition_limit": f"{db_storage.get('partition_limit_gb', 'N/A')} GB",
                    "available": f"{db_storage.get('partition_available_gb', 'N/A')} GB"
                },
                "file_upload": {
                    "max_size": f"{file_upload.get('max_size_mb', 'N/A')} MB",
                    "on_exceed": file_upload.get('reject_behavior', '')
                },
                "pids": pids_info
            },
            "ram": ram_info,
            "cpu": cpu_info,
            "storage": storage_info,
            "db_storage": db_storage,
            "file_storage": file_storage,
            "uptime": uptime_info,
            "process": process_info,
            "status": "healthy"
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "status": "error"
        }


async def _analyze_file_storage():
    """
    تحليل حجم ملفات التخزين (ATS, المعاملات، المرفقات)
    """
    file_storage = {
        "total_mb": 0,
        "ats_files_mb": 0,
        "transaction_files_mb": 0,
        "other_files_mb": 0,
        "breakdown": []
    }
    
    # Define upload directories to check
    upload_dirs = [
        ("/app/uploads", "uploads"),
        ("/app/backend/uploads", "backend_uploads"),
        ("/app/backend/static", "static"),
    ]
    
    for dir_path, dir_name in upload_dirs:
        if os.path.exists(dir_path):
            dir_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        dir_size += file_size
                        file_count += 1
                        
                        # Categorize by path
                        if 'ats' in root.lower() or 'cv' in root.lower() or 'resume' in root.lower():
                            file_storage["ats_files_mb"] += file_size / (1024 ** 2)
                        elif 'transaction' in root.lower() or 'attachment' in root.lower():
                            file_storage["transaction_files_mb"] += file_size / (1024 ** 2)
                        else:
                            file_storage["other_files_mb"] += file_size / (1024 ** 2)
                            
                    except (OSError, PermissionError):
                        continue
            
            size_mb = dir_size / (1024 ** 2)
            file_storage["total_mb"] += size_mb
            
            if size_mb > 0 or file_count > 0:
                file_storage["breakdown"].append({
                    "directory": dir_name,
                    "size_mb": round(size_mb, 2),
                    "file_count": file_count
                })
    
    # Round values
    file_storage["total_mb"] = round(file_storage["total_mb"], 2)
    file_storage["ats_files_mb"] = round(file_storage["ats_files_mb"], 2)
    file_storage["transaction_files_mb"] = round(file_storage["transaction_files_mb"], 2)
    file_storage["other_files_mb"] = round(file_storage["other_files_mb"], 2)
    
    return file_storage


def _format_uptime(seconds):
    """
    تنسيق مدة التشغيل بشكل مقروء
    """
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    
    return {
        "total_seconds": int(seconds),
        "formatted": " ".join(parts),
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": secs
    }
