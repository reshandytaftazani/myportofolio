import datetime
import logging
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from django.core.mail import send_mail
from django.conf import settings
from main.models import Experience, Skill, Education, Project, TechStack, ContactMessage
from main.forms import ExperienceForm, SkillForm, EducationForm, ProjectForm, TechStackForm, ContactMessageForm
from django_ratelimit.decorators import ratelimit
from main.access import is_editor, require_access
from main.resource_api import public_resource_list, resource_context, RESOURCES

logger = logging.getLogger('main')

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def show_main(request):
    featured_projects = Project.objects.filter(is_featured=True).prefetch_related('tags')[:3]

    if request.method == "POST":
        # Honeypot check â€” jika field "website" terisi, kemungkinan bot
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
                recipient = settings.CONTACT_RECIPIENT_EMAIL
                if recipient:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [recipient],
                        fail_silently=False,
                    )
                else:
                    logger.warning("CONTACT_RECIPIENT_EMAIL is not set. Contact email was saved to DB but not sent via SMTP.")
            except Exception as e:
                logger.error("Gagal mengirim email kontak", exc_info=True)

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

    editor = is_editor(request.user)
    context = {
        "bio": (
            "CS student at Universitas Indonesia."
        ),
        'education_resource': resource_context('education'),
        'techstack_resource': resource_context('techstack'),
        'contact_form': form,
        'is_editor': editor,
        'featured_projects': featured_projects,
    }
    return render(request, "index.html", context)


@ensure_csrf_cookie
def show_experience(request):
    editor = is_editor(request.user)
    context = {
        "resource": resource_context('experience'),
        "is_editor": editor,
    }
    return render(request, "experience.html", context)

@ensure_csrf_cookie
def show_skills(request):
    editor = is_editor(request.user)
    context = {
        "resource": resource_context('skills'),
        "is_editor": editor,
    }
    return render(request, "skills.html", context)

@login_required(login_url='/login/')
def create_experience(request):
    require_access(request, "add")
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
    require_access(request, "edit")
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
    require_access(request, "add")
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
    require_access(request, "add")
    form = EducationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pendidikan baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "form": form,
    }
    return render(request, "education_form.html", context)

@ensure_csrf_cookie
def show_projects(request):
    title_query = request.GET.get("title", "").strip()
    categories = (
        Project.objects.order_by()
        .values_list("category", flat=True)
        .exclude(category="")
        .distinct()
        .order_by("category")
    )
    editor = is_editor(request.user)

    context = {
        "title_query": title_query,
        "category_query": request.GET.get("category", "all").strip() or "all",
        "categories": categories,
        "is_editor": editor,
        "form": ProjectForm(),
        "project_resource": resource_context('projects'),
    }
    return render(request, "project.html", context)

@login_required(login_url='/login/')
def create_project(request):
    require_access(request, "add")
    form = ProjectForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proyek baru berhasil ditambahkan!")
        return redirect("main:dashboard")

    context = {
        "form": form,
    }
    return render(request, "projects_form.html", context)

def get_projects_json(request):
    title_query = request.GET.get("title", "").strip()
    category = request.GET.get("category", "").strip()
    projects = Project.objects.prefetch_related('tags', 'starred_by').all()

    if title_query:
        projects = projects.filter(title__icontains=title_query)
    if category and category.lower() != "all":
        projects = projects.filter(category=category)

    # Konstruksi data JSON secara manual agar bisa menyisipkan logika Star
    data = []
    for project in projects:
        starred_users = project.starred_by.all()
        is_starred = request.user in starred_users if request.user.is_authenticated else False
        starred_by_names = ", ".join(user.username for user in starred_users)
        
        # Mengambil nama-nama tag dan menggabungkannya menjadi string (contoh: "Python, Django")
        tech_stack_str = ", ".join(tag.name for tag in project.tags.all())

        data.append({
            "pk": str(project.id),
            "fields": {
                "title": project.title,
                "description": project.description,
                "category": project.category,
                "tech_stack": tech_stack_str or project.category,
                "project_url": project.project_url,
                "project_image_url": project.project_image_url,
                "star_count": starred_users.count(),
                "is_starred": is_starred,
                "starred_by_names": starred_by_names,
            }
        })

    return JsonResponse(data, safe=False)

@require_POST
def create_project_ajax(request):
    denied = require_access(
        request,
        "add",
        "Hanya pemilik portofolio yang dapat menambahkan proyek.",
        json_response=True,
    )
    if denied:
        return denied

    form = ProjectForm(request.POST)
    if form.is_valid():
        project = form.save()
        return JsonResponse(
            {
                "message": "Proyek berhasil ditambahkan.",
                "pk": str(project.id),
                "category": project.category,
            },
            status=201,
        )

    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

@login_required(login_url='/login/')
def delete_project(request, project_id):
    require_access(request, "delete")
    project = get_object_or_404(Project, pk=project_id)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project berhasil dihapus!")
        return redirect("main:dashboard")

    return redirect("main:dashboard")

def register(request):
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        messages.error(request, "Registrasi publik saat ini dinonaktifkan.")
        return redirect("main:show_main")

    form = UserCreationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Akun berhasil dibuat dan berhasil login.")
        response = redirect("main:show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response

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
@ensure_csrf_cookie
def show_dashboard(request):
    require_access(request, "dashboard")
    editor = is_editor(request.user)
    
    context = {
        "resources": [resource_context(name, admin=True) for name in RESOURCES],
        "is_editor": editor,
    }
    return render(request, "dashboard.html", context)

@login_required(login_url='/login/')
def delete_experience(request, id):
    require_access(request, "delete")
    experience = get_object_or_404(Experience, pk=id)
    if request.method == "POST":
        experience.delete()
        messages.success(request, "Experience berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def delete_skill(request, id):
    require_access(request, "delete")
    skill = get_object_or_404(Skill, pk=id)
    if request.method == "POST":
        skill.delete()
        messages.success(request, "Skill berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def delete_education(request, id):
    require_access(request, "delete")
    education = get_object_or_404(Education, pk=id)
    if request.method == "POST":
        education.delete()
        messages.success(request, "Education berhasil dihapus!")
    return redirect("main:dashboard")

@login_required(login_url='/login/')
def edit_project(request, id):
    require_access(request, "edit")
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
    require_access(request, "edit")
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
    require_access(request, "edit")
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
    require_access(request, "add")
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
    require_access(request, "edit")
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
    require_access(request, "delete")
    tech = get_object_or_404(TechStack, pk=id)
    if request.method == "POST":
        tech.delete()
        messages.success(request, "Tech Stack berhasil dihapus!")
    return redirect("main:dashboard")

@require_GET
def get_experience_json(request):
    return public_resource_list(request, 'experience')

@require_GET
def get_skills_json(request):
    return public_resource_list(request, 'skills')

@require_GET
def get_education_json(request):
    return public_resource_list(request, 'education')

@require_GET
def get_tech_stack_json(request):
    return public_resource_list(request, 'techstack')
@login_required(login_url="/login/")
def toggle_star_project(request, project_id):
    require_access(request, "star")
    project = get_object_or_404(Project, pk=project_id)
    if request.method == "POST":
        is_starred = False  # inisialisasi defensif
        if project.starred_by.filter(id=request.user.id).exists():
            project.starred_by.remove(request.user)
            is_starred = False
        else:
            project.starred_by.add(request.user)
            is_starred = True
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            starred_by_names = ", ".join(
                project.starred_by.order_by("username").values_list("username", flat=True)
            )
            return JsonResponse({
                'is_starred': is_starred,
                'count': project.starred_by.count(),
                'starred_by_names': starred_by_names,
            })
    return redirect("main:show_projects")











