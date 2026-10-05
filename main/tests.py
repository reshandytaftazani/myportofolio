from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from main.models import Experience, Skill, Education, Project


class MainTest(TestCase):
    def setUp(self):
        self.client = Client()
        # test untuk experience
        self.experience = Experience.objects.create(
            title="Asisten Dosen PBP",
            description="Membantu mahasiswa memahami pengembangan web.",
            category="part-time",
        )

        # test untuk skill
        Skill.objects.create(
            title="Mathematic Olympiad",
            level="Advanced",
            description="Math problems.",
            code_snippet="\\begin{aligned} a = b \\end{aligned}"
        )
        Skill.objects.create(
            title="Problem Solving",
            level="Advanced",
            description="C++ coding.",
            code_snippet="#include <bits/stdc++.h>\nusing namespace std;"
        )
        Skill.objects.create(
            title="Software Dev",
            level="Intermediate",
            description="Python backend.",
            code_snippet="import django\nprint('Hello')"
        )

        # Setup data education
        self.edu_sma = Education.objects.create(
            school_name="SMA Taruna Nusantara",
            period="2022 - 2025",
            detail="GPA : 93.5",
            start_year=2022
        )
        self.edu_ui = Education.objects.create(
            school_name="Universitas Indonesia",
            period="2025 - Present",
            detail="Bachelor's Degree - Computer Science",
            start_year=2025
        )

    # Test experience
    def test_main_url_is_accessible(self):
        response = self.client.get(reverse("main:show_main"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
        # Portfolio lists are empty shells populated from their JSON endpoints.
        self.assertNotContains(response, self.experience.title)
        self.assertContains(response, 'data-window-id="experience"', count=1)
        self.assertContains(response, f'href="{reverse("main:show_experience")}"')

    def test_nonexistent_page_returns_404(self):
        response = self.client.get("/halaman-yang-tidak-ada/")

        self.assertEqual(response.status_code, 404)

    def test_experience_model(self):
        self.assertEqual(str(self.experience), "Asisten Dosen PBP")
        self.assertEqual(self.experience.category, "part-time")
        self.assertTrue(self.experience.is_ongoing)

    def test_experience_page(self):
        response = self.client.get(reverse("main:show_experience"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "experience.html")
        self.assertContains(response, 'data-list-url="/api/experience/"')
        data = self.client.get(reverse('main:get_experience_json')).json()[0]['fields']
        self.assertEqual(data['title'], self.experience.title)
        self.assertIn(self.experience.description, data['description_html'])
        self.assertEqual(data['category_display'], 'Part-Time')
        self.assertTrue(data['is_ongoing'])
        self.assertContains(response, f'href="{reverse("main:show_main")}"')

    def test_empty_experience_page(self):
        Experience.objects.all().delete()
        response = self.client.get(reverse("main:show_experience"))

        self.assertContains(response, 'data-empty')
        self.assertEqual(self.client.get(reverse('main:get_experience_json')).json(), [])

    def test_completed_experience(self):
        self.experience.ended_at = timezone.now()
        self.experience.save()
        response = self.client.get(reverse("main:show_experience"))

        self.assertFalse(self.experience.is_ongoing)
        data = self.client.get(reverse('main:get_experience_json')).json()[0]['fields']
        self.assertFalse(data['is_ongoing'])
        self.assertIsNotNone(data['ended_at'])

    #  Test skills
    def test_skills_url_and_template(self):
        """Memastikan routing URL dan template yang digunakan sudah benar"""
        response = self.client.get(reverse('main:show_skills'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'skills.html')

    def test_skills_context_data(self):
        """Skill data is loaded from the public JSON endpoint."""
        response = self.client.get(reverse('main:show_skills'))
        self.assertContains(response, 'data-list-url="/api/skills/"')
        self.assertEqual(len(self.client.get(reverse('main:get_skills_json')).json()), 3)

    def test_tab_ui_rendering(self):
        """Memastikan elemen struktur Tab UI berhasil dirender"""
        response = self.client.get(reverse('main:show_skills'))
        content = response.content.decode('utf-8')
        
        self.assertIn('skills-tabs-container', content)
        self.assertIn('data-list', content)
        self.assertIn('public-resources.js', content)

    def test_ide_window_logic(self):
        """Menguji logika if-else untuk menampilkan judul file dan tema editor yang tepat"""
        data = self.client.get(reverse('main:get_skills_json')).json()
        snippets = {item['fields']['title']: item['fields']['code_snippet'] for item in data}
        self.assertIn('\\begin', snippets['Mathematic Olympiad'])
        self.assertIn('#include <bits/stdc++.h>', snippets['Problem Solving'])
        self.assertIn("print('Hello')", snippets['Software Dev'])

    def test_external_scripts_loaded(self):
        """Memastikan library MathJax dan Highlight.js sudah dipanggil"""
        response = self.client.get(reverse('main:show_skills'))
        content = response.content.decode('utf-8')
        
        self.assertIn('mathjax@3', content)
        self.assertIn('highlight.min.js', content)
        self.assertIn("load: ['ui/safe']", content)

    # Test untuk education
    def test_education_model_and_ordering(self):
        """Memastikan pengurutan berjalan otomatis dari tahun terbaru (-start_year)"""
        self.assertEqual(str(self.edu_ui), "Universitas Indonesia")
        educations = Education.objects.all()
        self.assertEqual(educations[0], self.edu_ui)
        self.assertEqual(educations[1], self.edu_sma)

    def test_main_context_contains_education(self):
        """Education loads independently of the rest of the home page."""
        response = self.client.get(reverse("main:show_main"))
        self.assertContains(response, 'data-list-url="/api/education/"')
        self.assertEqual(len(self.client.get(reverse('main:get_education_json')).json()), 2)

    def test_education_rendering_on_main_page(self):
        """Memastikan data education dirender dengan benar di HTML"""
        response = self.client.get(reverse("main:show_main"))
        self.assertContains(response, 'data-public-resource')
        data = self.client.get(reverse('main:get_education_json')).json()
        self.assertEqual(data[0]['fields']['school_name'], 'Universitas Indonesia')
        self.assertEqual(data[0]['fields']['period'], '2025 - Present')
        self.assertEqual(data[1]['fields']['school_name'], 'SMA Taruna Nusantara')
        self.assertEqual(data[1]['fields']['detail'], 'GPA : 93.5')


class ProjectAjaxRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='project-owner', is_superuser=True)
        cls.reader = User.objects.create_user(username='project-reader')
        cls.project = Project.objects.create(title='Portfolio Web', description='Website', category='Web')
        Project.objects.create(title='Portfolio Mobile', description='App', category='Mobile')
        Project.objects.create(title='Other Web', description='Other', category='Web')
        cls.project.starred_by.add(cls.reader)

    def test_search_combines_title_category_and_role_specific_star_state(self):
        url = reverse('main:get_projects_json')
        query = {'title': '  pOrTfOlIo  ', 'category': 'Web'}
        for user in (None, self.reader, self.owner):
            self.client.logout()
            if user:
                self.client.force_login(user)
            with self.subTest(user=user):
                response = self.client.get(url, query)
                self.assertEqual(response.status_code, 200)
                item, = response.json()
                self.assertEqual(item['pk'], str(self.project.pk))
                self.assertEqual(item['fields']['star_count'], 1)
                self.assertEqual(item['fields']['is_starred'], user == self.reader)
        self.assertEqual(self.client.get(url, {'title': 'no-match', 'category': 'Web'}).json(), [])

    def test_required_project_fields_empty_after_sanitizing_never_save(self):
        self.client.force_login(self.owner)
        valid = {'title': 'Valid', 'description': 'Content', 'category': 'Web'}
        endpoints = (
            reverse('main:create_project_ajax'),
            reverse('main:manage_resource_create', args=['projects']),
            reverse('main:manage_resource_edit', args=['projects', self.project.pk]),
        )
        for url in endpoints:
            for field in valid:
                with self.subTest(url=url, field=field):
                    response = self.client.post(url, {**valid, field: '<b></b>'})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.json()['errors'])
                    self.assertEqual(Project.objects.count(), 3)
                    self.project.refresh_from_db()
                    self.assertEqual(self.project.title, 'Portfolio Web')
                    self.assertEqual(self.project.description, 'Website')
                    self.assertEqual(self.project.category, 'Web')
