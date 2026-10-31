# StayMate AI architecture

StayMate is intentionally a portfolio-sized monolith. The goal is to show clean agent orchestration and backend engineering without pretending a student project needs a fleet of microservices.

```text
React UI
   |
   v
FastAPI
   |
   v
LangGraph workflow
   |
   +--> Intent router
   |      +--> FAQ agent ------> RAG tool
   |      +--> Booking agent --> availability / booking / cancellation tools
   |      +--> Service agent --> housekeeping / maintenance tool
   |      +--> General agent --> direct response
   |
   v
PostgreSQL + pgvector
   +--> rooms
   +--> guests
   +--> bookings
   +--> service requests
   +--> hotel knowledge embeddings
```

## Why one backend service?

For this version, one FastAPI service keeps local development and deployment simple. The domain modules are already separated enough that booking, service-request, and RAG logic can be split later if there is a real scaling reason.

## Agent design

The LangGraph workflow first classifies the latest guest request into one of four intents. Each branch gets only the tools it needs. Tool results are returned to the same branch so the model can turn structured backend results into a natural response.

This makes the workflow easy to explain in an interview and avoids giving every request every tool.

## RAG design

Hotel FAQs and menu content are chunked and embedded during seeding. Embeddings are stored in PostgreSQL with pgvector. Retrieval is filtered by `hotel_id` before ordering by cosine distance.

For a multi-hotel version, the same `hotel_id` boundary can be used throughout the relational and vector data model.

## What to scale later

Only add these if you actually implement and measure the need:

- Redis for caching and shared agent/session state
- background workers for emails and reminders
- persistent LangGraph checkpointing
- JWT/RBAC for staff roles
- multi-tenant hotel onboarding
- WebSocket updates for the operations dashboard
- human approval for refunds or complimentary upgrades
