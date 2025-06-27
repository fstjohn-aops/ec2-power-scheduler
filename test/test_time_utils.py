import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, time
import app


@pytest.fixture
def sample_tags():
    """Set up test fixtures"""
    return [
        {'Key': 'Name', 'Value': 'TestInstance'},
        {'Key': 'PowerScheduleOnTime', 'Value': '09:00'},
        {'Key': 'PowerScheduleOffTime', 'Value': '17:00'}
    ]


class TestTimeParsing:
    """Test cases for time parsing functionality"""

    def test_parse_time_valid_formats(self):
        """Test parsing various valid time formats"""
        test_cases = [
            ('09:00', time(9, 0)),
            ('17:30', time(17, 30)),
            ('9:00am', time(9, 0)),
            ('5:30pm', time(17, 30)),
            ('9am', time(9, 0)),
            ('5pm', time(17, 0)),
            ('09:00 AM', time(9, 0)),
            ('05:30 PM', time(17, 30))
        ]
        
        for time_str, expected in test_cases:
            result = app.parse_time(time_str)
            assert result == expected

    def test_parse_time_invalid_formats(self):
        """Test parsing invalid time formats returns None"""
        invalid_times = [
            'invalid',
            '25:00',
            '12:60',
            '',
            'abc:def'
        ]
        
        for time_str in invalid_times:
            result = app.parse_time(time_str)
            assert result is None


class TestScheduleExtraction:
    """Test cases for schedule extraction from tags"""

    def test_get_schedule_from_tags_valid(self, sample_tags):
        """Test extracting schedule from valid tags"""
        result = app.get_schedule_from_tags(sample_tags)
        
        assert result is not None
        assert result['start_time'] == time(9, 0)
        assert result['stop_time'] == time(17, 0)

    def test_get_schedule_from_tags_missing_tags(self):
        """Test extracting schedule when tags are missing"""
        # Missing both tags
        result = app.get_schedule_from_tags([{'Key': 'Name', 'Value': 'Test'}])
        assert result is None
        
        # Missing one tag
        partial_tags = [{'Key': 'PowerScheduleOnTime', 'Value': '09:00'}]
        result = app.get_schedule_from_tags(partial_tags)
        assert result is None

    def test_get_schedule_from_tags_empty(self):
        """Test extracting schedule from empty tags"""
        result = app.get_schedule_from_tags([])
        assert result is None
        
        result = app.get_schedule_from_tags(None)
        assert result is None


class TestScheduleLogic:
    """Test cases for schedule logic and instance state determination"""

    def test_should_instance_be_running_normal_schedule(self):
        """Test normal schedule (same day)"""
        schedule = {'start_time': time(9, 0), 'stop_time': time(17, 0)}
        
        # Should be running during schedule
        assert app.should_instance_be_running(schedule, time(10, 0)) is True
        assert app.should_instance_be_running(schedule, time(9, 0)) is True
        assert app.should_instance_be_running(schedule, time(17, 0)) is True
        
        # Should not be running outside schedule
        assert app.should_instance_be_running(schedule, time(8, 0)) is False
        assert app.should_instance_be_running(schedule, time(18, 0)) is False

    def test_should_instance_be_running_overnight_schedule(self):
        """Test overnight schedule (crosses midnight)"""
        schedule = {'start_time': time(22, 0), 'stop_time': time(6, 0)}
        
        # Should be running during overnight schedule
        assert app.should_instance_be_running(schedule, time(23, 0)) is True
        assert app.should_instance_be_running(schedule, time(1, 0)) is True
        assert app.should_instance_be_running(schedule, time(5, 0)) is True
        
        # Should not be running during day
        assert app.should_instance_be_running(schedule, time(10, 0)) is False
        assert app.should_instance_be_running(schedule, time(15, 0)) is False

    def test_should_instance_be_running_no_schedule(self):
        """Test behavior when no schedule is provided"""
        result = app.should_instance_be_running(None, time(10, 0))
        assert result is None

    def test_edge_cases(self):
        """Test various edge cases"""
        # Test exact boundary times
        schedule = {'start_time': time(9, 0), 'stop_time': time(17, 0)}
        assert app.should_instance_be_running(schedule, time(9, 0)) is True
        assert app.should_instance_be_running(schedule, time(17, 0)) is True
        
        # Test overnight boundary
        overnight_schedule = {'start_time': time(22, 0), 'stop_time': time(6, 0)}
        assert app.should_instance_be_running(overnight_schedule, time(22, 0)) is True
        assert app.should_instance_be_running(overnight_schedule, time(6, 0)) is True 