FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=4173

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential fonts-noto-cjk fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY src ./src
COPY tools ./tools
COPY deploy ./deploy
COPY runtime.txt Procfile README.md DEPLOY.md ./

RUN mkdir -p /app/data

EXPOSE 4173

CMD ["python", "src/api_server.py"]
