#!/bin/sh
# Apply database migrations, then serve the API.
# (Render's free plan has no pre-deploy step, so migrations run here;
# with a single instance that is safe. Move them to a release job when scaling out.)
set -eu

alembic upgrade head

# --proxy-headers: trust X-Forwarded-For from the host's proxy so rate limits
# see the real client. FORWARDED_ALLOW_IPS must name that proxy (or "*" when
# the container is reachable only through it, as on Render).
exec uvicorn langex.api.app:create_app --factory \
    --host 0.0.0.0 --port "${PORT:-8000}" \
    --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
    --no-server-header
