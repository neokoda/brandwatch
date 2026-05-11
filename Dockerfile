FROM python:3.11-slim

WORKDIR /app

# Build tools needed for umap-learn, hdbscan, and numpy extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend package
COPY backend/ ./backend/

# Cloud Run injects PORT; default to 8080
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
