# The hosted GeoMine audit API: the lean paid-path install only (no GDAL/geo stack).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY geomine ./geomine
COPY benchmark ./benchmark

# Editable on purpose: geomine.benchmark resolves benchmark/manifest.json relative to
# the source tree, so a site-packages install would make /v1/benchmark return 503.
RUN pip install -e ".[api,audit]" \
    && useradd --create-home --uid 10001 geomine

# One BLAS/OpenMP thread per process. Without this, numpy/scipy start one thread per
# *host* core and the container's CPU quota throttles them: measured on the benchmark
# payload at 0.5 CPU, /v1/audit went from a 30s timeout to 1.1s.
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

USER geomine

# Hosts such as Render inject $PORT; 8000 is the local default.
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn geomine.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
