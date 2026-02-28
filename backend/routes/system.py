"""
نقاط نهاية إدارة النظام
System Management Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from database import db
from routes.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/system", tags=["System"])


class NuclearDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_counts: dict
    preserved_collections: list
    timestamp: str


@router.post("/nuclear-delete", response_model=NuclearDeleteResponse)
async def nuclear_delete_all_transactions(current_user: dict = Depends(get_current_user)):
    """
    الحذف النووي - يحذف جميع البيانات المعاملاتية ويحافظ على العقود والمستخدمين
    Nuclear Delete - Deletes all transactional data but preserves contracts and users
    
    هذا الإجراء لا يمكن التراجع عنه!
    This action is IRREVERSIBLE!
    """
    # التحقق من أن المستخدم sysadmin أو sultan
    allowed_roles = ["stas", "sultan"]
    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail="فقط مدير النظام أو السلطان يمكنه تنفيذ هذا الإجراء | Only SysAdmin or Sultan can perform this action"
        )
    
    # المجموعات التي سيتم حذفها
    collections_to_delete = [
        "login_sessions",
        "attendance",
        "transactions",
        "financial_custody",
        "leave_requests",
        "security_logs",
        "notifications",
        "custody_items",
        "deduction_transactions",
        "penalties",
        "tasks",
        "announcements",
        "performance_reviews",
        "maintenance_requests",
        "job_applications",
    ]
    
    # المجموعات المحفوظة (لن يتم حذفها)
    preserved_collections = [
        "contracts",
        "users",
        "employees",
        "settings",
        "work_locations",
        "company_settings",
        "policies",
        "deductions",
        "job_positions",
    ]
    
    deleted_counts = {}
    
    try:
        # تسجيل عملية الحذف النووي قبل الحذف
        await db.security_logs.insert_one({
            "action": "NUCLEAR_DELETE_INITIATED",
            "performed_by": current_user.get("username"),
            "performed_by_id": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc),
            "details": {
                "collections_to_delete": collections_to_delete,
                "preserved_collections": preserved_collections
            }
        })
        
        # حذف كل مجموعة
        for collection_name in collections_to_delete:
            collection = db[collection_name]
            result = await collection.delete_many({})
            deleted_counts[collection_name] = result.deleted_count
        
        # تسجيل نجاح العملية
        await db.security_logs.insert_one({
            "action": "NUCLEAR_DELETE_COMPLETED",
            "performed_by": current_user.get("username"),
            "performed_by_id": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc),
            "details": {
                "deleted_counts": deleted_counts,
                "total_deleted": sum(deleted_counts.values())
            }
        })
        
        return NuclearDeleteResponse(
            success=True,
            message="تم الحذف النووي بنجاح | Nuclear delete completed successfully",
            deleted_counts=deleted_counts,
            preserved_collections=preserved_collections,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        # تسجيل الخطأ
        await db.security_logs.insert_one({
            "action": "NUCLEAR_DELETE_FAILED",
            "performed_by": current_user.get("username"),
            "performed_by_id": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc),
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=f"خطأ في الحذف النووي: {str(e)}")


@router.get("/collections-stats")
async def get_collections_stats(current_user: dict = Depends(get_current_user)):
    """
    الحصول على إحصائيات المجموعات قبل الحذف
    Get collections statistics before deletion
    """
    allowed_roles = ["stas", "sultan"]
    if current_user.get("role") not in allowed_roles:
        raise HTTPException(status_code=403, detail="غير مصرح | Unauthorized")
    
    # المجموعات المعاملاتية
    transactional_collections = [
        "login_sessions",
        "attendance",
        "transactions",
        "financial_custody",
        "leave_requests",
        "security_logs",
        "notifications",
        "custody_items",
        "deduction_transactions",
        "penalties",
        "tasks",
        "announcements",
        "performance_reviews",
        "maintenance_requests",
        "job_applications",
    ]
    
    stats = {}
    total_count = 0
    
    for collection_name in transactional_collections:
        try:
            count = await db[collection_name].count_documents({})
            stats[collection_name] = count
            total_count += count
        except:
            stats[collection_name] = 0
    
    return {
        "collections": stats,
        "total_documents": total_count,
        "preserved": ["contracts", "users", "employees", "settings", "work_locations"]
    }
