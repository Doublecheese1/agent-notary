FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system agentsolis && adduser --system --ingroup agentsolis agentsolis \
    && mkdir -p /var/data/agentnotary \
    && chown -R root:root /app \
    && chmod -R a-w /app \
    && chown -R agentsolis:agentsolis /var/data/agentnotary
USER agentsolis

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
