FROM python:3.12.3-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN playwright install chromium --with-deps

RUN apt-get update && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]