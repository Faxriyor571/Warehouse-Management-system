# Production image for the Warehouse Management System API.
FROM python:3.13-slim AS base

# - PYTHONDONTWRITEBYTECODE: no .pyc files in the image
# - PYTHONUNBUFFERED: stream logs straight to the console
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application source.
COPY . .

# Runtime data directories (also created by the app, kept here for clarity).
RUN mkdir -p uploads logs

EXPOSE 8000

# Uses the app's built-in startup (create tables + seed) via the lifespan.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
