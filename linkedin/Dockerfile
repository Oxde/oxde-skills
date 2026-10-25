# Built from the staging directory feed/deploy.sh assembles: Dockerfile, railway.toml, feed/, public/.
FROM python:3.12-alpine

WORKDIR /app
COPY feed /app/feed
COPY public /app/public

ENV PORT=8080 \
    FEED_STATIC=/app/public \
    FEED_DB=/data/feed.db \
    PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "feed.service"]
