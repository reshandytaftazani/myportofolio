import re

with open('main/urls.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_pattern = r'from main\.views import \('
import_replacement = 'from main.views import (\\n    toggle_star_project, toggle_star_experience, toggle_star_skill, toggle_star_education, toggle_star_tech_stack,'

content = re.sub(import_pattern, import_replacement, content)

urlpatterns_pattern = r'(urlpatterns = \[)'
urlpatterns_replacement = r'\1\n    path("projects/<uuid:project_id>/star/", toggle_star_project, name="toggle_star_project"),\n    path("experience/<uuid:id>/star/", toggle_star_experience, name="toggle_star_experience"),\n    path("skills/<uuid:id>/star/", toggle_star_skill, name="toggle_star_skill"),\n    path("education/<int:id>/star/", toggle_star_education, name="toggle_star_education"),\n    path("techstack/<int:id>/star/", toggle_star_tech_stack, name="toggle_star_tech_stack"),'
content = re.sub(urlpatterns_pattern, urlpatterns_replacement, content)

with open('main/urls.py', 'w', encoding='utf-8') as f:
    f.write(content)
