from fastapi import APIRouter, HTTPException

from app.schemas.config import TaskType
from app.schemas.training import TrainingRequest, TrainingResponse
from app.services import dataset_store
from app.services.classification_training import run_classification_training
from app.services.clustering_training import run_clustering_training
from app.services.config_validation import ConfigValidationError
from app.services.dataset_profile import build_dataset_profile
from app.services.dataset_store import DatasetNotFoundError
from app.services.eda_report import render_eda_report_html
from app.services.experiment_store import persist_experiment
from app.services.regression_training import run_regression_training
from app.services.training_run import TrainingRun

router = APIRouter(tags=["training"])


@router.post("/datasets/{dataset_id}/train", response_model=TrainingResponse)
def train_models(dataset_id: str, request: TrainingRequest) -> TrainingResponse:
    try:
        active = dataset_store.get_dataset_or_raise(dataset_id)
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        run: TrainingRun | None = None
        if request.task == TaskType.regression:
            run = run_regression_training(active, request)
        elif request.task == TaskType.classification:
            run = run_classification_training(active, request)
        elif request.task == TaskType.clustering:
            run = run_clustering_training(active, request)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    if run is None:
        raise HTTPException(
            status_code=501,
            detail=f"{request.task.value.capitalize()} training is not implemented yet.",
        )

    if run.response.winner_key is not None:
        eda_html = render_eda_report_html(build_dataset_profile(active))
        run.response.experiment_id = persist_experiment(
            dataset_filename=active.filename,
            response=run.response,
            fitted_pipelines=run.fitted_pipelines,
            eda_report_html=eda_html,
        )

    return run.response
