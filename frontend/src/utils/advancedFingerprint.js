/**
 * Advanced Device Fingerprint - بصمة الجهاز المتقدمة
 * ============================================================
 * جمع أقصى معلومات ممكنة عن الجهاز لكشف التلاعب
 */

export async function generateAdvancedFingerprint() {
  const fp = {
    // === المعلومات الأساسية ===
    userAgent: navigator.userAgent || '',
    platform: navigator.platform || '',
    vendor: navigator.vendor || '',
    language: navigator.language || '',
    languages: navigator.languages ? navigator.languages.join(',') : '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    timezoneOffset: new Date().getTimezoneOffset(),
    
    // === معلومات الشاشة ===
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
    screenResolution: `${window.screen.width}x${window.screen.height}`,
    screenColorDepth: window.screen.colorDepth,
    screenPixelDepth: window.screen.pixelDepth,
    devicePixelRatio: window.devicePixelRatio || 1,
    screenAvailWidth: window.screen.availWidth,
    screenAvailHeight: window.screen.availHeight,
    
    // === معلومات الأجهزة ===
    deviceMemory: navigator.deviceMemory || 0,
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    maxTouchPoints: navigator.maxTouchPoints || 0,
    
    // === إمكانيات الجهاز ===
    touchSupport: 'ontouchstart' in window,
    cookiesEnabled: navigator.cookieEnabled,
    localStorageEnabled: typeof localStorage !== 'undefined',
    sessionStorageEnabled: typeof sessionStorage !== 'undefined',
    indexedDBEnabled: typeof indexedDB !== 'undefined',
    
    // === معلومات الاتصال ===
    connectionType: '',
    connectionEffectiveType: '',
    connectionDownlink: 0,
    connectionRtt: 0,
    
    // === معلومات البطارية ===
    batteryLevel: null,
    batteryCharging: null,
    
    // === WebGL/GPU ===
    webglVendor: '',
    webglRenderer: '',
    webglVersion: '',
    webglShadingLanguageVersion: '',
    webglMaxTextureSize: 0,
    webglExtensions: '',
    
    // === Canvas ===
    canvasFingerprint: '',
    
    // === Audio ===
    audioFingerprint: '',
    
    // === Fonts ===
    fontsDetected: '',
    
    // === معلومات إضافية ===
    doNotTrack: navigator.doNotTrack || '',
    pdfViewerEnabled: navigator.pdfViewerEnabled || false,
    webdriver: navigator.webdriver || false,
    
    // === بيانات محسوبة ===
    isIPhone: false,
    isIPad: false,
    isMac: false,
    isAndroid: false,
    isSamsung: false,
    isHuawei: false,
    isXiaomi: false,
    isWindows: false,
    isLinux: false,
    
    // === معلومات الجهاز المحللة ===
    deviceType: 'unknown',
    deviceBrand: '',
    deviceModel: '',
    osName: '',
    osVersion: '',
    browserName: '',
    browserVersion: '',
  };

  // === جمع معلومات الاتصال ===
  try {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (connection) {
      fp.connectionType = connection.type || '';
      fp.connectionEffectiveType = connection.effectiveType || '';
      fp.connectionDownlink = connection.downlink || 0;
      fp.connectionRtt = connection.rtt || 0;
    }
  } catch (e) {}

  // === جمع معلومات البطارية ===
  try {
    if (navigator.getBattery) {
      const battery = await navigator.getBattery();
      fp.batteryLevel = Math.round(battery.level * 100);
      fp.batteryCharging = battery.charging;
    }
  } catch (e) {}

  // === WebGL المتقدم ===
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (gl) {
      fp.webglVersion = gl.getParameter(gl.VERSION) || '';
      fp.webglShadingLanguageVersion = gl.getParameter(gl.SHADING_LANGUAGE_VERSION) || '';
      fp.webglMaxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE) || 0;
      
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        fp.webglVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || '';
        fp.webglRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || '';
      }
      
      // الإضافات المدعومة
      const extensions = gl.getSupportedExtensions();
      fp.webglExtensions = extensions ? extensions.slice(0, 20).join(',') : '';
    }
  } catch (e) {}

  // === Canvas Fingerprint ===
  try {
    const canvas = document.createElement('canvas');
    canvas.width = 280;
    canvas.height = 60;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      // رسم معقد للحصول على بصمة فريدة
      ctx.textBaseline = 'alphabetic';
      ctx.fillStyle = '#f60';
      ctx.fillRect(125, 1, 62, 20);
      
      ctx.fillStyle = '#069';
      ctx.font = '11pt no-real-font-123';
      ctx.fillText('Cwm fjordbank glyphs vext quiz, 😃', 2, 15);
      
      ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
      ctx.font = '18pt Arial';
      ctx.fillText('Cwm fjordbank glyphs vext quiz, 😃', 4, 45);
      
      ctx.globalCompositeOperation = 'multiply';
      ctx.fillStyle = 'rgb(255,0,255)';
      ctx.beginPath();
      ctx.arc(50, 50, 50, 0, Math.PI * 2, true);
      ctx.closePath();
      ctx.fill();
      
      const dataUrl = canvas.toDataURL();
      let hash = 0;
      for (let i = 0; i < dataUrl.length; i++) {
        const char = dataUrl.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      fp.canvasFingerprint = Math.abs(hash).toString(16);
    }
  } catch (e) {}

  // === Audio Fingerprint ===
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const analyser = audioContext.createAnalyser();
    const gainNode = audioContext.createGain();
    const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    
    gainNode.gain.value = 0;
    oscillator.type = 'triangle';
    oscillator.connect(analyser);
    analyser.connect(scriptProcessor);
    scriptProcessor.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.start(0);
    
    const audioData = new Float32Array(analyser.frequencyBinCount);
    analyser.getFloatFrequencyData(audioData);
    
    let audioSum = 0;
    for (let i = 0; i < audioData.length; i++) {
      audioSum += Math.abs(audioData[i]);
    }
    fp.audioFingerprint = audioSum.toString(16).slice(0, 16);
    
    oscillator.stop();
    audioContext.close();
  } catch (e) {}

  // === تحليل User Agent للحصول على معلومات الجهاز ===
  const ua = navigator.userAgent;
  const uaLower = ua.toLowerCase();
  
  // كشف الأجهزة
  fp.isIPhone = /iphone/i.test(ua);
  fp.isIPad = /ipad/i.test(ua) || (navigator.platform === 'MacIntel' && fp.maxTouchPoints > 1);
  fp.isMac = /macintosh|mac os x/i.test(ua) && !fp.isIPhone && !fp.isIPad;
  fp.isAndroid = /android/i.test(ua);
  fp.isSamsung = /samsung|sm-/i.test(ua);
  fp.isHuawei = /huawei|honor/i.test(ua);
  fp.isXiaomi = /xiaomi|redmi|poco|mi /i.test(ua);
  fp.isWindows = /windows/i.test(ua);
  fp.isLinux = /linux/i.test(ua) && !fp.isAndroid;

  // تحديد نوع الجهاز
  if (fp.isIPhone) {
    fp.deviceType = 'mobile';
    fp.deviceBrand = 'Apple';
    fp.osName = 'iOS';
    // محاولة استخراج موديل الآيفون
    const iphoneMatch = ua.match(/iPhone\s*(\d+),?(\d*)/i) || ua.match(/iPhone OS (\d+)_(\d+)/i);
    if (iphoneMatch) {
      fp.osVersion = `${iphoneMatch[1]}.${iphoneMatch[2] || '0'}`;
    }
    fp.deviceModel = _detectIPhoneModel(fp.screenWidth, fp.screenHeight, fp.devicePixelRatio);
  } else if (fp.isIPad) {
    fp.deviceType = 'tablet';
    fp.deviceBrand = 'Apple';
    fp.osName = 'iPadOS';
    fp.deviceModel = _detectIPadModel(fp.screenWidth, fp.screenHeight);
  } else if (fp.isMac) {
    fp.deviceType = 'desktop';
    fp.deviceBrand = 'Apple';
    fp.osName = 'macOS';
    fp.deviceModel = _detectMacModel(fp.webglRenderer);
  } else if (fp.isAndroid) {
    fp.deviceType = fp.maxTouchPoints > 4 || fp.screenWidth > 800 ? 'tablet' : 'mobile';
    fp.osName = 'Android';
    
    // استخراج إصدار أندرويد
    const androidMatch = ua.match(/Android\s*(\d+\.?\d*)/i);
    if (androidMatch) {
      fp.osVersion = androidMatch[1];
    }
    
    // استخراج موديل الجهاز
    if (fp.isSamsung) {
      fp.deviceBrand = 'Samsung';
      fp.deviceModel = _extractSamsungModel(ua);
    } else if (fp.isHuawei) {
      fp.deviceBrand = 'Huawei';
      fp.deviceModel = _extractHuaweiModel(ua);
    } else if (fp.isXiaomi) {
      fp.deviceBrand = 'Xiaomi';
      fp.deviceModel = _extractXiaomiModel(ua);
    } else {
      // محاولة استخراج أي موديل
      const modelMatch = ua.match(/;\s*([^;)]+)\s*Build/i);
      if (modelMatch) {
        fp.deviceModel = modelMatch[1].trim();
        // محاولة تخمين الماركة
        if (/oppo/i.test(fp.deviceModel)) fp.deviceBrand = 'Oppo';
        else if (/vivo/i.test(fp.deviceModel)) fp.deviceBrand = 'Vivo';
        else if (/oneplus/i.test(fp.deviceModel)) fp.deviceBrand = 'OnePlus';
        else if (/realme/i.test(fp.deviceModel)) fp.deviceBrand = 'Realme';
        else if (/nokia/i.test(fp.deviceModel)) fp.deviceBrand = 'Nokia';
        else if (/lg/i.test(fp.deviceModel)) fp.deviceBrand = 'LG';
        else if (/sony/i.test(fp.deviceModel)) fp.deviceBrand = 'Sony';
        else if (/pixel/i.test(fp.deviceModel)) fp.deviceBrand = 'Google';
        else fp.deviceBrand = 'Android';
      }
    }
  } else if (fp.isWindows) {
    fp.deviceType = 'desktop';
    fp.osName = 'Windows';
    // استخراج إصدار ويندوز
    const winMatch = ua.match(/Windows NT (\d+\.?\d*)/i);
    if (winMatch) {
      const ntVersion = parseFloat(winMatch[1]);
      if (ntVersion >= 10) fp.osVersion = '10/11';
      else if (ntVersion >= 6.3) fp.osVersion = '8.1';
      else if (ntVersion >= 6.2) fp.osVersion = '8';
      else if (ntVersion >= 6.1) fp.osVersion = '7';
    }
  } else if (fp.isLinux) {
    fp.deviceType = 'desktop';
    fp.osName = 'Linux';
  }

  // استخراج معلومات المتصفح
  const browserInfo = _detectBrowser(ua);
  fp.browserName = browserInfo.name;
  fp.browserVersion = browserInfo.version;

  return fp;
}

// === وظائف مساعدة لكشف الموديلات ===

function _detectIPhoneModel(width, height, pixelRatio) {
  const screenSize = `${Math.min(width, height)}x${Math.max(width, height)}@${pixelRatio}`;
  
  const models = {
    '390x844@3': 'iPhone 12/13/14',
    '393x852@3': 'iPhone 14 Pro/15/15 Pro',
    '430x932@3': 'iPhone 14 Pro Max/15 Plus/15 Pro Max',
    '375x812@3': 'iPhone X/XS/11 Pro/12 Mini/13 Mini',
    '414x896@3': 'iPhone XS Max/11 Pro Max',
    '414x896@2': 'iPhone XR/11',
    '375x667@2': 'iPhone 6/6S/7/8/SE2/SE3',
    '414x736@3': 'iPhone 6+/6S+/7+/8+',
    '320x568@2': 'iPhone 5/5S/SE',
  };
  
  return models[screenSize] || 'iPhone';
}

function _detectIPadModel(width, height) {
  const screenSize = Math.max(width, height);
  
  if (screenSize >= 1366) return 'iPad Pro 12.9"';
  if (screenSize >= 1194) return 'iPad Pro 11"';
  if (screenSize >= 1180) return 'iPad Air';
  if (screenSize >= 1024) return 'iPad';
  return 'iPad Mini';
}

function _detectMacModel(webglRenderer) {
  if (!webglRenderer) return 'Mac';
  
  const renderer = webglRenderer.toLowerCase();
  
  if (renderer.includes('m3 max')) return 'MacBook Pro M3 Max';
  if (renderer.includes('m3 pro')) return 'MacBook Pro M3 Pro';
  if (renderer.includes('m3')) return 'Mac M3';
  if (renderer.includes('m2 max')) return 'MacBook Pro M2 Max';
  if (renderer.includes('m2 pro')) return 'MacBook Pro M2 Pro';
  if (renderer.includes('m2')) return 'Mac M2';
  if (renderer.includes('m1 max')) return 'MacBook Pro M1 Max';
  if (renderer.includes('m1 pro')) return 'MacBook Pro M1 Pro';
  if (renderer.includes('m1')) return 'Mac M1';
  if (renderer.includes('intel')) return 'Mac Intel';
  
  return 'Mac';
}

function _extractSamsungModel(ua) {
  // Galaxy S series
  const sMatch = ua.match(/SM-S(\d{3})[A-Z]?/i);
  if (sMatch) {
    const code = parseInt(sMatch[1]);
    if (code >= 928) return 'Galaxy S24 Ultra';
    if (code >= 926) return 'Galaxy S24+';
    if (code >= 921) return 'Galaxy S24';
    if (code >= 918) return 'Galaxy S23 Ultra';
    if (code >= 916) return 'Galaxy S23+';
    if (code >= 911) return 'Galaxy S23';
    if (code >= 908) return 'Galaxy S22 Ultra';
    if (code >= 906) return 'Galaxy S22+';
    if (code >= 901) return 'Galaxy S22';
  }
  
  // Galaxy A series
  const aMatch = ua.match(/SM-A(\d{3})[A-Z]?/i);
  if (aMatch) {
    const code = parseInt(aMatch[1]);
    if (code >= 556) return 'Galaxy A55';
    if (code >= 546) return 'Galaxy A54';
    if (code >= 536) return 'Galaxy A53';
    if (code >= 346) return 'Galaxy A34';
    if (code >= 256) return 'Galaxy A25';
    if (code >= 156) return 'Galaxy A15';
  }
  
  // Galaxy Z Fold/Flip
  if (/SM-F9/i.test(ua)) return 'Galaxy Z Fold';
  if (/SM-F7/i.test(ua)) return 'Galaxy Z Flip';
  
  // Galaxy Note
  if (/SM-N/i.test(ua)) return 'Galaxy Note';
  
  // Galaxy Tab
  if (/SM-T/i.test(ua)) return 'Galaxy Tab';
  if (/SM-X/i.test(ua)) return 'Galaxy Tab S';
  
  // Default
  const genericMatch = ua.match(/Samsung\s*([\w\-]+)/i);
  if (genericMatch) return genericMatch[1];
  
  return 'Galaxy';
}

function _extractHuaweiModel(ua) {
  const modelMatch = ua.match(/(Mate|P\d+|Nova|Honor)\s*(\d+)?\s*(Pro|Plus|Lite|Ultra)?/i);
  if (modelMatch) {
    return `${modelMatch[1]} ${modelMatch[2] || ''} ${modelMatch[3] || ''}`.trim();
  }
  return 'Huawei';
}

function _extractXiaomiModel(ua) {
  // Xiaomi 14/13/12
  const xiaomiMatch = ua.match(/Xiaomi\s*(\d+)\s*(Ultra|Pro|T)?/i);
  if (xiaomiMatch) {
    return `Xiaomi ${xiaomiMatch[1]} ${xiaomiMatch[2] || ''}`.trim();
  }
  
  // Redmi Note
  const redmiNoteMatch = ua.match(/Redmi\s*Note\s*(\d+)\s*(Pro|S|Plus)?/i);
  if (redmiNoteMatch) {
    return `Redmi Note ${redmiNoteMatch[1]} ${redmiNoteMatch[2] || ''}`.trim();
  }
  
  // Redmi
  const redmiMatch = ua.match(/Redmi\s*(\d+[A-Z]?)\s*(Pro)?/i);
  if (redmiMatch) {
    return `Redmi ${redmiMatch[1]} ${redmiMatch[2] || ''}`.trim();
  }
  
  // Poco
  const pocoMatch = ua.match(/POCO\s*(\w+)/i);
  if (pocoMatch) {
    return `Poco ${pocoMatch[1]}`;
  }
  
  // Mi
  const miMatch = ua.match(/Mi\s*(\d+)\s*(Ultra|Pro|T|Lite)?/i);
  if (miMatch) {
    return `Mi ${miMatch[1]} ${miMatch[2] || ''}`.trim();
  }
  
  return 'Xiaomi';
}

function _detectBrowser(ua) {
  const browsers = [
    { name: 'Edge', pattern: /Edg(?:e|A|iOS)?\/(\d+[\.\d]*)/ },
    { name: 'Opera', pattern: /(?:OPR|Opera)\/(\d+[\.\d]*)/ },
    { name: 'Samsung Internet', pattern: /SamsungBrowser\/(\d+[\.\d]*)/ },
    { name: 'UC Browser', pattern: /UCBrowser\/(\d+[\.\d]*)/ },
    { name: 'Firefox', pattern: /Firefox\/(\d+[\.\d]*)/ },
    { name: 'Chrome', pattern: /Chrome\/(\d+[\.\d]*)/ },
    { name: 'Safari', pattern: /Version\/(\d+[\.\d]*).*Safari/ },
  ];
  
  for (const browser of browsers) {
    const match = ua.match(browser.pattern);
    if (match) {
      return { name: browser.name, version: match[1] };
    }
  }
  
  return { name: 'Unknown', version: '' };
}

/**
 * مقارنة بصمتين لكشف التلاعب
 */
export function compareFingerprints(fp1, fp2) {
  const changes = [];
  let suspicionLevel = 0;
  
  // مقارنة الخصائص الحرجة (التي لا يجب أن تتغير)
  const criticalFields = [
    { key: 'webglRenderer', weight: 30, name: 'كرت الشاشة' },
    { key: 'webglVendor', weight: 25, name: 'مصنع كرت الشاشة' },
    { key: 'hardwareConcurrency', weight: 20, name: 'عدد أنوية المعالج' },
    { key: 'deviceMemory', weight: 15, name: 'حجم الذاكرة' },
    { key: 'screenResolution', weight: 15, name: 'دقة الشاشة' },
    { key: 'maxTouchPoints', weight: 10, name: 'نقاط اللمس' },
    { key: 'canvasFingerprint', weight: 20, name: 'بصمة الرسوميات' },
  ];
  
  for (const field of criticalFields) {
    const val1 = fp1[field.key];
    const val2 = fp2[field.key];
    
    if (val1 && val2 && val1 !== val2) {
      changes.push({
        field: field.key,
        name: field.name,
        from: val1,
        to: val2,
        severity: field.weight >= 20 ? 'critical' : 'warning'
      });
      suspicionLevel += field.weight;
    }
  }
  
  // تغيير نظام التشغيل = تلاعب مؤكد
  if (fp1.osName && fp2.osName && fp1.osName !== fp2.osName) {
    changes.push({
      field: 'osName',
      name: 'نظام التشغيل',
      from: fp1.osName,
      to: fp2.osName,
      severity: 'critical'
    });
    suspicionLevel += 50;
  }
  
  // تغيير نوع الجهاز = تلاعب مؤكد
  if (fp1.deviceType && fp2.deviceType && fp1.deviceType !== fp2.deviceType) {
    changes.push({
      field: 'deviceType',
      name: 'نوع الجهاز',
      from: fp1.deviceType,
      to: fp2.deviceType,
      severity: 'critical'
    });
    suspicionLevel += 50;
  }
  
  return {
    hasChanges: changes.length > 0,
    changes,
    suspicionLevel,
    isSuspicious: suspicionLevel >= 30,
    isCritical: suspicionLevel >= 60,
    verdict: suspicionLevel >= 60 ? 'جهاز مختلف تماماً' :
             suspicionLevel >= 30 ? 'تغييرات مشبوهة' :
             'تغييرات طفيفة مقبولة'
  };
}

/**
 * توليد ملخص الجهاز للعرض
 */
export function getDeviceSummary(fp) {
  let deviceName = '';
  let deviceIcon = 'computer';
  
  if (fp.isIPhone) {
    deviceName = fp.deviceModel || 'iPhone';
    deviceIcon = 'smartphone';
  } else if (fp.isIPad) {
    deviceName = fp.deviceModel || 'iPad';
    deviceIcon = 'tablet';
  } else if (fp.isMac) {
    deviceName = fp.deviceModel || 'Mac';
    deviceIcon = 'laptop';
  } else if (fp.isSamsung) {
    deviceName = fp.deviceModel || 'Samsung';
    deviceIcon = 'smartphone';
  } else if (fp.isHuawei) {
    deviceName = fp.deviceModel || 'Huawei';
    deviceIcon = 'smartphone';
  } else if (fp.isXiaomi) {
    deviceName = fp.deviceModel || 'Xiaomi';
    deviceIcon = 'smartphone';
  } else if (fp.isAndroid) {
    deviceName = fp.deviceModel || 'Android';
    deviceIcon = fp.deviceType === 'tablet' ? 'tablet' : 'smartphone';
  } else if (fp.isWindows) {
    deviceName = `Windows PC`;
    deviceIcon = 'monitor';
  } else if (fp.isLinux) {
    deviceName = 'Linux PC';
    deviceIcon = 'monitor';
  } else {
    deviceName = 'جهاز غير معروف';
  }
  
  return {
    deviceName,
    deviceIcon,
    brand: fp.deviceBrand || '',
    model: fp.deviceModel || '',
    os: `${fp.osName || ''} ${fp.osVersion || ''}`.trim(),
    browser: `${fp.browserName || ''} ${fp.browserVersion || ''}`.trim(),
    screen: fp.screenResolution || '',
    memory: fp.deviceMemory ? `${fp.deviceMemory} GB` : '',
    cores: fp.hardwareConcurrency || '',
    gpu: fp.webglRenderer || '',
    connection: fp.connectionEffectiveType || '',
    battery: fp.batteryLevel !== null ? `${fp.batteryLevel}%` : '',
    isCharging: fp.batteryCharging,
  };
}

export default generateAdvancedFingerprint;
