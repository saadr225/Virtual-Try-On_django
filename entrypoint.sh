#!/bin/sh
python manage.py makemigrations --noinput
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Optimized for 2 vCPU + 20 concurrent requests
# Workers: (2 x CPU) + 1 = 5 workers
# Threads: To handle I/O-bound VTON API calls
gunicorn VTON_APP.wsgi:application \
  --bind 0.0.0.0:8080 \
  --workers 5 \
  --threads 4 \
  --worker-class gthread \
  --timeout 600 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --worker-tmp-dir /dev/shm \
  --access-logfile - \
  --error-logfile -