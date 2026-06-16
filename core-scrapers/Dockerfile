FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Copy requirements file first to utilize Docker build cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy scraper source code
COPY . .

# Start scraper script
CMD ["python", "scraper_procure.py"]
