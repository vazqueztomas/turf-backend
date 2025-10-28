import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from turf_backend.controllers import process_pdfs_and_update_db

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/turf", tags=["Turf Daily Update"])


@router.post("/daily-update")
def trigger_daily_update(background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(process_pdfs_and_update_db)
    except Exception as e:
        msg_error = f"No se pudo iniciar el proceso: {e}"
        logger.exception(msg_error)
        raise HTTPException(status_code=500, detail=msg_error)  # noqa: B904
    return {"message": "🚀 Daily update iniciado en background."}
