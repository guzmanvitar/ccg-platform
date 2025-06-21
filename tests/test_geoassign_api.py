#!/usr/bin/env python3
"""
Tests for the geographic assignment API
"""

import logging
import unittest
from datetime import datetime
from pathlib import Path

import requests


class TestGeographicAssignmentAPI(unittest.TestCase):
    """Test cases for the geographic assignment API"""

    BASE_URL = "http://127.0.0.1:8000/geoassign"

    @classmethod
    def setUpClass(cls):
        """Set up logging for all tests"""
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Set up logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"test_api_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),  # Also output to console
            ],
        )
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("Starting API tests")

    def setUp(self):
        """Set up test fixtures"""
        self.session = requests.Session()
        self.logger.info(f"Starting test: {self._testMethodName}")

    def tearDown(self):
        """Clean up after tests"""
        self.session.close()
        self.logger.info(f"Completed test: {self._testMethodName}")

    def test_health_check(self):
        """Test the health check endpoint"""
        self.logger.info("Testing health check endpoint...")

        response = self.session.get(f"{self.BASE_URL}/api/health/")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "healthy")
        self.assertIn("service", data)
        self.assertEqual(data["service"], "geographic_assignment_api")
        self.assertIn("version", data)

        self.logger.info(f"✓ Health check passed: {data}")

    def test_pipeline_with_default_species(self):
        """Test the pipeline endpoint with default species (panthera_onca)"""
        self.logger.info("Testing pipeline endpoint with default species...")

        response = self.session.post(f"{self.BASE_URL}/api/test/")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "success")
        self.assertIn("message", data)
        self.assertIn("results_directory", data)

        self.logger.info(f"✓ Pipeline test passed: {data['message']}")

    def test_pipeline_with_specific_species(self):
        """Test the pipeline endpoint with specific species parameter"""
        self.logger.info("Testing pipeline endpoint with panthera_onca species...")

        response = self.session.post(
            f"{self.BASE_URL}/api/test/", data={"species": "panthera_onca"}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "success")
        self.assertIn("message", data)
        self.assertIn("panthera_onca", data["message"])

        self.logger.info(f"✓ Pipeline test with species passed: {data['message']}")

    def test_invalid_endpoint(self):
        """Test that invalid endpoints return 404"""
        self.logger.info("Testing invalid endpoint...")

        response = self.session.get(f"{self.BASE_URL}/api/nonexistent/")

        self.assertEqual(response.status_code, 404)

        self.logger.info("✓ Invalid endpoint correctly returns 404")


def run_tests():
    """Run all tests with verbose output"""
    print("Testing Geographic Assignment API")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGeographicAssignmentAPI)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n🎉 All tests passed! API is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the details above.")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
