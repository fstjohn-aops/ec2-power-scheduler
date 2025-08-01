#!/bin/bash

# --- Configuration ---
IMAGE_NAME="ec2-power-scheduler"
# ---------------------

# Check if tag parameter is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <tag>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

TAG=$1

# Build x86_64 image for EKS compatibility
podman build --platform linux/amd64 -t $IMAGE_NAME:latest .

# Tag with provided tag
podman tag $IMAGE_NAME:latest $IMAGE_NAME:$TAG

# Show built images
echo "Built images:"
podman images $IMAGE_NAME 