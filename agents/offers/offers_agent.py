import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel, Field
import json
from agents.base_agent import BaseAgent

class Discount(BaseModel):
    type: str = Field(..., description="Discount type: percentage/fixed/upgrade")
    value: float = Field(..., description="Discount value")
    description: str = Field(..., description="Discount description")
    conditions: List[str] = Field([], description="Conditions for discount")
    expires_at: Optional[str] = Field(None, description="Discount expiry date")

class SupplierRanking(BaseModel):
    supplier_code: str = Field(..., description="Supplier/airline/hotel code")
    ranking_score: float = Field(..., description="Ranking score 0.0-1.0")
    reasons: List[str] = Field(..., description="Reasons for ranking")
    preferred: bool = Field(False, description="Is preferred supplier")

class EnhancedOffer(BaseModel):
    original_offer_id: str = Field(..., description="Original offer ID")
    offer_type: str = Field(..., description="flight/hotel/package")
    original_price: Dict[str, Any] = Field(..., description="Original price")
    effective_price: Dict[str, Any] = Field(..., description="Price after CKB overlays")
    savings: Dict[str, Any] = Field({}, description="Savings breakdown")
    applied_discounts: List[Discount] = Field([], description="Applied discounts")
    supplier_ranking: Optional[SupplierRanking] = Field(None, description="Supplier ranking")
    ckb_explanations: List[str] = Field([], description="CKB overlay explanations")
    recommendation_score: float = Field(..., description="Overall recommendation score")

class OffersResult(BaseModel):
    enhanced_offers: List[EnhancedOffer]
    total_original_price: float
    total_effective_price: float
    total_savings: float
    ckb_insights: Dict[str, Any]

class OffersAgent(BaseAgent):
    def __init__(self):
        super().__init__("OffersAgent")
        self.amadeus_client_id = os.getenv("AMADEUS_CLIENT_ID")
        self.amadeus_client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        self.amadeus_base_url = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
        self.access_token = None
        self.token_expires_at = None
        
        # Commercial Knowledge Base data (in production, this would be from database/API)
        self.ckb_data = self._load_commercial_knowledge_base()
    
    def _load_commercial_knowledge_base(self) -> Dict[str, Any]:
        """Load Commercial Knowledge Base data - discounts, waivers, supplier rankings"""
        return {
            "discounts": {
                "loyalty_tiers": {
                    "GOLD": {"flight_discount": 0.10, "hotel_discount": 0.15},
                    "SILVER": {"flight_discount": 0.05, "hotel_discount": 0.10},
                    "BRONZE": {"flight_discount": 0.02, "hotel_discount": 0.05}
                },
                "seasonal": {
                    "shoulder_season": {"discount": 0.08, "months": [3, 4, 5, 9, 10, 11]},
                    "peak_season": {"discount": 0.0, "months": [6, 7, 8, 12, 1, 2]}
                },
                "advance_booking": {
                    "30_days": {"discount": 0.05},
                    "60_days": {"discount": 0.10},
                    "90_days": {"discount": 0.15}
                }
            },
            "supplier_rankings": {
                "airlines": {
                    "AA": {"score": 0.85, "preferred": True, "reasons": ["Reliability", "Route network"]},
                    "BA": {"score": 0.82, "preferred": True, "reasons": ["Service quality", "Lounge access"]},
                    "UA": {"score": 0.75, "preferred": False, "reasons": ["Coverage", "Price competitive"]},
                    "DL": {"score": 0.80, "preferred": True, "reasons": ["On-time performance", "Fleet quality"]}
                },
                "hotel_chains": {
                    "AC": {"score": 0.90, "preferred": True, "reasons": ["Consistent quality", "Global presence"]},
                    "HI": {"score": 0.85, "preferred": True, "reasons": ["Premium service", "Amenities"]},
                    "MC": {"score": 0.80, "preferred": False, "reasons": ["Good value", "Locations"]}
                }
            },
            "fee_waivers": {
                "change_fee": {
                    "conditions": ["GOLD_tier", "business_class", "advance_booking_90"],
                    "waiver_amount": 200.00
                },
                "seat_selection": {
                    "conditions": ["SILVER_tier", "family_booking"],
                    "waiver_amount": 50.00
                }
            },
            "special_offers": {
                "package_deals": {
                    "flight_hotel_combo": {"discount": 0.12, "min_nights": 3},
                    "extended_stay": {"discount": 0.08, "min_nights": 7}
                }
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Apply CKB overlays to flight and hotel offers
        
        Input:
        - flight_offers: List of flight offers from FlightsSearchAgent
        - hotel_offers: List of hotel offers from HotelSearchAgent  
        - customer_profile: Customer profile data (loyalty tier, preferences)
        - booking_context: Booking details (dates, advance booking days, etc.)
        """
        
        try:
            flight_offers = input_data.get("flight_offers", [])
            hotel_offers = input_data.get("hotel_offers", [])
            customer_profile = input_data.get("customer_profile", {})
            booking_context = input_data.get("booking_context", {})
            
            enhanced_offers = []
            total_original_price = 0
            total_effective_price = 0
            
            # Process flight offers
            for offer in flight_offers:
                enhanced_offer = await self._apply_flight_overlays(offer, customer_profile, booking_context)
                enhanced_offers.append(enhanced_offer)
                total_original_price += float(enhanced_offer.original_price.get("total", 0))
                total_effective_price += float(enhanced_offer.effective_price.get("total", 0))
            
            # Process hotel offers
            for offer in hotel_offers:
                enhanced_offer = await self._apply_hotel_overlays(offer, customer_profile, booking_context)
                enhanced_offers.append(enhanced_offer)
                total_original_price += float(enhanced_offer.original_price.get("total", 0))
                total_effective_price += float(enhanced_offer.effective_price.get("total", 0))
            
            # Generate CKB insights
            ckb_insights = self._generate_ckb_insights(enhanced_offers, customer_profile)
            
            result = OffersResult(
                enhanced_offers=enhanced_offers,
                total_original_price=total_original_price,
                total_effective_price=total_effective_price,
                total_savings=total_original_price - total_effective_price,
                ckb_insights=ckb_insights
            )
            
            return self.format_output(result.model_dump())
            
        except Exception as e:
            self.log(f"OffersAgent error: {e}")
            # Return original offers without enhancement as fallback
            return self._generate_fallback_offers(input_data)
    
    async def _apply_flight_overlays(self, flight_offer: Dict[str, Any], customer_profile: Dict[str, Any], booking_context: Dict[str, Any]) -> EnhancedOffer:
        """Apply CKB overlays to a flight offer"""
        
        original_price = flight_offer.get("price", {})
        original_total = float(original_price.get("total", 0))
        
        applied_discounts = []
        explanations = []
        
        # Start with original price
        effective_total = original_total
        
        # Apply loyalty tier discount
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        if loyalty_tier in self.ckb_data["discounts"]["loyalty_tiers"]:
            discount_rate = self.ckb_data["discounts"]["loyalty_tiers"][loyalty_tier]["flight_discount"]
            discount_amount = original_total * discount_rate
            effective_total -= discount_amount
            
            applied_discounts.append(Discount(
                type="percentage",
                value=discount_rate * 100,
                description=f"{loyalty_tier} loyalty tier discount",
                conditions=[f"{loyalty_tier}_tier"],
                expires_at=None
            ))
            explanations.append(f"Applied {discount_rate*100:.0f}% {loyalty_tier} tier discount")
        
        # Apply advance booking discount
        advance_days = booking_context.get("advance_booking_days", 0)
        if advance_days >= 90:
            discount_rate = self.ckb_data["discounts"]["advance_booking"]["90_days"]["discount"]
        elif advance_days >= 60:
            discount_rate = self.ckb_data["discounts"]["advance_booking"]["60_days"]["discount"]
        elif advance_days >= 30:
            discount_rate = self.ckb_data["discounts"]["advance_booking"]["30_days"]["discount"]
        else:
            discount_rate = 0
        
        if discount_rate > 0:
            discount_amount = original_total * discount_rate
            effective_total -= discount_amount
            
            applied_discounts.append(Discount(
                type="percentage",
                value=discount_rate * 100,
                description=f"Advance booking discount ({advance_days} days)",
                conditions=[f"advance_booking_{advance_days}"],
                expires_at=None
            ))
            explanations.append(f"Applied {discount_rate*100:.0f}% advance booking discount")
        
        # Apply seasonal discount
        departure_month = booking_context.get("departure_month", datetime.now().month)
        shoulder_months = self.ckb_data["discounts"]["seasonal"]["shoulder_season"]["months"]
        if departure_month in shoulder_months:
            discount_rate = self.ckb_data["discounts"]["seasonal"]["shoulder_season"]["discount"]
            discount_amount = original_total * discount_rate
            effective_total -= discount_amount
            
            applied_discounts.append(Discount(
                type="percentage",
                value=discount_rate * 100,
                description="Shoulder season discount",
                conditions=["shoulder_season"],
                expires_at=None
            ))
            explanations.append(f"Applied {discount_rate*100:.0f}% shoulder season discount")
        
        # Get supplier ranking
        validating_airline = flight_offer.get("validatingAirlineCodes", [""])[0]
        supplier_ranking = None
        if validating_airline in self.ckb_data["supplier_rankings"]["airlines"]:
            ranking_data = self.ckb_data["supplier_rankings"]["airlines"][validating_airline]
            supplier_ranking = SupplierRanking(
                supplier_code=validating_airline,
                ranking_score=ranking_data["score"],
                reasons=ranking_data["reasons"],
                preferred=ranking_data["preferred"]
            )
            
            if ranking_data["preferred"]:
                explanations.append(f"Preferred airline partner with {ranking_data['score']*100:.0f}% quality score")
        
        # Calculate recommendation score
        base_score = 0.5
        if supplier_ranking and supplier_ranking.preferred:
            base_score += 0.2
        if applied_discounts:
            base_score += min(0.3, len(applied_discounts) * 0.1)
        
        recommendation_score = min(1.0, base_score)
        
        # Build effective price structure
        effective_price = original_price.copy()
        effective_price["total"] = f"{effective_total:.2f}"
        
        # Calculate savings
        savings = {
            "amount": original_total - effective_total,
            "currency": original_price.get("currency", "USD"),
            "percentage": ((original_total - effective_total) / original_total * 100) if original_total > 0 else 0
        }
        
        return EnhancedOffer(
            original_offer_id=flight_offer.get("id", ""),
            offer_type="flight",
            original_price=original_price,
            effective_price=effective_price,
            savings=savings,
            applied_discounts=applied_discounts,
            supplier_ranking=supplier_ranking,
            ckb_explanations=explanations,
            recommendation_score=recommendation_score
        )
    
    async def _apply_hotel_overlays(self, hotel_offer: Dict[str, Any], customer_profile: Dict[str, Any], booking_context: Dict[str, Any]) -> EnhancedOffer:
        """Apply CKB overlays to a hotel offer"""
        
        # Extract price from hotel structure (hotels have offers array)
        offers = hotel_offer.get("offers", [])
        if not offers:
            # Fallback structure
            original_price = {"total": "0.00", "currency": "USD"}
        else:
            original_price = offers[0].get("price", {"total": "0.00", "currency": "USD"})
        
        original_total = float(original_price.get("total", 0))
        effective_total = original_total
        
        applied_discounts = []
        explanations = []
        
        # Apply loyalty tier discount for hotels
        loyalty_tier = customer_profile.get("loyalty_tier", "STANDARD")
        if loyalty_tier in self.ckb_data["discounts"]["loyalty_tiers"]:
            discount_rate = self.ckb_data["discounts"]["loyalty_tiers"][loyalty_tier]["hotel_discount"]
            discount_amount = original_total * discount_rate
            effective_total -= discount_amount
            
            applied_discounts.append(Discount(
                type="percentage",
                value=discount_rate * 100,
                description=f"{loyalty_tier} loyalty tier hotel discount",
                conditions=[f"{loyalty_tier}_tier"],
                expires_at=None
            ))
            explanations.append(f"Applied {discount_rate*100:.0f}% {loyalty_tier} tier hotel discount")
        
        # Apply extended stay discount
        nights = booking_context.get("nights", 1)
        if nights >= 7:
            discount_rate = self.ckb_data["special_offers"]["package_deals"]["extended_stay"]["discount"]
            discount_amount = original_total * discount_rate
            effective_total -= discount_amount
            
            applied_discounts.append(Discount(
                type="percentage",
                value=discount_rate * 100,
                description=f"Extended stay discount ({nights} nights)",
                conditions=["extended_stay"],
                expires_at=None
            ))
            explanations.append(f"Applied {discount_rate*100:.0f}% extended stay discount")
        
        # Get hotel chain ranking
        chain_code = hotel_offer.get("chainCode")
        supplier_ranking = None
        if chain_code and chain_code in self.ckb_data["supplier_rankings"]["hotel_chains"]:
            ranking_data = self.ckb_data["supplier_rankings"]["hotel_chains"][chain_code]
            supplier_ranking = SupplierRanking(
                supplier_code=chain_code,
                ranking_score=ranking_data["score"],
                reasons=ranking_data["reasons"],
                preferred=ranking_data["preferred"]
            )
            
            if ranking_data["preferred"]:
                explanations.append(f"Preferred hotel partner with {ranking_data['score']*100:.0f}% quality score")
        
        # Calculate recommendation score
        base_score = 0.5
        if supplier_ranking and supplier_ranking.preferred:
            base_score += 0.2
        if applied_discounts:
            base_score += min(0.3, len(applied_discounts) * 0.1)
        
        recommendation_score = min(1.0, base_score)
        
        # Build effective price structure
        effective_price = original_price.copy()
        effective_price["total"] = f"{effective_total:.2f}"
        
        # Calculate savings
        savings = {
            "amount": original_total - effective_total,
            "currency": original_price.get("currency", "USD"),
            "percentage": ((original_total - effective_total) / original_total * 100) if original_total > 0 else 0
        }
        
        return EnhancedOffer(
            original_offer_id=hotel_offer.get("hotelId", ""),
            offer_type="hotel",
            original_price=original_price,
            effective_price=effective_price,
            savings=savings,
            applied_discounts=applied_discounts,
            supplier_ranking=supplier_ranking,
            ckb_explanations=explanations,
            recommendation_score=recommendation_score
        )
    
    def _generate_ckb_insights(self, enhanced_offers: List[EnhancedOffer], customer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights based on CKB overlays"""
        
        total_discounts = sum(len(offer.applied_discounts) for offer in enhanced_offers)
        preferred_suppliers = sum(1 for offer in enhanced_offers if offer.supplier_ranking and offer.supplier_ranking.preferred)
        
        insights = {
            "total_discounts_applied": total_discounts,
            "preferred_suppliers_count": preferred_suppliers,
            "average_recommendation_score": sum(offer.recommendation_score for offer in enhanced_offers) / len(enhanced_offers) if enhanced_offers else 0,
            "customer_tier_benefits": customer_profile.get("loyalty_tier", "STANDARD"),
            "savings_opportunities": [],
            "supplier_quality_score": 0
        }
        
        # Generate savings opportunities
        for offer in enhanced_offers:
            if offer.savings.get("amount", 0) > 0:
                insights["savings_opportunities"].append({
                    "offer_id": offer.original_offer_id,
                    "offer_type": offer.offer_type,
                    "savings_amount": offer.savings["amount"],
                    "savings_percentage": offer.savings["percentage"]
                })
        
        # Calculate average supplier quality
        supplier_scores = [offer.supplier_ranking.ranking_score for offer in enhanced_offers if offer.supplier_ranking]
        if supplier_scores:
            insights["supplier_quality_score"] = sum(supplier_scores) / len(supplier_scores)
        
        return insights
    
    def _generate_fallback_offers(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic offers without CKB overlays as fallback"""
        
        flight_offers = input_data.get("flight_offers", [])
        hotel_offers = input_data.get("hotel_offers", [])
        
        fallback_offers = []
        total_price = 0
        
        # Process flight offers without enhancement
        for offer in flight_offers:
            price = offer.get("price", {"total": "0.00", "currency": "USD"})
            total_price += float(price.get("total", 0))
            
            fallback_offer = EnhancedOffer(
                original_offer_id=offer.get("id", ""),
                offer_type="flight",
                original_price=price,
                effective_price=price,
                savings={},
                applied_discounts=[],
                supplier_ranking=None,
                ckb_explanations=["CKB overlays not available"],
                recommendation_score=0.5
            )
            fallback_offers.append(fallback_offer)
        
        # Process hotel offers without enhancement  
        for offer in hotel_offers:
            offers = offer.get("offers", [])
            price = offers[0].get("price", {"total": "0.00", "currency": "USD"}) if offers else {"total": "0.00", "currency": "USD"}
            total_price += float(price.get("total", 0))
            
            fallback_offer = EnhancedOffer(
                original_offer_id=offer.get("hotelId", ""),
                offer_type="hotel",
                original_price=price,
                effective_price=price,
                savings={},
                applied_discounts=[],
                supplier_ranking=None,
                ckb_explanations=["CKB overlays not available"],
                recommendation_score=0.5
            )
            fallback_offers.append(fallback_offer)
        
        fallback_result = OffersResult(
            enhanced_offers=fallback_offers,
            total_original_price=total_price,
            total_effective_price=total_price,
            total_savings=0,
            ckb_insights={
                "mode": "fallback",
                "total_discounts_applied": 0,
                "preferred_suppliers_count": 0
            }
        )
        
        return self.format_output(fallback_result.model_dump())