import hashlib
import json
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .decorators import check_email_verification
from .forms import UploadFileForm

logger = logging.getLogger(__name__)


def home(request):
    return render(request, "inference/home.html")


@login_required
@check_email_verification
def upload_data(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        species = request.POST.get("species", "unknown_species")
        username = request.user.email

        if form.is_valid():
            file = request.FILES["file"]
            file_ext = Path(file.name).suffix.lower().lstrip(".")

            if file_ext not in ["vcf", "fasta", "fastq", "txt"]:
                return JsonResponse(
                    {"success": False, "errors": "Unsupported file format"}, status=400
                )

            handle_uploaded_file(file, species, file_ext, username)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    return JsonResponse({"success": False, "errors": "Method not allowed"}, status=405)


def handle_uploaded_file(file, species, file_format, username):
    base_dir = Path.home() / "seafile_drive"
    target_dir = base_dir / species / file_format / username
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / file.name
    with file_path.open("wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)


def get_file_hash(file_path):
    """Generate a hash for the file to use as a unique identifier"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_inference_status(file_path, username):
    """Check if inference has been run for this file and return status"""
    base_dir = Path.home() / "seafile_drive"
    inference_dir = base_dir / "panthera-onca" / "inference" / username

    if not inference_dir.exists():
        return None

    # Generate file hash for mapping
    file_hash = get_file_hash(file_path)
    mapping_file = inference_dir / "file_mapping.json"

    if mapping_file.exists():
        with open(mapping_file) as f:
            mapping = json.load(f)

        if file_hash in mapping:
            inference_path = inference_dir / mapping[file_hash]
            if inference_path.exists():
                return {
                    "status": "completed",
                    "path": str(inference_path),
                    "files": (
                        list(inference_path.glob("*"))
                        if inference_path.is_dir()
                        else []
                    ),
                }

    return None


@login_required
@check_email_verification
def jaguar_tools(request):
    base_path = Path.home() / "seafile_drive" / "panthera-onca"
    user = request.user.email
    uploaded_files = []

    for fmt in ["vcf", "fasta", "fastq", "txt"]:
        folder = base_path / fmt / user
        if folder.exists():
            for f in folder.iterdir():
                if f.is_file():
                    # Check inference status for this file
                    inference_status = (
                        get_inference_status(f, user) if fmt == "vcf" else None
                    )

                    uploaded_files.append(
                        {
                            "name": f.name,
                            "format": fmt,
                            "path": f,
                            "modified": f.stat().st_mtime,
                            "inference_status": inference_status,
                            "can_run_inference": fmt
                            == "vcf",  # Only VCF files can run inference
                            "file_hash": get_file_hash(f) if fmt == "vcf" else None,
                        }
                    )

    uploaded_files.sort(key=lambda x: x["modified"], reverse=True)

    return render(
        request, "inference/jaguar_tools.html", {"uploaded_files": uploaded_files}
    )


@login_required
@check_email_verification
def run_geographic_inference(request):
    """
    Run geographic inference on a selected uploaded file
    """
    if request.method == "POST":
        try:
            # Get the file path from the request
            file_path = request.POST.get("file_path")
            if not file_path:
                return JsonResponse(
                    {"success": False, "error": "No file path provided"}, status=400
                )

            file_path = Path(file_path)
            if not file_path.exists():
                return JsonResponse(
                    {"success": False, "error": "File not found"}, status=400
                )

            # Validate file type
            if not file_path.name.endswith(".vcf"):
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Only VCF files are supported for geographic inference",
                    },
                    status=400,
                )

            # Check if inference already exists
            user = request.user.email
            inference_status = get_inference_status(file_path, user)
            if inference_status and inference_status["status"] == "completed":
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Inference already completed for this file",
                        "results": {
                            "output_directory": inference_status["path"],
                            "files": [f.name for f in inference_status["files"]],
                            "message": "Results loaded from previous inference",
                        },
                    }
                )

            # Get parameters
            species = request.POST.get("species", "panthera_onca")
            num_snps = int(request.POST.get("num_snps", 84))

            # Set up inference output directory
            base_dir = Path.home() / "seafile_drive"
            inference_dir = base_dir / "panthera-onca" / "inference" / user
            inference_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique output directory for this inference
            file_hash = get_file_hash(file_path)
            output_dir = inference_dir / f"inference_{file_hash}"
            output_dir.mkdir(exist_ok=True)

            # Call the geoassign API
            from geoassign.api.views import GeographicAssignmentView

            # Create a mock request for the API view
            class MockRequest:
                def __init__(self, files, data):
                    self.FILES = files
                    self.data = data
                    self.query_params = {}

            # Create a file-like object from the file path
            with open(file_path, "rb") as f:
                from django.core.files.base import ContentFile

                file_content = f.read()
                file_obj = ContentFile(file_content, name=file_path.name)

            mock_request = MockRequest(
                files={"file": file_obj},
                data={"species": species, "num_snps": num_snps, "user_email": user},
            )

            # Call the geoassign API view
            api_view = GeographicAssignmentView()
            response = api_view.post(mock_request)

            if response.status_code == 200:
                # Extract data from DRF Response object
                response_data = response.data

                # Save mapping for future reference
                mapping_file = inference_dir / "file_mapping.json"
                mapping = {}
                if mapping_file.exists():
                    with open(mapping_file) as f:
                        mapping = json.load(f)

                mapping[file_hash] = f"inference_{file_hash}"

                with open(mapping_file, "w") as f:
                    json.dump(mapping, f, indent=2)

                # Success - return the results from the API
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Geographic inference completed successfully",
                        "results": response_data.get("results", {}),
                        "seafile_inference_dir": response_data.get(
                            "seafile_inference_dir", ""
                        ),
                    }
                )
            else:
                # Error from the API
                error_message = "Unknown error occurred"
                if hasattr(response, "data") and response.data:
                    error_message = response.data.get("error", error_message)

                return JsonResponse(
                    {"success": False, "error": error_message},
                    status=response.status_code,
                )

        except Exception as e:
            logger.error(f"Error in geographic inference: {e}")
            return JsonResponse(
                {"success": False, "error": f"Processing failed: {str(e)}"}, status=500
            )

    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@login_required
@check_email_verification
def view_inference_results(request, file_hash):
    """
    Display inference results with credible region on Google Maps
    """
    try:
        user = request.user.email

        # Get the inference directory from seafile
        base_dir = Path.home() / "seafile_drive"
        inference_dir = (
            base_dir / "panthera-onca" / "inference" / user / f"inference_{file_hash}"
        )

        if not inference_dir.exists():
            return JsonResponse(
                {"success": False, "error": "Inference results not found"}, status=404
            )

        # Read credible region data
        credible_region_file = inference_dir / "credible_region.json"
        credible_region = None

        if credible_region_file.exists():
            with open(credible_region_file) as f:
                credible_region = json.load(f)

        # Get list of result files
        result_files = []
        for item in inference_dir.iterdir():
            if item.is_file():
                result_files.append(
                    {
                        "name": item.name,
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                    }
                )

        # Read Google Maps API key from secrets
        maps_secret_file = Path(settings.BASE_DIR) / ".secrets" / "gcp_maps_secret.json"
        maps_api_key = None
        if maps_secret_file.exists():
            with open(maps_secret_file) as f:
                maps_secret = json.load(f)
                maps_api_key = maps_secret.get("api_key")
                logger.info(
                    f"Loaded Google Maps API key: {maps_api_key[:10]}..."
                    if maps_api_key
                    else "No API key found"
                )
        else:
            logger.warning(f"Google Maps secret file not found: {maps_secret_file}")

        context = {
            "file_hash": file_hash,
            "credible_region": credible_region,
            "result_files": result_files,
            "inference_dir": str(inference_dir),
            "user_email": user,
            "maps_api_key": maps_api_key,
        }

        logger.info(
            f"Rendering results page with API key: {'Present' if maps_api_key else 'Missing'}"
        )
        return render(request, "inference/view_results.html", context)

    except Exception as e:
        logger.error(f"Error viewing inference results: {e}")
        return JsonResponse(
            {"success": False, "error": f"Error loading results: {str(e)}"}, status=500
        )
