from django.contrib import admin
from .models import Experience, Skill, Education, Project, TechStack

@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'category', 'started_at', 'ended_at')
    search_fields = ('title', 'company')
    list_filter = ('category',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('title', 'level')
    search_fields = ('title',)
    list_filter = ('level',)

@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'period', 'start_year')
    search_fields = ('school_name',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'tech_stack')
    search_fields = ('title', 'tech_stack')
    list_filter = ('category',)

@admin.register(TechStack)
class TechStackAdmin(admin.ModelAdmin):
    list_display = ('name', 'filename', 'order')
    list_editable = ('order',)
