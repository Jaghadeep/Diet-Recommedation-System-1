import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// Check if the credentials are set and not placeholder values
const isConfigured = !!(
  firebaseConfig.apiKey && 
  !firebaseConfig.apiKey.startsWith('your_') && 
  firebaseConfig.projectId && 
  !firebaseConfig.projectId.startsWith('your_')
);

let app;
let auth;
let db;

if (isConfigured) {
  try {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
    db = getFirestore(app);
  } catch (error) {
    console.error('Firebase initialization failed:', error);
  }
} else {
  console.warn(
    'Firebase is not configured yet. Please replace the placeholder values in .env.local with your real credentials. ' +
    'Falling back to browser localStorage offline mode.'
  );
}

export { auth, db, isConfigured };
