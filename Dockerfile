FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# gettext: {% translate %} kataloglarını derlemek için (compilemessages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# NGINX /static/'i staticfiles/ volume'undan servis ediyor; bu adım olmadan
# eklenen her CSS/JS dosyası 404 döner ve sayfa sessizce stilsiz açılır.
# Veritabanı gerektirmez: DATABASES tembel, SECRET_KEY None olabilir.
RUN python manage.py collectstatic --noinput \
    && python manage.py compilemessages

EXPOSE 8000
