"""Past-paper question segmentation contract."""

from pydantic import BaseModel, ConfigDict, Field

from uni_rag_core.schemas.chunk import ImageRef


class PastPaperQuestion(BaseModel):
    """A single segmented question from a past-paper page."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str
    doc_id: str
    source_url: str
    page: int
    question_number: int
    text: str
    year: int | None = None
    subject: str | None = None
    options: list[str] = Field(default_factory=list)
    image_ref: ImageRef | None = None
    course_code: str | None = None
    term: str | None = None
    exam_type: str | None = None
    department: str | None = None
