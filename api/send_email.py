import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pickle
from typing import List, Optional

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pydantic import BaseModel
from shapely import transform

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
    creds = None
    if os.path.exists("token.pickle"):
        print("in token.pickle authenticate")
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

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

    # ✅ Generate flights HTML cards
    flights_html = "".join([
        f"""
        <div class="card">
          <div><strong>Option {f.get('rank','-')}:</strong> {f.get('airline','TBD')}</div>
          <div>Route: {f.get('route','TBD')}</div>
          <div>Price: {f.get('price','TBD')}</div>
          <div>Why: {f.get('recommendation_reason','')}</div>
        </div>
        """ for f in flights
    ]) or "<p>No flights available</p>"

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
          background: linear-gradient(135deg, #0061f2, #00b5f5);
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
        <!-- Header -->
        <div class="header">
          <h1>✈️ Your Travel Proposal is Ready!</h1>
          <p>Curated options for your {trip.get('destination','TBD')} trip</p>
        </div>

        <!-- Customer -->
        <div class="section">
          <h2>👤 Customer Details</h2>
          <div class="info"><strong>Name:</strong> {customer.get('name','Valued Customer')}</div>
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
    if isinstance(email_data, BaseModel):
        email_data = email_data.model_dump()
    service = gmail_authenticate()
    message = MIMEMultipart("alternative")
    for i in list(email_data['customer']['email'].split(',')):
        message["to"] = i
        message["from"] = "no_reply@gmail.com"
        message["subject"] = "Welcome to Trip"

        # Attach HTML body
        html_body = build_html(email_data)
        message.attach(MIMEText(html_body, "html"))

        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": raw_message}
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"[OK] Email sent. Message Id: {sent_message['id']}")