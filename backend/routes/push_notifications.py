# Push Notifications API for DAR AL CODE HR OS
# Uses Web Push Protocol with VAPID (no Firebase)

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from utils.auth import require_auth

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])

# Get database
def get_db():
    from server import db
    return db

# VAPID keys storage file
VAPID_KEYS_FILE = "/app/backend/vapid_keys.json"

def generate_vapid_keys():
    """Generate new VAPID key pair"""
    # Generate EC private key
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    
    # Get raw bytes
    private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Convert to URL-safe base64
    private_b64 = base64.urlsafe_b64encode(private_bytes).decode('utf-8').rstrip('=')
    public_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
    
    return {
        "private_key": private_b64,
        "public_key": public_b64,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

def get_or_create_vapid_keys():
    """Get existing VAPID keys or create new ones"""
    if os.path.exists(VAPID_KEYS_FILE):
        with open(VAPID_KEYS_FILE, 'r') as f:
            return json.load(f)
    
    # Generate new keys
    keys = generate_vapid_keys()
    
    # Save keys
    with open(VAPID_KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=2)
    
    print(f"[Push] Generated new VAPID keys")
    return keys

# Get VAPID keys at startup
try:
    VAPID_KEYS = get_or_create_vapid_keys()
    print(f"[Push] VAPID keys loaded successfully")
except Exception as e:
    print(f"[Push] Error loading VAPID keys: {e}")
    VAPID_KEYS = generate_vapid_keys()

VAPID_CLAIMS = {
    "sub": "mailto:admin@daralcode.com"
}

# Models
class PushSubscription(BaseModel):
    user_id: str
    subscription: dict  # Contains endpoint, keys (p256dh, auth)

class PushMessage(BaseModel):
    user_id: Optional[str] = None
    user_ids: Optional[list] = None
    title: str
    title_ar: Optional[str] = None
    body: str
    body_ar: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None

# Endpoints
@router.get("/vapid-key")
async def get_vapid_public_key():
    """Get the public VAPID key for push subscriptions"""
    return {"publicKey": VAPID_KEYS["public_key_b64"]}

@router.post("/subscribe")
async def subscribe_to_push(data: PushSubscription, current_user: dict = Depends(require_auth)):
    """Save push subscription for a user"""
    db = get_db()
    
    subscription_doc = {
        "user_id": data.user_id,
        "endpoint": data.subscription.get("endpoint"),
        "keys": data.subscription.get("keys"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "is_active": True
    }
    
    # Upsert subscription (update if exists, insert if not)
    db.push_subscriptions.update_one(
        {"user_id": data.user_id, "endpoint": data.subscription.get("endpoint")},
        {"$set": subscription_doc},
        upsert=True
    )
    
    return {"success": True, "message": "تم تفعيل الإشعارات"}

@router.post("/unsubscribe")
async def unsubscribe_from_push(data: dict, current_user: dict = Depends(require_auth)):
    """Remove push subscription for a user"""
    db = get_db()
    
    db.push_subscriptions.update_many(
        {"user_id": data.get("user_id")},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"success": True, "message": "تم إلغاء الإشعارات"}

@router.get("/status")
async def get_push_status(current_user: dict = Depends(require_auth)):
    """Get push notification status for current user"""
    db = get_db()
    
    subscriptions = list(db.push_subscriptions.find(
        {"user_id": current_user["id"], "is_active": True},
        {"_id": 0, "endpoint": 1, "created_at": 1}
    ))
    
    return {
        "enabled": len(subscriptions) > 0,
        "subscriptions_count": len(subscriptions)
    }

async def send_push_notification(user_id: str, title: str, body: str, url: str = "/", tag: str = None):
    """Send push notification to a specific user"""
    db = get_db()
    
    subscriptions = list(db.push_subscriptions.find({
        "user_id": user_id,
        "is_active": True
    }))
    
    if not subscriptions:
        return {"sent": 0, "reason": "no_subscriptions"}
    
    sent_count = 0
    failed_endpoints = []
    
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "tag": tag or f"notification-{datetime.now(timezone.utc).timestamp()}"
    })
    
    for sub in subscriptions:
        try:
            subscription_info = {
                "endpoint": sub["endpoint"],
                "keys": sub["keys"]
            }
            
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_KEYS["private_key"],
                vapid_claims=VAPID_CLAIMS
            )
            sent_count += 1
            
        except WebPushException as e:
            print(f"[Push] Failed to send to {sub['endpoint']}: {e}")
            failed_endpoints.append(sub["endpoint"])
            
            # Mark subscription as inactive if endpoint is gone (410 Gone)
            if e.response and e.response.status_code == 410:
                db.push_subscriptions.update_one(
                    {"endpoint": sub["endpoint"]},
                    {"$set": {"is_active": False}}
                )
        except Exception as e:
            print(f"[Push] Error sending notification: {e}")
            failed_endpoints.append(sub["endpoint"])
    
    return {"sent": sent_count, "failed": len(failed_endpoints)}

async def send_push_to_role(role: str, title: str, body: str, url: str = "/"):
    """Send push notification to all users with a specific role"""
    db = get_db()
    
    # Get all users with this role
    users = list(db.users.find({"role": role, "is_active": True}, {"id": 1}))
    
    total_sent = 0
    for user in users:
        result = await send_push_notification(user["id"], title, body, url)
        total_sent += result.get("sent", 0)
    
    return {"total_sent": total_sent, "users_count": len(users)}

async def send_push_to_admins(title: str, body: str, url: str = "/"):
    """Send push notification to all admin users (stas, sultan, naif)"""
    admin_roles = ["stas", "sultan", "naif"]
    total_sent = 0
    
    for role in admin_roles:
        result = await send_push_to_role(role, title, body, url)
        total_sent += result.get("total_sent", 0)
    
    return {"total_sent": total_sent}

# Admin endpoint to send test notification
@router.post("/send")
async def send_notification(data: PushMessage, current_user: dict = Depends(require_auth)):
    """Send push notification (admin only)"""
    if current_user.get("role") not in ["stas", "sultan", "naif"]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بإرسال الإشعارات")
    
    if data.user_id:
        result = await send_push_notification(
            data.user_id,
            data.title_ar or data.title,
            data.body_ar or data.body,
            data.url or "/",
            data.tag
        )
    elif data.user_ids:
        total_sent = 0
        for uid in data.user_ids:
            r = await send_push_notification(
                uid,
                data.title_ar or data.title,
                data.body_ar or data.body,
                data.url or "/",
                data.tag
            )
            total_sent += r.get("sent", 0)
        result = {"sent": total_sent}
    else:
        raise HTTPException(status_code=400, detail="يجب تحديد user_id أو user_ids")
    
    return result

@router.post("/test")
async def send_test_notification(current_user: dict = Depends(require_auth)):
    """Send test notification to current user"""
    result = await send_push_notification(
        current_user["id"],
        "اختبار الإشعارات",
        "هذا إشعار تجريبي من نظام دار الكود",
        "/",
        "test-notification"
    )
    return result
