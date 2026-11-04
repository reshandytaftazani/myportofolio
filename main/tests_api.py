import uuid

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from main.models import Experience, Project


class ProjectAPITest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="owner", password="test-password", email="owner@example.com",
        )
        self.visitor = User.objects.create_user(username="visitor", password="test-password")
        # Catatan: Gunakan category="Django" (karena model Project di proyek ini memiliki kolom category, bukan tech_stack)
        self.project = Project.objects.create(
            title="Portfolio", description="My website", category="Django",
        )
        self.list_url = reverse("api:project-list")
        self.detail_url = reverse("api:project-detail", args=[self.project.id])
        self.star_url = reverse("api:project-star", args=[self.project.id])
        self.payload = {
            "title": "New project", "description": "A useful app", "tech_stack": "Python",
            "project_url": "https://example.com/", "project_image_url": "",
        }

    def test_public_list_and_detail(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(self.project.id))
        self.assertFalse(response.data[0]["is_starred"])
        self.assertNotIn("fields", response.data[0])
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_200_OK)

    def test_search_and_empty_results(self):
        response = self.client.get(self.list_url, {"title": "PORT"})
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.list_url, {"title": "not-found"})
        self.assertEqual(response.data, [])

    def test_missing_project(self):
        url = reverse("api:project-detail", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_and_visitor_cannot_write(self):
        for user in (None, self.visitor):
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.post(self.list_url, self.payload, format="json").status_code, 403)
            self.assertEqual(self.client.patch(self.detail_url, {"title": "Changed"}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(self.detail_url).status_code, 403)
        self.assertEqual(Project.objects.count(), 1)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Portfolio")

    def test_owner_can_create(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Project.objects.filter(pk=response.data["id"]).exists())

    def test_validation(self):
        self.client.force_authenticate(user=self.owner)
        for changes, field in [
            ({"title": "   "}, "title"),
            ({"title": '<img src="x" onerror="alert(1)">'}, "title"),
            ({"project_url": "javascript:alert(1)"}, "project_url"),
        ]:
            response = self.client.post(self.list_url, {**self.payload, **changes}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(field, response.data)
        self.assertEqual(Project.objects.count(), 1)

    def test_patch_put_and_delete(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(self.detail_url, {"title": "Changed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.description, "My website")
        response = self.client.put(self.detail_url, {"title": "Incomplete"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.put(self.detail_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b"")
        self.assertFalse(Project.objects.filter(pk=self.project.id).exists())

    def test_star_requires_login_and_toggles(self):
        self.assertEqual(self.client.post(self.star_url).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.visitor)
        response = self.client.post(self.star_url)
        self.assertTrue(response.data["is_starred"])
        self.assertEqual(response.data["star_count"], 1)
        response = self.client.post(self.star_url)
        self.assertFalse(response.data["is_starred"])
        self.assertEqual(response.data["star_count"], 0)

    def test_computed_fields_are_read_only(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(self.list_url, {
            **self.payload, "star_count": 99, "is_starred": True,
            "starred_by_names": "forged", "starred_by": [self.visitor.id],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["star_count"], 0)
        self.assertFalse(response.data["is_starred"])

    def test_staff_and_editor_cannot_manage_tutorial_projects(self):
        self.visitor.is_staff = True
        self.visitor.save()
        self.visitor.groups.add(Group.objects.create(name="Editor"))
        self.client.force_authenticate(user=self.visitor)
        response = self.client.patch(self.detail_url, {"title": "Changed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_method(self):
        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.delete(self.list_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_session_write_without_csrf_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="owner", password="test-password"))
        response = client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Project.objects.count(), 1)

    def test_session_write_with_csrf_succeeds(self):
        client = APIClient(enforce_csrf_checks=True)
        client.login(username="owner", password="test-password")
        # The Browsable API form renders a real CSRF token into the response.
        page = client.get(self.list_url, HTTP_ACCEPT="text/html")
        self.assertEqual(page.status_code, status.HTTP_200_OK)
        token = client.cookies["csrftoken"].value
        response = client.post(
            self.list_url, self.payload, format="json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ExperienceAPITest(APITestCase):
    """Comprehensive test suite for Experience REST API implementing 4-role RBAC,
    input sanitization, relational validation, computed read-only fields,
    database mutation integrity, and strict CSRF protection.
    """

    def setUp(self):
        """Initialize test database with clean roles, accounts, and sample experience."""
        # 1. Superuser / Portfolio Owner
        self.owner = User.objects.create_superuser(
            username="owner",
            password="test-password",
            email="owner@example.com",
        )

        # 2. Editor user belonging to 'Editor' group
        editor_group = Group.objects.create(name="Editor")
        self.editor = User.objects.create_user(
            username="editor",
            password="test-password",
            email="editor@example.com",
        )
        self.editor.groups.add(editor_group)

        # 3. Regular authenticated visitor
        self.visitor = User.objects.create_user(
            username="visitor",
            password="test-password",
            email="visitor@example.com",
        )

        # Sample initial Experience instance
        self.experience = Experience.objects.create(
            title="Software Engineering Intern",
            company="TechCorp",
            description="Developing REST APIs and backend services.",
            category="internship",
            started_at="2025-01-01",
            ended_at="2025-06-30",
        )

        self.list_url = reverse("api:experience-list")
        self.detail_url = reverse("api:experience-detail", args=[self.experience.id])
        self.star_url = reverse("api:experience-star", args=[self.experience.id])

        self.payload = {
            "title": "Junior Python Developer",
            "company": "StartupX",
            "description": "Backend API development with DRF.",
            "category": "full-time",
            "started_at": "2025-07-01",
            "ended_at": "2025-12-31",
        }

    def test_public_list_and_detail(self):
        """Ensure unauthenticated visitors can view list and detail with expected fields."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["id"], str(self.experience.id))
        self.assertEqual(item["title"], "Software Engineering Intern")
        self.assertEqual(item["company"], "TechCorp")
        self.assertEqual(item["category"], "internship")
        self.assertEqual(item["category_display"], "Internship")
        self.assertFalse(item["is_starred"])
        self.assertEqual(item["star_count"], 0)
        self.assertEqual(item["starred_by_names"], "")
        self.assertNotIn("fields", item)

        detail_response = self.client.get(self.detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(self.experience.id))

        options_response = self.client.options(self.detail_url)
        self.assertEqual(options_response.status_code, status.HTTP_200_OK)

    def test_search_and_filtering(self):
        """Test query parameter filtering by title substring, q alias, and category slug."""
        # Query title substring
        res = self.client.get(self.list_url, {"title": "Software"})
        self.assertEqual(len(res.data), 1)

        # Alternative query parameter q
        res_q = self.client.get(self.list_url, {"q": "Engineering"})
        self.assertEqual(len(res_q.data), 1)

        # Category match
        res_cat = self.client.get(self.list_url, {"category": "internship"})
        self.assertEqual(len(res_cat.data), 1)

        # Category mismatch
        res_mismatch = self.client.get(self.list_url, {"category": "freelance"})
        self.assertEqual(res_mismatch.data, [])

        # Non-matching title query
        res_empty = self.client.get(self.list_url, {"title": "NonExistent"})
        self.assertEqual(res_empty.data, [])

    def test_missing_experience_returns_404(self):
        """Verify 404 Not Found is returned for non-existent experience UUIDs."""
        non_existent_url = reverse("api:experience-detail", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(non_existent_url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.put(non_existent_url, self.payload, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(non_existent_url, {"title": "Updated"}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(non_existent_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_and_visitor_cannot_write_and_db_remains_intact(self):
        """Ensure anonymous visitors and regular users cannot perform mutating operations (403),
        and verify database integrity is completely preserved.
        """
        for user in (None, self.visitor):
            self.client.force_authenticate(user=user)
            self.assertEqual(
                self.client.post(self.list_url, self.payload, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(
                self.client.put(self.detail_url, self.payload, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(
                self.client.patch(self.detail_url, {"title": "Unauthorized"}, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(
                self.client.delete(self.detail_url).status_code,
                status.HTTP_403_FORBIDDEN,
            )

        # Verify DB integrity: record count and values remain strictly untouched
        self.assertEqual(Experience.objects.count(), 1)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.title, "Software Engineering Intern")
        self.assertEqual(self.experience.company, "TechCorp")

    def test_star_requires_login(self):
        """Ensure unauthenticated visitors cannot star experiences (403 Forbidden)."""
        self.client.force_authenticate(user=None)
        response = self.client.post(self.star_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.experience.starred_by.count(), 0)

    def test_regular_user_can_star_and_toggle(self):
        """Ensure authenticated regular users can toggle star status successfully (200 OK)."""
        self.client.force_authenticate(user=self.visitor)

        # Star the experience
        response = self.client.post(self.star_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_starred"])
        self.assertEqual(response.data["star_count"], 1)
        self.assertIn(self.visitor.username, response.data["starred_by_names"])
        self.assertEqual(self.experience.starred_by.count(), 1)

        # Unstar the experience
        response = self.client.post(self.star_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_starred"])
        self.assertEqual(response.data["star_count"], 0)
        self.assertEqual(self.experience.starred_by.count(), 0)

    def test_editor_role_can_patch_and_put_but_cannot_create_or_delete(self):
        """Ensure Editors can update (PUT/PATCH) but are strictly forbidden from POST and DELETE,
        verifying database state after each rejection.
        """
        self.client.force_authenticate(user=self.editor)

        # 1. Editor PATCH succeeds
        patch_resp = self.client.patch(
            self.detail_url, {"title": "Patched by Editor"}, format="json"
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.title, "Patched by Editor")
        self.assertEqual(self.experience.company, "TechCorp")

        # 2. Editor PUT succeeds
        put_payload = {
            "title": "Full Update by Editor",
            "company": "Editor Corp",
            "description": "Comprehensive update from Editor role.",
            "category": "freelance",
            "started_at": "2025-02-01",
            "ended_at": "2025-08-01",
        }
        put_resp = self.client.put(self.detail_url, put_payload, format="json")
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.title, "Full Update by Editor")
        self.assertEqual(self.experience.company, "Editor Corp")
        self.assertEqual(self.experience.category, "freelance")

        # 3. Editor POST (create) is FORBIDDEN
        post_resp = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(post_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Experience.objects.count(), 1)

        # 4. Editor DELETE is FORBIDDEN
        del_resp = self.client.delete(self.detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Experience.objects.count(), 1)
        self.assertTrue(Experience.objects.filter(pk=self.experience.id).exists())

    def test_owner_role_can_create_update_and_delete(self):
        """Ensure Portfolio Owner (superuser) has full CRUD access."""
        self.client.force_authenticate(user=self.owner)

        # 1. Create (POST) -> 201 Created
        create_resp = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Experience.objects.count(), 2)
        new_pk = create_resp.data["id"]
        self.assertTrue(Experience.objects.filter(pk=new_pk).exists())

        # 2. Update (PATCH) -> 200 OK
        patch_resp = self.client.patch(
            self.detail_url, {"company": "Owner Enterprise"}, format="json"
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.company, "Owner Enterprise")

        # 3. Update (PUT) -> 200 OK
        put_payload = {
            **self.payload,
            "title": "Principal Architect",
            "company": "Enterprise Global",
        }
        put_resp = self.client.put(self.detail_url, put_payload, format="json")
        self.assertEqual(put_resp.status_code, status.HTTP_200_OK)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.title, "Principal Architect")

        # 4. Delete (DELETE) -> 204 No Content with empty body
        del_resp = self.client.delete(self.detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(del_resp.content, b"")
        self.assertFalse(Experience.objects.filter(pk=self.experience.id).exists())
        self.assertEqual(Experience.objects.count(), 1)

    def test_validation_empty_and_whitespace_title(self):
        """Ensure empty title or XSS payload that strips to empty string is rejected with 400."""
        self.client.force_authenticate(user=self.owner)
        for bad_title in ["   ", '<img src="x" onerror="alert(1)">']:
            response = self.client.post(
                self.list_url, {**self.payload, "title": bad_title}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("title", response.data)
        self.assertEqual(Experience.objects.count(), 1)

    def test_validation_date_order(self):
        """Ensure relational date validation rejects ended_at earlier than started_at."""
        self.client.force_authenticate(user=self.owner)
        invalid_dates = {
            **self.payload,
            "started_at": "2025-12-01",
            "ended_at": "2025-01-01",
        }
        response = self.client.post(self.list_url, invalid_dates, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ended_at", response.data)
        self.assertEqual(Experience.objects.count(), 1)

    def test_sanitization_html_tags_stripped(self):
        """Ensure XSS HTML tags in title, company, and description are stripped by serializer."""
        self.client.force_authenticate(user=self.owner)
        html_payload = {
            **self.payload,
            "title": "<h3>Security Engineer</h3>",
            "company": "<b>Cyber Defense Corp</b>",
            "description": "<p>Securing <i>cloud infrastructure</i> against exploits.</p>",
        }
        response = self.client.post(self.list_url, html_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_exp = Experience.objects.get(pk=response.data["id"])
        self.assertEqual(new_exp.title, "Security Engineer")
        self.assertEqual(new_exp.company, "Cyber Defense Corp")
        self.assertEqual(
            new_exp.description, "Securing cloud infrastructure against exploits."
        )
        self.assertNotIn("<h3>", new_exp.title)
        self.assertNotIn("<b>", new_exp.company)
        self.assertNotIn("<p>", new_exp.description)

    def test_computed_fields_are_read_only(self):
        """Verify computed and read-only fields cannot be forged or altered via request payload."""
        self.client.force_authenticate(user=self.owner)
        forged_payload = {
            **self.payload,
            "star_count": 999,
            "is_starred": True,
            "is_ongoing": False,
            "category_display": "Hacked Category",
            "starred_by_names": "fake_user",
            "starred_by": [self.visitor.id],
        }
        response = self.client.post(self.list_url, forged_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["star_count"], 0)
        self.assertFalse(response.data["is_starred"])
        self.assertEqual(response.data["starred_by_names"], "")
        self.assertEqual(response.data["category_display"], "Full-Time")

    def test_wrong_method(self):
        """Verify unsupported HTTP method on collection endpoint returns 405 Method Not Allowed."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_session_write_without_csrf_is_rejected(self):
        """Ensure modifying operations without CSRF token are strictly rejected (HTTP 403)
        when SessionAuthentication is enforced, preserving database state.
        """
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="owner", password="test-password"))

        post_res = client.post(self.list_url, self.payload, format="json")
        self.assertEqual(post_res.status_code, status.HTTP_403_FORBIDDEN)

        put_res = client.put(self.detail_url, self.payload, format="json")
        self.assertEqual(put_res.status_code, status.HTTP_403_FORBIDDEN)

        del_res = client.delete(self.detail_url)
        self.assertEqual(del_res.status_code, status.HTTP_403_FORBIDDEN)

        # Confirm DB was not touched
        self.assertEqual(Experience.objects.count(), 1)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.title, "Software Engineering Intern")

    def test_session_write_with_csrf_succeeds(self):
        """Ensure session-authenticated write succeeds when legitimate CSRF token is provided."""
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="owner", password="test-password"))

        # Fetch collection page to populate csrftoken cookie
        page = client.get(self.list_url, HTTP_ACCEPT="text/html")
        self.assertEqual(page.status_code, status.HTTP_200_OK)
        token = client.cookies["csrftoken"].value

        response = client.post(
            self.list_url,
            self.payload,
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Experience.objects.count(), 2)

    def test_editor_session_with_csrf_can_patch_but_delete_is_forbidden(self):
        """Ensure Editor using session and valid CSRF token can PATCH data,
        but DELETE remains strictly forbidden due to RBAC permissions.
        """
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username="editor", password="test-password"))

        page = client.get(self.list_url, HTTP_ACCEPT="text/html")
        self.assertEqual(page.status_code, status.HTTP_200_OK)
        token = client.cookies["csrftoken"].value

        # Editor PATCH with CSRF succeeds
        patch_res = client.patch(
            self.detail_url,
            {"title": "CSRF Verified Editor Patch"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.experience.refresh_from_db()
        self.assertEqual(self.experience.title, "CSRF Verified Editor Patch")

        # Editor DELETE with CSRF is forbidden by RBAC
        del_res = client.delete(self.detail_url, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(del_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Experience.objects.count(), 1)
        self.assertTrue(Experience.objects.filter(pk=self.experience.id).exists())


# Backward compatibility alias
EditorRoleAPITest = ExperienceAPITest
