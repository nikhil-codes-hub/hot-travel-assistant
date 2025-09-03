import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent

class FlightScore(BaseModel):
    preference_score: float = Field(..., description="Score based on customer preferences")
    loyalty_score: float = Field(..., description="Score based on loyalty benefits")
    convenience_score: float = Field(..., description="Score based on convenience factors")
    value_score: float = Field(..., description="Score based on value for money")
    total_score: float = Field(..., description="Overall recommendation score")

class CuratedFlight(BaseModel):
    offer_id: str = Field(..., description="Original flight offer ID")
    rank: int = Field(..., description="Ranking position (1 = best)")
    recommendation_reason: str = Field(..., description="Why this flight is recommended")
    flight_score: FlightScore = Field(..., description="Detailed scoring breakdown")
    highlights: List[str] = Field([], description="Key highlights of this option")
    considerations: List[str] = Field([], description="Things to consider")
    original_offer: Dict[str, Any] = Field({}, description="Original flight offer data")

class FlightCurationResult(BaseModel):
    curated_flights: List[CuratedFlight]
    curation_criteria: Dict[str, Any]
    personalization_factors: List[str]
    total_options_analyzed: int
    curation_confidence: float

class FlightCuratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("FlightCuratorAgent")
        
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Curate and rank flight offers based on customer preferences
        
        Input:
        - flight_offers: List of flight offers from FlightsSearchAgent
        - customer_profile: Customer profile with preferences and history
        - requirements: Travel requirements (cabin class, budget, etc.)
        - enhanced_offers: Enhanced offers with CKB overlays from OffersAgent
        """
        
        flight_offers = input_data.get("flight_offers", [])
        customer_profile = input_data.get("customer_profile", {})
        requirements = input_data.get("requirements", {})
        enhanced_offers = input_data.get("enhanced_offers", {})
        
        if not flight_offers:
            self.log("No flight offers to curate")
            return self._generate_empty_curation_result()
        
        try:
            # Extract customer preferences
            preferences = self._extract_customer_preferences(customer_profile, requirements)
            
            # Score and rank each flight offer
            curated_flights = []
            for i, offer in enumerate(flight_offers):
                flight_score = self._score_flight_offer(offer, preferences, enhanced_offers)
                curated_flight = self._create_curated_flight(offer, flight_score, preferences, i + 1)
                curated_flights.append(curated_flight)
            
            # Sort by total score (descending)
            curated_flights.sort(key=lambda x: x.flight_score.total_score, reverse=True)
            
            # Update rankings
            for i, flight in enumerate(curated_flights):
                flight.rank = i + 1
            
            # Generate curation result
            result = FlightCurationResult(
                curated_flights=curated_flights[:10],  # Top 10 options
                curation_criteria=preferences,
                personalization_factors=self._get_personalization_factors(customer_profile),
                total_options_analyzed=len(flight_offers),
                curation_confidence=self._calculate_confidence(curated_flights, preferences)
            )
            
            self.log(f"✈️ Curated {len(curated_flights)} flight options based on customer preferences")
            return self.format_output(result.model_dump())
            
        except Exception as e:
            self.log(f"Flight curation failed: {e}")
            return self._generate_fallback_curation(flight_offers, customer_profile)
    
    def _extract_customer_preferences(self, customer_profile: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and standardize customer preferences for flight curation"""
        
        # Get customer profile data
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        preferences = customer_profile.get("preferences", {})
        travel_history = customer_profile.get("travel_history", [])
        
        # Get requirements
        budget = requirements.get("budget", 0)
        preferred_cabin = requirements.get("travel_class", "ECONOMY")
        departure_time_pref = requirements.get("departure_time_preference", "flexible")
        
        # Analyze travel history for patterns
        airline_preference = self._analyze_airline_preference(travel_history)
        timing_preference = self._analyze_timing_preference(travel_history)
        
        return {
            "loyalty_tier": loyalty_tier,
            "budget": budget,
            "preferred_cabin_class": preferred_cabin,
            "preferred_airlines": airline_preference,
            "departure_time_preference": departure_time_pref,
            "timing_patterns": timing_preference,
            "values_convenience": loyalty_tier in ["GOLD", "PLATINUM"],
            "price_sensitive": loyalty_tier == "STANDARD" and budget > 0,
            "premium_seeker": preferences.get("preferred_cabin_class") in ["Business", "First"]
        }
    
    def _analyze_airline_preference(self, travel_history: List[Dict[str, Any]]) -> List[str]:
        """Analyze preferred airlines from travel history"""
        if not travel_history:
            return []
        
        airline_counts = {}
        for booking in travel_history:
            # Extract airline from departure or destination codes (simplified)
            departure = booking.get("departure", {})
            if departure and isinstance(departure, dict):
                # This is a simplified approach - in reality you'd map airport codes to airlines
                airline_counts["preferred_airline"] = airline_counts.get("preferred_airline", 0) + 1
        
        return ["American", "Delta", "United"]  # Default major airlines
    
    def _analyze_timing_preference(self, travel_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze timing preferences from travel history"""
        return {
            "prefers_morning": True,
            "avoids_red_eye": True,
            "flexible_on_connections": False
        }
    
    def _score_flight_offer(self, offer: Dict[str, Any], preferences: Dict[str, Any], enhanced_offers: Dict[str, Any]) -> FlightScore:
        """Score a flight offer based on customer preferences"""
        
        # Extract flight details
        price_info = offer.get("price", {})
        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        validating_airline = offer.get("validatingAirlineCodes", [""])[0]
        
        # Calculate preference score (0-1)
        preference_score = self._calculate_preference_score(offer, preferences)
        
        # Calculate loyalty score (0-1) 
        loyalty_score = self._calculate_loyalty_score(offer, preferences, enhanced_offers)
        
        # Calculate convenience score (0-1)
        convenience_score = self._calculate_convenience_score(segments, preferences)
        
        # Calculate value score (0-1)
        value_score = self._calculate_value_score(offer, preferences, enhanced_offers)
        
        # Calculate weighted total score
        weights = {
            "preference": 0.25,
            "loyalty": 0.25,
            "convenience": 0.25,
            "value": 0.25
        }
        
        total_score = (
            preference_score * weights["preference"] +
            loyalty_score * weights["loyalty"] + 
            convenience_score * weights["convenience"] +
            value_score * weights["value"]
        )
        
        return FlightScore(
            preference_score=preference_score,
            loyalty_score=loyalty_score,
            convenience_score=convenience_score,
            value_score=value_score,
            total_score=total_score
        )
    
    def _calculate_preference_score(self, offer: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate how well flight matches customer preferences"""
        score = 0.5  # Base score
        
        # Check cabin class preference
        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        if segments:
            cabin_class = segments[0].get("cabin", "ECONOMY")
            preferred_cabin = preferences.get("preferred_cabin_class", "ECONOMY")
            if cabin_class.upper() == preferred_cabin.upper():
                score += 0.3
            elif self._is_cabin_upgrade(cabin_class, preferred_cabin):
                score += 0.2
        
        # Check airline preference
        validating_airline = offer.get("validatingAirlineCodes", [""])[0]
        preferred_airlines = preferences.get("preferred_airlines", [])
        if validating_airline in preferred_airlines:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_loyalty_score(self, offer: Dict[str, Any], preferences: Dict[str, Any], enhanced_offers: Dict[str, Any]) -> float:
        """Calculate loyalty benefits score"""
        loyalty_tier = preferences.get("loyalty_tier", "STANDARD")
        
        if loyalty_tier == "STANDARD":
            return 0.3
        elif loyalty_tier == "SILVER":
            return 0.6
        elif loyalty_tier == "GOLD":
            return 0.8
        elif loyalty_tier == "PLATINUM":
            return 1.0
        
        return 0.3
    
    def _calculate_convenience_score(self, segments: List[Dict[str, Any]], preferences: Dict[str, Any]) -> float:
        """Calculate convenience score based on flight timing and connections"""
        if not segments:
            return 0.3
        
        score = 0.5  # Base score
        
        # Check number of connections
        num_connections = len(segments) - 1
        if num_connections == 0:
            score += 0.3  # Direct flight bonus
        elif num_connections == 1:
            score += 0.1  # One connection acceptable
        else:
            score -= 0.2  # Multiple connections penalty
        
        # Check departure time preference
        first_segment = segments[0]
        departure_time = first_segment.get("departure", {}).get("at", "")
        if departure_time:
            try:
                dep_hour = int(departure_time[11:13])  # Extract hour from ISO datetime
                if 6 <= dep_hour <= 10 and preferences.get("timing_patterns", {}).get("prefers_morning", False):
                    score += 0.2
                elif dep_hour >= 22 and preferences.get("timing_patterns", {}).get("avoids_red_eye", True):
                    score -= 0.2
            except:
                pass
        
        return min(max(score, 0), 1.0)
    
    def _calculate_value_score(self, offer: Dict[str, Any], preferences: Dict[str, Any], enhanced_offers: Dict[str, Any]) -> float:
        """Calculate value for money score"""
        price_info = offer.get("price", {})
        original_price = float(price_info.get("total", 999999))
        
        # Find enhanced offer for this flight
        offer_id = offer.get("id", "")
        enhanced_price = original_price
        
        # Look for enhanced offer
        if enhanced_offers and "enhanced_offers" in enhanced_offers:
            for enhanced in enhanced_offers["enhanced_offers"]:
                if enhanced.get("original_offer_id") == offer_id:
                    enhanced_price = float(enhanced.get("effective_price", {}).get("total", original_price))
                    break
        
        # Calculate savings
        savings = original_price - enhanced_price
        savings_percentage = savings / original_price if original_price > 0 else 0
        
        # Score based on value
        budget = preferences.get("budget", 0)
        if budget > 0:
            budget_fit = enhanced_price / budget
            if budget_fit <= 0.8:
                score = 1.0  # Well under budget
            elif budget_fit <= 1.0:
                score = 0.8  # Within budget
            elif budget_fit <= 1.2:
                score = 0.5  # Slightly over budget
            else:
                score = 0.2  # Significantly over budget
        else:
            # No budget specified, score based on savings
            score = 0.5 + (savings_percentage * 2)  # Max boost of 0.5 for 25% savings
        
        return min(max(score, 0), 1.0)
    
    def _is_cabin_upgrade(self, actual_cabin: str, preferred_cabin: str) -> bool:
        """Check if actual cabin is an upgrade from preferred"""
        cabin_hierarchy = {
            "ECONOMY": 1,
            "PREMIUM_ECONOMY": 2, 
            "BUSINESS": 3,
            "FIRST": 4
        }
        
        actual_level = cabin_hierarchy.get(actual_cabin.upper(), 1)
        preferred_level = cabin_hierarchy.get(preferred_cabin.upper(), 1)
        
        return actual_level > preferred_level
    
    def _create_curated_flight(self, offer: Dict[str, Any], flight_score: FlightScore, preferences: Dict[str, Any], initial_rank: int) -> CuratedFlight:
        """Create a curated flight object with recommendation details"""
        
        offer_id = offer.get("id", f"flight_{initial_rank}")
        
        # Generate recommendation reason
        reason = self._generate_recommendation_reason(offer, flight_score, preferences)
        
        # Generate highlights
        highlights = self._generate_flight_highlights(offer, flight_score, preferences)
        
        # Generate considerations
        considerations = self._generate_flight_considerations(offer, flight_score)
        
        return CuratedFlight(
            offer_id=offer_id,
            rank=initial_rank,
            recommendation_reason=reason,
            flight_score=flight_score,
            highlights=highlights,
            considerations=considerations,
            original_offer=offer
        )
    
    def _generate_recommendation_reason(self, offer: Dict[str, Any], flight_score: FlightScore, preferences: Dict[str, Any]) -> str:
        """Generate personalized recommendation reason"""
        
        loyalty_tier = preferences.get("loyalty_tier", "STANDARD")
        price_info = offer.get("price", {})
        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        
        reasons = []
        
        # Check best aspects
        if flight_score.convenience_score >= 0.8:
            if len(segments) == 1:
                reasons.append("direct flight")
            else:
                reasons.append("convenient connections")
        
        if flight_score.value_score >= 0.8:
            reasons.append("excellent value")
        elif flight_score.value_score >= 0.6:
            reasons.append("good value")
        
        if flight_score.loyalty_score >= 0.8:
            reasons.append(f"{loyalty_tier} member benefits")
        
        if flight_score.preference_score >= 0.8:
            reasons.append("matches your preferences")
        
        if not reasons:
            reasons.append("solid option")
        
        return f"Recommended for {' and '.join(reasons[:2])}"
    
    def _generate_flight_highlights(self, offer: Dict[str, Any], flight_score: FlightScore, preferences: Dict[str, Any]) -> List[str]:
        """Generate flight highlights"""
        
        highlights = []
        
        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        price_info = offer.get("price", {})
        
        # Connection highlights
        if len(segments) == 1:
            highlights.append("✈️ Direct flight - no connections")
        elif len(segments) == 2:
            highlights.append("🔄 One convenient connection")
        
        # Price highlights
        total_price = price_info.get("total", "0")
        highlights.append(f"💰 Total price: {price_info.get('currency', 'USD')} {total_price}")
        
        # Loyalty highlights
        loyalty_tier = preferences.get("loyalty_tier", "STANDARD")
        if loyalty_tier in ["GOLD", "PLATINUM"]:
            highlights.append(f"⭐ {loyalty_tier} tier benefits included")
        
        # Cabin class highlights
        if segments:
            cabin_class = segments[0].get("cabin", "ECONOMY")
            if cabin_class != "ECONOMY":
                highlights.append(f"🥇 {cabin_class.title()} class experience")
        
        return highlights[:4]  # Limit to 4 highlights
    
    def _generate_flight_considerations(self, offer: Dict[str, Any], flight_score: FlightScore) -> List[str]:
        """Generate things to consider about this flight"""
        
        considerations = []
        
        segments = offer.get("itineraries", [{}])[0].get("segments", [])
        
        # Connection considerations
        if len(segments) > 2:
            considerations.append("⚠️ Multiple connections - longer travel time")
        
        # Timing considerations
        if segments:
            departure_time = segments[0].get("departure", {}).get("at", "")
            if departure_time:
                try:
                    dep_hour = int(departure_time[11:13])
                    if dep_hour >= 22 or dep_hour <= 5:
                        considerations.append("🌙 Red-eye flight - overnight travel")
                    elif dep_hour <= 7:
                        considerations.append("🌅 Early morning departure")
                except:
                    pass
        
        # Score-based considerations
        if flight_score.value_score < 0.5:
            considerations.append("💸 Higher price point")
        
        if flight_score.convenience_score < 0.5:
            considerations.append("⏰ Less convenient timing")
        
        return considerations[:3]  # Limit to 3 considerations
    
    def _get_personalization_factors(self, customer_profile: Dict[str, Any]) -> List[str]:
        """Get list of personalization factors applied"""
        
        factors = []
        
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        if loyalty_tier != "STANDARD":
            factors.append(f"{loyalty_tier} loyalty tier benefits")
        
        preferences = customer_profile.get("preferences", {})
        if preferences.get("preferred_cabin_class"):
            factors.append(f"Preferred {preferences['preferred_cabin_class']} class")
        
        travel_history = customer_profile.get("travel_history", [])
        if travel_history:
            factors.append("Historical travel patterns")
        
        factors.extend([
            "Convenience scoring (connections, timing)",
            "Value optimization with available discounts",
            "Airline preference matching"
        ])
        
        return factors
    
    def _calculate_confidence(self, curated_flights: List[CuratedFlight], preferences: Dict[str, Any]) -> float:
        """Calculate confidence in curation results"""
        
        if not curated_flights:
            return 0.0
        
        # Base confidence on score distribution
        scores = [f.flight_score.total_score for f in curated_flights]
        
        if not scores:
            return 0.5
        
        max_score = max(scores)
        min_score = min(scores)
        score_range = max_score - min_score
        
        # High confidence if there's a clear winner
        if max_score >= 0.8 and score_range >= 0.2:
            return 0.9
        elif max_score >= 0.7:
            return 0.8
        elif max_score >= 0.6:
            return 0.7
        else:
            return 0.6
    
    def _generate_empty_curation_result(self) -> Dict[str, Any]:
        """Generate empty result when no flights to curate"""
        
        result = FlightCurationResult(
            curated_flights=[],
            curation_criteria={},
            personalization_factors=["No flight offers available for curation"],
            total_options_analyzed=0,
            curation_confidence=0.0
        )
        
        return self.format_output(result.model_dump())
    
    def _generate_fallback_curation(self, flight_offers: List[Dict[str, Any]], customer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic curation when detailed curation fails"""
        
        curated_flights = []
        
        for i, offer in enumerate(flight_offers[:5]):  # Top 5 offers
            flight_score = FlightScore(
                preference_score=0.6,
                loyalty_score=0.5,
                convenience_score=0.6,
                value_score=0.5,
                total_score=0.55
            )
            
            curated_flight = CuratedFlight(
                offer_id=offer.get("id", f"flight_{i+1}"),
                rank=i + 1,
                recommendation_reason="Available flight option",
                flight_score=flight_score,
                highlights=["Flight option available"],
                considerations=["Review details carefully"],
                original_offer=offer
            )
            
            curated_flights.append(curated_flight)
        
        result = FlightCurationResult(
            curated_flights=curated_flights,
            curation_criteria={"fallback_mode": True},
            personalization_factors=["Basic curation applied"],
            total_options_analyzed=len(flight_offers),
            curation_confidence=0.4
        )
        
        return self.format_output(result.model_dump())