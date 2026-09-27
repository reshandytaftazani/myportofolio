from django.core.exceptions import PermissionDenied
import datetime
import os
from django.contrib import messages
from django.core import serializers
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from django.core.mail import send_mail
from django.conf import settings
from main.models import Experience, Skill, Education, Project, TechStack, ContactMessage
from main.forms import ExperienceForm, SkillForm, EducationForm, ProjectForm, TechStackForm, ContactMessageForm

def show_main(request):
    last_login = request.COOKIES.get('last_login', 'Belum ada sesi login / Cookie tidak ditemukan')
    educations = Education.objects.all()
    tech_stacks = TechStack.objects.all()
    featured_projects = Project.objects.filter(is_featured=True).prefetch_related('tags')[:3]

    if request.method == "POST":
        # Honeypot check — jika field "website" terisi, kemungkinan bot
        if request.POST.get('website'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Pesan Anda berhasil dikirim!'})
            messages.success(request, "Pesan Anda berhasil dikirim!")
            return redirect('main:show_main')

        form = ContactMessageForm(request.POST)
        if form.is_valid():
            contact = form.save()
            # Send Email
            subject = f"New Contact Message from {contact.name}"
            message = f"Name: {contact.name}\nEmail: {contact.email}\n\nMessage:\n{contact.message}"
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'webmaster@localhost',
                    [os.getenv('CONTACT_RECIPIENT_EMAIL', 'admin@myportofolio.com')],
                    fail_silently=True,
                )
            except Exception as e:
                print(e)

            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Pesan Anda berhasil dikirim!'})

            messages.success(request, "Pesan Anda berhasil dikirim!")
            return redirect('main:show_main')
        else:
            # AJAX error response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
                return JsonResponse({'status': 'error', 'errors': errors}, status=400)
    else:
        form = ContactMessageForm()

    is_editor = request.user.groups.filter(name='Editor').exists() if request.user.is_authenticated else False
    context = {
        "last_login": last_login,
        "bio": (
            "CS student at Universitas Indonesia."
        ),
        'education_list': educations,
        'tech_stacks': tech_stacks,
        'contact_form': form,
        'is_editor': is_editor,
        'featured_projects': featured_projects,
    }
    return render(request, "index.html", context)


def show_experience(request):
    is_editor = request.user.groups.filter(name='Editor').exists() if request.user.is_authenticated else False
    context = {
        "experience_list": Experience.objects.all(),
        "is_editor": is_editor,
    }
    return render(request, "experience.html", context)

def show_skills(request):
    is_editor = request.user.groups.filter(name='Editor').exists() if request.user.is_authenticated else False
    context = {
        "skills": Skill.objects.all(),
        "is_editor": is_editor,
    }
    return render(request, "skills.html", context)

@login_required(login_url='/login/')
def create_experience(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = ExperienceForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pengalaman baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "form": form,
    }
    return render(request, "experience_form.html", context)

@login_required(login_url='/login/')
def edit_experience(request, id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Editor').exists()):
        raise PermissionDenied
    experience = get_object_or_404(Experience, pk=id)
    form = ExperienceForm(request.POST or None, instance=experience)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pengalaman berhasil diperbarui!")
        return redirect("main:dashboard")

    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, "experience_form.html", context)

@login_required(login_url='/login/')
def create_skill(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = SkillForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Keahlian baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "form": form,
    }
    return render(request, "skill_form.html", context)

@login_required(login_url='/login/')
def create_education(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = EducationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pendidikan baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "form": form,
    }
    return render(request, "education_form.html", context)

from main.templatetags.markdown_extras import markdown_format

def show_projects(request):
    title_query = request.GET.get("title", "").strip()
    tag_query = request.GET.get("tag", "").strip()
    projects = Project.objects.prefetch_related('tags').all()
    
    if title_query:
        projects = projects.filter(title__icontains=title_query)
        
    if tag_query:
        projects = projects.filter(tags__slug=tag_query)
    
    # Handle AJAX response for Skeleton Loader demo
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        project_data = []
        for p in projects:
            tags = [{"name": t.name, "color": t.color, "slug": t.slug} for t in p.tags.all()]
            project_data.append({
                "id": p.id,
                "title": p.title,
                "description": markdown_format(p.description),
                "category": p.category,
                "project_url": p.project_url,
                "project_image_url": p.project_image_url,
                "tags": tags,
            })
        return JsonResponse({"projects": project_data})

    categories = set(p.category for p in projects if p.category)
    is_editor = request.user.groups.filter(name='Editor').exists() if request.user.is_authenticated else False

    context = {
        "project_list": projects,
        "title_query": title_query,
        "categories": categories,
        "is_editor": is_editor,
    }
    return render(request, "project.html", context)

@login_required(login_url='/login/')
def create_project(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = ProjectForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proyek baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "form": form,
    }
    return render(request, "projects_form.html", context)

@login_required(login_url="/login/")
def get_projects_json(request):
    title_query = request.GET.get("title", "").strip()
    projects = Project.objects.all()

    if title_query:
        projects = projects.filter(title__icontains=title_query)

    projects_json = serializers.serialize("json", projects, use_natural_foreign_keys=True)
    return HttpResponse(projects_json, content_type="application/json")

@login_required(login_url='/login/')
def delete_project(request, project_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    project = get_object_or_404(Project, pk=project_id)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project berhasil dihapus!")
        return redirect("main:dashboard")

    return redirect("main:dashboard")

@login_required(login_url='/login/')
def register(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Akun berhasil dibuat. Silakan login.")
        return redirect("main:login")

    context = {
        "form": form,
    }
    return render(request, "register.html", context)

def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        response = redirect("main:show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response

    context = {
        "form": form,
    }
    return render(request, "login.html", context)

def logout_user(request):
    logout(request)
    response = redirect('main:show_main')
    response.delete_cookie('last_login')
    return response

@login_required(login_url='/login/')
def show_dashboard(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Editor').exists()):
        raise PermissionDenied
    
    is_editor = request.user.groups.filter(name='Editor').exists()
    
    context = {
        "experiences": Experience.objects.all(),
        "skills": Skill.objects.all(),
        "educations": Education.objects.all(),
        "projects": Project.objects.all(),
        "tech_stacks": TechStack.objects.all(),
        "is_editor": is_editor,
    }
    return render(request, "dashboard.html", context)

@login_required(login_url='/login/')
def delete_experience(request, id):
    if not request.user.is_superuser:
        raise PermissionDenied
    experience = get_object_or_404(Experience, pk=id)
    if request.method == "POST":
        experience.delete()
        messages.success(request, "Experience berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def delete_skill(request, id):
    if not request.user.is_superuser:
        raise PermissionDenied
    skill = get_object_or_404(Skill, pk=id)
    if request.method == "POST":
        skill.delete()
        messages.success(request, "Skill berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def delete_education(request, id):
    if not request.user.is_superuser:
        raise PermissionDenied
    education = get_object_or_404(Education, pk=id)
    if request.method == "POST":
        education.delete()
        messages.success(request, "Education berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def edit_project(request, id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Editor').exists()):
        raise PermissionDenied
    project = get_object_or_404(Project, pk=id)
    form = ProjectForm(request.POST or None, instance=project)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proyek berhasil diperbarui!")
        return redirect("main:dashboard")
        
    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, "projects_form.html", context)

@login_required(login_url='/login/')
def edit_skill(request, id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Editor').exists()):
        raise PermissionDenied
    skill = get_object_or_404(Skill, pk=id)
    form = SkillForm(request.POST or None, instance=skill)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Keahlian berhasil diperbarui!")
        return redirect("main:dashboard")
        
    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, "skill_form.html", context)

@login_required(login_url='/login/')
def edit_education(request, id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Editor').exists()):
        raise PermissionDenied
    education = get_object_or_404(Education, pk=id)
    form = EducationForm(request.POST or None, instance=education)
    
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pendidikan berhasil diperbarui!")
        return redirect("main:dashboard")
        
    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, "education_form.html", context)

@login_required(login_url='/login/')
def create_tech_stack(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    form = TechStackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tech Stack baru berhasil ditambahkan!")
        return redirect("main:dashboard")
    context = {
        "form": form,
    }
    return render(request, "tech_stack_form.html", context)

@login_required(login_url='/login/')
def edit_tech_stack(request, id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Editor').exists()):
        raise PermissionDenied
    tech = get_object_or_404(TechStack, pk=id)
    form = TechStackForm(request.POST or None, instance=tech)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Tech Stack berhasil diperbarui!")
        return redirect("main:dashboard")
    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, "tech_stack_form.html", context)

@login_required(login_url='/login/')
def delete_tech_stack(request, id):
    if not request.user.is_superuser:
        raise PermissionDenied
    tech = get_object_or_404(TechStack, pk=id)
    if request.method == "POST":
        tech.delete()
        messages.success(request, "Tech Stack berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url="/login/")
def get_experience_json(request):
    data = Experience.objects.all()
    return HttpResponse(serializers.serialize("json", data, use_natural_foreign_keys=True), content_type="application/json")

@login_required(login_url="/login/")
def get_skills_json(request):
    data = Skill.objects.all()
    return HttpResponse(serializers.serialize("json", data, use_natural_foreign_keys=True), content_type="application/json")

@login_required(login_url="/login/")
def get_education_json(request):
    data = Education.objects.all()
    return HttpResponse(serializers.serialize("json", data, use_natural_foreign_keys=True), content_type="application/json")

@login_required(login_url="/login/")
def get_tech_stack_json(request):
    data = TechStack.objects.all()
    return HttpResponse(serializers.serialize("json", data, use_natural_foreign_keys=True), content_type="application/json")
@login_required(login_url="/login/")
def toggle_star_project(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    if request.method == "POST":
        if request.user in project.starred_by.all():
            project.starred_by.remove(request.user)
        else:
            project.starred_by.add(request.user)
    return redirect("main:show_projects")

@login_required(login_url="/login/")
def toggle_star_experience(request, id):
    exp = get_object_or_404(Experience, pk=id)
    if request.method == "POST":
        if request.user in exp.starred_by.all():
            exp.starred_by.remove(request.user)
        else:
            exp.starred_by.add(request.user)
    return redirect("main:show_experience")

@login_required(login_url="/login/")
def toggle_star_skill(request, id):
    skill = get_object_or_404(Skill, pk=id)
    if request.method == "POST":
        if request.user in skill.starred_by.all():
            skill.starred_by.remove(request.user)
        else:
            skill.starred_by.add(request.user)
    return redirect("main:show_skills")

@login_required(login_url="/login/")
def toggle_star_education(request, id):
    edu = get_object_or_404(Education, pk=id)
    if request.method == "POST":
        if request.user in edu.starred_by.all():
            edu.starred_by.remove(request.user)
        else:
            edu.starred_by.add(request.user)
    return redirect("main:show_main")

@login_required(login_url="/login/")
def toggle_star_tech_stack(request, id):
    ts = get_object_or_404(TechStack, pk=id)
    if request.method == "POST":
        if request.user in ts.starred_by.all():
            ts.starred_by.remove(request.user)
        else:
            ts.starred_by.add(request.user)
    return redirect("main:show_main")



