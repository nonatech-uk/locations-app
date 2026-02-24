#!/bin/bash
# Daily FollowMee sync with healthcheck pings

cd /app
set -a; source /app/.env; set +a

curl -fsS -m 10 --retry 5 "${HC_URL}/start" > /dev/null 2>&1

if python3 /app/gps/followmee_sync.py --daily >> /var/log/sync.log 2>&1; then
    curl -fsS -m 10 --retry 5 "${HC_URL}" > /dev/null 2>&1
else
    curl -fsS -m 10 --retry 5 "${HC_URL}/fail" > /dev/null 2>&1
fi
