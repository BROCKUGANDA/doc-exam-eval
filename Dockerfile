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
