"""Stage-6 mechanism check: simulated personas through the real HTTP loop.

Five synthetic personas (the canned scenario fixtures) run through the real
API: register -> import observations -> generate a plan with the phase-4
scheduler -> seven simulated days of execution + evening feedback (postpone /
micro / full routes). Aggregated metrics are printed as a markdown table and
saved under .tmp/simulation/.

MECHANISM check only: the personas are synthetic and there is no real
long-term user data here, so nothing below is evidence of prediction accuracy.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM_DIR = ROOT / ".tmp" / "simulation"
SIM_DIR.mkdir(parents=True, exist_ok=True)
SIM_DB = SIM_DIR / "sim.db"
if SIM_DB.exists():
    SIM_DB.unlink()

# Configure the app BEFORE importing it (settings are cached on first use).
os.environ["DATABASE_URL"] = f"sqlite:///{SIM_DB.as_posix()}"
os.environ["JWT_SECRET_KEY"] = "stage6-simulation-secret-key-0123456789"
os.environ["ENVIRONMENT"] = "test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ENABLE_SYNTHETIC_IMPORT"] = "true"
os.environ["PASSWORD_HASH_ITERATIONS"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DAY_COUNT = 7
PERSONAS: dict[str, dict] = {
    "stable_executor": {"label": "稳定执行者", "completion": 0.9, "partial": 0.05, "stress": 3, "energy": 8, "ratio": 1.0},
    "recovery": {"label": "恢复期使用者", "completion": 0.6, "partial": 0.1, "stress": 6, "energy": 5, "ratio": 1.1},
    "deadline_stress": {"label": "截止压力型", "completion": 0.65, "partial": 0.1, "stress": 7, "energy": 5, "ratio": 1.4},
    "overload": {"label": "超载型", "completion": 0.35, "partial": 0.2, "stress": 8, "energy": 3, "ratio": 1.25},
    "procrastination": {"label": "拖延型", "completion": 0.45, "partial": 0.15, "stress": 5, "energy": 6, "ratio": 1.15},
}


def _wait_job(client: TestClient, headers: dict, job_id: str, timeout: float = 120.0) -> dict:
    deadline = time.time() + timeout
    while True:
        body = client.get(f"/api/v1/plans/generation/{job_id}", headers=headers).json()
        if body["status"] in {"completed", "failed"}:
            return body
        if time.time() > deadline:
            raise RuntimeError("generation job did not finish in time")
        time.sleep(0.05)


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Sim"},
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": "Bearer " + login.json()["access_token"]}


def _generate_plan(client: TestClient, headers: dict, today: date) -> dict:
    payload = {
        "goals": [
            {"title": "高数复习", "estimated_minutes": 120, "priority": 3,
             "start_date": today.isoformat(), "deadline": (today + timedelta(days=6)).isoformat()},
            {"title": "英语阅读", "estimated_minutes": 60, "priority": 2,
             "start_date": today.isoformat()},
            {"title": "课程项目", "estimated_minutes": 90, "priority": 2,
             "start_date": today.isoformat(), "deadline": (today + timedelta(days=3)).isoformat()},
        ],
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=6)).isoformat(),
    }
    accepted = client.post("/api/v1/plans/generate", json=payload, headers=headers)
    assert accepted.status_code == 202, accepted.text
    result = _wait_job(client, headers, accepted.json()["job_id"])
    assert result["status"] == "completed", result
    return result["result"]


def _active_plan(client: TestClient, headers: dict):
    for plan in client.get("/api/v1/plans", headers=headers).json():
        if plan.get("status") == "active":
            detail = client.get("/api/v1/plans/" + str(plan["id"]), headers=headers)
            if detail.status_code == 200:
                return detail.json()
    return None


def _patch_task(client: TestClient, headers: dict, plan_id: int, task: dict, outcome: str, ratio: float) -> dict:
    estimated = int(task.get("estimated_duration") or 60)
    actual = max(1, int(round(estimated * ratio)))
    if outcome == "completed":
        body = {"completed": True, "actual_duration": actual,
                "finished_at": datetime.now().astimezone().isoformat()}
    else:
        rate = 0.5 if outcome == "partial" else 0.0
        body = {"completed": False, "completion_rate": rate, "actual_duration": actual,
                "failure_reason": "simulated"}
    response = client.patch(
        "/api/v1/plans/" + str(plan_id) + "/tasks/" + str(task["id"]),
        json=body,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return body


def _simulate_persona(client: TestClient, headers: dict, scenario: str, profile: dict, today: date) -> list[dict]:
    rng = random.Random(scenario)
    _generate_plan(client, headers, today)
    events: list[dict] = []
    first_seen: dict[str, int] = {}
    max_wait = 0
    for offset in range(DAY_COUNT):
        day = today + timedelta(days=offset)
        detail = _active_plan(client, headers)
        if detail is None:
            break
        plan_id = detail["id"]
        day_tasks = [task for task in detail["tasks"] if task.get("scheduled_date") == day.isoformat()]
        day_completed = 0
        estimated_minutes = actual_minutes = 0
        estimates: list[dict] = []
        for task in day_tasks:
            title = str(task.get("title") or task["id"])
            first_seen.setdefault(title, offset)
            roll = rng.random()
            if roll < profile["completion"]:
                outcome = "completed"
            elif roll < profile["completion"] + profile["partial"]:
                outcome = "partial"
            else:
                outcome = "none"
            body = _patch_task(client, headers, plan_id, task, outcome, profile["ratio"])
            estimated_minutes += int(task.get("estimated_duration") or 60)
            actual_minutes += int(body["actual_duration"])
            if outcome == "completed":
                day_completed += 1
                max_wait = max(max_wait, offset - first_seen[title])
                estimates.append(
                    {
                        "task_id": task["id"],
                        "accuracy": "over" if profile["ratio"] > 1.2 else "ok",
                        "actual_minutes": int(body["actual_duration"]),
                    }
                )
            else:
                max_wait = max(max_wait, offset - first_seen[title] + 1)
        rate = day_completed / len(day_tasks) if day_tasks else 0.0
        feedback = {
            "date": day.isoformat(),
            "completion_rate": round(min(rate, 0.99), 3),
            "stress_level": profile["stress"],
            "energy_level": profile["energy"],
            "day_review": "模拟反馈 day " + str(offset + 1),
            "task_estimates": estimates,
            "close_day": bool(day_tasks) and day_completed == len(day_tasks),
        }
        response = client.post(
            "/api/v1/plans/" + str(plan_id) + "/feedback", json=feedback, headers=headers
        )
        if response.status_code != 201:
            raise RuntimeError("feedback failed: " + str(response.status_code) + " " + response.text)
        body = response.json()
        events.append(
            {
                "day": day.isoformat(),
                "tasks": len(day_tasks),
                "completed": day_completed,
                "estimated_minutes": estimated_minutes,
                "actual_minutes": actual_minutes,
                "route": body.get("replan_decision"),
                "replan_triggered": body.get("replan_triggered"),
                "postponed": len(body.get("postponed_task_ids") or []),
            }
        )
    events.append({"max_wait_days": max_wait})
    return events


def _metrics(client: TestClient, headers: dict, events: list[dict]) -> dict:
    """Mechanism metrics accumulated during the simulated week.

    Reading only the current active plan would hide what happened before a
    replan, so the simulation accumulates day-level totals instead.
    """
    plan_versions = len(client.get("/api/v1/plans", headers=headers).json())
    day_events = [event for event in events if "tasks" in event]
    planned_tasks = sum(event["tasks"] for event in day_events)
    completed = sum(event["completed"] for event in day_events)
    estimated = sum(event["estimated_minutes"] for event in day_events)
    actual = sum(event["actual_minutes"] for event in day_events)
    full_replans = sum(1 for event in day_events if event["route"] == "full_replan")
    micro_adjusts = sum(
        1 for event in day_events if event["route"] == "micro_adjust"
    )
    postpones = sum(1 for event in day_events if event["route"] == "postpone")
    max_wait = max(
        (event.get("max_wait_days", 0) for event in events if "max_wait_days" in event),
        default=0,
    )
    return {
        "plan_versions": plan_versions,
        "planned_tasks": planned_tasks,
        "completed_tasks": completed,
        "completion_rate": round(completed / planned_tasks, 3) if planned_tasks else 0.0,
        "tasks_per_day": round(planned_tasks / len(day_events), 2) if day_events else 0.0,
        "estimated_minutes": estimated,
        "actual_minutes": actual,
        "utilization": round(actual / estimated, 3) if estimated else None,
        "full_replans": full_replans,
        "micro_adjusts": micro_adjusts,
        "postpones": postpones,
        "max_wait_days": max_wait,
        "feedbacks": len(day_events),
    }


def main() -> int:
    today = date.today()
    results: list[dict] = []
    with TestClient(app) as client:
        for index, (scenario, profile) in enumerate(PERSONAS.items()):
            headers = _register(client, "sim-" + scenario + "@example.com")
            imported = client.post(
                "/api/v1/dev/scenarios/import",
                json={"scenario_name": scenario},
                headers=headers,
            )
            assert imported.status_code == 200, imported.text
            events = _simulate_persona(client, headers, scenario, profile, today)
            metrics = _metrics(client, headers, events)
            metrics["scenario"] = scenario
            metrics["label"] = profile["label"]
            results.append(metrics)
            print("[" + str(index + 1) + "/" + str(len(PERSONAS)) + "] " + scenario + ": " + str(metrics))

    report = {"generated_at": datetime.now().isoformat(), "days": DAY_COUNT, "results": results}
    (SIM_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    header = (
        "| 模拟使用者 | 完成率 | 日均任务 | 计划版本 | 反馈数 | 顺延次数 "
        "| 小修次数 | 大改次数 | 实际/计划用量 | 最长等待天数 |"
    )
    separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    rows = []
    for item in results:
        utilization = "-" if item["utilization"] is None else str(item["utilization"])
        rows.append(
            "| " + item["label"] + " | "
            + format(item["completion_rate"], ".0%") + " | "
            + str(item["tasks_per_day"]) + " | "
            + str(item["plan_versions"]) + " | "
            + str(item["feedbacks"]) + " | "
            + str(item["postpones"]) + " | "
            + str(item["micro_adjusts"]) + " | "
            + str(item["full_replans"]) + " | "
            + utilization + " | "
            + str(item["max_wait_days"]) + " |"
        )
    markdown = "\n".join([header, separator] + rows)
    print("\n" + markdown)
    (SIM_DIR / "report.md").write_text(markdown + "\n", encoding="utf-8")
    print("\nreport: " + str(SIM_DIR))
    return 0


if __name__ == "__main__":
    sys.exit(main())