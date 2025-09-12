import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class SeatCharacteristic(BaseModel):
    code: str = Field(..., description="Characteristic code")
    description: str = Field(..., description="Characteristic description")

class Seat(BaseModel):
    number: str = Field(..., description="Seat number")
    available: bool = Field(..., description="Seat availability")
    characteristics: List[SeatCharacteristic] = Field([], description="Seat characteristics")
    price: Optional[Dict[str, Any]] = Field(None, description="Seat selection price")
    traveler_type: Optional[str] = Field(None, description="Allowed traveler type")

class Deck(BaseModel):
    deck_type: str = Field(..., description="Deck type (MAIN/UPPER)")
    seats: List[Seat] = Field(..., description="Seats on this deck")
    facilities: List[str] = Field([], description="Deck facilities")

class SeatMap(BaseModel):
    flight_offer_id: str = Field(..., description="Related flight offer ID")
    segment_id: str = Field(..., description="Flight segment ID")
    aircraft_code: str = Field(..., description="Aircraft code")
    cabin_class: str = Field(..., description="Cabin class")
    decks: List[Deck] = Field(..., description="Aircraft decks")
    seat_layout: Dict[str, Any] = Field({}, description="Seat map layout info")

class SeatRecommendation(BaseModel):
    seat_number: str = Field(..., description="Recommended seat")
    reason: str = Field(..., description="Why this seat is recommended")
    price: Optional[Dict[str, Any]] = Field(None, description="Seat price")
    characteristics: List[str] = Field(..., description="Seat features")

class SeatMapResult(BaseModel):
    seat_maps: List[SeatMap]
    recommendations: List[SeatRecommendation]
    ckb_benefits: List[str] = Field([], description="CKB seat benefits/waivers")
    total_seat_fees: Dict[str, Any] = Field({}, description="Total seat selection costs")

class SeatMapAgent(BaseAgent):
    def __init__(self):
        super().__init__("SeatMapAgent")
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.amadeus_base_url = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
        self.access_token = None
        self.token_expires_at = None
        
        # CKB seat benefits
        self.seat_benefits = self._load_seat_benefits()
    
    def _load_seat_benefits(self) -> Dict[str, Any]:
        """Load CKB seat selection benefits"""
        return {
            "loyalty_benefits": {
                "GOLD": {
                    "free_seat_selection": True,
                    "preferred_seats": ["extra_legroom", "window", "aisle"],
                    "waived_fees": ["seat_selection", "preferred_seat"]
                },
                "SILVER": {
                    "free_seat_selection": True,
                    "preferred_seats": ["window", "aisle"],
                    "waived_fees": ["seat_selection"]
                },
                "BRONZE": {
                    "free_seat_selection": False,
                    "preferred_seats": [],
                    "waived_fees": []
                }
            },
            "family_benefits": {
                "conditions": ["children_under_12", "family_booking"],
                "benefits": ["adjacent_seats", "priority_selection", "waived_fees"]
            },
            "accessibility": {
                "wheelchair_accessible": {"waived_fees": True, "priority_selection": True},
                "mobility_assistance": {"waived_fees": True, "preferred_locations": ["aisle", "bulkhead"]}
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Get seat maps and recommendations for flight offers
        
        Input:
        - flight_offer_id: Flight offer ID from previous search
        - customer_profile: Customer profile for personalized recommendations
        - preferences: Seat preferences (window/aisle, legroom, etc.)
        """
        required_fields = ["flight_offer_id"]
        self.validate_input(input_data, required_fields)
        
        # Check Amadeus API availability
        if not self.amadeus_client_id or not self.amadeus_client_secret:
            return self._generate_fallback_seatmap(input_data)
        
        try:
            # Ensure we have valid access token
            await self._ensure_access_token()
            
            # Get seat map from Amadeus
            seat_map_data = await self._get_amadeus_seatmap(input_data["flight_offer_id"])
            
            # Apply CKB benefits and generate recommendations
            result = await self._process_seatmap_with_benefits(seat_map_data, input_data)
            
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"Amadeus SeatMap API error: {e}")
            return self._generate_fallback_seatmap(input_data)
    
    async def _ensure_access_token(self):
        """Ensure valid Amadeus access token"""
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return
        
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.amadeus_client_id,
                "client_secret": self.amadeus_client_secret
            }
            
            response = await client.post(
                f"{self.amadeus_base_url}/v1/security/oauth2/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response["access_token"]
            expires_in = token_response.get("expires_in", 1799)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
    
    async def _get_amadeus_seatmap(self, flight_offer_id: str) -> Dict[str, Any]:
        """Get seat map from Amadeus SeatMap Display API"""
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Build request body for seat map
            request_body = {
                "data": [
                    {
                        "type": "flight-offer",
                        "id": flight_offer_id
                    }
                ]
            }
            
            response = await client.post(
                f"{self.amadeus_base_url}/v1/shopping/seatmaps",
                json=request_body,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            return response.json()
    
    async def _process_seatmap_with_benefits(self, seat_map_data: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process seat map data and apply CKB benefits"""
        
        customer_profile = input_data.get("customer_profile", {})
        preferences = input_data.get("preferences", {})
        
        # Process seat maps
        processed_seat_maps = []
        for seatmap_data in seat_map_data.get("data", []):
            seat_map = self._process_individual_seatmap(seatmap_data)
            processed_seat_maps.append(seat_map)
        
        # Generate recommendations based on preferences and profile
        recommendations = self._generate_seat_recommendations(
            processed_seat_maps, customer_profile, preferences
        )
        
        # Apply CKB benefits
        ckb_benefits = self._apply_seat_benefits(customer_profile, recommendations)
        
        # Calculate total costs with benefits
        total_fees = self._calculate_seat_fees(recommendations, ckb_benefits)
        
        result = SeatMapResult(
            seat_maps=processed_seat_maps,
            recommendations=recommendations,
            ckb_benefits=ckb_benefits,
            total_seat_fees=total_fees
        )
        
        return result.model_dump()
    
    def _process_individual_seatmap(self, seatmap_data: Dict[str, Any]) -> SeatMap:
        """Process individual seat map from Amadeus response"""
        
        # Extract flight information
        flight_offer_id = seatmap_data.get("flightOfferSource", {}).get("id", "")
        segment_id = seatmap_data.get("segmentId", "")
        aircraft_code = seatmap_data.get("aircraft", {}).get("code", "")
        cabin_class = seatmap_data.get("class", "ECONOMY")
        
        # Process decks
        decks = []
        for deck_data in seatmap_data.get("decks", []):
            # Process seats in deck
            seats = []
            for seat_data in deck_data.get("seats", []):
                # Process seat characteristics
                characteristics = []
                for char_data in seat_data.get("characteristics", []):
                    characteristic = SeatCharacteristic(
                        code=char_data.get("code", ""),
                        description=char_data.get("description", "")
                    )
                    characteristics.append(characteristic)
                
                # Process seat pricing
                seat_price = None
                if "price" in seat_data:
                    seat_price = seat_data["price"]
                
                seat = Seat(
                    number=seat_data.get("number", ""),
                    available=seat_data.get("available", True),
                    characteristics=characteristics,
                    price=seat_price,
                    traveler_type=seat_data.get("travelerType")
                )
                seats.append(seat)
            
            deck = Deck(
                deck_type=deck_data.get("deckType", "MAIN"),
                seats=seats,
                facilities=deck_data.get("facilities", [])
            )
            decks.append(deck)
        
        seat_map = SeatMap(
            flight_offer_id=flight_offer_id,
            segment_id=segment_id,
            aircraft_code=aircraft_code,
            cabin_class=cabin_class,
            decks=decks,
            seat_layout=seatmap_data.get("layout", {})
        )
        
        return seat_map
    
    def _generate_seat_recommendations(self, seat_maps: List[SeatMap], customer_profile: Dict[str, Any], preferences: Dict[str, Any]) -> List[SeatRecommendation]:
        """Generate personalized seat recommendations"""
        
        recommendations = []
        
        # Customer preferences
        preferred_location = preferences.get("location", "window")  # window/aisle/middle
        legroom_priority = preferences.get("legroom", False)
        quiet_preference = preferences.get("quiet", False)
        
        # Customer profile factors
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        age = customer_profile.get("age", 35)
        travel_frequency = customer_profile.get("travel_frequency", "occasional")
        
        for seat_map in seat_maps:
            best_seats = []
            
            for deck in seat_map.decks:
                for seat in deck.seats:
                    if not seat.available:
                        continue
                    
                    # Score the seat based on preferences
                    score = self._score_seat(seat, preferences, customer_profile)
                    
                    if score > 6:  # Only recommend good seats
                        reason = self._explain_seat_recommendation(seat, preferences)
                        
                        recommendation = SeatRecommendation(
                            seat_number=seat.number,
                            reason=reason,
                            price=seat.price,
                            characteristics=[char.description for char in seat.characteristics]
                        )
                        best_seats.append((score, recommendation))
            
            # Sort by score and take top 3
            best_seats.sort(key=lambda x: x[0], reverse=True)
            recommendations.extend([rec for score, rec in best_seats[:3]])
        
        return recommendations
    
    def _score_seat(self, seat: Seat, preferences: Dict[str, Any], customer_profile: Dict[str, Any]) -> float:
        """Score a seat based on preferences and customer profile"""
        score = 5.0  # Base score
        
        characteristics = [char.code.lower() for char in seat.characteristics]
        
        # Location preference
        preferred_location = preferences.get("location", "window").lower()
        if preferred_location == "window" and "window" in characteristics:
            score += 2.0
        elif preferred_location == "aisle" and "aisle" in characteristics:
            score += 2.0
        
        # Legroom preference
        if preferences.get("legroom", False):
            if any(char in characteristics for char in ["extra_legroom", "emergency_exit", "bulkhead"]):
                score += 1.5
        
        # Quiet preference
        if preferences.get("quiet", False):
            if any(char in characteristics for char in ["forward", "away_from_galley"]):
                score += 1.0
            if any(char in characteristics for char in ["near_galley", "near_lavatory"]):
                score -= 1.0
        
        # Age considerations
        age = customer_profile.get("age", 35)
        if age > 60:
            if "aisle" in characteristics:  # Easier access
                score += 1.0
            if "near_lavatory" in characteristics:
                score += 0.5
        
        # Frequent traveler preferences
        if customer_profile.get("travel_frequency") == "frequent":
            if "premium_location" in characteristics:
                score += 1.0
        
        return min(score, 10.0)
    
    def _explain_seat_recommendation(self, seat: Seat, preferences: Dict[str, Any]) -> str:
        """Explain why a seat is recommended"""
        characteristics = [char.description for char in seat.characteristics]
        
        reasons = []
        
        if preferences.get("location") == "window" and any("window" in char.lower() for char in characteristics):
            reasons.append("preferred window location")
        
        if preferences.get("location") == "aisle" and any("aisle" in char.lower() for char in characteristics):
            reasons.append("preferred aisle access")
        
        if preferences.get("legroom") and any("legroom" in char.lower() or "exit" in char.lower() for char in characteristics):
            reasons.append("extra legroom")
        
        if any("premium" in char.lower() for char in characteristics):
            reasons.append("premium location")
        
        if not reasons:
            reasons.append("good location with standard amenities")
        
        return f"Recommended for: {', '.join(reasons)}"
    
    def _apply_seat_benefits(self, customer_profile: Dict[str, Any], recommendations: List[SeatRecommendation]) -> List[str]:
        """Apply CKB seat selection benefits"""
        
        benefits = []
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        
        # Loyalty tier benefits
        if loyalty_tier in self.seat_benefits["loyalty_benefits"]:
            tier_benefits = self.seat_benefits["loyalty_benefits"][loyalty_tier]
            
            if tier_benefits["free_seat_selection"]:
                benefits.append(f"{loyalty_tier} tier: Free seat selection")
            
            if tier_benefits["waived_fees"]:
                waived = ", ".join(tier_benefits["waived_fees"])
                benefits.append(f"{loyalty_tier} tier: Waived fees for {waived}")
        
        # Family benefits
        has_children = customer_profile.get("children", 0) > 0
        if has_children:
            benefits.append("Family booking: Priority adjacent seat selection")
            benefits.append("Family booking: Children seat fees waived")
        
        # Accessibility benefits
        accessibility_needs = customer_profile.get("accessibility_needs", [])
        if accessibility_needs:
            benefits.append("Accessibility assistance: Seat selection fees waived")
            benefits.append("Accessibility assistance: Priority seat selection")
        
        return benefits
    
    def _calculate_seat_fees(self, recommendations: List[SeatRecommendation], ckb_benefits: List[str]) -> Dict[str, Any]:
        """Calculate total seat fees with CKB benefits applied"""
        
        total_fees = 0.0
        original_fees = 0.0
        savings = 0.0
        
        # Check if seat fees are waived
        fees_waived = any("free seat selection" in benefit.lower() or "fees waived" in benefit.lower() for benefit in ckb_benefits)
        
        for rec in recommendations:
            if rec.price:
                seat_fee = float(rec.price.get("amount", 0))
                original_fees += seat_fee
                
                if not fees_waived:
                    total_fees += seat_fee
                else:
                    savings += seat_fee
        
        return {
            "total_fees": f"${total_fees:.2f}",
            "original_fees": f"${original_fees:.2f}",
            "savings": f"${savings:.2f}",
            "currency": "USD",
            "fees_waived": fees_waived
        }
    
    def _generate_fallback_seatmap(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock seat map when API unavailable"""
        
        # Mock seat characteristics
        mock_characteristics = [
            SeatCharacteristic(code="WINDOW", description="Window seat"),
            SeatCharacteristic(code="AISLE", description="Aisle seat"),
            SeatCharacteristic(code="EXTRA_LEGROOM", description="Extra legroom")
        ]
        
        # Mock seats
        mock_seats = []
        for row in ["12", "13", "14"]:
            for letter in ["A", "C", "D", "F"]:
                seat_char = []
                if letter in ["A", "F"]:
                    seat_char.append(mock_characteristics[0])  # Window
                elif letter in ["C", "D"]:
                    seat_char.append(mock_characteristics[1])  # Aisle
                
                seat = Seat(
                    number=f"{row}{letter}",
                    available=True,
                    characteristics=seat_char,
                    price={"amount": "25.00", "currency": "USD"},
                    traveler_type="ADULT"
                )
                mock_seats.append(seat)
        
        # Mock deck
        mock_deck = Deck(
            deck_type="MAIN",
            seats=mock_seats,
            facilities=["Overhead bins", "Reading lights"]
        )
        
        # Mock seat map
        mock_seatmap = SeatMap(
            flight_offer_id=input_data["flight_offer_id"],
            segment_id="1",
            aircraft_code="737",
            cabin_class="ECONOMY",
            decks=[mock_deck],
            seat_layout={"rows": 30, "seats_per_row": 6}
        )
        
        # Mock recommendations
        mock_recommendations = [
            SeatRecommendation(
                seat_number="12A",
                reason="Window seat with good forward location",
                price={"amount": "25.00", "currency": "USD"},
                characteristics=["Window seat"]
            ),
            SeatRecommendation(
                seat_number="13C",
                reason="Aisle seat for easy access",
                price={"amount": "25.00", "currency": "USD"},
                characteristics=["Aisle seat"]
            )
        ]
        
        result = SeatMapResult(
            seat_maps=[mock_seatmap],
            recommendations=mock_recommendations,
            ckb_benefits=["Mock seat selection available"],
            total_seat_fees={
                "total_fees": "$50.00",
                "currency": "USD",
                "mode": "fallback_mock_data"
            }
        )
        
        return self.format_output(result.model_dump())