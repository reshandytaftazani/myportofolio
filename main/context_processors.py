from django.urls import reverse
from main.access import is_editor


def portfolio_context(request):
    # Error handlers may render before AuthenticationMiddleware has run.
    user = getattr(request, 'user', None)
    return {
        "is_editor": is_editor(user) if user is not None else False,
        "owner_name": "Reshandy Taftazani Aulya",
        "owner_name_short": "Reshandy",
        "npm": "2506547651",
        "study_program": "S1 Ilmu Komputer",
        "desktop_apps": [
            {'id': 'about', 'title': 'About', 'url': reverse('main:show_main') + '#about', 'icon': 'folder'},
            {'id': 'experience', 'title': 'Experience', 'url': reverse('main:show_experience'), 'icon': 'folder'},
            {'id': 'skills', 'title': 'Skills', 'url': reverse('main:show_skills'), 'icon': 'folder'},
            {'id': 'projects', 'title': 'Projects', 'url': reverse('main:show_projects'), 'icon': 'folder'},
            {'id': 'education', 'title': 'Education', 'url': reverse('main:show_main') + '#education', 'icon': 'folder'},
            {'id': 'tech-stack', 'title': 'Tools', 'url': reverse('main:show_main') + '#tech-stack', 'icon': 'folder'},
            {'id': 'contact', 'title': 'Contact', 'url': reverse('main:show_main') + '#contact', 'icon': 'mail'},
        ],
    }
