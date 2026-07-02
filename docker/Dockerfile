FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV DJANGO_SETTINGS_MODULE=config.settings.production

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN npm run build:css

RUN DJANGO_SECRET_KEY=collectstatic-placeholder \
    DJANGO_ALLOWED_HOSTS=localhost \
    DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput

RUN chmod +x docker/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8080", "config.asgi:application"]
