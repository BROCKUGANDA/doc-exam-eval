# Evaluation image: the benchmark runs here with no keys, no database and no network
# dependency for --validate. That is the reproducibility guarantee judges are asked to
# check from a clean environment, so the image deliberately contains nothing else.
FROM python:3.13-slim AS eval

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# fpdf2 renders synthetic PDFs for the optional document track; it needs no system libs.
WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY run_eval.py pytest.ini ./
COPY benchmark ./benchmark
COPY tests ./tests

# Generated at build time so the image proves its own claims rather than trusting a
# committed artifact that could have drifted from the code.
RUN python run_eval.py --validate

CMD ["python", "run_eval.py", "--validate"]

# Test image: the benchmark stages plus the parts of the repo the platform and edge tests
# read. Kept as a second target so `eval` stays minimal — the artifact a judge builds to
# reproduce a result should not carry FastAPI or a Caddyfile.
#
# tests/test_submission.py is deliberately absent from the container run: it packs the
# working tree with `git ls-files`, and a container built from an image has no repository
# metadata to list. That is disclosed in docker-compose.yml rather than papered over with a
# skip marker that would make a zero-test run look like a passing one.
FROM eval AS testenv

COPY backend ./backend
COPY scripts ./scripts
COPY infra ./infra
COPY README.md docker-compose.yml .env.example ./
RUN pip install --no-cache-dir -r backend/requirements.txt

CMD ["python", "-m", "pytest", "tests", "-q", "--ignore=tests/test_submission.py"]
