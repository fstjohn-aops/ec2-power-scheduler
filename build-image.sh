#!/bin/bash

# Check if tag parameter is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <tag>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

TAG=$1

# Build x86_64 image for EKS compatibility
podman build --platform linux/amd64 -t ec2-power-scheduler:latest .

# Tag with provided tag
podman tag ec2-power-scheduler:latest ec2-power-scheduler:$TAG

# Show built images
echo "Built images:"
podman images ec2-power-scheduler 