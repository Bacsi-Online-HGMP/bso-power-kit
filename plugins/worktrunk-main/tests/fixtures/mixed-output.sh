#!/bin/bash
# Test script that outputs to both stdout and stderr
# Usage: mixed-output.sh <name> <count>

NAME="${1:-test}"
COUNT="${2:-5}"

for i in $(seq 1 "$COUNT"); do
    echo "[$NAME] stdout line $i"
    echo "[$NAME] stderr line $i" >&2
done

echo "[$NAME] stdout complete"
echo "[$NAME] stderr complete" >&2
