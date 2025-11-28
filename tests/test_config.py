"""
Test configuration for auto-coin trading system
"""
import unittest
import yaml
import os
import sys
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestConfig(unittest.TestCase):
    """Test configuration file validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.config_path = os.path.join(
            os.path.dirname(__file__), '..', 'config.yaml')

    def test_config_exists(self):
        """Test that config.yaml exists"""
        self.assertTrue(os.path.exists(self.config_path),
                        "config.yaml file not found")

    def test_config_valid_yaml(self):
        """Test that config.yaml is valid YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.assertIsInstance(
                    config, dict, "Config should be a dictionary")
        except yaml.YAMLError as e:
            self.fail(f"Invalid YAML syntax: {e}")
        except Exception as e:
            self.fail(f"Error reading config file: {e}")

    def test_config_required_fields(self):
        """Test that config contains required fields"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        required_fields = ['upbit', 'trading', 'discord']
        for field in required_fields:
            self.assertIn(
                field, config, f"Required field '{field}' missing from config")

    def test_upbit_config(self):
        """Test Upbit API configuration"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        upbit_config = config.get('upbit', {})
        self.assertIn('access_key', upbit_config, "Upbit access_key missing")
        self.assertIn('secret_key', upbit_config, "Upbit secret_key missing")

        # Check that keys are not placeholder values
        access_key = upbit_config.get('access_key', '')
        secret_key = upbit_config.get('secret_key', '')

        self.assertNotEqual(access_key, '', "Upbit access_key is empty")
        self.assertNotEqual(secret_key, '', "Upbit secret_key is empty")
        self.assertNotIn('your_', access_key.lower(),
                         "Upbit access_key appears to be a placeholder")
        self.assertNotIn('your_', secret_key.lower(),
                         "Upbit secret_key appears to be a placeholder")


if __name__ == '__main__':
    unittest.main()
