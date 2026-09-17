from django.contrib import messages
from django.core import serializers
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from main.models import Experience, Skill, Education, Project
from main.forms import ExperienceForm, SkillForm, EducationForm, ProjectForm

def show_main(request):
    educations = Education.objects.all()

    context = {
        "name": "Reshandy Taftazani Aulya",
        "npm": "2506547651",
        "study_program": "S1 Ilmu Komputer",
        "bio": (
            "CS student at Universitas Indonesia."
        ),
        'education_list': educations,
    }
    return render(request, "index.html", context)


def show_experience(request):
    context = {
        "name": "Reshandy",
        "experience_list": Experience.objects.all(),
    }
    return render(request, "experience.html", context)

def show_skills(request):
    context = {
        "name": "Reshandy",
        "skills": Skill.objects.all(),
    }
    return render(request, "skills.html", context)

def create_experience(request):
    form = ExperienceForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pengalaman baru berhasil ditambahkan!")
        return redirect("main:show_experience")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "experience_form.html", context)

def edit_experience(request, id):
    experience = get_object_or_404(Experience, pk=id)
    form = ExperienceForm(request.POST or None, instance=experience)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pengalaman berhasil diperbarui!")
        return redirect("main:show_experience")

    context = {
        "name": "Reshandy",
        "form": form,
        "is_edit": True,
    }
    return render(request, "experience_form.html", context)

def create_skill(request):
    form = SkillForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Keahlian baru berhasil ditambahkan!")
        return redirect("main:show_skills")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "skill_form.html", context)

def create_education(request):
    form = EducationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pendidikan baru berhasil ditambahkan!")
        return redirect("main:show_main")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "education_form.html", context)

import os

def show_projects(request):
    # Tambahkan header rahasia agar get_projects_json tidak menolak request internal ini
    request.META['HTTP_X_PORTFOLIO_SECRET'] = os.environ.get('PORTFOLIO_PASSWORD', 'rahasia123')
    json_response = get_projects_json(request)

    if json_response.status_code == 403:
        projects = []
    else:
        projects = serializers.deserialize(
            "json",
            json_response.content.decode("utf-8"),
        )
        projects = [project.object for project in projects]
        
    title_query = request.GET.get("title", "").strip()
    
    # Ambil semua kategori unik dari proyek yang ada
    categories = set(p.category for p in projects if p.category)

    context = {
        "name": "Reshandy",
        "project_list": projects,
        "title_query": title_query,
        "categories": categories,
    }
    return render(request, "project.html", context)

def create_project(request):
    form = ProjectForm(request.POST or None)

    if request.method == "POST":
        secret = os.environ.get('PORTFOLIO_PASSWORD', 'rahasia123')
        if request.POST.get('password') != secret:
            messages.error(request, "Gagal menambah proyek: Password salah!")
            return redirect("main:show_projects")

        if form.is_valid():
            form.save()
            messages.success(request, "Proyek baru berhasil ditambahkan!")
            return redirect("main:show_projects")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "projects_form.html", context)

def get_projects_json(request):
    secret = os.environ.get('PORTFOLIO_PASSWORD', 'rahasia123')
    if request.headers.get('X-Portfolio-Secret') != secret:
        return HttpResponse("Unauthorized", status=403)

    title_query = request.GET.get("title", "").strip()
    projects = Project.objects.all()

    if title_query:
        projects = projects.filter(title__icontains=title_query)

    projects_json = serializers.serialize("json", projects)
    return HttpResponse(projects_json, content_type="application/json")

def delete_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    if request.method == "POST":
        secret = os.environ.get('PORTFOLIO_PASSWORD', 'rahasia123')
        if request.POST.get('password') != secret:
            messages.error(request, "Gagal menghapus proyek: Password salah!")
            return redirect("main:show_projects")

        project.delete()
        messages.success(request, "Project berhasil dihapus!")
        return redirect("main:show_projects")

    return redirect("main:show_projects")