#!/bin/bash

set -e

LATEST_TAG=$1

if [ -z "$LATEST_TAG" ]; then
  echo "Usage: $0 <latest-tag>"
  exit 1
fi

echo "Updating ec2-power-scheduler cronjob to image tag: $LATEST_TAG"

# Update the cronjob with new image
kubectl -n ec2-power-scheduler patch cronjob ec2-power-scheduler -p "{\"spec\":{\"jobTemplate\":{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"scheduler\",\"image\":\"cr.aops.tools/aops-docker-repo/ec2-power-scheduler:$LATEST_TAG\"}]}}}}}}"

echo "CronJob successfully updated!"

# Optional: Display the cronjob status
echo -e "\nCronJob status:"
kubectl -n ec2-power-scheduler get cronjob ec2-power-scheduler