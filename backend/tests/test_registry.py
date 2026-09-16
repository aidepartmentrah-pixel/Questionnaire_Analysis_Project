"""Regression test for a real environment-specific bug: XGBoost's default
n_jobs auto-detects the reported CPU count and, under Docker Desktop's
WSL2 backend on a high-core-count host, spawning that many threads for a
small fit was observed to go from ~0.1s to never completing at all (a real
hang from thread-pool contention, reproduced directly with a bare
XGBRegressor().fit() outside this project's own code). The fix is a small
fixed n_jobs on every XGBoost estimator in the registry - this test makes
sure that fix can't be silently reverted (e.g. by someone "cleaning up" what
looks like a redundant constructor argument) without a test failing.
"""

from __future__ import annotations

from app.ml.registry import CLASSIFICATION_MODELS, REGRESSION_MODELS, XGBOOST_N_JOBS


def test_xgboost_models_have_a_small_fixed_thread_count() -> None:
    xgb_regressor = next(m for m in REGRESSION_MODELS if m.key == "xgboost_regressor")
    xgb_classifier = next(m for m in CLASSIFICATION_MODELS if m.key == "xgboost_classifier")

    assert xgb_regressor.estimator_factory().n_jobs == XGBOOST_N_JOBS
    assert xgb_classifier.estimator_factory().n_jobs == XGBOOST_N_JOBS
    # The whole point of the cap: never fall back to "auto-detect all cores".
    assert XGBOOST_N_JOBS is not None
    assert 1 <= XGBOOST_N_JOBS <= 8
