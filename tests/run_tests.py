#!/usr/bin/env python3
"""
Test runner for the CCG Platform
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Run all tests"""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"test_runner_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),  # Also output to console
        ],
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting CCG Platform Test Suite")
    print("CCG Platform Test Suite")
    print("=" * 30)

    # Run API tests
    from tests.test_geoassign_api import run_tests

    success = run_tests()

    if success:
        logger.info("All tests completed successfully!")
        print("\n✅ All tests completed successfully!")
        return 0
    else:
        logger.error("Some tests failed!")
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
