"""Infrastructure layer - adapters to the outside world.

Contains database access (engine, ORM models, repositories), LLM HTTP access
and the ML model store. Domain code never imports this package; only
Application/Service and edge-code (API, CLI) may.
"""