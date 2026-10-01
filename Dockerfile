# Docker config
FROM python:3.11-slim

WORKDIR /app

ARG USER=appuser

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos "" --home /home/${USER} ${USER} || true
RUN chown -R ${USER}:${USER} /app

USER ${USER}

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
	CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]