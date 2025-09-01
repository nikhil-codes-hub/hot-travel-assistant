import React, { useState, useRef, useEffect } from 'react';

function App() {
  const [messages, setMessages] = useState([
    {
      type: 'agent',
      content: `Welcome to HOT Intelligent Travel Assistant! 🌍

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
    const loadingMessage = { type: 'loading', content: '🤔 Processing your travel request...' };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      const response = await fetch('http://localhost:8000/travel/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_request: query,
          email_id: customerData.email_id || null,
          nationality: customerData.nationality || null,
          passport_number: customerData.passport_number || null
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Remove loading message and add agent response
      setMessages(prev => {
        const filtered = prev.filter(msg => msg.type !== 'loading');
        
        let agentContent = '';
        if (data.data) {
          if (typeof data.data === 'string') {
            agentContent = data.data;
          } else if (data.data.response) {
            agentContent = data.data.response;
          } else {
            // Format the travel assistant response properly
            const requirements = data.data.requirements?.requirements || {};
            const itinerary = data.data.itinerary || {};
            const profile = data.data.profile || {};
            
            agentContent = `🌍 **Travel Plan Analysis**

**Extracted Requirements:**
• Destination: ${requirements.destination || 'Not specified'}
• Passengers: ${requirements.passengers || 1}
• Duration: ${requirements.duration ? requirements.duration + ' days' : 'Not specified'}
• Budget: ${requirements.budget ? '$' + requirements.budget : 'Not specified'}
• Travel Class: ${requirements.travel_class || 'Not specified'}

**Customer Profile:**
• Email: ${customerData.email_id || 'Not provided'}
• Customer ID: ${profile.customer_id || 'N/A'}
• Loyalty Tier: ${profile.loyalty_tier || 'N/A'}
• Nationality: ${profile.nationality || customerData.nationality || 'Not specified'}

**Next Steps:**
${itinerary.message || 'Your travel request has been processed successfully!'}

*Missing Information:* ${data.data.requirements?.missing_fields?.join(', ') || 'None'}

💡 *This is an MVP demonstration. Full flight/hotel search and itinerary generation will be implemented in the next phase.*`;
          }
        } else {
          agentContent = 'Travel request processed successfully!';
        }

        return [...filtered, {
          type: 'agent',
          content: agentContent,
          sessionId: data.session_id,
          suggestions: [
            'Get more details about this trip',
            'Check travel requirements',
            'Find the best deals',
            'Modify this itinerary'
          ]
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

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      sendMessage();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🌍 HOT Intelligent Travel Assistant</h1>
        <p>Your AI-powered travel planning companion</p>
      </div>

      {/* Customer Info Panel */}
      <div className="customer-info">
        <div className="customer-fields">
          <input
            type="email"
            placeholder="Your email address (for personalized service)"
            value={customerData.email_id}
            onChange={(e) => setCustomerData(prev => ({...prev, email_id: e.target.value}))}
            className="customer-input email-input"
          />
          <input
            type="text"
            placeholder="Your nationality (optional)"
            value={customerData.nationality}
            onChange={(e) => setCustomerData(prev => ({...prev, nationality: e.target.value}))}
            className="customer-input nationality-input"
          />
        </div>
        <div className="customer-help">
          💡 Try existing emails: henry.thomas596@yahoo.com, amelia.martinez810@gmail.com, noah.smith754@icloud.com
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
                  <div className="content">{message.content}</div>
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
                  {message.sessionId && (
                    <div className="session-info">
                      Session ID: {message.sessionId}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="chat-input">
          <input
            type="text"
            className="input-field"
            placeholder="Describe your travel plans... (e.g., 'Plan a 7-day trip to Japan for 2 people')"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
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
    </div>
  );
}

export default App;