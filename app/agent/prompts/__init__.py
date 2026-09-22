"""Prompt loading.

Prompts live as Markdown files next to this module so behaviour can be changed
without touching Python. Each file starts with a YAML-ish front-matter block:

```
---
purpose: ...
input_variables: a, b
expected_output: SomeSchema
constraints: ...
when_used: ...
---
body with {{placeholders}}
```

Nodes do ``load_prompt("goal_analysis").render(goals=..., user_profile=...)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class PromptTemplate:
    """A prompt plus its documented metadata."""

    name: str
    body: str
    meta: dict[str, str]
    path: Path

    def render(self, **variables: object) -> str:
        """Substitute ``{{var}}`` placeholders; unknown ones are left untouched."""
        missing = set(self.required_variables) - set(variables)

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                return match.group(0)
            value = variables[key]
            return value if isinstance(value, str) else repr(value)

        rendered = _PLACEHOLDER_RE.sub(replace, self.body)
        if missing:
            rendered += f"\n\n[missing input variables: {', '.join(sorted(missing))}]"
        return rendered

    @property
    def required_variables(self) -> list[str]:
        return [v.strip() for v in self.meta.get("input_variables", "").split(",") if v.strip()]

    @property
    def version(self) -> str:
        return self.meta.get("version", "v1")


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, text[match.end() :]


@lru_cache(maxsize=64)
def load_prompt(name: str) -> PromptTemplate:
    """Load and cache a prompt by file stem, e.g. ``load_prompt("goal_analysis")``."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))
    return PromptTemplate(name=name, body=body.strip(), meta=meta, path=path)


def list_prompts() -> list[str]:
    """All available prompt names (sorted)."""
    return sorted(path.stem for path in PROMPTS_DIR.glob("*.md"))


def clear_prompt_cache() -> None:
    """Drop the cache (used by tests after editing prompt files)."""
    load_prompt.cache_clear()


__all__ = [
    "PROMPTS_DIR",
    "PromptTemplate",
    "clear_prompt_cache",
    "list_prompts",
    "load_prompt",
]
