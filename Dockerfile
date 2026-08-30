# syntax=docker/dockerfile:1

# basamento-synapsys is installed from PyPI, exactly as a user would install it.

FROM python:3.12-slim AS build

WORKDIR /src

COPY pyproject.toml README.md ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-compile --prefix=/install .

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=build /install /usr/local

RUN useradd --system --uid 10001 worker

USER worker

EXPOSE 3004

CMD ["synapsys-python-example"]
