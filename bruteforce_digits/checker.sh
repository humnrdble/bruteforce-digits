#!/bin/bash
# Forwards the query to the root-owned checker server (see checker.py); the answer is not readable from here.
if [ "$#" -gt 0 ]; then
    userinput="$1"
else
    echo "Check your answer:"
    IFS= read -r userinput
fi
userinput=${userinput//$'\n'/}
userinput=${userinput//$'\r'/}

if ! exec 3<>/dev/tcp/127.0.0.1/7117; then
    echo "checker unavailable" >&2
    exit 2
fi
printf '%s\n' "$userinput" >&3
IFS= read -r reply <&3
exec 3>&-

echo "$reply"
if [ "$reply" = "malformed query" ]; then
    exit 1
fi
