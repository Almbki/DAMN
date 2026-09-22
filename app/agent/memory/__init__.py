"""Memory layers.

The agent consumes three structured memory kinds (no vector database):

* :mod:`app.agent.memory.semantic`  - stable facts / preferences / abilities
* :mod:`app.agent.memory.episodic`  - concrete execution events
* :mod:`app.agent.memory.procedural` - scheduling rules of thumb

These modules are pure functions over domain rows. The *database read* lives in
``app.application.context.RepoContextBuilder`` so no agent node touches a
session or a repository (see docs/agent/memory.md).
"""

from app.agent.memory.episodic import build_episodic_memory
from app.agent.memory.procedural import derive_procedural_memory
from app.agent.memory.semantic import build_semantic_memory

__all__ = [
    "build_episodic_memory",
    "build_semantic_memory",
    "derive_procedural_memory",
]
