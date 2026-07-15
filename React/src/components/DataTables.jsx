import { useState } from 'react';
import { 
  User, 
  Utensils, 
  CheckCircle2, 
  Droplet, 
  ShoppingCart, 
  Database,
  ExternalLink,
  Info
} from 'lucide-react';

export default function DataTables({ 
  profile, 
  mealPlan, 
  completedMeals, 
  waterIntake, 
  shoppingCheckedItems,
  onViewRecipe 
}) {
  const [activeSubTab, setActiveSubTab] = useState('profile');

  const subTabs = [
    { id: 'profile', label: 'User Profile', icon: User },
    { id: 'mealPlan', label: 'Weekly Meal Plan', icon: Utensils },
    { id: 'completedMeals', label: 'Meal Tracker Status', icon: CheckCircle2 },
    { id: 'water', label: 'Water Logging', icon: Droplet },
    { id: 'shopping', label: 'Shopping Checklist', icon: ShoppingCart },
  ];

  // Compile ingredients list for shopping checklist view
  const compileIngredients = () => {
    if (!mealPlan) return [];
    const totals = {};
    
    // Simple helper to match the categorization from ShoppingList.jsx
    const categorizeIngredient = (name) => {
      const nameLower = name.toLowerCase();
      const produce = ['avocado', 'spinach', 'berry', 'berries', 'banana', 'lemon', 'chives', 'romaine', 'lettuce', 'tomato', 'cucumber', 'onion', 'garlic', 'carrot', 'celery', 'broccoli', 'asparagus', 'ginger', 'bell pepper', 'peppers'];
      const proteins = ['egg', 'eggs', 'tofu', 'chicken', 'salmon', 'turkey', 'beef', 'steak', 'bacon', 'whey', 'shrimp'];
      const dairy = ['yogurt', 'mayonnaise', 'parmesan', 'cheese', 'butter', 'almond milk', 'coconut milk', 'cream', 'milk'];
      
      if (produce.some(kw => nameLower.includes(kw))) return 'Produce 🥦';
      if (proteins.some(kw => nameLower.includes(kw))) return 'Proteins 🥩';
      if (dairy.some(kw => nameLower.includes(kw))) return 'Dairy & Alts 🥛';
      return 'Pantry/Spices 🧂';
    };

    Object.values(mealPlan).forEach((recipe) => {
      if (!recipe) return;
      recipe.ingredients.forEach((ing) => {
        const key = `${ing.name.toLowerCase().trim()}_${ing.unit.toLowerCase().trim()}`;
        if (totals[key]) {
          totals[key].quantity += ing.quantity;
        } else {
          totals[key] = {
            name: ing.name.trim(),
            quantity: ing.quantity,
            unit: ing.unit.trim(),
            category: categorizeIngredient(ing.name),
            key: key
          };
        }
      });
    });
    return Object.values(totals);
  };

  const ingredients = compileIngredients();

  const getGoalLabel = (goal) => {
    switch (goal) {
      case 'lose': return 'Weight Loss (Caloric Deficit)';
      case 'gain': return 'Weight Gain (Caloric Surplus)';
      case 'maintain': default: return 'Maintain Weight (TDEE Balance)';
    }
  };

  const renderTableContent = () => {
    switch (activeSubTab) {
      case 'profile':
        if (!profile) return <p style={{ color: 'var(--text-muted)' }}>No profile data found.</p>;
        const profileData = [
          { label: 'Full Name', value: profile.name },
          { label: 'Gender', value: profile.gender.charAt(0).toUpperCase() + profile.gender.slice(1) },
          { label: 'Age', value: `${profile.age} years` },
          { label: 'Weight', value: `${profile.weight} kg` },
          { label: 'Height', value: `${profile.height} cm` },
          { label: 'Activity Level', value: profile.activityLevel.charAt(0).toUpperCase() + profile.activityLevel.slice(1) },
          { label: 'Primary Goal', value: getGoalLabel(profile.goal) },
          { label: 'Diet Type Choice', value: profile.dietType },
          { label: 'Basal Metabolic Rate (BMR)', value: `${profile.bmr} kcal/day` },
          { label: 'Total Daily Energy Expenditure (TDEE)', value: `${profile.tdee} kcal/day` },
          { label: 'Target Calorie Intake', value: `${profile.targetCalories} kcal/day` },
          { label: 'Target Protein Intake', value: `${profile.targetProtein} g` },
          { label: 'Target Carbs Intake', value: `${profile.targetCarbs} g` },
          { label: 'Target Fat Intake', value: `${profile.targetFat} g` },
        ];

        return (
          <div className="data-table-container animate-fade">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Stored Value</th>
                </tr>
              </thead>
              <tbody>
                {profileData.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, color: 'var(--text-muted)', width: '40%' }}>{row.label}</td>
                    <td style={{ color: 'var(--text-main)' }}>{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      case 'mealPlan':
        if (!mealPlan) {
          return (
            <div className="glass-card" style={{ padding: '2rem', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-muted)' }}>No meal plan generated yet.</p>
            </div>
          );
        }

        const meals = [
          { key: 'breakfast', label: 'Breakfast 🍳', recipe: mealPlan.breakfast },
          { key: 'lunch', label: 'Lunch 🥗', recipe: mealPlan.lunch },
          { key: 'dinner', label: 'Dinner 🥩', recipe: mealPlan.dinner },
          { key: 'snack', label: 'Snack 🍎', recipe: mealPlan.snack },
        ];

        return (
          <div className="data-table-container animate-fade">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Meal Slot</th>
                  <th>Recipe Name</th>
                  <th>Calories</th>
                  <th>Macros (P / C / F)</th>
                  <th>Time Needed</th>
                  <th>Difficulty</th>
                  <th style={{ textAlign: 'center' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {meals.map((item) => (
                  <tr key={item.key}>
                    <td style={{ fontWeight: 600 }}>{item.label}</td>
                    <td>
                      {item.recipe ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span>{item.recipe.image}</span>
                          <span style={{ fontWeight: 500 }}>{item.recipe.name}</span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Not scheduled</span>
                      )}
                    </td>
                    <td>{item.recipe ? `${item.recipe.calories} kcal` : '-'}</td>
                    <td>
                      {item.recipe ? (
                        <span style={{ fontSize: '0.85rem' }}>
                          <strong>{item.recipe.protein}g</strong> P • <strong>{item.recipe.carbs}g</strong> C • <strong>{item.recipe.fat}g</strong> F
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>{item.recipe ? `${item.recipe.prepTime} prep / ${item.recipe.cookTime} cook` : '-'}</td>
                    <td>{item.recipe ? item.recipe.difficulty : '-'}</td>
                    <td style={{ textAlign: 'center' }}>
                      {item.recipe ? (
                        <button 
                          onClick={() => onViewRecipe(item.recipe)}
                          className="btn btn-ghost"
                          style={{ padding: '0.25rem 0.5rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                          <ExternalLink size={14} /> View
                        </button>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      case 'completedMeals':
        const completedData = [
          { label: 'Breakfast 🍳', calorieEstimate: mealPlan?.breakfast?.calories || 0, status: completedMeals.breakfast },
          { label: 'Lunch 🥗', calorieEstimate: mealPlan?.lunch?.calories || 0, status: completedMeals.lunch },
          { label: 'Dinner 🥩', calorieEstimate: mealPlan?.dinner?.calories || 0, status: completedMeals.dinner },
          { label: 'Snack 🍎', calorieEstimate: mealPlan?.snack?.calories || 0, status: completedMeals.snack },
        ];

        return (
          <div className="data-table-container animate-fade">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Meal Slot</th>
                  <th>Calorie Weight</th>
                  <th>Consumption Log Status</th>
                </tr>
              </thead>
              <tbody>
                {completedData.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{row.label}</td>
                    <td>{row.calorieEstimate > 0 ? `${row.calorieEstimate} kcal` : 'N/A'}</td>
                    <td>
                      <span 
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          padding: '0.25rem 0.75rem',
                          borderRadius: '12px',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          backgroundColor: row.status ? 'var(--primary-glow)' : 'var(--accent-glow)',
                          color: row.status ? 'var(--primary)' : 'var(--accent)'
                        }}
                      >
                        {row.status ? 'Eaten & Tracked' : 'Not Eaten'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      case 'water':
        const waterData = [
          { label: 'Daily Water Goal', value: '2500 mL (84.5 fl oz)' },
          { label: 'Current Logged Intake', value: `${waterIntake} mL` },
          { label: 'Remaining Balance', value: `${Math.max(0, 2500 - waterIntake)} mL` },
          { label: 'Hydration Percentage', value: `${Math.min(100, Math.round((waterIntake / 2500) * 100))}%` },
          { label: 'Status', value: waterIntake >= 2500 ? 'Fully Hydrated 💧' : 'Still Dehydrated 🏜️' },
        ];

        return (
          <div className="data-table-container animate-fade">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Hydration Metric</th>
                  <th>Logged Quantity / Status</th>
                </tr>
              </thead>
              <tbody>
                {waterData.map((row, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, color: 'var(--text-muted)', width: '50%' }}>{row.label}</td>
                    <td style={{ fontWeight: 600, color: row.label === 'Status' && waterIntake >= 2500 ? 'var(--primary)' : 'var(--text-main)' }}>{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );

      case 'shopping':
        if (ingredients.length === 0) {
          return (
            <div className="glass-card" style={{ padding: '2rem', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-muted)' }}>No ingredients compiled. Generate a meal plan to populate this checklist.</p>
            </div>
          );
        }

        return (
          <div className="data-table-container animate-fade">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ingredient</th>
                  <th>Quantity / Unit</th>
                  <th>Category</th>
                  <th>Checklist State</th>
                </tr>
              </thead>
              <tbody>
                {ingredients.map((item) => {
                  const isChecked = !!shoppingCheckedItems[item.key];
                  return (
                    <tr key={item.key} style={{ opacity: isChecked ? 0.6 : 1 }}>
                      <td style={{ textDecoration: isChecked ? 'line-through' : 'none', fontWeight: 500 }}>
                        {item.name}
                      </td>
                      <td>
                        {parseFloat(item.quantity.toFixed(2))} {item.unit}
                      </td>
                      <td>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          {item.category}
                        </span>
                      </td>
                      <td>
                        <span 
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            color: isChecked ? 'var(--primary)' : 'var(--text-muted)'
                          }}
                        >
                          {isChecked ? 'Checked (Purchased)' : 'Pending'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="animate-fade">
      <div className="dashboard-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '2.0rem', margin: 0, fontFamily: 'var(--font-heading)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Database className="logo-icon" style={{ width: '2.0rem', height: '2.0rem' }} /> Stored Data Tables
          </h1>
          <p style={{ color: 'var(--text-muted)' }}>
            Direct interactive table views of all state parameters stored in the database.
          </p>
        </div>
      </div>

      {/* Subnavigation tab bars */}
      <div className="subnav-tabs">
        {subTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`subnav-tab ${activeSubTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveSubTab(tab.id)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="glass-card" style={{ padding: '1.5rem', marginTop: '1rem', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', padding: '0.75rem', borderRadius: '8px', backgroundColor: 'var(--primary-glow)', color: 'var(--text-main)', fontSize: '0.85rem' }}>
          <Info size={16} style={{ color: 'var(--primary)', flexShrink: 0 }} />
          <span>
            This screen displays real-time values compiled from your local cache and synchronized with the Express backend or Firebase Firestore.
          </span>
        </div>

        {renderTableContent()}
      </div>
    </div>
  );
}
