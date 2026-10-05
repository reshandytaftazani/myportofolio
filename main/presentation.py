"""Shared read models for HTML and the existing public JSON API."""

from main.models import Project
from main.resource_api import resource_queryset, serialize_resource


def desktop_context(request):
    """Public app shells; non-project records load only through the JSON API."""
    from main.forms import ContactMessageForm
    from main.resource_api import resource_context

    context = {
        'contact_form': ContactMessageForm(),
        'featured_projects': Project.objects.filter(is_featured=True).prefetch_related('tags')[:3],
        'projects': projects_for_request(request),
        'project_resource': resource_context('projects'),
        'title_query': request.GET.get('title', '').strip(),
        'category_query': request.GET.get('category', 'all').strip() or 'all',
        'categories': Project.objects.order_by().values_list('category', flat=True)
            .exclude(category='').distinct().order_by('category'),
    }
    for kind in ('education', 'techstack', 'skills', 'experience'):
        context[kind + '_resource'] = resource_context(kind)
    return context


def projects_for_request(request):
    projects = Project.objects.prefetch_related('tags', 'starred_by').all()
    title = request.GET.get('title', '').strip()
    category = request.GET.get('category', '').strip()
    if title:
        projects = projects.filter(title__icontains=title)
    if category and category.lower() != 'all':
        projects = projects.filter(category=category)
    return projects


def public_items(request, resource):
    return [serialize_resource(resource, obj, request.user)
            for obj in resource_queryset(request, resource)]
