#!/bin/bash

# Number of peers to start
n=$1

# Check if the number of peers is provided
if [ -z "$n" ]; then
    echo "Usage: $0 <number_of_peers>"
    exit 1
fi

# Loop to start n peers
for ((i = 1; i <= n; i++)); do
    # Run docker container for peer$i
    docker run --name peer$i -p 800$i:8000 -v /Users/rert0/Desktop/p2p:/p2pUI/base/shared -d peer
    echo "Started peer$i"
done

echo "All peers started successfully."