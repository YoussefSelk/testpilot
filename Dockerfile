FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/testpilot
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install . "pytest>=8.3,<10" \
    && useradd --create-home --uid 10001 testpilot \
    && mkdir /workspace \
    && chown testpilot:testpilot /workspace

USER testpilot
WORKDIR /workspace
ENTRYPOINT ["testpilot"]
CMD ["--help"]
