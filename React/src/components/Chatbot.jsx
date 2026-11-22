import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, Trash2, ShieldAlert } from 'lucide-react';
import { sendChatMessage } from '../utils/api';

export default function Chatbot({
  profile,
  mealPlan,
  completedMeals,
  waterIntake,
  onChatAction
}) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Initialize messages from localStorage or default
  useEffect(() => {
    const saved = localStorage.getItem('nutriguide_chat_history');
    if (saved) {
      setMessages(JSON.parse(saved));
    } else {
      setMessages([
        {
          id: 'welcome',
          role: 'model',
          text: `Hi ${profile?.name || 'there'}! 👋 I'm your NutriGuide AI Diet Coach. I have access to your ${profile?.dietType || ''} profile and your current meal plan. How can I help you reach your ${profile?.goal === 'lose' ? 'weight loss' : profile?.goal === 'gain' ? 'weight gain' : 'fitness'} goals today?`,
          timestamp: new Date().toISOString()
        }
      ]);
    }
  }, [profile]);

  // Save messages to local storage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('nutriguide_chat_history', JSON.stringify(messages));
    }
  }, [messages]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (textToSend) => {
    const text = textToSend || inputValue.trim();
    if (!text) return;

    if (!textToSend) {
      setInputValue('');
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      text: text,
      timestamp: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Map message history to api format (strip ids and timestamps)
      const chatHistory = messages.map((m) => ({
        role: m.role,
        text: m.text
      }));

      // Call API
      const result = await sendChatMessage(
        text,
        chatHistory,
        profile,
        mealPlan,
        completedMeals,
        waterIntake
      );

      const botMessage = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        text: result.reply || "I'm sorry, I encountered an issue parsing that request.",
        timestamp: new Date().toISOString()
      };

      setMessages((prev) => [...prev, botMessage]);

      // If there is an action triggered, dispatch it to App
      if (result.action && onChatAction) {
        onChatAction(result.action);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        text: "Sorry, I couldn't reach the AI coach server. Please make sure the Python Flask backend is running on http://localhost:5000.",
        isError: true,
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear your conversation history?')) {
      const defaultMsg = [
        {
          id: 'welcome',
          role: 'model',
          text: `Hi ${profile?.name || 'there'}! 👋 I'm your NutriGuide AI Diet Coach. How can I help you today?`,
          timestamp: new Date().toISOString()
        }
      ];
      setMessages(defaultMsg);
      localStorage.setItem('nutriguide_chat_history', JSON.stringify(defaultMsg));
    }
  };

  const suggestions = [
    { label: '🥛 Add 250ml Water', query: 'Log 250ml water' },
    { label: '🍳 Check Breakfast eaten', query: 'I ate my breakfast' },
    { label: '🍲 Swap Lunch recipe', query: 'Swap my lunch recipe' },
    { label: '🛒 Show Shopping List', query: 'Show me my shopping list' },
    { label: '📊 View Calorie Goal', query: 'What is my current calorie target?' }
  ];

  return (
    <div className="chat-container glass-panel" style={{ height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      
      {/* Chat Header */}
      <div className="chat-header" style={{ padding: '1rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--glass-bg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="avatar" style={{ background: 'var(--primary-glow)', color: 'var(--primary)', width: '2.5rem', height: '2.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }}>
            <Bot size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, fontFamily: 'var(--font-heading)', margin: 0 }}>AI Diet Coach</h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ width: '6px', height: '6px', background: 'var(--primary)', borderRadius: '50%', display: 'inline-block' }}></span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Online & Ready</span>
            </div>
          </div>
        </div>
        <button 
          onClick={handleClearHistory} 
          className="btn btn-ghost" 
          title="Clear Conversation"
          style={{ padding: '0.5rem', color: 'var(--text-muted)' }}
        >
          <Trash2 size={16} />
        </button>
      </div>

      {/* Messages area */}
      <div className="chat-messages" style={{ flexGrow: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div 
              key={msg.id} 
              style={{ 
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: '75%',
                display: 'flex',
                gap: '0.5rem',
                flexDirection: isUser ? 'row-reverse' : 'row'
              }}
            >
              <div 
                className="avatar" 
                style={{ 
                  background: isUser ? 'var(--primary-hover)' : 'var(--border-color)', 
                  color: isUser ? 'white' : 'var(--text-main)', 
                  width: '2rem', 
                  height: '2rem', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  borderRadius: '50%',
                  flexShrink: 0,
                  fontSize: '0.8rem'
                }}
              >
                {isUser ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div 
                style={{ 
                  background: msg.isError ? 'var(--accent-glow)' : isUser ? 'var(--primary)' : 'var(--bg-card)', 
                  color: isUser ? 'white' : 'var(--text-main)', 
                  padding: '0.8rem 1.2rem', 
                  borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                  boxShadow: 'var(--shadow-sm)',
                  border: msg.isError ? '1px solid var(--accent)' : '1px solid var(--border-color)',
                  whiteSpace: 'pre-wrap',
                  fontSize: '0.9rem'
                }}
              >
                {msg.isError && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--accent)', fontWeight: 600, marginBottom: '0.25rem' }}>
                    <ShieldAlert size={14} />
                    <span>Connection Error</span>
                  </div>
                )}
                {msg.text}
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div style={{ alignSelf: 'flex-start', display: 'flex', gap: '0.5rem' }}>
            <div className="avatar" style={{ background: 'var(--border-color)', color: 'var(--text-main)', width: '2rem', height: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }}>
              <Bot size={14} />
            </div>
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', padding: '0.8rem 1.2rem', borderRadius: '16px 16px 16px 2px', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span className="dot-blink" style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', display: 'inline-block' }}></span>
              <span className="dot-blink" style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', display: 'inline-block', animationDelay: '0.2s' }}></span>
              <span className="dot-blink" style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%', display: 'inline-block', animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestion Chips */}
      {messages.length < 5 && (
        <div className="suggestions-container" style={{ padding: '0.5rem 1.5rem', display: 'flex', gap: '0.5rem', overflowX: 'auto', whiteSpace: 'nowrap', background: 'transparent' }}>
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(s.query)}
              className="btn btn-ghost"
              style={{
                fontSize: '0.78rem',
                padding: '0.35rem 0.75rem',
                border: '1px solid var(--border-color)',
                borderRadius: '20px',
                background: 'var(--bg-card)',
                color: 'var(--text-main)',
                flexShrink: 0
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {/* Chat Input form */}
      <form 
        onSubmit={(e) => { e.preventDefault(); handleSend(); }} 
        style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--border-color)', background: 'var(--glass-bg)', display: 'flex', gap: '0.75rem', alignItems: 'center' }}
      >
        <div style={{ position: 'relative', flexGrow: 1 }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your diet question or request (e.g. 'I drank 500ml water')..."
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              borderRadius: '24px',
              border: '1px solid var(--border-color)',
              background: 'var(--bg-card)',
              color: 'var(--text-main)',
              fontSize: '0.9rem',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
          />
          <div style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--primary)', opacity: 0.5, display: 'flex', alignItems: 'center' }}>
            <Sparkles size={16} />
          </div>
        </div>
        <button 
          type="submit" 
          disabled={isLoading || !inputValue.trim()}
          className="btn btn-primary"
          style={{ borderRadius: '50%', width: '2.5rem', height: '2.5rem', minWidth: '2.5rem', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <Send size={16} />
        </button>
      </form>

      {/* Embedded dots animation style */}
      <style>{`
        .dot-blink {
          animation: dotBlink 1.4s infinite both;
        }
        @keyframes dotBlink {
          0% { opacity: .2; }
          20% { opacity: 1; }
          100% { opacity: .2; }
        }
      `}</style>
    </div>
  );
}
