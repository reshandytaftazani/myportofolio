"""Explicit public serializers and role protected AJAX content management."""

from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_POST

from main.access import require_access
from main.forms import ExperienceForm, SkillForm, EducationForm, TechStackForm, ProjectForm, TagForm
from main.models import Experience, Skill, Education, TechStack, Project, Tag
from main.templatetags.markdown_extras import markdown_format


RESOURCES = {
    'experience': {'model': Experience, 'form': ExperienceForm, 'label': 'Experience',
                   'search': ('title', 'company'), 'order': ('-started_at', 'title', 'pk'),
                   'columns': (('title', 'Title'), ('company', 'Company')),
                   'public_view': 'get_experience_json'},
    'skills': {'model': Skill, 'form': SkillForm, 'label': 'Skills',
               'search': ('title', 'level'), 'order': ('title', 'pk'),
               'columns': (('title', 'Title'), ('level', 'Level')),
               'public_view': 'get_skills_json'},
    'education': {'model': Education, 'form': EducationForm, 'label': 'Education',
                  'search': ('school_name',), 'order': ('-start_year', 'pk'),
                  'columns': (('school_name', 'School'), ('period', 'Period')),
                  'public_view': 'get_education_json'},
    'techstack': {'model': TechStack, 'form': TechStackForm, 'label': 'Tech Stack',
                  'search': ('name',), 'order': ('order', 'pk'),
                  'columns': (('name', 'Name'), ('filename', 'Filename'), ('order', 'Order')),
                  'public_view': 'get_tech_stack_json'},
    'projects': {'model': Project, 'form': ProjectForm, 'label': 'Projects',
                 'search': ('title', 'category'), 'order': ('title', 'pk'),
                 'columns': (('title', 'Title'), ('category', 'Category'), ('is_featured', 'Featured')),
                 'public_view': 'get_projects_json'},
}


def resource_form(resource, *args, **kwargs):
    return RESOURCES[resource]['form'](*args, auto_id=f'id_{resource}_%s', **kwargs)


def serialize_tag(tag):
    return {'pk': str(tag.pk), 'fields': {'name': tag.name, 'color': tag.color}}


@require_GET
def manage_tag_list(request):
    denied = require_access(request, 'dashboard', json_response=True)
    if denied:
        return denied
    return JsonResponse([serialize_tag(tag) for tag in Tag.objects.order_by('name', 'pk')], safe=False)


@require_POST
def manage_tag_create(request):
    denied = require_access(request, 'add', json_response=True)
    if denied:
        return denied
    form = TagForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    name = form.cleaned_data['name']
    existing = Tag.objects.filter(name__iexact=name).order_by('pk').first()
    if existing:
        return JsonResponse({'message': 'Tag sudah tersedia dan dipilih.', 'item': serialize_tag(existing)})
    base = slugify(name)[:50] or 'tag'
    tag = form.save(commit=False)
    for attempt in range(3):
        tag.slug = base if attempt == 0 else f'{base[:41]}-{uuid4().hex[:8]}'
        try:
            with transaction.atomic():
                tag.save(force_insert=True)
        except IntegrityError:
            # A matching name may have been created while this request was running.
            existing = Tag.objects.filter(name__iexact=name).order_by('pk').first()
            if existing:
                return JsonResponse({'message': 'Tag sudah tersedia dan dipilih.', 'item': serialize_tag(existing)})
        else:
            return JsonResponse({'message': 'Tag berhasil dibuat dan dipilih.', 'item': serialize_tag(tag)}, status=201)
    return JsonResponse({'message': 'Tag belum dapat disimpan. Silakan coba lagi.'}, status=409)


def resource_context(resource, *, admin=False):
    spec = RESOURCES[resource]
    return {
        'name': resource, 'label': spec['label'], 'columns': spec['columns'],
        'form': resource_form(resource),
        'list_url': reverse('main:manage_resource_list', args=[resource]) if admin
                    else reverse('main:' + spec['public_view']),
        'create_url': reverse('main:manage_resource_create', args=[resource]),
        'detail_url': reverse('main:manage_resource_detail', args=[resource, '__pk__']),
        'edit_url': reverse('main:manage_resource_edit', args=[resource, '__pk__']),
        'delete_url': reverse('main:manage_resource_delete', args=[resource, '__pk__']),
        'star_url': reverse('main:toggle_star_resource', args=[resource, '__pk__']),
    }


def serialize_resource(resource, obj, user=None):
    # Only the explicitly declared portfolio fields leave the server.
    fields = {name: getattr(obj, name) for name in RESOURCES[resource]['form'].Meta.fields
              if name != 'tags'}
    if resource == 'experience':
        fields.update(category_display=obj.get_category_display(), is_ongoing=obj.is_ongoing)
    if resource in {'experience', 'skills'}:
        fields['description_html'] = markdown_format(obj.description)
    if resource == 'projects':
        fields['tags'] = [tag.pk for tag in obj.tags.all()]
    starred_users = list(obj.starred_by.all())
    fields['star_count'] = len(starred_users)
    fields['is_starred'] = bool(user and user.is_authenticated and
                                any(starred.pk == user.pk for starred in starred_users))
    return {'pk': str(obj.pk), 'fields': fields}


def resource_queryset(request, resource):
    spec = RESOURCES[resource]
    queryset = spec['model'].objects.prefetch_related('starred_by').order_by(*spec['order'])
    query = request.GET.get('q', '').strip()
    if query:
        predicate = Q()
        for field in spec['search']:
            predicate |= Q(**{field + '__icontains': query})
        queryset = queryset.filter(predicate)
    if resource == 'projects':
        queryset = queryset.prefetch_related('tags')
    return queryset


def public_resource_list(request, resource):
    return JsonResponse([serialize_resource(resource, obj, request.user)
                         for obj in resource_queryset(request, resource)], safe=False)


def resource_error():
    return JsonResponse({'message': 'Resource atau data tidak ditemukan.'}, status=404)


def resource_object(resource, pk):
    try:
        return RESOURCES[resource]['model'].objects.get(pk=pk)
    except (RESOURCES[resource]['model'].DoesNotExist, ValidationError, ValueError):
        return None


@require_GET
def manage_resource_list(request, resource):
    denied = require_access(request, 'dashboard', json_response=True)
    if denied:
        return denied
    if resource not in RESOURCES:
        return resource_error()
    return public_resource_list(request, resource)


@require_GET
def manage_resource_detail(request, resource, pk):
    denied = require_access(request, 'edit', json_response=True)
    if denied:
        return denied
    if resource not in RESOURCES:
        return resource_error()
    obj = resource_object(resource, pk)
    if obj is None:
        return resource_error()
    return JsonResponse({
        **serialize_resource(resource, obj, request.user),
        'form_html': render_to_string('components/resource_form_fields.html',
                                     {'form': resource_form(resource, instance=obj),
                                      'can_create_tags': request.user.is_superuser}),
    })


def save_resource(request, resource, *, pk=None):
    denied = require_access(request, 'edit' if pk is not None else 'add', json_response=True)
    if denied:
        return denied
    if resource not in RESOURCES:
        return resource_error()
    obj = resource_object(resource, pk) if pk is not None else None
    if pk is not None and obj is None:
        return resource_error()
    form = resource_form(resource, request.POST, instance=obj)
    if not form.is_valid():
        return JsonResponse({'errors': form.errors.get_json_data()}, status=400)
    obj = form.save()
    return JsonResponse({'message': 'Data berhasil diperbarui.' if pk is not None
                                  else 'Data berhasil ditambahkan.',
                         'item': serialize_resource(resource, obj, request.user)},
                        status=200 if pk is not None else 201)


@require_POST
def manage_resource_create(request, resource):
    return save_resource(request, resource)


@require_POST
def toggle_star_resource(request, resource, pk):
    denied = require_access(request, 'star', json_response=True)
    if denied:
        return denied
    if resource not in RESOURCES:
        return resource_error()
    # Serialize concurrent toggles for the same record.
    with transaction.atomic():
        try:
            obj = RESOURCES[resource]['model'].objects.select_for_update().get(pk=pk)
        except (RESOURCES[resource]['model'].DoesNotExist, ValidationError, ValueError):
            return resource_error()
        if obj.starred_by.filter(pk=request.user.pk).exists():
            obj.starred_by.remove(request.user)
        else:
            obj.starred_by.add(request.user)
        return JsonResponse({'item': serialize_resource(resource, obj, request.user)})


@require_POST
def manage_resource_edit(request, resource, pk):
    return save_resource(request, resource, pk=pk)


@require_POST
def manage_resource_delete(request, resource, pk):
    denied = require_access(request, 'delete', json_response=True)
    if denied:
        return denied
    if resource not in RESOURCES:
        return resource_error()
    obj = resource_object(resource, pk)
    if obj is None:
        return resource_error()
    obj.delete()
    return JsonResponse({'message': 'Data berhasil dihapus.', 'pk': str(pk)})
