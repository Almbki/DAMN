"""Frontend contract tests: decompose/confirm, preferences, trends, changes, goals.

These exercise the endpoints the frontend added after its refactor, against the
default dependency wiring (no overrides), so they also cover the production path.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

_ONE_GOAL = [
    {
        "title": "复习高数极限",
        "description": "看课\n做例题",
        "subject": "math",
        "estimated_minutes": 120,
        "priority": 3,
    }
]


def _decompose(client: TestClient, headers: dict, goals: list[dict], **extra) -> dict:
    return client.post(
        "/api/v1/plans/decompose", json={"goals": goals, **extra}, headers=headers
    )


# ---------------------------------------------------------------------------
# Scheduling preferences
# ---------------------------------------------------------------------------
def test_preferences_defaults_then_roundtrip(client: TestClient, auth_headers: dict) -> None:
    initial = client.get("/api/v1/users/me/preferences", headers=auth_headers)
    assert initial.status_code == 200, initial.text
    assert initial.json() == {
        "available_minutes_per_day": 480,
        "daily_limit_minutes": 300,
        "buffer_minutes": 15,
        "high_cognitive_max_per_day": 2,
        "sleep_start": None,
        "sleep_end": None,
    }

    updated = client.put(
        "/api/v1/users/me/preferences",
        json={
            "available_minutes_per_day": 240,
            "daily_limit_minutes": 120,
            "buffer_minutes": 20,
            "high_cognitive_max_per_day": 1,
            "sleep_start": "23:30",
            "sleep_end": "07:00",
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["daily_limit_minutes"] == 120

    reread = client.get("/api/v1/users/me/preferences", headers=auth_headers)
    assert reread.json()["daily_limit_minutes"] == 120
    assert reread.json()["sleep_start"] == "23:30"


def test_profile_patch_does_not_wipe_preferences(
    client: TestClient, auth_headers: dict
) -> None:
    """The whole reason preferences live on their own column."""
    client.put(
        "/api/v1/users/me/preferences",
        json={
            "available_minutes_per_day": 240,
            "daily_limit_minutes": 120,
            "buffer_minutes": 20,
            "high_cognitive_max_per_day": 1,
        },
        headers=auth_headers,
    )
    patched = client.patch(
        "/api/v1/users/me",
        json={"profile": {"mbti": "INTJ"}},  # wholesale profile overwrite
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text

    after = client.get("/api/v1/users/me/preferences", headers=auth_headers)
    assert after.json()["daily_limit_minutes"] == 120


def test_bad_sleep_time_is_rejected(client: TestClient, auth_headers: dict) -> None:
    response = client.put(
        "/api/v1/users/me/preferences",
        json={
            "available_minutes_per_day": 240,
            "daily_limit_minutes": 120,
            "buffer_minutes": 20,
            "high_cognitive_max_per_day": 1,
            "sleep_start": "25:99",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def _dated_minutes(plan: dict) -> dict[str, int]:
    totals: dict[str, int] = {}
    for task in plan["tasks"]:
        if not task["scheduled_date"]:
            continue
        totals[task["scheduled_date"]] = totals.get(task["scheduled_date"], 0) + task[
            "estimated_duration"
        ]
    return totals


def test_generate_falls_back_to_stored_preferences(
    client: TestClient, auth_headers: dict
) -> None:
    """A 60-minute day cannot host a 120-minute task -> it stays unscheduled."""
    client.put(
        "/api/v1/users/me/preferences",
        json={
            "available_minutes_per_day": 60,
            "daily_limit_minutes": 60,
            "buffer_minutes": 15,
            "high_cognitive_max_per_day": 2,
        },
        headers=auth_headers,
    )
    generated = client.post(
        "/api/v1/plans/generate", json={"goals": _ONE_GOAL}, headers=auth_headers
    )
    assert generated.status_code == 202, generated.text
    plan = generated.json()["plan"]
    assert _dated_minutes(plan) == {}


def test_generate_request_overrides_stored_preferences(
    client: TestClient, auth_headers: dict
) -> None:
    """Explicitly sending the cap must win over the stored 60-minute day."""
    client.put(
        "/api/v1/users/me/preferences",
        json={
            "available_minutes_per_day": 60,
            "daily_limit_minutes": 60,
            "buffer_minutes": 15,
            "high_cognitive_max_per_day": 2,
        },
        headers=auth_headers,
    )
    generated = client.post(
        "/api/v1/plans/generate",
        json={
            "goals": _ONE_GOAL,
            "available_minutes_per_day": 480,
            "daily_limit_minutes": 600,
        },
        headers=auth_headers,
    )
    assert generated.status_code == 202, generated.text
    totals = _dated_minutes(generated.json()["plan"])
    assert totals, "the request override should have made the task schedulable"
    assert max(totals.values()) > 60


# ---------------------------------------------------------------------------
# decompose -> confirm
# ---------------------------------------------------------------------------
def test_decompose_returns_days_and_confirm_persists(
    client: TestClient, auth_headers: dict
) -> None:
    decomposed = _decompose(client, auth_headers, _ONE_GOAL)
    assert decomposed.status_code == 200, decomposed.text
    body = decomposed.json()
    assert body["draft_id"]
    assert body["days"], "a draft must group tasks by day"

    first_day = body["days"][0]
    task = first_day["tasks"][0]
    assert task["title"]
    assert 1 <= task["priority"] <= 3
    assert task["estimated_minutes"] >= 1
    assert task["source_index"] == 0

    confirmed = client.post(
        "/api/v1/plans/confirm", json={"draft_id": body["draft_id"]}, headers=auth_headers
    )
    assert confirmed.status_code == 200, confirmed.text
    plan = confirmed.json()
    assert plan["version"] == 1
    assert plan["tasks"]

    # Confirming twice is a conflict, not a second plan.
    again = client.post(
        "/api/v1/plans/confirm", json={"draft_id": body["draft_id"]}, headers=auth_headers
    )
    assert again.status_code == 409


def test_confirm_unknown_draft_is_404(client: TestClient, auth_headers: dict) -> None:
    response = client.post(
        "/api/v1/plans/confirm", json={"draft_id": "does-not-exist"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_decompose_regenerate_then_hit_budget(
    client: TestClient, auth_headers: dict
) -> None:
    draft_id = _decompose(client, auth_headers, _ONE_GOAL).json()["draft_id"]

    for _ in range(3):  # AGENT_MAX_PREVIEW_ADJUSTMENTS = 3
        regenerated = _decompose(
            client, auth_headers, _ONE_GOAL, draft_id=draft_id, feedback="少一点"
        )
        assert regenerated.status_code == 200, regenerated.text
        assert regenerated.json()["draft_id"] == draft_id

    exhausted = _decompose(
        client, auth_headers, _ONE_GOAL, draft_id=draft_id, feedback="再少一点"
    )
    assert exhausted.status_code == 409
    assert "调整次数" in exhausted.json()["message"]


def test_decompose_supports_several_goals(client: TestClient, auth_headers: dict) -> None:
    goals = [
        {"title": "复习高数极限", "priority": 3, "notes": "看课\n做例题"},
        {"title": "准备汇报", "priority": 2, "notes": "写大纲\n做 PPT"},
    ]
    body = _decompose(client, auth_headers, goals).json()
    source_indices = {
        task["source_index"] for day in body["days"] for task in day["tasks"]
    }
    assert source_indices == {0, 1}


# ---------------------------------------------------------------------------
# situation trends
# ---------------------------------------------------------------------------
def test_situation_trends_shape(client: TestClient, auth_headers: dict) -> None:
    response = client.get(
        "/api/v1/users/me/situation/trends?days=14", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert len(body["points"]) == 14
    assert body["samples"] == 0
    assert body["min_samples"] > 0
    assert body["sufficient"] is False
    assert body["drivers"], "the profile page needs an explanation even when empty"
    assert all(point["energy"] is None for point in body["points"])


def test_situation_trends_rejects_out_of_range_days(
    client: TestClient, auth_headers: dict
) -> None:
    assert (
        client.get("/api/v1/users/me/situation/trends?days=500", headers=auth_headers).status_code
        == 422
    )


# ---------------------------------------------------------------------------
# plan changes
# ---------------------------------------------------------------------------
def test_plan_changes_after_a_replan(client: TestClient, auth_headers: dict) -> None:
    generated = client.post(
        "/api/v1/plans/generate", json={"goals": _ONE_GOAL}, headers=auth_headers
    )
    plan_id = generated.json()["plan_id"]

    empty = client.get(f"/api/v1/plans/{plan_id}/changes", headers=auth_headers)
    assert empty.status_code == 200
    assert empty.json() == []

    replanned = client.post(
        f"/api/v1/plans/{plan_id}/replan",
        json={"reason": "manual replan"},
        headers=auth_headers,
    )
    assert replanned.status_code == 201, replanned.text
    new_plan_id = replanned.json()["plan_id"]

    changes = client.get(f"/api/v1/plans/{new_plan_id}/changes", headers=auth_headers)
    assert changes.status_code == 200
    events = changes.json()
    assert len(events) == 1
    event = events[0]
    assert event["old_version"] == 1 and event["new_version"] == 2
    assert event["trigger_type"] == "manual"
    for day in event["days"]:
        assert set(day) >= {"date", "added", "moved", "removed", "summary", "task_ids"}
        assert day["summary"]


# ---------------------------------------------------------------------------
# insights extension
# ---------------------------------------------------------------------------
def test_insights_report_sufficiency_and_drivers(
    client: TestClient, auth_headers: dict
) -> None:
    generated = client.post(
        "/api/v1/plans/generate", json={"goals": _ONE_GOAL}, headers=auth_headers
    )
    plan_id = generated.json()["plan_id"]

    response = client.get(f"/api/v1/plans/{plan_id}/insights", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["data_sufficiency"]["sufficient"] is False
    assert body["data_sufficiency"]["min_samples"] > 0
    assert body["drivers"]


# ---------------------------------------------------------------------------
# goals CRUD
# ---------------------------------------------------------------------------
def test_goals_crud(client: TestClient, auth_headers: dict) -> None:
    created = client.post(
        "/api/v1/goals",
        json={"title": "待拆解：准备汇报", "description": "补充说明", "status": "draft"},
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    goal = created.json()
    assert goal["status"] == "draft"
    goal_id = goal["id"]

    drafts = client.get("/api/v1/goals?status=draft", headers=auth_headers)
    assert [item["id"] for item in drafts.json()] == [goal_id]

    patched = client.patch(
        f"/api/v1/goals/{goal_id}",
        json={"title": "准备汇报", "priority": 4, "status": "active"},
        headers=auth_headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["title"] == "准备汇报"
    assert patched.json()["status"] == "active"

    assert client.get("/api/v1/goals?status=draft", headers=auth_headers).json() == []

    deleted = client.delete(f"/api/v1/goals/{goal_id}", headers=auth_headers)
    assert deleted.status_code == 204

    missing = client.patch(
        f"/api/v1/goals/{goal_id}", json={"title": "x"}, headers=auth_headers
    )
    assert missing.status_code == 404


def test_goals_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/goals").status_code == 401


def test_goal_delete_conflicts_when_plan_references_it(
    client: TestClient, auth_headers: dict
) -> None:
    """A goal used by a plan task cannot be deleted (FK integrity)."""
    generated = client.post(
        "/api/v1/plans/generate", json={"goals": _ONE_GOAL}, headers=auth_headers
    )
    plan_id = generated.json()["plan_id"]
    goal_id = client.get(f"/api/v1/plans/{plan_id}", headers=auth_headers).json()["goals"][0][
        "id"
    ]

    response = client.delete(f"/api/v1/goals/{goal_id}", headers=auth_headers)
    assert response.status_code == 409
