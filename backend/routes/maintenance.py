"""
STAS System Maintenance API
نظام صيانة STAS - أرشفة + حذف + إحصائيات

القواعد:
- STAS فقط يمكنه الوصول
- الأرشفة تحفظ كل شيء
- الحذف يمسح المعاملات فقط (لا يمس المستخدمين)
- أي collection جديدة يجب إضافتها هنا
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import require_roles
from datetime import datetime, timezone
import uuid
import json
import gzip
import base64

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
]

# Collections التي لا تُحذف (بيانات أساسية)
PROTECTED_COLLECTIONS = [
    "users",
    "employees", 
    "contracts",
    "finance_codes",
    "public_holidays",
    "holidays",
    "work_locations",
    "settings",
    "counters",
    "system_archives",      # أرشيفات النظام
    "maintenance_log",      # سجل الصيانة
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
        },
        "categories": {
            "transactions": {"collections": [], "total_docs": 0},
            "protected": {"collections": [], "total_docs": 0},
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
            
            coll_info = {
                "name": coll_name,
                "documents": count,
                "estimated_size_bytes": estimated_size,
                "estimated_size_kb": round(estimated_size / 1024, 2),
                "is_protected": coll_name in PROTECTED_COLLECTIONS,
                "is_transaction_data": coll_name in TRANSACTION_COLLECTIONS,
            }
            
            storage_info["collections"][coll_name] = coll_info
            storage_info["totals"]["total_documents"] += count
            storage_info["totals"]["total_collections"] += 1
            
            if coll_name in TRANSACTION_COLLECTIONS:
                storage_info["totals"]["transaction_documents"] += count
                storage_info["categories"]["transactions"]["collections"].append(coll_name)
                storage_info["categories"]["transactions"]["total_docs"] += count
            else:
                storage_info["totals"]["protected_documents"] += count
                storage_info["categories"]["protected"]["collections"].append(coll_name)
                storage_info["categories"]["protected"]["total_docs"] += count
                
        except Exception as e:
            storage_info["collections"][coll_name] = {
                "name": coll_name,
                "error": str(e),
                "documents": 0
            }
    
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
        
        # 3. إعادة أرصدة الإجازات الأولية للموظفين
        employees = await db.employees.find({}, {"_id": 0}).to_list(500)
        initial_balances_added = 0
        
        for emp in employees:
            ent = emp.get("leave_entitlement", {"annual": 25, "sick": 30, "emergency": 5})
            for leave_type, days in ent.items():
                await db.leave_ledger.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": emp["id"],
                    "transaction_id": None,
                    "type": "credit",
                    "leave_type": leave_type,
                    "days": days,
                    "note": "Initial entitlement (after purge)",
                    "date": now,
                    "created_at": now
                })
                initial_balances_added += 1
        
        results["collections_reset"]["leave_ledger"] = f"تمت إعادة {initial_balances_added} رصيد إجازة أولي"
        
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
