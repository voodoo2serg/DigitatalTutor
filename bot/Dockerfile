FROM python:3.11-slim

WORKDIR /app/bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/bot

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot_v2.py"]
