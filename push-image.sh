#!/bin/bash

set -e

LATEST_TAG=$1

if [ -z "$LATEST_TAG" ]; then
  echo "Usage: $0 <latest-tag>"
  exit 1
fi

echo "Pushing ec2-power-scheduler image with tag: $LATEST_TAG"

# Push the Docker image
docker push cr.aops.tools/aops-docker-repo/ec2-power-scheduler:$LATEST_TAG

echo "Image pushed successfully!" 