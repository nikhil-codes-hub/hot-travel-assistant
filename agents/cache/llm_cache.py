import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import structlog

logger = structlog.get_logger()

class LLMCache:
    """
    File-based cache system for storing LLM responses to improve performance
    and reduce API costs for similar travel planning queries.
    """
    
    def __init__(self, cache_dir: str = None, cache_duration_hours: int = 24):
        """
        Initialize LLM cache
        
        Args:
            cache_dir: Directory to store cache files (default: ./cache)
            cache_duration_hours: How long to keep cache entries valid (default: 24 hours, 0 = disabled)
        """
        self.cache_dir = Path(cache_dir or "cache/llm_responses")
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.cache_enabled = cache_duration_hours > 0
        
        if self.cache_enabled:
            # Create cache directory if it doesn't exist
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"LLM cache initialized", cache_dir=str(self.cache_dir), duration_hours=cache_duration_hours)
        else:
            logger.info("🚫 LLM cache DISABLED (duration_hours=0)")
    
    def _generate_cache_key(self, user_request: str, conversation_context: Dict[str, Any] = None) -> str:
        """
        Generate a unique cache key based on normalized travel requirements
        
        Args:
            user_request: The original user request
            conversation_context: Previous conversation context
            
        Returns:
            Unique cache key string
        """
        # Normalize the user request for better cache hits
        normalized_request = self._normalize_request(user_request)
        
        # Create a cache key from normalized request and relevant context
        cache_data = {
            "normalized_request": normalized_request,
            "context": self._normalize_context(conversation_context or {})
        }
        
        # Generate MD5 hash for the cache key
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_key = hashlib.md5(cache_string.encode()).hexdigest()
        
        return cache_key
    
    def _normalize_request(self, user_request: str) -> str:
        """
        Normalize user request to improve cache hit rates
        
        Args:
            user_request: Raw user request
            
        Returns:
            Normalized request string
        """
        if not user_request:
            return ""
            
        # Convert to lowercase and remove extra whitespace
        normalized = user_request.lower().strip()
        
        # Normalize common variations
        replacements = {
            # Destination variations
            "thailand trip": "thailand",
            "visit thailand": "thailand", 
            "travel to thailand": "thailand",
            "trip to thailand": "thailand",
            "thailand vacation": "thailand",
            "thailand travel": "thailand",
            
            # Paris variations
            "paris trip": "paris",
            "visit paris": "paris",
            "travel to paris": "paris",
            "trip to paris": "paris", 
            "paris vacation": "paris",
            
            # Time variations
            "next month": "1 month",
            "in a month": "1 month",
            "in december": "december",
            "this december": "december",
            
            # Duration variations
            "1 week": "7 days",
            "one week": "7 days",
            "2 weeks": "14 days",
            "two weeks": "14 days",
        }
        
        for original, replacement in replacements.items():
            normalized = normalized.replace(original, replacement)
        
        # Remove articles and common words that don't affect planning
        common_words = ["i", "want", "to", "would", "like", "please", "can", "you", "help", "me"]
        words = normalized.split()
        words = [word for word in words if word not in common_words]
        
        return " ".join(words)
    
    def _normalize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize conversation context for cache key generation
        
        Args:
            context: Raw conversation context
            
        Returns:
            Normalized context dictionary
        """
        if not context:
            return {}
            
        # Only include fields that affect LLM responses
        relevant_fields = [
            'destination', 'destination_type', 'duration', 'budget', 
            'budget_currency', 'passengers', 'travel_class', 'accommodation_type'
        ]
        
        normalized_context = {}
        for field in relevant_fields:
            if field in context and context[field] is not None:
                normalized_context[field] = context[field]
        
        return normalized_context
    
    def get_cached_response(self, user_request: str, conversation_context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached LLM response if available and valid
        
        Args:
            user_request: The user's travel request
            conversation_context: Previous conversation context
            
        Returns:
            Cached response dictionary or None if not found/expired
        """
        if not self.cache_enabled:
            return None
            
        cache_key = self._generate_cache_key(user_request, conversation_context)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            if not cache_file.exists():
                logger.debug("Cache miss - file not found", cache_key=cache_key)
                return None
            
            # Load cache file
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cached_data.get('timestamp', ''))
            if datetime.now() - cached_time > self.cache_duration:
                logger.debug("Cache expired", cache_key=cache_key, cached_time=cached_time)
                # Clean up expired cache file
                cache_file.unlink(missing_ok=True)
                return None
            
            logger.info("Cache hit - returning cached response", 
                       cache_key=cache_key, 
                       age_minutes=int((datetime.now() - cached_time).total_seconds() / 60))
            
            return cached_data.get('response')
            
        except Exception as e:
            logger.warning("Cache read error", cache_key=cache_key, error=str(e))
            return None
    
    def store_cached_response(self, user_request: str, conversation_context: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """
        Store LLM response in cache
        
        Args:
            user_request: The user's travel request
            conversation_context: Conversation context used
            response: LLM response to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        if not self.cache_enabled:
            return False
            
        cache_key = self._generate_cache_key(user_request, conversation_context)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'user_request': user_request,
                'normalized_request': self._normalize_request(user_request),
                'conversation_context': self._normalize_context(conversation_context or {}),
                'response': response,
                'cache_key': cache_key
            }
            
            # Write to cache file
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Response cached successfully", 
                       cache_key=cache_key, 
                       file_size=cache_file.stat().st_size)
            
            return True
            
        except Exception as e:
            logger.error("Cache write error", cache_key=cache_key, error=str(e))
            return False
    
    def clear_expired_cache(self) -> int:
        """
        Clean up expired cache files
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    cached_time = datetime.fromisoformat(cached_data.get('timestamp', ''))
                    if datetime.now() - cached_time > self.cache_duration:
                        cache_file.unlink()
                        removed_count += 1
                        
                except Exception:
                    # Remove corrupted cache files
                    cache_file.unlink(missing_ok=True)
                    removed_count += 1
            
            if removed_count > 0:
                logger.info("Cache cleanup completed", files_removed=removed_count)
            
        except Exception as e:
            logger.error("Cache cleanup error", error=str(e))
        
        return removed_count
    
    def clear_all_cache(self) -> Dict[str, Any]:
        """
        Clear all cache files
        
        Returns:
            Dictionary with clearing results
        """
        removed_count = 0
        total_size = 0
        
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_files = len(cache_files)
            
            for cache_file in cache_files:
                try:
                    file_size = cache_file.stat().st_size
                    total_size += file_size
                    cache_file.unlink()
                    removed_count += 1
                except Exception as e:
                    logger.warning("Failed to remove cache file", file=str(cache_file), error=str(e))
            
            logger.info("Cache cleared completely", 
                       files_removed=removed_count, 
                       size_cleared_mb=round(total_size / (1024 * 1024), 2))
            
            return {
                'success': True,
                'files_removed': removed_count,
                'total_files': total_files,
                'size_cleared_bytes': total_size,
                'size_cleared_mb': round(total_size / (1024 * 1024), 2),
                'message': f"Successfully cleared {removed_count} cache files"
            }
            
        except Exception as e:
            logger.error("Cache clear error", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'files_removed': removed_count
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_files = len(cache_files)
            total_size = sum(f.stat().st_size for f in cache_files)
            
            # Count valid vs expired
            valid_files = 0
            expired_files = 0
            
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    cached_time = datetime.fromisoformat(cached_data.get('timestamp', ''))
                    if datetime.now() - cached_time > self.cache_duration:
                        expired_files += 1
                    else:
                        valid_files += 1
                        
                except Exception:
                    expired_files += 1
            
            return {
                'cache_directory': str(self.cache_dir),
                'total_files': total_files,
                'valid_files': valid_files,
                'expired_files': expired_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_duration_hours': self.cache_duration.total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error("Error getting cache stats", error=str(e))
            return {'error': str(e)}