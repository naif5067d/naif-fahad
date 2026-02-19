/**
 * Device Fingerprint Utility
 * يولّد بصمة فريدة للجهاز باستخدام Browser Fingerprint Hybrid
 */

export async function generateFingerprint() {
  const fp = {
    userAgent: navigator.userAgent || '',
    platform: navigator.platform || '',
    screenResolution: `${window.screen.width}x${window.screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
    language: navigator.language || '',
    webglVendor: '',
    webglRenderer: '',
    canvasFingerprint: '',
    deviceMemory: navigator.deviceMemory?.toString() || '',
    hardwareConcurrency: navigator.hardwareConcurrency?.toString() || '',
    touchSupport: ('ontouchstart' in window).toString(),
    cookiesEnabled: navigator.cookieEnabled?.toString() || '',
    localStorageEnabled: (typeof localStorage !== 'undefined').toString(),
  };

  // WebGL Vendor & Renderer
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        fp.webglVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) || '';
        fp.webglRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || '';
      }
    }
  } catch (e) {
    // WebGL not available
  }

  // Canvas Fingerprint
  try {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 50;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillStyle = '#f60';
      ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = '#069';
      ctx.fillText('Device FP', 2, 15);
      ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
      ctx.fillText('Device FP', 4, 17);
      
      // Simple hash of canvas data
      const dataUrl = canvas.toDataURL();
      let hash = 0;
      for (let i = 0; i < dataUrl.length; i++) {
        const char = dataUrl.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      fp.canvasFingerprint = Math.abs(hash).toString(16);
    }
  } catch (e) {
    // Canvas not available
  }

  return fp;
}

/**
 * التحقق من الجهاز مع الـ Backend
 */
export async function validateDevice(api) {
  try {
    const fingerprint = await generateFingerprint();
    const response = await api.post('/api/devices/validate', fingerprint);
    return response.data;
  } catch (error) {
    if (error.response?.status === 403) {
      return {
        valid: false,
        error: error.response.data.detail || 'Device not authorized'
      };
    }
    // في حالة الخطأ، نسمح بالمتابعة (fallback)
    return { valid: true, fallback: true };
  }
}

/**
 * إضافة fingerprint للـ request
 */
export async function getAttendancePayload(basePayload) {
  const fingerprint = await generateFingerprint();
  return {
    ...basePayload,
    fingerprint
  };
}
