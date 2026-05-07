#!/usr/bin/env bash
# Render (Linux): usá esto como Start Command →  bash start.sh
# Aplica migraciones sin shell manual y levanta Gunicorn.
set -o errexit

python manage.py migrate --noinput
exec gunicorn mysite.wsgi:application --bind "0.0.0.0:${PORT}"
