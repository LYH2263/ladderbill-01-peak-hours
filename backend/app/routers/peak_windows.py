from fastapi import APIRouter, HTTPException

from app.db import connect
from app.modules.peak_hours import service
from app.modules.peak_hours.schemas import PeakWindowCreate, PeakWindowUpdate
from app.modules.peak_hours.service import PeakHoursError

router = APIRouter(tags=["peak-windows"])


def _call(fn, *args):
    conn = connect()
    try:
        return fn(conn, *args)
    except PeakHoursError as e:
        raise HTTPException(e.status_code, e.message) from e
    finally:
        conn.close()


@router.get("/peak-windows")
def list_peak_windows():
    return {"items": _call(service.list_windows)}


@router.post("/peak-windows", status_code=201)
def create_peak_window(body: PeakWindowCreate):
    return _call(service.create_window, body.model_dump())


@router.put("/peak-windows/{window_id}")
def update_peak_window(window_id: int, body: PeakWindowUpdate):
    return _call(service.update_window, window_id, body.model_dump(exclude_unset=True))


@router.post("/peak-windows/{window_id}/disable")
def disable_peak_window(window_id: int):
    return _call(service.disable_window, window_id)
