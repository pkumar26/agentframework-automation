FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy source and install
COPY . .
RUN uv pip install --system --no-cache --prerelease allow -e .

EXPOSE 8088

# Health check for ACA
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8088/')" || exit 1

CMD ["python", "app.py"]
