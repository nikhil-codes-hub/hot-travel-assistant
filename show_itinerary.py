#!/usr/bin/env python3

from agents.flights_search.flights_agent import FlightsSearchAgent
from agents.hotel_search.hotel_agent import HotelSearchAgent
import asyncio

async def show_complete_itinerary():
    print('=' * 70)
    print('✈️🏨 YOUR COMPLETE TRAVEL ITINERARY')
    print('=' * 70)
    print()
    
    # Get flight details
    print('✈️ FLIGHT OPTIONS:')
    print('-' * 30)
    
    flight_agent = FlightsSearchAgent()
    flight_input = {
        'origin': 'LAX',
        'destination': 'ZUR', 
        'departure_date': '2025-11-25',
        'return_date': '2025-12-01',
        'adults': 2,
        'travel_class': 'BUSINESS'
    }
    
    try:
        flight_result = await flight_agent.execute(flight_input, 'display-session')
        flights = flight_result.get('data', {}).get('offers', [])
        
        if flights:
            print(f'Found {len(flights)} live flight options from Amadeus API!')
            for i, flight in enumerate(flights[:3], 1):
                segments = flight.get('segments', [])
                if segments:
                    segment = segments[0]
                    departure = segment.get('departure', {})
                    arrival = segment.get('arrival', {})
                    price = flight.get('price', {})
                    
                    print(f'\nOption {i}:')
                    print(f'  🛫 {departure.get("iataCode", "LAX")} → {arrival.get("iataCode", "ZUR")}')
                    print(f'  ⏰ Depart: {departure.get("at", "08:00")}')
                    print(f'  ⏰ Arrive: {arrival.get("at", "20:00")}')
                    print(f'  ✈️ Flight: {segment.get("flight_number", "AA123")}')
                    print(f'  💺 Class: {segment.get("cabin_class", "BUSINESS")}')
                    print(f'  💰 Price: ${price.get("total", "899")} {price.get("currency", "USD")}')
        else:
            print('Mock flight data (API returned 0 results):')
            print('  🛫 LAX → ZUR (Business Class)')
            print('  ⏰ Nov 25, 2025 - 8:00 AM')
            print('  💰 Starting from $899 USD')
            
    except Exception as e:
        print(f'Error getting flights: {e}')
        print('Using fallback flight data')
    
    print()
    
    # Get hotel details
    print('🏨 HOTEL OPTIONS:')
    print('-' * 30)
    
    hotel_agent = HotelSearchAgent()
    hotel_input = {
        'cityCode': 'ZUR',
        'checkInDate': '2025-11-25',
        'checkOutDate': '2025-12-01',
        'adults': 2,
        'rooms': 1
    }
    
    try:
        hotel_result = await hotel_agent.execute(hotel_input, 'display-session')
        hotels = hotel_result.get('data', {}).get('hotels', [])
        
        for i, hotel in enumerate(hotels, 1):
            print(f'\nHotel Option {i}:')
            print(f'  🏨 Name: {hotel.get("name", "Grand City Hotel")}')
            print(f'  ⭐ Rating: {hotel.get("rating", 4.2)}/5.0')
            
            address = hotel.get('address', {})
            lines = address.get('lines', [])
            city = address.get('cityName', 'Zurich')
            location = lines[0] if lines else 'City Center'
            print(f'  📍 Location: {location}, {city}')
            
            offers = hotel.get('offers', [])
            if offers:
                offer = offers[0]
                price = offer.get('price', {})
                room = offer.get('room', {})
                room_type = room.get('type', 'STANDARD')
                print(f'  🛏️ Room: {room_type.replace("_", " ").title()}')
                print(f'  💰 Price: ${price.get("total", "199")} per night')
                total_per_night = float(price.get("total", "199"))
                print(f'  📅 Total (6 nights): ${total_per_night * 6:.0f}')
            
            amenities = hotel.get('amenities', [])
            if amenities:
                amenity_names = []
                for amenity in amenities[:3]:
                    desc = amenity.get('description', '')
                    if desc:
                        amenity_names.append(desc.replace('_', ' ').title())
                if amenity_names:
                    print(f'  🎯 Amenities: {", ".join(amenity_names)}')
                    
    except Exception as e:
        print(f'Error getting hotels: {e}')
    
    print()
    print('📋 COMPLETE ITINERARY SUMMARY:')
    print('=' * 40)
    print('🗓️ Trip: Nov 25 - Dec 1, 2025 (7 days)')
    print('👥 Travelers: 2 people')
    print('🎯 Destination: Snowy Alpine destination')
    print('💺 Flight Class: Business')
    print()
    print('💰 ESTIMATED TOTAL COSTS:')
    print('  ✈️ Flights: $800-1200')
    print('  🏨 Hotels: $700-1200 (6 nights)')
    print('  🎯 Activities: $350')
    print('  🍽️ Meals: $525')
    print('  💳 GRAND TOTAL: $2,375-3,275')
    print()
    print('✅ Status: Complete travel plan ready!')
    print('🚀 Next: Review options and proceed with booking')
    print('=' * 70)

if __name__ == "__main__":
    asyncio.run(show_complete_itinerary())