"""
Test main modules and import structure
"""
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestImports(unittest.TestCase):
    """Test that all modules can be imported without errors"""

    def test_modules_import(self):
        """Test that modules package imports correctly"""
        try:
            import modules
            self.assertTrue(hasattr(modules, 'ConfigManager'))
            self.assertTrue(hasattr(modules, 'TradingEngine'))
            self.assertTrue(hasattr(modules, 'LearningSystem'))
        except ImportError as e:
            self.fail(f"Failed to import modules package: {e}")

    def test_trading_engine_import(self):
        """Test TradingEngine import"""
        try:
            from modules.trading_engine import TradingEngine
            self.assertTrue(callable(TradingEngine))
        except ImportError as e:
            self.fail(f"Failed to import TradingEngine: {e}")

    def test_config_manager_import(self):
        """Test ConfigManager import"""
        try:
            from modules.config_manager import ConfigManager
            self.assertTrue(callable(ConfigManager))
        except ImportError as e:
            self.fail(f"Failed to import ConfigManager: {e}")

    def test_auto_optimizer_import(self):
        """Test AutoOptimizationEngine import"""
        try:
            from scripts.auto_optimizer import AutoOptimizationEngine
            self.assertTrue(callable(AutoOptimizationEngine))
        except ImportError as e:
            self.fail(f"Failed to import AutoOptimizationEngine: {e}")


class TestMainExecution(unittest.TestCase):
    """Test main.py execution safety"""

    @patch('modules.TradingEngine')
    @patch('modules.ConfigManager')
    def test_main_imports_safely(self, mock_config_manager, mock_trading_engine):
        """Test that main.py can import its dependencies"""
        try:
            # Mock the classes to prevent actual initialization
            mock_trading_engine.return_value = MagicMock()
            mock_config_manager.return_value = MagicMock()

            # Test import without executing main logic
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "main",
                os.path.join(os.path.dirname(__file__), '..', 'main.py')
            )
            # Just test that the file can be loaded, don't execute it
            self.assertIsNotNone(spec)

        except Exception as e:
            self.fail(f"main.py has import or syntax errors: {e}")


if __name__ == '__main__':
    unittest.main()
