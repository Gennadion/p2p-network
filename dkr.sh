#!/bin/bash


# Remove existing image
docker rmi $image_name

# Rebuild image
docker build -t peer .

echo "Image $image_name rebuilt successfully."
