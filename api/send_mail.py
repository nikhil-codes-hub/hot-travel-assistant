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
    customer = email_data.get("customer", {})
    trip = email_data.get("trip_details", {})
    flights = email_data.get("flights", [])
    hotels = email_data.get("hotels", [])

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

    # ✅ Return full HTML
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Travel Proposal</title>
      <style>
        body {{
          font-family: 'Segoe UI', Arial, sans-serif;
          background-color: #f4f7fb;
          margin: 0;
          padding: 0;
        }}
        .container {{
          max-width: 700px;
          margin: 20px auto;
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
          overflow: hidden;
        }}
        .header {{
          background: linear-gradient(135deg, #46166B, #FFCC32);
          color: #fff;
          text-align: center;
          padding: 20px;
        }}
        .header h1 {{ margin: 0; font-size: 22px; }}
        .section {{ padding: 20px; border-bottom: 1px solid #eee; }}
        .section h2 {{ font-size: 18px; color: #333; margin-bottom: 10px; }}
        .info {{ margin: 5px 0; font-size: 14px; color: #555; }}
        .card {{
          background: #f9fafc;
          border: 1px solid #e0e6ed;
          border-radius: 8px;
          padding: 12px 15px;
          margin-bottom: 10px;
        }}
        .card strong {{ color: #222; }}
        .footer {{
          text-align: center;
          padding: 15px;
          font-size: 12px;
          color: #888;
          background: #fafafa;
        }}
        .btn {{
          display: inline-block;
          padding: 10px 18px;
          background: #0061f2;
          color: #fff !important;
          text-decoration: none;
          border-radius: 6px;
          margin-top: 15px;
          font-size: 14px;
        }}
        .contact {{
          background: #f9fafc;
          border: 1px solid #e0e6ed;
          border-radius: 8px;
          padding: 15px 20px;
          margin: 20px;
        }}
        .contact h2 {{
          margin-top: 0;
          font-size: 18px;
          color: #0061f2;
        }}
        .contact-item {{
          margin: 8px 0;
          font-size: 14px;
          color: #444;
        }}
        .contact-item .icon {{
          margin-right: 8px;
        }}
        .contact a {{
          color: #0061f2;
          text-decoration: none;
        }}
        .contact a:hover {{
          text-decoration: underline;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <!-- Header with Logo -->
        <div class="header">
          <div style="text-align: center; margin-bottom: 15px; padding: 10px 0; background-color: #003366;">
            <img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyMDAgNTAiPjxwYXRoIGZpbGw9IiNmZmYiIGQ9Ik0xODUuMSA0MC4xaC0xM2MtMS43IDAtMy0xLjMtMy0zVjEyLjljMC0xLjcgMS4zLTMgMy0zaDEzYzEuNyAwIDMgMS4zIDMgM3YyNC4yYzAgMS42LTEuMyAzLTMgM3ptLTMxLjYtMTUuN2MwLTUuMyA0LjMtOS42IDkuNi05LjZoMTAuOWMxLjcgMCAzLTEuMyAzLTN2LS4xYzAtMS43LTEuMy0zLTMtM2gtMTFjLTguNiAwLTE1LjYgNy0xNS42IDE1LjZ2LjFjMCA4LjYgNyAxNS42IDE1LjYgMTUuNmgxMWMxLjcgMCAzLTEuMyAzLTN2LS4xYzAtMS43LTEuMy0zLTMtM2gtMTAuOWMtNS4zIDAtOS42LTQuMy05LjYtOS42di0uMXptLTI3LjktMTIuN2MwLTEuNy0xLjMtMy0zLTNoLTEzYy0xLjcgMC0zIDEuMy0zIDN2MTIuM2MwIDEuNyAxLjMgMyAzIDNoM2MxLjcgMCAzLTEuMyAzLTN2LTkuM2g3YzEuNyAwIDMtMS4zIDMtM3YtLjF6bS0yOC4xLTIuM2MwLTguNi03LTE1LjYtMTUuNi0xNS42aC0xM2MtMS43IDAtMyAxLjMtMyAzdjI0LjJjMCAxLjcgMS4zIDMgMyAzaDEzYzguNiAwIDE1LjYtNyAxNS42LTE1LjZ2LS4xem0tMy4xIDBjMCA1LjMtNC4zIDkuNi05LjYgOS42aC0xMFYxMS44aDEwYzUuMyAwIDkuNiA0LjMgOS42IDkuNnYuMXptLTMxLjMtMTIuN2MwLTEuNy0xLjMtMy0zLTNoLTEzYy0xLjcgMC0zIDEuMy0zIDN2MTIuM2MwIDEuNyAxLjMgMyAzIDNoM2MxLjcgMCAzLTEuMyAzLTN2LTkuM2g3YzEuNyAwIDMtMS4zIDMtM3YtLjF6bS0yOC4xLTIuM2MwLTguNi03LTE1LjYtMTUuNi0xNS42aC0xM2MtMS43IDAtMyAxLjMtMyAzdjI0LjJjMCAxLjcgMS4zIDMgMyAzaDEzYzguNiAwIDE1LjYtNyAxNS42LTE1LjZ2LS4xem0tMy4xIDBjMCA1LjMtNC4zIDkuNi05LjYgOS42aC0xMFYxMS44aDEwYzUuMyAwIDkuNiA0LjMgOS42IDkuNnYuMXoiLz48L3N2Zz4=" alt="HOT Travel" style="max-width: 180px; height: auto; display: block; margin: 0 auto;">
          </div>
          <h1>✈️ Your Travel Proposal is Ready!</h1>
          <p>Curated options for your {trip.get('destination','TBD')} trip</p>
        </div>
        <!-- Customer -->
        <div class="section">
          <h2>👤 Customer Details</h2>
          <div class="info"><strong>Name:</strong> {customer.get('name', customer.get('email', 'Valued Customer'))}</div>
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
        
        <!-- Proceed to Booking Button -->
        <div class="section" style="text-align: center; padding: 30px 0;">
          <a href="tel:0800355999" class="btn" style="background-color: #ff6b35; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 16px; display: inline-block;">
            📞 Call HOT to Book Now
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
    if isinstance(email_data, BaseModel):
        email_data = email_data.model_dump()
    
    # Check if Gmail is enabled via environment variable
    gmail_enabled = os.getenv("GMAIL_ENABLED", "false").lower() == "true"
    
    if not gmail_enabled:
        # Gmail disabled - simulate email for demo
        customer_email = email_data.get('customer', {}).get('email', 'unknown@example.com')
        destination = email_data.get('trip_details', {}).get('destination', 'Unknown Destination')
        
        print(f"[DEMO MODE] Gmail disabled - simulating email send:")
        print(f"[DEMO MODE] To: {customer_email}")
        print(f"[DEMO MODE] Subject: 🌆 Discover {destination}: Your Tailored Travel Guide")
        print(f"[DEMO MODE] HTML content length: {len(build_html(email_data))} characters")
        print(f"[DEMO MODE] Email would be sent in production with proper Gmail setup")
        
        return True
    
    try:
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
            message["subject"] = f"🌆 Discover {destination}: Your Tailored Travel Guide"

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