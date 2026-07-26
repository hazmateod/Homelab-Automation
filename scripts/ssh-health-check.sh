#!/bin/bash

echo "================================="
echo " Homelab SSH Health Check"
echo " $(date)"
echo "================================="

HOSTS=(
10.10.37.50
10.10.37.51
10.10.37.52
10.10.37.9
)

for HOST in "${HOSTS[@]}"
do
    echo
    echo "Checking $HOST"

    ssh -o ConnectTimeout=5 root@$HOST \
    "hostname && uptime"

    if [ $? -eq 0 ]; then
        echo "STATUS: ONLINE"
    else
        echo "STATUS: FAILED"
    fi

    echo "---------------------------------"
done
