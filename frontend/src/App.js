import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  // Environment-specific API URL configuration
  const getApiUrl = () => {
    // Check if REACT_APP_API_URL is explicitly set (for cloud deployment)
    if (process.env.REACT_APP_API_URL) {
      return process.env.REACT_APP_API_URL;
    }
    
    // Check if we're in development mode
    if (process.env.NODE_ENV === 'development') {
      return 'http://localhost:8000';
    }
    
    // Default cloud URL for production builds
    return 'https://hot-travel-backend-377235717727.uc.r.appspot.com';
  };
  
  const API_BASE_URL = getApiUrl();
  const CUSTOMER_API_URL = getApiUrl();  // Use same API for customer profiles
  
  // Debug logging for API URL configuration
  console.log('🔧 API Configuration:', {
    NODE_ENV: process.env.NODE_ENV,
    REACT_APP_API_URL: process.env.REACT_APP_API_URL,
    API_BASE_URL,
    CUSTOMER_API_URL
  });
  
  const [messages, setMessages] = useState([
    {
      type: 'agent',
      content: `Welcome to Smart Trip Assistant! 🌍

I'm your AI-powered travel planning companion. I can help you with:

🎯 **Travel Planning**
• Destination recommendations
• Itinerary planning 
• Hotel and flight searches
• Budget optimization

📋 **Travel Requirements**
• Visa requirements and applications
• Health and vaccination requirements
• Travel insurance recommendations
• Document verification

🏢 **HOT Services**
• Commercial knowledge base
• HOT-specific discounts and offers
• Loyalty program benefits
• Agent assistance

Try asking: "Plan a 7-day trip to Japan" or "What visa do I need for Thailand?"`,
      suggestions: [
        'Plan a 7-day trip to Japan for 2 people',
        'What visa requirements for Thailand?',
        'Find cheap flights to Europe',
        'What vaccinations do I need for India?',
        'Show me HOT travel deals'
      ]
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [customerData, setCustomerData] = useState({
    email_id: '',
    nationality: '',
    passport_number: ''
  });
  const [customerProfile, setCustomerProfile] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (messageText = null) => {
    const query = messageText || inputValue.trim();
    if (!query || isLoading) return;

    // Add user message
    const userMessage = { type: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    
    // Clear input
    setInputValue('');
    setIsLoading(true);

    // Add loading message
    const loadingMessage = { type: 'loading', content: '⏳ Processing your travel request...' };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      // Build request with conversation context
      const requestBody = {
        user_request: query,
        email_id: customerData.email_id || null,
        nationality: customerData.nationality || null,
        passport_number: customerData.passport_number || null
      };

      const response = await fetch(`${API_BASE_URL}/travel/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Remove loading message and add agent response
      setMessages(prev => {
        const filtered = prev.filter(msg => msg.type !== 'loading');
        
        let agentContent = '';
        const responseData = data.data;
        
        if (responseData) {
          // Check for detailed itinerary
          if (responseData.itinerary && responseData.itinerary.data) {
            const itinerary = responseData.itinerary.data;
            agentContent = `🌟 **Your Travel Itinerary**

${itinerary.itinerary_summary || 'Complete travel plan prepared!'}

**📅 Travel Overview:**
• Destination: ${responseData.requirements?.destination || 'Multiple destinations'}
• Duration: ${responseData.requirements?.duration || '7'} days
• Travelers: ${responseData.requirements?.passengers || 1} person(s)
• Dates: ${responseData.requirements?.departure_date || 'TBD'} - ${responseData.requirements?.return_date || 'TBD'}

**✈️ Flight Options:**
${responseData.flight_offers?.length ? `Found ${responseData.flight_offers.length} flight options` : 'Flight search in progress...'}

**🏨 Hotel Options:**  
${responseData.hotel_offers?.length ? `Found ${responseData.hotel_offers.length} hotel options` : 'Hotel search in progress...'}

**🎯 Key Recommendations:**
${itinerary.key_recommendations?.map(rec => `• ${rec}`).join('\n') || '• Personalized recommendations based on your profile'}

**💰 Estimated Budget:**
${itinerary.estimated_cost ? `From $${itinerary.estimated_cost}` : 'Budget calculation in progress...'}

Ready to book or need modifications?`;
          }
          // Check for string response
          else if (typeof responseData === 'string') {
            agentContent = responseData;
          } 
          // Check for basic response property
          else if (responseData.response) {
            agentContent = responseData.response;
          }
          // Check for requirements-only response (partial completion)
          else if (responseData.requirements) {
            agentContent = `✅ **Travel Requirements Processed**

**📋 Your Request Details:**
• Destination: ${responseData.requirements.destination || 'Not specified'}
• Departure: ${responseData.requirements.departure_date || 'TBD'}
• Duration: ${responseData.requirements.duration || 'TBD'} days
• Travelers: ${responseData.requirements.passengers || 1} person(s)
• Budget: ${responseData.requirements.budget ? `$${responseData.requirements.budget} ${responseData.requirements.budget_currency || 'USD'}` : 'Not specified'}

🔄 **Processing your complete itinerary...**
Flight and hotel search in progress. This may take a few moments.`;
          }
          else {
            agentContent = 'Travel request processed successfully! Detailed itinerary is being prepared.';
          }
        } else {
          agentContent = 'Travel request processed successfully! Please try again for detailed results.';
        }

        return [...filtered, {
          type: 'agent',
          content: agentContent,
          suggestions: [
            'Show flight details',
            'Check hotel options', 
            'View complete itinerary',
            'Modify travel dates',
            'Check visa requirements'
          ],
          rawData: responseData // Store raw data for debugging
        }];
      });

    } catch (error) {
      console.error('API Error:', error);
      // Remove loading message and add error
      setMessages(prev => {
        const filtered = prev.filter(msg => msg.type !== 'loading');
        return [...filtered, {
          type: 'agent',
          content: `Sorry, I encountered an error: ${error.message}. Please make sure the API server is running on port 8000.`
        }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      sendMessage();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  // Customer profile functions
  const loadCustomerProfile = async (email) => {
    console.log('🔍 DEBUG: loadCustomerProfile called with email:', email);
    
    if (!email) {
      console.log('❌ DEBUG: No email provided, returning early');
      return;
    }
    
    setIsLoadingProfile(true);
    console.log('⏳ DEBUG: Set loading state to true');
    
    try {
      const apiUrl = `${CUSTOMER_API_URL}/customer/profile/${encodeURIComponent(email)}`;
      console.log('🌐 DEBUG: Making API request to:', apiUrl);
      console.log('🌐 DEBUG: CUSTOMER_API_URL:', CUSTOMER_API_URL);
      
      const response = await fetch(apiUrl);
      console.log('📡 DEBUG: Response status:', response.status);
      console.log('📡 DEBUG: Response ok:', response.ok);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('📦 DEBUG: Raw response data:', JSON.stringify(data, null, 2));
      
      if (data.success) {
        console.log('✅ DEBUG: API returned success=true');
        console.log('📋 DEBUG: Profile data:', JSON.stringify(data.data, null, 2));
        
        setCustomerProfile(data.data);
        setShowSuggestions(true);
        console.log('✅ DEBUG: Set customer profile state');
        
        // Add comprehensive profile message with suggestions
        if (data.data) {
          const profile = data.data;
          console.log('👤 DEBUG: Processing profile for:', profile.customer_email);
          console.log('📊 DEBUG: Suggestions count:', profile.suggestions?.length || 0);
          console.log('📅 DEBUG: Similar events count:', profile.similar_events?.length || 0);
          
          let profileContent = `Welcome back, ${profile.customer_name || 'valued customer'}! 👋

📊 **Customer Profile Summary:**
• Email: ${profile.customer_email}
• Travel History: ${profile.travel_history_count} previous trips
• Available Recommendations: ${profile.suggestions?.length || 0}

🎯 **Personalized Event Recommendations:**`;

          // Add each suggestion with detailed reasoning
          if (profile.suggestions && profile.suggestions.length > 0) {
            console.log('🎯 DEBUG: Adding suggestions to profile content');
            profile.suggestions.forEach((suggestion, index) => {
              profileContent += `

**${index + 1}. ${suggestion.suggestion_title}**
📍 Destination: ${suggestion.destination}
📅 Event Date: ${suggestion.event_date || 'TBD'}
🎪 Event: ${suggestion.event_name || 'Cultural Experience'}
💡 Why this matches: ${suggestion.reasoning}
⭐ Confidence: ${Math.round((suggestion.confidence_score || 0.8) * 100)}%`;
            });
          } else {
            console.log('⚠️ DEBUG: No suggestions found in profile data');
          }

          // Add upcoming similar events
          if (profile.similar_events && profile.similar_events.length > 0) {
            console.log('📅 DEBUG: Adding similar events to profile content');
            profileContent += `

🗓️ **Upcoming Similar Events:**`;
            profile.similar_events.slice(0, 3).forEach((event, index) => {
              profileContent += `
${index + 1}. ${event.event_name} - ${event.destination} (${event.event_date_start})`;
            });
          } else {
            console.log('⚠️ DEBUG: No similar events found in profile data');
          }

          profileContent += `

Would you like me to help plan any of these experiences, or do you have other travel preferences in mind?`;

          const profileMessage = {
            type: 'agent',
            content: profileContent,
            suggestions: profile.suggestions?.map(s => s.suggestion_title) || [],
            profileData: profile
          };
          
          console.log('💬 DEBUG: Adding profile message to chat');
          console.log('💬 DEBUG: Profile message content length:', profileContent.length);
          setMessages(prev => {
            console.log('💬 DEBUG: Current messages count:', prev.length);
            const newMessages = [...prev, profileMessage];
            console.log('💬 DEBUG: New messages count:', newMessages.length);
            return newMessages;
          });
        } else {
          console.log('❌ DEBUG: data.data is empty or null');
        }
      } else {
        console.error('❌ DEBUG: API returned success=false, error:', data.error);
        console.error('❌ DEBUG: Full error response:', JSON.stringify(data, null, 2));
        
        // Add error message to chat
        const errorMessage = {
          type: 'agent',
          content: `❌ **Profile Loading Failed**\n\nError: ${data.error || 'Unknown error'}\n\nPlease check:\n• Database is initialized\n• Email exists in system\n• Backend server is running\n\n🔧 Try: \`python verify_database.py\``
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('🚨 DEBUG: Network/fetch error:', error);
      console.error('🚨 DEBUG: Error stack:', error.stack);
      
      // Add network error message to chat
      const networkErrorMessage = {
        type: 'agent',
        content: `🚨 **Network Error**\n\nFailed to load customer profile.\n\nError: ${error.message}\n\nPlease check:\n• Backend server is running on port 8000\n• Network connection\n• API endpoint accessibility\n\n🔧 Test: \`curl "${CUSTOMER_API_URL}/customer/profile/${encodeURIComponent(email)}"\``
      };
      setMessages(prev => [...prev, networkErrorMessage]);
    } finally {
      console.log('🏁 DEBUG: Setting loading state to false');
      setIsLoadingProfile(false);
    }
  };

  const handleEmailChange = (event) => {
    const email = event.target.value;
    setCustomerData(prev => ({ ...prev, email_id: email }));
    
    // Reset profile state when email changes
    setCustomerProfile(null);
    setShowSuggestions(false);
  };

  const handleLoadProfile = () => {
    const email = customerData.email_id.trim();
    if (email && email.includes('@') && email.includes('.')) {
      loadCustomerProfile(email);
    } else {
      alert('Please enter a valid email address');
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo" style={{ display: 'flex', alignItems: 'center' }}>
            <img src="/hot-logo.png" alt="House of Travel Logo" style={{ width: '50px', height: '50px', marginRight: '10px' }} />
            <div>
              <h1 style={{ margin: 0, fontSize: '1.5rem' }}>House of Travel</h1>
              <span className="tagline">Intelligent Travel Solutions</span>
            </div>
          </div>
          <div className="agent-info">
            <span className="agent-badge">Travel Agent Portal</span>
          </div>
        </div>
      </header>

      <div className="main-layout">
        {/* Left Side - Chatbot */}
        <div className="left-panel">
          <div className="chat-header">
            <h2>🤖 AI Travel Assistant</h2>
            <p>Smart itinerary planning & booking support</p>
          </div>

          {/* Customer Info Panel */}
          <div className="customer-info">
            <div style={{display: 'flex', gap: '10px', marginBottom: '10px'}}>
              <input
                type="email"
                placeholder="Enter client email (e.g., henry.thomas596@yahoo.com)"
                value={customerData.email_id}
                onChange={handleEmailChange}
                className="customer-input"
                style={{flex: 1}}
              />
              <button
                onClick={handleLoadProfile}
                disabled={isLoadingProfile || !customerData.email_id}
                style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: customerData.email_id ? '#4CAF50' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: customerData.email_id ? 'pointer' : 'not-allowed',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  whiteSpace: 'nowrap'
                }}
              >
                {isLoadingProfile ? '⏳ Loading...' : '👤 Load Profile'}
              </button>
            </div>
            
            {isLoadingProfile && (
              <div className="profile-loading">🔍 Fetching customer profile, preferences, and travel history...</div>
            )}
            
            {customerProfile && (
              <div className="profile-info">
                ✅ Profile loaded: {customerProfile.customer_name} • {customerProfile.travel_history_count} trips • {customerProfile.suggestions?.length || 0} recommendations
              </div>
            )}
            
            <div style={{fontSize: '0.75em', color: '#666', marginTop: '5px'}}>
              💡 Try sample emails: henry.thomas596@yahoo.com, john.doe@example.com, jane.smith@example.com
            </div>
          </div>
          
          <div className="chat-container">
            <div className="chat-messages">
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.type}-message`}>
                  {message.type === 'loading' ? (
                    <div className="loading">{message.content}</div>
                  ) : (
                    <>
                      <div className="content" style={{whiteSpace: 'pre-wrap'}}>
                        {message.content}
                      </div>
                      {message.type === 'agent' && message.suggestions && message.suggestions.length > 0 && (
                        <div className="suggestions">
                          {message.suggestions.map((suggestion, suggIndex) => (
                            <span
                              key={suggIndex}
                              className="suggestion"
                              onClick={() => handleSuggestionClick(suggestion)}
                            >
                              {suggestion}
                            </span>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
          
          <div className="chat-input">
            <input
              type="text"
              className="input-field"
              placeholder="Describe client's travel plans... (e.g., 'Plan a 7-day trip to Japan for 2 people')"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={isLoading || !inputValue.trim()}
            >
              {isLoading ? 'Planning...' : 'Send'}
            </button>
          </div>
        </div>

        {/* Right Side - Travel Information & Agent Tools */}
        <div className="right-panel">
          {/* Hero Image Section */}
          <div className="hero-section">
            <div className="hero-image">
              <img 
                src="https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&h=400&fit=crop&crop=center&auto=format&q=80" 
                alt="Luxury tropical paradise"
                style={{width: '100%', height: '250px', objectFit: 'cover', borderRadius: '12px'}}
              />
              <div className="hero-overlay">
                <h3>Craft Unforgettable Journeys</h3>
                <p>Powered by AI, Perfected by Experience</p>
              </div>
            </div>
          </div>

          {/* Agent Capabilities */}
          <div className="agent-capabilities">
            <h3>🎯 What This AI Agent Can Do For You</h3>
            
            <div className="capability-group">
              <h4>📋 Instant Trip Planning</h4>
              <ul>
                <li>Multi-destination itinerary creation</li>
                <li>Real-time flight & hotel searches</li>
                <li>Budget optimization & cost breakdown</li>
                <li>Personalized recommendations based on client profile</li>
              </ul>
            </div>

            <div className="capability-group">
              <h4>✅ Compliance & Documentation</h4>
              <ul>
                <li>Visa requirements checking</li>
                <li>Health advisories & vaccination info</li>
                <li>Travel documentation checklists</li>
                <li>Country-specific entry requirements</li>
              </ul>
            </div>

            <div className="capability-group">
              <h4>💼 Agent Productivity Tools</h4>
              <ul>
                <li>Client profile analysis & loyalty matching</li>
                <li>Automated email proposal generation</li>
                <li>HOT-specific discounts & offers integration</li>
                <li>Session continuity for complex bookings</li>
              </ul>
            </div>

            <div className="capability-group">
              <h4>🌐 Global Intelligence</h4>
              <ul>
                <li>200+ country visa database</li>
                <li>Real-time flight pricing via Amadeus</li>
                <li>Cultural events & seasonal recommendations</li>
                <li>Multi-language support & local insights</li>
              </ul>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="quick-actions">
            <h3>⚡ Quick Actions</h3>
            <div className="action-buttons">
              <button 
                className="action-btn"
                onClick={() => sendMessage("What visa requirements for US citizens traveling to Japan?")}
              >
                Check Visa Requirements
              </button>
              <button 
                className="action-btn"
                onClick={() => sendMessage("Find flights from Tokyo to Paris for business class")}
              >
                Search Premium Flights
              </button>
              <button 
                className="action-btn"
                onClick={() => sendMessage("Plan a luxury honeymoon to Maldives")}
              >
                Luxury Package Builder
              </button>
              <button 
                className="action-btn"
                onClick={() => sendMessage("Health requirements for travel to Thailand")}
              >
                Health Advisory Check
              </button>
            </div>
          </div>

          {/* Agent Performance Stats */}
          <div className="performance-stats">
            <h3>📊 AI Performance</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-number">98.5%</span>
                <span className="stat-label">Accuracy Rate</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">&lt;3s</span>
                <span className="stat-label">Response Time</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">200+</span>
                <span className="stat-label">Countries Covered</span>
              </div>
              <div className="stat-item">
                <span className="stat-number">24/7</span>
                <span className="stat-label">Availability</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;