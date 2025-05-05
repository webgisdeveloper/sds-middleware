#!/bin/bash

echo "Going to kill currently running hsi processes"

PIDS=`pgrep -f -u rdsisdp "<path/to/hpss/bin/hsi>"`

for PID in $PIDS
do
	echo "Killing hsi with PID: $PID"
	kill -9 $PID
done

