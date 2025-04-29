FROM python:3.11
WORKDIR /app
COPY pyproject.toml poetry.lock README.md ./
RUN pip install poetry  && poetry install --no-root
COPY . .
CMD ["poetry run python3 -m feedscoring.main"]