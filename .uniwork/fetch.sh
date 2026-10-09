#!/bin/bash
# $1 = output name, $2 = url
curl -sS -m 40 -A "Mozilla/5.0" -o "$1.html" "$2" && python3 x.py "$1.html" > "$1.txt" 2>/dev/null
echo "$1: $(wc -c < "$1.txt" 2>/dev/null) bytes  <- $2"
