#!/usr/bin/env python3
"""
EC2 Power State Scheduler
"""

import logging
import json
import datetime
import os
import pytz
import requests

# Configure structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    def format(self, record):
        # Convert plain text logs to structured JSON format
        log_data = {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'pod_name': os.environ.get('HOSTNAME', 'unknown'),
            'namespace': os.environ.get('POD_NAMESPACE', 'unknown'),
            'deployment': os.environ.get('DEPLOYMENT_NAME', 'unknown')
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'component'):
            log_data['component'] = record.component
        if hasattr(record, 'instance_name'):
            log_data['instance_name'] = record.instance_name
        if hasattr(record, 'instance_id'):
            log_data['instance_id'] = record.instance_id
        if hasattr(record, 'current_state'):
            log_data['current_state'] = record.current_state
        if hasattr(record, 'start_time'):
            log_data['start_time'] = record.start_time
        if hasattr(record, 'stop_time'):
            log_data['stop_time'] = record.stop_time
        if hasattr(record, 'current_time'):
            log_data['current_time'] = record.current_time
        if hasattr(record, 'timezone'):
            log_data['timezone'] = record.timezone
        if hasattr(record, 'region'):
            log_data['region'] = record.region
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'should_run'):
            log_data['should_run'] = record.should_run
        if hasattr(record, 'instances_processed'):
            log_data['instances_processed'] = record.instances_processed
        if hasattr(record, 'instances_started'):
            log_data['instances_started'] = record.instances_started
        if hasattr(record, 'instances_stopped'):
            log_data['instances_stopped'] = record.instances_stopped
        if hasattr(record, 'time_string'):
            log_data['time_string'] = record.time_string
        if hasattr(record, 'error'):
            log_data['error'] = record.error
        if hasattr(record, 'reason'):
            log_data['reason'] = record.reason
        if hasattr(record, 'schedule_found'):
            log_data['schedule_found'] = record.schedule_found
        if hasattr(record, 'disabled_until'):
            log_data['disabled_until'] = record.disabled_until
            
        return json.dumps(log_data)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Apply structured formatter to root logger
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.setFormatter(StructuredFormatter())

logger = logging.getLogger(__name__)

def get_timezone_for_region(region):
    """Get the appropriate timezone for an AWS region"""
    # Mapping of AWS regions to their primary timezones
    region_timezones = {
        # US East (N. Virginia)
        'us-east-1': 'America/New_York',
        # US East (Ohio)
        'us-east-2': 'America/New_York',
        # US West (N. California)
        'us-west-1': 'America/Los_Angeles',
        # US West (Oregon)
        'us-west-2': 'America/Los_Angeles',
        # US West (Oregon) GovCloud
        'us-gov-west-1': 'America/Los_Angeles',
        # US East (N. Virginia) GovCloud
        'us-gov-east-1': 'America/New_York',
        # Canada (Central)
        'ca-central-1': 'America/Toronto',
        # Europe (Ireland)
        'eu-west-1': 'Europe/Dublin',
        # Europe (London)
        'eu-west-2': 'Europe/London',
        # Europe (Paris)
        'eu-west-3': 'Europe/Paris',
        # Europe (Frankfurt)
        'eu-central-1': 'Europe/Berlin',
        # Europe (Stockholm)
        'eu-north-1': 'Europe/Stockholm',
        # Europe (Milan)
        'eu-south-1': 'Europe/Rome',
        # Europe (Spain)
        'eu-south-2': 'Europe/Madrid',
        # Asia Pacific (Tokyo)
        'ap-northeast-1': 'Asia/Tokyo',
        # Asia Pacific (Seoul)
        'ap-northeast-2': 'Asia/Seoul',
        # Asia Pacific (Osaka)
        'ap-northeast-3': 'Asia/Tokyo',
        # Asia Pacific (Singapore)
        'ap-southeast-1': 'Asia/Singapore',
        # Asia Pacific (Sydney)
        'ap-southeast-2': 'Australia/Sydney',
        # Asia Pacific (Jakarta)
        'ap-southeast-3': 'Asia/Jakarta',
        # Asia Pacific (Melbourne)
        'ap-southeast-4': 'Australia/Melbourne',
        # Asia Pacific (Mumbai)
        'ap-south-1': 'Asia/Kolkata',
        # Asia Pacific (Hong Kong)
        'ap-south-2': 'Asia/Hong_Kong',
        # South America (São Paulo)
        'sa-east-1': 'America/Sao_Paulo',
        # Africa (Cape Town)
        'af-south-1': 'Africa/Johannesburg',
        # Middle East (Bahrain)
        'me-south-1': 'Asia/Bahrain',
        # Middle East (UAE)
        'me-central-1': 'Asia/Dubai',
        # China (Beijing)
        'cn-north-1': 'Asia/Shanghai',
        # China (Ningxia)
        'cn-northwest-1': 'Asia/Shanghai',
        # Israel (Tel Aviv)
        'il-central-1': 'Asia/Jerusalem',
    }
    
    timezone_name = region_timezones.get(region, 'UTC')
    logger.debug(f"Using timezone {timezone_name} for region {region}")
    return pytz.timezone(timezone_name)

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

def parse_disabled_until(tag_value):
    """Parse PowerScheduleDisabledUntil tag value to datetime object"""
    try:
        from dateutil import parser
        parsed = parser.parse(tag_value.strip())
        return parsed
    except Exception as e:
        logger.error(f"Error parsing disabled until time '{tag_value}': {e}")
        return None

def get_schedule_from_tags(tags):
    """Extract schedule from EC2 instance tags"""
    if not tags:
        return None
    
    on_time = None
    off_time = None
    disabled_until = None
    
    for tag in tags:
        if tag['Key'] == 'PowerScheduleOnTime':
            on_time = parse_time(tag['Value'])
        elif tag['Key'] == 'PowerScheduleOffTime':
            off_time = parse_time(tag['Value'])
        elif tag['Key'] == 'PowerScheduleDisabledUntil':
            disabled_until = parse_disabled_until(tag['Value'])
    
    if on_time and off_time:
        return {'start_time': on_time, 'stop_time': off_time, 'disabled_until': disabled_until}
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

def get_stakeholders_from_tags(tags):
    """Extract stakeholders from EC2 instance tags"""
    if not tags:
        return []
    
    for tag in tags:
        if tag['Key'] == 'Stakeholders':
            # Parse comma-separated list of Slack user IDs
            stakeholders = [user_id.strip() for user_id in tag['Value'].split(',') if user_id.strip()]
            return stakeholders
    
    return []

def send_slack_notification(user_id, instance_name, instance_id, action, region, bot_token):
    """Send Slack DM notification to a stakeholder about power state change"""
    try:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }
        
        # Create a user-friendly message
        action_emoji = "🟢" if action == "start" else "🔴"
        action_text = "started" if action == "start" else "stopped"
        
        message = f"{action_emoji} *EC2 Instance Power State Change*\n\n" \
                 f"*Instance:* {instance_name}\n" \
                 f"*Instance ID:* `{instance_id}`\n" \
                 f"*Action:* {action_text}\n" \
                 f"*Region:* {region}\n" \
                 f"*Time:* {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        data = {
            "channel": user_id,
            "text": message
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response_data = response.json()
        
        if response_data.get('ok'):
            logger.info(f"Successfully sent Slack notification to {user_id} for {action} action on {instance_name}", extra={
                'component': 'slack_notification',
                'instance_name': instance_name,
                'instance_id': instance_id,
                'action': action,
                'slack_user_id': user_id,
                'status': 'success'
            })
        else:
            logger.error(f"Failed to send Slack notification to {user_id}: {response_data.get('error')}", extra={
                'component': 'slack_notification',
                'instance_name': instance_name,
                'instance_id': instance_id,
                'action': action,
                'slack_user_id': user_id,
                'status': 'error',
                'error': response_data.get('error')
            })
            
    except Exception as e:
        logger.error(f"Exception sending Slack notification to {user_id}: {e}", extra={
            'component': 'slack_notification',
            'instance_name': instance_name,
            'instance_id': instance_id,
            'action': action,
            'slack_user_id': user_id,
            'status': 'exception',
            'error': str(e)
        })

def notify_stakeholders(instance_name, instance_id, action, region, stakeholders, bot_token):
    """Notify all stakeholders about a power state change"""
    if not stakeholders:
        logger.debug(f"No stakeholders to notify for instance {instance_name}", extra={
            'component': 'stakeholder_notification',
            'instance_name': instance_name,
            'instance_id': instance_id,
            'action': action,
            'stakeholders_count': 0
        })
        return
    
    logger.info(f"Notifying {len(stakeholders)} stakeholders about {action} action on {instance_name}", extra={
        'component': 'stakeholder_notification',
        'instance_name': instance_name,
        'instance_id': instance_id,
        'action': action,
        'stakeholders_count': len(stakeholders),
        'stakeholders': stakeholders
    })
    
    for user_id in stakeholders:
        send_slack_notification(user_id, instance_name, instance_id, action, region, bot_token)

def main(region='us-west-2'):
    """Main scheduler function"""
    import boto3
    from datetime import datetime, time
    
    # Get timezone for the region
    region_tz = get_timezone_for_region(region)
    
    # Get Slack bot token from environment variable
    slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
    if not slack_bot_token:
        logger.warning("SLACK_BOT_TOKEN environment variable not set - stakeholder notifications will be disabled", extra={
            'component': 'scheduler_start',
            'slack_notifications_enabled': False
        })
    
    ec2 = boto3.client('ec2', region_name=region)
    current_time = datetime.datetime.now(datetime.timezone.utc).astimezone(region_tz).time()
    
    logger.info("Starting EC2 scheduler", extra={
        'component': 'scheduler_start',
        'current_time': current_time.strftime('%H:%M'),
        'timezone': region_tz.zone,
        'region': region,
        'slack_notifications_enabled': bool(slack_bot_token)
    })
    
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
            stakeholders = get_stakeholders_from_tags(tags)
            
            if not schedule:
                logger.debug(f"Found instance {instance_name} ({instance_id}) - no power schedule tags found, skipping", extra={
                    'component': 'instance_processing',
                    'instance_name': instance_name,
                    'instance_id': instance_id,
                    'current_state': current_state,
                    'schedule_found': False,
                    'reason': 'no power schedule tags found'
                })
                continue
            
            # Check if scheduling is disabled until a specific time
            current_datetime = datetime.datetime.now(datetime.timezone.utc)
            if schedule.get('disabled_until') and current_datetime < schedule['disabled_until']:
                disabled_until_str = schedule['disabled_until'].strftime('%Y-%m-%d %H:%M:%S UTC')
                logger.info(f"Skipping instance {instance_name} ({instance_id}) - scheduling disabled until {disabled_until_str}", extra={
                    'component': 'instance_processing',
                    'instance_name': instance_name,
                    'instance_id': instance_id,
                    'current_state': current_state,
                    'disabled_until': disabled_until_str,
                    'reason': 'scheduling disabled until specified time'
                })
                continue
            
            instances_processed += 1
            should_run = should_instance_be_running(schedule, current_time)
            
            # Log detailed information about the instance and decision
            start_time_str = schedule['start_time'].strftime('%H:%M')
            stop_time_str = schedule['stop_time'].strftime('%H:%M')
            current_time_str = current_time.strftime('%H:%M')
            
            logger.info(f"Processing instance {instance_name} ({instance_id}) - schedule: ON at {start_time_str}, OFF at {stop_time_str}, current time: {current_time_str}", extra={
                'component': 'instance_processing',
                'instance_name': instance_name,
                'instance_id': instance_id,
                'current_state': current_state,
                'start_time': start_time_str,
                'stop_time': stop_time_str,
                'current_time': current_time_str,
                'timezone': region_tz.zone,
                'schedule_found': True
            })
            
            if should_run and current_state == 'stopped':
                logger.info(f"Starting instance {instance_name} - current time {current_time_str} is within ON period {start_time_str}-{stop_time_str}", extra={
                    'component': 'instance_action',
                    'instance_name': instance_name,
                    'instance_id': instance_id,
                    'current_time': current_time_str,
                    'start_time': start_time_str,
                    'stop_time': stop_time_str,
                    'action': 'start',
                    'reason': f'current time {current_time_str} is within ON period {start_time_str}-{stop_time_str}'
                })
                ec2.start_instances(InstanceIds=[instance_id])
                instances_started += 1
                
                # Notify stakeholders about the power state change
                if slack_bot_token:
                    notify_stakeholders(instance_name, instance_id, 'start', region, stakeholders, slack_bot_token)
            elif not should_run and current_state == 'running':
                logger.info(f"Stopping instance {instance_name} - current time {current_time_str} is outside ON period {start_time_str}-{stop_time_str}", extra={
                    'component': 'instance_action',
                    'instance_name': instance_name,
                    'instance_id': instance_id,
                    'current_time': current_time_str,
                    'start_time': start_time_str,
                    'stop_time': stop_time_str,
                    'action': 'stop',
                    'reason': f'current time {current_time_str} is outside ON period {start_time_str}-{stop_time_str}'
                })
                ec2.stop_instances(InstanceIds=[instance_id])
                instances_stopped += 1
                
                # Notify stakeholders about the power state change
                if slack_bot_token:
                    notify_stakeholders(instance_name, instance_id, 'stop', region, stakeholders, slack_bot_token)
            else:
                logger.info(f"No action needed for instance {instance_name} - already in correct state ({current_state})", extra={
                    'component': 'instance_action',
                    'instance_name': instance_name,
                    'instance_id': instance_id,
                    'current_state': current_state,
                    'should_run': should_run,
                    'reason': 'instance is already in correct state'
                })
    
    logger.info(f"Scheduler completed: {instances_processed} processed, {instances_started} started, {instances_stopped} stopped", extra={
        'component': 'scheduler_completion',
        'instances_processed': instances_processed,
        'instances_started': instances_started,
        'instances_stopped': instances_stopped
    })

if __name__ == '__main__':
    import sys
    
    # Get region from command line argument or environment variable, default to us-west-2
    region = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('AWS_REGION', 'us-west-2')
    main(region)
