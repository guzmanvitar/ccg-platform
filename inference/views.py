from django.shortcuts import render, redirect
from .forms import UploadFileForm
from django.urls import reverse

def home(request):
    return render(request, "inference/home.html")


def jaguar_tools(request):
    return render(request, "inference/jaguar_tools.html")


def upload_data(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Here we'll later upload to Seafile
            handle_uploaded_file(file)  # Local stub
            return redirect(reverse('jaguar_tools'))
    else:
        form = UploadFileForm()
    return redirect(reverse('jaguar_tools'))


def handle_uploaded_file(file):
    with open(f'/tmp/{file.name}', 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
