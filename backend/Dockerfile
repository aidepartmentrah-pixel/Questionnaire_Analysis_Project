FROM python:3.11-slim

WORKDIR /app

# System deps needed to build scientific-python wheels on some platforms.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# xgboost's Linux wheel unconditionally pulls nvidia-nccl-cu12 (a ~340MB
# GPU-only library) even though we only ever run it on CPU here; it's safe
# to remove post-install (verified: CPU fit/predict work fine without it).
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y nvidia-nccl-cu12 || true

COPY app ./app

ENV APP_ENVIRONMENT=production
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
