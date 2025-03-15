#!/bin/bash

# Build the Docker image
echo "Building Docker image..."
docker build -t milpsoft-optimizer .

# Determine the parent directory path for mounting
PARENT_DIR=$(dirname "$(pwd)")
CURRENT_DIR=$(pwd)

# Run the container with volumes mounted to ensure access to all files
echo "Running optimization pipeline in Docker container..."
docker run --rm \
  -v "$CURRENT_DIR:/app" \
  -v "$PARENT_DIR:/app/parent" \
  milpsoft-optimizer
