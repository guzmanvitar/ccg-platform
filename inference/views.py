from django.shortcuts import render


def home(request):
    return render(request, "inference/home.html")


def jaguar_tools(request):
    return render(request, "inference/jaguar_tools.html")
