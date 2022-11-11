#!/bin/bash

upload_recursively() {
    BASENAME=${BASENAME:-$1}
    for sub_path in "$1"/*; do

        # Check if it's a directory
        if [ -d "$sub_path" ]; then
            upload_recursively "$sub_path"

        # Check if it's a file
        elif [ -f "$sub_path" ]; then
            RELATIVE_PATH="${sub_path##$BASENAME/}"
            echo "uploading: $RELATIVE_PATH"
            curl -X PUT -H "${HEADER}" -F json='{"backup_if_present": false}' -F file=@$sub_path https://sites.ecmwf.int/docs/pyflow/api/v1/files/$RELATIVE_PATH
        fi
    done
}

# Check if curl exists
which curl || exit 1

# Check if $TOKEN is set
if [ -z "$TOKEN" ]; then
    echo "You must set TOKEN first, i.e: export TOKEN=..."
    exit 1
fi

# Try to get path from first argument
path=""
if [ -d "$1" ]; then
    path=$1;
else
    echo "Usage: sh publish.sh /path/to/_build/html"
    exit 1
fi

export HEADER="Authorization: Bearer ${TOKEN}"

upload_recursively $path

echo Done.
