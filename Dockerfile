FROM python:3.12-slim

WORKDIR /code

ENV PYTHONPATH=/code
ENV PDM_CHECK_UPDATE=false

RUN pip install --no-cache-dir pdm

COPY pyproject.toml pdm.lock ./
RUN pdm install --prod --no-editable --no-self --global --project .

COPY . .

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
