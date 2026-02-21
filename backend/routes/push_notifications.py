# Push Notifications API for DAR AL CODE HR OS
# Uses Firebase Cloud Messaging (FCM)

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os
import json

from utils.auth import get_current_user

router = APIRouter(prefix="/api/push", tags=["Push Notifications"])

# Get database
def get_db():
    from server import db
    return db

# Firebase Admin SDK initialization
firebase_initialized = False
firebase_app = None

def init_firebase():
    global firebase_initialized, firebase_app
    if firebase_initialized:
        return True
    
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        
        # Check if already initialized
        if firebase_admin._apps:
            firebase_app = firebase_admin.get_app()
            firebase_initialized = True
            return True
        
        # Try to initialize with service account
        service_account_path = "/app/backend/firebase-admin.json"
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_app = firebase_admin.initialize_app(cred)
            firebase_initialized = True
            print("[FCM] Firebase Admin SDK initialized with service account")
            return True
        else:
            # Initialize without credentials (limited functionality)
            firebase_app = firebase_admin.initialize_app()
            firebase_initialized = True
            print("[FCM] Firebase Admin SDK initialized without service account")
            return True
    except Exception as e:
        print(f"[FCM] Firebase initialization failed: {e}")
        return False

# Models
class PushSubscription(BaseModel):
    user_id: str
    subscription: dict  # Contains endpoint, keys (fcm_token for FCM)
    type: Optional[str] = "fcm"  # fcm or web_push

class PushMessage(BaseModel):
    user_id: Optional[str] = None
    user_ids: Optional[list] = None
    title: str
    title_ar: Optional[str] = None
    body: str
    body_ar: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None

# Initialize Firebase on module load
init_firebase()

# Endpoints
@router.get("/vapid-key")
async def get_vapid_public_key():
    """Get Firebase config (for compatibility)"""
    return {
        "publicKey": "firebase",
        "type": "fcm",
        "projectId": "alcode-co"
    }

@router.post("/subscribe")
async def subscribe_to_push(data: PushSubscription, current_user: dict = Depends(get_current_user)):
    """Save push subscription for a user"""
    db = get_db()
    
    # Extract FCM token
    fcm_token = None
    if data.subscription.get("keys", {}).get("fcm_token"):
        fcm_token = data.subscription["keys"]["fcm_token"]
    elif data.subscription.get("endpoint", "").startswith("fcm:"):
        fcm_token = data.subscription["endpoint"][4:]  # Remove "fcm:" prefix
    
    subscription_doc = {
        "user_id": data.user_id,
        "endpoint": data.subscription.get("endpoint"),
        "fcm_token": fcm_token,
        "keys": data.subscription.get("keys"),
        "type": data.type,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "is_active": True
    }
    
    # Upsert subscription (update if exists, insert if not)
    if fcm_token:
        db.push_subscriptions.update_one(
            {"user_id": data.user_id, "fcm_token": fcm_token},
            {"$set": subscription_doc},
            upsert=True
        )
    else:
        db.push_subscriptions.update_one(
            {"user_id": data.user_id, "endpoint": data.subscription.get("endpoint")},
            {"$set": subscription_doc},
            upsert=True
        )
    
    return {"success": True, "message": "تم تفعيل الإشعارات"}

@router.post("/unsubscribe")
async def unsubscribe_from_push(data: dict, current_user: dict = Depends(get_current_user)):
    """Remove push subscription for a user"""
    db = get_db()
    
    db.push_subscriptions.update_many(
        {"user_id": data.get("user_id")},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"success": True, "message": "تم إلغاء الإشعارات"}

@router.get("/status")
async def get_push_status(current_user: dict = Depends(get_current_user)):
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
    """Send push notification to a specific user via FCM"""
    db = get_db()
    
    subscriptions = list(db.push_subscriptions.find({
        "user_id": user_id,
        "is_active": True
    }))
    
    if not subscriptions:
        return {"sent": 0, "reason": "no_subscriptions"}
    
    sent_count = 0
    failed_tokens = []
    
    # Try Firebase Admin SDK
    if firebase_initialized:
        try:
            from firebase_admin import messaging
            
            for sub in subscriptions:
                fcm_token = sub.get("fcm_token")
                if not fcm_token:
                    continue
                
                try:
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data={
                            "url": url,
                            "tag": tag or f"notification-{datetime.now(timezone.utc).timestamp()}",
                            "title": title,
                            "body": body
                        },
                        token=fcm_token,
                        android=messaging.AndroidConfig(
                            priority="high",
                            notification=messaging.AndroidNotification(
                                click_action="OPEN_URL"
                            )
                        ),
                        webpush=messaging.WebpushConfig(
                            notification=messaging.WebpushNotification(
                                title=title,
                                body=body,
                                icon="/icon-192.png"
                            ),
                            fcm_options=messaging.WebpushFCMOptions(
                                link=url
                            )
                        )
                    )
                    
                    response = messaging.send(message)
                    print(f"[FCM] Message sent: {response}")
                    sent_count += 1
                    
                except Exception as e:
                    print(f"[FCM] Failed to send to token: {e}")
                    failed_tokens.append(fcm_token)
                    
                    # Mark as inactive if token is invalid
                    if "not registered" in str(e).lower() or "invalid" in str(e).lower():
                        db.push_subscriptions.update_one(
                            {"fcm_token": fcm_token},
                            {"$set": {"is_active": False}}
                        )
            
            return {"sent": sent_count, "failed": len(failed_tokens)}
            
        except Exception as e:
            print(f"[FCM] Error sending notifications: {e}")
            return {"sent": 0, "reason": str(e)}
    else:
        return {"sent": 0, "reason": "firebase_not_initialized"}

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
async def send_notification(data: PushMessage, current_user: dict = Depends(get_current_user)):
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
async def send_test_notification(current_user: dict = Depends(get_current_user)):
    """Send test notification to current user"""
    result = await send_push_notification(
        current_user["id"],
        "اختبار الإشعارات",
        "هذا إشعار تجريبي من نظام دار الكود",
        "/",
        "test-notification"
    )
    return result
