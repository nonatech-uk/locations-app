## Stage 1: Build the React UI
FROM node:22-slim AS ui-build

WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

## Stage 2: Python API + static UI
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY scripts/ scripts/
COPY sync.sh .
COPY config.py .
COPY db.py .
COPY gps/ gps/
COPY flights/ flights/
COPY skiing/ skiing/
COPY ga/ ga/
COPY immich/ immich/
RUN chmod +x scripts/entrypoint.sh sync.sh

ENV PYTHONPATH=/app

# Copy built UI into /app/static
COPY --from=ui-build /ui/dist static/

EXPOSE 8100

CMD ["scripts/entrypoint.sh"]
