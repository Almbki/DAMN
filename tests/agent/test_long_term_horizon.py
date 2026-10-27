"""API/persistence horizon regression for long-term recurring goals.

A 30-day daily goal must survive the whole pipeline (preview -> confirm -> GET
plan). The API returns every task; any 7-day limit is a UI view concern, never a
recurrence-lifecycle truncation.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.agent.conftest import override_plan_service, preview_of


def test_30_day_daily_goal_is_fully_persisted_and_returned(
    client: TestClient, auth_headers: dict
) -> None:
    override_plan_service(client)
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=29)
    payload = {
        "goals": [
            {
                "title": "每天背考研英语单词",
                "goal_type": "habit",
                "task_kind": "routine",
                "start_date": start.isoformat(),
                "deadline": end.isoformat(),
                "daily_target_minutes": 20,
            }
        ],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }

    body = preview_of(client, auth_headers, payload)
    preview_tasks = body["preview"]["tasks"]
    expected_days = [start + timedelta(days=offset) for offset in range(30)]

    assert len(preview_tasks) == 30
    assert [task["occurrence_date"] for task in preview_tasks] == [
        day.isoformat() for day in expected_days
    ]
    assert [task["scheduled_date"] for task in preview_tasks] == [
        day.isoformat() for day in expected_days
    ]

    confirmed = client.post(
        f"/api/v1/plans/preview/{body['thread_id']}/confirm",
        headers=auth_headers,
    )
    assert confirmed.status_code == 201, confirmed.text
    plan = confirmed.json()["plan"]

    # The plan metadata covers the real lifecycle, not today + 13.
    assert plan["end_date"] == end.isoformat()

    fetched = client.get(f"/api/v1/plans/{plan['id']}", headers=auth_headers)
    assert fetched.status_code == 200, fetched.text
    persisted = fetched.json()["tasks"]

    assert len(persisted) == 30
    assert {task["series_id"] for task in persisted} == {"goal-1-routine"}
    assert [task["occurrence_date"] for task in persisted] == [
        day.isoformat() for day in expected_days
    ]
    # Prove there is data beyond the first week (the old symptom was exactly 7).
    later_than_week = [
        task for task in persisted if task["occurrence_date"] > expected_days[6].isoformat()
    ]
    assert len(later_than_week) == 23
