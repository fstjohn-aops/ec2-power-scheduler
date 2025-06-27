# EC2 Power State Scheduler

Automatically starts and stops EC2 instances based on schedule tags.

## How it works

Runs as a Kubernetes CronJob every 5 minutes, checking EC2 instances for `PowerScheduleOnTime` and `PowerScheduleOffTime` tags and enforcing the schedules.

## Schedule Format

Set EC2 tags:
- `PowerScheduleOnTime`: `"9am"`, `"5:30pm"`, `"17:30"`
- `PowerScheduleOffTime`: `"5pm"`, `"6:30am"`, `"06:30"`

## Deployment

```bash
# Build and push image
./build-image.sh v1.0.0
./push-image.sh v1.0.0

# Deploy to cluster
kubectl apply -f k8s/
kubectl apply -f eks/

# Update deployment
./k8s/update-deployment.sh v1.0.0
```

## Requirements

- EKS cluster with pod identity enabled
- IAM role with EC2 permissions 