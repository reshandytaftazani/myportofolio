from django.forms import ModelForm, TextInput, Textarea, URLInput, Select, DateTimeInput, NumberInput, DateInput

from main.models import Experience, Skill, Education, Project

class ExperienceForm(ModelForm):
    class Meta:
        model = Experience
        fields = [
            "title",
            "company",
            "description",
            "category",
            "thumbnail",
            "started_at",
            "ended_at",
        ]

        labels = {
            "title": "Nama Pengalaman",
            "company": "Nama Perusahaan/Organisasi",
            "description": "Deskripsi Pengalaman",
            "category": "Kategori",
            "thumbnail": "URL Thumbnail",
            "started_at": "Mulai Pada",
            "ended_at": "Selesai Pada",
        }

        widgets = {
            "title": TextInput(
                attrs={
                    "placeholder": "Software Engineer Intern",
                    "maxlength": 255,
                }
            ),
            "company": TextInput(
                attrs={
                    "placeholder": "Google",
                    "maxlength": 255,
                }
            ),
            "description": Textarea(
                attrs={
                    "placeholder": "Ceritakan Pengalamanmu",
                    "rows": 3,
                }
            ),
            "category": Select(),
            "thumbnail": URLInput(
                attrs={
                    "placeholder": "https://drive.google.com/thumbnail?id=...&sz=w1000",
                }
            ),
            "started_at": DateInput(
                attrs={
                    "type": "date",
                }
            ),
            "ended_at": DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

class SkillForm(ModelForm):
    class Meta:
        model = Skill
        fields = [
            "title",
            "description",
            "level",
            "code_snippet",
        ]

        labels = {
            "title": "Nama Keahlian",
            "description": "Deskripsi Keahlian",
            "level": "Tingkat Keahlian",
            "code_snippet": "Cuplikan Kode",
        }

        widgets = {
            "title": TextInput(
                attrs={
                    "placeholder": "Python",
                    "maxlength": 255,
                }
            ),
            "description": Textarea(
                attrs={
                    "placeholder": "Deskripsi singkat tentang keahlianmu",
                    "rows": 3,
                }
            ),
            "level": TextInput(
                attrs={
                    "placeholder": "Beginner, Intermediate, Expert",
                    "maxlength": 50,
                }
            ),
            "code_snippet": Textarea(
                attrs={
                    "placeholder": "print('Hello World')",
                    "rows": 3,
                }
            ),
        }

class EducationForm(ModelForm):
    class Meta:
        model = Education
        fields = [
            "school_name",
            "period",
            "detail",
            "start_year",
        ]

        labels = {
            "school_name": "Nama Institusi Pendidikan",
            "period": "Periode Pendidikan",
            "detail": "Detail (Jurusan/Fakultas)",
            "start_year": "Tahun Mulai",
        }

        widgets = {
            "school_name": TextInput(
                attrs={
                    "placeholder": "Universitas Indonesia",
                    "maxlength": 255,
                }
            ),
            "period": TextInput(
                attrs={
                    "placeholder": "2021 - Sekarang",
                    "maxlength": 50,
                }
            ),
            "detail": TextInput(
                attrs={
                    "placeholder": "Fakultas Ilmu Komputer",
                    "maxlength": 255,
                }
            ),
            "start_year": NumberInput(
                attrs={
                    "placeholder": "2021",
                }
            ),
        }

class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "category",
            "tech_stack",
            "project_url",
            "project_image_url",
        ]

        labels = {
            "title": "Nama Proyek",
            "description": "Deskripsi Proyek",
            "category": "Kategori",
            "tech_stack": "Teknologi yang Digunakan",
            "project_url": "URL Proyek",
            "project_image_url": "URL Gambar Proyek",
        }

        widgets = {
            "title": TextInput(
                attrs={
                    "placeholder": "Portfolio Website",
                    "maxlength": 255,
                }
            ),
            "description": Textarea(
                attrs={
                    "placeholder": "Ceritakan Proyekmu",
                    "rows": 3,
                }
            ),
            "category": TextInput(
                attrs={
                    "placeholder": "Contoh: Web Dev, Data Science, dll.",
                    "maxlength": 50,
                }
            ),
            "tech_stack": TextInput(
                attrs={
                    "placeholder": "Django, Python, HTML, CSS",
                }
            ),
            "project_url": URLInput(
                attrs={
                    "placeholder": "https://github.com/kakBurhan/burhanquestv4",
                }
            ),
            "project_image_url": URLInput(
                attrs={
                    "placeholder": "https://drive.google.com/thumbnail?id=...&sz=w1000",
                }
            ),
        }
