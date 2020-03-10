#!/usr/bin/env bash

exec /usr/sbin/rotki --api-port 4242 --data-dir /data/ --logfile /logs/rotki.log --api-cors http://localhost:8080 --api-host 0.0.0.0 &

status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start rotki: $status"
  exit $status
fi

nginx -g "daemon off;"

status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start nginx: $status"
  exit $status
fi