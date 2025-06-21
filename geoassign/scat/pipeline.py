#!/usr/bin/env python3
"""
Geographic Assignment Pipeline using SCAT
Converts VCF files to SCAT format and runs geographic assignment
"""

import subprocess
import sys
from pathlib import Path


class SCATPipeline:
    def __init__(
        self,
        data_dir: str = "data",
        inference_dir: str = "inference_api",
        species: str = "panthera_onca",
    ):
        """
        Initialize the SCAT pipeline

        Args:
            data_dir: Directory containing input data
            inference_dir: Directory containing SCAT data and instructions
            species: Species name for reference data
        """
        self.data_dir = Path(data_dir)
        self.inference_dir = Path(inference_dir)
        self.species = species

        # Load reference data for the species
        self.reference_dir = Path(__file__).parent.parent / "reference" / species
        self.grid_file = self.reference_dir / "grid_bPon.txt"

        if not self.grid_file.exists():
            raise FileNotFoundError(f"Grid file not found: {self.grid_file}")

        print(f"Initialized SCAT pipeline for {species}")
        print(f"Grid file: {self.grid_file}")
        print(f"Reference directory: {self.reference_dir}")

    def vcf_to_scat_format(
        self, vcf_file: str, output_dir: str = "temp_scat"
    ) -> tuple[str, str]:
        """
        Convert VCF file to SCAT genotype format

        Args:
            vcf_file: Path to input VCF file
            output_dir: Directory to store output files

        Returns:
            Tuple of (genotype_file, location_file) paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"Converting VCF file: {vcf_file}")

        # Read VCF file
        vcf_data = self._read_vcf(vcf_file)

        # Convert to SCAT format
        genotype_file = output_path / "genotype_scat.txt"
        location_file = output_path / "location_scat.txt"

        self._write_scat_genotype(vcf_data, genotype_file)
        self._write_scat_location(vcf_data, location_file)

        return str(genotype_file), str(location_file)

    def _read_vcf(self, vcf_file: str) -> dict:
        """Read VCF file and extract sample information"""
        samples = []
        genotypes = {}

        with open(vcf_file) as f:
            for line in f:
                if line.startswith("#"):
                    if line.startswith("#CHROM"):
                        # Parse sample names
                        parts = line.strip().split("\t")
                        samples = parts[9:]  # Skip metadata columns
                        print(f"Found {len(samples)} samples: {samples[:5]}...")
                    continue

                # Parse variant line
                parts = line.strip().split("\t")
                ref = parts[3]
                alt = parts[4]

                # Parse genotypes for each sample
                for i, sample in enumerate(samples):
                    if sample not in genotypes:
                        genotypes[sample] = []

                    gt_info = parts[9 + i]
                    gt_parts = gt_info.split(":")
                    gt = gt_parts[0]  # Genotype field

                    # Convert genotype to numeric format
                    if gt == "0/0" or gt == "0|0":
                        genotype = f"{ref}/{ref}"
                    elif gt == "1/1" or gt == "1|1":
                        genotype = f"{alt}/{alt}"
                    elif gt == "0/1" or gt == "0|1" or gt == "1/0" or gt == "1|0":
                        genotype = f"{ref}/{alt}"
                    elif gt == "./." or gt == ".":
                        genotype = "0/0"  # Missing data
                    else:
                        genotype = "0/0"  # Default for unknown

                    genotypes[sample].append(genotype)

        return {
            "samples": samples,
            "genotypes": genotypes,
            "num_variants": len(genotypes[samples[0]]) if samples else 0,
        }

    def _write_scat_genotype(self, vcf_data: dict, output_file: Path):
        """Write genotype data in SCAT format"""
        samples = vcf_data["samples"]
        genotypes = vcf_data["genotypes"]
        num_variants = vcf_data["num_variants"]

        print(
            f"Writing genotype file with {num_variants} variants for {len(samples)} samples"
        )

        with open(output_file, "w") as f:
            for i, sample in enumerate(samples):
                # Write two lines per sample (diploid)
                location_id = i + 1  # Sequential location ID

                # First haplotype
                f.write(f"{sample} {location_id}")
                for variant_idx in range(num_variants):
                    gt = genotypes[sample][variant_idx]
                    if gt == "0/0":
                        f.write(" -9")  # Missing data
                    else:
                        alleles = gt.split("/")
                        f.write(f" {alleles[0]}")
                f.write("\n")

                # Second haplotype
                f.write(f"{sample} {location_id}")
                for variant_idx in range(num_variants):
                    gt = genotypes[sample][variant_idx]
                    if gt == "0/0":
                        f.write(" -9")  # Missing data
                    else:
                        alleles = gt.split("/")
                        f.write(f" {alleles[1]}")
                f.write("\n")

    def _write_scat_location(self, vcf_data: dict, output_file: Path):
        """Write location file in SCAT format"""
        samples = vcf_data["samples"]

        print(f"Writing location file for {len(samples)} samples")

        # For now, we'll use dummy coordinates
        # In a real implementation, you'd need actual coordinates for each sample
        with open(output_file, "w") as f:
            for i, sample in enumerate(samples):
                # Using dummy coordinates - replace with real coordinates
                lat = -15.0 + (i * 0.1)  # Dummy latitude
                lon = -50.0 + (i * 0.1)  # Dummy longitude
                f.write(f"{sample} {i+1} {lat:.6f} {lon:.6f}\n")

    def run_scat_assignment(
        self,
        genotype_file: str,
        location_file: str,
        output_dir: str = "scat_output",
        num_loci: int = 84,
        niter: int = 100,
        nthin: int = 100,
        nburn: int = 100,
    ) -> str:
        """
        Run SCAT geographic assignment

        Args:
            genotype_file: Path to genotype file
            location_file: Path to location file
            output_dir: Output directory for SCAT results
            num_loci: Number of loci
            niter: Number of MCMC iterations
            nthin: Thinning parameter
            nburn: Burn-in iterations

        Returns:
            Path to output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Check if SCAT executable exists
        scat_exec = Path.home() / "support_repos" / "scat" / "src" / "SCAT3"
        if not scat_exec.exists():
            print(f"SCAT executable not found at {scat_exec}")
            print("Please compile SCAT first:")
            print("cd ~/support_repos/scat/src && make")
            return None

        # Build SCAT command
        cmd = [
            str(scat_exec),
            "-A",
            "1",
            "1",
            "-g",
            str(self.grid_file),
            genotype_file,
            location_file,
            str(output_path),
            str(num_loci),
            str(niter),
            str(nthin),
            str(nburn),
        ]

        print(f"Running SCAT command: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("SCAT completed successfully")
            print(f"Output directory: {output_path}")
            return str(output_path)
        except subprocess.CalledProcessError as e:
            print(f"SCAT failed with error: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return None

    def process_vcf_file(
        self, vcf_file: str, output_dir: str = "results"
    ) -> str | None:
        """
        Complete pipeline: VCF to SCAT assignment

        Args:
            vcf_file: Path to input VCF file
            output_dir: Output directory for results

        Returns:
            Path to results directory or None if failed
        """
        try:
            # Convert VCF to SCAT format
            genotype_file, location_file = self.vcf_to_scat_format(vcf_file)

            # Run SCAT assignment
            results_dir = self.run_scat_assignment(
                genotype_file, location_file, output_dir=output_dir
            )

            if results_dir:
                print("Pipeline completed successfully!")
                print(f"Results available in: {results_dir}")
                return results_dir
            else:
                print("Pipeline failed during SCAT execution")
                return None

        except Exception as e:
            print(f"Pipeline failed: {e}")
            return None


def main():
    """Main function to run the pipeline"""
    if len(sys.argv) < 2:
        print("Usage: python inference_pipeline.py <vcf_file> [output_dir]")
        sys.exit(1)

    vcf_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "results"

    # Initialize pipeline
    pipeline = SCATPipeline()

    # Run pipeline
    results = pipeline.process_vcf_file(vcf_file, output_dir)

    if results:
        print(f"Success! Results in: {results}")
    else:
        print("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
