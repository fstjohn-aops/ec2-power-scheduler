import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from src import app
from freezegun import freeze_time

@pytest.fixture
def sample_tags():
    return [
        {'Key': 'Name', 'Value': 'TestInstance'},
        {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
        {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
    ]

class TestSchedulerIntegration:
    @freeze_time("2023-01-01 18:00:00")  # 10:00 PST
    @patch('boto3.client')
    def test_starts_stopped_instance_within_schedule(self, mock_boto3, sample_tags):
        """Should start a stopped instance if current time is within schedule window."""
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'stopped'},
                    'Tags': sample_tags
                }]
            }]
        }
        mock_ec2.start_instances.return_value = {}
        app.main(region='us-west-2')
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_called_once_with(
            InstanceIds=['i-1234567890abcdef0']
        )
        mock_ec2.stop_instances.assert_not_called()

    @freeze_time("2023-01-02 02:00:00")  # 18:00 PST (next day UTC)
    @patch('boto3.client')
    def test_stops_running_instance_outside_schedule(self, mock_boto3, sample_tags):
        """Should stop a running instance if current time is outside schedule window."""
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'running'},
                    'Tags': sample_tags
                }]
            }]
        }
        mock_ec2.stop_instances.return_value = {}
        app.main(region='us-west-2')
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.stop_instances.assert_called_once_with(
            InstanceIds=['i-1234567890abcdef0']
        )
        mock_ec2.start_instances.assert_not_called()

    @freeze_time("2023-01-01 18:00:00")  # 10:00 PST
    @patch('boto3.client')
    def test_skips_instance_with_no_schedule_tags(self, mock_boto3):
        """Should skip instances that do not have schedule tags."""
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'Name', 'Value': 'NoScheduleInstance'}]
                }]
            }]
        }
        app.main(region='us-west-2')
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_not_called()
        mock_ec2.stop_instances.assert_not_called()

    @freeze_time("2023-01-01 18:00:00")  # 10:00 PST
    @patch('boto3.client')
    def test_skips_instance_with_disabled_until(self, mock_boto3, sample_tags):
        """Should skip instances with scheduling disabled until a future time."""
        disabled_until = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        tags = sample_tags + [{'Key': 'PowerScheduleDisabledUntil', 'Value': disabled_until.isoformat()}]
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'stopped'},
                    'Tags': tags
                }]
            }]
        }
        app.main(region='us-west-2')
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_not_called()
        mock_ec2.stop_instances.assert_not_called()

    @freeze_time("2023-01-01 18:00:00")  # 10:00 PST
    @patch('boto3.client')
    def test_multiple_instances_mixed_states(self, mock_boto3, sample_tags):
        """Should handle multiple instances with mixed states and schedules."""
        # Instance 1: stopped, should be started at 10:00 PST
        # Instance 2: running, no schedule (should be skipped)
        # Instance 3: running, outside schedule (should be stopped at 18:00 PST)
        tags2 = [{'Key': 'Name', 'Value': 'NoScheduleInstance'}]
        tags3 = [
            {'Key': 'Name', 'Value': 'TestInstance2'},
            {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
            {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
        ]
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        mock_ec2.describe_instances.return_value = {
            'Reservations': [
                {'Instances': [{
                    'InstanceId': 'i-1',
                    'State': {'Name': 'stopped'},
                    'Tags': sample_tags
                }]},
                {'Instances': [{
                    'InstanceId': 'i-2',
                    'State': {'Name': 'running'},
                    'Tags': tags2
                }]},
                {'Instances': [{
                    'InstanceId': 'i-3',
                    'State': {'Name': 'running'},
                    'Tags': tags3
                }]}
            ]
        }
        mock_ec2.start_instances.return_value = {}
        mock_ec2.stop_instances.return_value = {}
        # First, at 10:00 PST, i-1 should be started, i-3 not stopped
        app.main(region='us-west-2')
        mock_ec2.start_instances.assert_called_once_with(InstanceIds=['i-1'])
        mock_ec2.stop_instances.assert_not_called()
        # Reset mocks
        mock_ec2.start_instances.reset_mock()
        mock_ec2.stop_instances.reset_mock()
        # Now, at 18:00 PST (02:00 UTC next day), i-3 should be stopped
        with freeze_time("2023-01-02 02:00:00"):
            app.main(region='us-west-2')
        mock_ec2.start_instances.assert_not_called()
        mock_ec2.stop_instances.assert_called_once_with(InstanceIds=['i-3']) 

    @freeze_time("2023-01-01 05:30:00")  # 21:30 PST (previous day), before 6:00 AM
    @patch('boto3.client')
    def test_updates_on_time_tag_later_than_latest_valid(self, mock_boto3):
        """Should update PowerScheduleOnTime tag to 06:00 if it is set later than 06:00."""
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        # Instance with on time at 09:00 (should be updated to 06:00)
        tags = [
            {'Key': 'Name', 'Value': 'LateOnTimeInstance'},
            {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
            {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
        ]
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-lateon',
                    'State': {'Name': 'stopped'},
                    'Tags': tags
                }]
            }]
        }
        mock_ec2.start_instances.return_value = {}
        mock_ec2.create_tags.return_value = {}
        app.main(region='us-west-2')
        # Should update the tag to 06:00
        mock_ec2.create_tags.assert_called_once_with(
            Resources=['i-lateon'],
            Tags=[{'Key': 'PowerScheduleOnTime', 'Value': '06:00'}]
        )
        # Should use the corrected time and start the instance (since 05:30 < 06:00, instance should not be started yet)
        mock_ec2.start_instances.assert_not_called()
        mock_ec2.stop_instances.assert_not_called() 