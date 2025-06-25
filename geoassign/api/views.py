"""
API views for geographic assignment functionality
"""

import json
import logging
import os
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..scat.pipeline import SCATPipeline, SCATPipelineError

logger = logging.getLogger(__name__)


class GeographicAssignmentView(APIView):
    """
    API endpoint for geographic assignment using VCF files
    """

    parser_classes = [MultiPartParser, FileUploadParser]

    def post(self, request):
        """
        Accept a VCF file and return geographic assignment results
        """
        try:
            # Check if file was uploaded
            if "file" not in request.FILES:
                return Response(
                    {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
                )

            uploaded_file = request.FILES["file"]

            # Validate file type
            if not uploaded_file.name.endswith(".vcf"):
                return Response(
                    {"error": "File must be a VCF file"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get species parameter (optional, defaults to panthera_onca)
            species = (
                request.data.get("species")
                or request.query_params.get("species")
                or "panthera_onca"
            )

            # Get num_snps parameter (optional, defaults to 84)
            try:
                num_snps = int(
                    request.data.get("num_snps")
                    or request.query_params.get("num_snps")
                    or 84
                )
            except (TypeError, ValueError):
                return Response(
                    {"error": "num_snps must be a valid integer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            logger.info(f"Processing VCF file: {uploaded_file.name}")
            logger.info(f"Species: {species}, SNPs: {num_snps}")

            # Require user email as a POST parameter or from authenticated user
            user_email = request.data.get("user_email") or (
                getattr(request.user, "email", None)
                if hasattr(request, "user") and request.user.is_authenticated
                else None
            )
            if not user_email:
                logger.error("User email is required for inference folder structure.")
                return Response(
                    {"error": "User email is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get seafile base directory from POST or use default
            seafile_base_dir = request.data.get("seafile_base_dir") or str(
                Path.home() / "seafile_drive"
            )
            seafile_base_dir = os.path.expanduser(seafile_base_dir)

            # Save uploaded file
            vcf_path = Path(settings.BASE_DIR) / "data" / "temp_upload.vcf"
            with open(vcf_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Compute file hash for folder naming
            import hashlib

            hash_md5 = hashlib.md5()
            with open(vcf_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            file_hash = hash_md5.hexdigest()
            logger.info(f"Computed file hash: {file_hash} for file {vcf_path}")

            # Create persistent inference directory structure matching seafile
            base_inference_dir = Path(settings.BASE_DIR) / "data" / "inference"
            species_inference_dir = (
                base_inference_dir / "panthera-onca" / "inference" / user_email
            )
            species_inference_dir.mkdir(parents=True, exist_ok=True)
            inference_dir = species_inference_dir / f"inference_{file_hash}"
            inference_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created inference directory: {inference_dir}")

            # Move uploaded file to inference directory
            final_vcf_path = inference_dir / uploaded_file.name
            vcf_path.replace(final_vcf_path)

            # Initialize pipeline
            pipeline = SCATPipeline(species=species, num_snps=num_snps)

            # Run the pipeline
            results_dir = pipeline.run(
                test_vcf=str(final_vcf_path), output_dir=str(inference_dir / "results")
            )

            # Read and return results
            results = self._read_scat_results(results_dir)

            # Compute credible region polygon if SCAT output file exists
            credible_region = None
            try:
                from ..utils.credible_region import compute_credible_region_from_file

                scat_output_files = list(Path(results_dir).glob("*"))
                scat_output_file = None

                # Look for LegadoSP file which contains posterior samples
                for file_path in scat_output_files:
                    if file_path.is_file() and file_path.name == "LegadoSP":
                        scat_output_file = file_path
                        break

                if scat_output_file:
                    credible_region = compute_credible_region_from_file(
                        scat_output_file
                    )
                    logger.info(
                        f"Computed credible region with {credible_region['n_samples']} samples"
                    )
                else:
                    logger.warning(
                        "No LegadoSP file found for credible region computation"
                    )
            except Exception as e:
                logger.warning(f"Failed to compute credible region: {e}")
                credible_region = None

            # Add credible region to results if available and save to file
            if credible_region:
                results["credible_region"] = credible_region
                credible_region_file = inference_dir / "credible_region.json"
                try:
                    with open(credible_region_file, "w") as f:
                        json.dump(credible_region, f, indent=2)
                    logger.info(f"Saved credible region data to {credible_region_file}")
                except Exception as e:
                    logger.warning(f"Failed to save credible region data: {e}")
            else:
                logger.info("No credible region computed")

            # Copy the entire inference folder to seafile
            seafile_inference_dir = (
                Path(seafile_base_dir)
                / "panthera-onca"
                / "inference"
                / user_email
                / f"inference_{file_hash}"
            )
            seafile_inference_dir.parent.mkdir(parents=True, exist_ok=True)
            import shutil

            try:
                if seafile_inference_dir.exists():
                    shutil.rmtree(seafile_inference_dir)
                shutil.copytree(inference_dir, seafile_inference_dir)
                logger.info(
                    f"Copied inference folder to seafile: {seafile_inference_dir}"
                )
            except Exception as e:
                logger.warning(f"Failed to copy inference folder to seafile: {e}")

            return Response(
                {
                    "status": "success",
                    "message": (
                        f"Geographic assignment completed for {species} "
                        f"with {num_snps} SNPs"
                    ),
                    "results": results,
                    "seafile_inference_dir": str(seafile_inference_dir),
                }
            )

        except SCATPipelineError as e:
            logger.error(f"SCAT pipeline error: {e}")
            return Response(
                {"error": f"Pipeline error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Unexpected error in geographic assignment: {e}")
            return Response(
                {"error": f"Processing failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _read_scat_results(self, results_dir: str) -> dict:
        """
        Read SCAT results and return structured data
        """
        results_path = Path(results_dir)

        # Look for SCAT output files
        output_files = list(results_path.glob("*"))

        return {
            "output_directory": results_dir,
            "files": [str(f.name) for f in output_files],
            "message": (
                "Results files generated successfully. "
                "Check the output directory for detailed results."
            ),
        }


@api_view(["GET"])
def health_check(request):
    """
    Health check endpoint for the geographic assignment API
    """
    return Response(
        {
            "status": "healthy",
            "service": "geographic_assignment_api",
            "version": "1.0.0",
        }
    )


@api_view(["POST"])
@parser_classes([MultiPartParser])
def test_pipeline(request):
    """
    Test endpoint that runs the pipeline with a sample VCF file
    """
    try:
        # Get species parameter (POST body, form, or query param)
        species = (
            request.data.get("species")
            or request.query_params.get("species")
            or "panthera_onca"
        )

        # Get num_snps parameter (optional, defaults to 84)
        try:
            num_snps = int(
                request.data.get("num_snps")
                or request.query_params.get("num_snps")
                or 84
            )
        except (TypeError, ValueError):
            return Response(
                {"error": "num_snps must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use the sample VCF file from data directory
        sample_vcf = Path(settings.BASE_DIR) / "data" / "jaguar.57samples.84snps.vcf"

        if not sample_vcf.exists():
            return Response(
                {"error": "Sample VCF file not found"}, status=status.HTTP_404_NOT_FOUND
            )

        logger.info(f"Running test pipeline for {species} with {num_snps} SNPs")

        # Initialize pipeline
        pipeline = SCATPipeline(species=species, num_snps=num_snps)

        # Run with sample file
        results_dir = pipeline.run(test_vcf=str(sample_vcf), output_dir="test_results")

        return Response(
            {
                "status": "success",
                "message": (
                    f"Test pipeline completed successfully for {species} "
                    f"with {num_snps} SNPs"
                ),
                "results_directory": results_dir,
            }
        )

    except SCATPipelineError as e:
        logger.error(f"SCAT pipeline error in test: {e}")
        return Response(
            {"error": f"Test pipeline error: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Unexpected error in test pipeline: {e}")
        return Response(
            {"error": f"Test failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
