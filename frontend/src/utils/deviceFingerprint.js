/**
 * نظام بصمة الجهاز المتقدم
 * ===========================
 * يجمع أقصى معلومات ممكنة من المتصفح
 */

export async function collectDeviceFingerprint() {
  const fp = {};
  
  // === 1. معلومات النظام ===
  fp.userAgent = navigator.userAgent;
  fp.platform = navigator.platform;
  fp.language = navigator.language;
  fp.languages = navigator.languages?.join(',') || '';
  fp.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  fp.timezoneOffset = new Date().getTimezoneOffset();
  
  // === 2. معلومات الشاشة ===
  fp.screenWidth = screen.width;
  fp.screenHeight = screen.height;
  fp.screenResolution = `${screen.width}x${screen.height}`;
  fp.colorDepth = screen.colorDepth;
  fp.pixelRatio = window.devicePixelRatio || 1;
  fp.availWidth = screen.availWidth;
  fp.availHeight = screen.availHeight;
  
  // === 3. معلومات الأجهزة ===
  fp.hardwareConcurrency = navigator.hardwareConcurrency || 0;
  fp.deviceMemory = navigator.deviceMemory || 0;
  fp.maxTouchPoints = navigator.maxTouchPoints || 0;
  
  // === 4. WebGL - GPU ===
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        fp.webglVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || '';
        fp.webglRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || '';
      }
      fp.webglVersion = gl.getParameter(gl.VERSION) || '';
      fp.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE) || 0;
    }
  } catch (e) {
    fp.webglVendor = '';
    fp.webglRenderer = '';
  }
  
  // === 5. Canvas Fingerprint ===
  try {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 50;
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(100, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('DeviceFingerprint', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('DeviceFingerprint', 4, 17);
    
    const dataUrl = canvas.toDataURL();
    let hash = 0;
    for (let i = 0; i < dataUrl.length; i++) {
      hash = ((hash << 5) - hash) + dataUrl.charCodeAt(i);
      hash = hash & hash;
    }
    fp.canvasHash = Math.abs(hash).toString(16);
  } catch (e) {
    fp.canvasHash = '';
  }
  
  // === 6. Audio Fingerprint ===
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const analyser = audioCtx.createAnalyser();
    const gain = audioCtx.createGain();
    gain.gain.value = 0;
    oscillator.connect(analyser);
    analyser.connect(gain);
    gain.connect(audioCtx.destination);
    oscillator.start(0);
    
    const data = new Float32Array(analyser.frequencyBinCount);
    analyser.getFloatFrequencyData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += Math.abs(data[i]);
    fp.audioHash = sum.toString(16).slice(0, 16);
    
    oscillator.stop();
    audioCtx.close();
  } catch (e) {
    fp.audioHash = '';
  }
  
  // === 7. معلومات الاتصال ===
  try {
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn) {
      fp.connectionType = conn.effectiveType || '';
      fp.connectionDownlink = conn.downlink || 0;
    }
  } catch (e) {}
  
  // === 8. البطارية ===
  try {
    if (navigator.getBattery) {
      const battery = await navigator.getBattery();
      fp.batteryLevel = Math.round(battery.level * 100);
      fp.batteryCharging = battery.charging;
    }
  } catch (e) {}
  
  // === 9. تحليل النظام ===
  const ua = navigator.userAgent.toLowerCase();
  
  // نوع النظام
  if (ua.includes('iphone')) {
    fp.osType = 'iOS';
    fp.deviceCategory = 'iPhone';
    const match = navigator.userAgent.match(/iPhone OS (\d+)_(\d+)/);
    if (match) fp.osVersion = `${match[1]}.${match[2]}`;
  } else if (ua.includes('ipad') || (ua.includes('mac') && fp.maxTouchPoints > 1)) {
    fp.osType = 'iPadOS';
    fp.deviceCategory = 'iPad';
  } else if (ua.includes('macintosh') || ua.includes('mac os')) {
    fp.osType = 'macOS';
    fp.deviceCategory = 'Mac';
    const match = navigator.userAgent.match(/Mac OS X (\d+)[_.](\d+)/);
    if (match) fp.osVersion = `${match[1]}.${match[2]}`;
  } else if (ua.includes('android')) {
    fp.osType = 'Android';
    const match = navigator.userAgent.match(/Android\s*(\d+\.?\d*)/i);
    if (match) fp.osVersion = match[1];
    
    if (ua.includes('samsung') || ua.includes('sm-')) {
      fp.deviceCategory = 'Samsung';
    } else if (ua.includes('huawei') || ua.includes('honor')) {
      fp.deviceCategory = 'Huawei';
    } else if (ua.includes('xiaomi') || ua.includes('redmi') || ua.includes('poco')) {
      fp.deviceCategory = 'Xiaomi';
    } else if (ua.includes('oppo')) {
      fp.deviceCategory = 'Oppo';
    } else if (ua.includes('vivo')) {
      fp.deviceCategory = 'Vivo';
    } else if (ua.includes('pixel')) {
      fp.deviceCategory = 'Google Pixel';
    } else {
      fp.deviceCategory = 'Android';
    }
  } else if (ua.includes('windows')) {
    fp.osType = 'Windows';
    fp.deviceCategory = 'Windows PC';
    const match = navigator.userAgent.match(/Windows NT (\d+\.?\d*)/);
    if (match) {
      const ver = parseFloat(match[1]);
      fp.osVersion = ver >= 10 ? '10/11' : ver >= 6.3 ? '8.1' : ver >= 6.1 ? '7' : '';
    }
  } else if (ua.includes('linux')) {
    fp.osType = 'Linux';
    fp.deviceCategory = 'Linux PC';
  } else {
    fp.osType = 'Unknown';
    fp.deviceCategory = 'Unknown';
  }
  
  // نوع الجهاز
  if (fp.maxTouchPoints > 0 && (ua.includes('mobile') || ua.includes('iphone') || fp.screenWidth < 768)) {
    fp.deviceType = 'mobile';
  } else if (fp.maxTouchPoints > 0 && (ua.includes('tablet') || ua.includes('ipad') || (fp.screenWidth >= 768 && fp.screenWidth <= 1024))) {
    fp.deviceType = 'tablet';
  } else {
    fp.deviceType = 'desktop';
  }
  
  // المتصفح
  if (ua.includes('edg/')) fp.browser = 'Edge';
  else if (ua.includes('opr/') || ua.includes('opera')) fp.browser = 'Opera';
  else if (ua.includes('samsungbrowser')) fp.browser = 'Samsung Browser';
  else if (ua.includes('firefox')) fp.browser = 'Firefox';
  else if (ua.includes('chrome')) fp.browser = 'Chrome';
  else if (ua.includes('safari')) fp.browser = 'Safari';
  else fp.browser = 'Unknown';
  
  // === 10. توليد البصمة الفريدة ===
  const signatureData = [
    fp.webglRenderer,
    fp.webglVendor,
    fp.canvasHash,
    fp.hardwareConcurrency,
    fp.deviceMemory,
    fp.screenResolution,
    fp.colorDepth,
    fp.pixelRatio,
    fp.maxTouchPoints,
    fp.platform,
    fp.timezone
  ].join('|');
  
  // Simple hash
  let hash = 0;
  for (let i = 0; i < signatureData.length; i++) {
    hash = ((hash << 5) - hash) + signatureData.charCodeAt(i);
    hash = hash & hash;
  }
  fp.deviceSignature = Math.abs(hash).toString(16).padStart(8, '0');
  
  // === 11. تحليل GPU لتحديد نوع الجهاز ===
  const gpu = (fp.webglRenderer || '').toLowerCase();
  
  if (gpu.includes('apple m3')) fp.gpuType = 'Apple M3';
  else if (gpu.includes('apple m2')) fp.gpuType = 'Apple M2';
  else if (gpu.includes('apple m1')) fp.gpuType = 'Apple M1';
  else if (gpu.includes('apple a17')) fp.gpuType = 'Apple A17 Pro';
  else if (gpu.includes('apple a16')) fp.gpuType = 'Apple A16';
  else if (gpu.includes('apple a15')) fp.gpuType = 'Apple A15';
  else if (gpu.includes('apple gpu')) fp.gpuType = 'Apple GPU';
  else if (gpu.includes('rtx 40')) fp.gpuType = 'NVIDIA RTX 40 Series';
  else if (gpu.includes('rtx 30')) fp.gpuType = 'NVIDIA RTX 30 Series';
  else if (gpu.includes('rtx 20')) fp.gpuType = 'NVIDIA RTX 20 Series';
  else if (gpu.includes('rtx')) fp.gpuType = 'NVIDIA RTX';
  else if (gpu.includes('gtx')) fp.gpuType = 'NVIDIA GTX';
  else if (gpu.includes('nvidia')) fp.gpuType = 'NVIDIA';
  else if (gpu.includes('radeon')) fp.gpuType = 'AMD Radeon';
  else if (gpu.includes('amd')) fp.gpuType = 'AMD';
  else if (gpu.includes('intel iris')) fp.gpuType = 'Intel Iris';
  else if (gpu.includes('intel uhd')) fp.gpuType = 'Intel UHD';
  else if (gpu.includes('intel')) fp.gpuType = 'Intel';
  else if (gpu.includes('adreno 7')) fp.gpuType = 'Qualcomm Adreno 7xx';
  else if (gpu.includes('adreno 6')) fp.gpuType = 'Qualcomm Adreno 6xx';
  else if (gpu.includes('adreno')) fp.gpuType = 'Qualcomm Adreno';
  else if (gpu.includes('mali-g7')) fp.gpuType = 'ARM Mali-G7x';
  else if (gpu.includes('mali')) fp.gpuType = 'ARM Mali';
  else fp.gpuType = 'Unknown GPU';
  
  return fp;
}

export default collectDeviceFingerprint;
