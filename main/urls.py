from django.urls import path
from main.views import (
    show_main, 
    show_experience, 
    show_skills, 
    create_experience, 
    edit_experience,
    create_skill, 
    create_education,
    show_projects,
    create_project,
    get_projects_json,
    delete_project
)

app_name = 'main'

urlpatterns = [
    path('', show_main, name='show_main'),
    path('experience/', show_experience, name='show_experience'),
    path('skills/', show_skills, name='show_skills'),
    path('experience/add/', create_experience, name='create_experience'),
    path('experience/edit/<uuid:id>/', edit_experience, name='edit_experience'),
    path('skills/add/', create_skill, name='create_skill'),
    path('education/add/', create_education, name='create_education'),
    path('projects/', show_projects, name='show_projects'),
    path('projects/add/', create_project, name='create_project'),
    path('api/projects/', get_projects_json, name='get_projects_json'),
    path("projects/<uuid:project_id>/delete/", delete_project, name="delete_project"),
]