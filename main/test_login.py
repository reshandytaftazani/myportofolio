"""Regression coverage for login return destinations."""

from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class HiddenFieldsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden" and "name" in attrs:
            self.fields[attrs["name"]] = attrs.get("value", "")


class LoginRedirectTests(TestCase):
    credentials = {"username": "login-visitor", "password": "Login-regression-42!"}

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(**cls.credentials)

    def hidden_fields(self, response):
        parser = HiddenFieldsParser()
        parser.feed(response.content.decode())
        return parser.fields

    def test_login_form_preserves_projects_filters_through_post(self):
        client = Client(enforce_csrf_checks=True)
        destination = reverse("main:show_projects") + "?title=Compiler&category=Web"
        response = client.get(reverse("main:login"), {"next": destination})
        fields = self.hidden_fields(response)
        self.assertEqual(fields["next"], destination)

        response = client.post(reverse("main:login"), {**fields, **self.credentials})
        self.assertRedirects(response, destination, fetch_redirect_response=False)
        self.assertEqual(client.session["_auth_user_id"], str(self.user.pk))
        self.assertIn("last_login", response.cookies)

    def test_failed_login_keeps_return_destination_for_retry(self):
        destination = reverse("main:show_projects")
        response = self.client.post(reverse("main:login"), {
            **self.credentials, "password": "wrong-password", "next": destination,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        fields = self.hidden_fields(response)
        self.assertEqual(fields["next"], destination)

        response = self.client.post(reverse("main:login"), {**fields, **self.credentials})
        self.assertRedirects(response, destination, fetch_redirect_response=False)

    def test_login_without_destination_returns_home(self):
        response = self.client.post(reverse("main:login"), self.credentials)
        self.assertRedirects(response, reverse("main:show_main"), fetch_redirect_response=False)

    def test_direct_post_can_use_destination_from_query_string(self):
        response = self.client.post(
            reverse("main:login") + "?next=/projects/", self.credentials,
        )
        self.assertRedirects(response, "/projects/", fetch_redirect_response=False)

    def test_posted_destination_takes_priority_over_query_string(self):
        response = self.client.post(
            reverse("main:login") + "?next=/skills/",
            {**self.credentials, "next": "/projects/"},
        )
        self.assertRedirects(response, "/projects/", fetch_redirect_response=False)

    def test_unsafe_destinations_fall_back_to_home(self):
        for destination in (
            "https://example.invalid/projects/",
            "//example.invalid/projects/",
            "///example.invalid/projects/",
            "javascript:alert(1)",
            "http:///example.invalid/projects/",
            "\\\\example.invalid/projects/",
        ):
            with self.subTest(destination=destination):
                client = Client()
                page = client.get(reverse("main:login"), {"next": destination})
                self.assertEqual(self.hidden_fields(page)["next"], "")
                response = client.post(reverse("main:login"), {
                    **self.credentials, "next": destination,
                })
                self.assertRedirects(response, reverse("main:show_main"), fetch_redirect_response=False)

    def test_same_host_absolute_destination_is_allowed(self):
        destination = "http://testserver/projects/"
        response = self.client.post(reverse("main:login"), {
            **self.credentials, "next": destination,
        })
        self.assertRedirects(response, destination, fetch_redirect_response=False)

    def test_secure_login_rejects_http_destination(self):
        response = self.client.post(reverse("main:login"), {
            **self.credentials, "next": "http://testserver/projects/",
        }, secure=True)
        self.assertRedirects(response, reverse("main:show_main"), fetch_redirect_response=False)
