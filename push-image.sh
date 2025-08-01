#!/bin/bash

# --- Configuration ---
REGISTRY="cr.aops.tools/aops-docker-repo"
IMAGE_NAME="ec2-power-scheduler"
# ---------------------

# Check if tag parameter is provided
if [ -z "$1" ]; then
    echo "No tag provided. Available tags in registry:"
    podman search --list-tags $REGISTRY/$IMAGE_NAME 2>/dev/null | grep -v "TAG" | head -20
    echo ""
    echo "Usage: $0 <tag>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

TAG=$1

# Build the image
echo "Building image with tag: $TAG"
./build-image.sh $TAG

# Tag for registry
echo "Tagging for registry..."
podman tag $IMAGE_NAME:$TAG $REGISTRY/$IMAGE_NAME:$TAG
podman tag $IMAGE_NAME:latest $REGISTRY/$IMAGE_NAME:latest

# Push to registry
echo "Pushing to registry..."
podman push $REGISTRY/$IMAGE_NAME:$TAG
podman push $REGISTRY/$IMAGE_NAME:latest

echo "Images pushed:"
echo "  $REGISTRY/$IMAGE_NAME:$TAG"
echo "  $REGISTRY/$IMAGE_NAME:latest"