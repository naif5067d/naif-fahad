// Push Notifications Service for DAR AL CODE HR OS
// Uses Web Push API (no Firebase required)

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

class PushNotificationService {
  constructor() {
    this.swRegistration = null;
    this.subscription = null;
    this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
  }

  // Check if push notifications are supported
  checkSupport() {
    if (!this.isSupported) {
      console.log('[Push] Not supported in this browser');
      return { supported: false, reason: 'browser_not_supported' };
    }
    
    if (Notification.permission === 'denied') {
      console.log('[Push] Permission denied');
      return { supported: true, reason: 'permission_denied' };
    }

    return { supported: true, reason: 'ok' };
  }

  // Register service worker
  async registerServiceWorker() {
    if (!this.isSupported) {
      throw new Error('Push notifications not supported');
    }

    try {
      this.swRegistration = await navigator.serviceWorker.register('/sw.js');
      console.log('[Push] Service Worker registered:', this.swRegistration);
      
      // Wait for service worker to be ready
      await navigator.serviceWorker.ready;
      console.log('[Push] Service Worker ready');
      
      return this.swRegistration;
    } catch (error) {
      console.error('[Push] Service Worker registration failed:', error);
      throw error;
    }
  }

  // Request notification permission
  async requestPermission() {
    const permission = await Notification.requestPermission();
    console.log('[Push] Permission result:', permission);
    return permission;
  }

  // Subscribe to push notifications
  async subscribe(userId) {
    try {
      // Get VAPID public key from server
      const vapidResponse = await fetch(`${API_URL}/api/push/vapid-key`);
      if (!vapidResponse.ok) {
        throw new Error('Failed to get VAPID key');
      }
      const { publicKey } = await vapidResponse.json();
      
      // Convert VAPID key to Uint8Array
      const applicationServerKey = this.urlBase64ToUint8Array(publicKey);

      // Subscribe to push manager
      this.subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey
      });

      console.log('[Push] Subscribed:', this.subscription);

      // Send subscription to server
      const saveResponse = await fetch(`${API_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: userId,
          subscription: this.subscription.toJSON()
        })
      });

      if (!saveResponse.ok) {
        throw new Error('Failed to save subscription');
      }

      console.log('[Push] Subscription saved to server');
      return this.subscription;
    } catch (error) {
      console.error('[Push] Subscription failed:', error);
      throw error;
    }
  }

  // Unsubscribe from push notifications
  async unsubscribe(userId) {
    try {
      if (this.subscription) {
        await this.subscription.unsubscribe();
        
        // Notify server
        await fetch(`${API_URL}/api/push/unsubscribe`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({ user_id: userId })
        });
        
        this.subscription = null;
        console.log('[Push] Unsubscribed');
      }
    } catch (error) {
      console.error('[Push] Unsubscribe failed:', error);
      throw error;
    }
  }

  // Check current subscription status
  async getSubscriptionStatus() {
    if (!this.swRegistration) {
      return { subscribed: false, permission: Notification.permission };
    }

    const subscription = await this.swRegistration.pushManager.getSubscription();
    return {
      subscribed: !!subscription,
      permission: Notification.permission,
      subscription
    };
  }

  // Helper: Convert base64 VAPID key to Uint8Array
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Initialize everything
  async initialize(userId) {
    const support = this.checkSupport();
    if (!support.supported) {
      return { success: false, reason: support.reason };
    }

    try {
      // Register service worker
      await this.registerServiceWorker();

      // Check current permission
      if (Notification.permission === 'default') {
        const permission = await this.requestPermission();
        if (permission !== 'granted') {
          return { success: false, reason: 'permission_denied' };
        }
      } else if (Notification.permission === 'denied') {
        return { success: false, reason: 'permission_denied' };
      }

      // Subscribe to push notifications
      await this.subscribe(userId);

      return { success: true, reason: 'subscribed' };
    } catch (error) {
      console.error('[Push] Initialization failed:', error);
      return { success: false, reason: error.message };
    }
  }
}

// Singleton instance
const pushService = new PushNotificationService();

export default pushService;

// Hook for React components
export function usePushNotifications() {
  const [status, setStatus] = useState({
    supported: false,
    permission: 'default',
    subscribed: false,
    loading: true
  });

  useEffect(() => {
    const checkStatus = async () => {
      const support = pushService.checkSupport();
      
      if (support.supported && pushService.swRegistration) {
        const subStatus = await pushService.getSubscriptionStatus();
        setStatus({
          supported: true,
          permission: subStatus.permission,
          subscribed: subStatus.subscribed,
          loading: false
        });
      } else {
        setStatus({
          supported: support.supported,
          permission: Notification.permission,
          subscribed: false,
          loading: false
        });
      }
    };

    checkStatus();
  }, []);

  return status;
}

// Missing import for hook
import { useState, useEffect } from 'react';
