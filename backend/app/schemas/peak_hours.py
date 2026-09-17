from pydantic import BaseModel, Field

_TIME_PATTERN = r"^([01]\d|2[0-3]):([0-5]\d)$"


class PeakWindowBase(BaseModel):
    code: str = Field(min_length=1, max_length=40, description="时段标识，如 EVENING_PEAK")
    start_time: str = Field(pattern=_TIME_PATTERN, description="开始时刻 HH:MM")
    end_time: str = Field(pattern=_TIME_PATTERN, description="结束时刻 HH:MM")
    cross_day: bool = Field(default=False, description="是否跨日（结束时刻落在次日）")
    priority: int = Field(default=100, ge=0, le=9999, description="优先级，数值小者优先")
    enabled: bool = True
    note: str | None = Field(default=None, max_length=200)


class PeakWindowCreate(PeakWindowBase):
    pass


class PeakWindowUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    start_time: str | None = Field(default=None, pattern=_TIME_PATTERN)
    end_time: str | None = Field(default=None, pattern=_TIME_PATTERN)
    cross_day: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=9999)
    enabled: bool | None = None
    note: str | None = Field(default=None, max_length=200)


class PeakWindowOut(BaseModel):
    id: int
    code: str
    start_time: str
    end_time: str
    cross_day: bool
    priority: int
    enabled: bool
    note: str | None = None
    created_at: str
    updated_at: str
