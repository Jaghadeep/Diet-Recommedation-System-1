import { auth, db, isConfigured } from './firebase';
import { signInAnonymously } from 'firebase/auth';
import { doc, getDoc, setDoc, deleteDoc } from 'firebase/firestore';

const BACKEND_URL = 'http://localhost:5000/api';

// Shared auth promise helper to prevent multiple concurrent login requests
let authPromise = null;

/**
 * Ensures that the user is authenticated anonymously and returns their UID.
 * @returns {Promise<string>} - User's unique authentication ID.
 */
function ensureAuth() {
  if (!isConfigured) {
    return Promise.reject(new Error('Firebase Web SDK is not configured.'));
  }

  // Already authenticated
  if (auth.currentUser) {
    return Promise.resolve(auth.currentUser.uid);
  }

  // Auth is already in progress, join the existing promise
  if (authPromise) {
    return authPromise;
  }

  authPromise = signInAnonymously(auth)
    .then((userCredential) => {
      authPromise = null;
      return userCredential.user.uid;
    })
    .catch((error) => {
      authPromise = null;
      console.error('Firebase Anonymous Auth failed:', error);
      throw error;
    });

  return authPromise;
}

/**
 * Fetch the complete user database state.
 */
export async function fetchState() {
  if (!isConfigured) {
    // Call the local SQLite backend
    const response = await fetch(`${BACKEND_URL}/state`);
    if (!response.ok) {
      throw new Error('Failed to fetch state from local SQLite backend');
    }
    return await response.json();
  }

  const uid = await ensureAuth();
  const userDocRef = doc(db, 'users', uid);
  const docSnap = await getDoc(userDocRef);

  if (docSnap.exists()) {
    return docSnap.data();
  } else {
    // Return empty default state structure if new document
    return {
      profile: null,
      mealPlan: null,
      completedMeals: { breakfast: false, lunch: false, dinner: false, snack: false },
      waterIntake: 0,
      shoppingCheckedItems: {}
    };
  }
}

/**
 * Save state updates to the database.
 * @param {Object} stateUpdate - The slice of state to save/merge.
 */
export async function saveState(stateUpdate) {
  if (!isConfigured) {
    // Save to the local SQLite backend
    const response = await fetch(`${BACKEND_URL}/state`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(stateUpdate),
    });
    if (!response.ok) {
      throw new Error('Failed to save state to local SQLite backend');
    }
    const result = await response.json();
    return result.state || stateUpdate;
  }

  const uid = await ensureAuth();
  const userDocRef = doc(db, 'users', uid);

  // Write changes with merge = true to support incremental updates
  await setDoc(userDocRef, stateUpdate, { merge: true });
  return stateUpdate;
}

/**
 * Delete the user's configuration and records document in the database.
 */
export async function resetState() {
  if (!isConfigured) {
    // Reset the local SQLite backend
    const response = await fetch(`${BACKEND_URL}/reset`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to reset state on local SQLite backend');
    }
    const result = await response.json();
    return result.state || {
      profile: null,
      mealPlan: null,
      completedMeals: { breakfast: false, lunch: false, dinner: false, snack: false },
      waterIntake: 0,
      shoppingCheckedItems: {}
    };
  }

  const uid = await ensureAuth();
  const userDocRef = doc(db, 'users', uid);
  await deleteDoc(userDocRef);

  return {
    profile: null,
    mealPlan: null,
    completedMeals: { breakfast: false, lunch: false, dinner: false, snack: false },
    waterIntake: 0,
    shoppingCheckedItems: {}
  };
}

/**
 * Send a chat message to the Diet Coach Chatbot.
 */
export async function sendChatMessage(message, history, profile, mealPlan, completedMeals, waterIntake) {
  const response = await fetch(`${BACKEND_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      history,
      profile,
      mealPlan,
      completedMeals,
      waterIntake
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to communicate with AI Coach backend');
  }

  return await response.json();
}

