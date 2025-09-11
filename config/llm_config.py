# LLM Configuration for Customer Profile Service
# Set up your LLM integration here

import os
from typing import Optional

class LLMConfig:
    """Configuration for LLM integration"""
    
    # OpenAI Configuration
    USE_OPENAI: bool = False  # Set to True to use OpenAI API
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')  # Set your API key as environment variable
    OPENAI_MODEL: str = 'gpt-3.5-turbo'  # Or 'gpt-4' for better results
    
    # Local LLM Configuration (LM Studio, Ollama, etc.)
    USE_LOCAL_LLM: bool = True  # Set to True to try local LLM first
    LOCAL_LLM_URL: str = 'http://localhost:1234/v1/chat/completions'  # LM Studio default
    LOCAL_LLM_MODEL: str = 'local-model'  # Model name for local LLM
    
    # Anthropic Claude Configuration (if you prefer)
    USE_CLAUDE: bool = False
    CLAUDE_API_KEY: Optional[str] = os.getenv('CLAUDE_API_KEY')
    CLAUDE_MODEL: str = 'claude-3-haiku-20240307'  # Fast and cost-effective
    
    # LLM Parameters
    TEMPERATURE: float = 0.7  # Creativity level (0.0 = deterministic, 1.0 = very creative)
    MAX_TOKENS: int = 1000    # Maximum response length
    TIMEOUT: int = 30         # Request timeout in seconds
    
    # Fallback Configuration
    USE_DYNAMIC_FALLBACK: bool = True  # Use database-driven suggestions if LLM fails

# Instructions for setting up LLM integration:

"""
## Quick Setup Guide:

### Option 1: OpenAI API (Recommended for best results)
1. Get API key from https://platform.openai.com/api-keys
2. Set environment variable: export OPENAI_API_KEY="your-key-here"
3. Set USE_OPENAI = True above

### Option 2: Local LLM with LM Studio (Free)
1. Download LM Studio from https://lmstudio.ai/
2. Download a model (recommend: llama-2-7b-chat or similar)
3. Start local server in LM Studio (usually runs on port 1234)
4. Keep USE_LOCAL_LLM = True (default)

### Option 3: Anthropic Claude API
1. Get API key from https://console.anthropic.com/
2. Set environment variable: export CLAUDE_API_KEY="your-key-here"  
3. Set USE_CLAUDE = True above

### Testing Your Setup:
After configuration, the system will:
1. Try LLM API first (OpenAI, Claude, or Local)
2. Fall back to intelligent database-driven suggestions if LLM fails
3. Provide basic suggestions as final fallback

The system works without any LLM setup using smart database analysis!
"""