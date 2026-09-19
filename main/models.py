import uuid
from django.db import models

class Experience(models.Model):
    EXPERIENCE_CHOICES = [
        ('internship', 'Internship'),
        ('research', 'Research'),
        ('volunteer', 'Volunteer'),
        ('part-time', 'Part-Time'),
        ('full-time', 'Full-Time'),
        ('freelance', 'Freelance'),
        ('organization', 'Organization'),
        ('competition', 'Competition'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='full-time')
    thumbnail = models.URLField(blank=True, null=True)
    started_at = models.DateField(null=True, blank=True)
    ended_at = models.DateField(blank=True, null=True)
    def __str__(self):
        return self.title
    
    @property
    def is_ongoing(self):
        return self.ended_at is None

class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    level = models.CharField(max_length=50) 
    code_snippet = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.title

class Education(models.Model):
    school_name = models.CharField(max_length=255)
    period = models.CharField(max_length=50) 
    detail = models.CharField(max_length=255)
    start_year = models.IntegerField()

    class Meta:
        ordering = ['-start_year']

    def __str__(self):
        return self.school_name

class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=20, default="#3b82f6")

    def __str__(self):
        return self.name

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, default='Other')
    tags = models.ManyToManyField(Tag, blank=True)
    project_url = models.URLField(blank=True)
    project_image_url = models.URLField(blank=True, max_length=500)

    def __str__(self):
        return self.title

class TechStack(models.Model):
    name = models.CharField(max_length=50, help_text="Nama bahasa (contoh: Python)")
    icon_url = models.URLField(help_text="URL ikon devicon (SVG/PNG)")
    filename = models.CharField(max_length=50, help_text="Nama file untuk Mac UI (contoh: script.py)")
    code_snippet = models.TextField(help_text="Contoh kode program")
    order = models.IntegerField(default=0, help_text="Urutan tampilan di halaman")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"