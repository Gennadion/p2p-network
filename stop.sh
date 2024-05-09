#!/bin/bash

# Stop and remove all containers
docker rm -f $(docker ps -aq)

echo "All peer containers stopped and removed successfully."