import re

with open('main/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

functions_to_restrict = [
    'create_experience', 'edit_experience', 'delete_experience',
    'create_skill', 'edit_skill', 'delete_skill',
    'create_education', 'edit_education', 'delete_education',
    'create_project', 'edit_project', 'delete_project',
    'create_tech_stack', 'edit_tech_stack', 'delete_tech_stack'
]

import_permission_denied = "from django.core.exceptions import PermissionDenied\nimport datetime\n"
if "PermissionDenied" not in content:
    content = import_permission_denied + content

for func in functions_to_restrict:
    pattern = r'(def ' + func + r'\(.*?\):\n)'
    replacement = r'\g<1>    if not request.user.is_superuser:\n        raise PermissionDenied\n'
    content = re.sub(pattern, replacement, content)

login_user_new = '''def login_user(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        response = redirect("main:show_main")
        response.set_cookie('last_login', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return response

    context = {
        "name": "Reshandy Taftazani Aulya",
        "form": form,
    }
    return render(request, "login.html", context)'''
content = re.sub(r'def login_user\(request\):.*?return render\(request, "login\.html", context\)', login_user_new, content, flags=re.DOTALL)

logout_user_new = '''def logout_user(request):
    logout(request)
    response = redirect('main:show_main')
    response.delete_cookie('last_login')
    return response'''
content = re.sub(r'def logout_user\(request\):.*?return redirect\(\'main:show_main\'\)', logout_user_new, content, flags=re.DOTALL)

show_main_pattern = r'(def show_main\(request\):\n)'
content = re.sub(show_main_pattern, r"\g<1>    last_login = request.COOKIES.get('last_login', 'Belum ada sesi login / Cookie tidak ditemukan')\n", content)
content = re.sub(r'("name": "Reshandy",\n)', r'\g<1>        "last_login": last_login,\n', content)

content = re.sub(r'serializers\.serialize\("json", (.*?)\)', r'serializers.serialize("json", \g<1>, use_natural_foreign_keys=True)', content)

toggle_stars = '''
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
'''
content += toggle_stars

with open('main/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

