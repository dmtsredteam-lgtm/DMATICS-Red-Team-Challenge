FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DB_PATH=/app/data/leaderboard.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

EXPOSE 8000

# Sessions are signed client-side cookies, so 2 workers is totally fine.
# (Just make sure SECRET_KEY is set in the environment - compose does that.)
CMD ["gunicorn", "-w", "2", "--threads", "4", "-b", "0.0.0.0:8000", "app:app"]
