FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME_DASH_REFRESH_INTERVAL_SECONDS=5

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

RUN mkdir -p /app/data

COPY app ./app
COPY templates ./templates
COPY static ./static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

