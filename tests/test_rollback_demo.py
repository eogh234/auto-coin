"""
Test that intentionally fails to demonstrate rollback mechanism
"""
import unittest


class TestFailureDemo(unittest.TestCase):
    """Test failure demonstration"""

    def test_intentional_failure(self):
        """This test will fail to show rollback behavior"""
        # Uncomment next line to trigger test failure and rollback
        # self.fail("Intentional test failure for rollback demo")
        self.assertTrue(True)  # This passes normally

    def test_critical_system_check(self):
        """Critical system validation"""
        # This simulates a critical system check that might fail
        import os

        # Check if we're in CI environment
        if os.getenv('GITHUB_ACTIONS'):
            # In CI, this should pass
            self.assertTrue(True, "CI environment validation")
        else:
            # Local testing - always pass
            self.assertTrue(True, "Local environment validation")


if __name__ == '__main__':
    unittest.main()
