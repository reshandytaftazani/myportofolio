"""Server fallback contracts; desktop enhancement must not own portfolio data."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from main.models import Education, Experience, Project, Skill, TechStack


class DesktopFallbackTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(title='Portfolio Web', category='Web', description='A <script>danger</script>')
        Project.objects.create(title='Portfolio Mobile', category='Mobile', description='Mobile project')
        Experience.objects.create(title='Researcher', description='**Safe** <script>unsafe()</script>')
        Skill.objects.create(title='Algorithms', level='Advanced', description='**Readable**', code_snippet='<script>alert(1)</script>')
        Education.objects.create(school_name='University', period='2025–Present', detail='CS', start_year=2025)
        TechStack.objects.create(name='Python', filename='<img src=x>.py', code_snippet='<script>code()</script>', icon_url='https://example.com/icon.svg')
        cls.editor = User.objects.create_user(username='editor')
        cls.editor.groups.add(Group.objects.create(name='Editor'))
        cls.owner = User.objects.create_user(username='owner', is_superuser=True)

    def test_html_projects_matches_public_api_filter(self):
        query = {'title': 'portfolio', 'category': 'Web'}
        response = self.client.get('/projects/', query)
        self.assertContains(response, self.project.title)
        self.assertNotContains(response, 'Portfolio Mobile')
        self.assertContains(response, 'A &lt;script&gt;danger&lt;/script&gt;')
        self.assertEqual([str(project.pk) for project in response.context['projects']],
                         [item['pk'] for item in self.client.get('/api/projects/', query).json()])
        self.assertContains(response, 'name="category" value="Web"')
        self.assertContains(response, 'Login untuk star')

    def test_resources_render_shells_and_json_preserves_safe_text_and_code(self):
        home = self.client.get('/')
        self.assertNotContains(home, 'University')
        self.assertNotContains(home, '&lt;img src=x&gt;.py')
        self.assertEqual(self.client.get('/api/education/').json()[0]['fields']['school_name'], 'University')
        self.assertEqual(self.client.get('/api/techstack/').json()[0]['fields']['filename'], '<img src=x>.py')
        skills = self.client.get('/skills/')
        self.assertNotContains(skills, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(skills, '<script>alert(1)</script>')
        self.assertEqual(self.client.get('/api/skills/').json()[0]['fields']['code_snippet'], '<script>alert(1)</script>')
        experience = self.client.get('/experience/')
        self.assertNotContains(experience, '<strong>Safe</strong>')
        self.assertNotContains(experience, 'unsafe()')
        html = self.client.get('/api/experience/').json()[0]['fields']['description_html']
        self.assertIn('<strong>Safe</strong>', html)
        self.assertNotIn('unsafe()', html)

    def test_fallback_management_obeys_roles_and_star_is_post(self):
        for user, can_add in [(self.editor, False), (self.owner, True)]:
            self.client.force_login(user)
            response = self.client.get('/projects/')
            self.assertContains(response, reverse('main:edit_project', args=[self.project.pk]))
            if can_add:
                self.assertContains(response, 'class="server-create"')
            else:
                self.assertNotContains(response, 'class="server-create"')
                self.assertNotContains(response, 'data-can-delete="true"')
            self.assertContains(response, 'class="star-form"')
            self.assertContains(response, 'csrfmiddlewaretoken')

    def test_empty_and_system_pages_are_independent_of_desktop_boot(self):
        response = self.client.get('/projects/', {'title': 'missing'})
        self.assertContains(response, 'id="empty" class="empty-state"')
        self.assertContains(response, 'data-window-id="projects"')
        login = self.client.get('/login/')
        self.assertContains(login, 'system-page')
        self.assertNotContains(login, 'js/desktop/boot.js')

    def test_invalid_document_contact_submission_reopens_contact(self):
        response = self.client.post('/', {'name': '<b></b>', 'email': 'invalid', 'message': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-initial-window="contact"')

    def test_filtered_empty_projects_offer_no_javascript_reset(self):
        response = self.client.get('/projects/', {'title': 'missing', 'category': 'Web'})
        self.assertContains(response, 'Tidak ada proyek yang cocok')
        self.assertContains(response, 'href="/projects/" data-projects-reset>Reset pencarian')
        self.assertContains(self.client.get('/projects/'), self.project.title)
