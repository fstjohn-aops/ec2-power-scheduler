#!/usr/bin/env python3
"""
Tests for Slack notification functionality
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add the parent directory to the path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import get_stakeholders_from_tags, send_slack_notification, notify_stakeholders


class TestStakeholdersParsing:
    """Test stakeholder tag parsing functionality"""
    
    def test_single_stakeholder(self):
        """Test parsing a single stakeholder"""
        tags = [{'Key': 'Stakeholders', 'Value': 'U08QYU6AX0V'}]
        result = get_stakeholders_from_tags(tags)
        assert result == ['U08QYU6AX0V']
    
    def test_multiple_stakeholders(self):
        """Test parsing multiple stakeholders"""
        tags = [{'Key': 'Stakeholders', 'Value': 'U08QYU6AX0V,U1234567890,U9876543210'}]
        result = get_stakeholders_from_tags(tags)
        assert result == ['U08QYU6AX0V', 'U1234567890', 'U9876543210']
    
    def test_stakeholders_with_spaces(self):
        """Test parsing stakeholders with spaces around commas"""
        tags = [{'Key': 'Stakeholders', 'Value': 'U08QYU6AX0V, U1234567890 , U9876543210'}]
        result = get_stakeholders_from_tags(tags)
        assert result == ['U08QYU6AX0V', 'U1234567890', 'U9876543210']
    
    def test_no_stakeholders_tag(self):
        """Test when no Stakeholders tag exists"""
        tags = [{'Key': 'Name', 'Value': 'test-instance'}]
        result = get_stakeholders_from_tags(tags)
        assert result == []
    
    def test_empty_tags(self):
        """Test with empty tags list"""
        tags = []
        result = get_stakeholders_from_tags(tags)
        assert result == []
    
    def test_empty_stakeholders_value(self):
        """Test with empty Stakeholders tag value"""
        tags = [{'Key': 'Stakeholders', 'Value': ''}]
        result = get_stakeholders_from_tags(tags)
        assert result == []
    
    def test_stakeholders_with_empty_entries(self):
        """Test with empty entries in comma-separated list"""
        tags = [{'Key': 'Stakeholders', 'Value': 'U08QYU6AX0V,,U1234567890, ,U9876543210'}]
        result = get_stakeholders_from_tags(tags)
        assert result == ['U08QYU6AX0V', 'U1234567890', 'U9876543210']


class TestSlackNotification:
    """Test Slack notification functionality"""
    
    @patch('src.app.requests.post')
    def test_successful_notification(self, mock_post):
        """Test successful Slack notification"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True, 'channel': 'D1234567890', 'ts': '1234567890.123456'}
        mock_post.return_value = mock_response
        
        # Test parameters
        user_id = "U08QYU6AX0V"
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "start"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function
        send_slack_notification(user_id, instance_name, instance_id, action, region, bot_token)
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert call_args[0][0] == "https://slack.com/api/chat.postMessage"
        
        # Check headers
        headers = call_args[1]['headers']
        assert headers['Authorization'] == f"Bearer {bot_token}"
        assert headers['Content-Type'] == "application/json"
        
        # Check data
        data = call_args[1]['json']
        assert data['channel'] == user_id
        assert "🟢" in data['text']  # Start action should have green emoji
        assert instance_name in data['text']
        assert instance_id in data['text']
        assert "started" in data['text']
        assert region in data['text']
    
    @patch('src.app.requests.post')
    def test_stop_notification(self, mock_post):
        """Test Slack notification for stop action"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True}
        mock_post.return_value = mock_response
        
        # Test parameters
        user_id = "U08QYU6AX0V"
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "stop"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function
        send_slack_notification(user_id, instance_name, instance_id, action, region, bot_token)
        
        # Verify the request was made correctly
        call_args = mock_post.call_args
        data = call_args[1]['json']
        assert "🔴" in data['text']  # Stop action should have red emoji
        assert "stopped" in data['text']
    
    @patch('src.app.requests.post')
    def test_failed_notification(self, mock_post):
        """Test failed Slack notification"""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': False, 'error': 'channel_not_found'}
        mock_post.return_value = mock_response
        
        # Test parameters
        user_id = "U08QYU6AX0V"
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "start"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function (should not raise exception, just log error)
        send_slack_notification(user_id, instance_name, instance_id, action, region, bot_token)
        
        # Verify the request was made
        mock_post.assert_called_once()
    
    @patch('src.app.requests.post')
    def test_request_exception(self, mock_post):
        """Test handling of request exceptions"""
        # Mock request exception
        mock_post.side_effect = Exception("Network error")
        
        # Test parameters
        user_id = "U08QYU6AX0V"
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "start"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function (should not raise exception, just log error)
        send_slack_notification(user_id, instance_name, instance_id, action, region, bot_token)
        
        # Verify the request was attempted
        mock_post.assert_called_once()


class TestStakeholderNotifications:
    """Test stakeholder notification orchestration"""
    
    @patch('src.app.send_slack_notification')
    def test_notify_multiple_stakeholders(self, mock_send_notification):
        """Test notifying multiple stakeholders"""
        stakeholders = ['U08QYU6AX0V', 'U1234567890', 'U9876543210']
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "start"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function
        notify_stakeholders(instance_name, instance_id, action, region, stakeholders, bot_token)
        
        # Verify notifications were sent to all stakeholders
        assert mock_send_notification.call_count == 3
        
        # Check each call
        calls = mock_send_notification.call_args_list
        for i, call in enumerate(calls):
            args = call[0]  # Get positional arguments
            assert args[0] == stakeholders[i]  # user_id
            assert args[1] == instance_name
            assert args[2] == instance_id
            assert args[3] == action
            assert args[4] == region
            assert args[5] == bot_token
    
    @patch('src.app.send_slack_notification')
    def test_notify_no_stakeholders(self, mock_send_notification):
        """Test notifying when no stakeholders exist"""
        stakeholders = []
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "start"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function
        notify_stakeholders(instance_name, instance_id, action, region, stakeholders, bot_token)
        
        # Verify no notifications were sent
        mock_send_notification.assert_not_called()
    
    @patch('src.app.send_slack_notification')
    def test_notify_single_stakeholder(self, mock_send_notification):
        """Test notifying a single stakeholder"""
        stakeholders = ['U08QYU6AX0V']
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "stop"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # Call the function
        notify_stakeholders(instance_name, instance_id, action, region, stakeholders, bot_token)
        
        # Verify notification was sent
        mock_send_notification.assert_called_once_with(
            'U08QYU6AX0V', instance_name, instance_id, action, region, bot_token
        )


class TestIntegration:
    """Integration tests for Slack notifications"""
    
    def test_end_to_end_stakeholder_parsing_and_notification(self):
        """Test the complete flow from tag parsing to notification"""
        # Test data
        tags = [
            {'Key': 'Name', 'Value': 'test-instance'},
            {'Key': 'Stakeholders', 'Value': 'U08QYU6AX0V,U1234567890'},
            {'Key': 'PowerScheduleOnTime', 'Value': '9am'},
            {'Key': 'PowerScheduleOffTime', 'Value': '5pm'}
        ]
        
        # Parse stakeholders
        stakeholders = get_stakeholders_from_tags(tags)
        assert stakeholders == ['U08QYU6AX0V', 'U1234567890']
        
        # Test notification parameters
        instance_name = "test-instance"
        instance_id = "i-1234567890abcdef0"
        action = "start"
        region = "us-west-2"
        bot_token = "xoxb-test-token"
        
        # This would normally send notifications, but we're just testing the flow
        assert len(stakeholders) == 2
        assert all(user_id.startswith('U') for user_id in stakeholders) 