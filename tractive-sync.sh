#!/bin/bash
# Daily Tractive GPS sync - standalone entrypoint inside container

cd /app
set -a; source /app/.env; set +a

python3 /app/tractive/tractive_sync.py --daily
