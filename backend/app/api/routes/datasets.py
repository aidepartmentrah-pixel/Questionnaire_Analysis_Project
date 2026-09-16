import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.core.config import Settings, get_settings
from app.schemas.config import PreprocessingPreview, PreprocessingRequest
from app.schemas.dataset import DatasetSummary
from app.schemas.profile import DatasetProfileResponse
from app.services import dataset_store
from app.services.config_validation import ConfigValidationError, build_preprocessing_preview
from app.services.csv_validation import DatasetValidationError, validate_and_parse_csv
from app.services.dataset_profile import build_dataset_profile
from app.services.dataset_store import ActiveDataset, DatasetNotFoundError
from app.services.dataset_summary import build_dataset_summary
from app.services.eda_report import render_eda_report_html

router = APIRouter(tags=["datasets"])


def _get_dataset_or_404(dataset_id: str) -> ActiveDataset:
    try:
        return dataset_store.get_dataset_or_raise(dataset_id)
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/datasets/upload", response_model=DatasetSummary)
async def upload_dataset(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> DatasetSummary:
    raw_bytes = await file.read()
    filename = file.filename or "upload.csv"

    try:
        df = validate_and_parse_csv(filename, raw_bytes, settings.max_upload_size_bytes)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    active = dataset_store.set_active_dataset(
        filename=filename, dataframe=df, raw_csv_bytes=raw_bytes
    )
    return build_dataset_summary(active)


@router.get("/datasets/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(dataset_id: str) -> DatasetProfileResponse:
    active = _get_dataset_or_404(dataset_id)
    return build_dataset_profile(active)


@router.get("/datasets/{dataset_id}/profile/report")
def download_eda_report(dataset_id: str) -> HTMLResponse:
    active = _get_dataset_or_404(dataset_id)
    profile = build_dataset_profile(active)
    html_content = render_eda_report_html(profile)

    safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(active.filename).stem) or "dataset"
    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="eda_report_{safe_stem}.html"'},
    )


@router.post("/datasets/{dataset_id}/preprocessing-preview", response_model=PreprocessingPreview)
def preview_preprocessing(dataset_id: str, request: PreprocessingRequest) -> PreprocessingPreview:
    active = _get_dataset_or_404(dataset_id)
    try:
        return build_preprocessing_preview(active, request)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
