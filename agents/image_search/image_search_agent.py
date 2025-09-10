import os
from typing import Dict, Any, List, Optional
import json
import google.generativeai as genai
from google.cloud import aiplatform
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent
from agents.cache.llm_cache import LLMCache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ImageSearchResult(BaseModel):
    url: str = Field(..., description="Image URL")
    title: str = Field(..., description="Image title/description")
    source: str = Field(..., description="Image source/attribution")
    alt_text: str = Field(..., description="Alt text for accessibility")
    context: str = Field(..., description="Context where image would be used")
    relevance_score: float = Field(..., description="Relevance score 0-1")

class ImageSearchResponse(BaseModel):
    images: List[ImageSearchResult]
    search_query: str
    search_context: Dict[str, Any]
    total_results: int
    confidence_score: float

class ImageSearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("ImageSearchAgent")
        self.ai_provider = os.getenv("AI_PROVIDER", "gemini")
        self.ai_available = False
        
        # Initialize LLM response cache for image search
        cache_dir = os.getenv("LLM_CACHE_DIR", "cache/llm_responses")
        cache_duration = int(os.getenv("LLM_CACHE_DURATION_HOURS", "0"))
        self.cache = LLMCache(cache_dir=f"{cache_dir}/image_search", cache_duration_hours=cache_duration)
        
        try:
            if self.ai_provider == "vertex":
                # Initialize Vertex AI
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
                location = os.getenv("VERTEX_AI_LOCATION")
                if project_id and location:
                    aiplatform.init(project=project_id, location=location)
                    self.model = None
                    self.ai_available = True
            else:
                # Initialize Gemini
                api_key = os.getenv("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel('gemini-2.0-flash')
                    self.ai_available = True
        except Exception:
            self.ai_available = False
            self.model = None

    async def execute(self, input_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Generate contextual image suggestions for events, destinations, and activities
        
        Input:
        - event_name: specific event (e.g. "Diwali Festival")
        - destination: location (e.g. "Bangalore, India")
        - activity_type: type of activity (cultural, sightseeing, food, etc.)
        - context: where images will be used (itinerary_overview, day_activity, etc.)
        - image_count: number of images needed (default 3-5)
        """
        self.validate_input(input_data, [])
        
        # Check cache first
        cache_key_data = json.dumps(input_data, sort_keys=True)
        cached_response = self.cache.get_cached_response(cache_key_data, {})
        if cached_response:
            self.log(f"✅ Cache hit - returning cached image suggestions")
            return self.format_output(cached_response)
        
        # Use LLM to generate contextual image recommendations
        
        if not self.ai_available:
            self.log("⚠️ LLM not available - using fallback image suggestions")
            return self._generate_fallback_images(input_data)
        
        try:
            self.log(f"🔄 Cache miss - generating contextual image suggestions")
            prompt = self._create_image_search_prompt(input_data)
            
            # Call AI API
            if self.ai_provider == "vertex":
                response = await self._call_vertex_ai(prompt)
            else:
                response = self.model.generate_content(prompt)
            
            # Parse response
            if self.ai_provider == "vertex":
                result = self._parse_response(response, input_data)
            else:
                result = self._parse_response(response.text, input_data)
            
            # Store in cache
            cache_stored = self.cache.store_cached_response(cache_key_data, {}, result)
            if cache_stored:
                self.log(f"💾 Image suggestions cached")
            
            result["cache_info"] = {
                "cache_hit": False,
                "cached": cache_stored
            }
            
            self.log("✅ AI-powered image suggestions generated")
            return self.format_output(result)
            
        except Exception as e:
            self.log(f"⚠️ LLM image search failed: {str(e)}")
            return self._generate_fallback_images(input_data)

    async def _call_vertex_ai(self, prompt: str) -> str:
        """Call Vertex AI Gemini model"""
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel('gemini-2.0-flash')
        response = await model.generate_content_async(prompt)
        return response.text

    def _create_image_search_prompt(self, input_data: Dict[str, Any]) -> str:
        event_name = input_data.get("event_name", "")
        destination = input_data.get("destination", "")
        activity_type = input_data.get("activity_type", "")
        context = input_data.get("context", "itinerary_overview")
        image_count = input_data.get("image_count", 4)
        
        return f"""
You are a visual content curator specializing in travel and event photography. Your mission is to recommend the most compelling, contextually appropriate images that will enhance a travel itinerary and inspire travelers.

IMAGE SEARCH CRITERIA:
- Event: {event_name or "Not specified"}
- Destination: {destination or "Not specified"}
- Activity type: {activity_type or "General travel"}
- Context: {context}
- Number of images needed: {image_count}

VISUAL CONTENT MISSION:
1. Recommend authentic, high-quality images that capture the essence of the event/destination
2. Ensure cultural sensitivity and accurate representation
3. Select images that inspire and inform travelers
4. Consider the context where images will be displayed
5. Provide diverse perspectives (aerial, street level, details, people, architecture)

CONTEXT-SPECIFIC REQUIREMENTS:
- itinerary_overview: Hero images that showcase the destination's highlight
- event_highlight: Images specific to the event/festival being attended
- day_activity: Images relevant to specific daily activities
- destination_gallery: Comprehensive visual tour of the location

Return ONLY valid JSON with image recommendations:
{{
    "images": [
        {{
            "url": "https://placeholder-image-service.com/image-id",
            "title": "Descriptive title of the image",
            "source": "Stock photo service / Travel photography",
            "alt_text": "Detailed alt text for accessibility",
            "context": "Where this image would be most effective",
            "relevance_score": 0.95
        }}
    ],
    "search_query": "Keywords that would find these images",
    "search_context": {{
        "event_name": "{event_name}",
        "destination": "{destination}",
        "activity_type": "{activity_type}",
        "recommended_sources": ["Unsplash", "Getty Images", "Local tourism boards"]
    }},
    "total_results": {image_count},
    "confidence_score": 0.9
}}

DYNAMIC IMAGE CURATION GUIDELINES:
- Analyze the specific event and destination to generate appropriate image recommendations
- Focus on authentic, culturally accurate visual representations
- Include both wide-angle destination shots and intimate cultural details
- Consider the time of year, local customs, and regional characteristics
- Generate diverse perspectives: aerial views, street-level shots, architectural details, people celebrating
- Ensure images represent the authentic experience travelers will encounter
- Include both iconic landmarks and hidden local gems
- Consider the emotional impact and inspirational value of each image

QUALITY CRITERIA:
- High resolution and professional quality
- Culturally accurate and respectful representation
- Visually stunning and travel-inspiring
- Diverse perspectives and subjects
- Accessible and inclusive imagery

AVOID:
- Stereotypical or outdated representations
- Low-quality or amateur photography
- Culturally insensitive imagery
- Generic stock photos without local context
"""

    def _parse_response(self, response_text: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
                
            parsed_data = json.loads(response_text)
            
            # Validate and create result
            images = [ImageSearchResult(**image) for image in parsed_data["images"]]
            
            result = ImageSearchResponse(
                images=images,
                search_query=parsed_data.get("search_query", ""),
                search_context=parsed_data.get("search_context", {}),
                total_results=parsed_data.get("total_results", len(images)),
                confidence_score=parsed_data.get("confidence_score", 0.8)
            )
            
            parsed_result = result.model_dump()
            self.log(f"✅ Parsed {len(images)} AI image recommendations successfully")
            return parsed_result
            
        except Exception as e:
            self.log(f"⚠️ AI response parsing failed ({e}), using fallback images")
            return self._generate_fallback_images(input_data)

    def _generate_fallback_images(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback image suggestions when LLM is not available"""
        event_name = input_data.get("event_name", "")
        destination = input_data.get("destination", "")
        activity_type = input_data.get("activity_type", "")
        image_count = input_data.get("image_count", 3)
        
        # Instead of hardcoded URLs, provide placeholder descriptions that encourage LLM usage
        fallback_images = []
        for i in range(min(image_count, 3)):
            fallback_images.append({
                "url": "",
                "title": f"Image suggestion {i+1} - {event_name or destination or 'Travel destination'}",
                "source": "LLM Generated (currently unavailable)",
                "alt_text": f"Contextual image for {event_name or destination or activity_type}",
                "context": "llm_unavailable",
                "relevance_score": 0.5
            })
        
        fallback_result = {
            "images": fallback_images,
            "search_query": f"{event_name} {destination} {activity_type}".strip(),
            "search_context": {
                "event_name": input_data.get("event_name"),
                "destination": input_data.get("destination"), 
                "activity_type": input_data.get("activity_type"),
                "recommended_sources": ["LLM Generated Content"],
                "note": "LLM image generation currently unavailable"
            },
            "total_results": len(fallback_images),
            "confidence_score": 0.1,
            "mode": "llm_unavailable"
        }
        
        self.log(f"⚠️ LLM unavailable - returning {len(fallback_images)} placeholder image suggestions")
        return fallback_result