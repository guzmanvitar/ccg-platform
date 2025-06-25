"""
API views for geographic assignment functionality
"""

import logging
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

            # Create persistent inference directory structure
            base_inference_dir = Path(settings.BASE_DIR) / "data" / "inference"
            base_inference_dir.mkdir(parents=True, exist_ok=True)

            # Create unique inference directory using timestamp and random string
            import random
            import string
            import time

            timestamp = int(time.time())
            random_suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=8)
            )
            inference_dir = (
                base_inference_dir / f"inference_{timestamp}_{random_suffix}"
            )
            inference_dir.mkdir(parents=True, exist_ok=True)

            temp_path = inference_dir

            # Save uploaded file
            vcf_path = temp_path / uploaded_file.name
            with open(vcf_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Initialize pipeline
            pipeline = SCATPipeline(species=species, num_snps=num_snps)

            # Run the pipeline
            results_dir = pipeline.run(
                test_vcf=str(vcf_path), output_dir=str(temp_path / "results")
            )

            # Read and return results
            results = self._read_scat_results(results_dir)
            return Response(
                {
                    "status": "success",
                    "message": (
                        f"Geographic assignment completed for {species} "
                        f"with {num_snps} SNPs"
                    ),
                    "results": results,
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
