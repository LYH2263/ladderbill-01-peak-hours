from pydantic import BaseModel, Field


class BillRequest(BaseModel):
    account_id: int | None = None
    kwh: float = Field(ge=0)
    peak: bool = False
    persist: bool = True
    #: 账期锚定日，YYYY-MM-DD 或 YYYY-MM-DDTHH:MM；勾选尖峰时用于命中时段
    anchor_date: str | None = None


class CompareRequest(BaseModel):
    kwh: float = Field(ge=0)
    persist: bool = False


class CalcRunOut(BaseModel):
    id: int
    kind: str
    account_id: int | None
    input_json: str
    result_json: str
    created_at: str
