"""Regression coverage for role enforcement across HTML and JSON endpoints."""

import json
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser, Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase

from main import views
from main.access import require_access
from main.models import Project


class AccessRegressionTests(TestCase):
    headers = (
        {},
        {"HTTP_ACCEPT": "application/json"},
        {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
        {
            "HTTP_ACCEPT": "application/json",
            "HTTP_X_REQUESTED_WITH": "XMLHttpRequest",
        },
    )

    @classmethod
    def setUpTestData(cls):
        cls.regular = User.objects.create_user(username="access-regular")
        cls.editor = User.objects.create_user(username="access-editor")
        cls.editor.groups.add(Group.objects.create(name="Editor"))
        cls.owner = User.objects.create_user(username="access-owner", is_superuser=True)
        cls.project = Project.objects.create(
            title="Original", description="Description", category="Web"
        )

    def request(self, user, method="post", data=None, **headers):
        request = getattr(RequestFactory(), method)("/projects/", data or {}, **headers)
        request.user = user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_projects_supplies_csrf_for_users_without_the_creation_modal(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.regular)
        response = client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="project-form"')
        self.assertIn("csrftoken", response.cookies)

        with patch("main.views.require_access", wraps=require_access) as access_check:
            response = client.post(
                "/projects/add/",
                {"title": "Forbidden", "description": "Text", "category": "Web"},
                HTTP_ACCEPT="application/json",
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            )
        self.assertEqual(response.status_code, 403)
        access_check.assert_called_once()
        self.assertEqual(access_check.call_args.args[1], "add")
        self.assertEqual(Project.objects.count(), 1)

    def test_html_denials_do_not_depend_on_request_headers(self):
        endpoints = (
            (views.create_experience, (), "add"),
            (views.create_skill, (), "add"),
            (views.create_education, (), "add"),
            (views.create_project, (), "add"),
            (views.create_tech_stack, (), "add"),
            (views.edit_experience, (self.project.pk,), "edit"),
            (views.edit_skill, (self.project.pk,), "edit"),
            (views.edit_education, (1,), "edit"),
            (views.edit_project, (self.project.pk,), "edit"),
            (views.edit_tech_stack, (1,), "edit"),
            (views.delete_experience, (self.project.pk,), "delete"),
            (views.delete_skill, (self.project.pk,), "delete"),
            (views.delete_education, (1,), "delete"),
            (views.delete_project, (self.project.pk,), "delete"),
            (views.delete_tech_stack, (1,), "delete"),
            (views.show_dashboard, (), "dashboard"),
        )
        payload = {"title": "Changed", "description": "Text", "category": "Web"}
        for user, denied_actions in (
            (self.regular, {"add", "edit", "delete", "dashboard"}),
            (self.editor, {"add", "delete"}),
        ):
            for view, args, action in endpoints:
                if action not in denied_actions:
                    continue
                for headers in self.headers:
                    with self.subTest(user=user.username, view=view.__name__, headers=headers):
                        with self.assertRaises(PermissionDenied):
                            view(self.request(user, data=payload, **headers), *args)

        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Original")
        self.assertEqual(Project.objects.count(), 1)

    def test_authorized_html_operations_work_with_json_headers(self):
        headers = self.headers[-1]
        response = views.create_project(self.request(
            self.owner,
            data={"title": "New", "description": "Text", "category": "Web"},
            **headers,
        ))
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(title="New")

        response = views.edit_project(self.request(
            self.editor,
            data={"title": "Edited", "description": "Text", "category": "Web"},
            **headers,
        ), project.pk)
        self.assertEqual(response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.title, "Edited")

        response = views.delete_project(self.request(self.owner, **headers), project.pk)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

    def test_json_creation_denial_returns_403_without_saving(self):
        for user in (AnonymousUser(), self.regular, self.editor):
            for headers in self.headers:
                with self.subTest(user=str(user), headers=headers):
                    response = views.create_project_ajax(self.request(
                        user,
                        data={"title": "Forbidden", "description": "Text", "category": "Web"},
                        **headers,
                    ))
                    self.assertEqual(response.status_code, 403)
                    self.assertIn("message", json.loads(response.content))
        self.assertEqual(Project.objects.count(), 1)

    def test_public_resources_are_readable_without_login(self):
        for view in (
            views.get_experience_json,
            views.get_skills_json,
            views.get_education_json,
            views.get_tech_stack_json,
        ):
            with self.subTest(view=view.__name__):
                response = view(self.request(AnonymousUser(), method="get"))
                self.assertEqual(response.status_code, 200)
                self.assertIsInstance(json.loads(response.content), list)
