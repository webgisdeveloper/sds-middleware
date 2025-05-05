#/bin/bash

SCRIPT="</path/to/house_keeper.py>"
DATA_ROOT="</path/to/mounted/staging/area>" # e.g., "/volume-mnt-point/staging"
TTL_IN_MIN=1440 # time to live in minutes
WHITE_LIST="</path/to/white_list.csv>" # e.g., path to "ISDPmetadatafilenamesforwhitelist.csv"

python $SCRIPT --dataroot $DATA_ROOT --ttl_in_min $TTL_IN_MIN --white_list $WHITE_LIST
