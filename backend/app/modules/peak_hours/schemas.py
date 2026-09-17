from pydantic import BaseModel, Field


class PeakWindowCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    start: str  # "HH:MM", validated in the service layer for readable errors
    end: str
    cross_day: bool = False
    priority: int = 0
    enabled: bool = True
    note: str | None = None


class PeakWindowUpdate(BaseModel):
    code: str | None = None
    start: str | None = None
    end: str | None = None
    cross_day: bool | None = None
    priority: int | None = None
    enabled: bool | None = None
    note: str | None = None
