from django.forms import ModelForm, TextInput, Textarea, URLInput, Select, DateTimeInput, NumberInput, DateInput
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.core.validators import RegexValidator
from urllib.parse import urlsplit

from main.models import Experience, Skill, Education, Project, TechStack, ContactMessage, Tag

class PortfolioForm(ModelForm):
    """Clean plain text while preserving Markdown and source code."""
    plain_text_fields = ()
    http_url_fields = ()
    markdown_fields = ()

    def clean_text_field(self, name):
        value = self.cleaned_data.get(name) or ''
        if name in self.markdown_fields:
            from main.templatetags.markdown_extras import markdown_format
            if value and not strip_tags(markdown_format(value)).strip():
                raise ValidationError('Deskripsi harus memuat teks yang dapat ditampilkan.')
        value = strip_tags(value).strip()
        if self.fields[name].required and not value:
            raise ValidationError('Field ini tidak boleh kosong setelah sanitasi HTML.')
        return value

    def clean(self):
        cleaned = super().clean()
        for name in self.plain_text_fields:
            if name not in cleaned:
                continue
            value = strip_tags(cleaned[name] or '').strip()
            if self.fields[name].required and not value:
                self.add_error(name, 'Field ini tidak boleh kosong setelah sanitasi HTML.')
            else:
                cleaned[name] = value
        for name in self.http_url_fields:
            value = cleaned.get(name)
            if value and urlsplit(value).scheme.lower() not in {'http', 'https'}:
                self.add_error(name, 'Gunakan URL dengan skema http atau https.')
        if self.markdown_fields:
            from main.templatetags.markdown_extras import markdown_format
            for name in self.markdown_fields:
                value = cleaned.get(name)
                if value and not strip_tags(markdown_format(value)).strip():
                    self.add_error(name, 'Deskripsi harus memuat teks yang dapat ditampilkan.')
        return cleaned


class ExperienceForm(PortfolioForm):
    plain_text_fields = ('title', 'company')
    http_url_fields = ('thumbnail',)
    markdown_fields = ('description',)

    def clean_title(self):
        return self.clean_text_field('title')

    def clean_company(self):
        return self.clean_text_field('company')

    def clean_description(self):
        return self.clean_text_field('description')
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

class SkillForm(PortfolioForm):
    plain_text_fields = ('title', 'level')
    markdown_fields = ('description',)

    def clean_title(self):
        return self.clean_text_field('title')

    def clean_level(self):
        return self.clean_text_field('level')

    def clean_description(self):
        return self.clean_text_field('description')
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

class EducationForm(PortfolioForm):
    plain_text_fields = ('school_name', 'period', 'detail')

    def clean_school_name(self):
        return self.clean_text_field('school_name')

    def clean_period(self):
        return self.clean_text_field('period')

    def clean_detail(self):
        return self.clean_text_field('detail')
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

class TagForm(PortfolioForm):
    plain_text_fields = ('name',)

    class Meta:
        model = Tag
        fields = ('name', 'color')

    def clean_color(self):
        color = self.cleaned_data['color'].strip()
        RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Gunakan warna hex, misalnya #3b82f6.')(color)
        return color.lower()


class ProjectForm(PortfolioForm):
    http_url_fields = ('project_url', 'project_image_url')
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "category",
            "tags",
            "project_url",
            "project_image_url",
            "is_featured",
        ]

        labels = {
            "title": "Nama Proyek",
            "description": "Deskripsi Proyek",
            "category": "Kategori",
            "tags": "Tags",
            "project_url": "URL Proyek",
            "project_image_url": "URL Gambar Proyek",
            "is_featured": "Tampilkan di Beranda (Featured)",
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

    def clean_title(self):
        title = strip_tags(self.cleaned_data["title"]).strip()
        if not title:
            raise ValidationError("Nama proyek tidak boleh hanya berisi tag HTML.")
        return title

    def clean_category(self):
        category = strip_tags(self.cleaned_data["category"]).strip()
        if not category:
            raise ValidationError("Kategori tidak boleh hanya berisi tag HTML.")
        return category

    def clean_description(self):
        description = strip_tags(self.cleaned_data["description"]).strip()
        if not description:
            raise ValidationError("Deskripsi tidak boleh hanya berisi tag HTML.")
        return description

class TechStackForm(PortfolioForm):
    plain_text_fields = ('name', 'filename')
    http_url_fields = ('icon_url',)

    def clean_name(self):
        return self.clean_text_field('name')

    def clean_filename(self):
        return self.clean_text_field('filename')
    class Meta:
        model = TechStack
        fields = [
            "name",
            "icon_url",
            "filename",
            "code_snippet",
            "order",
        ]
        labels = {
            "name": "Nama Bahasa",
            "icon_url": "URL Icon Devicon",
            "filename": "Nama File (UI Mac)",
            "code_snippet": "Code Snippet",
            "order": "Urutan Tampil",
        }
        widgets = {
            "name": TextInput(attrs={"placeholder": "Python", "maxlength": 50}),
            "icon_url": URLInput(attrs={"placeholder": "https://cdn.jsdelivr.net/..."}),
            "filename": TextInput(attrs={"placeholder": "main.py", "maxlength": 50}),
            "code_snippet": Textarea(attrs={"placeholder": "print('Hello')", "rows": 5}),
            "order": NumberInput(attrs={"placeholder": "1"}),
        }

class ContactMessageForm(PortfolioForm):
    plain_text_fields = ('name', 'message')
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        labels = {
            "name": "Nama Lengkap",
            "email": "Alamat Email",
            "message": "Pesan Anda",
        }
        widgets = {
            "name": TextInput(attrs={"placeholder": "Nama Anda", "autocomplete": "name", "class": "form-control"}),
            "email": TextInput(attrs={"placeholder": "anda@example.com", "type": "email", "autocomplete": "email", "class": "form-control"}),
            "message": Textarea(attrs={"placeholder": "Tuliskan pesan Anda di sini...", "rows": 4, "class": "form-control"}),
        }
