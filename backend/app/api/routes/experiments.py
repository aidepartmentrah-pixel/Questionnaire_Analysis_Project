from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.services.experiment_store import (
    ExperimentModelNotFoundError,
    ExperimentNotFoundError,
    build_experiment_zip,
    get_model_artifact_path,
)

router = APIRouter(tags=["experiments"])


@router.get("/experiments/{experiment_id}/models/{model_key}/download")
def download_model(experiment_id: str, model_key: str) -> FileResponse:
    try:
        path = get_model_artifact_path(experiment_id, model_key)
    except (ExperimentNotFoundError, ExperimentModelNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=f"{model_key}.joblib",
    )


@router.get("/experiments/{experiment_id}/download")
def download_experiment(experiment_id: str) -> Response:
    try:
        zip_bytes = build_experiment_zip(experiment_id)
    except ExperimentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="experiment_{experiment_id}.zip"'},
    )
