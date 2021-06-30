#!/usr/bin/env bash

exec /usr/sbin/rotki --rest-api-port 4242 --websockets-api-port 4243 --data-dir /data/ --logfile /logs/rotki.log --api-cors http://localhost:*/*,app://. --api-host 0.0.0.0 &

status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start rotki: $status"
  exit $status
fi

nginx -g "daemon off;" &

status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start nginx: $status"
  exit $status
fi

echo "Service started"

while sleep 60; do
  ps aux | grep "rotki" | grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux | grep "nginx: master" | grep -q -v grep
  PROCESS_2_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 ]; then
    echo "One of the processes has already exited."
    exit 1
  fi
done
