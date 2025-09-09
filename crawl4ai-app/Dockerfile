FROM python:3.10-slim

WORKDIR /app

# Cài crawl4ai
RUN pip install --no-cache-dir crawl4ai && \
    pip install --no-cache-dir playwright && \
    playwright install --with-deps chromium

# Copy code vào container (nếu muốn)
COPY . /app

CMD ["python", "main.py"]