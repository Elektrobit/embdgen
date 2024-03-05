#!/bin/bash

BASEDIR=$(dirname $(readlink -f $(dirname $0)))

cd $BASEDIR
for d in embdgen-*; do
    echo "mypy $d"
    (
        cd $d
        mypy src
    )
done
