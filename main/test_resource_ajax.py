"""Behavior and security coverage for the resource migration."""

from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from main.models import Experience, Skill, Education, TechStack, Project, Tag, ContactMessage
from main.resource_api import RESOURCES
from main.templatetags.markdown_extras import markdown_format


class ResourceAjaxTests(TestCase):
    payloads = {
        'experience': {'title': 'Developer', 'company': 'Acme', 'description': '**Build** software',
                       'category': 'internship', 'started_at': '2026-01-01'},
        'skills': {'title': 'C++', 'level': 'Advanced', 'description': '**Algorithms**',
                   'code_snippet': '#include <iostream>\nif (a < b) cout << "ok";'},
        'education': {'school_name': 'University', 'period': '2025 - Present',
                      'detail': 'Computer Science', 'start_year': 2025},
        'techstack': {'name': 'Python', 'filename': 'main.py', 'icon_url': 'https://example.com/icon.svg',
                      'code_snippet': '<script>alert(1)</script>\nprint(a < b)', 'order': 1},
        'projects': {'title': 'Portfolio', 'description': 'Website', 'category': 'Web'},
    }

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='resource-owner', is_superuser=True)
        cls.editor = User.objects.create_user(username='resource-editor')
        cls.editor.groups.add(Group.objects.create(name='Editor'))
        cls.regular = User.objects.create_user(username='resource-staff', is_staff=True)
        cls.objects = {name: spec['model'].objects.create(**cls.payloads[name])
                       for name, spec in RESOURCES.items()}
        cls.tag = Tag.objects.create(name='Django', slug='django')
        cls.objects['projects'].tags.add(cls.tag)

    def url(self, action, name, pk=None):
        return reverse('main:manage_resource_' + action, args=[name] + ([pk] if pk is not None else []))

    def test_public_lists_are_available_to_all_roles_and_send_explicit_fields(self):
        for user in (None, self.regular, self.editor, self.owner):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for name, spec in RESOURCES.items():
                with self.subTest(user=user, resource=name):
                    response = self.client.get(reverse('main:' + spec['public_view']))
                    self.assertEqual(response.status_code, 200)
                    item = response.json()[0]
                    self.assertEqual(item['pk'], str(self.objects[name].pk))
                    self.assertNotIn('model', item)
                    self.assertNotIn('form_html', item)
                    self.assertNotIn('is_read', item['fields'])
                    self.assertNotIn('email', item['fields'])

    def test_public_search_and_ordering(self):
        Experience.objects.create(title='Older', company='Other', description='Old', started_at='2025-01-01')
        Skill.objects.create(title='Beginner', level='Entry', description='Learning')
        Education.objects.create(school_name='School', period='2020', detail='Study', start_year=2020)
        TechStack.objects.create(name='Other', filename='other.py', icon_url='https://example.com/i.png',
                                 code_snippet='pass', order=0)
        cases = [('experience', 'aCMe', 'company'), ('skills', 'aDVanced', 'level'),
                 ('education', 'uNiv', 'school_name'), ('techstack', 'pYth', 'name')]
        for name, query, field in cases:
            with self.subTest(resource=name):
                url = reverse('main:' + RESOURCES[name]['public_view'])
                data = self.client.get(url, {'q': query}).json()
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]['fields'][field], self.payloads[name][field])
                self.assertEqual(self.client.get(url, {'q': 'no-match'}).json(), [])
        for name in ('experience', 'education'):
            data = self.client.get(reverse('main:' + RESOURCES[name]['public_view'])).json()
            self.assertEqual(data[0]['pk'], str(self.objects[name].pk))
        tools = self.client.get(reverse('main:get_tech_stack_json')).json()
        self.assertEqual([item['fields']['order'] for item in tools], [0, 1])

    def test_resource_stars_permissions_csrf_and_user_specific_json(self):
        client = Client(enforce_csrf_checks=True)
        for name in ('experience', 'skills', 'education', 'techstack'):
            obj = self.objects[name]
            url = reverse('main:toggle_star_resource', args=[name, obj.pk])
            client.logout()
            client.get('/')
            token = client.cookies['csrftoken'].value
            self.assertEqual(client.post(url, HTTP_X_CSRFTOKEN=token).status_code, 403)
            self.assertEqual(obj.starred_by.count(), 0)
            for user in (self.regular, self.editor, self.owner):
                client.force_login(user)
                client.get('/')
                token = client.cookies['csrftoken'].value
                self.assertEqual(client.get(url).status_code, 405)
                self.assertEqual(client.post(url).status_code, 403)
                response = client.post(url, HTTP_X_CSRFTOKEN=token)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['item']['fields']['is_starred'])
                fields = client.get(reverse('main:' + RESOURCES[name]['public_view'])).json()[0]['fields']
                self.assertEqual(fields['star_count'], 1)
                self.assertTrue(fields['is_starred'])
                anonymous = self.client.get(reverse('main:' + RESOURCES[name]['public_view'])).json()[0]['fields']
                self.assertEqual(anonymous['star_count'], 1)
                self.assertFalse(anonymous['is_starred'])
                self.assertFalse(client.post(url, HTTP_X_CSRFTOKEN=token).json()['item']['fields']['is_starred'])
                self.assertEqual(obj.starred_by.count(), 0)
            self.assertEqual(client.post(reverse('main:toggle_star_resource', args=[name, 'invalid']),
                                         HTTP_X_CSRFTOKEN=token).status_code, 404)

    def test_ajax_shell_and_field_sanitization(self):
        response = self.client.get('/')
        for kind in ('experience', 'skills', 'education', 'techstack'):
            self.assertNotIn(kind + '_items', response.context)
        self.assertNotContains(response, 'data-list data-server-rendered')
        self.client.force_login(self.owner)
        attack = '<img src="x" onerror="alert(\'XSS!\')">'
        for name, spec in RESOURCES.items():
            if name == 'projects':
                continue
            for field in (*spec['form'].plain_text_fields, *spec['form'].markdown_fields):
                with self.subTest(resource=name, field=field):
                    payload = {**self.payloads[name], field: 'Safe ' + attack}
                    response = self.client.post(self.url('create', name), payload)
                    self.assertEqual(response.status_code, 201, response.content)
                    saved = spec['model'].objects.get(pk=response.json()['item']['pk'])
                    self.assertEqual(getattr(saved, field), 'Safe')

    def test_management_role_matrix_and_denials_never_mutate_data(self):
        for user in (None, self.regular, self.editor):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for name, spec in RESOURCES.items():
                pk = self.objects[name].pk
                denied = ('create', 'delete') if user == self.editor else ('create', 'edit', 'delete')
                for action in denied:
                    with self.subTest(user=user, resource=name, action=action):
                        response = self.client.post(self.url(action, name, None if action == 'create' else pk),
                                                    self.payloads[name])
                        self.assertEqual(response.status_code, 403)
                        self.assertIn('message', response.json())
                        self.assertEqual(spec['model'].objects.count(), 1)
                if user != self.editor:
                    for action in ('list', 'detail'):
                        response = self.client.get(self.url(action, name, pk if action == 'detail' else None))
                        self.assertEqual(response.status_code, 403)
                        self.assertIn('message', response.json())
        for name, obj in self.objects.items():
            obj.refresh_from_db()
            first_field = RESOURCES[name]['form'].Meta.fields[0]
            self.assertEqual(getattr(obj, first_field), self.payloads[name][first_field])

    def test_owner_creates_editor_edits_owner_deletes_each_resource(self):
        for name, spec in RESOURCES.items():
            with self.subTest(resource=name):
                self.client.force_login(self.owner)
                payload = dict(self.payloads[name])
                if name == 'projects':
                    payload['tags'] = [self.tag.pk]
                response = self.client.post(self.url('create', name), payload)
                self.assertEqual(response.status_code, 201, response.content)
                pk = response.json()['item']['pk']
                self.client.force_login(self.editor)
                detail = self.client.get(self.url('detail', name, pk))
                self.assertEqual(detail.status_code, 200)
                self.assertIn('form_html', detail.json())
                self.assertEqual(self.client.get(self.url('list', name)).status_code, 200)
                title_field = spec['form'].Meta.fields[0]
                payload[title_field] = 'Edited'
                response = self.client.post(self.url('edit', name, pk), payload)
                self.assertEqual(response.status_code, 200, response.content)
                obj = spec['model'].objects.get(pk=pk)
                self.assertEqual(getattr(obj, title_field), 'Edited')
                if name == 'projects':
                    self.assertEqual(list(obj.tags.all()), [self.tag])
                self.client.force_login(self.owner)
                self.assertEqual(self.client.post(self.url('delete', name, pk)).status_code, 200)
                self.assertFalse(spec['model'].objects.filter(pk=pk).exists())

    def test_invalid_forms_return_field_errors_without_saving(self):
        self.client.force_login(self.owner)
        for name, spec in RESOURCES.items():
            payload = dict(self.payloads[name])
            field = spec['form'].Meta.fields[0]
            payload[field] = '<img src=x onerror=alert(1)>'
            response = self.client.post(self.url('create', name), payload)
            with self.subTest(resource=name):
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()['errors'])
                self.assertEqual(spec['model'].objects.count(), 1)
                response = self.client.post(self.url('edit', name, self.objects[name].pk), payload)
                self.assertEqual(response.status_code, 400)
                self.objects[name].refresh_from_db()
                self.assertEqual(getattr(self.objects[name], field), self.payloads[name][field])
        for name in ('experience', 'skills'):
            payload = {**self.payloads[name], 'description': '<script>alert(1)</script>'}
            response = self.client.post(self.url('create', name), payload)
            self.assertEqual(response.status_code, 400)
            self.assertIn('description', response.json()['errors'])

    def test_http_only_urls_and_code_preservation(self):
        self.client.force_login(self.owner)
        for name, field in [('experience', 'thumbnail'), ('techstack', 'icon_url'), ('projects', 'project_url')]:
            for url in ('javascript:alert(1)', 'ftp://example.com/file'):
                response = self.client.post(self.url('create', name), {**self.payloads[name], field: url})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()['errors'])
        for name in ('skills', 'techstack'):
            response = self.client.post(self.url('create', name), self.payloads[name])
            self.assertEqual(response.json()['item']['fields']['code_snippet'], self.payloads[name]['code_snippet'])

    def test_markdown_is_sanitized_and_retains_supported_formatting(self):
        source = '**bold**\n\n```cpp\n#include <iostream>\n```\n\n<script>alert(1)</script>'
        source += '<img src=x onerror=alert(1)>[bad](javascript:alert(1)) [good](https://example.com)'
        html = markdown_format(source)
        self.assertIn('<strong>bold</strong>', html)
        self.assertIn('&lt;iostream&gt;', html)
        self.assertIn('href="https://example.com"', html)
        for forbidden in ('<script', '<img', 'onerror', 'javascript:'):
            self.assertNotIn(forbidden, html)
        self.objects['experience'].description = source
        self.objects['experience'].save()
        data = self.client.get(reverse('main:get_experience_json')).json()[0]['fields']
        self.assertEqual(data['description_html'], html)

    def test_csrf_is_required_on_every_write_endpoint(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.get(reverse('main:dashboard'))
        self.assertEqual(response.status_code, 200)
        token = client.cookies['csrftoken'].value
        for name in RESOURCES:
            for action in ('create', 'edit', 'delete'):
                pk = None if action == 'create' else self.objects[name].pk
                self.assertEqual(client.post(self.url(action, name, pk), self.payloads[name]).status_code, 403)
            response = client.post(self.url('create', name), self.payloads[name], HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 201, response.content)

    def test_unknown_resources_missing_records_and_methods(self):
        self.client.force_login(self.owner)
        for name in RESOURCES:
            self.assertEqual(self.client.get(self.url('detail', name, 'invalid-id')).status_code, 404)
            self.assertEqual(self.client.post(self.url('edit', name, 'invalid-id'), {}).status_code, 404)
            for action in ('create', 'edit', 'delete'):
                self.assertEqual(self.client.get(self.url(action, name, None if action == 'create'
                                                          else self.objects[name].pk)).status_code, 405)
        self.assertEqual(self.client.get(self.url('list', 'contact')).status_code, 404)
        self.assertEqual(self.client.post(self.url('create', 'unknown')).status_code, 404)
        for name in ('experience', 'skills', 'education', 'techstack'):
            self.assertEqual(self.client.post(reverse('main:' + RESOURCES[name]['public_view'])).status_code, 405)

    def test_public_controls_follow_roles(self):
        for user in (None, self.regular, self.editor, self.owner):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for page in ('show_experience', 'show_skills', 'show_main'):
                response = self.client.get(reverse('main:' + page))
                self.assertContains(response, 'data-search-input', count=4)
                self.assertEqual(b'data-open-create' in response.content, user == self.owner)
                self.assertEqual(b'class="resource-dialog"' in response.content, user in (self.owner, self.editor))
            self.assertContains(self.client.get(reverse('main:show_projects')), 'id="search-input"')
            if user in (self.owner, self.editor):
                self.assertContains(self.client.get(reverse('main:dashboard')), 'data-search-input', count=5)

    def test_contact_keeps_honeypot_validation_and_rate_limit(self):
        kwargs = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest', 'REMOTE_ADDR': '192.0.2.51'}
        with patch('main.views.send_mail') as send_mail:
            response = self.client.post('/', {'website': 'bot'}, **kwargs)
            self.assertEqual(response.json()['status'], 'success')
            self.assertEqual(ContactMessage.objects.count(), 0)
            send_mail.assert_not_called()
        response = self.client.post('/', {'name': 'A', 'email': 'bad', 'message': 'Hi'}, **kwargs)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])
        for _ in range(3):
            self.assertEqual(self.client.post('/', {'website': 'bot'}, **kwargs).status_code, 200)
        self.assertEqual(self.client.post('/', {'website': 'bot'}, **kwargs).status_code, 403)
