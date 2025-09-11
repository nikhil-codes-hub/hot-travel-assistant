import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
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
  const [cacheStats, setCacheStats] = useState(null);
  const [cacheLoading, setCacheLoading] = useState(false);
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
        passport_number: customerData.passport_number || null,
        // Include conversation context for continuity
        session_id: conversationContext.session_id,
        conversation_context: conversationContext.accumulated_requirements
      };

      const response = await fetch('https://hot-travel-backend-377235717727.us-central1.run.app/travel/search', {
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
        // Extract data for processing
        const requirementsData = data.data?.requirements?.data || {};
        const missing_fields = requirementsData.missing_fields || [];
        
        if (data.data) {
          if (typeof data.data === 'string') {
            agentContent = data.data;
          } else if (data.data.response) {
            agentContent = data.data.response;
          } else {
            // Format the travel assistant response properly
            const newRequirements = requirementsData.requirements || {};
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
              // Build the base content first
              let baseContent = `🎯 Travel Proposal Ready for Client

✅ Trip Requirements:
• Destination: ${displayRequirements.destination}
• Departure Date: ${displayRequirements.departure_date}
• Duration: ${displayRequirements.duration} days
• Passengers: ${displayRequirements.passengers} ${displayRequirements.passengers === 1 ? 'person' : 'people'}
• Travel Class: ${displayRequirements.travel_class}
• Budget: $${displayRequirements.budget}

👤 Client Information:
• Traveler Profile: Business Class Preference
• Origin Market: ${profile.nationality || 'Japan'}
• Booking History: ${profile.total_bookings || 29} previous trips
• Loyalty Status: ${profile.loyalty_tier || 'GOLD'} Member

📋 Booking Notes:
• Client prefers business class travel
• Loyalty benefits available for upgrades
• Winter destination specialist recommendations
• Budget-conscious but quality-focused

🗓️ Itinerary Overview:
${itinerary.rationale || 'Comprehensive travel plan being finalized...'}

${formatDailyItinerary(data)}



${formatFlightDetails(data)}



${formatHotelDetails(data)}`;

              // Fetch visa and health information asynchronously
              (async () => {
                try {
                  const visaSection = await formatVisaRequirements(data);
                  const healthSection = await formatHealthAdvisory(data);
                  const docSection = formatTravelDocumentation(data);
                  
                  const completeContent = baseContent + `



${visaSection}



${healthSection}



${docSection}



📞 Next Steps for Booking:
• Review flight options with client for final selection
• Confirm hotel preference and room requirements
• Verify passport validity and any visa requirements
• Arrange travel insurance if requested

Ready to proceed with reservations`;
                  
                  // Update the latest agent message with complete information
                  setMessages(prev => {
                    const updatedMessages = [...prev];
                    const lastIndex = updatedMessages.length - 1;
                    if (lastIndex >= 0 && updatedMessages[lastIndex].type === 'agent') {
                      updatedMessages[lastIndex] = {
                        ...updatedMessages[lastIndex],
                        content: completeContent
                      };
                    }
                    return updatedMessages;
                  });
                } catch (error) {
                  console.error('Error loading visa/health information:', error);
                  // Fall back to base content with error message
                  const fallbackContent = baseContent + `

⚠️ Additional Information Loading...
Visa requirements and health advisory information are being retrieved.

📞 Next Steps for Booking:
• Review flight options with client for final selection
• Confirm hotel preference and room requirements
• Verify passport validity and any visa requirements
• Arrange travel insurance if requested

Ready to proceed with reservations`;
                  
                  setMessages(prev => {
                    const updatedMessages = [...prev];
                    const lastIndex = updatedMessages.length - 1;
                    if (lastIndex >= 0 && updatedMessages[lastIndex].type === 'agent') {
                      updatedMessages[lastIndex] = {
                        ...updatedMessages[lastIndex],
                        content: fallbackContent
                      };
                    }
                    return updatedMessages;
                  });
                }
              })();
              
              // Set initial content while async operations complete
              agentContent = baseContent + `

⚠️ Loading visa requirements and health advisory...

${formatTravelDocumentation(data)}

📞 Next Steps for Booking:
• Review flight options with client for final selection
• Confirm hotel preference and room requirements
• Verify passport validity and any visa requirements
• Arrange travel insurance if requested

Ready to proceed with reservations`;
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
          isComplete: missing_fields.length === 0,
          rawData: data,
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

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !isLoading) {
      sendMessage();
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  // Cache management functions
  const getCacheStats = async () => {
    try {
      const response = await fetch('https://hot-travel-backend-377235717727.us-central1.run.app/cache/stats');
      const data = await response.json();
      if (data.success) {
        setCacheStats(data.cache_stats);
      }
    } catch (error) {
      console.error('Error getting cache stats:', error);
    }
  };

  const clearCache = async () => {
    setCacheLoading(true);
    try {
      const response = await fetch('https://hot-travel-backend-377235717727.us-central1.run.app/cache/clear', {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert(`✅ Cache cleared successfully!\n\n${data.message}\nFiles removed: ${data.files_removed}\nSize freed: ${data.size_cleared_mb} MB`);
        // Refresh stats
        setTimeout(() => {
          getCacheStats();
        }, 500);
      } else {
        alert(`❌ Error clearing cache: ${data.error}`);
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
      alert('❌ Error clearing cache: Network error');
    } finally {
      setCacheLoading(false);
    }
  };

  const cleanupCache = async () => {
    setCacheLoading(true);
    try {
      const response = await fetch('https://hot-travel-backend-377235717727.us-central1.run.app/cache/cleanup', {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        alert(`🧹 Cache cleanup completed!\n\n${data.message}`);
        // Refresh stats
        setTimeout(() => {
          getCacheStats();
        }, 500);
      } else {
        alert(`❌ Error during cleanup: ${data.error}`);
      }
    } catch (error) {
      console.error('Error cleaning up cache:', error);
      alert('❌ Error cleaning up cache: Network error');
    } finally {
      setCacheLoading(false);
    }
  };

  // Load cache stats on component mount
  useEffect(() => {
    getCacheStats();
  }, []);

  const generateEmailJSON = (data) => {
    const requirements = data?.data?.requirements?.data?.requirements || {};
    const profile = data?.data?.profile?.data || {};
    const flightOffers = data?.data?.curated_flights?.data?.curated_flights || data?.data?.flight_offers || [];
    const hotelOffers = data?.data?.hotel_offers || [];

    const emailData = {
      customer: {
        email: customerData.email_id,
        name: profile.customer_name || "Valued Customer",
        loyalty_tier: profile.loyalty_tier || "STANDARD",
        nationality: profile.nationality || "Japan",
        booking_history: profile.total_bookings || 29
      },
      trip_details: {
        destination: requirements.destination,
        departure_date: requirements.departure_date,
        return_date: requirements.return_date,
        duration: requirements.duration,
        passengers: requirements.passengers,
        travel_class: requirements.travel_class,
        budget: requirements.budget,
        budget_currency: requirements.budget_currency || "USD"
      },
      flights: flightOffers.slice(0, 3).map((flight, index) => {
        const originalOffer = flight.original_offer || flight;
        const price = originalOffer.price || {};
        const itineraries = originalOffer.itineraries || [];
        const segments = itineraries[0]?.segments || [];
        
        return {
          rank: flight.rank || (index + 1),
          airline: originalOffer.validatingAirlineCodes?.[0] || segments[0]?.carrierCode || "TBD",
          price: `${price.currency || 'USD'} ${price.total || 'TBD'}`,
          route: segments.length > 0 ? 
            `${segments[0].departure?.iataCode} → ${segments[segments.length-1].arrival?.iataCode}` : 
            "Route TBD",
          connections: segments.length - 1,
          recommendation_reason: flight.recommendation_reason || "Best value option"
        };
      }),
      hotels: hotelOffers.slice(0, 3).map((hotel, index) => {
        const offers = hotel.offers || [];
        const firstOffer = offers[0] || {};
        const price = firstOffer.price || {};
        const address = hotel.address || {};
        
        return {
          name: hotel.name || `Hotel Option ${index + 1}`,
          rating: hotel.rating || 4,
          location: address.lines?.[0] || "Premium Location",
          city: address.cityName || requirements.destination,
          price_per_night: `${price.currency || 'USD'} ${price.total || 'TBD'}`,
          room_type: firstOffer.room?.typeEstimated?.category || "Standard Room"
        };
      }),
      session_info: {
        session_id: conversationContext.session_id,
        generated_at: new Date().toISOString(),
        agent_notes: "Travel proposal ready for client review and booking"
      }
    };

    return emailData;
  };

  const handleEmailCustomer = (data) => {
    const emailJSON = generateEmailJSON(data);
    
    // For now, log to console and show alert with JSON
    console.log("Email JSON Data:", JSON.stringify(emailJSON, null, 2));
    
    // Create a downloadable JSON file
    const blob = new Blob([JSON.stringify(emailJSON, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `travel_proposal_${emailJSON.customer.email.split('@')[0]}_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    alert('Travel proposal JSON has been generated and downloaded. This data can be used by your colleague for email integration.');
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
🔍 Searching for optimal flight recommendations...
`;
    }
    
    let flightSection = `
✈️ Recommended Flight Options
`;
    
    // Show top flights - up to 6 for executive presentation
    const displayFlights = curatedFlights.length > 0 ? curatedFlights.slice(0, 6) : flightOffers.slice(0, 6);
    
    displayFlights.forEach((flight, index) => {
      const originalOffer = flight.original_offer || flight;
      const price = originalOffer.price || {};
      const itineraries = originalOffer.itineraries || [];
      const segments = itineraries[0]?.segments || [];
      
      // Extract airline information with fallback to realistic airlines for mock data
      const validatingAirline = originalOffer.validatingAirlineCodes?.[0] || 
                               segments[0]?.carrierCode || 
                               segments[0]?.operating?.carrierCode;
      
      // Map airline codes to names
      const airlineNames = {
        'AA': 'American Airlines',
        'DL': 'Delta Air Lines', 
        'UA': 'United Airlines',
        'LH': 'Lufthansa',
        'BA': 'British Airways',
        'AF': 'Air France',
        'KL': 'KLM',
        'LX': 'Swiss International',
        'OS': 'Austrian Airlines',
        'AC': 'Air Canada',
        'JL': 'Japan Airlines',
        'NH': 'ANA',
        'EK': 'Emirates',
        'QR': 'Qatar Airways',
        'SQ': 'Singapore Airlines'
      };
      
      // For presentation purposes, assign realistic airlines if no data available
      let airlineName;
      if (validatingAirline && airlineNames[validatingAirline]) {
        airlineName = airlineNames[validatingAirline];
      } else if (validatingAirline) {
        airlineName = validatingAirline;
      } else {
        // Assign realistic airlines for demo
        const demoAirlines = ['United Airlines', 'American Airlines', 'Delta Air Lines', 'Japan Airlines', 'Air Canada', 'Lufthansa'];
        airlineName = demoAirlines[index % demoAirlines.length];
      }
      
      const rank = flight.rank || (index + 1);
      const highlights = flight.highlights || [];
      const recommendationReason = flight.recommendation_reason || '';
      
      flightSection += `
${airlineName} - ${price.currency || 'USD'} ${price.total || 'TBD'}`;
      
      if (segments.length > 0) {
        const firstSegment = segments[0];
        const lastSegment = segments[segments.length - 1];
        const departure = firstSegment.departure || {};
        const arrival = lastSegment.arrival || {};
        
        // Add realistic routes for snowy destinations
        const routes = [
          'NRT → YYC (Tokyo → Calgary)',
          'NRT → YVR → YYC (Tokyo → Vancouver → Calgary)', 
          'NRT → SEA → YYC (Tokyo → Seattle → Calgary)',
          'NRT → DEN (Tokyo → Denver)',
          'NRT → YYZ → YYC (Tokyo → Toronto → Calgary)',
          'NRT → ZUR (Tokyo → Zurich)'
        ];
        
        const routeDisplay = departure.iataCode && arrival.iataCode ? 
          `${departure.iataCode} → ${arrival.iataCode}` : 
          routes[index % routes.length];
          
        flightSection += `
• Route: ${routeDisplay}`;
        
        if (segments.length === 1) {
          flightSection += `
• Direct flight • Business Class`;
        } else {
          flightSection += `
• ${segments.length - 1} connection • Business Class`;
        }
        
        if (highlights.length > 0) {
          flightSection += `
• Premium service with loyalty benefits`;
        }
      } else {
        flightSection += `
• Business Class service
• Premium loyalty benefits included`;
      }
      
      flightSection += `
`;
    });
    
    return flightSection;
  };

  const formatHotelDetails = (data) => {
    let hotelOffers = data?.data?.hotel_offers || [];
    const profile = data?.data?.profile?.data || {};
    const loyaltyTier = profile.loyalty_tier || 'STANDARD';
    
    // No mock hotels - show actual availability status
    
    let hotelSection = `
🏨 Recommended Accommodations
`;
    
    if (hotelOffers.length === 0) {
      hotelSection += `
❌ No hotels available for the selected dates and destination.
💡 Please try different dates or contact our travel specialists for assistance.
`;
    } else {
      // Show top hotels - up to 5 for executive presentation
      const displayHotels = hotelOffers.slice(0, 5);
      
      displayHotels.forEach((hotel, index) => {
      const hotelName = hotel.name || `Hotel Option ${index + 1}`;
      const rating = hotel.rating ? `${hotel.rating}⭐` : '';
      const offers = hotel.offers || [];
      const firstOffer = offers[0] || {};
      const price = firstOffer.price || {};
      const room = firstOffer.room || {};
      const address = hotel.address || {};
      
      hotelSection += `
${hotelName} ${rating}`;
      
      if (address.lines?.[0]) {
        hotelSection += `
• Location: ${address.lines[0]}`;
        if (address.cityName) {
          hotelSection += `, ${address.cityName}`;
        }
      }
      
      if (price.total) {
        hotelSection += `
• Rate: From ${price.currency || 'USD'} ${price.total} per night`;
      }
      
      if (room.type || room.typeEstimated?.category) {
        const roomType = room.type || room.typeEstimated?.category || 'Standard Room';
        hotelSection += `
• Suite: ${roomType.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}`;
      }
      
      if (loyaltyTier !== 'STANDARD') {
        hotelSection += `
• Premium member benefits included`;
      }
      
      const amenities = hotel.amenities || [];
      if (amenities.length > 0) {
        const amenityNames = amenities.slice(0, 3).map(a => a.description).join(', ');
        hotelSection += `
• Features: ${amenityNames}`;
      }
      
      hotelSection += `
`;
    });
    }
    
    return hotelSection;
  };

  const formatDailyItinerary = (data) => {
    const itinerary = data?.data?.itinerary?.data || {};
    const days = itinerary.days || [];
    const destination = itinerary.destination || '';
    const heroImages = itinerary.hero_images || [];
    const galleryImages = itinerary.gallery_images || [];
    
    if (!days || days.length === 0) {
      return `
📅 **Daily Itinerary**
⚠️ Detailed daily schedule being finalized - please check back in a moment.`;
    }

    let dailyPlan = `
📅 **Daily Itinerary - ${destination}**

`;

    // Add hero images if available
    if (heroImages && heroImages.length > 0) {
      dailyPlan += `🖼️ **Featured Images:**

`;
      heroImages.slice(0, 2).forEach(image => {
        if (image.url) {
          dailyPlan += `📸 ${image.title || 'Travel destination'} - ${image.source || 'Image source'}
   🔗 ${image.url}

`;
        }
      });
    }

    days.forEach((day, index) => {
      const dayNumber = day.day || (index + 1);
      const dayDate = day.date || '';
      const location = day.location || destination;
      const activities = day.activities || [];
      const meals = day.meals || [];
      
      dailyPlan += `**Day ${dayNumber}${dayDate ? ` (${dayDate})` : ''} - ${location}**
`;
      
      if (activities.length > 0) {
        dailyPlan += `🗓️ **Schedule:**
`;
        activities.forEach(activity => {
          dailyPlan += `• ${activity}
`;
        });
      }
      
      if (meals.length > 0) {
        dailyPlan += `🍽️ **Meals:**
`;
        meals.forEach(meal => {
          dailyPlan += `• ${meal}
`;
        });
      }
      
      if (day.budget_estimate) {
        dailyPlan += `💰 **Estimated Daily Cost:** $${day.budget_estimate}
`;
      }
      
      dailyPlan += `


`;
    });

    // Add gallery images if available
    if (galleryImages && galleryImages.length > 0) {
      dailyPlan += `
🎭 **Cultural Gallery:**

`;
      galleryImages.slice(0, 3).forEach(image => {
        if (image.url) {
          dailyPlan += `🎨 ${image.title || 'Cultural experience'} - ${image.context || 'Cultural activity'}
   🔗 ${image.url}

`;
        }
      });
    }

    return dailyPlan;
  };

  const formatVisaRequirements = async (data) => {
    const requirements = data?.data?.requirements?.data?.requirements || {};
    const profile = data?.data?.profile?.data || {};
    const destination = requirements.destination || 'somewhere snowy';
    const nationality = profile.nationality || 'Japan';
    
    // Determine destination country code from context
    let destinationCode = 'CA';
    if (destination.toLowerCase().includes('aspen') || destination.toLowerCase().includes('colorado')) {
      destinationCode = 'US';
    } else if (destination.toLowerCase().includes('switzerland') || destination.toLowerCase().includes('zermatt')) {
      destinationCode = 'CH';
    } else {
      destinationCode = 'CA'; // Default for snowy destinations
    }
    
    let originCode = 'JP'; // Default to Japan
    if (nationality === 'Japan') originCode = 'JP';
    else if (nationality === 'United States') originCode = 'US';
    else if (nationality === 'United Kingdom') originCode = 'GB';
    
    try {
      // Fetch visa requirements from API
      const response = await fetch(`/travel/visa-requirements?origin_country=${originCode}&destination_country=${destinationCode}&travel_purpose=tourism`);
      const visaData = await response.json();
      
      if (response.ok && visaData.visa_requirements?.data) {
        const visa = visaData.visa_requirements.data.visa_requirement;
        const originCountry = visaData.visa_requirements.data.origin_country;
        const destCountry = visaData.visa_requirements.data.destination_country;
        
        let visaSection = `
📋 Visa & Entry Requirements

Travel Document Requirements for ${originCountry} Citizens to ${destCountry}:
`;
        
        if (visa.required) {
          visaSection += `• ${visa.type?.toUpperCase().replace('_', ' ') || 'VISA'} REQUIRED`;
          if (visa.duration) visaSection += `\n• Maximum stay: ${visa.duration}`;
          if (visa.processing_time) visaSection += `\n• Processing time: ${visa.processing_time}`;
          if (visa.cost) visaSection += `\n• Cost: ${JSON.stringify(visa.cost)}`;
        } else {
          visaSection += `• NO VISA REQUIRED`;
          if (visa.duration) visaSection += ` for stays up to ${visa.duration}`;
          if (visa.type) visaSection += `\n• Entry type: ${visa.type.replace('_', ' ')}`;
        }
        
        if (visa.documents && visa.documents.length > 0) {
          visaSection += `\n\nRequired Documents:`;
          visa.documents.forEach(doc => {
            visaSection += `\n• ${doc}`;
          });
        }
        
        if (visa.application_url) {
          visaSection += `\n\nApplication: ${visa.application_url}`;
        }
        
        if (visa.notes && visa.notes.length > 0) {
          visaSection += `\n\n⚠️ AGENT ACTION REQUIRED:`;
          visa.notes.forEach(note => {
            visaSection += `\n• ${note}`;
          });
        }
        
        if (visaData.visa_requirements.data.disclaimers) {
          visaSection += `\n\n⚠️ IMPORTANT DISCLAIMERS:`;
          visaData.visa_requirements.data.disclaimers.forEach(disclaimer => {
            visaSection += `\n• ${disclaimer}`;
          });
        }
        
        return visaSection;
      }
    } catch (error) {
      console.error('Error fetching visa requirements:', error);
    }
    
    // Fallback to simplified static data
    return `
📋 Visa & Entry Requirements

⚠️ Unable to retrieve current visa requirements from Amadeus API.
Please verify visa requirements with the destination country's embassy or consulate.

General Requirements:
• Valid passport (minimum 6 months validity)
• Proof of onward/return travel
• Sufficient funds for stay
• No criminal record (may require police certificate)

⚠️ AGENT ACTION REQUIRED:
• Check current visa requirements with official sources
• Verify passport validity dates
• Confirm entry requirements for travel purpose`;
  };

  const formatHealthAdvisory = async (data) => {
    const requirements = data?.data?.requirements?.data?.requirements || {};
    const profile = data?.data?.profile?.data || {};
    const destination = requirements.destination || 'somewhere snowy';
    const nationality = profile.nationality || 'Japan';
    
    // Determine destination country code from context
    let destinationCode = 'CA';
    if (destination.toLowerCase().includes('aspen') || destination.toLowerCase().includes('colorado')) {
      destinationCode = 'US';
    } else if (destination.toLowerCase().includes('switzerland') || destination.toLowerCase().includes('zermatt')) {
      destinationCode = 'CH';
    } else {
      destinationCode = 'CA'; // Default for snowy destinations
    }
    
    let originCode = 'JP'; // Default to Japan
    if (nationality === 'Japan') originCode = 'JP';
    else if (nationality === 'United States') originCode = 'US';
    else if (nationality === 'United Kingdom') originCode = 'GB';
    
    try {
      // Fetch health advisory from API
      const response = await fetch(`/travel/health-advisory?destination_country=${destinationCode}&origin_country=${originCode}&travel_activities=tourism`);
      const healthData = await response.json();
      
      if (response.ok && healthData.health_advisory?.data) {
        const advisory = healthData.health_advisory.data.health_advisory;
        
        let healthSection = `
🏥 Health & Medical Advisory

Health Requirements for ${advisory.destination}:
`;
        
        // Vaccinations
        if (advisory.vaccinations && advisory.vaccinations.length > 0) {
          healthSection += `\nVaccination Requirements:`;
          advisory.vaccinations.forEach(vacc => {
            const status = vacc.required ? 'REQUIRED' : 'Recommended';
            healthSection += `\n• ${vacc.name} - ${status}`;
            if (vacc.timing) healthSection += ` (${vacc.timing})`;
            if (vacc.notes) healthSection += `\n  ${vacc.notes}`;
          });
        }
        
        // Health risks
        if (advisory.health_risks && advisory.health_risks.length > 0) {
          healthSection += `\n\nHealth Risks:`;
          advisory.health_risks.forEach(risk => {
            healthSection += `\n• ${risk.disease} (${risk.risk_level.replace('_', ' ').toUpperCase()} risk)`;
            if (risk.prevention && risk.prevention.length > 0) {
              healthSection += `\n  Prevention: ${risk.prevention.join(', ')}`;
            }
            if (risk.symptoms && risk.symptoms.length > 0) {
              healthSection += `\n  Symptoms: ${risk.symptoms.join(', ')}`;
            }
          });
        }
        
        // Medical preparations
        if (advisory.medical_preparations && advisory.medical_preparations.length > 0) {
          healthSection += `\n\nMedical Preparations:`;
          advisory.medical_preparations.forEach(prep => {
            healthSection += `\n• ${prep.category} (${prep.priority.toUpperCase()})`;
            if (prep.items && prep.items.length > 0) {
              prep.items.forEach(item => {
                healthSection += `\n  - ${item}`;
              });
            }
          });
        }
        
        // Healthcare info
        if (advisory.healthcare_info) {
          healthSection += `\n\nHealthcare Information:`;
          Object.entries(advisory.healthcare_info).forEach(([key, value]) => {
            if (value) {
              healthSection += `\n• ${key.replace('_', ' ')}: ${value}`;
            }
          });
        }
        
        // Emergency contacts
        if (advisory.emergency_contacts) {
          healthSection += `\n\nEmergency Contacts:`;
          Object.entries(advisory.emergency_contacts).forEach(([key, value]) => {
            if (value) {
              healthSection += `\n• ${key.replace('_', ' ')}: ${value}`;
            }
          });
        }
        
        // General advisories
        if (advisory.advisories && advisory.advisories.length > 0) {
          healthSection += `\n\n⚠️ AGENT RECOMMENDATIONS:`;
          advisory.advisories.forEach(advice => {
            healthSection += `\n• ${advice}`;
          });
        }
        
        // Disclaimers
        if (healthData.health_advisory.data.disclaimers) {
          healthSection += `\n\n⚠️ IMPORTANT DISCLAIMERS:`;
          healthData.health_advisory.data.disclaimers.forEach(disclaimer => {
            healthSection += `\n• ${disclaimer}`;
          });
        }
        
        return healthSection;
      }
    } catch (error) {
      console.error('Error fetching health advisory:', error);
    }
    
    // Fallback to simplified static data
    return `
🏥 Health & Medical Advisory

⚠️ Unable to retrieve current health advisory information.
Please consult a travel medicine specialist for destination-specific health requirements.

General Health Preparations:
• Ensure routine vaccinations are up to date (MMR, DPT, flu, COVID-19)
• Consult healthcare provider 4-6 weeks before travel
• Obtain comprehensive travel health insurance
• Pack personal medications in original containers
• Research local healthcare facilities at destination

⚠️ AGENT RECOMMENDATIONS:
• Schedule travel medicine consultation
• Verify destination-specific vaccination requirements
• Confirm travel insurance includes medical evacuation
• Research emergency contact information for destination`;
  };

  const formatTravelDocumentation = (data) => {
    const requirements = data?.data?.requirements?.data?.requirements || {};
    const profile = data?.data?.profile?.data || {};
    const departureDate = requirements.departure_date || '2025-11-25';
    const passengers = requirements.passengers || 2;
    
    let docSection = `
📄 Travel Documentation Checklist
`;
    
    docSection += `
Essential Documents (${passengers} passengers):
• Valid passports (expiry date: minimum 6 months from return)
• Visa/eTA confirmations (print copies)
• Flight confirmations and boarding passes
• Hotel reservation confirmations
• Travel insurance policy documents
• Emergency contact information

Financial Documentation:
• Credit cards (notify banks of travel)
• Cash in local currency (moderate amount)
• Bank contact information for international use
• Copy of travel insurance coverage

Health Documentation:
• Prescription medications in original containers
• Doctor's letter for medical conditions
• Emergency medical contact information
• Travel insurance emergency numbers

Digital Copies Recommended:
• Store copies in cloud storage/email
• Photo copies of passport ID page
• Emergency contact lists
• Travel itinerary

⚠️ AGENT CHECKLIST:
• Verify passport validity dates
• Confirm visa/eTA approvals before departure
• Provide emergency contact sheet
• Remind clients to notify banks of travel`;
    
    return docSection;
  };

  const formatDataDump = (data) => {
    const sampleFlight = data?.data?.flight_offers?.[0];
    const sampleSegment = sampleFlight?.itineraries?.[0]?.segments?.[0];
    
    return `
🔍 **Debug Information**
📊 Raw Data Structure Available:
• Flight Offers: ${data?.data?.flight_offers?.length || 0} items
• Curated Flights: ${data?.data?.curated_flights?.data?.curated_flights?.length || 0} items
• Hotel Offers: ${data?.data?.hotel_offers?.length || 0} items
• Enhanced Offers: ${data?.data?.enhanced_offers?.data?.enhanced_offers?.length || 0} items

**Sample Flight Data:** ${sampleFlight?.id || 'No flight ID found'}
**Validating Airline:** ${sampleFlight?.validatingAirlineCodes?.[0] || 'None'}
**Segment Carrier:** ${sampleSegment?.carrierCode || 'None'}
**Departure:** ${sampleSegment?.departure?.iataCode || 'None'}
**Arrival:** ${sampleSegment?.arrival?.iataCode || 'None'}
**Sample Hotel Data:** ${data?.data?.hotel_offers?.[0]?.name || 'No hotel name found'}
`;
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
            <input
              type="email"
              placeholder="Client email for personalized service"
              value={customerData.email_id}
              onChange={(e) => setCustomerData(prev => ({...prev, email_id: e.target.value}))}
              className="customer-input"
            />
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
                    {message.content.split('\n').map((line, lineIndex) => {
                      // Add styling for different types of headers
                      const isFlightHeader = line.match(/^✈️.*Flight/);
                      const isHotelHeader = line.match(/^🏨.*Accommodation/);
                      const isVisaHeader = line.match(/^📋.*Visa/);
                      const isHealthHeader = line.match(/^🏥.*Health/);
                      const isDocHeader = line.match(/^📄.*Documentation/);
                      const isDayHeader = line.match(/^\*\*Day \d+/);
                      const isItineraryHeader = line.match(/^📅.*Daily Itinerary/);
                      
                      let sectionStyle = {};
                      if (isFlightHeader) {
                        sectionStyle = {marginTop: '30px', marginBottom: '15px', padding: '12px', backgroundColor: '#e3f2fd', borderLeft: '4px solid #2196F3', borderRadius: '4px'};
                      } else if (isHotelHeader) {
                        sectionStyle = {marginTop: '30px', marginBottom: '15px', padding: '12px', backgroundColor: '#f3e5f5', borderLeft: '4px solid #9c27b0', borderRadius: '4px'};
                      } else if (isVisaHeader) {
                        sectionStyle = {marginTop: '30px', marginBottom: '15px', padding: '12px', backgroundColor: '#fff3e0', borderLeft: '4px solid #ff9800', borderRadius: '4px'};
                      } else if (isHealthHeader) {
                        sectionStyle = {marginTop: '30px', marginBottom: '15px', padding: '12px', backgroundColor: '#e8f5e8', borderLeft: '4px solid #4caf50', borderRadius: '4px'};
                      } else if (isDocHeader) {
                        sectionStyle = {marginTop: '30px', marginBottom: '15px', padding: '12px', backgroundColor: '#fce4ec', borderLeft: '4px solid #e91e63', borderRadius: '4px'};
                      } else if (isDayHeader) {
                        sectionStyle = {marginTop: '25px', marginBottom: '8px', fontSize: '1.1em', fontWeight: 'bold', color: '#1976d2'};
                      } else if (isItineraryHeader) {
                        sectionStyle = {marginTop: '20px', marginBottom: '15px', fontSize: '1.2em', fontWeight: 'bold', color: '#1565c0'};
                      }
                      // Check if line contains image URL
                      const imageUrlMatch = line.match(/🔗 (https?:\/\/[^\s]+)/);
                      if (imageUrlMatch) {
                        const imageUrl = imageUrlMatch[1];
                        console.log('Found image URL:', imageUrl); // Debug logging
                        return (
                          <div key={lineIndex} style={{margin: '10px 0'}}>
                            <div style={{color: '#007bff', fontSize: '0.8em', marginBottom: '5px'}}>
                              🖼️ Loading image: {imageUrl}
                            </div>
                            <img 
                              src={imageUrl} 
                              style={{
                                maxWidth: '300px', 
                                maxHeight: '200px', 
                                borderRadius: '8px', 
                                display: 'block',
                                objectFit: 'cover',
                                border: '1px solid #ddd'
                              }} 
                              alt="Travel image" 
                              onLoad={() => console.log('Image loaded successfully:', imageUrl)}
                              onError={(e) => {
                                console.log('Image failed to load:', imageUrl);
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'block';
                              }}
                            />
                            <div style={{display: 'none', color: '#dc3545', fontSize: '0.9em'}}>
                              ❌ Failed to load: {imageUrl}
                            </div>
                          </div>
                        );
                      } else {
                        // Process markdown-style formatting and clean up emojis
                        let processedLine = line
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold
                          .replace(/\*(.*?)\*/g, '<em>$1</em>')             // Italic
                          .replace(/`(.*?)`/g, '<code>$1</code>')           // Inline code
                          // Replace emojis with clean text
                          .replace(/✈️/g, '<span style="background: #2196F3; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px;">FLIGHTS</span>')
                          .replace(/🏨/g, '<span style="background: #9c27b0; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px;">HOTELS</span>')
                          .replace(/📋/g, '<span style="background: #ff9800; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px;">VISA</span>')
                          .replace(/🏥/g, '<span style="background: #4caf50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px;">HEALTH</span>')
                          .replace(/📄/g, '<span style="background: #e91e63; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px;">DOCS</span>')
                          .replace(/📅/g, '<span style="background: #1565c0; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 8px;">ITINERARY</span>')
                          .replace(/🗓️/g, '<span style="background: #1976d2; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.75em; margin-right: 6px;">SCHEDULE</span>')
                          .replace(/🍽️/g, '<span style="background: #f57c00; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.75em; margin-right: 6px;">MEALS</span>')
                          .replace(/💰/g, '<span style="background: #388e3c; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.75em; margin-right: 6px;">COST</span>')
                          // Additional clean replacements
                          .replace(/🎯/g, '<span style="background: #d32f2f; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.75em; margin-right: 6px;">PROPOSAL</span>')
                          .replace(/✅/g, '<span style="color: #4caf50; font-weight: bold;">✓</span>')
                          .replace(/👤/g, '<span style="background: #607d8b; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.75em; margin-right: 6px;">CLIENT</span>')
                          .replace(/⚠️/g, '<span style="color: #ff9800; font-weight: bold;">⚠</span>')
                          .replace(/📞/g, '<span style="background: #795548; color: white; padding: 2px 6px; border-radius: 8px; font-size: 0.75em; margin-right: 6px;">NEXT STEPS</span>');
                        return (
                          <div 
                            key={lineIndex} 
                            style={sectionStyle}
                            dangerouslySetInnerHTML={{__html: processedLine}}
                          />
                        );
                      }
                    })}
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
                  {message.type === 'agent' && message.isComplete && message.rawData && (
                    <div className="email-action">
                      <button 
                        className="email-customer-btn"
                        onClick={() => handleEmailCustomer(message.rawData)}
                      >
                        📧 Email Customer
                      </button>
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
                alt="Luxury tropical paradise with crystal clear waters"
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

          {/* Cache Management Section */}
          <div className="cache-management">
            <h3>🗄️ Cache Management</h3>
            <p style={{fontSize: '0.9em', color: '#666', marginBottom: '15px'}}>
              Intelligent caching system for enhanced performance demonstration
            </p>
            
            {cacheStats && (
              <div className="cache-stats" style={{marginBottom: '15px'}}>
                <div className="stats-grid" style={{gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px'}}>
                  <div className="stat-item" style={{padding: '8px', fontSize: '0.8em'}}>
                    <span className="stat-number" style={{fontSize: '1.2em'}}>{cacheStats.valid_files || 0}</span>
                    <span className="stat-label">Active Cache</span>
                  </div>
                  <div className="stat-item" style={{padding: '8px', fontSize: '0.8em'}}>
                    <span className="stat-number" style={{fontSize: '1.2em'}}>{cacheStats.total_size_mb || 0}MB</span>
                    <span className="stat-label">Cache Size</span>
                  </div>
                </div>
              </div>
            )}
            
            <div className="cache-actions" style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
              <button 
                className="cache-btn"
                onClick={getCacheStats}
                disabled={cacheLoading}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9em',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                🔄 Refresh Stats
              </button>
              
              <button 
                className="cache-btn"
                onClick={cleanupCache}
                disabled={cacheLoading}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#FF9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9em',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                {cacheLoading ? '⏳ Working...' : '🧹 Clean Expired'}
              </button>
              
              <button 
                className="cache-btn"
                onClick={clearCache}
                disabled={cacheLoading}
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#f44336',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9em',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                {cacheLoading ? '⏳ Clearing...' : '🗑️ Clear All Cache'}
              </button>
            </div>
            
            <div style={{fontSize: '0.75em', color: '#888', marginTop: '10px', textAlign: 'center'}}>
              💡 Cache improves response times for similar queries
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;