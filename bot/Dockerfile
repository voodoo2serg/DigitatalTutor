FROM python:3.11-slim

WORKDIR /app/bot

RUN pip install --no-cache-dir \
    aiogram==3.4.1 \
    sqlalchemy==2.0.27 \
    asyncpg==0.29.0 \
    httpx==0.27.0 \
    python-dotenv==1.0.0

COPY . /app/bot

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot_v2.py"]
