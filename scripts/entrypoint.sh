#!/bin/sh
set -eu
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if [ "${SEED_CONTENT:-true}" = "true" ]; then
  python manage.py seed_content
fi
exec "$@"
