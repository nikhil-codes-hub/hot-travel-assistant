import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pickle
from typing import List, Optional

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pydantic import BaseModel

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
    return_date = trip.get("return_date") or "TBD"

    # Generate flights HTML
    flights_html = "".join([
        f"<li>{f.get('airline', 'TBD')} | {f.get('route', 'TBD')} | {f.get('price', 'TBD')} ({f.get('recommendation_reason', '')})</li>"
        for f in flights
    ]) or "<li>No flights available</li>"

    # Generate hotels HTML
    hotels_html = "".join([
        f"<li>{h.get('name', 'TBD')} - {h.get('price_per_night', 'TBD')} | {h.get('location', 'TBD')} | {h.get('room_type', 'TBD')}</li>"
        for h in hotels
    ]) or "<li>No hotels available</li>"

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height:1.6; background:#f4f6f8; padding:20px;">
      <div style="background:#fff; padding:20px; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
        <h2 style="color:#2c3e50;">🌍 Your Smart Trip Itinerary</h2>
        <p>Dear {customer.get('name', 'Valued Customer')},</p>
        <p>Here’s your personalized travel itinerary:</p>

        <h3>✈️ Flights</h3>
        <ul>
          {flights_html}
        </ul>

        <h3>🏨 Hotels</h3>
        <ul>
          {hotels_html}
        </ul>

        <h3>📋 Trip Summary</h3>
        <p>
          Destination: <b>{trip.get('destination', 'TBD')}</b><br>
          Dates: {departure_date} → {return_date}<br>
          Passengers: {trip.get('passengers', 'TBD')}<br>
          Travel Class: {trip.get('travel_class', 'TBD')}<br>
          Budget: {trip.get('budget_currency', '')} {trip.get('budget', 'TBD')}
        </p>

        <p style="color:#555;">We look forward to making your trip amazing! ✨</p>
        <p>Warm regards,<br><b>Smart Trip Assistant Team</b></p>
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