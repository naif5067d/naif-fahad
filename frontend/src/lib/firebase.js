// Firebase Configuration for DAR AL CODE HR OS
import { initializeApp, getApps } from 'firebase/app';
import { getMessaging, getToken, onMessage, isSupported } from 'firebase/messaging';

const firebaseConfig = {
  apiKey: "AIzaSyC4bbi69690imeyWb6fYcCZglZmAaFIF6w",
  authDomain: "alcode-co.firebaseapp.com",
  projectId: "alcode-co",
  storageBucket: "alcode-co.appspot.com",
  messagingSenderId: "13877030585",
  appId: "1:13877030585:web:e0544ff362a647f8c27568"
};

// Initialize Firebase
let app = null;
let messaging = null;

export const initializeFirebase = async () => {
  if (getApps().length === 0) {
    app = initializeApp(firebaseConfig);
  } else {
    app = getApps()[0];
  }
  
  // Check if messaging is supported
  const supported = await isSupported();
  if (supported) {
    messaging = getMessaging(app);
  }
  
  return { app, messaging, supported };
};

export const getFirebaseMessaging = () => messaging;

export const getFirebaseApp = () => app;

export { firebaseConfig };
