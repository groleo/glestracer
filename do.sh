#! /bin/bash

#export PYTHONPATH=`pwd`/gen:${HOME}/s/a/jb/internal/development/testrunner

./gltrace.py -i ~/trace-mesa.gltrace > log
sort -n -r log > mesa-sorted.log
rm log

./gltrace.py -i ~/trace-ufo.gltrace > log
sort -n -r ufo-log > ufo-sorted.log
rm log
