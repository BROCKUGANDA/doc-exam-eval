# Artifact API for the examination console. Separate image from the eval image on purpose:
# the benchmark proof must stay installable with `pip install -r requirements.txt` and no
# FastAPI, because that is what a judge runs from a clean clone.
#
# Build context is the repository root (see docker-compose.yml), so .dockerignore governs
# what actually lands here — benchmark/results/runs/ and transcripts/ are excluded, which is
# the point: a container built from a clean clone serves the committed results and reports
# the trial journals as absent rather than pretending to have data it never shipped.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/docx

# Both requirement sets: the API reads and grades through the benchmark package.
# Copied to distinct paths — flattening them into one directory made
# `pip install -r backend/requirements.txt` fail, because COPY of two sources into `./`
# puts both files at the root and there is no backend/ directory yet at that point.
COPY requirements.txt ./requirements.txt
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r backend-requirements.txt

COPY run_eval.py pytest.ini ./
COPY benchmark ./benchmark
COPY backend ./backend

# The task pack is derived from seeds, so it is generated rather than copied. This also makes
# the image prove the generator runs in this environment instead of trusting the host's tree.
RUN python run_eval.py --offline

# Nothing in the request path writes. The store is read-only by construction, so the container
# can run unprivileged and with a read-only root filesystem.
RUN useradd --create-home --uid 10001 docx
USER docx

EXPOSE 8010

HEALTHCHECK --interval=20s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/healthz', timeout=2)"]

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8010"]
