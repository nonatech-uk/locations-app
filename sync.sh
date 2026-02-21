#!/bin/bash
# Daily FollowMee sync with healthcheck pings

HC_URL="https://hc.mees.st/ping/32960f21-f84a-4635-9de5-94dfbca6e16c"

curl -fsS -m 10 --retry 5 "${HC_URL}/start" > /dev/null 2>&1

if PYTHONPATH=/app /usr/local/bin/python3 /app/gps/followmee_sync.py --daily >> /var/log/sync.log 2>&1; then
    curl -fsS -m 10 --retry 5 "${HC_URL}" > /dev/null 2>&1
else
    curl -fsS -m 10 --retry 5 "${HC_URL}/fail" > /dev/null 2>&1
fi
