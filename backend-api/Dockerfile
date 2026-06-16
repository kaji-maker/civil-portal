FROM python:3.11-slim

WORKDIR /app

# Copy requirements file first to utilize Docker build cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app source code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI application using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
