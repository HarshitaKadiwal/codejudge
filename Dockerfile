FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt \
	&& groupadd --system app \
	&& useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY app.py ./
COPY database/ ./database/
COPY judge/ ./judge/
COPY templates/ ./templates/
COPY static/ ./static/

RUN chown -R app:app /app

USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"

CMD ["python", "app.py"]