import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pickle
from typing import List, Optional

from pydantic import BaseModel

# Optional Gmail imports - only used if credentials are available
try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

# # ---------------------- Models ---------------------- #
class Flight(BaseModel):
    rank: int
    airline: Optional[str]
    price: Optional[str]
    route: Optional[str]
    connections: Optional[int]
    recommendation_reason: Optional[str]

class Hotel(BaseModel):
    name: Optional[str]
    price_per_night: Optional[str]
    location: Optional[str]
    room_type: Optional[str]

class TripDetails(BaseModel):
    destination: str
    departure_date: str
    return_date: Optional[str]
    duration: Optional[int]
    passengers: Optional[int]
    travel_class: Optional[str]
    budget: Optional[float]
    budget_currency: Optional[str]

class Customer(BaseModel):
    email: str
    name: str
    loyalty_tier: Optional[str]
    nationality: Optional[str]
    booking_history: Optional[int]

class SessionInfo(BaseModel):
    session_id: str
    generated_at: str
    agent_notes: Optional[str]

class EmailData(BaseModel):
    customer: Customer
    trip_details: TripDetails
    flights: List[Flight] = []
    hotels: List[Hotel] = []
    itinerary: Optional[dict] = None
    session_info: Optional[SessionInfo]

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def gmail_authenticate():
    """Authenticate with Gmail API if credentials are available"""
    if not GMAIL_AVAILABLE:
        raise Exception("Gmail API not available - missing googleapiclient dependencies")
    
    creds = None
    
    # Try to load existing token
    if os.path.exists("token.pickle"):
        print("Loading existing Gmail token...")
        try:
            with open("token.pickle", "rb") as token:
                creds = pickle.load(token)
        except Exception as e:
            print(f"Error loading token.pickle: {e}")
            creds = None

    # Check if credentials are valid or need refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired Gmail token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        # If we still don't have valid creds, try to get new ones
        if not creds:
            if not os.path.exists("credentials.json"):
                raise Exception("Gmail credentials not found - credentials.json missing. Please add Gmail API credentials for email functionality.")
            
            print("Creating new Gmail authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        try:
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)
            print("Gmail token saved successfully")
        except Exception as e:
            print(f"Warning: Could not save token.pickle: {e}")

    return build("gmail", "v1", credentials=creds)

def build_html(email_data):
    if email_data is None:
        raise Exception("email_data is None")
    
    # Safely get data with fallbacks
    customer = email_data.get("customer") or {}
    trip = email_data.get("trip_details") or {}
    flights = email_data.get("flights") or []
    hotels = email_data.get("hotels") or []
    
    # Add debug logging
    print(f"[DEBUG] Customer data: {customer}")
    print(f"[DEBUG] Trip data: {trip}")
    print(f"[DEBUG] Flights count: {len(flights)}")
    print(f"[DEBUG] Hotels count: {len(hotels)}")

    departure_date = trip.get("departure_date", "TBD")
    duration = trip.get("duration")
    return_date = trip.get("return_date") or "TBD"
    if trip.get("return_date"):
        return_date = trip.get("return_date")
    elif departure_date and duration:
        try:
            dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
            return_date = (dep_date + timedelta(days=int(duration))).strftime("%Y-%m-%d")
        except Exception:
            return_date = "TBD"
    else:
        return_date = "TBD"

    # Generate flights HTML cards with proper data handling
    flights_html = ""
    for idx, flight in enumerate(flights, 1):
        airline = flight.get('airline', 'Multiple Airlines')
        price = flight.get('price', 'Price on request')
        route = flight.get('route', 'Route details not available')
        reason = flight.get('recommendation_reason', 'Recommended option')
        
        flights_html += f"""
        <div class="card">
          <div><strong>Option {idx}: {airline}</strong></div>
          <div>Route: {route}</div>
          <div>Price: {price}</div>
          <div>Why: {reason}</div>
        </div>
        """
    
    if not flights_html:
        flights_html = "<p>No flights available. Please contact our travel experts for assistance.</p>"

    # ✅ Generate hotels HTML cards
    hotels_html = "".join([
        f"""
        <div class="card">
          <div><strong>{h.get('name','TBD')}</strong></div>
          <div>📍 {h.get('location','TBD')}</div>
          <div>💲 {h.get('price_per_night','TBD')}</div>
          <div>🛏️ Room: {h.get('room_type','TBD')}</div>
        </div>
        """ for h in hotels
    ]) or "<p>No hotels available</p>"

    # ✅ Generate day-by-day itinerary HTML
    itinerary = email_data.get("itinerary") or {}
    days = itinerary.get("days") or [] if itinerary else []
    
    if days:
        itinerary_html = ""
        for day in days:
            if day is None:
                continue
            day_data = day if isinstance(day, dict) else {}
            
            activities_list = day_data.get('activities', []) or []
            activities_text = "<br>".join([f"• {activity}" for activity in activities_list]) if activities_list else "Activities to be confirmed"
            
            meals_list = day_data.get('meals', []) or []
            meals_text = ", ".join(meals_list) if meals_list else "Meal options available"
            
            budget_text = f"${day_data.get('budget_estimate', 'TBD')}" if day_data.get('budget_estimate') else "Budget estimate pending"
            
            itinerary_html += f"""
            <div class="card">
              <div><strong>Day {day_data.get('day', '?')} - {day_data.get('date', 'TBD')}</strong></div>
              <div>📍 Location: {day_data.get('location', 'TBD')}</div>
              <div>🎯 Activities:<br>{activities_text}</div>
              <div>🍽️ Meals: {meals_text}</div>
              <div>💰 Budget: {budget_text}</div>
            </div>
            """
    else:
        # Generate sample itinerary based on destination
        destination = trip.get('destination', '').upper()
        duration = trip.get('duration', 5)
        
        # Create sample itinerary for different cities
        sample_itineraries = {
            "MYSORE": [
                {"day": 1, "date": "Day 1", "location": "Mysore City Center", "activities": ["Arrival and hotel check-in", "Visit Mysore Palace", "Explore Devaraja Market", "Evening at Brindavan Gardens"], "meals": ["Welcome dinner at hotel"], "budget_estimate": 80},
                {"day": 2, "date": "Day 2", "location": "Chamundi Hills", "activities": ["Morning visit to Chamundeshwari Temple", "Nandi Bull statue", "Panoramic city views", "Shopping for Mysore silk"], "meals": ["Traditional South Indian lunch", "Local cuisine dinner"], "budget_estimate": 70},
                {"day": 3, "date": "Day 3", "location": "Srirangapatna", "activities": ["Day trip to historical Srirangapatna", "Tipu Sultan's Summer Palace", "Ranganathaswamy Temple", "River island exploration"], "meals": ["Packed lunch", "Riverside dinner"], "budget_estimate": 90}
            ],
            "RAJASTHAN": [
                {"day": 1, "date": "Day 1", "location": "Jaipur - Pink City", "activities": ["Arrival in Jaipur", "Check-in to heritage hotel", "Visit Hawa Mahal", "Evening at local bazaars"], "meals": ["Royal Rajasthani dinner"], "budget_estimate": 120},
                {"day": 2, "date": "Day 2", "location": "Amber Fort", "activities": ["Amber Fort and Palace complex", "Elephant ride experience", "Mirror Palace (Sheesh Mahal)", "Jaigarh Fort sunset views"], "meals": ["Fort-side lunch", "Traditional dal-baati-churma dinner"], "budget_estimate": 150},
                {"day": 3, "date": "Day 3", "location": "Udaipur", "activities": ["Travel to City of Lakes", "City Palace complex", "Boat ride on Lake Pichola", "Jagdish Temple visit"], "meals": ["Lakeside lunch", "Rooftop dinner with lake views"], "budget_estimate": 180}
            ],
            "VIENNA": [
                {"day": 1, "date": "Day 1", "location": "Historic Vienna", "activities": ["Arrival and city orientation", "Schönbrunn Palace tour", "Imperial Gardens walk", "Traditional coffeehouse experience"], "meals": ["Austrian lunch", "Schnitzel dinner"], "budget_estimate": 160},
                {"day": 2, "date": "Day 2", "location": "Cultural District", "activities": ["Salzburg Cathedral and Mozart's birthplace", "Hohensalzburg Fortress", "Old Town UNESCO site", "Classical music concert"], "meals": ["Traditional Austrian breakfast", "Mozart dinner concert"], "budget_estimate": 200},
                {"day": 3, "date": "Day 3", "location": "Art & Music", "activities": ["Belvedere Palace and Klimt paintings", "Vienna State Opera house tour", "Naschmarkt food experience", "Danube River cruise"], "meals": ["Market tastings", "Fine dining Austrian cuisine"], "budget_estimate": 220}
            ],
            "MATHURA": [
                {"day": 1, "date": "Day 1", "location": "Krishna Janmabhoomi", "activities": ["Arrival and temple visits", "Krishna Janmabhoomi Temple", "Dwarkadhish Temple", "Evening aarti ceremony"], "meals": ["Prasadam lunch", "Vegetarian dinner"], "budget_estimate": 60},
                {"day": 2, "date": "Day 2", "location": "Vrindavan", "activities": ["Day trip to Vrindavan", "ISKCON Temple", "Banke Bihari Temple", "Radha Raman Temple", "Traditional folk performances"], "meals": ["Temple prasadam", "Local vegetarian cuisine"], "budget_estimate": 70},
                {"day": 3, "date": "Day 3", "location": "Govardhan Hill", "activities": ["Govardhan Hill parikrama", "Sacred ponds and temples", "Local cultural experiences", "Spiritual discourse sessions"], "meals": ["Simple vegetarian meals", "Community dinner"], "budget_estimate": 50}
            ]
        }
        
        # Get sample itinerary for destination or create generic one
        if any(city in destination for city in sample_itineraries.keys()):
            city_key = next(city for city in sample_itineraries.keys() if city in destination)
            sample_days = sample_itineraries[city_key]
        else:
            # Generic sample itinerary for other destinations
            sample_days = [
                {"day": 1, "date": "Day 1", "location": trip.get('destination', 'Destination'), "activities": ["Arrival and hotel check-in", "City orientation tour", "Local landmark visits", "Welcome dinner"], "meals": ["Local cuisine dinner"], "budget_estimate": 100},
                {"day": 2, "date": "Day 2", "location": "Cultural Sites", "activities": ["Historical site visits", "Museum tours", "Local shopping", "Cultural performances"], "meals": ["Traditional lunch", "Local specialties dinner"], "budget_estimate": 120},
                {"day": 3, "date": "Day 3", "location": "Nature & Adventure", "activities": ["Outdoor activities", "Scenic viewpoints", "Local experiences", "Departure preparations"], "meals": ["Farewell lunch", "Light dinner"], "budget_estimate": 90}
            ]
        
        # Generate HTML for sample itinerary
        itinerary_html = ""
        for day in sample_days[:min(duration, len(sample_days))]:
            activities_list = day.get('activities', [])
            activities_text = "<br>".join([f"• {activity}" for activity in activities_list])
            
            meals_list = day.get('meals', [])
            meals_text = ", ".join(meals_list)
            
            budget_text = f"${day.get('budget_estimate', 'TBD')}"
            
            itinerary_html += f"""
            <div class="card">
              <div><strong>Day {day.get('day', '?')} - {day.get('date', 'TBD')}</strong></div>
              <div>📍 Location: {day.get('location', 'TBD')}</div>
              <div>🎯 Activities:<br>{activities_text}</div>
              <div>🍽️ Meals: {meals_text}</div>
              <div>💰 Budget: {budget_text}</div>
            </div>
            """

    # ✅ Return full HTML
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Travel Proposal</title>
      <style>
        body {{
          font-family: 'Source Sans Pro', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          margin: 0;
          padding: 20px 0;
          color: #333;
          line-height: 1.6;
        }}
        .container {{
          max-width: 720px;
          margin: 0 auto;
          background: #fff;
          border-radius: 20px;
          box-shadow: 0 20px 40px rgba(0,0,0,0.15);
          overflow: hidden;
          position: relative;
        }}
        .container::before {{
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: linear-gradient(90deg, #46166B, #FFCC32, #46166B);
        }}
        .header {{
          background: linear-gradient(135deg, #46166B 0%, #5d1a78 50%, #FFCC32 100%);
          color: #fff;
          text-align: center;
          padding: 40px 30px;
          position: relative;
          overflow: hidden;
        }}
        .header h1 {{ 
          margin: 0; 
          font-size: 28px; 
          font-weight: 700;
          text-shadow: 0 2px 4px rgba(0,0,0,0.3);
          position: relative;
          z-index: 1;
        }}
        .header p {{
          margin: 15px 0 0 0;
          font-size: 16px;
          opacity: 0.9;
          position: relative;
          z-index: 1;
        }}
        .section {{ 
          padding: 30px; 
          border-bottom: 1px solid #f0f2f5; 
          position: relative;
        }}
        .section:last-child {{
          border-bottom: none;
        }}
        .section h2 {{ 
          font-size: 20px; 
          color: #46166B; 
          margin-bottom: 20px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 10px;
        }}
        .section h2::after {{
          content: '';
          flex: 1;
          height: 2px;
          background: linear-gradient(90deg, #FFCC32, transparent);
        }}
        .info {{ 
          margin: 12px 0; 
          font-size: 15px; 
          color: #555;
          display: flex;
          justify-content: space-between;
          padding: 8px 0;
        }}
        .info strong {{
          color: #46166B;
          min-width: 120px;
        }}
        .card {{
          background: linear-gradient(145deg, #ffffff, #f8f9ff);
          border: 1px solid #e8ecf4;
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 15px;
          box-shadow: 0 4px 6px rgba(0,0,0,0.05);
          position: relative;
          overflow: hidden;
        }}
        .card::before {{
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 4px;
          height: 100%;
          background: linear-gradient(180deg, #46166B, #FFCC32);
        }}
        .card strong {{ 
          color: #46166B; 
          font-size: 16px;
          display: block;
          margin-bottom: 8px;
        }}
        .card div:not(:first-child) {{
          margin: 8px 0;
          color: #666;
        }}
        .footer {{
          text-align: center;
          padding: 30px;
          font-size: 13px;
          color: #888;
          background: linear-gradient(145deg, #f8f9fa, #e9ecef);
        }}
        .btn {{
          display: inline-block;
          padding: 16px 32px;
          background: linear-gradient(135deg, #FFCC32, #ffd60a);
          color: #46166B !important;
          text-decoration: none;
          border-radius: 30px;
          margin: 20px 10px;
          font-size: 16px;
          font-weight: 600;
          box-shadow: 0 8px 20px rgba(255, 204, 50, 0.3);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }}
        .contact {{
          background: linear-gradient(145deg, #46166B, #5d1a78);
          color: white;
          border-radius: 15px;
          padding: 25px;
          margin: 20px;
          box-shadow: 0 10px 25px rgba(70, 22, 107, 0.2);
        }}
        .contact h2 {{
          margin-top: 0;
          font-size: 20px;
          color: #FFCC32;
          border-bottom: 2px solid #FFCC32;
          padding-bottom: 10px;
        }}
        .contact-item {{
          margin: 15px 0;
          font-size: 15px;
          color: rgba(255,255,255,0.9);
          display: flex;
          align-items: center;
        }}
        .contact-item .icon {{
          margin-right: 12px;
          font-size: 18px;
        }}
        .contact a {{
          color: #FFCC32;
          text-decoration: none;
          font-weight: 500;
        }}
        .contact a:hover {{
          text-decoration: underline;
        }}
        .alert-box {{
          margin: 15px 0;
          padding: 15px 20px;
          border-radius: 10px;
          font-size: 14px;
          line-height: 1.5;
        }}
        .alert-warning {{
          background-color: #fff3cd;
          border-left: 4px solid #ffc107;
          color: #856404;
        }}
        .alert-info {{
          background-color: #d1ecf1;
          border-left: 4px solid #17a2b8;
          color: #0c5460;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <!-- Header with Logo -->
        <div class="header">
          <div style="text-align: center; margin-bottom: 20px; position: relative; z-index: 2;">
            <div style="display: inline-block; padding: 15px 25px; background: rgba(255,255,255,0.1); border-radius: 50px; backdrop-filter: blur(10px);">
              <span style="font-size: 24px; font-weight: bold; color: #FFCC32; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">🏠</span>
              <span style="font-size: 18px; font-weight: bold; color: white; margin-left: 8px; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">HOUSE OF TRAVEL</span>
            </div>
            <img hidden src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMDAgNTAiPjxwYXRoIGZpbGw9IiNmZmYiIGQ9Ik0xODUuMSA0MC4xaC0xM2MtMS43IDAtMy0xLjMtMy0zVjEyLjljMC0xLjcgMS4zLTMgMy0zaDEzYzEuNyAwIDMgMS4zIDMgM3YyNC4yYzAgMS42LTEuMyAzLTMgM3ptLTMxLjYtMTUuN2MwLTUuMyA0LjMtOS42IDkuNi05LjZoMTAuOWMxLjcgMCAzLTEuMyAzLTN2LS4xYzAtMS43LTEuMy0zLTMtM2gtMTFjLTguNiAwLTE1LjYgNy0xNS42IDE1LjZ2LjFjMCA4LjYgNyAxNS42IDE1LjYgMTUuNmgxMWMxLjcgMCAzLTEuMyAzLTN2LS4xYzAtMS43LTEuMy0zLTMtM2gtMTAuOWMtNS4zIDAtOS42LTQuMy05LjYtOS42di0uMXptLTI3LjktMTIuN2MwLTEuNy0xLjMtMy0zLTNoLTEzYy0xLjcgMC0zIDEuMy0zIDN2MTIuM2MwIDEuNyAxLjMgMyAzIDNoM2MxLjcgMCAzLTEuMyAzLTN2LTkuM2g3YzEuNyAwIDMtMS4zIDMtM3YtLjF6bS0yOC4xLTIuM2MwLTguNi03LTE1LjYtMTUuNi0xNS42aC0xM2MtMS43IDAtMyAxLjMtMyAzdjI0LjJjMCAxLjcgMS4zIDMgMyAzaDEzYzguNiAwIDE1LjYtNyAxNS42LTE1LjZ2LS4xem0tMy4xIDBjMCA1LjMtNC4zIDkuNi05LjYgOS42aC0xMFYxMS44aDEwYzUuMyAwIDkuNiA0LjMgOS42IDkuNnYuMXptLTMxLjMtMTIuN2MwLTEuNy0xLjMtMy0zLTNoLTEzYy0xLjcgMC0zIDEuMy0zIDN2MTIuM2MwIDEuNyAxLjMgMyAzIDNoM2MxLjcgMCAzLTEuMyAzLTN2LTkuM2g3YzEuNyAwIDMtMS4zIDMtM3YtLjF6bS0yOC4xLTIuM2MwLTguNi03LTE1LjYtMTUuNi0xNS42aC0xM2MtMS43IDAtMyAxLjMtMyAzdjI0LjJjMCAxLjcgMS4zIDMgMyAzaDEzYzguNiAwIDE1LjYtNyAxNS42LTE1LjZ2LS4xem0tMy4xIDBjMCA1LjMtNC4zIDkuNi05LjYgOS42aC0xMFYxMS44aDEwYzUuMyAwIDkuNiA0LjMgOS42IDkuNnYuMXoiLz48L3N2Zz4=" alt="HOT Travel" style="max-width: 180px; height: auto; display: block; margin: 0 auto;">
          </div>
          <h1>✈️ Your Dream Trip Awaits!</h1>
          <p>✨ Expertly curated travel experience for {trip.get('destination','your destination')} ✨</p>
        </div>
        <!-- Customer -->
        <div class="section">
          <h2>👤 Customer Details</h2>
          <div class="info"><strong>Name:</strong> {customer.get('name', 'Valued Customer')}</div>
          <div class="info"><strong>Email:</strong> {customer.get('email','')}</div>
          <div class="info"><strong>Loyalty Tier:</strong> {customer.get('loyalty_tier','')}</div>
          <div class="info"><strong>Nationality:</strong> {customer.get('nationality','')}</div>
        </div>
        <!-- Trip -->
        <div class="section">
          <h2>🌍 Trip Details</h2>
          <div class="info"><strong>Destination:</strong> {trip.get('destination','TBD')}</div>
          <div class="info"><strong>Dates:</strong> {departure_date} → {return_date}</div>
          <div class="info"><strong>Duration:</strong> {trip.get('duration','')} nights</div>
          <div class="info"><strong>Passengers:</strong> {trip.get('passengers','')}</div>
          <div class="info"><strong>Class:</strong> {trip.get('travel_class','')}</div>
          <div class="info"><strong>Budget:</strong> {trip.get('budget_currency','')} {trip.get('budget','')}</div>
        </div>
        <!-- Flights -->
        <div class="section">
          <h2>🛫 Flight Options</h2>
          {flights_html}
        </div>
        <!-- Hotels -->
        <div class="section">
          <h2>🏨 Hotel Options</h2>
          {hotels_html}
        </div>
        
        <!-- Day-by-Day Itinerary -->
        <div class="section">
          <h2>📅 Daily Itinerary</h2>
          {itinerary_html}
        </div>
        
        <!-- Visa & Travel Documents -->
        <div class="section">
          <h2>📋 Visa & Travel Requirements</h2>
          <div class="card">
            <div><strong>Important Travel Documentation</strong></div>
            <div style="margin-top: 10px;">
              • <strong>Passport:</strong> Must be valid for at least 6 months from travel date<br>
              • <strong>Visa Requirements:</strong> Check latest requirements for {trip.get('destination', 'your destination')}<br>
              • <strong>Travel Authorization:</strong> eTA/ESTA may be required depending on destination<br>
              • <strong>Travel Insurance:</strong> Comprehensive coverage recommended<br>
              • <strong>Documentation:</strong> Print copies of all bookings and confirmations
            </div>
            <div class="alert-box alert-warning">
              <strong>⚠️ Important:</strong> Our travel experts will provide specific visa requirements and assist with applications during booking confirmation.
            </div>
          </div>
        </div>
        
        <!-- Health Advisory -->
        <div class="section">
          <h2>🏥 Health & Safety Advisory</h2>
          <div class="card">
            <div><strong>Travel Health Recommendations</strong></div>
            <div style="margin-top: 10px;">
              • <strong>Vaccinations:</strong> Routine vaccinations up to date (MMR, DPT, flu)<br>
              • <strong>Travel Insurance:</strong> Medical coverage with emergency evacuation<br>
              • <strong>Medications:</strong> Bring prescriptions in original containers<br>
              • <strong>Health Precautions:</strong> Check CDC/WHO advisories for destination<br>
              • <strong>Emergency Contacts:</strong> Local embassy and emergency services information
            </div>
            <div class="alert-box alert-info">
              <strong>💡 Note:</strong> Specific health requirements and recommendations for {trip.get('destination', 'your destination')} will be provided by our travel health specialists.
            </div>
          </div>
        </div>
        
        <!-- Proceed to Booking Button -->
        <div class="section" style="text-align: center; padding: 30px 0;">
          <a href="tel:0800355999" class="btn">
            📞 Call to Book Now
          </a>
          <p style="margin-top: 15px; color: #666; font-size: 14px;">
            Our travel experts are ready to make your dream trip a reality!
          </p>
        </div>
        <!-- Contact Info -->
        <div class="section contact">
          <h2>📞 Contact Information</h2>
          <div class="contact-item">
            <span class="icon">📧</span>
            <a href="mailto:hello@hot.co.nz">hello@hot.co.nz</a>
          </div>
          <div class="contact-item">
            <span class="icon">☎️</span>
            <span>0800 355 999</span> <br>
            <span style="margin-left: 24px;">International: +64 3 357 3023</span>
          </div>
          <div class="contact-item">
            <span class="icon">🌐</span>
            <a href="https://www.houseoftravel.co.nz/">www.houseoftravel.co.nz</a>
          </div>
        </div>
        <!-- Footer -->
        <div class="footer">
          This is an automated email. Please do not reply.<br>
          © 2025 HOT Travel Assistant
        </div>
      </div>
    </body>
    </html>
    """

def send_message(email_data):
    """Send email with travel proposal"""
    try:
        if isinstance(email_data, BaseModel):
            email_data = email_data.model_dump()
        
        # Check if Gmail is enabled via environment variable
        gmail_enabled = os.getenv("GMAIL_ENABLED", "false").lower() == "true"
        
        if not gmail_enabled:
            # Gmail disabled - simulate email for demo
            customer_email = email_data.get('customer', {}).get('email', 'unknown@example.com')
            destination = email_data.get('trip_details', {}).get('destination', 'Unknown Destination')
            # Clean up destination string by removing extra commas and spaces
            destination_clean = destination.replace(',', '').replace('  ', ' ').strip()
            
            print(f"[DEMO MODE] Gmail disabled - simulating email send:")
            print(f"[DEMO MODE] To: {customer_email}")
            print(f"[DEMO MODE] Subject: 🌆 Discover {destination_clean}: Your Tailored Travel Guide")
            print(f"[DEMO MODE] HTML content length: {len(build_html(email_data))} characters")
            print(f"[DEMO MODE] Email would be sent in production with proper Gmail setup")
            
            return True
        # Gmail enabled - attempt real email sending
        service = gmail_authenticate()
        
        # Get email recipients
        customer_email = email_data.get('customer', {}).get('email', '')
        if not customer_email:
            raise Exception("No customer email provided")
        
        # Create message
        message = MIMEMultipart("alternative")
        
        # Process each recipient
        recipients = [email.strip() for email in customer_email.split(',') if email.strip()]
        
        for recipient in recipients:
            message["to"] = recipient
            message["from"] = "no_reply@gmail.com"
            
            # Use the destination in the subject if available
            destination = email_data.get('trip_details', {}).get('destination', 'Your Destination')
            # Clean up destination string by removing extra commas and spaces
            destination_clean = destination.replace(',', '').replace('  ', ' ').strip()
            message["subject"] = f"🌆 Discover {destination_clean}: Your Tailored Travel Guide"

            # Generate and attach HTML body
            html_body = build_html(email_data)
            message.attach(MIMEText(html_body, "html"))

            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": raw_message}
            
            sent_message = service.users().messages().send(userId="me", body=create_message).execute()
            print(f"[SUCCESS] Email sent to {recipient}. Message Id: {sent_message['id']}")
        
            return True
        
        # Gmail enabled - attempt real email sending   
        service = gmail_authenticate()
        
        # Get email recipients
        customer_email = email_data.get('customer', {}).get('email', '')
        if not customer_email:
            raise Exception("No customer email provided")
        
        # Create message
        message = MIMEMultipart("alternative")
        
        # Process each recipient
        recipients = [email.strip() for email in customer_email.split(',') if email.strip()]
        
        for recipient in recipients:
            message["to"] = recipient
            message["from"] = "no_reply@gmail.com"
            
            # Use the destination in the subject if available
            destination = email_data.get('trip_details', {}).get('destination', 'Your Destination')
            # Clean up destination string by removing extra commas and spaces
            destination_clean = destination.replace(',', '').replace('  ', ' ').strip()
            message["subject"] = f"🌆 Discover {destination_clean}: Your Tailored Travel Guide"

            # Generate and attach HTML body
            html_body = build_html(email_data)
            message.attach(MIMEText(html_body, "html"))

            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": raw_message}
            
            sent_message = service.users().messages().send(userId="me", body=create_message).execute()
            print(f"[SUCCESS] Email sent to {recipient}. Message Id: {sent_message['id']}")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to send email: {error_msg}")
        
        # Provide more helpful error messages
        if "credentials.json" in error_msg:
            raise Exception("Gmail API credentials not found. Please add credentials.json file for email functionality.")
        elif "googleapiclient" in error_msg:
            raise Exception("Gmail API dependencies missing. Please install google-api-python-client.")
        elif "No customer email" in error_msg:
            raise Exception("No customer email address provided in request.")
        else:
            raise Exception(f"Email sending failed: {error_msg}")
            
        return False