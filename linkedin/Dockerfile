# Build context is the repository root (railway.toml sets dockerfilePath = "linkedin/Dockerfile").
FROM python:3.12-alpine

WORKDIR /app
COPY feed /app/feed
COPY linkedin/apps/linkedin-dashboard/public /app/public

ENV PORT=8080 \
    FEED_STATIC=/app/public \
    FEED_DB=/data/feed.db \
    PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "feed.service"]
