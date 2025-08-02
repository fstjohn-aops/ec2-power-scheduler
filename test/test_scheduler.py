import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, time, timezone
from src import app


@pytest.fixture
def sample_tags():
    """Set up test fixtures"""
    return [
        {'Key': 'Name', 'Value': 'TestInstance'},
        {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
        {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
    ]


class TestSchedulerIntegration:
    """Test cases for main scheduler integration with AWS"""

    @patch('boto3.client')
    @patch('src.app.datetime')
    def test_main_function_integration(self, mock_datetime, mock_boto3, sample_tags):
        # Set current time to 10:00 (within schedule)
        mock_now = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.timezone = timezone

        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        # Mock describe_instances response
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'stopped'},
                    'Tags': sample_tags
                }]
            }]
        }
        # Mock start_instances
        mock_ec2.start_instances.return_value = {}
        # Run the main function
        app.main()
        # Verify EC2 client was called correctly
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_called_once_with(
            InstanceIds=['i-1234567890abcdef0']
        )

    @patch('boto3.client')
    @patch('src.app.datetime')
    def test_main_function_no_schedule_instances(self, mock_datetime, mock_boto3):
        # Set current time to 10:00 (arbitrary)
        mock_now = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.timezone = timezone

        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        # Mock describe_instances response with no schedule tags
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'running'},
                    'Tags': [{'Key': 'Name', 'Value': 'NoScheduleInstance'}]
                }]
            }]
        }
        # Run the main function
        app.main()
        # Verify EC2 client was called but no start/stop operations
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_not_called()
        mock_ec2.stop_instances.assert_not_called()

    @patch('boto3.client')
    @patch('src.app.datetime')
    def test_main_function_stop_instances(self, mock_datetime, mock_boto3):
        # Set current time to 18:00 (outside schedule)
        mock_now = datetime(2023, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.timezone = timezone

        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        # Mock describe_instances response with running instance outside schedule
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'running'},
                    'Tags': [
                        {'Key': 'Name', 'Value': 'TestInstance'},
                        {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
                        {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
                    ]
                }]
            }]
        }
        # Mock stop_instances
        mock_ec2.stop_instances.return_value = {}
        # Run the main function
        app.main()
        # Verify EC2 client was called correctly
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.stop_instances.assert_called_once_with(
            InstanceIds=['i-1234567890abcdef0']
        )

    @patch('boto3.client')
    @patch('src.app.datetime')
    def test_main_function_multiple_instances(self, mock_datetime, mock_boto3, sample_tags):
        # Set current time to 10:00 (within schedule)
        mock_now = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.timezone = timezone

        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        # Mock describe_instances response with multiple instances
        mock_ec2.describe_instances.return_value = {
            'Reservations': [
                {
                    'Instances': [{
                        'InstanceId': 'i-1234567890abcdef0',
                        'State': {'Name': 'stopped'},
                        'Tags': sample_tags
                    }]
                },
                {
                    'Instances': [{
                        'InstanceId': 'i-0987654321fedcba0',
                        'State': {'Name': 'running'},
                        'Tags': [{'Key': 'Name', 'Value': 'NoScheduleInstance'}]
                    }]
                }
            ]
        }
        # Mock start_instances
        mock_ec2.start_instances.return_value = {}
        # Run the main function
        app.main()
        # Verify EC2 client was called correctly
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_called_once_with(
            InstanceIds=['i-1234567890abcdef0']
        )

    @patch('boto3.client')
    @patch('src.app.datetime')
    def test_main_function_disabled_until(self, mock_datetime, mock_boto3):
        # Set current time to 10:00 (arbitrary)
        mock_now = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.timezone = timezone

        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        # Mock describe_instances response with disabled until tag
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'stopped'},
                    'Tags': [
                        {'Key': 'Name', 'Value': 'DisabledInstance'},
                        {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
                        {'Key': 'PowerScheduleOffTime', 'Value': '17:00'},
                        {'Key': 'PowerScheduleDisabledUntil', 'Value': '2025-12-31T23:59:59.000000+00:00'}
                    ]
                }]
            }]
        }
        # Run the main function
        app.main()
        # Verify EC2 client was called but no start/stop operations due to disabled until
        mock_ec2.describe_instances.assert_called_once()
        mock_ec2.start_instances.assert_not_called()
        mock_ec2.stop_instances.assert_not_called() 