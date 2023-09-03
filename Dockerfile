FROM python:3.10-slim-buster

ENV PATH="/root/.local/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl


RUN curl -sSL 'https://install.python-poetry.org' | python3 - && poetry --version


RUN apt-get remove -y curl \
 && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
 && apt-get clean -y && rm -rf /var/lib/apt/lists/* \
 && rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml README.md /app/

WORKDIR /app

COPY ./jvc_projector /app/jvc_projector

RUN poetry config virtualenvs.in-project true

EXPOSE 8000/tcp

RUN poetry install --no-dev --no-interaction --no-ansi -vvv

CMD [ "/app/.venv/bin/uvicorn", "jvc_projector.rest_server.app:proj_api", "--host", "0.0.0.0", "--port", "80" ]
