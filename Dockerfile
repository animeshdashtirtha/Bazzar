FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install System Deps + Node.js (needed for Tailwind watcher)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && curl -sL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 3. Copy the project
COPY . .
RUN cd theme/static_src && npm install

EXPOSE 8000

# Note: Use sh -c for the command string to work properly
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]