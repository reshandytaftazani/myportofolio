from django.contrib import admin
from .models import Experience, Skill, Education, Project, TechStack, Tag

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

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category')
    search_fields = ('title',)
    list_filter = ('category',)
    filter_horizontal = ('tags',)

@admin.register(TechStack)
class TechStackAdmin(admin.ModelAdmin):
    list_display = ('name', 'filename', 'order')
    list_editable = ('order',)
