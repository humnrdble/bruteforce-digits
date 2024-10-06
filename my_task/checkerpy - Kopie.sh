#!/bin/bash
#https://askubuntu.com/a/1419701
if [ $(/bin/pgrep -f "checker.py") ]; then
    echo "An instance of the answer checker is already running"
else
    # Command when the script is not running
	python /home/simon/checker.py
fi