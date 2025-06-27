#!/usr/bin/env python3
"""
EC2 Power State Scheduler
"""

import logging
import json
from datetime import datetime, timezone
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_time(time_str):
    """Parse time string to time object"""
    try:
        from dateutil import parser
        time_str = time_str.strip().lower()
        if time_str.endswith('am') or time_str.endswith('pm'):
            if ':' not in time_str and len(time_str) <= 4:
                time_str = time_str[:-2] + ':00' + time_str[-2:]
        parsed = parser.parse(time_str)
        return parsed.time()
    except Exception as e:
        logger.error(f"Error parsing time '{time_str}': {e}")
        return None

def get_schedule_from_tags(tags):
    """Extract schedule from EC2 instance tags"""
    if not tags:
        return None
    
    on_time = None
    off_time = None
    
    for tag in tags:
        if tag['Key'] == 'PowerScheduleOnTime':
            on_time = parse_time(tag['Value'])
        elif tag['Key'] == 'PowerScheduleOffTime':
            off_time = parse_time(tag['Value'])
    
    if on_time and off_time:
        return {'start_time': on_time, 'stop_time': off_time}
    return None

def should_instance_be_running(schedule, current_time):
    """Determine if instance should be running based on schedule"""
    if not schedule:
        return None
    
    start_time = schedule['start_time']
    stop_time = schedule['stop_time']
    
    if start_time > stop_time:  # Overnight schedule
        return current_time >= start_time or current_time <= stop_time
    else:
        return start_time <= current_time <= stop_time

def main():
    """Main scheduler function"""
    import boto3
    from datetime import datetime, time
    
    ec2 = boto3.client('ec2', region_name='us-west-2')
    current_time = datetime.now().time()
    logger.info(f"Starting EC2 scheduler at {current_time}")
    
    response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'stopped']}]
    )
    
    instances_processed = instances_started = instances_stopped = 0
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            current_state = instance['State']['Name']
            tags = instance.get('Tags', [])
            
            instance_name = next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), instance_id)
            schedule = get_schedule_from_tags(tags)
            
            if not schedule:
                continue
            
            instances_processed += 1
            should_run = should_instance_be_running(schedule, current_time)
            
            if should_run and current_state == 'stopped':
                logger.info(f"Starting {instance_name}")
                ec2.start_instances(InstanceIds=[instance_id])
                instances_started += 1
            elif not should_run and current_state == 'running':
                logger.info(f"Stopping {instance_name}")
                ec2.stop_instances(InstanceIds=[instance_id])
                instances_stopped += 1
    
    logger.info(f"Completed: {instances_processed} processed, {instances_started} started, {instances_stopped} stopped")

if __name__ == '__main__':
    main() 