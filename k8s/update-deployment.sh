#!/bin/bash

set -e

# --- Configuration ---
REGISTRY="cr.aops.tools/aops-docker-repo"
IMAGE_NAME="ec2-power-scheduler"
K8S_NAMESPACE="ec2-power-scheduler"
K8S_RESOURCE_TYPE="cronjob"
K8S_RESOURCE_NAME="ec2-power-scheduler"
K8S_CONTAINER_NAME="scheduler"
# ---------------------

LATEST_TAG=$1

if [ -z "$LATEST_TAG" ]; then
  echo "Usage: $0 <latest-tag>"
  exit 1
fi

echo "Updating $K8S_RESOURCE_NAME $K8S_RESOURCE_TYPE to image tag: $LATEST_TAG"

# Update the resource with the new image
kubectl -n $K8S_NAMESPACE \
  set image ${K8S_RESOURCE_TYPE}/${K8S_RESOURCE_NAME} \
  ${K8S_CONTAINER_NAME}=${REGISTRY}/${IMAGE_NAME}:${LATEST_TAG}

echo "Resource successfully updated!"

# Optional: Display the resource status
echo -e "\nResource status:"
kubectl -n $K8S_NAMESPACE get $K8S_RESOURCE_TYPE $K8S_RESOURCE_NAME