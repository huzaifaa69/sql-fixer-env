FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY openenv.yaml .

WORKDIR /app/server

EXPOSE 7860

CMD ["python", "app.py"]