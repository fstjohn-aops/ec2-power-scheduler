# EC2 Power State Scheduler

A Kubernetes-based solution for automatically starting and stopping EC2 instances based on schedule tags. This tool helps reduce AWS costs by ensuring instances are only running during specified time periods.

## Features

- **Automated Scheduling**: Runs as a Kubernetes CronJob every 15 minutes
- **Flexible Time Formats**: Supports various time formats including 12/24 hour notation
- **Multi-Region Support**: Automatically detects and uses appropriate timezones for AWS regions
- **Overnight Schedules**: Supports schedules that cross midnight (e.g., 10 PM to 6 AM)
- **Structured Logging**: JSON-formatted logs for better observability and integration with log aggregation systems
- **Comprehensive Testing**: Unit and integration tests with coverage reporting
- **Pod Identity**: Uses EKS Pod Identity for secure AWS authentication

## How It Works

The scheduler runs as a Kubernetes CronJob every 15 minutes, checking EC2 instances for `PowerScheduleOnTime` and `PowerScheduleOffTime` tags and enforcing the schedules based on the current time in the instance's region.

### Schedule Logic

- **Normal Schedule**: When start time < stop time (e.g., 9 AM to 5 PM)
  - Instance should be running when current time is between start and stop times
- **Overnight Schedule**: When start time > stop time (e.g., 10 PM to 6 AM)
  - Instance should be running when current time is after start time OR before stop time

## Schedule Format

Set EC2 tags on your instances:
- `PowerScheduleOnTime`: Start time for the instance
- `PowerScheduleOffTime`: Stop time for the instance

### Supported Time Formats

- `"9am"`, `"5:30pm"`, `"17:30"`
- `"09:00"`, `"5pm"`, `"6:30am"`
- `"06:30"`, `"9:00 AM"`, `"05:30 PM"`

### Examples

```bash
# Tag an instance for 9 AM to 5 PM schedule
aws ec2 create-tags --resources i-1234567890abcdef0 \
  --tags Key=PowerScheduleOnTime,Value="9am" \
         Key=PowerScheduleOffTime,Value="5pm"

# Tag an instance for overnight schedule (10 PM to 6 AM)
aws ec2 create-tags --resources i-1234567890abcdef0 \
  --tags Key=PowerScheduleOnTime,Value="10pm" \
         Key=PowerScheduleOffTime,Value="6am"
```

## Prerequisites

- EKS cluster with Pod Identity enabled
- IAM role with EC2 permissions (see `eks/00-podIdentityAssociation.yml`)
- Container registry access (default: `cr.aops.tools/aops-docker-repo`)

## Deployment

### 1. Build and Push Docker Image

```bash
# Build and push image with version tag
./build-image.sh v1.0.0
./push-image.sh v1.0.0
```

### 2. Deploy to Kubernetes

```bash
# Create namespace and service account
kubectl apply -f k8s/00-namespace.yml
kubectl apply -f k8s/01-serviceaccount.yml

# Deploy the CronJob
kubectl apply -f k8s/02-cronjob.yml

# Set up Pod Identity (if using eksctl)
kubectl apply -f eks/00-podIdentityAssociation.yml
```

### 3. Update Deployment (for new versions)

```bash
# Update to a new image version
./k8s/update-deployment.sh 1.0.0
```

## Configuration

### Environment Variables

- `AWS_REGION`: AWS region to operate in (default: `us-west-2`)
- `REGISTRY`: Container registry URL (default: `cr.aops.tools/aops-docker-repo`)

### CronJob Schedule

The default schedule runs every 15 minutes. You can modify this in `k8s/02-cronjob.yml`:

```yaml
spec:
  schedule: "*/15 * * * *"  # Every 15 minutes
```

### Resource Limits

The CronJob is configured with conservative resource limits:
- CPU: 50m request, 100m limit
- Memory: 64Mi request, 128Mi limit

## Monitoring and Logging

### Log Format

The application outputs structured JSON logs with the following fields:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (INFO, ERROR, etc.)
- `component`: Component identifier (scheduler_start, instance_processing, etc.)
- `message`: Human-readable message
- `instance_name`: EC2 instance name
- `instance_id`: EC2 instance ID
- `current_state`: Current instance state
- `action`: Action taken (start, stop, none)
- `instances_processed`: Number of instances processed
- `instances_started`: Number of instances started
- `instances_stopped`: Number of instances stopped

### Viewing Logs

```bash
# View logs from the latest job
kubectl -n ec2-power-scheduler logs -l job-name=ec2-power-scheduler

# Follow logs in real-time
kubectl -n ec2-power-scheduler logs -f -l job-name=ec2-power-scheduler

# View CronJob status
kubectl -n ec2-power-scheduler get cronjob ec2-power-scheduler
```

## Testing

### Run Tests

```bash
# Run all tests with coverage
./test.sh

# Or run directly with pytest
pytest test/ -v --cov=app --cov-report=html
```

### Test Coverage

The test suite includes:
- **Unit Tests**: Time parsing, schedule logic, JSON logging
- **Integration Tests**: AWS API interactions, main function workflow
- **Coverage Reporting**: HTML and terminal coverage reports

### Test Structure

- `test/test_time_utils.py`: Time parsing and schedule logic tests
- `test/test_scheduler.py`: Main scheduler integration tests
- `test/test_json_logging.py`: Structured logging tests

## Security

### IAM Permissions

The application requires the following AWS permissions:
- `ec2:*` - Full EC2 access for starting/stopping instances
- `kms:*` - KMS permissions for encrypted resources
- `iam:PassRole` - For passing IAM roles to EC2 instances

### Pod Identity

The application uses EKS Pod Identity for secure AWS authentication, eliminating the need for IAM roles attached to EC2 nodes.

## Troubleshooting

### Common Issues

1. **Instances not starting/stopping**
   - Verify tags are correctly formatted
   - Check timezone settings for your region
   - Review logs for parsing errors

2. **Permission errors**
   - Ensure Pod Identity is properly configured
   - Verify IAM permissions are correct
   - Check service account configuration

3. **CronJob not running**
   - Verify the CronJob is not suspended
   - Check for failed jobs in the namespace
   - Review resource limits and requests

### Debug Mode

To enable debug logging, modify the CronJob to set the log level:

```yaml
env:
- name: LOG_LEVEL
  value: "DEBUG"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 