#!/bin/sh
python manage.py makemigrations --noinput
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Create cache table if using database cache
python manage.py createcachetable

python manage.py runserver
# Optimized for 2 vCPU with proper worker/thread balance
# For I/O-bound workloads (API calls to Vertex AI):
# - Fewer workers to reduce memory overhead
# - More threads per worker for concurrent I/O operations
# - Increased timeout for VTON processing
# gunicorn VTON_APP.wsgi:application \
#   --bind 0.0.0.0:8080 \
#   --workers 3 \
#   --threads 8 \
#   --worker-class gthread \
#   --timeout 900 \
#   --graceful-timeout 30 \
#   --max-requests 500 \
#   --max-requests-jitter 50 \
#   --worker-tmp-dir /dev/shm \
#   --keep-alive 5 \
#   --access-logfile - \
#   --error-logfile - \
#   --log-level info \
#   --preload