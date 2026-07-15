import { useState, useEffect } from 'react';
import Onboarding from './components/Onboarding';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import MealPlanner from './components/MealPlanner';
import RecipeLibrary from './components/RecipeLibrary';
import ShoppingList from './components/ShoppingList';
import DataTables from './components/DataTables';
import RecipeModal from './components/RecipeModal';
import { recipes } from './data/recipes';
import { fetchState, saveState, resetState } from './utils/api';
import './App.css';

export default function App() {
  const [profile, setProfile] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [mealPlan, setMealPlan] = useState(null);
  
  const [completedMeals, setCompletedMeals] = useState({ 
    breakfast: false, 
    lunch: false, 
    dinner: false, 
    snack: false 
  });
  
  const [waterIntake, setWaterIntake] = useState(0);
  const [shoppingCheckedItems, setShoppingCheckedItems] = useState({});
  const [selectedRecipe, setSelectedRecipe] = useState(null);

  const [isLoaded, setIsLoaded] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isOffline, setIsOffline] = useState(false);

  // Load state from backend on mount, fallback to local storage
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const data = await fetchState();
        if (!isMounted) return;
        if (data) {
          setProfile(data.profile);
          setMealPlan(data.mealPlan);
          setCompletedMeals(data.completedMeals || { breakfast: false, lunch: false, dinner: false, snack: false });
          setWaterIntake(data.waterIntake || 0);
          setShoppingCheckedItems(data.shoppingCheckedItems || {});
        }
        setIsOffline(false);
      } catch (err) {
        console.warn('Backend server offline. Falling back to local storage.', err);
        if (!isMounted) return;
        setIsOffline(true);
        // Fallback to localStorage
        const savedProfile = localStorage.getItem('nutriguide_profile');
        const savedMealPlan = localStorage.getItem('nutriguide_mealplan');
        const savedCompletedMeals = localStorage.getItem('nutriguide_completed_meals');
        const savedWater = localStorage.getItem('nutriguide_water');
        const savedShopping = localStorage.getItem('nutriguide_shopping_checked');

        if (savedProfile) setProfile(JSON.parse(savedProfile));
        if (savedMealPlan) setMealPlan(JSON.parse(savedMealPlan));
        if (savedCompletedMeals) setCompletedMeals(JSON.parse(savedCompletedMeals));
        if (savedWater) setWaterIntake(parseInt(savedWater, 10));
        if (savedShopping) setShoppingCheckedItems(JSON.parse(savedShopping));
      } finally {
        if (isMounted) setIsLoaded(true);
      }
    }
    loadData();
    return () => { isMounted = false; };
  }, []);

  // Sync to Local Storage (always run as an instant local cache)
  useEffect(() => {
    if (!isLoaded) return;
    if (profile) {
      localStorage.setItem('nutriguide_profile', JSON.stringify(profile));
    } else {
      localStorage.removeItem('nutriguide_profile');
    }
  }, [profile, isLoaded]);

  useEffect(() => {
    if (!isLoaded) return;
    if (mealPlan) {
      localStorage.setItem('nutriguide_mealplan', JSON.stringify(mealPlan));
    } else {
      localStorage.removeItem('nutriguide_mealplan');
    }
  }, [mealPlan, isLoaded]);

  useEffect(() => {
    if (!isLoaded) return;
    localStorage.setItem('nutriguide_completed_meals', JSON.stringify(completedMeals));
  }, [completedMeals, isLoaded]);

  useEffect(() => {
    if (!isLoaded) return;
    localStorage.setItem('nutriguide_water', waterIntake.toString());
  }, [waterIntake, isLoaded]);

  useEffect(() => {
    if (!isLoaded) return;
    localStorage.setItem('nutriguide_shopping_checked', JSON.stringify(shoppingCheckedItems));
  }, [shoppingCheckedItems, isLoaded]);

  // Debounced Sync to backend server
  useEffect(() => {
    if (!isLoaded) return;

    // Skip cloud saving if server is known to be offline
    if (isOffline) return;

    const timer = setTimeout(async () => {
      setIsSyncing(true);
      try {
        await saveState({
          profile,
          mealPlan,
          completedMeals,
          waterIntake,
          shoppingCheckedItems
        });
        setIsOffline(false);
      } catch (err) {
        console.error('Failed to sync state changes to backend:', err);
        setIsOffline(true);
      } finally {
        setIsSyncing(false);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [profile, mealPlan, completedMeals, waterIntake, shoppingCheckedItems, isLoaded, isOffline]);

  // Helper: Filter recipes by user's diet selection
  const getEligibleRecipes = (dietType, mealType) => {
    let filtered = recipes.filter(r => r.mealType === mealType);
    
    if (dietType === 'Balanced') {
      return filtered;
    }
    
    return filtered.filter(r => r.tags.some(tag => {
      if (dietType === 'Vegetarian') {
        return tag === 'Vegetarian' || tag === 'Vegan';
      }
      return tag.toLowerCase() === dietType.toLowerCase();
    }));
  };

  // Generate initial meal plan matching calorie targets and diet
  const generateInitialMealPlan = (userProfile) => {
    const mealTypes = ['breakfast', 'lunch', 'dinner', 'snack'];
    const newPlan = {};
    
    mealTypes.forEach((type) => {
      const eligible = getEligibleRecipes(userProfile.dietType, type);
      if (eligible.length > 0) {
        newPlan[type] = eligible[Math.floor(Math.random() * eligible.length)];
      } else {
        // Fallback to any recipe of that meal type
        const fallbackList = recipes.filter(r => r.mealType === type);
        newPlan[type] = fallbackList[Math.floor(Math.random() * fallbackList.length)];
      }
    });

    setMealPlan(newPlan);
    setCompletedMeals({ breakfast: false, lunch: false, dinner: false, snack: false });
    setShoppingCheckedItems({});
    setWaterIntake(0);
  };

  const handleOnboardingComplete = (calculatedProfile) => {
    setProfile(calculatedProfile);
    generateInitialMealPlan(calculatedProfile);
    setActiveTab('dashboard');
  };

  const handleResetProfile = async () => {
    if (window.confirm('Are you sure you want to reset your profile and clear all logged data?')) {
      setProfile(null);
      setMealPlan(null);
      setCompletedMeals({ breakfast: false, lunch: false, dinner: false, snack: false });
      setWaterIntake(0);
      setShoppingCheckedItems({});
      localStorage.clear();
      
      try {
        await resetState();
        setIsOffline(false);
      } catch (err) {
        console.error('Failed to reset state on backend:', err);
        setIsOffline(true);
      }
    }
  };

  const handleSwapMeal = (mealType) => {
    if (!profile) return;
    
    const eligible = getEligibleRecipes(profile.dietType, mealType);
    const currentMeal = mealPlan[mealType];
    
    // Filter out the current recipe to ensure we select a different one (if possible)
    const alternatives = eligible.filter(r => r.id !== currentMeal?.id);
    const pool = alternatives.length > 0 ? alternatives : eligible;
    
    const nextRecipe = pool[Math.floor(Math.random() * pool.length)];
    
    setMealPlan((prev) => ({
      ...prev,
      [mealType]: nextRecipe
    }));

    // Reset this specific meal as not eaten
    setCompletedMeals((prev) => ({
      ...prev,
      [mealType]: false
    }));
  };

  const handleToggleMealEaten = (mealType) => {
    setCompletedMeals((prev) => ({
      ...prev,
      [mealType]: !prev[mealType]
    }));
  };

  const handleToggleShoppingItem = (itemKey) => {
    setShoppingCheckedItems((prev) => ({
      ...prev,
      [itemKey]: !prev[itemKey]
    }));
  };

  const handleClearShoppingChecklist = () => {
    setShoppingCheckedItems({});
  };

  // Render Page Content based on selected tab
  const renderTabContent = () => {
    switch (activeTab) {
      case 'planner':
        return (
          <MealPlanner
            profile={profile}
            mealPlan={mealPlan}
            completedMeals={completedMeals}
            toggleMealEaten={handleToggleMealEaten}
            onSwapMeal={handleSwapMeal}
            onViewRecipe={setSelectedRecipe}
          />
        );
      case 'recipes':
        return <RecipeLibrary onViewRecipe={setSelectedRecipe} />;
      case 'shopping':
        return (
          <ShoppingList
            mealPlan={mealPlan}
            checkedItems={shoppingCheckedItems}
            toggleCheckedItem={handleToggleShoppingItem}
            clearCheckedItems={handleClearShoppingChecklist}
          />
        );
      case 'tables':
        return (
          <DataTables
            profile={profile}
            mealPlan={mealPlan}
            completedMeals={completedMeals}
            waterIntake={waterIntake}
            shoppingCheckedItems={shoppingCheckedItems}
            onViewRecipe={setSelectedRecipe}
          />
        );
      case 'dashboard':
      default:
        return (
          <Dashboard
            profile={profile}
            mealPlan={mealPlan}
            completedMeals={completedMeals}
            toggleMealEaten={handleToggleMealEaten}
            waterIntake={waterIntake}
            setWaterIntake={setWaterIntake}
          />
        );
    }
  };

  if (!isLoaded) {
    return (
      <main style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '1rem', gap: '1rem' }}>
        <div className="animate-spin" style={{ width: '2.5rem', height: '2.5rem', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%' }}></div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Connecting to database...</p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
        <Onboarding onComplete={handleOnboardingComplete} />
      </main>
    );
  }

  return (
    <div className="app-container">
      {/* Navigation sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        profile={profile}
        onReset={handleResetProfile}
        isSyncing={isSyncing}
        isOffline={isOffline}
      />

      {/* Main viewport panels */}
      <main className="main-content">
        {renderTabContent()}
      </main>

      {/* Detailed Recipe Overlay Modal */}
      {selectedRecipe && (
        <RecipeModal
          recipe={selectedRecipe}
          onClose={() => setSelectedRecipe(null)}
        />
      )}
    </div>
  );
}
