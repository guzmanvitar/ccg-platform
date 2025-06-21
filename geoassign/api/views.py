"""
API views for geographic assignment functionality
"""

import tempfile
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..scat.pipeline import SCATPipeline


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

            # Get species parameter (POST body, form, or query param)
            species = (
                request.data.get("species")
                or request.query_params.get("species")
                or "panthera_onca"
            )

            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Save uploaded file
                vcf_path = temp_path / uploaded_file.name
                with open(vcf_path, "wb+") as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)

                # Initialize pipeline with species
                pipeline = SCATPipeline(species=species)

                # Run the pipeline
                results_dir = pipeline.process_vcf_file(
                    str(vcf_path), output_dir=str(temp_path / "results")
                )

                if results_dir:
                    # Read and return results
                    results = self._read_scat_results(results_dir)
                    return Response(
                        {
                            "status": "success",
                            "message": f"Geo assignment completed for species: {species}",
                            "results": results,
                        }
                    )
                else:
                    return Response(
                        {"error": "Pipeline failed to complete"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

        except Exception as e:
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
        # Use the sample VCF file from data directory
        sample_vcf = Path(settings.BASE_DIR) / "data" / "jaguar.57samples.84snps.vcf"

        if not sample_vcf.exists():
            return Response(
                {"error": "Sample VCF file not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get species parameter (POST body, form, or query param)
        species = (
            request.data.get("species")
            or request.query_params.get("species")
            or "panthera_onca"
        )

        # Initialize pipeline with species
        pipeline = SCATPipeline(species=species)

        # Run with sample file
        results_dir = pipeline.process_vcf_file(
            str(sample_vcf), output_dir="test_results"
        )

        if results_dir:
            return Response(
                {
                    "status": "success",
                    "message": f"Test pipeline completed successfully for species: {species}",
                    "results_directory": results_dir,
                }
            )
        else:
            return Response(
                {"error": "Test pipeline failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        return Response(
            {"error": f"Test failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
