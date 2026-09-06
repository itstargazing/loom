"""Response models for the dashboard overview."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


from app.schemas.skills import SkillCount


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ActivityItem(CamelModel):
    """One entry in the cross-skill feed, projected to a common shape."""

    skill: str
    label: str
    title: str
    detail: str | None
    source_url: str
    page_title: str
    confidence: float
    times_seen: int
    last_seen_at: datetime


class CaptureSummary(CamelModel):
    total_events: int
    #  Named for the window rather than "24h", which camel-cases to the
    #  unreadable "eventsLast24H".
    events_last_day: int
    #  None when nothing has ever been captured. The dashboard reads this to
    #  decide whether capture looks live.
    last_event_at: datetime | None


class ClassificationSummary(CamelModel):
    succeeded: int
    failed: int
    #  Classified but not yet written into the skill stores.
    awaiting_routing: int


class DashboardOverview(CamelModel):
    skills: list[SkillCount]
    recent_activity: list[ActivityItem]
    capture: CaptureSummary
    classification: ClassificationSummary
