#!/usr/bin/env python3
"""
SCAT Inference Pipeline

This module processes a VCF file for a new specimen by merging it with fixed training data
(genotypes + locations + grid), converting to SCAT format, and running geographic assignment.

Expected input:
- A single-sample VCF file (new specimen)
- Reference training data (VCF + location + grid) based on species and num_snps

Outputs:
- SCAT-formatted genotype file
- SCAT-formatted location file (with target individual marked with -1)
- Assignment output folder with predicted location
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class SCATPipelineError(Exception):
    """
    Custom exception for SCAT pipeline errors.

    Provides detailed error information including error codes, context,
    and suggestions for resolution.
    """

    # Error codes for different types of failures
    ERROR_CODES = {
        "MISSING_FILES": "E001",
        "INVALID_VCF": "E002",
        "INVALID_COORDINATES": "E003",
        "SCAT_EXECUTION": "E004",
        "GENOTYPE_MISMATCH": "E005",
        "FILE_PARSING": "E006",
        "PERMISSION_DENIED": "E007",
        "UNKNOWN": "E999",
    }

    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: str = None,
        file_path: str = None,
        suggestion: str = None,
    ):
        """
        Initialize SCAT pipeline error.

        Args:
            message: Primary error message
            error_code: Error code for categorization
            details: Additional error details
            file_path: Path to file that caused the error
            suggestion: Suggested resolution
        """
        self.message = message
        self.error_code = error_code or self.ERROR_CODES["UNKNOWN"]
        self.details = details
        self.file_path = file_path
        self.suggestion = suggestion

        # Build the full error message
        full_message = f"[{self.error_code}] {self.message}"

        if self.details:
            full_message += f"\nDetails: {self.details}"

        if self.file_path:
            full_message += f"\nFile: {self.file_path}"

        if self.suggestion:
            full_message += f"\nSuggestion: {self.suggestion}"

        super().__init__(full_message)

    def __str__(self):
        """Return the formatted error message."""
        return self.message

    @classmethod
    def missing_files(cls, missing_files: list, reference_dir: str):
        """Create error for missing reference files."""
        return cls(
            message="Missing required reference files",
            error_code=cls.ERROR_CODES["MISSING_FILES"],
            details="Missing files:\n" + "\n".join(f"  - {f}" for f in missing_files),
            suggestion=f"Ensure all required files exist in {reference_dir}",
        )

    @classmethod
    def invalid_vcf(cls, vcf_path: str, reason: str):
        """Create error for invalid VCF file."""
        return cls(
            message=f"Invalid VCF file: {reason}",
            error_code=cls.ERROR_CODES["INVALID_VCF"],
            file_path=vcf_path,
            suggestion="Check VCF format and ensure it contains valid genotype data",
        )

    @classmethod
    def scat_execution_failed(
        cls, command: str, return_code: int, stdout: str = None, stderr: str = None
    ):
        """Create error for SCAT execution failure."""
        details = f"Command: {command}\nReturn code: {return_code}"
        if stdout:
            details += f"\nSTDOUT: {stdout}"
        if stderr:
            details += f"\nSTDERR: {stderr}"

        return cls(
            message="SCAT execution failed",
            error_code=cls.ERROR_CODES["SCAT_EXECUTION"],
            details=details,
            suggestion="Check SCAT installation and input file formats",
        )

    @classmethod
    def genotype_mismatch(cls, test_loci: int, training_loci: int):
        """Create error for genotype data mismatch."""
        return cls(
            message="Genotype data mismatch between test and training samples",
            error_code=cls.ERROR_CODES["GENOTYPE_MISMATCH"],
            details=f"Test sample has {test_loci} loci, training data has {training_loci} loci",
            suggestion="Ensure test VCF contains the same SNP panel as training data",
        )

    @classmethod
    def file_not_found(cls, file_path: str, file_type: str = "file"):
        """Create error for file not found."""
        return cls(
            message=f"{file_type.capitalize()} not found",
            error_code=cls.ERROR_CODES["MISSING_FILES"],
            file_path=file_path,
            suggestion=f"Check that {file_path} exists and is accessible",
        )

    @classmethod
    def permission_denied(cls, file_path: str, operation: str = "access"):
        """Create error for permission issues."""
        return cls(
            message=f"Permission denied: cannot {operation} file",
            error_code=cls.ERROR_CODES["PERMISSION_DENIED"],
            file_path=file_path,
            suggestion="Check file permissions and ensure read/write access",
        )


class SCATPipeline:
    """
    SCAT (Spatial Continuous Assignment Test) pipeline for geographic assignment.

    This class handles the complete workflow from VCF input to geographic assignment
    by merging new specimens with training data and running SCAT inference.
    """

    def __init__(self, species: str, num_snps: int = 84):
        """
        Initialize the SCAT pipeline with species and number of SNPs.

        Args:
            species: Species name (e.g., 'panthera_onca')
            num_snps: Number of SNPs in the panel (default: 84)

        Raises:
            SCATPipelineError: If required reference files are missing
        """
        self.species = species
        self.num_snps = num_snps

        # Determine reference directory and file paths
        self.reference_dir = Path("geoassign/reference") / species
        self.training_vcf = self.reference_dir / f"{species}.{num_snps}snps.vcf"
        self.training_loc = self.reference_dir / f"{species}_loc.txt"
        self.grid_file = self.reference_dir / f"{species}_grid.txt"
        self.scat_exec = Path.home() / "support_repos" / "scat" / "src" / "SCAT3"

        # Validate required files exist
        self._validate_reference_files()

        logger.info(f"SCAT pipeline initialized for {species} with {num_snps} SNPs")

    def _validate_reference_files(self) -> None:
        """
        Validate that all required reference files exist.

        Raises:
            SCATPipelineError: If any required file is missing
        """
        required_files = {
            "Training VCF": self.training_vcf,
            "Training locations": self.training_loc,
            "Grid file": self.grid_file,
            "SCAT executable": self.scat_exec,
        }

        missing_files = []
        for name, file_path in required_files.items():
            if not file_path.exists():
                missing_files.append(f"{name}: {file_path}")

        if missing_files:
            raise SCATPipelineError.missing_files(
                missing_files, str(self.reference_dir)
            )

    def run(self, test_vcf: str, output_dir: str) -> str:
        """
        Complete pipeline from single-sample VCF to SCAT assignment.

        Args:
            test_vcf: Path to new sample's VCF file
            output_dir: Output folder for SCAT results

        Returns:
            Path to the output folder containing SCAT inference results

        Raises:
            SCATPipelineError: If pipeline execution fails
        """
        logger.info(f"Starting SCAT pipeline for VCF: {test_vcf}")

        # Validate inputs
        test_vcf_path = Path(test_vcf)
        if not test_vcf_path.exists():
            raise SCATPipelineError.file_not_found(test_vcf, "VCF")

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        merged_geno = out_dir / "merged_genotype.txt"
        merged_loc = out_dir / "merged_location.txt"

        try:
            # Step 1: Merge new specimen and training into SCAT-compatible files
            logger.info("Converting VCFs to SCAT format...")
            self._convert_vcfs_to_scat_format(test_vcf, merged_geno, merged_loc)

            # Step 2: Run SCAT
            logger.info("Running SCAT inference...")
            self._run_scat(merged_geno, merged_loc, out_dir)

            logger.info(f"SCAT pipeline completed successfully. Results in: {out_dir}")
            return str(out_dir)

        except Exception as e:
            logger.error(f"SCAT pipeline failed: {e}")
            raise SCATPipelineError(
                f"Pipeline execution failed: {e}",
                error_code=SCATPipelineError.ERROR_CODES["UNKNOWN"],
            ) from e

    def _run_scat(self, geno_file: Path, loc_file: Path, output_dir: Path) -> None:
        """
        Execute SCAT with the given input files.

        Args:
            geno_file: Path to genotype file
            loc_file: Path to location file
            output_dir: Directory for SCAT output

        Raises:
            SCATPipelineError: If SCAT execution fails
        """
        scat_cmd = [
            str(self.scat_exec),
            "-A",
            "1",
            "1",
            "-g",
            str(self.grid_file.absolute()),
            str(geno_file),
            str(loc_file),
            str(output_dir),
            str(self.num_snps),
            "100",
            "100",
            "100",  # niter, nthin, nburn
        ]

        logger.debug(f"Running SCAT command: {' '.join(scat_cmd)}")

        try:
            result = subprocess.run(
                scat_cmd, check=True, capture_output=True, text=True, cwd=output_dir
            )
            logger.debug(f"SCAT stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"SCAT stderr: {result.stderr}")

        except subprocess.CalledProcessError as e:
            logger.error(f"SCAT execution failed with return code {e.returncode}")
            logger.error(f"SCAT stdout: {e.stdout}")
            logger.error(f"SCAT stderr: {e.stderr}")
            raise SCATPipelineError.scat_execution_failed(
                command=" ".join(scat_cmd),
                return_code=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
            ) from e

    def _convert_vcfs_to_scat_format(
        self, test_vcf: str, out_geno: Path, out_loc: Path
    ) -> None:
        """
        Merge the test sample's VCF with the training data into SCAT-compatible files.

        The test individual is placed at the top of the genotype file with location ID -1.
        The test individual's location is excluded from the location file (as required by SCAT).

        Args:
            test_vcf: Path to VCF file for the new specimen
            out_geno: Path to output genotype file (SCAT format)
            out_loc: Path to output location file (SCAT format)

        Raises:
            SCATPipelineError: If VCF parsing or file writing fails
        """
        try:
            # Parse training and test genotypes
            logger.debug("Parsing training VCF...")
            tr_samples, tr_genos = self._parse_vcf(self.training_vcf)

            logger.debug("Parsing test VCF...")
            te_samples, te_genos = self._parse_vcf(test_vcf)

            if len(te_samples) != 1:
                raise SCATPipelineError.invalid_vcf(
                    test_vcf,
                    f"should contain exactly one sample, found {len(te_samples)}",
                )

            te_name = te_samples[0]
            te_gt = te_genos[te_name]

            # Validate genotype data consistency
            if len(te_gt) != len(tr_genos[tr_samples[0]]):
                raise SCATPipelineError.genotype_mismatch(
                    test_loci=len(te_gt), training_loci=len(tr_genos[tr_samples[0]])
                )

            # Write merged genotype file
            logger.debug("Writing merged genotype file...")
            self._write_genotype_file(out_geno, te_name, te_gt, tr_samples, tr_genos)

            # Write merged location file: exclude test individual
            logger.debug("Writing merged location file...")
            self._write_location_file(out_loc, te_name)

        except SCATPipelineError:
            # Re-raise SCAT pipeline errors as-is
            raise
        except Exception as e:
            raise SCATPipelineError(
                f"Failed to convert VCFs to SCAT format: {e}",
                error_code=SCATPipelineError.ERROR_CODES["FILE_PARSING"],
            ) from e

    def _parse_vcf(
        self, vcf_path: Path
    ) -> tuple[list[str], dict[str, list[tuple[int, int]]]]:
        """
        Parse a VCF file and extract sample genotypes.

        Args:
            vcf_path: Path to VCF file

        Returns:
            Tuple of (sample_names, genotypes_dict)

        Raises:
            SCATPipelineError: If VCF parsing fails
        """
        samples = []
        genos: dict[str, list[tuple[int, int]]] = {}

        try:
            with open(vcf_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    if line.startswith("#CHROM"):
                        parts = line.split("\t")
                        if len(parts) < 9:
                            raise SCATPipelineError.invalid_vcf(
                                str(vcf_path),
                                f"invalid header at line {line_num}: insufficient columns",
                            )
                        samples = parts[9:]
                        for s in samples:
                            genos[s] = []

                    elif not line.startswith("#") and line:
                        parts = line.split("\t")
                        if len(parts) < 9:
                            logger.warning(
                                f"Skipping malformed line {line_num}: insufficient columns"
                            )
                            continue

                        fmt = parts[8].split(":")
                        if "GT" not in fmt:
                            logger.warning(
                                f"Skipping line {line_num}: no GT field in FORMAT"
                            )
                            continue

                        for i, s in enumerate(samples):
                            if 9 + i >= len(parts):
                                logger.warning(
                                    f"Skipping sample {s} at line {line_num}: missing data"
                                )
                                continue

                            fields = parts[9 + i].split(":")
                            if len(fields) <= fmt.index("GT"):
                                logger.warning(
                                    f"Skipping sample {s} at line {line_num}: missing GT data"
                                )
                                continue

                            gt = fields[fmt.index("GT")]
                            alleles = self._parse_genotype(gt)
                            genos[s].append(alleles)

        except FileNotFoundError:
            raise SCATPipelineError.file_not_found(str(vcf_path), "VCF")
        except PermissionError:
            raise SCATPipelineError.permission_denied(str(vcf_path), "read")
        except Exception as e:
            raise SCATPipelineError.invalid_vcf(
                str(vcf_path), f"parsing failed: {e}"
            ) from e

        if not samples:
            raise SCATPipelineError.invalid_vcf(str(vcf_path), "no samples found")

        return samples, genos

    def _parse_genotype(self, gt: str) -> tuple[int, int]:
        """
        Parse a genotype string and convert to allele codes.

        Args:
            gt: Genotype string (e.g., "0/1", "1|0", "./.")

        Returns:
            Tuple of (allele1, allele2) with 1-based allele codes
        """
        if gt in ["./.", ".", "./0", "0/."]:
            return (-9, -9)

        try:
            sep = "/" if "/" in gt else "|"
            a1, a2 = map(int, gt.split(sep))
            return (a1 + 1, a2 + 1)  # Convert to 1-based
        except (ValueError, TypeError):
            logger.warning(f"Invalid genotype format: {gt}, using missing data")
            return (-9, -9)

    def _write_genotype_block(
        self, f, name: str, loc_id: int, gts: list[tuple[int, int]]
    ) -> None:
        """
        Write two rows for a diploid individual to the genotype file.

        Args:
            f: File handle
            name: Sample name
            loc_id: Location ID
            gts: List of (allele1, allele2) tuples
        """
        f.write(f"{name} {loc_id} " + " ".join(str(a1) for a1, _ in gts) + "\n")
        f.write(f"{name} {loc_id} " + " ".join(str(a2) for _, a2 in gts) + "\n")

    def _write_genotype_file(
        self,
        out_geno: Path,
        te_name: str,
        te_gt: list[tuple[int, int]],
        tr_samples: list[str],
        tr_genos: dict[str, list[tuple[int, int]]],
    ) -> None:
        """
        Write the merged genotype file in SCAT format.

        Args:
            out_geno: Output genotype file path
            te_name: Test sample name
            te_gt: Test sample genotypes
            tr_samples: Training sample names
            tr_genos: Training sample genotypes
        """
        with open(out_geno, "w") as f:
            # Write test individual first with location ID -1
            self._write_genotype_block(f, te_name, -1, te_gt)

            # Write training individuals with sequential location IDs
            for i, name in enumerate(tr_samples):
                self._write_genotype_block(f, name, i + 1, tr_genos[name])

    def _write_location_file(self, out_loc: Path, te_name: str) -> None:
        """
        Write the merged location file, excluding the test individual.

        Args:
            out_loc: Output location file path
            te_name: Test sample name (to exclude)
        """
        with open(self.training_loc) as loc_file:
            with open(out_loc, "w") as f:
                for line in loc_file:
                    line = line.strip()
                    if line:
                        name = line.split()[0]
                        if name != te_name:
                            f.write(line + "\n")


def main():
    """Command-line interface for the SCAT pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run SCAT geographic assignment for a new specimen"
    )
    parser.add_argument(
        "test_vcf", help="Path to the VCF file of the test individual (single sample)"
    )
    parser.add_argument("species", help="Species name (e.g., panthera_onca)")
    parser.add_argument(
        "--num-snps",
        type=int,
        default=84,
        help="Number of SNPs in the panel (default: 84)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="scat_results",
        help="Directory to store SCAT output (default: scat_results)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    pipeline = SCATPipeline(args.species, args.num_snps)
    try:
        result_dir = pipeline.run(args.test_vcf, args.output_dir)
        print(f"✅ SCAT assignment completed. Results saved in: {result_dir}")
    except SCATPipelineError as e:
        print(f"❌ Error running SCAT pipeline: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
