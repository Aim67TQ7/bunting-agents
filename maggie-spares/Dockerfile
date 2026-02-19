FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

# Create logs directory
RUN mkdir -p /app/logs

# Non-root user for security
RUN useradd -m -r maggie && chown -R maggie:maggie /app
USER maggie

EXPOSE 8402

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8402", "--log-level", "info"]
