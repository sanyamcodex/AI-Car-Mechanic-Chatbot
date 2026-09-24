#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python manage.py seed_kb
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 90
