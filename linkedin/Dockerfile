FROM python:3.12-alpine

WORKDIR /app
COPY apps/linkedin-dashboard/public /app/public

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m http.server ${PORT:-8080} --directory /app/public"]
