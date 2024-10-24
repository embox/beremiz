#!/bin/bash

# Run python example throug command line, and check usual output

coproc setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -k --project-home $BEREMIZPATH/tests/projects/modbus_test_tcp build transfer run;

while read -u ${COPROC[0]} line; do 
    echo "$line"
    if [[ "$line" == "TEST OK" ]]; then
        pkill -9 -s $COPROC_PID 
        exit 0
    fi
done

exit 42
