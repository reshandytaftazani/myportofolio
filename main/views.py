from django.shortcuts import render

from main.models import Experience, Skill, Education


def show_main(request):
    educations = Education.objects.all()

    context = {
        "name": "Reshandy",
        "npm": "2506547651",
        "study_program": "S1 Ilmu Komputer",
        "bio": (
            "CS student at Universitas Indonesia."
        ),
        'education_list': educations,
    }
    return render(request, "index.html", context)


def show_experience(request):
    context = {
        "name": "Reshandy",
        "experience_list": Experience.objects.all(),
    }
    return render(request, "experience.html", context)

def show_skills(request):
    context = {
        "name": "Reshandy",
        "skills": Skill.objects.all(),
    }
    return render(request, "skills.html", context)