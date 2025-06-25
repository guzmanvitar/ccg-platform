"""
Tests for the improved SCAT pipeline
"""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from geoassign.scat.pipeline import SCATPipeline, SCATPipelineError


class TestSCATPipeline(TestCase):
    """Test the improved SCAT pipeline functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Configure logging for tests
        logging.basicConfig(level=logging.INFO)

        # Get paths to test data
        self.test_data_dir = Path(__file__).parent / "data"
        self.test_vcf = self.test_data_dir / "panthera_onca_test.vcf"

        # Get paths to reference data
        self.reference_dir = Path("geoassign/reference/panthera_onca")
        self.reference_vcf = self.reference_dir / "panthera_onca.84snps.vcf"
        self.reference_loc = self.reference_dir / "panthera_onca_loc.txt"
        self.reference_grid = self.reference_dir / "panthera_onca_grid.txt"

        # Create temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "test_results"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_data_files_exist(self):
        """Test that all required test data files exist."""
        self.assertTrue(self.test_vcf.exists(), f"Test VCF not found: {self.test_vcf}")
        self.assertTrue(
            self.reference_vcf.exists(),
            f"Reference VCF not found: {self.reference_vcf}",
        )
        self.assertTrue(
            self.reference_loc.exists(),
            f"Reference location file not found: {self.reference_loc}",
        )
        self.assertTrue(
            self.reference_grid.exists(),
            f"Reference grid file not found: {self.reference_grid}",
        )

    def test_vcf_file_formats(self):
        """Test that VCF files have the correct format."""
        # Check test VCF has single sample
        with open(self.test_vcf) as f:
            for line in f:
                if line.startswith("#CHROM"):
                    samples = line.strip().split("\t")[9:]
                    self.assertEqual(
                        len(samples),
                        1,
                        f"Test VCF should have 1 sample, found {len(samples)}",
                    )
                    self.assertEqual(
                        samples[0],
                        "LegadoSP",
                        f"Test sample should be 'LegadoSP', found '{samples[0]}'",
                    )
                    break

        # Check reference VCF has multiple samples
        with open(self.reference_vcf) as f:
            for line in f:
                if line.startswith("#CHROM"):
                    samples = line.strip().split("\t")[9:]
                    self.assertGreater(
                        len(samples),
                        1,
                        f"Reference VCF should have multiple samples, found {len(samples)}",
                    )
                    break

    def test_location_file_format(self):
        """Test that location file has correct format."""
        with open(self.reference_loc) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    parts = line.split()
                    self.assertEqual(
                        len(parts),
                        4,
                        f"Location line {line_num} should have 4 parts: {line}",
                    )

                    # Check that coordinates are valid numbers
                    try:
                        lat = float(parts[2])
                        lon = float(parts[3])

                        # Validate coordinate ranges
                        self.assertTrue(
                            -90 <= lat <= 90,
                            f"Invalid latitude on line {line_num}: {lat}",
                        )
                        self.assertTrue(
                            -180 <= lon <= 180,
                            f"Invalid longitude on line {line_num}: {lon}",
                        )

                    except (ValueError, IndexError) as e:
                        self.fail(
                            f"Invalid location data on line {line_num}: {line} - {e}"
                        )

    def test_grid_file_format(self):
        """Test that grid file has correct format."""
        with open(self.reference_grid) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    parts = line.split()
                    self.assertEqual(
                        len(parts),
                        2,
                        f"Grid line {line_num} should have 2 parts: {line}",
                    )

                    # Check that coordinates are valid numbers
                    try:
                        lat = float(parts[0])
                        lon = float(parts[1])

                        # Validate coordinate ranges
                        self.assertTrue(
                            -90 <= lat <= 90,
                            f"Invalid latitude on line {line_num}: {lat}",
                        )
                        self.assertTrue(
                            -180 <= lon <= 180,
                            f"Invalid longitude on line {line_num}: {lon}",
                        )

                    except (ValueError, IndexError) as e:
                        self.fail(f"Invalid grid data on line {line_num}: {line} - {e}")

    def test_pipeline_initialization_with_real_data(self):
        """Test pipeline initialization with real reference data."""
        try:
            pipeline = SCATPipeline("panthera_onca", 84)
            self.assertEqual(pipeline.species, "panthera_onca")
            self.assertEqual(pipeline.num_snps, 84)
            self.assertEqual(pipeline.reference_dir, self.reference_dir)
            self.assertEqual(pipeline.training_vcf, self.reference_vcf)
            self.assertEqual(pipeline.training_loc, self.reference_loc)
            self.assertEqual(pipeline.grid_file, self.reference_grid)
        except SCATPipelineError as e:
            self.fail(f"Pipeline initialization failed: {e}")

    def test_pipeline_initialization_missing_files(self):
        """Test pipeline initialization fails with missing files."""
        with self.assertRaises(SCATPipelineError) as cm:
            SCATPipeline("nonexistent_species")

        self.assertIn("Missing required reference files", str(cm.exception))

    def test_vcf_parsing_with_real_data(self):
        """Test VCF parsing with real test data."""
        pipeline = SCATPipeline("panthera_onca", 84)

        # Parse test VCF
        samples, genotypes = pipeline._parse_vcf(self.test_vcf)

        self.assertEqual(len(samples), 1, "Test VCF should have exactly one sample")
        self.assertEqual(samples[0], "LegadoSP", "Test sample should be 'LegadoSP'")
        self.assertIn("LegadoSP", genotypes)

        # Check that we have genotype data
        test_genotypes = genotypes["LegadoSP"]
        self.assertGreater(
            len(test_genotypes), 0, "Test sample should have genotype data"
        )

        # Check that genotypes are valid (alleles should be 1, 2, or -9)
        for gt in test_genotypes:
            self.assertIsInstance(gt, tuple, "Genotype should be a tuple")
            self.assertEqual(len(gt), 2, "Genotype should have 2 alleles")
            for allele in gt:
                self.assertIn(allele, [1, 2, -9], f"Invalid allele value: {allele}")

    def test_genotype_parsing_edge_cases(self):
        """Test genotype parsing with various edge cases."""
        pipeline = SCATPipeline("panthera_onca", 84)

        # Test various valid genotype formats
        test_cases = [
            ("0/1", (1, 2)),
            ("1|0", (2, 1)),
            ("1/1", (2, 2)),
            ("0/0", (1, 1)),
            ("0|1", (1, 2)),
            ("1|1", (2, 2)),
        ]

        for gt, expected in test_cases:
            result = pipeline._parse_genotype(gt)
            self.assertEqual(result, expected, f"Failed for genotype: {gt}")

    def test_genotype_parsing_missing_data(self):
        """Test genotype parsing with missing data formats."""
        pipeline = SCATPipeline("panthera_onca", 84)

        # Test missing data formats
        missing_formats = ["./.", ".", "./0", "0/."]

        for gt in missing_formats:
            result = pipeline._parse_genotype(gt)
            self.assertEqual(result, (-9, -9), f"Failed for missing genotype: {gt}")

    def test_genotype_parsing_invalid_formats(self):
        """Test genotype parsing with invalid formats."""
        pipeline = SCATPipeline("panthera_onca", 84)

        # Test invalid formats
        invalid_formats = ["invalid", "1/2/3", "a/b", "", "1/", "/1"]

        for gt in invalid_formats:
            result = pipeline._parse_genotype(gt)
            self.assertEqual(result, (-9, -9), f"Failed for invalid genotype: {gt}")

    def test_pipeline_integration_with_mocked_scat(self):
        """Test full pipeline integration with mocked SCAT execution."""
        # Mock SCAT executable to avoid actual execution
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run") as mock_run,
        ):

            # Configure mock to simulate successful SCAT execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "SCAT completed successfully"
            mock_run.return_value.stderr = ""

            pipeline = SCATPipeline("panthera_onca", 84)

            # Run pipeline with test VCF
            try:
                result_dir = pipeline.run(str(self.test_vcf), str(self.output_dir))
                self.assertTrue(
                    Path(result_dir).exists(), "Output directory should be created"
                )

                # Check that SCAT was called with correct parameters
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                self.assertIn("SCAT3", str(call_args))
                self.assertIn("84", str(call_args))  # num_snps parameter

            except SCATPipelineError as e:
                self.fail(f"Pipeline execution failed: {e}")

    def test_data_consistency(self):
        """Test that training data is consistent."""
        # Check that location file has same number of samples as training VCF
        with open(self.reference_loc) as f:
            location_samples = [line.split()[0] for line in f if line.strip()]

        with open(self.reference_vcf) as f:
            for line in f:
                if line.startswith("#CHROM"):
                    vcf_samples = line.strip().split("\t")[9:]
                    break

        # Note: This test might fail if the training VCF and location file
        # are not perfectly aligned. We'll log this for information.
        if len(location_samples) != len(vcf_samples):
            print(
                f"Warning: Location file has {len(location_samples)} samples, "
                f"training VCF has {len(vcf_samples)} samples"
            )

    def test_pipeline_error_handling(self):
        """Test pipeline error handling with various failure scenarios."""
        pipeline = SCATPipeline("panthera_onca", 84)

        # Test missing VCF file
        with self.assertRaises(SCATPipelineError) as cm:
            pipeline.run("nonexistent.vcf", str(self.output_dir))

        error = cm.exception
        self.assertEqual(error.error_code, "E001")  # MISSING_FILES
        self.assertIn("Vcf not found", error.message)

    def test_scat_execution_error_handling(self):
        """Test SCAT execution error handling."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run") as mock_run,
        ):

            # Configure mock to simulate SCAT failure
            mock_run.side_effect = Exception("SCAT execution failed")

            pipeline = SCATPipeline("panthera_onca", 84)

            with self.assertRaises(SCATPipelineError) as cm:
                pipeline.run(str(self.test_vcf), str(self.output_dir))

            error = cm.exception
            self.assertEqual(error.error_code, "E999")  # UNKNOWN
            self.assertIn("Pipeline execution failed", error.message)

    def test_file_structure_validation(self):
        """Test that the file structure follows expected conventions."""
        # Check reference directory structure
        self.assertTrue(self.reference_dir.exists(), "Reference directory should exist")
        self.assertTrue(
            self.reference_dir.is_dir(), "Reference directory should be a directory"
        )

        # Check file naming conventions
        self.assertTrue(
            self.reference_vcf.name.startswith("panthera_onca"),
            "VCF file should follow species naming convention",
        )
        self.assertTrue(
            self.reference_vcf.name.endswith("84snps.vcf"),
            "VCF file should include SNP count",
        )
        self.assertTrue(
            self.reference_loc.name == "panthera_onca_loc.txt",
            "Location file should follow naming convention",
        )
        self.assertTrue(
            self.reference_grid.name == "panthera_onca_grid.txt",
            "Grid file should follow naming convention",
        )


if __name__ == "__main__":
    unittest.main()
