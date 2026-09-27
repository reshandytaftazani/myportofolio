from django.shortcuts import render


def landing_page(request):
    return render(request, "index.html")

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)