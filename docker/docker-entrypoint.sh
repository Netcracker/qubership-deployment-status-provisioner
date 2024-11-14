#!/bin/bash

sleep ${INITIAL_WAIT:-30}
echo "Status Provisioner have started calculating the state of the cluster"
exec python ${STATUS_PROVISIONER_HOME}/status_provisioner.py $@