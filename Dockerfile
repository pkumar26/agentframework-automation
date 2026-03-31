FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .
RUN uv pip install --system --no-cache --prerelease allow -e .

EXPOSE 8088

CMD ["python", "app.py"]
