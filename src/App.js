import React, { useState, useRef, useEffect } from 'react';

function App() {
  const [messages, setMessages] = useState([
    {
      type: 'agent',
      content: `Welcome to HOT Travel Assistant! I specialize in visa requirements for international travel.

I can help you with:
• Visa requirements for specific countries
• Required documents and procedures  
• Processing times and costs
• Application guidance

Try asking: "Do I need a visa for Japan?" or "What are China visa requirements?"`,
      suggestions: [
        'Do I need a visa for Japan?',
        'What are China visa requirements?',
        'How to get India visa?',
        'Do I need Schengen visa?'
      ]
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
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
    const loadingMessage = { type: 'loading', content: '🤔 Analyzing visa requirements...' };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query })
      });

      const data = await response.json();

      // Remove loading message and add agent response
      setMessages(prev => {
        const filtered = prev.filter(msg => msg.type !== 'loading');
        return [...filtered, {
          type: 'agent',
          content: data.response,
          suggestions: data.suggestions || []
        }];
      });

    } catch (error) {
      // Remove loading message and add error
      setMessages(prev => {
        const filtered = prev.filter(msg => msg.type !== 'loading');
        return [...filtered, {
          type: 'agent',
          content: 'Sorry, I encountered an error. Please try again.'
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
        <h1>🌍 HOT Travel Assistant</h1>
        <p>Your intelligent visa requirements advisor</p>
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
            placeholder="Type your visa question here... (e.g., 'Do I need a visa for Japan?')"
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
            {isLoading ? 'Processing...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;