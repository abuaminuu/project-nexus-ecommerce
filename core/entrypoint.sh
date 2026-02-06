#!/bin/bash
echo "Starting entrypoint script..."
echo "Applying database migrations..."
# in case migrations are pending or another developer makemigrations.
python manage.py migrate

# echo "starting dev server @ port 8000"
python manage.py runserver 0.0.0.0:8001
