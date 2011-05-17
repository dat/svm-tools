#!/usr/bin/env bash

#Alias tool names into current shell.
#author: dth

if [ "$1" = "-h" -o "$1" = "--help" ]
then
    echo "Usage: . ./aliasing.sh" > /dev/stderr
    echo "This will load all aliases for the scripts into the current shell." > /dev/stderr
    exit 1
fi

#alias svm-train='~/svm/svm-train'
#alias svm-predict='~/svm/svm-predict'
#alias svm-scale='~/svm/svm-scale'

dir="$(cd `dirname $0` && pwd)"
alias arff2svm="$dir/arff2svm.py"
alias shuffle="$dir/shuffle.sh"
alias report="$dir/report.py"
alias grid-search="$dir/grid-search.py"
alias svm-remap="$dir/svm-remap.py"

