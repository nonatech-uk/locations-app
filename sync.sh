#!/bin/bash
# Daily FollowMee sync - invoked by Cronicle

cd /app
set -a; source /app/.env; set +a

python3 /app/gps/followmee_sync.py --daily
