from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render

from .forms import UploadFileForm


def home(request):
    return render(request, "inference/home.html")


def upload_data(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        species = request.POST.get("species", "unknown_species")
        username = "user"  # placeholder

        if form.is_valid():
            file = request.FILES["file"]
            file_ext = Path(file.name).suffix.lower().lstrip(".")

            if file_ext not in ["vcf", "fasta", "fastq"]:
                return JsonResponse(
                    {"success": False, "errors": "Unsupported file format"}, status=400
                )

            handle_uploaded_file(file, species, file_ext, username)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)


def handle_uploaded_file(file, species, file_format, username):
    base_dir = Path.home() / "seafile_drive"
    target_dir = base_dir / species / file_format / username
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / file.name
    with file_path.open("wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)


def jaguar_tools(request):
    base_path = Path.home() / "seafile_drive" / "panthera-onca"
    user = "user"
    uploaded_files = []

    for fmt in ["vcf", "fasta", "fastq", "txt"]:
        folder = base_path / fmt / user
        if folder.exists():
            for f in folder.iterdir():
                if f.is_file():
                    uploaded_files.append(
                        {
                            "name": f.name,
                            "format": fmt,
                            "path": f,
                            "modified": f.stat().st_mtime,
                        }
                    )

    uploaded_files.sort(key=lambda x: x["modified"], reverse=True)

    return render(
        request, "inference/jaguar_tools.html", {"uploaded_files": uploaded_files}
    )
