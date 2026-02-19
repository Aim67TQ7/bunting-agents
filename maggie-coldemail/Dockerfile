FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

RUN mkdir -p /app/logs /app/data
RUN useradd -m -r maggie && chown -R maggie:maggie /app
USER maggie

EXPOSE 8408

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8408", "--log-level", "info"]
