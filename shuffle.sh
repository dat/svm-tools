#!/usr/bin/env bash

#Simple script to shuffle all lines in a text file.

if [ $# -ne 1 -o "$1" = "-h" -o "$1" = "--help" ]
then
    echo "Usage: $0 <file>" > /dev/stderr
    echo "<file> := file to be shuffled by line" > /dev/stderr
    exit 1
fi

tmp=`mktemp`
cat $1 | while read line; do
    echo "$RANDOM#$line"
done | sort | cut -d'#' -f 2- > $tmp
cp $tmp $1

rm -f $tmp
exit 0
