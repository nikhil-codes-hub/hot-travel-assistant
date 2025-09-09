from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain.schema import BaseMessage, HumanMessage
from sqlalchemy.orm import Session
import structlog
import asyncio
from datetime import datetime, timezone

# Import all agents
from agents.llm_extractor.extractor_agent import LLMExtractorAgent
from agents.user_profile.profile_agent import UserProfileAgent
from agents.destination_discovery.destination_agent import DestinationDiscoveryAgent
from agents.event_search.event_agent import EventSearchAgent
from agents.flights_search.flights_agent import FlightsSearchAgent
from agents.hotel_search.hotel_agent import HotelSearchAgent
from agents.offers.offers_agent import OffersAgent
from agents.flight_curator.flight_curator_agent import FlightCuratorAgent
from agents.itinerary.itinerary_agent import PrepareItineraryAgent
from agents.compliance.visa_agent import VisaRequirementAgent
from agents.compliance.health_agent import HealthAdvisoryAgent
from agents.insurance.insurance_agent import InsuranceAgent
from agents.seatmap.seatmap_agent import SeatMapAgent
from models.database_models import SearchSession

logger = structlog.get_logger()

class TravelState(TypedDict):
    # Core identifiers
    session_id: str
    user_request: str
    customer_id: str
    email_id: Optional[str]
    nationality: Optional[str]
    conversation_context: Optional[Dict[str, Any]]
    
    # Agent outputs
    extracted_requirements: Dict[str, Any]
    user_profile: Dict[str, Any]
    destination_suggestions: Dict[str, Any]
    event_details: Dict[str, Any]
    flight_offers: List[Dict[str, Any]]
    hotel_offers: List[Dict[str, Any]]
    enhanced_offers: Dict[str, Any]
    curated_flights: Dict[str, Any]
    itinerary: Dict[str, Any]
    
    # Post-confirmation compliance
    visa_requirements: Dict[str, Any]
    health_advisory: Dict[str, Any]
    insurance_recommendations: Dict[str, Any]
    seatmap_data: Dict[str, Any]
    
    # Flow control
    status: str
    confirmation_pending: bool
    needs_destination_discovery: bool
    needs_event_search: bool
    messages: List[BaseMessage]

class TravelOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.planning_graph = self._build_planning_graph()
        self.compliance_graph = self._build_compliance_graph()
        
    def _build_planning_graph(self) -> StateGraph:
        """Build the pre-confirmation planning workflow"""
        workflow = StateGraph(TravelState)
        
        # Phase 1: Requirements & Profile
        workflow.add_node("extract_requirements", self._extract_requirements)
        workflow.add_node("get_user_profile", self._get_user_profile)
        
        # Phase 2: Destination Discovery (conditional)
        workflow.add_node("discover_destinations", self._discover_destinations)
        
        # Phase 2.5: Event Search (conditional)
        workflow.add_node("search_events", self._search_events)
        
        # Phase 3: Search & Offers (parallel)
        workflow.add_node("search_flights_hotels", self._search_flights_hotels_parallel)
        workflow.add_node("enhance_offers", self._enhance_offers)
        
        # Phase 4: Flight Curation (NEW)
        workflow.add_node("curate_flights", self._curate_flights)
        
        # Phase 5: Itinerary Preparation
        workflow.add_node("prepare_itinerary", self._prepare_itinerary)
        
        # Define flow
        workflow.set_entry_point("extract_requirements")
        workflow.add_edge("extract_requirements", "get_user_profile")
        
        # Conditional destination discovery
        workflow.add_conditional_edges(
            "get_user_profile",
            self._needs_destination_discovery,
            {"discover": "discover_destinations", "search": "search_events"}
        )
        workflow.add_edge("discover_destinations", "search_events")
        
        # Conditional event search
        workflow.add_conditional_edges(
            "search_events",
            self._needs_event_search,
            {"search": "search_flights_hotels", "skip": "search_flights_hotels"}
        )
        
        workflow.add_edge("search_flights_hotels", "enhance_offers")
        workflow.add_edge("enhance_offers", "curate_flights")
        workflow.add_edge("curate_flights", "prepare_itinerary")
        workflow.add_edge("prepare_itinerary", END)
        
        return workflow.compile()
    
    def _build_compliance_graph(self) -> StateGraph:
        """Build the post-confirmation compliance workflow"""
        workflow = StateGraph(TravelState)
        
        # Compliance agents (run in parallel)
        workflow.add_node("visa_requirements", self._check_visa_requirements)
        workflow.add_node("health_advisory", self._get_health_advisory)
        workflow.add_node("insurance_recommendations", self._get_insurance_recommendations)
        workflow.add_node("seatmap_selection", self._get_seatmap_options)
        
        # Finalize
        workflow.add_node("finalize_travel_package", self._finalize_travel_package)
        
        # Run all compliance checks in parallel
        workflow.set_entry_point("visa_requirements")
        workflow.add_edge("visa_requirements", "finalize_travel_package")
        
        # Note: In a full implementation, you'd use parallel execution
        # For simplicity, we'll run sequentially but could be made parallel
        workflow.add_edge("health_advisory", "finalize_travel_package")
        workflow.add_edge("insurance_recommendations", "finalize_travel_package")
        workflow.add_edge("seatmap_selection", "finalize_travel_package")
        workflow.add_edge("finalize_travel_package", END)
        
        return workflow.compile()
    
    async def process_travel_request(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Process travel request through full Agentic AI flow"""
        try:
            # Create session record
            await self._create_session_record(input_data, session_id)
            
            # Initialize comprehensive state
            state: TravelState = {
                "session_id": session_id,
                "user_request": input_data["user_request"],
                "customer_id": input_data.get("customer_id", ""),
                "email_id": input_data.get("email_id"),
                "nationality": input_data.get("nationality"),
                "conversation_context": input_data.get("conversation_context"),
                
                # Agent outputs (will be populated)
                "extracted_requirements": {},
                "user_profile": {},
                "destination_suggestions": {},
                "event_details": {},
                "flight_offers": [],
                "hotel_offers": [],
                "enhanced_offers": {},
                "curated_flights": {},
                "itinerary": {},
                
                # Compliance (post-confirmation)
                "visa_requirements": {},
                "health_advisory": {},
                "insurance_recommendations": {},
                "seatmap_data": {},
                
                # Flow control
                "status": "processing",
                "confirmation_pending": True,
                "needs_destination_discovery": False,
                "needs_event_search": False,
                "messages": [HumanMessage(content=input_data["user_request"])]
            }
            
            # Run planning workflow
            result = await self.planning_graph.ainvoke(state)
            
            # Update session with results
            await self._update_session_record(session_id, result)
            
            return {
                "requirements": result.get('extracted_requirements', {}),
                "profile": result.get('user_profile', {}),
                "event_details": result.get('event_details', {}),  # Include events for frontend
                "flight_offers": result.get('flight_offers', []),
                "curated_flights": result.get('curated_flights', {}),
                "hotel_offers": result.get('hotel_offers', []),
                "enhanced_offers": result.get('enhanced_offers', {}),
                "itinerary": result.get('itinerary', {}),
                "status": result.get('status', 'draft_ready')
            }
            
        except Exception as e:
            logger.error(f"Orchestrator error", session_id=session_id, error=str(e))
            raise
    
    async def process_confirmation(self, session_id: str) -> Dict[str, Any]:
        """Process booking confirmation and run compliance agents"""
        try:
            # Load session state
            session = self.db.query(SearchSession).filter(
                SearchSession.session_id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Initialize state from session
            state: TravelState = {
                "session_id": session_id,
                "user_request": session.original_request or "",
                "customer_id": session.customer_id or "",
                "email_id": None,
                "nationality": None,
                
                # Load from session
                "extracted_requirements": session.extracted_requirements or {},
                "user_profile": {},
                "destination_suggestions": {},
                "flight_offers": [],
                "hotel_offers": [],
                "enhanced_offers": {},
                "itinerary": session.final_itinerary or {},
                
                # To be populated
                "visa_requirements": {},
                "health_advisory": {},
                "insurance_recommendations": {},
                "seatmap_data": {},
                
                "status": "confirmed",
                "confirmation_pending": False,
                "needs_destination_discovery": False,
                "messages": []
            }
            
            # Run compliance workflow
            result = await self.compliance_graph.ainvoke(state)
            
            return {
                "visa_requirements": result.get("visa_requirements", {}),
                "health_advisory": result.get("health_advisory", {}),
                "insurance_recommendations": result.get("insurance_recommendations", {}),
                "seatmap_data": result.get("seatmap_data", {}),
                "status": "travel_ready"
            }
            
        except Exception as e:
            logger.error(f"Confirmation error", session_id=session_id, error=str(e))
            raise
    
    # ======================= PLANNING WORKFLOW NODES =======================
    
    async def _extract_requirements(self, state: TravelState) -> TravelState:
        """Phase 1: Extract travel requirements using enhanced LLM with no hallucination"""
        try:
            agent = LLMExtractorAgent()
            
            input_data = {
                "user_request": state["user_request"],
                "conversation_context": state.get("conversation_context")
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["extracted_requirements"] = result
            
            # Determine if destination discovery is needed
            result_data = result.get("data", {})
            requirements = result_data.get("requirements", {})
            destination = requirements.get("destination")
            destination_type = requirements.get("destination_type")
            
            # Check for vague destination patterns that need discovery
            vague_destination_patterns = [
                "europe", "asia", "africa", "america", "oceania",
                "somewhere warm", "somewhere cold", "somewhere snowy", "somewhere tropical",
                "beach destination", "mountain destination", "ski destination", "winter destination",
                "warm place", "cold place", "snowy place", "tropical place",
                "skiing", "beaches", "mountains", "desert", "islands"
            ]
            
            is_vague_destination = False
            if destination:
                destination_lower = destination.lower()
                is_vague_destination = any(pattern in destination_lower for pattern in vague_destination_patterns)
            
            state["needs_destination_discovery"] = (
                not destination or 
                is_vague_destination or
                (destination_type and not destination)
            )
            
            logger.info(f"Requirements extracted", 
                       session_id=state["session_id"],
                       destination_discovery_needed=state["needs_destination_discovery"])
            
        except Exception as e:
            logger.error(f"Requirements extraction failed", session_id=state["session_id"], error=str(e))
            state["extracted_requirements"] = {"error": str(e)}
        
        return state
    
    async def _get_user_profile(self, state: TravelState) -> TravelState:
        """Phase 1: Get comprehensive user profile with travel history and preferences"""
        try:
            agent = UserProfileAgent()
            
            # UserProfileAgent always needs customer_id, prefer email_id as customer_id
            input_data = {}
            if state["email_id"]:
                input_data["customer_id"] = state["email_id"]
                input_data["email_id"] = state["email_id"]
            elif state["customer_id"]:
                input_data["customer_id"] = state["customer_id"]
            else:
                input_data["customer_id"] = f"guest_{state['session_id'][:8]}"
            
            result = await agent.execute(input_data, state["session_id"])
            state["user_profile"] = result
            
            # Extract nationality if not provided
            if not state["nationality"] and result.get("data", {}).get("nationality"):
                state["nationality"] = result["data"]["nationality"]
            
            logger.info(f"User profile loaded", 
                       session_id=state["session_id"],
                       loyalty_tier=result.get("data", {}).get("loyalty_tier", "STANDARD"))
            
        except Exception as e:
            logger.error(f"User profile loading failed", session_id=state["session_id"], error=str(e))
            state["user_profile"] = {"error": str(e), "data": {"loyalty_tier": "STANDARD"}}
        
        return state
    
    def _needs_destination_discovery(self, state: TravelState) -> str:
        """Determine if destination discovery is needed"""
        return "discover" if state["needs_destination_discovery"] else "search"
    
    async def _discover_destinations(self, state: TravelState) -> TravelState:
        """Phase 2: Discover destinations for vague requests"""
        try:
            agent = DestinationDiscoveryAgent()
            
            requirements = state["extracted_requirements"].get("requirements", {})
            
            result_data = state["extracted_requirements"].get("data", {})
            requirements = result_data.get("requirements", {})
            
            input_data = {
                "destination_type": requirements.get("destination_type"),
                "budget": requirements.get("budget"),
                "budget_currency": requirements.get("budget_currency", "USD"),
                "departure_date": requirements.get("departure_date"),
                "duration": requirements.get("duration"),
                "passengers": requirements.get("passengers", 1),
                "nationality": state["nationality"] or "US",
                "special_requirements": requirements.get("special_requirements", [])
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["destination_suggestions"] = result
            
            logger.info(f"Destinations discovered", 
                       session_id=state["session_id"],
                       suggestion_count=len(result.get("suggestions", [])))
            
        except Exception as e:
            logger.error(f"Destination discovery failed", session_id=state["session_id"], error=str(e))
            state["destination_suggestions"] = {"error": str(e)}
        
        return state
    
    def _needs_event_search(self, state: TravelState) -> str:
        """Determine if event search is needed"""
        result_data = state["extracted_requirements"].get("data", {})
        requirements = result_data.get("requirements", {})
        
        has_event = (
            requirements.get("event_name") or 
            requirements.get("event_type") or
            state["needs_event_search"]
        )
        
        return "search" if has_event else "skip"
    
    async def _search_events(self, state: TravelState) -> TravelState:
        """Phase 2.5: Search for events and festivals"""
        # First, check if event search is needed
        if self._needs_event_search(state) == "skip":
            logger.info("No events detected, skipping event search", session_id=state["session_id"])
            return state
            
        try:
            agent = EventSearchAgent()
            
            result_data = state["extracted_requirements"].get("data", {})
            requirements = result_data.get("requirements", {})
            
            # Extract event information
            event_name = requirements.get("event_name")
            event_type = requirements.get("event_type")
            destination = requirements.get("destination")
            
            logger.info(f"🎉 Event search triggered", 
                       session_id=state["session_id"],
                       event_name=event_name,
                       event_type=event_type,
                       destination=destination)
            
            input_data = {
                "event_name": event_name,
                "event_type": event_type,
                "destination": destination,
                "departure_date": requirements.get("departure_date"),
                "duration": requirements.get("duration"),
                "passengers": requirements.get("passengers", 1),
                "budget": requirements.get("budget"),
                "special_requirements": requirements.get("special_requirements", [])
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["event_details"] = result
            
            logger.info(f"Events found", 
                       session_id=state["session_id"],
                       event_count=len(result.get("data", {}).get("events", [])))
            
        except Exception as e:
            logger.error(f"Event search failed", session_id=state["session_id"], error=str(e))
            state["event_details"] = {"error": str(e)}
        
        return state
    
    async def _search_flights_hotels_parallel(self, state: TravelState) -> TravelState:
        """Phase 3: Search flights and hotels in parallel using Amadeus APIs"""
        try:
            result_data = state["extracted_requirements"].get("data", {})
            requirements = result_data.get("requirements", {})
            
            # Determine final destination
            destination = requirements.get("destination")
            if not destination and state["destination_suggestions"].get("suggestions"):
                # Use first suggestion if no specific destination
                destination = state["destination_suggestions"]["suggestions"][0].get("destination")
            
            if not destination:
                logger.warning(f"No destination available for search", session_id=state["session_id"])
                state["flight_offers"] = []
                state["hotel_offers"] = []
                return state
            
            # Prepare search parameters
            departure_date = requirements.get("departure_date", "2024-07-01")
            return_date = requirements.get("return_date")
            duration = requirements.get("duration", 7)
            adults = requirements.get("passengers", 1)
            travel_class = requirements.get("travel_class", "ECONOMY")
            
            # Calculate check-out date if not provided
            if not return_date:
                try:
                    from datetime import datetime, timedelta
                    dep_date = datetime.fromisoformat(departure_date)
                    return_date = (dep_date + timedelta(days=duration-1)).isoformat()[:10]
                except:
                    # Fallback: add duration to departure date string
                    return_date = departure_date  # This should be fixed with proper date calculation
                    
            # Ensure check-out is at least 1 day after check-in
            if return_date == departure_date:
                try:
                    from datetime import datetime, timedelta
                    dep_date = datetime.fromisoformat(departure_date)
                    return_date = (dep_date + timedelta(days=1)).isoformat()[:10]
                except:
                    return_date = departure_date
            
            # Parse destination for airport/city codes (simplified)
            origin = "LAX"  # Default origin (would be determined from user location)
            dest_code = self._get_destination_code(destination)
            city_code = self._get_city_code(destination)
            
            # Run flights and hotels search in parallel
            flight_task = self._search_flights({
                "origin": origin,
                "destination": dest_code,
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "travel_class": travel_class
            }, state["session_id"])
            
            hotel_task = self._search_hotels({
                "cityCode": city_code,
                "checkInDate": departure_date,
                "checkOutDate": return_date,
                "adults": adults,
                "rooms": 1
            }, state["session_id"])
            
            # Wait for both to complete
            flight_result, hotel_result = await asyncio.gather(flight_task, hotel_task, return_exceptions=True)
            
            # Handle results - data is nested under "data" key
            if isinstance(flight_result, Exception):
                logger.error(f"Flight search failed", session_id=state["session_id"], error=str(flight_result))
                state["flight_offers"] = []
            else:
                state["flight_offers"] = flight_result.get("data", {}).get("offers", [])
            
            if isinstance(hotel_result, Exception):
                logger.error(f"Hotel search failed", session_id=state["session_id"], error=str(hotel_result))
                state["hotel_offers"] = []
            else:
                # Extract hotels from the agent's data structure
                hotel_data = hotel_result.get("data", {})
                state["hotel_offers"] = hotel_data.get("hotels", [])
            
            logger.info(f"Search completed", 
                       session_id=state["session_id"],
                       flights=len(state["flight_offers"]),
                       hotels=len(state["hotel_offers"]))
            
        except Exception as e:
            logger.error(f"Parallel search failed", session_id=state["session_id"], error=str(e))
            state["flight_offers"] = []
            state["hotel_offers"] = []
        
        return state
    
    async def _search_flights(self, search_params: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Search flights using FlightsSearchAgent"""
        agent = FlightsSearchAgent()
        return await agent.execute(search_params, session_id)
    
    async def _search_hotels(self, search_params: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Search hotels using HotelSearchAgent"""
        agent = HotelSearchAgent()
        return await agent.execute(search_params, session_id)
    
    async def _enhance_offers(self, state: TravelState) -> TravelState:
        """Phase 3: Apply CKB overlays to offers for discounts and supplier ranking"""
        try:
            agent = OffersAgent()
            
            customer_profile = state["user_profile"].get("data", {})
            result_data = state["extracted_requirements"].get("data", {})
            requirements = result_data.get("requirements", {})
            
            # Calculate booking context
            departure_date = requirements.get("departure_date")
            advance_days = 30  # Default
            current_month = datetime.now().month
            
            if departure_date:
                try:
                    dep_date = datetime.fromisoformat(departure_date)
                    advance_days = (dep_date - datetime.now()).days
                    current_month = dep_date.month
                except:
                    pass
            
            input_data = {
                "flight_offers": state["flight_offers"],
                "hotel_offers": state["hotel_offers"],
                "customer_profile": customer_profile,
                "booking_context": {
                    "advance_booking_days": advance_days,
                    "departure_month": current_month,
                    "nights": requirements.get("duration", 7)
                }
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["enhanced_offers"] = result
            
            logger.info(f"Offers enhanced", 
                       session_id=state["session_id"],
                       total_savings=result.get("total_savings", 0))
            
        except Exception as e:
            logger.error(f"Offer enhancement failed", session_id=state["session_id"], error=str(e))
            state["enhanced_offers"] = {"error": str(e)}
        
        return state
    
    async def _curate_flights(self, state: TravelState) -> TravelState:
        """Phase 4: Curate and rank flights based on customer preferences"""
        try:
            agent = FlightCuratorAgent()
            
            result_data = state["extracted_requirements"].get("data", {})
            requirements = result_data.get("requirements", {})
            
            input_data = {
                "flight_offers": state["flight_offers"],
                "customer_profile": state["user_profile"].get("data", {}),
                "requirements": requirements,
                "enhanced_offers": state["enhanced_offers"]
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["curated_flights"] = result
            
            curated_count = len(result.get("data", {}).get("curated_flights", []))
            confidence = result.get("data", {}).get("curation_confidence", 0)
            
            logger.info(f"Flights curated", 
                       session_id=state["session_id"],
                       curated_count=curated_count,
                       confidence_score=confidence)
            
        except Exception as e:
            logger.error(f"Flight curation failed", session_id=state["session_id"], error=str(e))
            state["curated_flights"] = {"error": str(e)}
        
        return state
    
    async def _prepare_itinerary(self, state: TravelState) -> TravelState:
        """Phase 5: Assemble coherent travel itinerary with rationale"""
        try:
            agent = PrepareItineraryAgent()
            
            result_data = state["extracted_requirements"].get("data", {})
            requirements = result_data.get("requirements", {})
            
            # Check if we have minimum required information
            if not requirements.get("destination") and not state.get("destination_suggestions", {}).get("suggestions"):
                logger.warning(f"Insufficient travel requirements for itinerary", session_id=state["session_id"])
                state["itinerary"] = {
                    "error": "Insufficient travel information provided. Please specify destination, dates, and travel preferences.",
                    "requirements_needed": ["destination", "departure_date", "duration", "travelers"]
                }
                state["status"] = "requirements_missing"
                return state
            
            # Use curated flights if available, otherwise fall back to enhanced offers
            curated_flight_data = state["curated_flights"].get("data", {})
            curated_flights = curated_flight_data.get("curated_flights", [])
            
            # Extract original flight offers from curated flights or use enhanced offers
            flight_offers_for_itinerary = []
            if curated_flights:
                flight_offers_for_itinerary = [cf.get("original_offer", {}) for cf in curated_flights[:3]]  # Top 3
            else:
                flight_offers_for_itinerary = state["enhanced_offers"].get("enhanced_offers", [])
            
            input_data = {
                "requirements": requirements,
                "customer_profile": state["user_profile"].get("data", {}),
                "flight_offers": flight_offers_for_itinerary,
                "hotel_offers": state["enhanced_offers"].get("enhanced_offers", []),
                "destination_suggestions": state["destination_suggestions"].get("suggestions", []),
                "curated_flights": curated_flight_data,  # Include curation data
                "events": state["event_details"].get("data", {}).get("events", []) if state.get("event_details") else []  # Pass event data for images and scheduling
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["itinerary"] = result
            state["status"] = "draft_ready"
            
            logger.info(f"Itinerary prepared", 
                       session_id=state["session_id"],
                       confidence_score=result.get("confidence_score", 0))
            
        except Exception as e:
            logger.error(f"Itinerary preparation failed", session_id=state["session_id"], error=str(e))
            state["itinerary"] = {"error": str(e)}
            state["status"] = "draft_failed"
        
        return state
    
    # ======================= COMPLIANCE WORKFLOW NODES =======================
    
    async def _check_visa_requirements(self, state: TravelState) -> TravelState:
        """Check visa requirements using Amadeus Travel Restrictions API"""
        try:
            agent = VisaRequirementAgent()
            
            requirements = state["extracted_requirements"].get("requirements", {})
            destination = requirements.get("destination", "")
            nationality = state["nationality"] or state["user_profile"].get("data", {}).get("nationality", "US")
            
            # Convert destination to country code (simplified)
            dest_country = self._get_country_code(destination)
            origin_country = self._get_country_code(nationality)
            
            input_data = {
                "origin_country": origin_country,
                "destination_country": dest_country,
                "travel_purpose": "tourism"
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["visa_requirements"] = result
            
        except Exception as e:
            logger.error(f"Visa requirements check failed", session_id=state["session_id"], error=str(e))
            state["visa_requirements"] = {"error": str(e)}
        
        return state
    
    async def _get_health_advisory(self, state: TravelState) -> TravelState:
        """Get health advisory for destination"""
        try:
            agent = HealthAdvisoryAgent()
            
            requirements = state["extracted_requirements"].get("requirements", {})
            destination = requirements.get("destination", "")
            dest_country = self._get_country_code(destination)
            
            customer_profile = state["user_profile"].get("data", {})
            
            input_data = {
                "destination_country": dest_country,
                "traveler_profile": {
                    "age": customer_profile.get("age", 35),
                    "nationality": state["nationality"] or "US"
                },
                "travel_dates": requirements.get("departure_date")
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["health_advisory"] = result
            
        except Exception as e:
            logger.error(f"Health advisory failed", session_id=state["session_id"], error=str(e))
            state["health_advisory"] = {"error": str(e)}
        
        return state
    
    async def _get_insurance_recommendations(self, state: TravelState) -> TravelState:
        """Get personalized insurance recommendations"""
        try:
            agent = InsuranceAgent()
            
            requirements = state["extracted_requirements"].get("requirements", {})
            customer_profile = state["user_profile"].get("data", {})
            
            trip_cost = 0
            if state["enhanced_offers"].get("total_effective_price"):
                trip_cost = state["enhanced_offers"]["total_effective_price"]
            
            input_data = {
                "trip_details": {
                    "destination": requirements.get("destination", ""),
                    "duration": requirements.get("duration", 7),
                    "activities": requirements.get("special_requirements", []),
                    "trip_cost": trip_cost
                },
                "traveler_profile": {
                    "age": customer_profile.get("age", 35),
                    "health_conditions": [],
                    "travel_frequency": "occasional"
                }
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["insurance_recommendations"] = result
            
        except Exception as e:
            logger.error(f"Insurance recommendations failed", session_id=state["session_id"], error=str(e))
            state["insurance_recommendations"] = {"error": str(e)}
        
        return state
    
    async def _get_seatmap_options(self, state: TravelState) -> TravelState:
        """Get seat map and recommendations with CKB benefits"""
        try:
            agent = SeatMapAgent()
            
            # Use first flight offer for seat map
            flight_offers = state.get("flight_offers", [])
            if not flight_offers:
                state["seatmap_data"] = {"message": "No flight offers available for seat selection"}
                return state
            
            flight_offer_id = flight_offers[0].get("id", "mock_flight_1")
            customer_profile = state["user_profile"].get("data", {})
            
            input_data = {
                "flight_offer_id": flight_offer_id,
                "customer_profile": customer_profile,
                "preferences": {
                    "location": "window",
                    "legroom": customer_profile.get("age", 30) > 60,
                    "quiet": True
                }
            }
            
            result = await agent.execute(input_data, state["session_id"])
            state["seatmap_data"] = result
            
        except Exception as e:
            logger.error(f"Seat map options failed", session_id=state["session_id"], error=str(e))
            state["seatmap_data"] = {"error": str(e)}
        
        return state
    
    async def _finalize_travel_package(self, state: TravelState) -> TravelState:
        """Finalize complete travel readiness package"""
        try:
            # Compile final travel readiness package
            state["status"] = "travel_ready"
            
            logger.info(f"Travel package finalized", 
                       session_id=state["session_id"],
                       has_visa_info=bool(state.get("visa_requirements")),
                       has_health_info=bool(state.get("health_advisory")),
                       has_insurance_info=bool(state.get("insurance_recommendations")),
                       has_seatmap_info=bool(state.get("seatmap_data")))
            
        except Exception as e:
            logger.error(f"Travel package finalization failed", session_id=state["session_id"], error=str(e))
            state["status"] = "finalization_failed"
        
        return state
    
    # ======================= UTILITY METHODS =======================
    
    def _get_destination_code(self, destination: str) -> str:
        """Convert destination name to airport code (simplified mapping)"""
        if not destination or destination is None:
            return "JFK"  # Default fallback
            
        destination_codes = {
            "Zermatt": "ZUR",  # Zurich airport for Zermatt
            "Switzerland": "ZUR",
            "Tokyo": "NRT",
            "Paris": "CDG",
            "London": "LHR",
            "New York": "JFK",
            "Bangkok": "BKK",
            "Bangkok, Thailand": "BKK",  # Support the standardized format
            "Thailand": "BKK",  # Many people say "Thailand" meaning Bangkok
            "Singapore": "SIN",
            "Dubai": "DXB",
            "Mumbai": "BOM",
            "Bangalore": "BLR",
            "Bangalore, India": "BLR",  # Support the standardized format
            "Bengaluru": "BLR",  # Official name of Bangalore
            "Bengaluru, India": "BLR",
            "Sydney": "SYD",
            "Los Angeles": "LAX"
        }
        
        try:
            for city, code in destination_codes.items():
                if city.lower() in destination.lower():
                    return code
        except (AttributeError, TypeError):
            # Handle case where destination is None or not a string
            pass
        
        # Default fallback
        return "JFK"
    
    def _get_city_code(self, destination: str) -> str:
        """Convert destination name to city code (simplified mapping)"""
        city_codes = {
            "Zermatt": "ZUR",  # Use Zurich city code for Zermatt hotels
            "Switzerland": "ZUR",
            "Tokyo": "TYO",
            "Paris": "PAR",
            "London": "LON",
            "New York": "NYC",
            "Bangkok": "BKK",
            "Bangkok, Thailand": "BKK",  # Support the standardized format
            "Thailand": "BKK",  # Many people say "Thailand" meaning Bangkok
            "Singapore": "SIN",
            "Dubai": "DXB",
            "Mumbai": "BOM",
            "Bangalore": "BLR",
            "Bangalore, India": "BLR",  # Support the standardized format
            "Bengaluru": "BLR",  # Official name of Bangalore
            "Bengaluru, India": "BLR",
            "Sydney": "SYD",
            "Los Angeles": "LAX"
        }
        
        logger.info(f"🗺️ [City Resolution] Input destination: '{destination}'")
        
        if not destination or destination is None:
            logger.info("⚠️ [City Resolution] Empty destination, using PAR fallback")
            return "PAR"  # Default fallback
        
        try:
            for city, code in city_codes.items():
                if city.lower() in destination.lower():
                    logger.info(f"✅ [City Resolution] Matched '{destination}' → {code}")
                    return code
        except (AttributeError, TypeError):
            # Handle case where destination is None or not a string
            logger.info(f"❌ [City Resolution] Error processing destination: {destination}")
            pass
        
        # Default fallback
        logger.info(f"⚠️ [City Resolution] No match found for '{destination}', using PAR fallback")
        return "PAR"
    
    def _get_country_code(self, location: str) -> str:
        """Convert location name to country code (simplified mapping)"""
        country_codes = {
            "Japan": "JP",
            "Tokyo": "JP",
            "France": "FR",
            "Paris": "FR",
            "United Kingdom": "GB",
            "UK": "GB",
            "London": "GB",
            "United States": "US",
            "US": "US",
            "New York": "US",
            "Thailand": "TH",
            "Bangkok": "TH",
            "Bangkok, Thailand": "TH",
            "Bangalore": "IN",
            "Bangalore, India": "IN",
            "Bengaluru": "IN",  # Official name of Bangalore
            "Bengaluru, India": "IN",
            "Singapore": "SG",
            "UAE": "AE",
            "Dubai": "AE",
            "India": "IN",
            "Mumbai": "IN",
            "Australia": "AU",
            "Sydney": "AU",
            "Brazil": "BR"
        }
        
        if not location or location is None:
            return "US"  # Default fallback
        
        try:
            location_lower = location.lower()
            for name, code in country_codes.items():
                if name.lower() in location_lower:
                    return code
        except (AttributeError, TypeError):
            # Handle case where location is None or not a string
            pass
        
        # Default fallback
        return "US"
    
    async def _create_session_record(self, input_data: Dict[str, Any], session_id: str):
        """Create or update session record in MySQL"""
        # Check if session already exists
        existing_session = self.db.query(SearchSession).filter(
            SearchSession.session_id == session_id
        ).first()
        
        if existing_session:
            # Update existing session with new request
            existing_session.original_request = input_data["user_request"]
            existing_session.status = "processing"
            existing_session.updated_at = datetime.now(timezone.utc)
            self.db.commit()
        else:
            # Create new session
            session = SearchSession(
                session_id=session_id,
                customer_id=input_data.get("customer_id") or input_data.get("email_id") or f"guest_{session_id[:8]}",
                original_request=input_data["user_request"],
                status="processing"
            )
            
            self.db.add(session)
            self.db.commit()
        
    async def _update_session_record(self, session_id: str, result: TravelState):
        """Update session record with results"""
        session = self.db.query(SearchSession).filter(
            SearchSession.session_id == session_id
        ).first()
        
        if session:
            session.extracted_requirements = result.get("extracted_requirements")
            session.final_itinerary = result.get("itinerary")
            session.status = result.get("status")
            self.db.commit()