FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY router ./router

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn router.api:app --host 0.0.0.0 --port ${PORT}"]
