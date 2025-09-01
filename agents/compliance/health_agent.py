import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class Vaccination(BaseModel):
    name: str = Field(..., description="Vaccine name")
    required: bool = Field(..., description="Whether vaccine is required or recommended")
    timing: str = Field(..., description="When to get vaccinated")
    notes: str = Field(..., description="Additional notes")

class HealthRisk(BaseModel):
    disease: str = Field(..., description="Disease name")
    risk_level: str = Field(..., description="low/medium/high/very_high")
    prevention: List[str] = Field(..., description="Prevention measures")
    symptoms: List[str] = Field(..., description="Symptoms to watch for")

class MedicalPreparation(BaseModel):
    category: str = Field(..., description="Category of preparation")
    items: List[str] = Field(..., description="Recommended items/actions")
    priority: str = Field(..., description="essential/recommended/optional")

class HealthAdvisory(BaseModel):
    destination: str = Field(..., description="Destination country/region")
    vaccinations: List[Vaccination] = Field(..., description="Vaccination requirements")
    health_risks: List[HealthRisk] = Field(..., description="Health risks in destination")
    medical_preparations: List[MedicalPreparation] = Field(..., description="Medical preparations needed")
    healthcare_info: Dict[str, Any] = Field(..., description="Healthcare system information")
    emergency_contacts: Dict[str, str] = Field(..., description="Emergency contact information")
    advisories: List[str] = Field(..., description="General health advisories")

class HealthAdvisoryResult(BaseModel):
    health_advisory: HealthAdvisory
    disclaimers: List[str]
    last_updated: str
    sources: List[str]

class HealthAdvisoryAgent(BaseAgent):
    def __init__(self):
        super().__init__("HealthAdvisoryAgent")
        # Health advisory database (in production, integrate with CDC/WHO APIs)
        self.health_database = self._load_health_database()
    
    def _load_health_database(self) -> Dict[str, Dict[str, Any]]:
        """Load health advisory database"""
        return {
            "TH": {  # Thailand
                "country_name": "Thailand",
                "vaccinations": [
                    {"name": "Hepatitis A", "required": False, "timing": "2 weeks before travel", "notes": "Recommended for all travelers"},
                    {"name": "Hepatitis B", "required": False, "timing": "At least 1 month before travel", "notes": "Recommended for travelers with risk factors"},
                    {"name": "Japanese Encephalitis", "required": False, "timing": "1 month before travel", "notes": "For rural areas and long stays"},
                    {"name": "Typhoid", "required": False, "timing": "1-2 weeks before travel", "notes": "Recommended for most travelers"},
                    {"name": "Yellow Fever", "required": True, "timing": "10 days before travel", "notes": "Required if arriving from yellow fever area"}
                ],
                "health_risks": [
                    {"disease": "Dengue", "risk_level": "medium", "prevention": ["Mosquito repellent", "Long sleeves", "Air conditioning"], "symptoms": ["Fever", "Headache", "Joint pain"]},
                    {"disease": "Malaria", "risk_level": "low", "prevention": ["Antimalarial medication", "Mosquito nets", "Repellent"], "symptoms": ["Fever", "Chills", "Fatigue"]},
                    {"disease": "Zika", "risk_level": "low", "prevention": ["Mosquito protection", "Safe practices"], "symptoms": ["Mild fever", "Rash", "Joint pain"]}
                ]
            },
            "IN": {  # India
                "country_name": "India",
                "vaccinations": [
                    {"name": "Hepatitis A", "required": False, "timing": "2 weeks before travel", "notes": "Recommended for all travelers"},
                    {"name": "Hepatitis B", "required": False, "timing": "1 month before travel", "notes": "Recommended for most travelers"},
                    {"name": "Typhoid", "required": False, "timing": "1-2 weeks before travel", "notes": "Recommended for most travelers"},
                    {"name": "Japanese Encephalitis", "required": False, "timing": "1 month before travel", "notes": "For certain regions and seasons"},
                    {"name": "Polio", "required": True, "timing": "4 weeks to 12 months before travel", "notes": "Required for travel to/from India"}
                ],
                "health_risks": [
                    {"disease": "Malaria", "risk_level": "medium", "prevention": ["Antimalarial medication", "Mosquito nets"], "symptoms": ["Fever", "Chills", "Sweats"]},
                    {"disease": "Dengue", "risk_level": "medium", "prevention": ["Mosquito protection", "Day and night precautions"], "symptoms": ["High fever", "Severe headache", "Pain behind eyes"]},
                    {"disease": "Traveler's Diarrhea", "risk_level": "high", "prevention": ["Safe food/water", "Hand hygiene"], "symptoms": ["Diarrhea", "Nausea", "Cramps"]}
                ]
            },
            "BR": {  # Brazil
                "country_name": "Brazil",
                "vaccinations": [
                    {"name": "Yellow Fever", "required": True, "timing": "10 days before travel", "notes": "Required for certain regions"},
                    {"name": "Hepatitis A", "required": False, "timing": "2 weeks before travel", "notes": "Recommended for all travelers"},
                    {"name": "Hepatitis B", "required": False, "timing": "1 month before travel", "notes": "Recommended for most travelers"},
                    {"name": "Typhoid", "required": False, "timing": "1-2 weeks before travel", "notes": "For areas with poor sanitation"}
                ],
                "health_risks": [
                    {"disease": "Zika", "risk_level": "medium", "prevention": ["Mosquito protection", "Safe practices"], "symptoms": ["Mild fever", "Rash", "Conjunctivitis"]},
                    {"disease": "Dengue", "risk_level": "high", "prevention": ["Mosquito repellent", "Protective clothing"], "symptoms": ["High fever", "Headache", "Muscle pain"]},
                    {"disease": "Malaria", "risk_level": "medium", "prevention": ["Antimalarial medication", "Mosquito nets"], "symptoms": ["Fever", "Chills", "Flu-like symptoms"]}
                ]
            },
            "JP": {  # Japan
                "country_name": "Japan",
                "vaccinations": [
                    {"name": "Routine Vaccines", "required": False, "timing": "Up to date", "notes": "MMR, DPT, flu, COVID-19"},
                    {"name": "Hepatitis A", "required": False, "timing": "2 weeks before travel", "notes": "Recommended for unvaccinated travelers"},
                    {"name": "Hepatitis B", "required": False, "timing": "1 month before travel", "notes": "For travelers with risk factors"},
                    {"name": "Japanese Encephalitis", "required": False, "timing": "1 month before travel", "notes": "For rural areas during transmission season"}
                ],
                "health_risks": [
                    {"disease": "Seasonal Flu", "risk_level": "low", "prevention": ["Vaccination", "Hand hygiene"], "symptoms": ["Fever", "Cough", "Body aches"]},
                    {"disease": "Foodborne Illness", "risk_level": "very_low", "prevention": ["Safe food practices"], "symptoms": ["Nausea", "Vomiting", "Diarrhea"]}
                ]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Provide health advisory for destination
        
        Input:
        - destination_country: ISO country code
        - traveler_profile: Age, gender, medical conditions, current vaccinations
        - travel_dates: For seasonal considerations
        - travel_activities: Rural vs urban, adventure activities
        """
        required_fields = ["destination_country"]
        self.validate_input(input_data, required_fields)
        
        destination = input_data["destination_country"].upper()
        traveler_profile = input_data.get("traveler_profile", {})
        
        try:
            if destination in self.health_database:
                result = self._create_detailed_advisory(destination, input_data)
            else:
                result = self._create_general_advisory(destination, input_data)
            
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"HealthAdvisoryAgent error: {e}")
            return self._generate_fallback_advisory(destination, input_data)
    
    def _create_detailed_advisory(self, destination: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed health advisory from database"""
        
        country_data = self.health_database[destination]
        country_name = country_data["country_name"]
        
        # Process vaccinations
        vaccinations = []
        for vacc_data in country_data.get("vaccinations", []):
            vaccination = Vaccination(
                name=vacc_data["name"],
                required=vacc_data["required"],
                timing=vacc_data["timing"],
                notes=vacc_data["notes"]
            )
            vaccinations.append(vaccination)
        
        # Process health risks
        health_risks = []
        for risk_data in country_data.get("health_risks", []):
            risk = HealthRisk(
                disease=risk_data["disease"],
                risk_level=risk_data["risk_level"],
                prevention=risk_data["prevention"],
                symptoms=risk_data["symptoms"]
            )
            health_risks.append(risk)
        
        # Generate medical preparations
        medical_preparations = [
            MedicalPreparation(
                category="Travel Medicine Kit",
                items=[
                    "Personal prescription medications",
                    "Pain relievers (acetaminophen, ibuprofen)",
                    "Antidiarrheal medication",
                    "Antiseptic wipes",
                    "Bandages and gauze",
                    "Thermometer",
                    "Hand sanitizer",
                    "Insect repellent (DEET-based)",
                    "Sunscreen (SPF 30+)"
                ],
                priority="essential"
            ),
            MedicalPreparation(
                category="Insurance and Documentation",
                items=[
                    "Travel health insurance with medical evacuation",
                    "Copies of prescriptions",
                    "Emergency contact information",
                    "Blood type and allergy information",
                    "Vaccination records"
                ],
                priority="essential"
            ),
            MedicalPreparation(
                category="Preventive Measures",
                items=[
                    "Mosquito nets (for high-risk areas)",
                    "Water purification tablets",
                    "Oral rehydration salts",
                    "Antimalarial medication (if recommended)",
                    "Probiotics for digestive health"
                ],
                priority="recommended"
            )
        ]
        
        # Healthcare information
        healthcare_info = {
            "healthcare_quality": self._get_healthcare_quality(destination),
            "emergency_services": "Available in major cities",
            "recommended_facilities": "International hospitals in capital and major cities",
            "payment_method": "Payment often required upfront - insurance important"
        }
        
        # Emergency contacts
        emergency_contacts = {
            "emergency_services": self._get_emergency_number(destination),
            "us_embassy": "Contact local US embassy for assistance",
            "travel_assistance": "Contact travel insurance provider"
        }
        
        # General advisories
        advisories = [
            f"Check CDC travel health notices for {country_name} before departure",
            "Consult a travel medicine specialist 4-6 weeks before travel",
            "Ensure routine vaccinations are up to date",
            "Consider travel health insurance with medical evacuation coverage",
            "Register with your embassy if staying long-term"
        ]
        
        health_advisory = HealthAdvisory(
            destination=country_name,
            vaccinations=vaccinations,
            health_risks=health_risks,
            medical_preparations=medical_preparations,
            healthcare_info=healthcare_info,
            emergency_contacts=emergency_contacts,
            advisories=advisories
        )
        
        result = HealthAdvisoryResult(
            health_advisory=health_advisory,
            disclaimers=[
                "⚠️ This health information is for general guidance only",
                "Consult a healthcare professional for personalized medical advice",
                "Health risks and requirements can change rapidly",
                "This information may not reflect current outbreaks or alerts",
                "Individual health conditions may require special precautions"
            ],
            last_updated=datetime.now().strftime("%Y-%m-%d"),
            sources=["CDC", "WHO", "Travel medicine guidelines"]
        )
        
        return result.model_dump()
    
    def _create_general_advisory(self, destination: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create general health advisory for unknown destinations"""
        
        # General vaccinations for international travel
        general_vaccinations = [
            Vaccination(
                name="Routine Vaccines",
                required=True,
                timing="Up to date",
                notes="MMR, DPT, flu, COVID-19 as recommended"
            ),
            Vaccination(
                name="Hepatitis A",
                required=False,
                timing="2 weeks before travel",
                notes="Recommended for most international destinations"
            ),
            Vaccination(
                name="Hepatitis B",
                required=False,
                timing="1 month before travel",
                notes="Consider for travelers with risk factors"
            )
        ]
        
        # General health risks
        general_risks = [
            HealthRisk(
                disease="Traveler's Diarrhea",
                risk_level="medium",
                prevention=["Safe food and water practices", "Hand hygiene"],
                symptoms=["Diarrhea", "Nausea", "Abdominal cramps"]
            ),
            HealthRisk(
                disease="Respiratory Infections",
                risk_level="low",
                prevention=["Hand washing", "Avoid crowded areas if sick"],
                symptoms=["Cough", "Fever", "Shortness of breath"]
            )
        ]
        
        health_advisory = HealthAdvisory(
            destination=f"Country Code: {destination}",
            vaccinations=general_vaccinations,
            health_risks=general_risks,
            medical_preparations=[
                MedicalPreparation(
                    category="Basic Travel Kit",
                    items=["First aid supplies", "Personal medications", "Hand sanitizer"],
                    priority="essential"
                )
            ],
            healthcare_info={
                "note": "Healthcare information not available for this destination",
                "recommendation": "Research local healthcare facilities before travel"
            },
            emergency_contacts={
                "local_emergency": "Research local emergency numbers",
                "embassy": "Contact your embassy for assistance"
            },
            advisories=[
                "Consult a travel medicine specialist before departure",
                "Research destination-specific health risks",
                "Ensure comprehensive travel health insurance"
            ]
        )
        
        result = HealthAdvisoryResult(
            health_advisory=health_advisory,
            disclaimers=[
                "Limited health information available for this destination",
                "Consult travel medicine specialist for detailed advice",
                "Check government travel advisories for current health risks"
            ],
            last_updated=datetime.now().strftime("%Y-%m-%d"),
            sources=["General travel health guidelines"]
        )
        
        return result.model_dump()
    
    def _get_healthcare_quality(self, country_code: str) -> str:
        """Get healthcare quality assessment"""
        high_quality = ["JP", "US", "CA", "GB", "DE", "AU", "NZ", "CH", "SE"]
        medium_quality = ["TH", "MY", "SG", "KR", "TW", "CL", "AR"]
        
        if country_code in high_quality:
            return "High quality healthcare available"
        elif country_code in medium_quality:
            return "Good healthcare in major cities, variable in rural areas"
        else:
            return "Healthcare quality varies - research local facilities"
    
    def _get_emergency_number(self, country_code: str) -> str:
        """Get emergency service number"""
        emergency_numbers = {
            "TH": "191 (Police), 1669 (Medical)",
            "IN": "112 (General Emergency)",
            "BR": "190 (Police), 192 (Medical)",
            "JP": "110 (Police), 119 (Fire/Medical)",
            "US": "911",
            "GB": "999"
        }
        return emergency_numbers.get(country_code, "Research local emergency numbers")
    
    def _generate_fallback_advisory(self, destination: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate minimal fallback advisory"""
        
        fallback_advisory = HealthAdvisory(
            destination=f"Destination: {destination}",
            vaccinations=[
                Vaccination(
                    name="Consult Travel Medicine Specialist",
                    required=True,
                    timing="4-6 weeks before travel",
                    notes="Get personalized vaccination recommendations"
                )
            ],
            health_risks=[],
            medical_preparations=[
                MedicalPreparation(
                    category="Essential Preparations",
                    items=["Travel health consultation", "Travel insurance", "Basic first aid kit"],
                    priority="essential"
                )
            ],
            healthcare_info={"note": "Health advisory service temporarily unavailable"},
            emergency_contacts={"note": "Contact local emergency services and your embassy"},
            advisories=["Seek professional travel health advice before departure"]
        )
        
        result = HealthAdvisoryResult(
            health_advisory=fallback_advisory,
            disclaimers=["Health advisory service not available - seek professional advice"],
            last_updated=datetime.now().strftime("%Y-%m-%d"),
            sources=["Fallback advisory"]
        )
        
        return self.format_output(result.model_dump())