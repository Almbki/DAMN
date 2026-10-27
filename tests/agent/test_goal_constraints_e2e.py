"""End-to-end: explicit earliest dates and persisted goal ids across replan."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.domain.feedback.models import AdjustmentRoute, AdjustmentSeverity
from tests.agent.conftest import override_plan_service, preview_of
from tests.support import replan_and_wait


def _date(value: str) -> date:
    return date.fromisoformat(value)


def test_initial_and_full_replan_respect_dates_and_goal_scope(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(
        client,
        route=AdjustmentRoute.FULL_REPLAN,
        severity=AdjustmentSeverity.HIGH,
    )
    today = date.today()
    base = today + timedelta(days=4)
    earliest = base + timedelta(days=1)
    cet_deadline = base + timedelta(days=6)
    damn_deadline = today + timedelta(days=1)
    cet_text = f"安排在{base.year}年{base.month}月{base.day}日之后"

    payload = {
        "goals": [
            {
                "title": "完成 DAMN 项目省赛版本开发",
                "planning_mode": "one_off",
                "deadline": damn_deadline.isoformat(),
                "estimated_minutes": 60,
            },
            {
                "title": "为同学撰写 CET4/6 焚决",
                "description": cet_text,
                "planning_mode": "one_off",
                "deadline": cet_deadline.isoformat(),
                "estimated_minutes": 120,
            },
        ],
        "start_date": today.isoformat(),
        "end_date": cet_deadline.isoformat(),
        "daily_limit_minutes": 60,
    }

    preview = preview_of(client, auth_headers, payload)
    preview_tasks = preview["preview"]["tasks"]
    preview_cet = [task for task in preview_tasks if "CET" in task["title"]]
    preview_damn = [task for task in preview_tasks if "DAMN" in task["title"]]

    assert preview_cet and preview_damn
    # Chunking must preserve the lower bound on every chunk (120 -> 2 x 60).
    assert len(preview_cet) >= 2
    assert all(task["goal_id"] == 2 for task in preview_cet)
    assert all(task["goal_id"] == 1 for task in preview_damn)
    for task in preview_cet:
        assert task["scheduled_date"] is not None
        assert earliest <= _date(task["scheduled_date"]) <= cet_deadline
    for task in preview_damn:
        assert task["scheduled_date"] is not None
        assert _date(task["scheduled_date"]) < earliest

    confirmed = client.post(
        f"/api/v1/plans/preview/{preview['thread_id']}/confirm",
        headers=auth_headers,
    )
    assert confirmed.status_code == 201, confirmed.text
    old_plan = confirmed.json()["plan"]
    old_plan_id = old_plan["id"]
    goal_by_title = {goal["title"]: goal["id"] for goal in old_plan["goals"]}
    cet_goal_id = goal_by_title["为同学撰写 CET4/6 焚决"]
    damn_goal_id = goal_by_title["完成 DAMN 项目省赛版本开发"]

    old_tasks = old_plan["tasks"]
    old_cet = [task for task in old_tasks if "CET" in task["title"]]
    old_damn = [task for task in old_tasks if "DAMN" in task["title"]]
    assert all(task["goal_id"] == cet_goal_id for task in old_cet)
    assert all(task["goal_id"] == damn_goal_id for task in old_damn)
    for task in old_cet:
        assert earliest <= _date(task["scheduled_date"]) <= cet_deadline
    old_snapshot = sorted(
        (task["id"], task["scheduled_date"], task["goal_id"]) for task in old_tasks
    )

    replanned = replan_and_wait(
        client, auth_headers, old_plan_id, {"reason": "date regression"}
    )
    new_plan_id = replanned["plan_id"]
    new_plan = client.get(
        f"/api/v1/plans/{new_plan_id}", headers=auth_headers
    ).json()
    new_goal_by_title = {goal["title"]: goal["id"] for goal in new_plan["goals"]}
    new_cet_goal_id = new_goal_by_title["为同学撰写 CET4/6 焚决"]
    assert new_cet_goal_id == cet_goal_id

    new_cet = [task for task in new_plan["tasks"] if "CET" in task["title"]]
    assert new_cet
    for task in new_cet:
        assert task["scheduled_date"] is not None
        assert earliest <= _date(task["scheduled_date"]) <= cet_deadline
        assert task["goal_id"] == cet_goal_id

    # The old version remains immutable history.
    old_again = client.get(
        f"/api/v1/plans/{old_plan_id}", headers=auth_headers
    ).json()
    assert (
        sorted(
            (task["id"], task["scheduled_date"], task["goal_id"])
            for task in old_again["tasks"]
        )
        == old_snapshot
    )


def test_replan_keeps_real_goal_ids_beyond_request_count(
    client: TestClient, auth_headers: dict
) -> None:
    """Two request goals with database ids > 2 must still map to themselves."""
    # Consume a few goal ids so the plan's real ids are larger than N=2.
    for index in range(3):
        created = client.post(
            "/api/v1/goals",
            json={"title": f"placeholder-{index}", "status": "draft"},
            headers=auth_headers,
        )
        assert created.status_code == 201, created.text

    override_plan_service(
        client,
        route=AdjustmentRoute.FULL_REPLAN,
        severity=AdjustmentSeverity.HIGH,
    )
    start = date.today() + timedelta(days=1)
    payload = {
        "goals": [
            {
                "title": "goal A",
                "planning_mode": "one_off",
                "deadline": start.isoformat(),
                "estimated_minutes": 30,
            },
            {
                "title": "goal B",
                "planning_mode": "one_off",
                "deadline": (start + timedelta(days=3)).isoformat(),
                "estimated_minutes": 30,
            },
        ],
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=3)).isoformat(),
    }
    preview = preview_of(client, auth_headers, payload)
    confirmed = client.post(
        f"/api/v1/plans/preview/{preview['thread_id']}/confirm",
        headers=auth_headers,
    )
    assert confirmed.status_code == 201, confirmed.text
    old_plan = confirmed.json()["plan"]
    real_ids = {goal["title"]: goal["id"] for goal in old_plan["goals"]}
    assert set(real_ids) == {"goal A", "goal B"}
    assert all(goal_id > 2 for goal_id in real_ids.values())

    replanned = replan_and_wait(
        client, auth_headers, old_plan["id"], {"reason": "identity regression"}
    )
    new_plan = client.get(
        f"/api/v1/plans/{replanned['plan_id']}", headers=auth_headers
    ).json()
    new_real_ids = {goal["title"]: goal["id"] for goal in new_plan["goals"]}
    assert new_real_ids == real_ids
    for task in new_plan["tasks"]:
        assert task["goal_id"] == real_ids[task["title"]]
