from fastapi import APIRouter, HTTPException

from app.modules.peak_hours.matcher import PeakWindowConflict
from app.schemas.peak_hours import PeakWindowCreate, PeakWindowOut, PeakWindowUpdate
from app.services.peak_hours_service import PeakHoursService

router = APIRouter(prefix="/peak-windows", tags=["peak-hours"])


@router.get("")
def list_windows(enabled_only: bool = False):
    with PeakHoursService() as svc:
        return {"items": svc.list_windows(enabled_only=enabled_only)}


@router.post("", response_model=PeakWindowOut, status_code=201)
def create_window(body: PeakWindowCreate):
    with PeakHoursService() as svc:
        try:
            return svc.create_window(body.model_dump())
        except PeakWindowConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@router.put("/{window_id}", response_model=PeakWindowOut)
def update_window(window_id: int, body: PeakWindowUpdate):
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "没有需要更新的字段")
    with PeakHoursService() as svc:
        try:
            return svc.update_window(window_id, changes)
        except KeyError as exc:
            raise HTTPException(404, f"时段 #{window_id} 不存在") from exc
        except PeakWindowConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@router.post("/{window_id}/disable", response_model=PeakWindowOut)
def disable_window(window_id: int):
    with PeakHoursService() as svc:
        try:
            return svc.disable_window(window_id)
        except KeyError as exc:
            raise HTTPException(404, f"时段 #{window_id} 不存在") from exc
