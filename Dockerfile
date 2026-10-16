FROM python:3.13-slim-trixie

# Note: this Dockerfile intentionally avoids BuildKit-only features (e.g., RUN --mount) so that it can also
# be built with Docker's classic builder, which Portainer uses when deploying through the Portainer Agent.

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN pip install "poetry==2.5.1"

WORKDIR /app

# Install dependencies first, so that this layer is cached across source-only changes
COPY poetry.lock pyproject.toml README.md /app/
RUN poetry install --only main --no-root --no-ansi

COPY ./jvc_projector /app/jvc_projector

EXPOSE 80/tcp

CMD [ "/app/.venv/bin/uvicorn", "jvc_projector.rest_server.app:proj_api", "--host", "0.0.0.0", "--port", "80" ]
