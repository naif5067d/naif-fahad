"""
Advanced Device Analysis Service - خدمة تحليل الجهاز المتقدمة
============================================================
تحليل تفصيلي لبصمة الجهاز مع كشف التلاعب
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, List


def analyze_device_fingerprint(fingerprint_data: dict) -> dict:
    """
    تحليل شامل لبصمة الجهاز واستخراج كل المعلومات الممكنة
    """
    result = {
        # معلومات الجهاز الأساسية
        "device_type": "unknown",
        "device_brand": "",
        "device_model": "",
        "device_name_ar": "جهاز غير معروف",
        "device_icon": "monitor",
        
        # نظام التشغيل
        "os_name": "",
        "os_version": "",
        "os_display_ar": "",
        
        # المتصفح
        "browser_name": "",
        "browser_version": "",
        
        # الأجهزة (Hardware)
        "screen_resolution": "",
        "device_memory": 0,
        "cpu_cores": 0,
        "gpu_vendor": "",
        "gpu_renderer": "",
        "gpu_display_ar": "",
        
        # الاتصال
        "connection_type": "",
        "connection_speed": "",
        
        # البطارية
        "battery_level": None,
        "is_charging": None,
        
        # معلومات إضافية
        "is_mobile": False,
        "is_tablet": False,
        "is_desktop": True,
        "has_touch": False,
        "timezone": "",
        "language": "",
        
        # بصمات التحقق
        "hardware_signature": "",
        "canvas_signature": "",
        "audio_signature": "",
        
        # درجة الثقة
        "confidence_score": 0,
        "detection_method": "",
    }
    
    # === استخراج المعلومات من البيانات الجديدة (إذا كانت من advancedFingerprint) ===
    if fingerprint_data.get('deviceType'):
        result["device_type"] = fingerprint_data.get('deviceType', 'unknown')
        result["device_brand"] = fingerprint_data.get('deviceBrand', '')
        result["device_model"] = fingerprint_data.get('deviceModel', '')
        result["os_name"] = fingerprint_data.get('osName', '')
        result["os_version"] = fingerprint_data.get('osVersion', '')
        result["browser_name"] = fingerprint_data.get('browserName', '')
        result["browser_version"] = fingerprint_data.get('browserVersion', '')
        result["is_mobile"] = fingerprint_data.get('deviceType') == 'mobile'
        result["is_tablet"] = fingerprint_data.get('deviceType') == 'tablet'
        result["is_desktop"] = fingerprint_data.get('deviceType') == 'desktop'
        result["detection_method"] = "advanced_fingerprint"
        result["confidence_score"] = 95
    else:
        # === تحليل User Agent (الطريقة القديمة) ===
        ua = fingerprint_data.get('userAgent', '')
        parsed = _parse_user_agent_detailed(ua)
        result.update(parsed)
        result["detection_method"] = "user_agent_parsing"
        result["confidence_score"] = 70
    
    # === معلومات الشاشة ===
    result["screen_resolution"] = fingerprint_data.get('screenResolution', '')
    
    # === معلومات الأجهزة ===
    result["device_memory"] = fingerprint_data.get('deviceMemory', 0)
    result["cpu_cores"] = fingerprint_data.get('hardwareConcurrency', 0)
    result["gpu_vendor"] = fingerprint_data.get('webglVendor', '')
    result["gpu_renderer"] = fingerprint_data.get('webglRenderer', '')
    result["gpu_display_ar"] = _translate_gpu(fingerprint_data.get('webglRenderer', ''))
    
    # === معلومات الاتصال ===
    result["connection_type"] = fingerprint_data.get('connectionEffectiveType', '')
    result["connection_speed"] = _translate_connection(fingerprint_data.get('connectionEffectiveType', ''))
    
    # === معلومات البطارية ===
    result["battery_level"] = fingerprint_data.get('batteryLevel')
    result["is_charging"] = fingerprint_data.get('batteryCharging')
    
    # === معلومات إضافية ===
    result["has_touch"] = fingerprint_data.get('touchSupport', False) or fingerprint_data.get('maxTouchPoints', 0) > 0
    result["timezone"] = fingerprint_data.get('timezone', '')
    result["language"] = fingerprint_data.get('language', '')
    
    # === البصمات ===
    result["hardware_signature"] = _generate_hardware_signature(fingerprint_data)
    result["canvas_signature"] = fingerprint_data.get('canvasFingerprint', '')
    result["audio_signature"] = fingerprint_data.get('audioFingerprint', '')
    
    # === توليد الأسماء العربية ===
    result["device_name_ar"] = _generate_device_name_ar(result)
    result["os_display_ar"] = _translate_os(result["os_name"], result["os_version"])
    result["device_icon"] = _get_device_icon(result)
    
    return result


def _generate_hardware_signature(fp: dict) -> str:
    """توليد بصمة الأجهزة (Hardware) - لا تتغير بتغيير المتصفح"""
    values = [
        str(fp.get('webglVendor', '')),
        str(fp.get('webglRenderer', '')),
        str(fp.get('canvasFingerprint', '')),
        str(fp.get('hardwareConcurrency', '')),
        str(fp.get('deviceMemory', '')),
        str(fp.get('screenResolution', '')),
        str(fp.get('maxTouchPoints', '')),
        str(fp.get('platform', '')),
    ]
    combined = '|'.join(values)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


def _parse_user_agent_detailed(ua: str) -> dict:
    """تحليل User Agent بالتفصيل"""
    result = {
        "device_type": "desktop",
        "device_brand": "",
        "device_model": "",
        "os_name": "",
        "os_version": "",
        "browser_name": "",
        "browser_version": "",
        "is_mobile": False,
        "is_tablet": False,
        "is_desktop": True,
    }
    
    ua_lower = ua.lower()
    
    # === كشف iPhone ===
    if 'iphone' in ua_lower:
        result["device_type"] = "mobile"
        result["device_brand"] = "Apple"
        result["is_mobile"] = True
        result["is_desktop"] = False
        result["os_name"] = "iOS"
        
        # استخراج إصدار iOS
        import re
        ios_match = re.search(r'iPhone OS (\d+)_(\d+)', ua)
        if ios_match:
            result["os_version"] = f"{ios_match.group(1)}.{ios_match.group(2)}"
        
        # محاولة تحديد الموديل من الشاشة (سيتم لاحقاً)
        result["device_model"] = "iPhone"
    
    # === كشف iPad ===
    elif 'ipad' in ua_lower:
        result["device_type"] = "tablet"
        result["device_brand"] = "Apple"
        result["device_model"] = "iPad"
        result["is_tablet"] = True
        result["is_desktop"] = False
        result["os_name"] = "iPadOS"
    
    # === كشف Mac ===
    elif 'macintosh' in ua_lower or 'mac os x' in ua_lower:
        result["device_type"] = "desktop"
        result["device_brand"] = "Apple"
        result["device_model"] = "Mac"
        result["os_name"] = "macOS"
    
    # === كشف Android ===
    elif 'android' in ua_lower:
        result["os_name"] = "Android"
        
        import re
        android_ver = re.search(r'Android\s*(\d+\.?\d*)', ua, re.I)
        if android_ver:
            result["os_version"] = android_ver.group(1)
        
        # تحديد النوع
        if 'mobile' in ua_lower:
            result["device_type"] = "mobile"
            result["is_mobile"] = True
            result["is_desktop"] = False
        elif 'tablet' in ua_lower:
            result["device_type"] = "tablet"
            result["is_tablet"] = True
            result["is_desktop"] = False
        
        # كشف Samsung
        if 'samsung' in ua_lower or 'sm-' in ua_lower:
            result["device_brand"] = "Samsung"
            result["device_model"] = _extract_samsung_model(ua)
        
        # كشف Huawei
        elif 'huawei' in ua_lower or 'honor' in ua_lower:
            result["device_brand"] = "Huawei"
            result["device_model"] = _extract_huawei_model(ua)
        
        # كشف Xiaomi
        elif any(x in ua_lower for x in ['xiaomi', 'redmi', 'poco', 'mi ']):
            result["device_brand"] = "Xiaomi"
            result["device_model"] = _extract_xiaomi_model(ua)
        
        # كشف ماركات أخرى
        else:
            import re
            model_match = re.search(r';\s*([^;)]+)\s*Build', ua, re.I)
            if model_match:
                model = model_match.group(1).strip()
                result["device_model"] = model
                
                if 'oppo' in model.lower():
                    result["device_brand"] = "Oppo"
                elif 'vivo' in model.lower():
                    result["device_brand"] = "Vivo"
                elif 'oneplus' in model.lower():
                    result["device_brand"] = "OnePlus"
                elif 'realme' in model.lower():
                    result["device_brand"] = "Realme"
                elif 'pixel' in model.lower():
                    result["device_brand"] = "Google"
                else:
                    result["device_brand"] = "Android"
    
    # === كشف Windows ===
    elif 'windows' in ua_lower:
        result["device_type"] = "desktop"
        result["os_name"] = "Windows"
        
        import re
        win_match = re.search(r'Windows NT (\d+\.?\d*)', ua)
        if win_match:
            nt_ver = float(win_match.group(1))
            if nt_ver >= 10:
                result["os_version"] = "10/11"
            elif nt_ver >= 6.3:
                result["os_version"] = "8.1"
            elif nt_ver >= 6.1:
                result["os_version"] = "7"
    
    # === كشف Linux ===
    elif 'linux' in ua_lower and 'android' not in ua_lower:
        result["device_type"] = "desktop"
        result["os_name"] = "Linux"
    
    # === كشف المتصفح ===
    result.update(_detect_browser(ua))
    
    return result


def _extract_samsung_model(ua: str) -> str:
    """استخراج موديل سامسونج"""
    import re
    
    # Galaxy S series
    s_match = re.search(r'SM-S(\d{3})', ua, re.I)
    if s_match:
        code = int(s_match.group(1))
        if code >= 928: return 'Galaxy S24 Ultra'
        if code >= 926: return 'Galaxy S24+'
        if code >= 921: return 'Galaxy S24'
        if code >= 918: return 'Galaxy S23 Ultra'
        if code >= 916: return 'Galaxy S23+'
        if code >= 911: return 'Galaxy S23'
        if code >= 908: return 'Galaxy S22 Ultra'
        if code >= 906: return 'Galaxy S22+'
        if code >= 901: return 'Galaxy S22'
    
    # Galaxy A series
    a_match = re.search(r'SM-A(\d{3})', ua, re.I)
    if a_match:
        code = int(a_match.group(1))
        if code >= 556: return 'Galaxy A55'
        if code >= 546: return 'Galaxy A54'
        if code >= 536: return 'Galaxy A53'
        if code >= 346: return 'Galaxy A34'
        if code >= 256: return 'Galaxy A25'
        if code >= 156: return 'Galaxy A15'
    
    # Z Fold/Flip
    if re.search(r'SM-F9', ua, re.I): return 'Galaxy Z Fold'
    if re.search(r'SM-F7', ua, re.I): return 'Galaxy Z Flip'
    
    # Note
    if re.search(r'SM-N', ua, re.I): return 'Galaxy Note'
    
    # Tab
    if re.search(r'SM-T', ua, re.I): return 'Galaxy Tab'
    if re.search(r'SM-X', ua, re.I): return 'Galaxy Tab S'
    
    return 'Galaxy'


def _extract_huawei_model(ua: str) -> str:
    """استخراج موديل هواوي"""
    import re
    match = re.search(r'(Mate|P\d+|Nova|Honor)\s*(\d+)?\s*(Pro|Plus|Lite|Ultra)?', ua, re.I)
    if match:
        return f"{match.group(1)} {match.group(2) or ''} {match.group(3) or ''}".strip()
    return 'Huawei'


def _extract_xiaomi_model(ua: str) -> str:
    """استخراج موديل شاومي"""
    import re
    
    # Xiaomi 14/13/12
    xiaomi_match = re.search(r'Xiaomi\s*(\d+)\s*(Ultra|Pro|T)?', ua, re.I)
    if xiaomi_match:
        return f"Xiaomi {xiaomi_match.group(1)} {xiaomi_match.group(2) or ''}".strip()
    
    # Redmi Note
    redmi_note = re.search(r'Redmi\s*Note\s*(\d+)\s*(Pro|S|Plus)?', ua, re.I)
    if redmi_note:
        return f"Redmi Note {redmi_note.group(1)} {redmi_note.group(2) or ''}".strip()
    
    # Redmi
    redmi = re.search(r'Redmi\s*(\d+[A-Z]?)\s*(Pro)?', ua, re.I)
    if redmi:
        return f"Redmi {redmi.group(1)} {redmi.group(2) or ''}".strip()
    
    # Poco
    poco = re.search(r'POCO\s*(\w+)', ua, re.I)
    if poco:
        return f"Poco {poco.group(1)}"
    
    return 'Xiaomi'


def _detect_browser(ua: str) -> dict:
    """كشف المتصفح"""
    import re
    
    browsers = [
        ('Edge', r'Edg(?:e|A|iOS)?\/(\d+[\.\d]*)'),
        ('Opera', r'(?:OPR|Opera)\/(\d+[\.\d]*)'),
        ('Samsung Internet', r'SamsungBrowser\/(\d+[\.\d]*)'),
        ('UC Browser', r'UCBrowser\/(\d+[\.\d]*)'),
        ('Firefox', r'Firefox\/(\d+[\.\d]*)'),
        ('Chrome', r'Chrome\/(\d+[\.\d]*)'),
        ('Safari', r'Version\/(\d+[\.\d]*).*Safari'),
    ]
    
    for name, pattern in browsers:
        match = re.search(pattern, ua)
        if match:
            return {"browser_name": name, "browser_version": match.group(1)}
    
    return {"browser_name": "Unknown", "browser_version": ""}


def _generate_device_name_ar(info: dict) -> str:
    """توليد اسم الجهاز بالعربية"""
    brand = info.get("device_brand", "")
    model = info.get("device_model", "")
    device_type = info.get("device_type", "")
    os_name = info.get("os_name", "")
    
    # Apple
    if brand == "Apple":
        if "iPhone" in model or device_type == "mobile":
            return f"آيفون {model.replace('iPhone', '').strip()}" if model else "آيفون"
        elif "iPad" in model or device_type == "tablet":
            return f"آيباد {model.replace('iPad', '').strip()}" if model else "آيباد"
        elif "Mac" in model or os_name == "macOS":
            if "M3" in model: return f"ماك {model}"
            if "M2" in model: return f"ماك {model}"
            if "M1" in model: return f"ماك {model}"
            return "ماك"
    
    # Samsung
    if brand == "Samsung":
        return f"سامسونج {model}" if model else "جهاز سامسونج"
    
    # Huawei
    if brand == "Huawei":
        return f"هواوي {model}" if model else "جهاز هواوي"
    
    # Xiaomi
    if brand == "Xiaomi":
        return f"شاومي {model}" if model else "جهاز شاومي"
    
    # Android Generic
    if os_name == "Android":
        if model:
            return model
        if device_type == "tablet":
            return "جهاز لوحي أندرويد"
        return "هاتف أندرويد"
    
    # Windows
    if os_name == "Windows":
        return "كمبيوتر ويندوز"
    
    # Linux
    if os_name == "Linux":
        return "كمبيوتر لينكس"
    
    # Default
    if device_type == "mobile":
        return "هاتف محمول"
    elif device_type == "tablet":
        return "جهاز لوحي"
    
    return "كمبيوتر"


def _translate_os(os_name: str, os_version: str) -> str:
    """ترجمة نظام التشغيل للعربية"""
    translations = {
        "iOS": "نظام آي أو إس",
        "iPadOS": "نظام آيباد",
        "macOS": "نظام ماك",
        "Android": "أندرويد",
        "Windows": "ويندوز",
        "Linux": "لينكس",
    }
    
    name_ar = translations.get(os_name, os_name)
    if os_version:
        return f"{name_ar} {os_version}"
    return name_ar


def _translate_gpu(gpu_renderer: str) -> str:
    """ترجمة كرت الشاشة للعربية"""
    if not gpu_renderer:
        return ""
    
    renderer = gpu_renderer.lower()
    
    # Apple Silicon
    if 'm3 max' in renderer: return "شريحة Apple M3 Max"
    if 'm3 pro' in renderer: return "شريحة Apple M3 Pro"
    if 'm3' in renderer: return "شريحة Apple M3"
    if 'm2 max' in renderer: return "شريحة Apple M2 Max"
    if 'm2 pro' in renderer: return "شريحة Apple M2 Pro"
    if 'm2' in renderer: return "شريحة Apple M2"
    if 'm1 max' in renderer: return "شريحة Apple M1 Max"
    if 'm1 pro' in renderer: return "شريحة Apple M1 Pro"
    if 'm1' in renderer: return "شريحة Apple M1"
    if 'apple' in renderer: return "شريحة Apple"
    
    # NVIDIA
    if 'nvidia' in renderer or 'geforce' in renderer:
        if 'rtx 40' in renderer: return "كرت NVIDIA RTX 40 Series"
        if 'rtx 30' in renderer: return "كرت NVIDIA RTX 30 Series"
        if 'rtx' in renderer: return "كرت NVIDIA RTX"
        if 'gtx' in renderer: return "كرت NVIDIA GTX"
        return "كرت NVIDIA"
    
    # AMD
    if 'amd' in renderer or 'radeon' in renderer:
        return "كرت AMD Radeon"
    
    # Intel
    if 'intel' in renderer:
        if 'iris' in renderer: return "كرت Intel Iris"
        if 'uhd' in renderer: return "كرت Intel UHD"
        return "كرت Intel"
    
    # Qualcomm (Mobile)
    if 'adreno' in renderer:
        return "معالج Qualcomm Adreno"
    
    # Mali (Mobile)
    if 'mali' in renderer:
        return "معالج ARM Mali"
    
    return gpu_renderer[:50]


def _translate_connection(connection_type: str) -> str:
    """ترجمة نوع الاتصال"""
    translations = {
        "4g": "شبكة 4G",
        "3g": "شبكة 3G",
        "2g": "شبكة 2G",
        "slow-2g": "شبكة بطيئة جداً",
        "wifi": "واي فاي",
        "ethernet": "سلكي",
    }
    return translations.get(connection_type.lower(), connection_type)


def _get_device_icon(info: dict) -> str:
    """تحديد أيقونة الجهاز"""
    device_type = info.get("device_type", "")
    brand = info.get("device_brand", "")
    
    if device_type == "mobile":
        return "smartphone"
    elif device_type == "tablet":
        return "tablet"
    elif brand == "Apple" and info.get("os_name") == "macOS":
        return "laptop"
    else:
        return "monitor"


def compare_fingerprints(fp1: dict, fp2: dict) -> dict:
    """
    مقارنة بصمتين لكشف التلاعب
    
    Returns:
        dict with:
        - has_changes: bool
        - changes: list of changes
        - suspicion_level: 0-100
        - is_suspicious: bool
        - verdict_ar: str
    """
    changes = []
    suspicion_level = 0
    
    # الحقول الحرجة التي لا يجب أن تتغير
    critical_fields = [
        ("webglRenderer", 30, "كرت الشاشة"),
        ("webglVendor", 25, "مصنع كرت الشاشة"),
        ("hardwareConcurrency", 20, "عدد أنوية المعالج"),
        ("deviceMemory", 15, "حجم الذاكرة"),
        ("screenResolution", 15, "دقة الشاشة"),
        ("maxTouchPoints", 10, "نقاط اللمس"),
        ("canvasFingerprint", 20, "بصمة الرسوميات"),
        ("platform", 15, "المنصة"),
    ]
    
    for field, weight, name_ar in critical_fields:
        val1 = fp1.get(field)
        val2 = fp2.get(field)
        
        if val1 and val2 and str(val1) != str(val2):
            changes.append({
                "field": field,
                "name_ar": name_ar,
                "from": str(val1),
                "to": str(val2),
                "severity": "critical" if weight >= 20 else "warning",
                "weight": weight
            })
            suspicion_level += weight
    
    # تغيير نظام التشغيل = تلاعب مؤكد
    os1 = fp1.get('osName') or fp1.get('os_name', '')
    os2 = fp2.get('osName') or fp2.get('os_name', '')
    if os1 and os2 and os1 != os2:
        changes.append({
            "field": "osName",
            "name_ar": "نظام التشغيل",
            "from": os1,
            "to": os2,
            "severity": "critical",
            "weight": 50
        })
        suspicion_level += 50
    
    # تغيير نوع الجهاز = تلاعب مؤكد
    type1 = fp1.get('deviceType') or fp1.get('device_type', '')
    type2 = fp2.get('deviceType') or fp2.get('device_type', '')
    if type1 and type2 and type1 != type2:
        changes.append({
            "field": "deviceType",
            "name_ar": "نوع الجهاز",
            "from": type1,
            "to": type2,
            "severity": "critical",
            "weight": 50
        })
        suspicion_level += 50
    
    # تحديد الحكم
    if suspicion_level >= 60:
        verdict_ar = "جهاز مختلف تماماً - تلاعب مؤكد"
    elif suspicion_level >= 30:
        verdict_ar = "تغييرات مشبوهة - يحتاج تحقيق"
    elif suspicion_level > 0:
        verdict_ar = "تغييرات طفيفة - مقبولة"
    else:
        verdict_ar = "نفس الجهاز - لا توجد تغييرات"
    
    return {
        "has_changes": len(changes) > 0,
        "changes": changes,
        "suspicion_level": min(suspicion_level, 100),
        "is_suspicious": suspicion_level >= 30,
        "is_critical": suspicion_level >= 60,
        "verdict_ar": verdict_ar
    }


def detect_fraud_indicators(sessions: List[dict]) -> List[dict]:
    """
    كشف مؤشرات التلاعب من سجل الجلسات
    """
    alerts = []
    
    if len(sessions) < 2:
        return alerts
    
    # ترتيب حسب التاريخ
    sorted_sessions = sorted(sessions, key=lambda x: x.get('login_at', ''))
    
    # === 1. كشف تغيير الجهاز المفاجئ ===
    for i in range(1, len(sorted_sessions)):
        prev = sorted_sessions[i-1]
        curr = sorted_sessions[i]
        
        prev_fp = prev.get('fingerprint_data', {})
        curr_fp = curr.get('fingerprint_data', {})
        
        if prev_fp and curr_fp:
            comparison = compare_fingerprints(prev_fp, curr_fp)
            if comparison['is_critical']:
                alerts.append({
                    "type": "device_change",
                    "severity": "critical",
                    "title_ar": "تغيير جهاز مفاجئ",
                    "message_ar": f"تم تغيير الجهاز من جلسة لأخرى: {comparison['verdict_ar']}",
                    "from_session": prev.get('id'),
                    "to_session": curr.get('id'),
                    "changes": comparison['changes'],
                    "timestamp": curr.get('login_at')
                })
    
    # === 2. كشف الجلسات المتزامنة (نفس الوقت من أجهزة مختلفة) ===
    for i, s1 in enumerate(sorted_sessions):
        for s2 in sorted_sessions[i+1:]:
            # إذا كانت الجلستان متداخلتان زمنياً
            s1_login = s1.get('login_at', '')
            s1_logout = s1.get('logout_at', '')
            s2_login = s2.get('login_at', '')
            
            if s1_login and s2_login and (not s1_logout or s1_logout > s2_login):
                # تحقق إذا كانت من أجهزة مختلفة
                if s1.get('core_signature') != s2.get('core_signature'):
                    alerts.append({
                        "type": "concurrent_sessions",
                        "severity": "high",
                        "title_ar": "جلسات متزامنة من أجهزة مختلفة",
                        "message_ar": "تم تسجيل الدخول من جهازين مختلفين في نفس الوقت",
                        "sessions": [s1.get('id'), s2.get('id')],
                        "timestamp": s2_login
                    })
    
    # === 3. كشف أوقات الدخول الغريبة (بين 12 ليلاً و 5 صباحاً) ===
    for session in sorted_sessions:
        login_at = session.get('login_at', '')
        if login_at:
            try:
                login_time = datetime.fromisoformat(login_at.replace('Z', '+00:00'))
                hour = login_time.hour
                if 0 <= hour < 5:
                    alerts.append({
                        "type": "unusual_time",
                        "severity": "medium",
                        "title_ar": "دخول في وقت غير اعتيادي",
                        "message_ar": f"تم تسجيل الدخول في الساعة {hour}:{login_time.minute:02d} صباحاً",
                        "session_id": session.get('id'),
                        "timestamp": login_at
                    })
            except:
                pass
    
    return alerts
