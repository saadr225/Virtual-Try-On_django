#!/bin/sh
python manage.py makemigrations --noinput
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Use gunicorn instead of runserver for production
gunicorn VTON_APP.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 300 --max-requests 1000