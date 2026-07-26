#!/bin/bash

HOSTS=(
"10.10.37.50"
"10.10.37.51"
"10.10.37.52"
"10.10.37.9"
)

for HOST in "${HOSTS[@]}"
do
    echo "Checking $HOST"

    ssh -o ConnectTimeout=5 root@$HOST "hostname && uptime" \
    && echo "SUCCESS $HOST" \
    || echo "FAILED $HOST"

    echo "---------------------"
done
