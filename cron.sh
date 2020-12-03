#!/bin/sh
set -e
printenv > .env
[ -p /var/log/cron.log ] || mkfifo /var/log/cron.log
service cron start
cat <> /var/log/cron.log