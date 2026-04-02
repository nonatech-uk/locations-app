#!/bin/bash
# Strava activity sync — invoked by Cronicle nightly
# Fetches new activities, inserts GPS points, posts to journal ingest

cd /app
set -a; source /app/.env; set +a

# Healthcheck UUID — create on hc.mees.st and replace this placeholder
HC_UUID="${STRAVA_HC_UUID:-}"
HC_URL="https://hc.mees.st/ping"

# Ping start
[ -n "$HC_UUID" ] && curl -fsS -m 10 --retry 3 "$HC_URL/$HC_UUID/start" > /dev/null 2>&1

# Run sync
python3 -m strava.sync
rc=$?

# Ping result
[ -n "$HC_UUID" ] && curl -fsS -m 10 --retry 3 "$HC_URL/$HC_UUID/$rc" > /dev/null 2>&1

exit $rc
