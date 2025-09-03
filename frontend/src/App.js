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
    email_id: 'henry.thomas596@yahoo.com',
    nationality: '',
    passport_number: ''
  });
  
  // Conversation context to remember accumulated requirements
  const [conversationContext, setConversationContext] = useState({
    session_id: null,
    accumulated_requirements: {
      destination: null,
      departure_date: null,
      return_date: null,
      duration: null,
      budget: null,
      budget_currency: 'USD',
      passengers: 1,
      children: null,
      travel_class: null,
      accommodation_type: null,
      special_requirements: []
    }
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
      // Build request with conversation context
      const requestBody = {
        user_request: query,
        email_id: customerData.email_id || null,
        nationality: customerData.nationality || null,
        passport_number: customerData.passport_number || null,
        // Include conversation context for continuity
        session_id: conversationContext.session_id,
        conversation_context: conversationContext.accumulated_requirements
      };

      const response = await fetch('http://localhost:8000/travel/search', {
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
        if (data.data) {
          if (typeof data.data === 'string') {
            agentContent = data.data;
          } else if (data.data.response) {
            agentContent = data.data.response;
          } else {
            // Format the travel assistant response properly
            const requirementsData = data.data.requirements?.data || {};
            const newRequirements = requirementsData.requirements || {};
            const missing_fields = requirementsData.missing_fields || [];
            const itinerary = data.data.itinerary?.data?.itinerary || {};
            const profile = data.data.profile?.data || {};
            
            // Merge current extraction with conversation context for display
            const displayRequirements = {
              destination: newRequirements.destination || conversationContext.accumulated_requirements.destination,
              passengers: newRequirements.passengers || conversationContext.accumulated_requirements.passengers,
              duration: newRequirements.duration || conversationContext.accumulated_requirements.duration,
              budget: newRequirements.budget || conversationContext.accumulated_requirements.budget,
              travel_class: newRequirements.travel_class || conversationContext.accumulated_requirements.travel_class,
              departure_date: newRequirements.departure_date || conversationContext.accumulated_requirements.departure_date
            };
            
            // If no missing fields, show comprehensive travel plan
            if (missing_fields.length === 0) {
              agentContent = `🎯 **Complete Travel Plan Ready!**

✅ **Your Travel Requirements:**
• **Destination:** ${displayRequirements.destination}
• **Departure Date:** ${displayRequirements.departure_date}
• **Duration:** ${displayRequirements.duration} days
• **Passengers:** ${displayRequirements.passengers} ${displayRequirements.passengers === 1 ? 'person' : 'people'}
• **Travel Class:** ${displayRequirements.travel_class}
• **Budget:** $${displayRequirements.budget}

👤 **Customer Profile (${profile.loyalty_tier || 'STANDARD'} Member):**
• Customer ID: ${profile.customer_id}
• Nationality: ${profile.nationality || 'Not specified'}
• Previous Bookings: ${profile.total_bookings || 0}

🎁 **Enhanced Offers & Savings:**
• Total Savings Applied: $${data.data.enhanced_offers?.data?.total_savings?.toFixed(2) || '0.00'}
• ${profile.loyalty_tier || 'STANDARD'} Tier Benefits: Active
• Preferred Suppliers: Included

🗓️ **Itinerary Status:**
${itinerary.rationale || 'AI-powered itinerary generation in progress...'}

${formatFlightDetails(data)}

${formatHotelDetails(data)}

🚀 **Next Steps:**
${generateFlightCurationStatus(data)}
• Activities and dining suggestions being compiled
• Travel documents and requirements being checked

*All requirements complete! Your personalized travel plan is being finalized...*`;
            } else {
              // Standard requirements gathering display
              agentContent = `🌍 **Travel Plan Analysis**

**Accumulated Requirements:**
• Destination: ${displayRequirements.destination || 'Not specified'}
• Passengers: ${displayRequirements.passengers || 1}
• Duration: ${displayRequirements.duration ? displayRequirements.duration + ' days' : 'Not specified'}
• Budget: ${displayRequirements.budget ? '$' + displayRequirements.budget : 'Not specified'}
• Travel Class: ${displayRequirements.travel_class || 'Not specified'}
• Departure Date: ${displayRequirements.departure_date || 'Not specified'}

**Customer Profile:**
• Email: ${customerData.email_id || 'Not provided'}
• Customer ID: ${profile.customer_id || 'N/A'}
• Loyalty Tier: ${profile.loyalty_tier || 'N/A'}
• Nationality: ${profile.nationality || customerData.nationality || 'Not specified'}

**Enhanced Offers:**
• Total Savings: ${data.data.enhanced_offers?.data?.total_savings ? '$' + data.data.enhanced_offers.data.total_savings.toFixed(2) : '$0.00'}
• Customer Benefits: ${profile.loyalty_tier || 'STANDARD'} tier discounts applied

*Missing Information:* ${missing_fields.join(', ')}

💡 *Please provide the missing information to complete your travel plan.*`;
            }
          }
        } else {
          agentContent = 'Travel request processed successfully!';
        }

        // Update conversation context with new information
        const requirementsData = data.data.requirements?.data || {};
        const newRequirements = requirementsData.requirements || {};
        setConversationContext(prev => ({
          session_id: data.session_id || prev.session_id,
          accumulated_requirements: {
            ...prev.accumulated_requirements,
            // Merge new requirements, keeping existing ones if new ones are null
            destination: newRequirements.destination || prev.accumulated_requirements.destination,
            departure_date: newRequirements.departure_date || prev.accumulated_requirements.departure_date,
            return_date: newRequirements.return_date || prev.accumulated_requirements.return_date,
            duration: newRequirements.duration || prev.accumulated_requirements.duration,
            budget: newRequirements.budget || prev.accumulated_requirements.budget,
            budget_currency: newRequirements.budget_currency || prev.accumulated_requirements.budget_currency,
            passengers: newRequirements.passengers || prev.accumulated_requirements.passengers,
            children: newRequirements.children || prev.accumulated_requirements.children,
            travel_class: newRequirements.travel_class || prev.accumulated_requirements.travel_class,
            accommodation_type: newRequirements.accommodation_type || prev.accumulated_requirements.accommodation_type,
            special_requirements: newRequirements.special_requirements || prev.accumulated_requirements.special_requirements
          }
        }));

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

  const generateFlightCurationStatus = (data) => {
    const curatedFlights = data?.data?.curated_flights?.data;
    const profile = data?.data?.profile?.data || {};
    const loyaltyTier = profile.loyalty_tier || 'STANDARD';
    
    if (curatedFlights && curatedFlights.curated_flights && curatedFlights.curated_flights.length > 0) {
      const topFlight = curatedFlights.curated_flights[0];
      const confidence = (curatedFlights.curation_confidence * 100).toFixed(0);
      const totalAnalyzed = curatedFlights.total_options_analyzed;
      
      return `• ✈️ ${totalAnalyzed} flight options analyzed and curated for your ${loyaltyTier} profile
• 🎯 Top recommendation: ${topFlight.recommendation_reason || 'Best match found'}
• 📊 Curation confidence: ${confidence}% (${curatedFlights.personalization_factors?.length || 0} factors applied)`;
    } else if (curatedFlights && curatedFlights.total_options_analyzed === 0) {
      return `• ✈️ Flight curation in progress for your ${loyaltyTier} member profile
• 🔍 Analyzing available options with personalized ranking
• ⚡ Real-time preference matching active`;
    } else {
      return `• ✈️ Flight options are being curated for your ${loyaltyTier} preferences
• 🎯 Personalizing based on your travel history and loyalty benefits
• 📈 Applying intelligent ranking and value optimization`;
    }
  };

  const formatFlightDetails = (data) => {
    const curatedFlights = data?.data?.curated_flights?.data?.curated_flights || [];
    const flightOffers = data?.data?.flight_offers || [];
    const profile = data?.data?.profile?.data || {};
    const loyaltyTier = profile.loyalty_tier || 'STANDARD';
    
    if (curatedFlights.length === 0 && flightOffers.length === 0) {
      return `
✈️ **Flight Options**
🔍 Searching for the best flight options for your trip...
`;
    }
    
    let flightSection = `
✈️ **Curated Flight Options for ${loyaltyTier} Member**
`;
    
    // Show top 3 curated flights
    const displayFlights = curatedFlights.length > 0 ? curatedFlights.slice(0, 3) : flightOffers.slice(0, 3);
    
    displayFlights.forEach((flight, index) => {
      const originalOffer = flight.original_offer || flight;
      const price = originalOffer.price || {};
      const itineraries = originalOffer.itineraries || [];
      const segments = itineraries[0]?.segments || [];
      const validatingAirline = originalOffer.validatingAirlineCodes?.[0] || 'Airline';
      
      const rank = flight.rank || (index + 1);
      const highlights = flight.highlights || [];
      const recommendationReason = flight.recommendation_reason || '';
      
      flightSection += `
**Option ${rank}${recommendationReason ? ` - ${recommendationReason}` : ''}**`;
      
      if (segments.length > 0) {
        const firstSegment = segments[0];
        const lastSegment = segments[segments.length - 1];
        const departure = firstSegment.departure || {};
        const arrival = lastSegment.arrival || {};
        
        flightSection += `
• 🛫 ${departure.iataCode || 'DEP'} → ${arrival.iataCode || 'ARR'}`;
        
        if (departure.at) {
          const depTime = new Date(departure.at).toLocaleString();
          flightSection += `
• 📅 Departure: ${depTime}`;
        }
        
        if (segments.length === 1) {
          flightSection += `
• ✅ Direct flight (no connections)`;
        } else {
          flightSection += `
• 🔄 ${segments.length - 1} connection(s)`;
        }
        
        flightSection += `
• 🏢 Airline: ${validatingAirline}
• 💰 Price: ${price.currency || 'USD'} ${price.total || 'TBD'}`;
        
        if (highlights.length > 0) {
          flightSection += `
• 🌟 ${highlights.slice(0, 2).join(' • ')}`;
        }
      } else {
        flightSection += `
• 💰 Price: ${price.currency || 'USD'} ${price.total || 'TBD'}
• 🏢 Airline: ${validatingAirline}`;
        
        if (highlights.length > 0) {
          flightSection += `
• 🌟 ${highlights.slice(0, 2).join(' • ')}`;
        }
      }
      
      flightSection += `
`;
    });
    
    return flightSection;
  };

  const formatHotelDetails = (data) => {
    const hotelOffers = data?.data?.hotel_offers || [];
    const profile = data?.data?.profile?.data || {};
    const loyaltyTier = profile.loyalty_tier || 'STANDARD';
    
    if (hotelOffers.length === 0) {
      return `
🏨 **Hotel Options**
🔍 Searching for the best hotel options for your stay...
`;
    }
    
    let hotelSection = `
🏨 **Hotel Recommendations for ${loyaltyTier} Member**
`;
    
    // Show top 3 hotels
    const displayHotels = hotelOffers.slice(0, 3);
    
    displayHotels.forEach((hotel, index) => {
      const hotelName = hotel.name || `Hotel Option ${index + 1}`;
      const rating = hotel.rating ? `${hotel.rating}⭐` : '';
      const offers = hotel.offers || [];
      const firstOffer = offers[0] || {};
      const price = firstOffer.price || {};
      const room = firstOffer.room || {};
      const address = hotel.address || {};
      
      hotelSection += `
**${hotelName}** ${rating}`;
      
      if (address.lines?.[0]) {
        hotelSection += `
• 📍 ${address.lines[0]}`;
        if (address.cityName) {
          hotelSection += `, ${address.cityName}`;
        }
      }
      
      if (price.total) {
        hotelSection += `
• 💰 From ${price.currency || 'USD'} ${price.total} per night`;
      }
      
      if (room.type || room.typeEstimated?.category) {
        const roomType = room.type || room.typeEstimated?.category || 'Standard Room';
        hotelSection += `
• 🏠 Room: ${roomType.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}`;
      }
      
      if (loyaltyTier !== 'STANDARD') {
        hotelSection += `
• ⭐ ${loyaltyTier} member benefits included`;
      }
      
      const amenities = hotel.amenities || [];
      if (amenities.length > 0) {
        const amenityNames = amenities.slice(0, 3).map(a => a.description).join(', ');
        hotelSection += `
• 🎯 Amenities: ${amenityNames}`;
      }
      
      hotelSection += `
`;
    });
    
    return hotelSection;
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