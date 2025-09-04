from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from config.database import get_db
from models.database_models import UserProfile
import hashlib
import os
import structlog
import io
from contextlib import redirect_stdout

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
except ImportError:
    vertexai = None
    GenerativeModel = None

logger = structlog.get_logger()

class UserProfileAgent(BaseAgent):
    def __init__(self):
        super().__init__("UserProfileAgent")
        self.csv_data = self._load_customer_dataset()
        self.ai_model = self._initialize_ai_model()
    
    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        self.validate_input(input_data, ["customer_id"])
        
        customer_id = input_data["customer_id"]
        db = next(get_db())
        
        try:
            # First check CSV data for customer information
            csv_customer = self._get_customer_from_csv(customer_id)
            
            # Retrieve user profile from MySQL
            profile = self._get_user_profile(db, customer_id)
            
            if not profile and csv_customer:
                # Create profile from CSV data if exists
                profile = self._create_profile_from_csv(db, csv_customer)
            elif not profile:
                # Create basic profile if not exists
                profile = self._create_basic_profile(db, customer_id, input_data)
            
            # Format profile data for other agents
            profile_data = self._format_profile_data(profile, csv_customer)
            
            return self.format_output(profile_data, {
                "profile_exists": profile is not None,
                "loyalty_tier": profile.loyalty_tier if profile else None
            })
            
        finally:
            db.close()
    
    def _get_user_profile(self, db: Session, customer_id: str) -> Optional[UserProfile]:
        """Retrieve user profile from MySQL database"""
        return db.query(UserProfile).filter(
            UserProfile.customer_id == customer_id
        ).first()
    
    def _create_basic_profile(self, db: Session, customer_id: str, input_data: Dict[str, Any]) -> UserProfile:
        """Create a basic user profile if one doesn't exist"""
        # Validate and truncate string fields to prevent database errors
        nationality = input_data.get("nationality")
        if nationality:
            nationality = str(nationality)[:100]
            
        profile = UserProfile(
            customer_id=str(customer_id)[:255],
            nationality=nationality,
            loyalty_tier="STANDARD",
            preferences={
                "created_from": "agent_interaction",
                "initial_request": input_data.get("initial_request", "")
            },
            travel_history=[]
        )
        
        # Hash passport number if provided for security
        if input_data.get("passport_number"):
            profile.passport_number_hash = self._hash_passport(input_data["passport_number"])
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        return profile
    
    def _create_profile_from_csv(self, db: Session, csv_customer: Dict[str, Any]) -> UserProfile:
        """Create user profile from CSV customer data"""
        customer_id = str(csv_customer["traveler_id"])[:255]
        
        # Check if profile already exists
        existing_profile = self._get_user_profile(db, customer_id)
        if existing_profile:
            logger.info(f"✅ Found existing profile for customer {customer_id}")
            return existing_profile
        
        # Validate and truncate string fields to prevent database errors
        nationality = str(csv_customer.get("nationality", ""))[:100] if csv_customer.get("nationality") else None
        loyalty_tier = str(self._determine_loyalty_tier(csv_customer["booking_history"]))[:50]
        
        profile = UserProfile(
            customer_id=customer_id,
            nationality=nationality,
            loyalty_tier=loyalty_tier,
            preferences={
                "name": csv_customer["name"],
                "age": csv_customer["age"],
                "data_source": "csv_dataset",
                "preferred_cabin_class": self._get_preferred_cabin_class(csv_customer["booking_history"])
            },
            travel_history=csv_customer["booking_history"][:10]  # Keep last 10 bookings
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        logger.info(f"✅ Created profile for customer {customer_id} from CSV data")
        return profile
    
    def _determine_loyalty_tier(self, booking_history: list) -> str:
        """Determine loyalty tier based on booking history"""
        booking_count = len(booking_history)
        business_first_count = sum(1 for booking in booking_history 
                                 if booking.get("cabin_class") in ["Business", "First"])
        
        if booking_count >= 10 or business_first_count >= 5:
            return "GOLD"
        elif booking_count >= 5 or business_first_count >= 2:
            return "SILVER"
        else:
            return "STANDARD"
    
    def _get_preferred_cabin_class(self, booking_history: list) -> str:
        """Determine preferred cabin class from booking history"""
        if not booking_history:
            return "Economy"
        
        cabin_counts = {}
        for booking in booking_history:
            cabin = booking.get("cabin_class", "Economy")
            cabin_counts[cabin] = cabin_counts.get(cabin, 0) + 1
        
        return max(cabin_counts, key=cabin_counts.get)
    
    def _format_profile_data(self, profile: UserProfile, csv_customer: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format profile data for consumption by other agents"""
        data = {
            "customer_id": profile.customer_id,
            "nationality": profile.nationality,
            "loyalty_tier": profile.loyalty_tier,
            "preferences": profile.preferences or {},
            "travel_history": profile.travel_history or [],
            "has_passport": profile.passport_number_hash is not None,
            "profile_completeness": self._calculate_completeness(profile)
        }
        
        # Add additional CSV data if available
        if csv_customer:
            data.update({
                "name": csv_customer.get("name"),
                "age": csv_customer.get("age"),
                "data_source": "csv_enhanced",
                "total_bookings": len(csv_customer.get("booking_history", [])),
                "preferred_destinations": self._get_preferred_destinations(csv_customer.get("booking_history", []))
            })
        
        return data
    
    def _calculate_completeness(self, profile: UserProfile) -> float:
        """Calculate profile completeness score"""
        fields = [
            profile.nationality,
            profile.passport_number_hash,
            profile.preferences,
            profile.travel_history
        ]
        
        completed_fields = sum(1 for field in fields if field)
        return completed_fields / len(fields)
    
    def _hash_passport(self, passport_number: str) -> str:
        """Hash passport number for security"""
        return hashlib.sha256(passport_number.encode()).hexdigest()
    
    async def update_travel_history(self, customer_id: str, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's travel history after a booking"""
        db = next(get_db())
        
        try:
            profile = self._get_user_profile(db, customer_id)
            if profile:
                if not profile.travel_history:
                    profile.travel_history = []
                
                profile.travel_history.append(booking_data)
                
                # Keep only last 10 bookings
                if len(profile.travel_history) > 10:
                    profile.travel_history = profile.travel_history[-10:]
                
                db.commit()
                
                return {"status": "updated", "history_count": len(profile.travel_history)}
            
            return {"status": "profile_not_found"}
            
        finally:
            db.close()
    
    async def update_preferences(self, customer_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update user preferences"""
        db = next(get_db())
        
        try:
            profile = self._get_user_profile(db, customer_id)
            if profile:
                if not profile.preferences:
                    profile.preferences = {}
                
                profile.preferences.update(preferences)
                db.commit()
                
                return {"status": "updated", "preferences": profile.preferences}
            
            return {"status": "profile_not_found"}
            
        finally:
            db.close()
    
    def _load_customer_dataset(self):
        """Load customer travel dataset from CSV"""
        if not PANDAS_AVAILABLE:
            logger.info("📊 Pandas not available - skipping CSV dataset loading")
            return None
            
        try:
            csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'customer_travel_dataset.csv')
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                logger.info(f"✅ User Profile Agent: Loaded {len(df)} customer records from CSV")
                return df
            else:
                logger.warning(f"⚠️ Customer dataset CSV not found at: {csv_path}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to load customer dataset: {e}")
            return None
    
    def _get_customer_from_csv(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer data from CSV by Traveler_Id or email_id"""
        if self.csv_data is None:
            return None
        
        try:
            # First try to find by email_id if it's an email format
            if "@" in customer_id and "email_id" in self.csv_data.columns:
                customer_row = self.csv_data[self.csv_data['email_id'] == customer_id]
                if not customer_row.empty:
                    return self._extract_customer_data(customer_row.iloc[0])
            
            # Try to convert customer_id to int for Traveler_Id matching
            try:
                traveler_id = int(customer_id)
                customer_row = self.csv_data[self.csv_data['Traveler_Id'] == traveler_id]
            except ValueError:
                # If can't convert to int, skip Traveler_Id matching
                return None
            
            if not customer_row.empty:
                return self._extract_customer_data(customer_row.iloc[0])
        except (ValueError, KeyError) as e:
            logger.warning(f"Error retrieving customer from CSV: {e}")
        
        return None
    
    def _extract_customer_data(self, row) -> Dict[str, Any]:
        """Extract customer data from CSV row"""
        traveler_id = int(row['Traveler_Id'])
        return {
            "traveler_id": str(traveler_id),
            "name": row['Traveler_name'],
            "age": int(row['Traveler_age']),
            "nationality": row['Nationality'],
            "booking_history": self._get_booking_history(traveler_id)
        }
    
    def _get_booking_history(self, traveler_id: int) -> list:
        """Get all bookings for a specific traveler"""
        if self.csv_data is None:
            return []
        
        bookings = self.csv_data[self.csv_data['Traveler_Id'] == traveler_id]
        history = []
        
        for _, booking in bookings.iterrows():
            history.append({
                "booking_id": str(booking['Booking_ID']),
                "departure": {
                    "code": booking['DepIATAcode'],
                    "location": booking['departureLocation'],
                    "date": booking['departure_date']
                },
                "destination": {
                    "code": booking['DestIATAcode'], 
                    "location": booking['destinationLocation']
                },
                "cabin_class": booking['cabinClass'],
                "booking_date": booking['booking_date']
            })
        
        return history
    
    def _get_preferred_destinations(self, booking_history: list) -> list:
        """Get most frequent destinations from booking history"""
        if not booking_history:
            return []
        
        dest_counts = {}
        for booking in booking_history:
            dest = booking.get("destination", {}).get("location", "Unknown")
            dest_counts[dest] = dest_counts.get(dest, 0) + 1
        
        # Return top 3 destinations
        sorted_dests = sorted(dest_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"destination": dest, "visits": count} for dest, count in sorted_dests[:3]]
    
    def _initialize_ai_model(self):
        """Initialize Vertex AI model for preference analysis if available"""
        if self.csv_data is None:
            logger.warning(f"⚠️ {self.name}: Skipping AI model initialization because CSV data is not loaded.")
            return None
        
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

            if project_id and vertexai:
                vertexai.init(project=project_id, location=location)
                model = GenerativeModel(model_name)
                logger.info(f"✅ {self.name}: Vertex AI initialized: {project_id} - {model_name}")
                return model
            else:
                logger.info(f"ℹ️ {self.name}: Using fallback mode (no AI)")
                return None
        except Exception as e:
            logger.error(f"❌ {self.name}: Failed to initialize Vertex AI: {e}")
            return None
    
    async def analyze_preferences(self, customer_id: str, query: str = None) -> Dict[str, Any]:
        """Analyze customer preferences using AI-powered analysis"""
        if self.ai_model is None or self.csv_data is None:
            return {
                "status": "unavailable",
                "message": "AI-powered preference analysis is currently unavailable",
                "fallback_analysis": self._get_basic_preferences(customer_id)
            }
        
        try:
            # Get customer data from CSV
            csv_customer = self._get_customer_from_csv(customer_id)
            
            if csv_customer:
                return await self._generate_personalized_analysis(csv_customer, query)
            else:
                return await self._generate_general_analysis(query or "Analyze travel preferences")
                
        except Exception as e:
            logger.error(f"❌ {self.name}: Error in preference analysis: {e}")
            return {
                "status": "error",
                "message": f"Analysis error: {e}",
                "fallback_analysis": self._get_basic_preferences(customer_id)
            }
    
    async def _generate_personalized_analysis(self, csv_customer: Dict[str, Any], query: str = None) -> Dict[str, Any]:
        """Generate AI-powered personalized preference analysis"""
        traveler_id = csv_customer["traveler_id"]
        
        # Get customer's travel history
        user_history_df = self.csv_data[self.csv_data['Traveler_Id'] == int(traveler_id)]
        user_history_md = user_history_df.to_markdown(index=False) if not user_history_df.empty else "No travel history found"
        
        # Create personalized prompt
        prompt = f"""You are a helpful travel assistant for HOT Travel analyzing customer preferences.

**Personalized Analysis for Customer ID: {traveler_id}**
Analyze this customer's travel history to understand their preferences and patterns.

**Customer's Travel History:**
```
{user_history_md}
```

**Analysis Request:**
"{query or 'Provide a comprehensive analysis of this customer travel preferences and recommend suitable future trips.'}"

Based on the customer's travel history, provide:
1. **Travel Patterns**: Frequency, preferred seasons, booking habits
2. **Destination Preferences**: Most visited locations, preferred regions
3. **Class & Budget**: Preferred cabin class, spending patterns
4. **Recommendations**: 2-3 personalized trip suggestions based on their history

Write your response in clear, friendly language that a customer would appreciate.
Use bullet points and structure your analysis clearly.
"""
        
        response = await self.ai_model.generate_content_async(prompt)
        
        return {
            "status": "success",
            "type": "personalized",
            "customer_id": traveler_id,
            "analysis": response.text,
            "travel_count": len(user_history_df),
            "data_source": "ai_powered"
        }
    
    async def _generate_general_analysis(self, query: str) -> Dict[str, Any]:
        """Generate AI-powered general travel trend analysis"""
        # Capture dataframe info for the prompt
        with io.StringIO() as buf, redirect_stdout(buf):
            self.csv_data.info()
            df_info = buf.getvalue()
        
        df_head = self.csv_data.head(10).to_markdown()
        
        prompt = f"""You are a travel data analyst for HOT Travel analyzing customer travel trends.

**General Dataset Analysis**
Analyze the entire customer travel dataset to answer the query and provide insights.

**Dataset Schema:**
```
{df_info}
```

**Sample Data (First 10 Rows):**
{df_head}

**Analysis Query:**
"{query}"

Based on the full dataset, provide insights about:
1. **Popular Destinations**: Most frequently visited locations
2. **Travel Patterns**: Seasonal trends, booking behaviors
3. **Customer Segments**: Different traveler types and preferences
4. **Recommendations**: General travel suggestions based on popular trends

Format your response clearly with bullet points and actionable insights.
"""
        
        response = await self.ai_model.generate_content_async(prompt)
        
        return {
            "status": "success",
            "type": "general",
            "analysis": response.text,
            "dataset_size": len(self.csv_data),
            "data_source": "ai_powered"
        }
    
    def _get_basic_preferences(self, customer_id: str) -> Dict[str, Any]:
        """Fallback basic preference analysis without AI"""
        csv_customer = self._get_customer_from_csv(customer_id)
        
        if csv_customer:
            booking_history = csv_customer["booking_history"]
            preferred_destinations = self._get_preferred_destinations(booking_history)
            preferred_cabin = self._get_preferred_cabin_class(booking_history)
            
            return {
                "customer_name": csv_customer["name"],
                "total_bookings": len(booking_history),
                "preferred_cabin_class": preferred_cabin,
                "top_destinations": preferred_destinations,
                "nationality": csv_customer["nationality"],
                "age": csv_customer["age"]
            }
        else:
            return {
                "message": "No travel history found for this customer",
                "customer_id": customer_id
            }
    
    async def get_travel_recommendations(self, customer_id: str, preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get AI-powered travel recommendations for a customer"""
        query = "Based on this customer's travel history, suggest 3 personalized trip recommendations with destinations, reasons, and estimated budgets."
        
        if preferences:
            query += f" Consider these additional preferences: {preferences}"
        
        return await self.analyze_preferences(customer_id, query)
