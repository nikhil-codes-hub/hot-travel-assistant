import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class InsuranceCoverage(BaseModel):
    category: str = Field(..., description="Coverage category")
    coverage_limit: Optional[str] = Field(None, description="Coverage limit amount")
    deductible: Optional[str] = Field(None, description="Deductible amount")
    details: List[str] = Field(..., description="Coverage details")

class InsuranceProduct(BaseModel):
    provider: str = Field(..., description="Insurance provider name")
    product_name: str = Field(..., description="Product name")
    coverage_type: str = Field(..., description="basic/comprehensive/premium")
    price: Dict[str, Any] = Field(..., description="Price information")
    coverages: List[InsuranceCoverage] = Field(..., description="Coverage details")
    exclusions: List[str] = Field(..., description="What's not covered")
    benefits: List[str] = Field(..., description="Key benefits")
    purchase_url: Optional[str] = Field(None, description="Where to purchase")
    terms_url: Optional[str] = Field(None, description="Terms and conditions URL")

class InsuranceRecommendation(BaseModel):
    recommended_products: List[InsuranceProduct]
    traveler_profile: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    disclaimers: List[str]

class InsuranceAgent(BaseAgent):
    def __init__(self):
        super().__init__("InsuranceAgent")
        # Partner insurance products (in production, integrate with partner APIs)
        self.insurance_products = self._load_insurance_products()
    
    def _load_insurance_products(self) -> List[Dict[str, Any]]:
        """Load partner insurance products"""
        return [
            {
                "provider": "TravelGuard",
                "product_name": "Essential Plan",
                "coverage_type": "basic",
                "base_price": 45,
                "price_per_day": 2.5,
                "coverages": [
                    {
                        "category": "Trip Cancellation",
                        "coverage_limit": "$10,000",
                        "deductible": "$0",
                        "details": ["Cancel for covered reasons", "Pre-existing condition coverage available"]
                    },
                    {
                        "category": "Emergency Medical",
                        "coverage_limit": "$100,000",
                        "deductible": "$100",
                        "details": ["Emergency medical expenses", "Emergency evacuation"]
                    },
                    {
                        "category": "Baggage Protection",
                        "coverage_limit": "$1,000",
                        "deductible": "$50",
                        "details": ["Lost, stolen, or damaged baggage", "Delayed baggage coverage"]
                    }
                ],
                "exclusions": ["Pre-existing medical conditions (without waiver)", "High-risk activities", "Travel to restricted countries"],
                "benefits": ["24/7 assistance hotline", "Direct payment to providers", "Mobile app for claims"]
            },
            {
                "provider": "Allianz Travel",
                "product_name": "OneTrip Premier",
                "coverage_type": "comprehensive",
                "base_price": 85,
                "price_per_day": 4.2,
                "coverages": [
                    {
                        "category": "Trip Cancellation",
                        "coverage_limit": "$100,000",
                        "deductible": "$0",
                        "details": ["Cancel for any reason (75% coverage)", "Pre-existing condition waiver available"]
                    },
                    {
                        "category": "Emergency Medical",
                        "coverage_limit": "$1,000,000",
                        "deductible": "$0",
                        "details": ["Comprehensive medical coverage", "Air ambulance", "Repatriation"]
                    },
                    {
                        "category": "Baggage Protection",
                        "coverage_limit": "$2,500",
                        "deductible": "$25",
                        "details": ["Electronics coverage", "Sports equipment", "Business equipment"]
                    },
                    {
                        "category": "Travel Delay",
                        "coverage_limit": "$2,000",
                        "deductible": "$0",
                        "details": ["Meal and accommodation expenses", "6+ hour delay coverage"]
                    }
                ],
                "exclusions": ["Intentional self-harm", "War and terrorism (varies)", "Some adventure activities"],
                "benefits": ["Cancel for any reason option", "Pre-existing condition waiver", "Rental car damage", "Identity theft coverage"]
            },
            {
                "provider": "World Nomads",
                "product_name": "Explorer Plan",
                "coverage_type": "adventure",
                "base_price": 95,
                "price_per_day": 5.1,
                "coverages": [
                    {
                        "category": "Adventure Activities",
                        "coverage_limit": "$10,000,000",
                        "deductible": "$0",
                        "details": ["Over 150 activities covered", "Equipment coverage", "Search and rescue"]
                    },
                    {
                        "category": "Emergency Medical",
                        "coverage_limit": "$10,000,000",
                        "deductible": "$0",
                        "details": ["Unlimited medical coverage", "Adventure activity injuries", "Emergency evacuation"]
                    },
                    {
                        "category": "Personal Liability",
                        "coverage_limit": "$4,000,000",
                        "deductible": "$0",
                        "details": ["Third party injury/damage", "Legal expenses"]
                    }
                ],
                "exclusions": ["Professional sports", "Some extreme activities", "Under influence of alcohol/drugs"],
                "benefits": ["Adventure activity coverage", "Extend/claim while traveling", "24/7 emergency assistance"]
            },
            {
                "provider": "IMG Global",
                "product_name": "iTravelInsured Travel LX",
                "coverage_type": "premium",
                "base_price": 125,
                "price_per_day": 6.8,
                "coverages": [
                    {
                        "category": "Trip Cancellation",
                        "coverage_limit": "$150,000",
                        "deductible": "$0",
                        "details": ["Primary coverage", "Work-related reasons", "Pre-existing condition waiver"]
                    },
                    {
                        "category": "Emergency Medical",
                        "coverage_limit": "$5,000,000",
                        "deductible": "$0",
                        "details": ["Primary medical coverage", "Mental health coverage", "Prescription drugs"]
                    },
                    {
                        "category": "Baggage & Personal Effects",
                        "coverage_limit": "$5,000",
                        "deductible": "$0",
                        "details": ["High-value item coverage", "Electronics", "Business equipment", "Sporting goods"]
                    },
                    {
                        "category": "Rental Car",
                        "coverage_limit": "$35,000",
                        "deductible": "$0",
                        "details": ["Primary rental car coverage", "Loss of use", "Towing"]
                    }
                ],
                "exclusions": ["High-risk countries (specific list)", "Some pre-existing conditions", "Professional sports"],
                "benefits": ["Primary coverage (no deductible)", "Concierge services", "Pet return coverage", "Home security monitoring"]
            }
        ]
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Recommend insurance products based on travel plans
        
        Input:
        - trip_details: destination, duration, activities, trip_cost
        - traveler_profile: age, health, travel_experience, risk_tolerance
        - coverage_preferences: medical_priority, cancellation_priority, etc.
        """
        
        try:
            trip_details = input_data.get("trip_details", {})
            traveler_profile = input_data.get("traveler_profile", {})
            
            # Assess risk and recommend products
            risk_assessment = self._assess_travel_risk(trip_details, traveler_profile)
            recommended_products = self._recommend_products(trip_details, traveler_profile, risk_assessment)
            
            result = InsuranceRecommendation(
                recommended_products=recommended_products,
                traveler_profile=traveler_profile,
                risk_assessment=risk_assessment,
                recommendations=self._generate_recommendations(risk_assessment, trip_details),
                disclaimers=self._generate_disclaimers()
            )
            
            return self.format_output(result.model_dump())
            
        except Exception as e:
            self.log(f"InsuranceAgent error: {e}")
            return self._generate_fallback_insurance(input_data)
    
    def _assess_travel_risk(self, trip_details: Dict[str, Any], traveler_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Assess travel risk factors"""
        
        destination = trip_details.get("destination", "").upper()
        duration = trip_details.get("duration", 7)
        activities = trip_details.get("activities", [])
        trip_cost = trip_details.get("trip_cost", 0)
        
        age = traveler_profile.get("age", 30)
        health_conditions = traveler_profile.get("health_conditions", [])
        travel_frequency = traveler_profile.get("travel_frequency", "occasional")
        
        # Risk scoring (0-10 scale)
        risk_factors = {
            "destination_risk": self._assess_destination_risk(destination),
            "activity_risk": self._assess_activity_risk(activities),
            "health_risk": self._assess_health_risk(age, health_conditions),
            "financial_risk": self._assess_financial_risk(trip_cost),
            "duration_risk": self._assess_duration_risk(duration)
        }
        
        overall_risk = sum(risk_factors.values()) / len(risk_factors)
        
        risk_level = "low"
        if overall_risk >= 7:
            risk_level = "high"
        elif overall_risk >= 5:
            risk_level = "medium"
        
        return {
            "overall_risk_score": overall_risk,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "key_concerns": self._identify_key_concerns(risk_factors, trip_details)
        }
    
    def _assess_destination_risk(self, destination: str) -> float:
        """Assess destination-specific risks"""
        high_risk_countries = ["AF", "IQ", "SY", "YE", "SO", "LY"]
        medium_risk_countries = ["IN", "BR", "ZA", "EG", "PH", "ID"]
        
        if destination in high_risk_countries:
            return 8.5
        elif destination in medium_risk_countries:
            return 6.0
        else:
            return 3.0
    
    def _assess_activity_risk(self, activities: List[str]) -> float:
        """Assess risk based on planned activities"""
        high_risk_activities = ["mountaineering", "skiing", "scuba diving", "bungee jumping", "skydiving"]
        medium_risk_activities = ["hiking", "cycling", "water sports", "rock climbing"]
        
        activity_str = " ".join(activities).lower()
        
        for activity in high_risk_activities:
            if activity in activity_str:
                return 8.0
        
        for activity in medium_risk_activities:
            if activity in activity_str:
                return 6.0
        
        return 2.0
    
    def _assess_health_risk(self, age: int, health_conditions: List[str]) -> float:
        """Assess health-related risks"""
        base_risk = 2.0
        
        # Age factor
        if age > 70:
            base_risk += 3.0
        elif age > 60:
            base_risk += 1.5
        elif age < 25:
            base_risk += 0.5
        
        # Health conditions
        high_risk_conditions = ["heart disease", "diabetes", "cancer", "respiratory conditions"]
        for condition in health_conditions:
            if any(hrc in condition.lower() for hrc in high_risk_conditions):
                base_risk += 2.0
        
        return min(base_risk, 9.0)
    
    def _assess_financial_risk(self, trip_cost: float) -> float:
        """Assess financial risk based on trip cost"""
        if trip_cost > 10000:
            return 7.0
        elif trip_cost > 5000:
            return 5.0
        elif trip_cost > 2000:
            return 3.0
        else:
            return 1.0
    
    def _assess_duration_risk(self, duration: int) -> float:
        """Assess risk based on trip duration"""
        if duration > 30:
            return 6.0
        elif duration > 14:
            return 4.0
        elif duration > 7:
            return 2.0
        else:
            return 1.0
    
    def _identify_key_concerns(self, risk_factors: Dict[str, float], trip_details: Dict[str, Any]) -> List[str]:
        """Identify key risk concerns"""
        concerns = []
        
        if risk_factors["destination_risk"] > 6:
            concerns.append("High-risk destination with potential political/health risks")
        
        if risk_factors["activity_risk"] > 6:
            concerns.append("Adventure activities require specialized coverage")
        
        if risk_factors["health_risk"] > 5:
            concerns.append("Age or health conditions increase medical risk")
        
        if risk_factors["financial_risk"] > 5:
            concerns.append("High trip cost increases financial exposure")
        
        if risk_factors["duration_risk"] > 4:
            concerns.append("Extended travel duration increases various risks")
        
        return concerns
    
    def _recommend_products(self, trip_details: Dict[str, Any], traveler_profile: Dict[str, Any], risk_assessment: Dict[str, Any]) -> List[InsuranceProduct]:
        """Recommend insurance products based on risk assessment"""
        
        duration = trip_details.get("duration", 7)
        activities = trip_details.get("activities", [])
        risk_level = risk_assessment["risk_level"]
        
        recommended = []
        
        # Always include basic option
        basic_product = self._build_insurance_product(self.insurance_products[0], duration)
        
        # Recommend based on risk level
        if risk_level == "high" or risk_assessment["risk_factors"]["financial_risk"] > 5:
            # Premium coverage
            premium_product = self._build_insurance_product(self.insurance_products[3], duration)
            recommended.append(premium_product)
            
            # Comprehensive as alternative
            comprehensive_product = self._build_insurance_product(self.insurance_products[1], duration)
            recommended.append(comprehensive_product)
            
            # Basic as budget option
            recommended.append(basic_product)
        
        elif any("adventure" in act.lower() or "sport" in act.lower() for act in activities):
            # Adventure coverage
            adventure_product = self._build_insurance_product(self.insurance_products[2], duration)
            recommended.append(adventure_product)
            
            # Comprehensive as alternative
            comprehensive_product = self._build_insurance_product(self.insurance_products[1], duration)
            recommended.append(comprehensive_product)
            
        else:
            # Standard recommendations
            comprehensive_product = self._build_insurance_product(self.insurance_products[1], duration)
            recommended.append(comprehensive_product)
            
            recommended.append(basic_product)
        
        return recommended[:3]  # Return top 3 recommendations
    
    def _build_insurance_product(self, product_data: Dict[str, Any], duration: int) -> InsuranceProduct:
        """Build insurance product with calculated pricing"""
        
        base_price = product_data["base_price"]
        daily_price = product_data["price_per_day"]
        total_price = base_price + (daily_price * duration)
        
        # Build coverages
        coverages = []
        for coverage_data in product_data["coverages"]:
            coverage = InsuranceCoverage(
                category=coverage_data["category"],
                coverage_limit=coverage_data["coverage_limit"],
                deductible=coverage_data["deductible"],
                details=coverage_data["details"]
            )
            coverages.append(coverage)
        
        product = InsuranceProduct(
            provider=product_data["provider"],
            product_name=product_data["product_name"],
            coverage_type=product_data["coverage_type"],
            price={
                "total": f"${total_price:.2f}",
                "base": f"${base_price}",
                "daily": f"${daily_price}",
                "duration_days": duration,
                "currency": "USD"
            },
            coverages=coverages,
            exclusions=product_data["exclusions"],
            benefits=product_data["benefits"],
            purchase_url=f"https://{product_data['provider'].lower().replace(' ', '')}.com/purchase",
            terms_url=f"https://{product_data['provider'].lower().replace(' ', '')}.com/terms"
        )
        
        return product
    
    def _generate_recommendations(self, risk_assessment: Dict[str, Any], trip_details: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        risk_level = risk_assessment["risk_level"]
        key_concerns = risk_assessment["key_concerns"]
        
        if risk_level == "high":
            recommendations.append("🔴 Consider comprehensive or premium coverage due to elevated risk factors")
        elif risk_level == "medium":
            recommendations.append("🟡 Comprehensive coverage recommended for balanced protection")
        else:
            recommendations.append("🟢 Basic coverage may be sufficient, but consider comprehensive for peace of mind")
        
        if "Adventure activities" in str(key_concerns):
            recommendations.append("⚠️ Ensure your policy covers specific adventure activities you plan to do")
        
        if "High trip cost" in str(key_concerns):
            recommendations.append("💰 Consider higher trip cancellation limits due to significant financial investment")
        
        if "Health conditions" in str(key_concerns):
            recommendations.append("🏥 Look for policies with pre-existing condition waivers if applicable")
        
        recommendations.extend([
            "📋 Purchase insurance within 14-21 days of initial trip deposit for maximum benefits",
            "📱 Choose providers with 24/7 assistance and mobile claim apps",
            "📄 Read policy terms carefully, especially exclusions and claim procedures"
        ])
        
        return recommendations
    
    def _generate_disclaimers(self) -> List[str]:
        """Generate insurance disclaimers"""
        return [
            "⚠️ Insurance recommendations are based on general risk assessment only",
            "Coverage details, terms, and pricing may vary by provider and individual circumstances",
            "Read all policy documents carefully before purchasing",
            "Pre-existing medical conditions may affect coverage - consult with providers",
            "Some activities or destinations may be excluded from standard policies",
            "Claims are subject to policy terms, conditions, and provider approval",
            "This service may receive commissions from insurance partners"
        ]
    
    def _generate_fallback_insurance(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic insurance recommendation as fallback"""
        
        basic_product = InsuranceProduct(
            provider="Travel Insurance Provider",
            product_name="Basic Travel Protection",
            coverage_type="basic",
            price={"total": "$75.00", "currency": "USD"},
            coverages=[
                InsuranceCoverage(
                    category="Essential Coverage",
                    coverage_limit="Varies",
                    deductible="Varies",
                    details=["Trip cancellation", "Emergency medical", "Baggage protection"]
                )
            ],
            exclusions=["Standard exclusions apply"],
            benefits=["Basic travel protection"],
            purchase_url=None,
            terms_url=None
        )
        
        result = InsuranceRecommendation(
            recommended_products=[basic_product],
            traveler_profile={},
            risk_assessment={"risk_level": "unknown", "overall_risk_score": 5.0},
            recommendations=["Consider travel insurance for your trip", "Compare multiple providers"],
            disclaimers=["Insurance recommendations unavailable - consult travel insurance providers directly"]
        )
        
        return self.format_output(result.model_dump())