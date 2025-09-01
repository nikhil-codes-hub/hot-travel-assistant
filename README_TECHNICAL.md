# HOT Intelligent Travel Assistant

An Agentic-AI travel assistant for House of Travel (HOT) agents, built with MySQL database backend.

## Architecture Overview

- **Framework**: LangGraph for agent orchestration
- **Backend**: FastAPI with Python
- **Database**: MySQL 8.0 with SQLAlchemy ORM
- **AI**: Google Gemini for LLM extraction
- **Containerization**: Docker & Docker Compose

## Key Features

- Multi-agent system for travel request processing
- MySQL-based user profiles and commercial knowledge base
- LLM-powered requirement extraction
- Agent execution tracking and auditing
- RESTful API endpoints

## Quick Start

1. **Clone and setup**:
   ```bash
   cd hot_intelligent_travel_assistant
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start with Podman (Recommended)**:
   ```bash
   ./scripts/setup-podman.sh
   ```

3. **Or use podman-compose directly**:
   ```bash
   podman-compose up -d
   ```

4. **Or run locally**:
   ```bash
   # Start MySQL only
   podman-compose up mysql -d
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run migrations
   python -c "from config.database import engine; from models.database_models import Base; Base.metadata.create_all(bind=engine)"
   
   # Start API
   uvicorn api.main:app --reload
   ```

## Podman Management

Use the management script for easy container operations:
```bash
./scripts/podman-commands.sh start     # Start services
./scripts/podman-commands.sh logs api  # View API logs
./scripts/podman-commands.sh stop      # Stop services
./scripts/podman-commands.sh shell mysql  # MySQL shell
```

## API Endpoints

- `POST /travel/search` - Submit travel request
- `GET /travel/session/{session_id}` - Get session status
- `POST /travel/confirm/{session_id}` - Confirm booking
- `GET /user/profile/{customer_id}` - Get user profile

## Database Schema

### Tables
- `user_profiles` - Customer profiles with preferences and history
- `commercial_knowledge_base` - HOT-specific rules and discounts
- `search_sessions` - Travel search sessions and results
- `agent_executions` - Agent execution logs and metrics
- `destination_data` - Destination information and requirements

## Agents

### MVP Agents (Implemented)
- **LLMExtractorAgent** - Extracts requirements from natural language
- **UserProfileAgent** - Manages customer profiles in MySQL

### Future Agents (Placeholder)
- **DestinationDiscoveryAgent** - Suggests destinations
- **FlightsSearchAgent** - Amadeus flight search
- **HotelsSearchAgent** - Amadeus hotel search
- **OffersAgent** - Apply CKB overlays
- **PrepareItineraryAgent** - Create travel plans
- **Compliance Agents** - Visa, health, insurance, seatmap

## Development

```bash
# Run tests
pytest

# Code formatting
black .

# Type checking
mypy .

# Linting
flake8 .
```

## Environment Variables

```bash
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/hot_travel_assistant
GEMINI_API_KEY=your_gemini_api_key_here
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
ENVIRONMENT=development
```

## Project Structure

```
hot_intelligent_travel_assistant/
├── agents/                 # AI agents
│   ├── base_agent.py      # Base agent class
│   ├── llm_extractor/     # Requirement extraction
│   ├── user_profile/      # User profile management
│   └── compliance/        # Visa, health, insurance, seatmap
├── api/                   # FastAPI application
├── config/                # Database and app configuration
├── database/              # Migrations and schemas
├── models/                # SQLAlchemy models
├── orchestrator/          # LangGraph workflow orchestration
└── tests/                 # Unit and integration tests
```

## Next Steps

1. Implement search agents (flights, hotels)
2. Add Commercial Knowledge Base overlays
3. Create itinerary preparation agent
4. Build compliance agents (visa, health, insurance)
5. Add Amadeus API integrations
6. Implement web dashboard for HOT agents