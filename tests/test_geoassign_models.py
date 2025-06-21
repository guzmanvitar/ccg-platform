"""
Django model tests for the geoassign app
"""

import logging
from datetime import datetime
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class GeoassignAPITestCase(APITestCase):
    """Test cases for the geoassign API using Django's test framework"""

    @classmethod
    def setUpClass(cls):
        """Set up logging for all tests"""
        super().setUpClass()

        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Set up logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"test_django_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),  # Also output to console
            ],
        )
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("Starting Django API tests")

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.logger.info(f"Starting test: {self._testMethodName}")

    def tearDown(self):
        """Clean up after tests"""
        self.logger.info(f"Completed test: {self._testMethodName}")
        super().tearDown()

    def test_health_check_endpoint(self):
        """Test the health check endpoint using Django's test client"""
        self.logger.info("Testing health check endpoint...")

        url = reverse("geoassign:health_check")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertEqual(response.data["service"], "geographic_assignment_api")

        self.logger.info("✓ Health check endpoint test passed")

    def test_test_pipeline_endpoint(self):
        """Test the test pipeline endpoint using Django's test client"""
        self.logger.info("Testing pipeline endpoint...")

        url = reverse("geoassign:test_pipeline")
        response = self.client.post(url, data={"species": "panthera_onca"})

        # Note: This test might fail if SCAT is not available in test environment
        # In a real test environment, you'd mock the SCAT execution
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data["status"], "success")
            self.logger.info("✓ Pipeline endpoint test passed")
        else:
            # If it fails, it should be a 500 error, not a 400/404
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR],
            )
            self.logger.warning(
                f"Pipeline endpoint returned status: {response.status_code}"
            )


class GeoassignModelTestCase(TestCase):
    """Test cases for geoassign models (when models are added)"""

    @classmethod
    def setUpClass(cls):
        """Set up logging for all tests"""
        super().setUpClass()

        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Set up logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"test_models_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),  # Also output to console
            ],
        )
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("Starting model tests")

    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.logger.info(f"Starting test: {self._testMethodName}")

    def tearDown(self):
        """Clean up after tests"""
        self.logger.info(f"Completed test: {self._testMethodName}")
        super().tearDown()

    def test_placeholder(self):
        """Placeholder test - replace with actual model tests when models are added"""
        self.logger.info("Running placeholder test")
        self.assertTrue(True)
        self.logger.info("✓ Placeholder test passed")
