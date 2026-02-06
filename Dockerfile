# first docker build -t project-nexus-ecommerce:latest

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. FIRST install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. THEN install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip setuptools
RUN pip install -r requirements.txt

# 3. Copy application code
COPY . .

EXPOSE 8001

CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]
