FROM python:3.11-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.6.1

# Copy project dependencies
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-root --without dev,docs

# Copy project source
COPY ztoq ./ztoq
COPY README.md ./

# Install project
RUN poetry install --no-interaction --only-root

FROM python:3.11-slim

WORKDIR /app

# Copy installed packages and source from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Run as non-root user
RUN useradd -m ztoq
USER ztoq

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Command to run the application
ENTRYPOINT ["ztoq"]
CMD ["--help"]
