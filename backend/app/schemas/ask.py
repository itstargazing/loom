from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class AskCitationOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    capture_event_id: str
    source_url: str
    page_title: str
    snippet: str
    occurred_at: datetime | None = None
    score: float


class AskAnswerOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    question: str
    answer: str
    empty: bool
    citations: list[AskCitationOut]


class AskQuestionIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    question: str
