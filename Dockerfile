FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY technews_briefing ./technews_briefing

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /var/lib/technews/data

EXPOSE 8080

CMD ["python", "-m", "technews_briefing.deployment", "serve", "--host", "0.0.0.0", "--port", "8080"]
