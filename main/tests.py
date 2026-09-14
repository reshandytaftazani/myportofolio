from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from main.models import Experience, Skill


class MainTest(TestCase):
    def setUp(self):
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

    # Test experience
    def test_main_url_is_accessible(self):
        response = self.client.get(reverse("main:show_main"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
        self.assertNotContains(response, self.experience.title)
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
        self.assertContains(response, self.experience.title)
        self.assertContains(response, self.experience.description)
        self.assertContains(response, "Part-Time")
        self.assertContains(response, "Sedang berlangsung")
        self.assertContains(response, f'href="{reverse("main:show_main")}"')

    def test_empty_experience_page(self):
        Experience.objects.all().delete()
        response = self.client.get(reverse("main:show_experience"))

        self.assertContains(response, "Belum ada pengalaman yang ditambahkan.")

    def test_completed_experience(self):
        self.experience.ended_at = timezone.now()
        self.experience.save()
        response = self.client.get(reverse("main:show_experience"))

        self.assertFalse(self.experience.is_ongoing)
        self.assertContains(response, "Selesai")
        self.assertNotContains(response, "Sedang berlangsung")

    #  Test skills
    def test_skills_url_and_template(self):
        """Memastikan routing URL dan template yang digunakan sudah benar"""
        response = self.client.get(reverse('main:show_skills'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'skills.html')

    def test_skills_context_data(self):
        """Memastikan data skills dari database berhasil dikirim ke template"""
        response = self.client.get(reverse('main:show_skills'))
        self.assertTrue('skills' in response.context)
        self.assertEqual(len(response.context['skills']), 3)

    def test_tab_ui_rendering(self):
        """Memastikan elemen struktur Tab UI berhasil dirender"""
        response = self.client.get(reverse('main:show_skills'))
        content = response.content.decode('utf-8')
        
        self.assertIn('skills-tabs-container', content)
        self.assertIn('tab-btn', content)
        self.assertIn('tab-panel', content)

    def test_ide_window_logic(self):
        """Menguji logika if-else untuk menampilkan judul file dan tema editor yang tepat"""
        response = self.client.get(reverse('main:show_skills'))
        content = response.content.decode('utf-8')

        self.assertIn('📄 main.tex — Overleaf', content)
        self.assertIn('overleaf-mode', content)
        self.assertIn('⚙️ main.cpp — VS Code', content)
        self.assertIn('🐍 main.py — VS Code', content)

    def test_external_scripts_loaded(self):
        """Memastikan library MathJax dan Highlight.js sudah dipanggil"""
        response = self.client.get(reverse('main:show_skills'))
        content = response.content.decode('utf-8')
        
        self.assertIn('mathjax@3', content)
        self.assertIn('highlight.min.js', content)
        self.assertIn('hljs.highlightAll()', content)