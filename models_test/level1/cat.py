"""Trait Model V1: independent Bayesian CAT for the five IPIP-NEO-120 domains.

The GRM parameters are fixed at artifacts/grm_parameters.json (grm_v1).  This
module only performs posterior updating, EAP estimation, item selection and
stopping.  It does not fit or modify the GRM.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
DEFAULT_PARAMS = ROOT / "artifacts" / "grm_parameters.json"
DEFAULT_CONFIG = ROOT / "artifacts" / "cat_config.json"

DOMAIN_ORDER = ["N", "E", "O", "A", "C"]
DOMAIN_NAMES = {
    "N": "Neuroticism",
    "E": "Extraversion",
    "O": "Openness",
    "A": "Agreeableness",
    "C": "Conscientiousness",
}
EPS = 1e-12


@dataclass(frozen=True)
class CATConfig:
    min_items: int = 4
    max_items: int = 12
    target_se: float = 0.35
    prior_mean: float = 0.0
    prior_sd: float = 1.0
    grid_min: float = -6.0
    grid_max: float = 6.0
    grid_n: int = 161
    ci_level: float = 0.95
    estimator: str = "EAP"
    item_selection: str = "max_fisher_information_at_eap"
    ci_method: str = "posterior_quantile"
    model: str = "samejima_grm"
    calibration_version: str = "grm_v1"
    schema_version: str = "1.0"

    @property
    def grid(self) -> np.ndarray:
        return np.linspace(self.grid_min, self.grid_max, self.grid_n)

    @property
    def prior_log(self) -> np.ndarray:
        grid = self.grid
        logp = -0.5 * ((grid - self.prior_mean) / self.prior_sd) ** 2
        logp -= math.log(self.prior_sd * math.sqrt(2.0 * math.pi))
        logp -= logp.max()
        logp -= math.log(np.exp(logp).sum())
        return logp

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> CATConfig:
        path = Path(path) if path is not None else DEFAULT_CONFIG
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        prior = data.get("prior", {})
        grid = data.get("posterior_grid", {})
        return cls(
            min_items=int(data.get("min_items", 4)),
            max_items=int(data.get("max_items", 12)),
            target_se=float(data.get("target_se", 0.35)),
            prior_mean=float(prior.get("mean", 0.0)),
            prior_sd=float(prior.get("sd", 1.0)),
            grid_min=float(grid.get("min", -6.0)),
            grid_max=float(grid.get("max", 6.0)),
            grid_n=int(grid.get("n", 161)),
            ci_level=float(data.get("ci_level", 0.95)),
            estimator=str(data.get("estimator", "EAP")),
            item_selection=str(data.get("item_selection", "max_fisher_information_at_eap")),
            ci_method=str(data.get("ci_method", "posterior_quantile")),
            model=str(data.get("calibration", {}).get("model", "samejima_grm")),
            calibration_version=str(data.get("calibration", {}).get("version", "grm_v1")),
            schema_version=str(data.get("schema_version", "1.0")),
        )


def load_grm_parameters(path: str | Path | None = None) -> dict:
    path = Path(path) if path is not None else DEFAULT_PARAMS
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("model") != "GRM":
        raise ValueError(f"expected GRM parameters, got {data.get('model')!r}")
    if set(data.get("domains", {})) != set(DOMAIN_ORDER):
        raise ValueError("GRM parameter file must contain N/E/O/A/C")
    return data


def _sigmoid(x: Any) -> np.ndarray:
    """Numerically stable logistic function without a SciPy dependency."""
    x = np.asarray(x, dtype=np.float64)
    out = np.empty_like(x, dtype=np.float64)
    positive = x >= 0.0
    out[positive] = 1.0 / (1.0 + np.exp(-x[positive]))
    exp_x = np.exp(x[~positive])
    out[~positive] = exp_x / (1.0 + exp_x)
    return out


def category_probabilities(
    theta: Any, a: float, thresholds: Iterable[float]
) -> np.ndarray:
    """Standard Samejima GRM category probabilities for categories 1..5."""
    theta_arr = np.asarray(theta, dtype=np.float64)
    b = np.asarray(list(thresholds), dtype=np.float64)
    if b.shape != (4,):
        raise ValueError("GRM thresholds must have length 4")
    # cumulative P(Y >= k+1) for k=1..4
    s = _sigmoid(a * (theta_arr[..., None] - b))
    p1 = 1.0 - s[..., 0]
    p2 = s[..., 0] - s[..., 1]
    p3 = s[..., 1] - s[..., 2]
    p4 = s[..., 2] - s[..., 3]
    p5 = s[..., 3]
    probs = np.stack([p1, p2, p3, p4, p5], axis=-1)
    probs = np.clip(probs, 0.0, None)
    total = probs.sum(axis=-1, keepdims=True)
    total = np.clip(total, EPS, None)
    return probs / total


def item_information(theta: float, a: float, thresholds: Iterable[float]) -> float:
    """Fisher information for one GRM item at theta."""
    b = np.asarray(list(thresholds), dtype=np.float64)
    s = _sigmoid(a * (theta - b))
    ds = a * s * (1.0 - s)
    p = np.array(
        [
            1.0 - s[0],
            s[0] - s[1],
            s[1] - s[2],
            s[2] - s[3],
            s[3],
        ],
        dtype=np.float64,
    )
    dp = np.array([-ds[0], ds[0] - ds[1], ds[1] - ds[2], ds[2] - ds[3], ds[3]])
    p = np.clip(p, EPS, None)
    return float(np.sum(dp * dp / p))


def posterior_summary(
    log_post: np.ndarray, grid: np.ndarray, ci_level: float = 0.95
):
    """Return EAP theta, posterior SD, and posterior quantile CI.

    Supports a single posterior (1-D) and a batch of posteriors (2-D).
    """
    log_post = np.asarray(log_post, dtype=np.float64)
    m = np.max(log_post, axis=-1, keepdims=True)
    weights = np.exp(log_post - m)
    weights /= weights.sum(axis=-1, keepdims=True)
    theta = np.sum(weights * grid, axis=-1)
    variance = np.sum(weights * (grid - theta[..., None]) ** 2, axis=-1)
    se = np.sqrt(np.clip(variance, 0.0, None))
    se = np.maximum(se, 1e-6)

    alpha = (1.0 - ci_level) / 2.0
    cdf = np.cumsum(weights, axis=-1)
    if weights.ndim == 1:
        lo = float(grid[min(int(np.searchsorted(cdf, alpha)), len(grid) - 1)])
        hi = float(grid[min(int(np.searchsorted(cdf, 1.0 - alpha)), len(grid) - 1)])
        return float(theta), float(se), (lo, hi)

    lo_idx = np.clip((cdf < alpha).sum(axis=-1), 0, len(grid) - 1)
    hi_idx = np.clip((cdf < 1.0 - alpha).sum(axis=-1), 0, len(grid) - 1)
    return theta, se, (grid[lo_idx], grid[hi_idx])


@dataclass
class DomainState:
    domain: str
    items: list[str]
    params: dict[str, dict]
    log_post: np.ndarray
    theta: float = 0.0
    se: float = 1.0
    ci95: tuple[float, float] = (-1.96, 1.96)
    administered: list[str] = field(default_factory=list)
    responses: dict[str, int] = field(default_factory=dict)
    unavailable: set[str] = field(default_factory=set)
    items_answered: int = 0
    stopped: bool = False
    stop_reason: str | None = None


@dataclass
class CATSession:
    config: CATConfig
    calibration: dict
    states: dict[str, DomainState]
    rr_index: int = 0
    completed: bool = False
    last_domain: str | None = None


def _make_session(config: CATConfig, params: dict) -> CATSession:
    states: dict[str, DomainState] = {}
    for domain in DOMAIN_ORDER:
        items = list(params["domains"][domain]["items"].keys())
        states[domain] = DomainState(
            domain=domain,
            items=items,
            params=params["domains"][domain]["items"],
            log_post=config.prior_log.copy(),
        )
    calibration = {
        "model": config.model,
        "version": config.calibration_version,
        "reference_population": "Johnson_IPIP_NEO_120",
    }
    return CATSession(config=config, calibration=calibration, states=states)


def start_assessment(
    config: CATConfig | None = None, params_path: str | Path | None = None
) -> CATSession:
    params = load_grm_parameters(params_path)
    return _make_session(config or CATConfig.from_json(), params)


def _find_state(session: CATSession, item_id: str) -> DomainState:
    for state in session.states.values():
        if item_id in state.params:
            return state
    raise KeyError(f"unknown item_id: {item_id}")


def get_next_item(
    session: CATSession, available_item_ids: Iterable[str] | None = None
) -> str | None:
    """Return the next item using domain round-robin and max Fisher information."""
    available = set(available_item_ids) if available_item_ids is not None else None
    for _ in range(len(DOMAIN_ORDER)):
        domain = DOMAIN_ORDER[session.rr_index]
        session.rr_index = (session.rr_index + 1) % len(DOMAIN_ORDER)
        state = session.states[domain]
        if state.stopped:
            continue
        candidates = [
            item_id
            for item_id in state.items
            if item_id not in state.responses
            and item_id not in state.unavailable
            and (available is None or item_id in available)
        ]
        if not candidates:
            state.stopped = True
            state.stop_reason = "no_available_items"
            continue
        info = [
            (item_information(state.theta, state.params[i]["a"], state.params[i]["thresholds"]), i)
            for i in candidates
        ]
        info.sort(key=lambda x: (-x[0], x[1]))
        session.last_domain = domain
        return info[0][1]

    if all(state.stopped for state in session.states.values()):
        session.completed = True
    return None


def submit_response(session: CATSession, item_id: str, response: int) -> dict:
    state = _find_state(session, item_id)
    if state.stopped:
        raise ValueError(f"domain {state.domain} is already stopped")
    if item_id in state.responses:
        raise ValueError(f"item {item_id} was already answered")
    if isinstance(response, bool) or not isinstance(response, (int, np.integer)):
        raise ValueError("response must be an integer 1..5")
    response = int(response)
    if response < 1 or response > 5:
        raise ValueError("response must be in 1..5")

    grid = session.config.grid
    probs = category_probabilities(grid, state.params[item_id]["a"], state.params[item_id]["thresholds"])
    likelihood = np.clip(probs[:, response - 1], EPS, None)
    state.log_post = state.log_post + np.log(likelihood)
    state.log_post -= state.log_post.max()
    state.log_post -= math.log(np.exp(state.log_post).sum())

    state.theta, state.se, state.ci95 = posterior_summary(
        state.log_post, grid, session.config.ci_level
    )
    state.administered.append(item_id)
    state.responses[item_id] = response
    state.items_answered += 1

    if state.items_answered >= session.config.min_items and state.se <= session.config.target_se:
        state.stopped = True
        state.stop_reason = "target_se"
    elif state.items_answered >= session.config.max_items:
        state.stopped = True
        state.stop_reason = "max_items"

    if all(s.stopped for s in session.states.values()):
        session.completed = True

    return {
        "item_id": item_id,
        "domain": state.domain,
        "response": response,
        "theta": state.theta,
        "se": state.se,
        "items_answered": state.items_answered,
        "stopped": state.stopped,
        "stop_reason": state.stop_reason,
    }


def mark_item_unavailable(session: CATSession, item_id: str) -> None:
    state = _find_state(session, item_id)
    state.unavailable.add(item_id)


def get_trait_profile(session: CATSession) -> dict:
    domains = {}
    for domain in DOMAIN_ORDER:
        state = session.states[domain]
        domains[domain] = {
            "theta": round(float(state.theta), 6),
            "se": round(float(state.se), 6),
            "ci95": [round(float(state.ci95[0]), 6), round(float(state.ci95[1]), 6)],
            "items_answered": int(state.items_answered),
        }
    return {
        "schema_version": "1.0",
        "model": "trait_v1",
        "instrument": "IPIP-NEO-120",
        "method": "bayesian_cat",
        "calibration": session.calibration,
        "domains": domains,
        "assessment": {
            "total_items_answered": int(sum(s.items_answered for s in session.states.values())),
            "completed": bool(all(s.stopped for s in session.states.values())),
        },
    }
