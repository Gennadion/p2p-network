#!/bin/bash

# Define the name of the container you want to enter
container_name=$1

# Check if the container with the specified name is running
if docker ps -a --format '{{.Names}}' | grep -Eq "^${container_name}\$"; then
    # Enter the terminal of the container
    docker exec -it "$container_name" /bin/bash
else
    echo "Container '$container_name' not found or not running."
fi
