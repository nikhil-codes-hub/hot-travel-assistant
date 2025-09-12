# 🧩 Design Document: HOT Agentic-AI Travel Assistant  

## 1. Objective  
Develop an **Agentic-AI internal assistant** for House of Travel (HOT) agents.  
The assistant supports sales teams when customers give fuzzy requirements (e.g., *“I want to travel to a snowy place in Oct/Nov with a kid, budget <$1000”*).  

The system orchestrates multiple specialized agents to:  
- Parse and complete customer intent,  
- Search flights and hotels via Amadeus APIs,  
- Apply HOT’s Commercial Knowledge Base (CKB) overlays,  
- Prepare a draft itinerary,  
- On booking confirmation, provide compliance checks (Visa, Health, Insurance) and seat selection.  

---

## 2. High-Level Flow  
1. **LLM Extractor** (Gemini) processes the request into `req.json`.  
   - Extracts fields (destination, dates, budget, pax).  
   - Lists missing fields for HOT agent clarification.  
   - **No guessing or hallucination** — only extraction.  

2. **Orchestrator Agent** creates a task plan and delegates to other agents.  
   - Runs agents in parallel where possible.  
   - Enforces dependencies (e.g., SeatMap after priced offer).  

3. **UserProfileAgent** retrieves customer profile: nationality, loyalty tier, travel history, preferences.  

4. **Destination Discovery Agent** (if destination vague) suggests options using seasonality + budget filters.  

5. **Search Agents**  
   - **FlightsSearchAgent** → Amadeus Flight Offers + Price.  
   - **HotelSearchAgent** → Amadeus Hotels API.  
   - Run in parallel.  

6. **OffersAgent**  
   - Calls Amadeus Offers.  
   - Applies **CKB overlays** (discounts, waivers, supplier ranking).  
   - Returns **effective prices** and explanations.  

7. **PrepareItineraryAgent** assembles results into a coherent plan with rationale.  

8. **Confirmation loop**  
   - Orchestrator waits for HOT agent confirmation.  
   - If confirmed → proceed to compliance agents.  
   - If changed → re-plan with updated inputs.  

9. **Compliance & Add-ons (Post-confirmation)**  
   - **VisaRequirementAgent** → Amadeus Travel Restrictions API (with disclaimers).  
   - **HealthAdvisoryAgent** → entry requirements.  
   - **InsuranceAgent** → partner insurance products (CKB overlays).  
   - **SeatMapAgent** → Amadeus SeatMap Display, CKB seat discounts/waivers.  

10. **Final Output**: A **Travel Readiness Package** = itinerary + advisories + enriched offers.  

---

## 3. Architecture Components  
- **Orchestrator**  
  - Plans, dispatches tasks, aggregates results.  
  - Implemented as a graph/state machine (LangGraph, CrewAI).  

- **Agents**  
  - *LLM Extractor* (Gemini)  
  - *UserProfileAgent*  
  - *DestinationDiscoveryAgent*  
  - *FlightsSearchAgent*  
  - *HotelSearchAgent*  
  - *OffersAgent (Amadeus + CKB)*  
  - *PrepareItineraryAgent*  
  - *VisaRequirementAgent*  
  - *HealthAdvisoryAgent*  
  - *InsuranceAgent*  
  - *SeatMapAgent*  

- **Commercial Knowledge Base (CKB)**  
  - Stores HOT-specific deals, supplier preferences, seat/baggage rules.  
  - Exposed as a shared service to all agents.  

- **Data Providers**  
  - Amadeus APIs: Flight Offers + Price, Hotels, SeatMap, Travel Restrictions, Ancillaries.  
  - External (future): Visa APIs, Insurance providers.  

---

## 4. Data Flow Example (Snowy mountains query)  
1. Input: “Snowy mountains with kid, <$1000 in Oct/Nov.”  
2. LLM Extractor → `req.json` with: `{destination:null, budget:1000, month:[Oct,Nov], pax:2, child:yes}`.  
3. Orchestrator → Checklist: `[destination_discovery, flights, hotels, offers]`.  
4. DestinationDiscoveryAgent → Suggests [NZ Alps, Hokkaido, Canadian Rockies].  
5. FlightsSearch + HotelSearch (parallel) → base offers.  
6. OffersAgent → overlays HOT CKB rules (e.g., *20% discount on TG flights*).  
7. PrepareItineraryAgent → builds draft itinerary.  
8. HOT agent reviews with customer.  
9. On confirmation → Visa, Health, Insurance, SeatMap agents enrich final package.  

---

## 5. Tech Stack  
- **Framework**: LangGraph (agent orchestration)  
- **Backend**: Python (FastAPI)  
- **LLM**: Gemini for extraction and reasoning  
- **DB**: Postgres for CKB & user profiles (MVP can use JSON)  
- **UI**: Web dashboard for HOT agents  

---

## 6. Guardrails & NFRs  
- **PII handling**: Passport/email never leave backend. LLM sees anonymized data.  
- **Explainability**: Every recommendation shows applied rule (e.g., *−20% HOT seat discount*).  
- **Resilience**: Agent retries, timeouts, and circuit breakers. Fail-open if CKB down.  
- **Performance**: Parallel calls to keep response <4s P50.  
- **Auditing**: Logs per-agent latency, applied CKB rules, confidence scores.  

---

## 7. Risks & Mitigations  
- **LLM hallucination** → use extraction-only mode with JSON Schema validation.  
- **SeatMap dependency** → enforce offer/PNR before calling SeatMap API.  
- **Visa/Health accuracy** → label as advisory only, include sources + disclaimers.  
- **Scope creep** → booking/payment remain with existing HOT system.  

---

## 8. Roadmap  
**MVP (Hackathon)**  
- Orchestrator, UserProfileAgent, Flights/Hotels Search, OffersAgent (CKB overlay), PrepareItineraryAgent.  
- Output = Draft itinerary with enriched offers.  

**Phase 2**  
- Add Visa, Health, Insurance, SeatMap.  
- Generate complete Travel Readiness Package.  

**Phase 3**  
- CRM integration for HOT agents.  
- Expand CKB rules.  
- Add ground transport, tours.  
