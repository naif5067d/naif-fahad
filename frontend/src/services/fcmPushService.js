// Firebase Cloud Messaging Push Notifications Service
// DAR AL CODE HR OS

import { useState, useEffect } from 'react';
import { getToken, onMessage } from 'firebase/messaging';
import { initializeFirebase, getFirebaseMessaging } from '@/lib/firebase';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

class FCMPushService {
  constructor() {
    this.messaging = null;
    this.token = null;
    this.isSupported = false;
    this.initialized = false;
  }

  async initialize() {
    if (this.initialized) return { success: true, token: this.token };
    
    try {
      const { messaging, supported } = await initializeFirebase();
      this.messaging = messaging;
      this.isSupported = supported;
      
      if (!supported) {
        console.log('[FCM] Not supported in this browser');
        return { success: false, reason: 'not_supported' };
      }

      // Register service worker
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
        console.log('[FCM] Service Worker registered:', registration);
      }

      this.initialized = true;
      return { success: true };
    } catch (error) {
      console.error('[FCM] Initialization failed:', error);
      return { success: false, reason: error.message };
    }
  }

  async requestPermissionAndGetToken(userId) {
    try {
      // Initialize first
      if (!this.initialized) {
        const initResult = await this.initialize();
        if (!initResult.success) return initResult;
      }

      if (!this.messaging) {
        return { success: false, reason: 'messaging_not_available' };
      }

      // Request permission
      const permission = await Notification.requestPermission();
      console.log('[FCM] Permission result:', permission);

      if (permission !== 'granted') {
        return { success: false, reason: 'permission_denied' };
      }

      // Get FCM token
      // Note: You need to get VAPID key from Firebase Console > Project Settings > Cloud Messaging > Web Push certificates
      const token = await getToken(this.messaging, {
        vapidKey: undefined, // Firebase will use default if not provided
        serviceWorkerRegistration: await navigator.serviceWorker.getRegistration('/firebase-messaging-sw.js')
      });

      if (!token) {
        return { success: false, reason: 'no_token' };
      }

      this.token = token;
      console.log('[FCM] Token obtained:', token.substring(0, 20) + '...');

      // Save token to server
      const saveResult = await this.saveTokenToServer(userId, token);
      
      return { success: true, token, saveResult };
    } catch (error) {
      console.error('[FCM] Error getting token:', error);
      return { success: false, reason: error.message };
    }
  }

  async saveTokenToServer(userId, token) {
    try {
      const response = await fetch(`${API_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: userId,
          subscription: {
            endpoint: `fcm:${token}`,
            keys: { fcm_token: token }
          },
          type: 'fcm'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save token');
      }

      console.log('[FCM] Token saved to server');
      return { success: true };
    } catch (error) {
      console.error('[FCM] Failed to save token:', error);
      return { success: false, reason: error.message };
    }
  }

  setupForegroundHandler(callback) {
    if (!this.messaging) return null;

    return onMessage(this.messaging, (payload) => {
      console.log('[FCM] Foreground message received:', payload);
      
      // Show notification manually for foreground
      if (Notification.permission === 'granted') {
        const notification = new Notification(
          payload.notification?.title || 'DAR AL CODE',
          {
            body: payload.notification?.body || '',
            icon: '/icon-192.png',
            tag: payload.data?.tag || 'foreground-notification',
            dir: 'rtl',
            lang: 'ar'
          }
        );

        notification.onclick = () => {
          window.focus();
          if (payload.data?.url) {
            window.location.href = payload.data.url;
          }
          notification.close();
        };
      }

      // Also call custom callback
      if (callback) callback(payload);
    });
  }

  async getStatus() {
    if (!this.isSupported) {
      return { supported: false, permission: 'denied', subscribed: false };
    }

    return {
      supported: true,
      permission: Notification.permission,
      subscribed: !!this.token,
      token: this.token
    };
  }
}

// Singleton instance
const fcmService = new FCMPushService();

export default fcmService;

// React Hook for FCM
export function useFCMNotifications() {
  const [status, setStatus] = useState({
    supported: false,
    permission: 'default',
    subscribed: false,
    loading: true
  });

  useEffect(() => {
    const checkStatus = async () => {
      await fcmService.initialize();
      const currentStatus = await fcmService.getStatus();
      setStatus({
        ...currentStatus,
        loading: false
      });
    };

    checkStatus();
  }, []);

  return status;
}
