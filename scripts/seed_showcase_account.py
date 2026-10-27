"""Create the synthetic two-week showcase account.

This is intentionally a seed/backfill script, not a production workflow:
* auth, Level 1 CAT, xlsx import and Level 2 replay use the real services;
* historical plans/tasks/executions/feedback are ORM-backfilled because the
  normal planning path cannot place tasks in the past;
* every showcase row is marked ``data_origin="synthetic"`` where the schema
  supports it and the account carries a seed marker;
* rerunning cleans only the verified showcase account and rebuilds it.

It never deletes another user or ``demo@damn.app``.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.engine import make_url

from app.application.services.auth_service import AuthService
from app.application.services.schedule_event_service import ScheduleEventService
from app.application.services.trait_assessment_service import TraitAssessmentService
from app.application.services.user_model_service import UserModelService
from app.core.config import get_settings
from app.core.security import hash_password
from app.domain.models.enums import (
    CognitiveLoad,
    GoalSetStatus,
    GoalStatus,
    GoalType,
    PlanningMode,
    PlanStatus,
    Priority,
    TaskKind,
    TaskStatus,
    TimeOfDay,
)
from app.domain.recurrence import RecurrenceFrequency
from app.domain.rules.base import RuleContext, RuleEngine
from app.domain.scheduling.fixed_events import expand_fixed_events
from app.domain.scheduling.schedule_result import CandidateSchedule, ScheduledTask
from app.domain.scheduling.scheduler import Scheduler
from app.infrastructure.database.models.agent_memory import AgentMemory
from app.infrastructure.database.models.agent_run import AgentRun
from app.infrastructure.database.models.execution import TaskExecution
from app.infrastructure.database.models.feedback import Feedback
from app.infrastructure.database.models.generation_job import GenerationJobModel
from app.infrastructure.database.models.goal import Goal
from app.infrastructure.database.models.goal_set import GoalSet
from app.infrastructure.database.models.plan import Plan
from app.infrastructure.database.models.prediction_log import PredictionLog
from app.infrastructure.database.models.replan_event import ReplanEvent
from app.infrastructure.database.models.schedule_event import ScheduleEvent
from app.infrastructure.database.models.shadow_prediction import ShadowPrediction
from app.infrastructure.database.models.task import Task
from app.infrastructure.database.models.task_standard import TaskStandard
from app.infrastructure.database.models.trait_assessment import TraitAssessmentModel
from app.infrastructure.database.models.user import User
from app.infrastructure.database.models.user_state import UserStateModel
from app.infrastructure.database.session import SessionLocal

EMAIL = "showcase@damn.app"
PASSWORD = "ShowcaseDemo2026!"
DISPLAY_NAME = "林嘉禾（演示）"
IDENTITY = "24级计算机科学与技术04班"
SEED_MARKER = "showcase-v1"
COURSE_FILE = Path("test.xlsx")
BACKUP_GLOB = "var/backups/planner-*.json"
MANIFEST = Path("var/showcase_seed_manifest.json")

TODAY = date.today()
HISTORY_END = TODAY - timedelta(days=1)
HISTORY_START = HISTORY_END - timedelta(days=13)
V1_DATE = HISTORY_START - timedelta(days=1)
PLAN_START = HISTORY_START
PLAN_END = TODAY + timedelta(days=7)
HISTORY_DAYS = [HISTORY_START + timedelta(days=i) for i in range(14)]
FUTURE_DAYS = [TODAY + timedelta(days=i) for i in range((PLAN_END - TODAY).days + 1)]

PROFILE: dict[str, Any] = {
    "showcase_seed": SEED_MARKER,
    "identity": IDENTITY,
    "preferred_time_slots": {
        "high": "morning",
        "medium": "afternoon",
        "low": "evening",
        "restorative": "evening",
    },
    "day_start": "08:00",
    "day_end": "22:00",
    "unavailable_weekdays": [],
    "conflicting_subject_pairs": [["math", "algorithm"]],
}

PREFERENCES: dict[str, Any] = {
    "available_minutes_per_day": 720,
    "daily_limit_minutes": 300,
    "buffer_minutes": 15,
    "high_cognitive_max_per_day": 2,
    "max_daily_minutes_per_goal": 120,
    "sleep_start": "23:30",
    "sleep_end": "07:30",
    "feedback_time": "21:00",
    "feedback_enabled": True,
}

DAY_NOTES = [
    "今天算法课和 Web 前端连在一起，晚上先把英语词汇和数学极限块推进完。",
    "周二课程比较满，英语照常完成；数学只推进了一块，明天补。",
    "周三下午的课结束后状态一般，先做了英语和复盘，再啃数学。",
    "今天把数学导数部分补上，晚上注意力比下午好。",
    "周五课程结束得晚，数学这块没啃动，先保证英语和复盘。",
    "周末没有课，上午补算法实验，下午把落下的数学补了一块。",
    "周日安排了算法实验和项目推进，英语和复盘保持住了。",
    "新的一周没有常规课程，上午做数学，下午推进 DAMN 项目。",
    "今天英语状态不好跳过一次，但数学和复盘完成得比较稳。",
    "项目推进顺利，数学换到晚上做，效率还可以。",
    "数学这一块比预估难，做到一半先停，明天继续。",
    "课程任务和项目撞在一起，数学没有开始，晚上只完成了英语和复盘。",
    "今天先保证英语和 OS 复习，数学做了一半，项目留到周末。",
    "周日收尾：英语、复盘和项目都完成，数学还差最后一块。",
]


@dataclass(frozen=True)
class TaskSpec:
    title: str
    goal_id: int
    day: date
    minutes: int
    load: CognitiveLoad
    priority: Priority
    task_kind: TaskKind
    subject: str
    status: TaskStatus = TaskStatus.COMPLETED
    series_id: str | None = None
    series_index: int | None = None
    occurrence_date: date | None = None
    work_unit_key: str | None = None
    chunk_index: int | None = None
    description: str | None = None


def _dt(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=UTC)


def _deadline(day: date) -> datetime:
    return _dt(day, 23, 59)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_dev_database() -> None:
    url = make_url(get_settings().database_url)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost"}
        or url.database != "planner"
    ):
        raise SystemExit(
            "refusing to seed: expected the local development PostgreSQL "
            f"database 'planner', got {url.render_as_string(hide_password=True)}"
        )


def _find_user(session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def _is_showcase(user: User) -> bool:
    return bool((user.profile or {}).get("showcase_seed") == SEED_MARKER)


def _cleanup_showcase(session, user_id: int) -> None:
    """Delete only rows owned by the verified showcase user, in FK order."""
    plan_ids = list(
        session.scalars(select(Plan.id).where(Plan.user_id == user_id)).all()
    )
    task_ids = (
        list(
            session.scalars(
                select(Task.id).where(Task.plan_id.in_(plan_ids))
            ).all()
        )
        if plan_ids
        else []
    )

    session.execute(delete(UserStateModel).where(UserStateModel.user_id == user_id))
    session.execute(delete(ScheduleEvent).where(ScheduleEvent.user_id == user_id))
    session.execute(
        delete(TraitAssessmentModel).where(TraitAssessmentModel.user_id == user_id)
    )
    session.execute(
        delete(GenerationJobModel).where(GenerationJobModel.user_id == user_id)
    )
    session.execute(delete(AgentMemory).where(AgentMemory.user_id == user_id))
    session.execute(delete(AgentRun).where(AgentRun.user_id == user_id))
    session.execute(
        delete(ShadowPrediction).where(ShadowPrediction.user_id == user_id)
    )
    session.execute(delete(PredictionLog).where(PredictionLog.user_id == user_id))
    if plan_ids:
        session.execute(delete(ReplanEvent).where(ReplanEvent.plan_id.in_(plan_ids)))
    session.execute(delete(Feedback).where(Feedback.user_id == user_id))
    if task_ids:
        session.execute(delete(TaskStandard).where(TaskStandard.task_id.in_(task_ids)))
        session.execute(
            delete(TaskExecution).where(TaskExecution.task_id.in_(task_ids))
        )
    if plan_ids:
        session.execute(
            update(Task)
            .where(Task.plan_id.in_(plan_ids))
            .values(parent_task_id=None)
        )
        session.execute(delete(Task).where(Task.plan_id.in_(plan_ids)))
        session.execute(
            update(Plan).where(Plan.user_id == user_id).values(parent_plan_id=None)
        )
        session.execute(delete(Plan).where(Plan.user_id == user_id))
    session.execute(delete(Goal).where(Goal.user_id == user_id))
    session.execute(delete(GoalSet).where(GoalSet.user_id == user_id))
    session.commit()


def _reset_user(session, user: User) -> None:
    user.password_hash = hash_password(PASSWORD)
    user.display_name = DISPLAY_NAME
    user.execution_weight = 0.5
    user.profile = dict(PROFILE)
    user.scheduling_preferences = dict(PREFERENCES)
    user.identity = IDENTITY
    user.trait_profile = None
    user.trait_model_version = None
    user.trait_artifact_hash = None
    user.trait_feature_version = None
    user.created_at = _dt(V1_DATE, 20, 0)
    session.commit()


def _create_or_reset_user(session) -> User:
    user = _find_user(session, EMAIL)
    if user is not None:
        if not _is_showcase(user):
            raise SystemExit(
                f"refusing to touch {EMAIL}: it exists but has no {SEED_MARKER} marker"
            )
        _cleanup_showcase(session, user.id)
        _reset_user(session, user)
        return user

    auth = AuthService(session)
    user = auth.register(
        EMAIL,
        PASSWORD,
        display_name=DISPLAY_NAME,
        execution_weight=0.5,
        profile=dict(PROFILE),
    )
    user = session.get(User, user.id)
    assert user is not None
    user.scheduling_preferences = dict(PREFERENCES)
    user.identity = IDENTITY
    user.created_at = _dt(V1_DATE, 20, 0)
    session.commit()
    return user


def _seed_level1(user_id: int) -> dict[str, Any]:
    session = SessionLocal()
    try:
        service = TraitAssessmentService(session)
        data = service.start(user_id)
        answers: list[dict[str, Any]] = []
        for _ in range(80):
            if data.status == "completed":
                break
            item = data.next_item
            if item is None:
                raise RuntimeError("CAT returned no next item before completion")
            # Stable synthetic profile: E/O/A/C above midpoint, N below.
            response = {"E": 4, "O": 4, "A": 4, "C": 4, "N": 2}.get(
                item.domain, 3
            )
            answers.append({"item_id": item.item_id, "response": response})
            data = service.answer(
                user_id,
                data.assessment_id,
                item_id=item.item_id,
                response=response,
            )
        if data.status != "completed":
            raise RuntimeError("CAT did not complete within the item cap")
        row = session.get(TraitAssessmentModel, data.assessment_id)
        if row is None:
            raise RuntimeError("completed trait assessment row is missing")
        row.data_origin = "synthetic"
        row.created_at = _dt(V1_DATE - timedelta(days=2), 20, 0)
        row.updated_at = row.created_at
        row.completed_at = row.created_at
        session.commit()
        user = session.get(User, user_id)
        if user is None or not user.trait_profile:
            raise RuntimeError("Level 1 profile was not persisted")
        return {
            "assessment_id": data.assessment_id,
            "items_answered": len(answers),
            "trait_domains": sorted((user.trait_profile or {}).get("domains", {})),
        }
    finally:
        session.close()


def _import_courses(user_id: int) -> dict[str, Any]:
    if not COURSE_FILE.exists():
        raise SystemExit(f"{COURSE_FILE} not found")
    session = SessionLocal()
    try:
        service = ScheduleEventService(session)
        result = service.import_file(
            user_id,
            filename=COURSE_FILE.name,
            content=COURSE_FILE.read_bytes(),
        )
        # These are historical timetable rows; keep their creation date sensible.
        session.execute(
            update(ScheduleEvent)
            .where(ScheduleEvent.user_id == user_id)
            .values(
                created_at=_dt(date(2026, 8, 31), 8, 0),
                updated_at=_dt(date(2026, 8, 31), 8, 0),
            )
        )
        session.commit()
        count = session.scalar(
            select(ScheduleEvent.id)
            .where(ScheduleEvent.user_id == user_id)
            .limit(1)
        )
        total = session.scalar(
            select(ScheduleEvent.id)
            .where(ScheduleEvent.user_id == user_id)
            .order_by(ScheduleEvent.id.desc())
            .limit(1)
        )
        return {
            "imported": result.imported,
            "updated": result.updated,
            "skipped": result.skipped,
            "warnings": result.warnings,
            "conflicts": result.conflicts,
            "first_event_id": count,
            "last_event_id": total,
            "file_sha256": _sha256(COURSE_FILE),
        }
    finally:
        session.close()


def _create_goals(session, user_id: int) -> dict[str, Goal]:
    set_a = GoalSet(
        user_id=user_id,
        name="考研复习与课程学习",
        description="围绕考研英语、高等数学和当前学期课程安排的学习目标集。",
        status=GoalSetStatus.ACTIVE,
        created_at=_dt(V1_DATE, 20, 0),
    )
    set_b = GoalSet(
        user_id=user_id,
        name="项目实践与长期习惯",
        description="DAMN 省赛版本开发与每日复盘习惯。",
        status=GoalSetStatus.ACTIVE,
        created_at=_dt(V1_DATE, 20, 0),
    )
    session.add_all([set_a, set_b])
    session.flush()

    common = {"showcase": True, "synthetic": True}
    goals = [
        Goal(
            user_id=user_id,
            goal_set_id=set_a.id,
            title="考研英语词汇复习",
            description="每天完成一组考研词汇、真题短语和错词回看。",
            goal_type=GoalType.LONG_TERM,
            deadline=_deadline(TODAY + timedelta(days=76)),
            priority=Priority.MEDIUM,
            status=GoalStatus.ACTIVE,
            estimated_minutes=20 * 14,
            start_date=HISTORY_START,
            task_kind=TaskKind.ROUTINE,
            planning_mode=PlanningMode.RECURRING,
            recurrence_frequency=RecurrenceFrequency.DAILY,
            recurrence_interval=1,
            daily_target_minutes=20,
            options=common,
            created_at=_dt(V1_DATE, 20, 0),
        ),
        Goal(
            user_id=user_id,
            goal_set_id=set_a.id,
            title="高等数学复习",
            description="高数上册重点章节：极限、导数、中值定理、积分和多元微分。",
            goal_type=GoalType.PROJECT,
            deadline=_deadline(TODAY + timedelta(days=20)),
            priority=Priority.HIGH,
            status=GoalStatus.ACTIVE,
            estimated_minutes=1800,
            start_date=HISTORY_START,
            task_kind=TaskKind.LONG_TERM,
            planning_mode=PlanningMode.PROJECT,
            options=common,
            created_at=_dt(V1_DATE, 20, 0),
        ),
        Goal(
            user_id=user_id,
            goal_set_id=set_a.id,
            title="算法分析与设计实验",
            description="完成分治与动态规划实验报告和代码测试。",
            goal_type=GoalType.SHORT_TERM,
            deadline=_deadline(HISTORY_START + timedelta(days=7)),
            priority=Priority.HIGH,
            status=GoalStatus.ACTIVE,
            estimated_minutes=180,
            start_date=HISTORY_START,
            task_kind=TaskKind.ONE_OFF,
            planning_mode=PlanningMode.ONE_OFF,
            options=common,
            created_at=_dt(V1_DATE, 20, 0),
        ),
        Goal(
            user_id=user_id,
            goal_set_id=set_a.id,
            title="操作系统课程复习",
            description="梳理进程、内存和文件系统的课程重点。",
            goal_type=GoalType.SHORT_TERM,
            deadline=_deadline(TODAY),
            priority=Priority.HIGH,
            status=GoalStatus.ACTIVE,
            estimated_minutes=180,
            start_date=HISTORY_START,
            task_kind=TaskKind.ONE_OFF,
            planning_mode=PlanningMode.ONE_OFF,
            options=common,
            created_at=_dt(V1_DATE, 20, 0),
        ),
        Goal(
            user_id=user_id,
            goal_set_id=set_b.id,
            title="DAMN 省赛版本开发",
            description="完成展示账号、课程表导入、反馈/Level 2 和前端演示验收。",
            goal_type=GoalType.PROJECT,
            deadline=_deadline(TODAY + timedelta(days=13)),
            priority=Priority.HIGH,
            status=GoalStatus.ACTIVE,
            estimated_minutes=720,
            start_date=HISTORY_START,
            task_kind=TaskKind.LONG_TERM,
            planning_mode=PlanningMode.PROJECT,
            options=common,
            created_at=_dt(V1_DATE, 20, 0),
        ),
        Goal(
            user_id=user_id,
            goal_set_id=set_b.id,
            title="每日复盘",
            description="用 15 分钟记录完成情况、卡点和第二天的安排。",
            goal_type=GoalType.HABIT,
            deadline=_deadline(PLAN_END),
            priority=Priority.LOW,
            status=GoalStatus.ACTIVE,
            estimated_minutes=15 * 14,
            start_date=HISTORY_START,
            task_kind=TaskKind.ROUTINE,
            planning_mode=PlanningMode.RECURRING,
            recurrence_frequency=RecurrenceFrequency.DAILY,
            recurrence_interval=1,
            daily_target_minutes=15,
            options=common,
            created_at=_dt(V1_DATE, 20, 0),
        ),
    ]
    session.add_all(goals)
    session.commit()
    return {
        "english": goals[0],
        "math": goals[1],
        "algorithm": goals[2],
        "os": goals[3],
        "damn": goals[4],
        "review": goals[5],
    }


def _task_specs(goals: dict[str, Goal]) -> list[TaskSpec]:
    english = goals["english"].id
    math = goals["math"].id
    algorithm = goals["algorithm"].id
    os_goal = goals["os"].id
    damn = goals["damn"].id
    review = goals["review"].id
    assert all(
        value is not None
        for value in (english, math, algorithm, os_goal, damn, review)
    )

    specs: list[TaskSpec] = []
    for index, day in enumerate([*HISTORY_DAYS, *FUTURE_DAYS]):
        status = (
            TaskStatus.SKIPPED
            if day == HISTORY_START + timedelta(days=8)
            else TaskStatus.IN_PROGRESS
            if day == HISTORY_START + timedelta(days=12)
            else TaskStatus.COMPLETED
            if day <= HISTORY_END
            else TaskStatus.SCHEDULED
        )
        specs.append(
            TaskSpec(
                title=f"考研英语词汇：List {index + 1} + 真题短语",
                goal_id=english,
                day=day,
                minutes=20,
                load=CognitiveLoad.MEDIUM,
                priority=Priority.MEDIUM,
                task_kind=TaskKind.ROUTINE,
                subject="english",
                status=status,
                series_id="english-daily",
                series_index=index,
                occurrence_date=day,
                description="词汇记忆 + 错词回看，保持每日英语输入。",
            )
        )

    for index, day in enumerate([*HISTORY_DAYS, *FUTURE_DAYS]):
        status = (
            TaskStatus.SKIPPED
            if day == HISTORY_START + timedelta(days=6)
            else TaskStatus.IN_PROGRESS
            if day in {
                HISTORY_START + timedelta(days=11),
                HISTORY_START + timedelta(days=13),
            }
            else TaskStatus.COMPLETED
            if day <= HISTORY_END
            else TaskStatus.SCHEDULED
        )
        specs.append(
            TaskSpec(
                title="晚间复盘：今日错题与明日安排",
                goal_id=review,
                day=day,
                minutes=15,
                load=CognitiveLoad.LOW,
                priority=Priority.LOW,
                task_kind=TaskKind.ROUTINE,
                subject="review",
                status=status,
                series_id="daily-review",
                series_index=index,
                occurrence_date=day,
                description="记录完成度、卡点和第二天优先级。",
            )
        )

    math_units = [
        "函数、极限与连续",
        "导数与微分",
        "中值定理与导数应用",
        "不定积分",
        "定积分及其应用",
        "多元函数微分",
    ]
    math_history_days = [
        HISTORY_START + timedelta(days=i)
        for i in (0, 1, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13)
    ]
    math_days = [*math_history_days, *FUTURE_DAYS[:6]]
    math_status = {
        math_history_days[4]: TaskStatus.SKIPPED,
        math_history_days[8]: TaskStatus.IN_PROGRESS,
        math_history_days[9]: TaskStatus.PENDING,
        math_history_days[11]: TaskStatus.IN_PROGRESS,
    }
    for index, day in enumerate(math_days):
        unit_index = index // 3
        chunk_index = index % 3
        specs.append(
            TaskSpec(
                title=f"{math_units[unit_index]} · 第{chunk_index + 1}/3块",
                goal_id=math,
                day=day,
                minutes=100,
                load=CognitiveLoad.HIGH,
                priority=Priority.HIGH,
                task_kind=TaskKind.LONG_TERM,
                subject="math",
                status=math_status.get(
                    day,
                    TaskStatus.COMPLETED if day <= HISTORY_END else TaskStatus.SCHEDULED,
                ),
                work_unit_key=f"wg-{math}-project-{unit_index}",
                chunk_index=chunk_index,
                description=math_units[unit_index],
            )
        )

    damn_units = [
        "数据模型与展示账号",
        "课程表导入与固定事件",
        "反馈、Level 2 与计划调整",
        "前端演示与验收",
    ]
    damn_days = [
        HISTORY_START + timedelta(days=4),
        HISTORY_START + timedelta(days=6),
        HISTORY_START + timedelta(days=9),
        HISTORY_START + timedelta(days=11),
        HISTORY_START + timedelta(days=13),
        TODAY + timedelta(days=2),
        TODAY + timedelta(days=5),
        TODAY + timedelta(days=7),
    ]
    damn_status = {
        damn_days[1]: TaskStatus.IN_PROGRESS,
        damn_days[3]: TaskStatus.SKIPPED,
    }
    for index, day in enumerate(damn_days):
        unit_index = index // 2
        chunk_index = index % 2
        specs.append(
            TaskSpec(
                title=f"{damn_units[unit_index]} · 第{chunk_index + 1}/2块",
                goal_id=damn,
                day=day,
                minutes=90,
                load=CognitiveLoad.HIGH,
                priority=Priority.HIGH,
                task_kind=TaskKind.LONG_TERM,
                subject="project",
                status=damn_status.get(
                    day,
                    TaskStatus.COMPLETED if day <= HISTORY_END else TaskStatus.SCHEDULED,
                ),
                work_unit_key=f"wg-{damn}-project-{unit_index}",
                chunk_index=chunk_index,
                description=damn_units[unit_index],
            )
        )

    algorithm_days = [HISTORY_START + timedelta(days=5), HISTORY_START + timedelta(days=6)]
    for chunk_index, day in enumerate(algorithm_days):
        specs.append(
            TaskSpec(
                title=f"算法实验：分治与动态规划 · 第{chunk_index + 1}/2块",
                goal_id=algorithm,
                day=day,
                minutes=90,
                load=CognitiveLoad.HIGH,
                priority=Priority.HIGH,
                task_kind=TaskKind.ONE_OFF,
                subject="algorithm",
                status=TaskStatus.COMPLETED if chunk_index == 0 else TaskStatus.SKIPPED,
                work_unit_key=f"wg-{algorithm}-one_off",
                chunk_index=chunk_index,
                description="实现、测试并整理实验报告。",
            )
        )

    os_days = [HISTORY_START + timedelta(days=12), TODAY]
    for chunk_index, day in enumerate(os_days):
        specs.append(
            TaskSpec(
                title=f"操作系统：进程与内存复习 · 第{chunk_index + 1}/2块",
                goal_id=os_goal,
                day=day,
                minutes=90,
                load=CognitiveLoad.HIGH,
                priority=Priority.HIGH,
                task_kind=TaskKind.ONE_OFF,
                subject="cs",
                status=TaskStatus.COMPLETED if chunk_index == 0 else TaskStatus.SCHEDULED,
                work_unit_key=f"wg-{os_goal}-one_off",
                chunk_index=chunk_index,
                description="进程调度、内存管理与文件系统重点。",
            )
        )
    return specs


def _task_model(spec: TaskSpec, plan_id: int, order_index: int) -> Task:
    return Task(
        plan_id=plan_id,
        goal_id=spec.goal_id,
        title=spec.title,
        description=spec.description,
        estimated_duration=spec.minutes,
        predicted_duration=spec.minutes,
        cognitive_load=spec.load,
        priority=spec.priority,
        status=TaskStatus.PENDING,
        completion_probability=0.8,
        prediction_source="deterministic:workload_estimate",
        prediction_mode="production",
        data_origin="synthetic",
        is_flexible=True,
        task_kind=spec.task_kind,
        series_id=spec.series_id,
        series_index=spec.series_index,
        occurrence_date=spec.occurrence_date,
        work_unit_key=spec.work_unit_key,
        chunk_index=spec.chunk_index,
        order_index=order_index,
    )


def _schedule_day(
    session,
    user_id: int,
    day: date,
    tasks: list[Task],
    goals: dict[str, Goal],
) -> dict[int, ScheduledTask]:
    events = ScheduleEventService(session).list_events(user_id, start=day, end=day)
    fixed = expand_fixed_events(events, day, day)
    subject_by_goal = {
        goal.id: key
        for key, goal in goals.items()
        for goal in [goal]
        if goal.id is not None
    }
    subject_by_goal: dict[int, str] = {}
    for task in tasks:
        if task.goal_id == goals["math"].id:
            subject_by_goal[task.id] = "math"
        elif task.goal_id == goals["algorithm"].id:
            subject_by_goal[task.id] = "algorithm"
        elif task.goal_id == goals["os"].id:
            subject_by_goal[task.id] = "cs"
        elif task.goal_id == goals["damn"].id:
            subject_by_goal[task.id] = "project"
        elif task.goal_id == goals["english"].id:
            subject_by_goal[task.id] = "english"
        else:
            subject_by_goal[task.id] = "review"

    deadlines: dict[int, date] = {}
    earliest: dict[int, date] = {}
    goal_deadlines = {
        key: goal.deadline.date() if goal.deadline else PLAN_END
        for key, goal in goals.items()
        if goal.id is not None
    }
    for task in tasks:
        assert task.id is not None
        if task.occurrence_date is not None:
            deadlines[task.id] = task.occurrence_date
        else:
            goal_key = next(
                (key for key, goal in goals.items() if goal.id == task.goal_id),
                "math",
            )
            deadlines[task.id] = goal_deadlines.get(goal_key, PLAN_END)
        earliest[task.id] = day

    context = RuleContext(
        # The production scheduler subtracts fixed-event minutes from the
        # placement capacity. For a 300-minute course day that would leave zero
        # task minutes even though the evening is free. The seed uses a larger
        # internal placement budget, then validates the final schedule against
        # the real 300-minute hard limit in _validate_schedule().
        daily_limit_minutes=800,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        max_daily_minutes_per_goal=120,
        available_minutes_per_day=800,
        day_start=time(8, 0),
        day_end=time(22, 0),
        preferred_time_slots=dict(PROFILE["preferred_time_slots"]),
        today=day,
        schedule_start=day,
        schedule_end=day,
        fixed_events=fixed,
        task_deadlines=deadlines,
        task_earliest_dates=earliest,
        task_subjects=subject_by_goal,
        conflicting_subject_pairs=[("math", "algorithm")],
    )
    result = Scheduler().schedule(tasks, context)
    if result.unscheduled_task_ids:
        raise RuntimeError(
            f"seed scheduling failed on {day}: unscheduled={result.unscheduled_task_ids}, "
            f"reasons={result.unscheduled_reasons}"
        )
    return {item.task_id: item for item in result.tasks}


def _validate_schedule(
    session,
    user_id: int,
    tasks: list[Task],
    goals: dict[str, Goal],
) -> None:
    events = ScheduleEventService(session).list_events(
        user_id, start=PLAN_START, end=PLAN_END
    )
    fixed = expand_fixed_events(events, PLAN_START, PLAN_END)
    subject_by_goal = {}
    for task in tasks:
        if task.id is None:
            continue
        if task.goal_id == goals["math"].id:
            subject_by_goal[task.id] = "math"
        elif task.goal_id == goals["algorithm"].id:
            subject_by_goal[task.id] = "algorithm"
        elif task.goal_id == goals["os"].id:
            subject_by_goal[task.id] = "cs"
        elif task.goal_id == goals["damn"].id:
            subject_by_goal[task.id] = "project"
        elif task.goal_id == goals["english"].id:
            subject_by_goal[task.id] = "english"
        else:
            subject_by_goal[task.id] = "review"
    deadlines = {}
    earliest = {}
    for task in tasks:
        if task.id is None:
            continue
        if task.occurrence_date is not None:
            deadlines[task.id] = task.occurrence_date
        else:
            goal = next((g for g in goals.values() if g.id == task.goal_id), None)
            deadlines[task.id] = goal.deadline.date() if goal and goal.deadline else PLAN_END
        earliest[task.id] = task.scheduled_date or PLAN_START
    schedule = CandidateSchedule(
        start_date=PLAN_START,
        end_date=PLAN_END,
        tasks=[
            ScheduledTask(
                task_id=task.id,
                title=task.title,
                goal_id=task.goal_id,
                scheduled_date=task.scheduled_date or PLAN_START,
                start_time=task.start_time or time(9, 0),
                end_time=task.end_time or time(10, 0),
                duration_minutes=task.estimated_duration,
                cognitive_load=task.cognitive_load,
                priority=task.priority,
                completion_probability=task.completion_probability or 0.8,
                is_flexible=task.is_flexible,
                series_id=task.series_id,
                occurrence_date=task.occurrence_date,
            )
            for task in tasks
            if task.id is not None
        ],
    )
    context = RuleContext(
        daily_limit_minutes=300,
        buffer_minutes=15,
        high_cognitive_max_per_day=2,
        max_daily_minutes_per_goal=120,
        available_minutes_per_day=480,
        day_start=time(8, 0),
        day_end=time(22, 0),
        preferred_time_slots=dict(PROFILE["preferred_time_slots"]),
        today=HISTORY_END,
        schedule_start=PLAN_START,
        schedule_end=PLAN_END,
        fixed_events=fixed,
        task_deadlines=deadlines,
        task_earliest_dates=earliest,
        task_subjects=subject_by_goal,
        conflicting_subject_pairs=[("math", "algorithm")],
    )
    violations = RuleEngine().hard_violations(schedule, context)
    if violations:
        raise RuntimeError(
            "seed schedule violates hard rules: "
            + ", ".join(f"{v.code}:{v.message}" for v in violations)
        )


def _execution_for(
    task: Task,
    spec: TaskSpec,
    user_id: int,
    index: int,
) -> TaskExecution | None:
    if spec.status in {TaskStatus.SKIPPED, TaskStatus.PENDING, TaskStatus.SCHEDULED}:
        return None
    start = datetime.combine(
        task.scheduled_date or spec.day,
        task.start_time or time(9, 0),
    )
    if spec.status == TaskStatus.COMPLETED:
        delta = (index % 5) * 3 - 4
        actual = max(spec.minutes + delta, 10)
        completion_rate = 1.0
        finished = start + timedelta(minutes=actual)
        completed = True
    else:
        actual = max(int(spec.minutes * 0.5), 10)
        completion_rate = 0.5
        finished = None
        completed = False
    return TaskExecution(
        task_id=task.id or 0,
        user_id=user_id,
        planned_duration=spec.minutes,
        actual_duration=actual,
        completion_rate=completion_rate,
        started_at=start,
        finished_at=finished,
        difficulty_feedback=3 if spec.load == CognitiveLoad.HIGH else 2,
        stress_before=4 + (index % 3),
        stress_after=5 + (index % 3),
        failure_reason=None if completed else "时间不足或课程打断",
        interruption_count=0 if completed else 1,
        time_of_day=(
            TimeOfDay.EVENING
            if start.hour >= 18
            else TimeOfDay.AFTERNOON
            if start.hour >= 12
            else TimeOfDay.MORNING
        ),
        completed=completed,
        data_origin="synthetic",
        created_at=finished or start,
    )


def _seed_plans_and_history(
    session, user_id: int, goals: dict[str, Goal]
) -> dict[str, Any]:
    v1 = Plan(
        user_id=user_id,
        version=1,
        status=PlanStatus.SUPERSEDED,
        title="初始计划：整理一周学习安排",
        start_date=V1_DATE,
        end_date=V1_DATE,
        parent_plan_id=None,
        confidence=0.6,
        data_origin="synthetic",
        created_at=_dt(V1_DATE, 8, 0),
    )
    session.add(v1)
    session.flush()
    v1_task = Task(
        plan_id=v1.id,
        goal_id=None,
        title="整理本周学习计划",
        description="把课程表、考研复习和项目目标整理成一周安排。",
        estimated_duration=30,
        predicted_duration=30,
        cognitive_load=CognitiveLoad.LOW,
        priority=Priority.MEDIUM,
        scheduled_date=V1_DATE,
        start_time=time(19, 0),
        end_time=time(19, 30),
        status=TaskStatus.COMPLETED,
        completion_probability=1.0,
        prediction_source="deterministic:workload_estimate",
        prediction_mode="production",
        data_origin="synthetic",
        is_flexible=True,
        task_kind=TaskKind.ONE_OFF,
        order_index=0,
    )
    session.add(v1_task)
    session.flush()
    session.add(
        TaskExecution(
            task_id=v1_task.id or 0,
            user_id=user_id,
            planned_duration=30,
            actual_duration=28,
            completion_rate=1.0,
            started_at=datetime.combine(V1_DATE, time(19, 0)),
            finished_at=datetime.combine(V1_DATE, time(19, 28)),
            difficulty_feedback=1,
            stress_before=3,
            stress_after=3,
            interruption_count=0,
            time_of_day=TimeOfDay.EVENING,
            completed=True,
            data_origin="synthetic",
            created_at=datetime.combine(V1_DATE, time(19, 28)),
        )
    )

    v2 = Plan(
        user_id=user_id,
        version=2,
        status=PlanStatus.ACTIVE,
        title="两周课程联动学习计划",
        start_date=PLAN_START,
        end_date=PLAN_END,
        parent_plan_id=v1.id,
        confidence=0.7,
        data_origin="synthetic",
        created_at=_dt(V1_DATE, 20, 30),
    )
    session.add(v2)
    session.flush()

    specs = _task_specs(goals)
    by_day: dict[date, list[TaskSpec]] = defaultdict(list)
    for spec in specs:
        by_day[spec.day].append(spec)

    created: list[tuple[Task, TaskSpec]] = []
    order_index = 0
    for day in [*HISTORY_DAYS, *FUTURE_DAYS]:
        for spec in by_day.get(day, []):
            task = _task_model(spec, v2.id, order_index)
            order_index += 1
            session.add(task)
            created.append((task, spec))
    session.flush()

    tasks_by_day: dict[date, list[Task]] = defaultdict(list)
    spec_by_task: dict[int, TaskSpec] = {}
    for task, spec in created:
        assert task.id is not None
        spec_by_task[task.id] = spec
        tasks_by_day[spec.day].append(task)

    for day in [*HISTORY_DAYS, *FUTURE_DAYS]:
        day_tasks = tasks_by_day.get(day, [])
        if not day_tasks:
            continue
        placed = _schedule_day(session, user_id, day, day_tasks, goals)
        for task in day_tasks:
            assert task.id is not None
            slot = placed[task.id]
            task.scheduled_date = slot.scheduled_date
            task.start_time = slot.start_time
            task.end_time = slot.end_time
            task.scheduling_reason = None
            task.scheduling_detail = None
            if day <= HISTORY_END:
                task.status = spec_by_task[task.id].status
            else:
                task.status = TaskStatus.SCHEDULED

    session.flush()
    for index, (task, spec) in enumerate(created):
        if task.status in {
            TaskStatus.SKIPPED,
            TaskStatus.PENDING,
            TaskStatus.SCHEDULED,
        }:
            continue
        execution = _execution_for(task, spec, user_id, index)
        if execution is not None:
            session.add(execution)

    session.add(
        ReplanEvent(
            plan_id=v2.id,
            trigger_type="manual",
            reason="初始计划扩展为两周课程联动计划",
            old_version=1,
            new_version=2,
            changed_tasks=[v1_task.id],
            created_at=_dt(V1_DATE, 20, 30),
        )
    )
    session.commit()

    _validate_schedule(session, user_id, [task for task, _ in created], goals)

    # Feedback is attached to the active v2 plan; the 14-day page therefore
    # shows the complete history instead of splitting it across versions.
    feedback_count = 0
    for day_index, day in enumerate(HISTORY_DAYS):
        day_tasks = tasks_by_day.get(day, [])
        if not day_tasks:
            continue
        completed_count = sum(
            1 for task in day_tasks if task.status == TaskStatus.COMPLETED
        )
        completion_rate = round(completed_count / len(day_tasks), 3)
        high_count = sum(
            1 for task in day_tasks if task.cognitive_load == CognitiveLoad.HIGH
        )
        reasons = []
        for task in day_tasks:
            if task.status == TaskStatus.COMPLETED:
                continue
            if task.status == TaskStatus.SKIPPED:
                reason = "skipped"
                note = "当天课程较多，主动跳过"
            elif task.status == TaskStatus.PENDING:
                reason = "not_enough_time"
                note = "课程和项目占满时间，未开始"
            else:
                reason = "interrupted"
                note = "做到一半被课程或精力打断，明天继续"
            reasons.append(
                {"task_id": task.id, "reason": reason, "note": note}
            )
        stress = max(3, min(9, 4 + high_count + (day_index % 3 - 1)))
        energy = max(3, min(8, 7 - high_count + ((day_index + 1) % 3 - 1)))
        note = DAY_NOTES[day_index % len(DAY_NOTES)]
        session.add(
            Feedback(
                user_id=user_id,
                plan_id=v2.id,
                date=day,
                completion_rate=completion_rate,
                stress_level=stress,
                energy_level=energy,
                delay_reason=(
                    "课程较多，部分任务顺延"
                    if completion_rate < 1
                    else "按计划完成"
                ),
                task_reasons=reasons or None,
                free_text=(
                    f"{note} 当天完成 {completed_count}/{len(day_tasks)} 项，"
                    f"压力 {stress}/10，精力 {energy}/10。"
                ),
                sleep_hours=round(7.2 + ((day_index % 4) - 1) * 0.3, 1),
                dominant_time_of_day=TimeOfDay.EVENING,
                data_origin="synthetic",
                created_at=_dt(day, 21, 45),
            )
        )
        feedback_count += 1
    session.commit()

    return {
        "plan_v1_id": v1.id,
        "plan_v2_id": v2.id,
        "v1_task_id": v1_task.id,
        "task_count_v2": len(created),
        "historical_task_count": sum(1 for _, spec in created if spec.day <= HISTORY_END),
        "future_task_count": sum(1 for _, spec in created if spec.day > HISTORY_END),
        "execution_count": session.scalar(
            select(TaskExecution.id)
            .where(TaskExecution.user_id == user_id)
            .order_by(TaskExecution.id.desc())
            .limit(1)
        )
        and session.query(TaskExecution)
        .filter(TaskExecution.user_id == user_id)
        .count(),
        "feedback_count": feedback_count,
    }


def _refresh_level2(user_id: int) -> dict[str, Any]:
    session = SessionLocal()
    hidden: list[Task] = []
    saved: list[tuple[int, date | None, date | None]] = []
    try:
        # The current day's tasks are future work with no executions yet. Including
        # them would make the snapshot describe 10-26 with zero observed task logs.
        # Replay the last complete history day instead, then restore the current
        # tasks so the active plan and todo page remain complete.
        hidden = list(
            session.scalars(
                select(Task)
                .join(Plan)
                .where(Plan.user_id == user_id, Task.scheduled_date == TODAY)
            ).all()
        )
        saved = [(t.id or 0, t.scheduled_date, t.occurrence_date) for t in hidden]
        for task in hidden:
            task.scheduled_date = None
            if task.occurrence_date == TODAY:
                task.occurrence_date = None
        session.commit()

        snapshot = UserModelService(session).refresh_dynamic_state(
            user_id, commit=True
        )
        if snapshot is None:
            raise RuntimeError("Level 2 replay returned no snapshot")
        row = session.scalar(
            select(UserStateModel).where(UserStateModel.user_id == user_id)
        )
        if row is None or not row.level2_profile:
            raise RuntimeError("Level 2 snapshot was not persisted")
        profile = row.level2_profile or {}
        return {
            "state_id": row.id,
            "observed_on": snapshot.date.isoformat(),
            "update_count": row.update_count,
            "fatigue": round(row.state_fatigue, 4),
            "stress": round(row.state_stress, 4),
            "self_efficacy": round(row.self_efficacy, 4),
            "evidence": profile.get("evidence"),
            "behavioral_indicators": profile.get("behavioral_indicators"),
            "limitations": profile.get("limitations"),
            "source": "real DDSR-V1 replay over synthetic history through the last complete day",
        }
    finally:
        if saved:
            for task_id, scheduled_date, occurrence_date in saved:
                task = session.get(Task, task_id)
                if task is not None:
                    task.scheduled_date = scheduled_date
                    task.occurrence_date = occurrence_date
            session.commit()
        session.close()


def _counts(user_id: int) -> dict[str, int]:
    session = SessionLocal()
    try:
        plan_ids = list(
            session.scalars(select(Plan.id).where(Plan.user_id == user_id)).all()
        )
        task_ids = (
            list(
                session.scalars(
                    select(Task.id).where(Task.plan_id.in_(plan_ids))
                ).all()
            )
            if plan_ids
            else []
        )
        return {
            "goal_sets": session.query(GoalSet).filter_by(user_id=user_id).count(),
            "goals": session.query(Goal).filter_by(user_id=user_id).count(),
            "plans": len(plan_ids),
            "tasks": len(task_ids),
            "executions": session.query(TaskExecution)
            .filter(TaskExecution.user_id == user_id)
            .count(),
            "feedbacks": session.query(Feedback).filter_by(user_id=user_id).count(),
            "trait_assessments": session.query(TraitAssessmentModel)
            .filter_by(user_id=user_id)
            .count(),
            "schedule_events": session.query(ScheduleEvent)
            .filter_by(user_id=user_id)
            .count(),
            "user_states": session.query(UserStateModel)
            .filter_by(user_id=user_id)
            .count(),
            "replan_events": session.query(ReplanEvent)
            .filter(ReplanEvent.plan_id.in_(plan_ids))
            .count()
            if plan_ids
            else 0,
        }
    finally:
        session.close()


def main() -> None:
    _assert_dev_database()
    if not COURSE_FILE.exists():
        raise SystemExit(f"{COURSE_FILE} not found")
    session = SessionLocal()
    try:
        user = _create_or_reset_user(session)
        user_id = user.id
        assert user_id is not None
    finally:
        session.close()

    level1 = _seed_level1(user_id)
    course = _import_courses(user_id)

    session = SessionLocal()
    try:
        goals = _create_goals(session, user_id)
        plans = _seed_plans_and_history(session, user_id, goals)
    finally:
        session.close()

    level2 = _refresh_level2(user_id)
    counts = _counts(user_id)
    manifest = {
        "seed": SEED_MARKER,
        "generated_at": datetime.now(UTC).isoformat(),
        "login_email": EMAIL,
        "user_id": user_id,
        "display_name": DISPLAY_NAME,
        "history_start": HISTORY_START.isoformat(),
        "history_end": HISTORY_END.isoformat(),
        "current_date": TODAY.isoformat(),
        "plan_start": PLAN_START.isoformat(),
        "plan_end": PLAN_END.isoformat(),
        "course_file": str(COURSE_FILE),
        "course": course,
        "level1": level1,
        "plans": plans,
        "level2": level2,
        "counts": counts,
        "backup": str(sorted(Path("var/backups").glob("planner-*.json"))[-1])
        if list(Path("var/backups").glob("planner-*.json"))
        else None,
        "note": "All showcase observations are synthetic; Level 1/2 algorithms were run for real.",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, default=str))
    print(f"\nLOGIN {EMAIL} / {PASSWORD}")


if __name__ == "__main__":
    main()
