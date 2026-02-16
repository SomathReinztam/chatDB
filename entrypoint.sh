#!/bin/bash
set -e

echo "Running database initialization..."
python3 -m src.database.crud.crud

echo "Starting Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisord.conf