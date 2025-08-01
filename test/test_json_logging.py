import pytest
import json
import logging
from io import StringIO
from unittest.mock import patch, Mock
from src import app


class TestJsonLogging:
    """Test cases for JSON logging functionality"""

    def test_json_logging_format(self):
        """Test that logs are output in JSON format"""
        # Capture log output
        log_output = StringIO()
        
        # Create a handler that writes to our StringIO
        handler = logging.StreamHandler(log_output)
        formatter = app.StructuredFormatter()
        handler.setFormatter(formatter)
        
        # Get the logger and add our handler
        logger = logging.getLogger(__name__)
        logger.handlers = []  # Clear existing handlers
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log a test message
        test_message = "Test log message"
        logger.info(test_message, extra={
            'test_field': 'test_value',
            'component': 'test_component'
        })
        
        # Get the log output
        log_line = log_output.getvalue().strip()
        
        # Verify it's valid JSON
        try:
            log_data = json.loads(log_line)
        except json.JSONDecodeError:
            pytest.fail(f"Log output is not valid JSON: {log_line}")
        
        # Verify required fields are present
        assert 'timestamp' in log_data
        assert 'level' in log_data
        assert 'logger' in log_data
        assert 'message' in log_data
        assert log_data['message'] == test_message
        assert log_data['component'] == 'test_component'

    def test_app_logging_integration(self):
        """Test that the app's logging configuration works correctly"""
        # This test verifies that the app's logging setup doesn't cause errors
        # We'll just verify that the logger is properly configured
        logger = logging.getLogger(__name__)
        
        # The logger should have handlers configured
        assert len(logger.handlers) > 0
        
        # The root logger should also have handlers
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    @patch('boto3.client')
    def test_structured_logging_in_main_function(self, mock_boto3):
        """Test that the main function uses structured logging"""
        # Mock EC2 client
        mock_ec2 = Mock()
        mock_boto3.return_value = mock_ec2
        
        # Mock describe_instances response
        mock_ec2.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': {'Name': 'stopped'},
                    'Tags': [
                        {'Key': 'Name', 'Value': 'TestInstance'},
                        {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
                        {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
                    ]
                }]
            }]
        }
        
        # Capture log output
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        formatter = app.StructuredFormatter()
        handler.setFormatter(formatter)
        
        # Temporarily replace the app's logger handler
        app_logger = logging.getLogger('app')
        original_handlers = app_logger.handlers[:]
        app_logger.handlers = [handler]
        
        try:
            # Run the main function
            app.main()
            
            # Get the log output
            log_lines = log_output.getvalue().strip().split('\n')
            
            # Verify we have JSON logs
            for line in log_lines:
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        # Verify it has the expected structure
                        assert 'message' in log_data
                        assert 'component' in log_data
                    except json.JSONDecodeError:
                        pytest.fail(f"Log line is not valid JSON: {line}")
        finally:
            # Restore original handlers
            app_logger.handlers = original_handlers 