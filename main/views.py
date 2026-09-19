import os
from django.contrib import messages
from django.core import serializers
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm

from main.models import Experience, Skill, Education, Project, TechStack
from main.forms import ExperienceForm, SkillForm, EducationForm, ProjectForm, TechStackForm

def show_main(request):
    educations = Education.objects.all()
    tech_stacks = TechStack.objects.all()

    context = {
        "name": "Reshandy Taftazani Aulya",
        "npm": "2506547651",
        "study_program": "S1 Ilmu Komputer",
        "bio": (
            "CS student at Universitas Indonesia."
        ),
        'education_list': educations,
        'tech_stacks': tech_stacks,
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

@login_required(login_url='/login/')
def create_experience(request):
    form = ExperienceForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pengalaman baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "experience_form.html", context)

@login_required(login_url='/login/')
def edit_experience(request, id):
    experience = get_object_or_404(Experience, pk=id)
    form = ExperienceForm(request.POST or None, instance=experience)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pengalaman berhasil diperbarui!")
        return redirect("main:dashboard")

    context = {
        "name": "Reshandy",
        "form": form,
        "is_edit": True,
    }
    return render(request, "experience_form.html", context)

@login_required(login_url='/login/')
def create_skill(request):
    form = SkillForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Keahlian baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "skill_form.html", context)

@login_required(login_url='/login/')
def create_education(request):
    form = EducationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pendidikan baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "education_form.html", context)

def show_projects(request):
    title_query = request.GET.get("title", "").strip()
    tag_query = request.GET.get("tag", "").strip()
    projects = Project.objects.prefetch_related('tags').all()
    
    if title_query:
        projects = projects.filter(title__icontains=title_query)
        
    if tag_query:
        projects = projects.filter(tags__slug=tag_query)
    
    categories = set(p.category for p in projects if p.category)

    context = {
        "name": "Reshandy",
        "project_list": projects,
        "title_query": title_query,
        "categories": categories,
    }
    return render(request, "project.html", context)

@login_required(login_url='/login/')
def create_project(request):
    form = ProjectForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proyek baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "projects_form.html", context)

def get_projects_json(request):
    title_query = request.GET.get("title", "").strip()
    projects = Project.objects.all()

    if title_query:
        projects = projects.filter(title__icontains=title_query)

    projects_json = serializers.serialize("json", projects)
    return HttpResponse(projects_json, content_type="application/json")

@login_required(login_url='/login/')
def delete_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project berhasil dihapus!")
        return redirect("main:dashboard")

    return redirect("main:dashboard")

def login_user(request):
    if request.user.is_authenticated:
        return redirect('main:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('main:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
        
    return render(request, 'login.html', {'form': form, 'name': 'Reshandy'})

def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('main:show_main')

@login_required(login_url='/login/')
def show_dashboard(request):
    context = {
        "name": "Reshandy",
        "experiences": Experience.objects.all(),
        "skills": Skill.objects.all(),
        "educations": Education.objects.all(),
        "projects": Project.objects.all(),
        "tech_stacks": TechStack.objects.all(),
    }
    return render(request, "dashboard.html", context)

@login_required(login_url='/login/')
def delete_experience(request, id):
    experience = get_object_or_404(Experience, pk=id)
    if request.method == "POST":
        experience.delete()
        messages.success(request, "Experience berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def delete_skill(request, id):
    skill = get_object_or_404(Skill, pk=id)
    if request.method == "POST":
        skill.delete()
        messages.success(request, "Skill berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def delete_education(request, id):
    education = get_object_or_404(Education, pk=id)
    if request.method == "POST":
        education.delete()
        messages.success(request, "Education berhasil dihapus!")
@login_required(login_url='/login/')
def edit_project(request, id):
    project = get_object_or_404(Project, pk=id)
    form = ProjectForm(request.POST or None, instance=project)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proyek berhasil diperbarui!")
        return redirect("main:dashboard")
        
    context = {
        "name": "Reshandy",
        "form": form,
        "is_edit": True,
    }
    return render(request, "projects_form.html", context)

@login_required(login_url='/login/')
def edit_skill(request, id):
    skill = get_object_or_404(Skill, pk=id)
    form = SkillForm(request.POST or None, instance=skill)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Keahlian berhasil diperbarui!")
        return redirect("main:dashboard")
        
    context = {
        "name": "Reshandy",
        "form": form,
        "is_edit": True,
    }
    return render(request, "skill_form.html", context)

@login_required(login_url='/login/')
def edit_education(request, id):
    education = get_object_or_404(Education, pk=id)
    form = EducationForm(request.POST or None, instance=education)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pendidikan berhasil diperbarui!")
        return redirect("main:dashboard")
        
    context = {
        "name": "Reshandy",
        "form": form,
        "is_edit": True,
    }
    return render(request, "education_form.html", context)

@login_required(login_url='/login/')
def create_tech_stack(request):
    form = TechStackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tech Stack baru berhasil ditambahkan!")
        return redirect("main:dashboard")
    context = {
        "name": "Reshandy",
        "form": form,
    }
    return render(request, "tech_stack_form.html", context)

@login_required(login_url='/login/')
def edit_tech_stack(request, id):
    tech = get_object_or_404(TechStack, pk=id)
    form = TechStackForm(request.POST or None, instance=tech)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tech Stack berhasil diperbarui!")
        return redirect("main:dashboard")
    context = {
        "name": "Reshandy",
        "form": form,
        "is_edit": True,
    }
    return render(request, "tech_stack_form.html", context)

@login_required(login_url='/login/')
def delete_tech_stack(request, id):
    tech = get_object_or_404(TechStack, pk=id)
    if request.method == "POST":
        tech.delete()
        messages.success(request, "Tech Stack berhasil dihapus!")
    return redirect("main:dashboard")