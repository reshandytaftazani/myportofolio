import uuid

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from main.models import Education, Experience, Project, Skill


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


class SkillAPITest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="owner", password="test-password", email="owner@example.com",
        )
        self.visitor = User.objects.create_user(
            username="visitor", password="test-password",
        )
        self.editor = User.objects.create_user(
            username="editor", password="test-password",
        )
        self.editor_group, _ = Group.objects.get_or_create(name="Editor")
        self.editor.groups.add(self.editor_group)

        self.skill = Skill.objects.create(
            title="Django REST Framework",
            description="Building robust RESTful APIs in Python.",
            level="Advanced",
            code_snippet="def get_queryset(self):\n    return Skill.objects.filter(is_active=True)",
        )
        self.skill_beginner = Skill.objects.create(
            title="Python Basics",
            description="Introduction to Python programming syntax.",
            level="Beginner",
            code_snippet="for x in [1, 2, 3]:\n    if x < 2:\n        print('<div>test</div>')",
        )

        self.list_url = reverse("api:skill-list")
        self.detail_url = reverse("api:skill-detail", args=[self.skill.id])
        self.star_url = reverse("api:skill-star", args=[self.skill.id])
        self.payload = {
            "title": "PostgreSQL",
            "description": "Relational database management and query optimization.",
            "level": "Intermediate",
            "code_snippet": "SELECT * FROM skills WHERE level = 'Intermediate' AND count < 10;",
        }

    def test_public_list_and_detail(self):
        """Test unauthenticated public access to skill list and detail endpoints."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

        # Verify items contain correct fields and no Django internal 'fields' wrapper
        found = next((item for item in response.data if item["id"] == str(self.skill.id)), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["title"], "Django REST Framework")
        self.assertEqual(found["description"], "Building robust RESTful APIs in Python.")
        self.assertEqual(found["level"], "Advanced")
        self.assertEqual(found["code_snippet"], "def get_queryset(self):\n    return Skill.objects.filter(is_active=True)")
        self.assertFalse(found["is_starred"])
        self.assertEqual(found["star_count"], 0)
        self.assertEqual(found["starred_by_names"], "")
        self.assertNotIn("fields", found)

        detail_response = self.client.get(self.detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(self.skill.id))
        self.assertEqual(detail_response.data["title"], "Django REST Framework")

        options_response = self.client.options(self.detail_url)
        self.assertEqual(options_response.status_code, status.HTTP_200_OK)

    def test_search_and_filtering(self):
        """Test searching by title and level: individually, combined, and with no results."""
        # 1. Filter title individually
        res_title = self.client.get(self.list_url, {"title": "Django"})
        self.assertEqual(res_title.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_title.data), 1)
        self.assertEqual(res_title.data[0]["title"], "Django REST Framework")

        # 2. Filter level individually
        res_level = self.client.get(self.list_url, {"level": "Beginner"})
        self.assertEqual(res_level.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_level.data), 1)
        self.assertEqual(res_level.data[0]["title"], "Python Basics")

        # Level 'all' should return all items without filtering
        res_all = self.client.get(self.list_url, {"level": "all"})
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data), 2)

        # 3. Filter title and level together
        res_both = self.client.get(self.list_url, {"title": "Python", "level": "Beginner"})
        self.assertEqual(res_both.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_both.data), 1)
        self.assertEqual(res_both.data[0]["title"], "Python Basics")

        # 4. Filter with no results (title mismatch)
        res_no_title = self.client.get(self.list_url, {"title": "NonExistentSkill"})
        self.assertEqual(res_no_title.status_code, status.HTTP_200_OK)
        self.assertEqual(res_no_title.data, [])

        # 5. Filter with no results (level mismatch)
        res_no_level = self.client.get(self.list_url, {"level": "Expert"})
        self.assertEqual(res_no_level.status_code, status.HTTP_200_OK)
        self.assertEqual(res_no_level.data, [])

        # 6. Filter with no results (title and level together do not match)
        res_no_both = self.client.get(self.list_url, {"title": "Django", "level": "Beginner"})
        self.assertEqual(res_no_both.status_code, status.HTTP_200_OK)
        self.assertEqual(res_no_both.data, [])

    def test_missing_skill_returns_404(self):
        """Verify 404 Not Found is returned for non-existent skill UUIDs."""
        non_existent_url = reverse("api:skill-detail", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(non_existent_url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.put(non_existent_url, self.payload, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(non_existent_url, {"title": "Updated"}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(non_existent_url).status_code, status.HTTP_404_NOT_FOUND)

        non_existent_star_url = reverse("api:skill-star", args=[uuid.uuid4()])
        self.client.force_authenticate(user=self.visitor)
        self.assertEqual(self.client.post(non_existent_star_url).status_code, status.HTTP_404_NOT_FOUND)

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
        self.assertEqual(Skill.objects.count(), 2)
        self.skill.refresh_from_db()
        self.assertEqual(self.skill.title, "Django REST Framework")
        self.assertEqual(self.skill.description, "Building robust RESTful APIs in Python.")

    def test_owner_can_create_update_delete(self):
        """Verify superuser can create, update (PUT/PATCH), and delete skills."""
        self.client.force_authenticate(user=self.owner)

        # Create
        res_create = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        new_id = res_create.data["id"]
        self.assertTrue(Skill.objects.filter(pk=new_id).exists())
        self.assertEqual(Skill.objects.count(), 3)

        new_detail_url = reverse("api:skill-detail", args=[new_id])

        # PATCH update
        res_patch = self.client.patch(new_detail_url, {"level": "Expert"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["level"], "Expert")

        # PUT update
        updated_payload = {
            "title": "PostgreSQL Advanced",
            "description": "Deep dive into query planner, indexing, and WAL.",
            "level": "Expert",
            "code_snippet": "EXPLAIN ANALYZE SELECT 1;",
        }
        res_put = self.client.put(new_detail_url, updated_payload, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.assertEqual(res_put.data["title"], "PostgreSQL Advanced")

        # DELETE
        res_delete = self.client.delete(new_detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(res_delete.content, b"")
        self.assertFalse(Skill.objects.filter(pk=new_id).exists())
        self.assertEqual(Skill.objects.count(), 2)

    def test_editor_can_put_and_patch_but_cannot_create_or_delete(self):
        """Verify Editor role can update via PUT and PATCH, but POST create and DELETE are forbidden."""
        self.client.force_authenticate(user=self.editor)

        # Editor cannot create new skill
        res_post = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Skill.objects.count(), 2)

        # Editor can PATCH existing skill
        res_patch = self.client.patch(self.detail_url, {"description": "Updated by Editor."}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.skill.refresh_from_db()
        self.assertEqual(self.skill.description, "Updated by Editor.")

        # Editor can PUT existing skill
        put_payload = {
            "title": "Django REST Framework 3.15",
            "description": "Comprehensive REST framework for Django.",
            "level": "Advanced",
            "code_snippet": "print('updated')",
        }
        res_put = self.client.put(self.detail_url, put_payload, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.skill.refresh_from_db()
        self.assertEqual(self.skill.title, "Django REST Framework 3.15")

        # Editor cannot DELETE skill
        res_del = self.client.delete(self.detail_url)
        self.assertEqual(res_del.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Skill.objects.count(), 2)
        self.assertTrue(Skill.objects.filter(pk=self.skill.id).exists())

    def test_text_validation_and_sanitization(self):
        """Verify plain text fields are sanitized and empty values are rejected,
        while code_snippet preserves '<', '>', and HTML examples without code execution or stripping.
        """
        self.client.force_authenticate(user=self.owner)

        # Validation failure: empty fields after strip_tags
        for invalid_field in [
            {"title": "   "},
            {"title": "<b>  </b>"},
            {"description": "   "},
            {"description": "<p></p>"},
            {"level": "   "},
            {"level": "<span></span>"},
        ]:
            res = self.client.post(self.list_url, {**self.payload, **invalid_field}, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Skill.objects.count(), 2)

        # Sanitization: plain text fields stripped of tags, code_snippet preserves tags and '<'
        payload_with_html = {
            "title": "<b>FastAPI</b>",
            "description": "<p>Modern web framework.</p>",
            "level": "<strong>Intermediate</strong>",
            "code_snippet": "if a < b and c > d:\n    return '<div>keep-html</div>'",
        }
        res_create = self.client.post(self.list_url, payload_with_html, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        created_skill = Skill.objects.get(pk=res_create.data["id"])
        self.assertEqual(created_skill.title, "FastAPI")
        self.assertEqual(created_skill.description, "Modern web framework.")
        self.assertEqual(created_skill.level, "Intermediate")
        # Ensure code_snippet preserves operator '<' and raw HTML strings intact
        self.assertEqual(created_skill.code_snippet, "if a < b and c > d:\n    return '<div>keep-html</div>'")
        self.assertIn("< b", created_skill.code_snippet)
        self.assertIn("<div>keep-html</div>", created_skill.code_snippet)

    def test_star_requires_login_and_toggles(self):
        """Ensure anonymous user cannot star, while authenticated users can toggle star."""
        # Unauthenticated star attempt rejected
        self.client.force_authenticate(user=None)
        res_anon = self.client.post(self.star_url)
        self.assertEqual(res_anon.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.skill.starred_by.count(), 0)

        # Authenticated visitor stars skill
        self.client.force_authenticate(user=self.visitor)
        res_star = self.client.post(self.star_url)
        self.assertEqual(res_star.status_code, status.HTTP_200_OK)
        self.assertTrue(res_star.data["is_starred"])
        self.assertEqual(res_star.data["star_count"], 1)
        self.assertIn(self.visitor.username, res_star.data["starred_by_names"])
        self.assertEqual(self.skill.starred_by.count(), 1)

        # Authenticated visitor unstars skill
        res_unstar = self.client.post(self.star_url)
        self.assertEqual(res_unstar.status_code, status.HTTP_200_OK)
        self.assertFalse(res_unstar.data["is_starred"])
        self.assertEqual(res_unstar.data["star_count"], 0)
        self.assertEqual(res_unstar.data["starred_by_names"], "")
        self.assertEqual(self.skill.starred_by.count(), 0)

    def test_computed_fields_are_read_only(self):
        """Verify computed star fields cannot be manipulated via request payload."""
        self.client.force_authenticate(user=self.owner)
        forged_payload = {
            **self.payload,
            "star_count": 9999,
            "is_starred": True,
            "starred_by_names": "fake_owner, fake_visitor",
            "starred_by": [self.visitor.id],
        }
        response = self.client.post(self.list_url, forged_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["star_count"], 0)
        self.assertFalse(response.data["is_starred"])
        self.assertEqual(response.data["starred_by_names"], "")

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
        self.assertEqual(Skill.objects.count(), 2)
        self.skill.refresh_from_db()
        self.assertEqual(self.skill.title, "Django REST Framework")

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
        self.assertEqual(Skill.objects.count(), 3)

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
        self.skill.refresh_from_db()
        self.assertEqual(self.skill.title, "CSRF Verified Editor Patch")

        # Editor DELETE with CSRF is forbidden by RBAC
        del_res = client.delete(self.detail_url, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(del_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Skill.objects.count(), 2)
        self.assertTrue(Skill.objects.filter(pk=self.skill.id).exists())


class EducationAPITest(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="owner", password="test-password", email="owner@example.com",
        )
        self.visitor = User.objects.create_user(
            username="visitor", password="test-password",
        )
        self.editor = User.objects.create_user(
            username="editor", password="test-password",
        )
        self.editor_group, _ = Group.objects.get_or_create(name="Editor")
        self.editor.groups.add(self.editor_group)

        # Create two educations with same start_year to test tie-breaker id ordering
        # Meta ordering is ['-start_year'], API ordering is ['-start_year', 'id']
        self.edu_ui = Education.objects.create(
            school_name="Universitas Indonesia",
            period="2023 - 2027",
            detail="Undergraduate Computer Science Program.",
            start_year=2023,
        )
        self.edu_itb = Education.objects.create(
            school_name="Institut Teknologi Bandung",
            period="2023 - 2027",
            detail="Exchange program in software engineering.",
            start_year=2023,
        )
        self.edu_sma = Education.objects.create(
            school_name="SMAN 1 Jakarta",
            period="2020 - 2023",
            detail="High School Diploma in Natural Sciences.",
            start_year=2020,
        )

        self.list_url = reverse("api:education-list")
        self.detail_url = reverse("api:education-detail", args=[self.edu_ui.id])
        self.star_url = reverse("api:education-star", args=[self.edu_ui.id])
        self.payload = {
            "school_name": "National University of Singapore",
            "period": "2024 - 2025",
            "detail": "Academic exchange scholarship.",
            "start_year": 2024,
        }

    def test_public_list_and_detail(self):
        """Test unauthenticated public access to education list and detail endpoints."""
        for client_user in (None, self.visitor, self.editor, self.owner):
            self.client.force_authenticate(user=client_user)
            response = self.client.get(self.list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 3)

            # Check explicit fields contract
            item = next((x for x in response.data if x["id"] == self.edu_ui.id), None)
            self.assertIsNotNone(item)
            self.assertEqual(item["school_name"], "Universitas Indonesia")
            self.assertEqual(item["period"], "2023 - 2027")
            self.assertEqual(item["detail"], "Undergraduate Computer Science Program.")
            self.assertEqual(item["start_year"], 2023)
            self.assertEqual(item["star_count"], 0)
            self.assertFalse(item["is_starred"])
            self.assertEqual(item["starred_by_names"], "")
            self.assertNotIn("fields", item)

            detail_res = self.client.get(self.detail_url)
            self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
            self.assertEqual(detail_res.data["id"], self.edu_ui.id)
            self.assertEqual(detail_res.data["school_name"], "Universitas Indonesia")

        # Check OPTIONS method works
        self.client.force_authenticate(user=None)
        options_res = self.client.options(self.detail_url)
        self.assertEqual(options_res.status_code, status.HTTP_200_OK)

    def test_search_and_ordering(self):
        """Test searching by school_name (match / no match) and ordering (-start_year, id)."""
        # 1. Search match substring case-insensitive
        res_match = self.client.get(self.list_url, {"school_name": "universitas"})
        self.assertEqual(res_match.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_match.data), 1)
        self.assertEqual(res_match.data[0]["school_name"], "Universitas Indonesia")

        res_match_upper = self.client.get(self.list_url, {"school_name": "TEKNOLOGI"})
        self.assertEqual(res_match_upper.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_match_upper.data), 1)
        self.assertEqual(res_match_upper.data[0]["school_name"], "Institut Teknologi Bandung")

        # 2. Search no match
        res_none = self.client.get(self.list_url, {"school_name": "Oxford University"})
        self.assertEqual(res_none.status_code, status.HTTP_200_OK)
        self.assertEqual(res_none.data, [])

        # 3. Test empty list
        Education.objects.all().delete()
        res_empty = self.client.get(self.list_url)
        self.assertEqual(res_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(res_empty.data, [])

        # 4. Recreate fixtures with distinct and tie-breaker years
        e1 = Education.objects.create(
            school_name="Alpha Academy",
            period="2023",
            detail="Detail 1",
            start_year=2023,
        )
        e2 = Education.objects.create(
            school_name="Beta College",
            period="2023",
            detail="Detail 2",
            start_year=2023,
        )
        e3 = Education.objects.create(
            school_name="Gamma High",
            period="2021",
            detail="Detail 3",
            start_year=2021,
        )
        e4 = Education.objects.create(
            school_name="Delta Primary",
            period="2025",
            detail="Detail 4",
            start_year=2025,
        )

        res_order = self.client.get(self.list_url)
        self.assertEqual(res_order.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_order.data), 4)

        # Ordering should be -start_year, id:
        # e4 (2025) first, then e1 (2023, id smaller), then e2 (2023, id larger), then e3 (2021)
        self.assertLess(e1.id, e2.id)
        expected_ids = [e4.id, e1.id, e2.id, e3.id]
        actual_ids = [item["id"] for item in res_order.data]
        self.assertEqual(actual_ids, expected_ids)

    def test_missing_education_returns_404(self):
        """Verify 404 Not Found is returned for non-existent education IDs."""
        non_existent_url = reverse("api:education-detail", args=[999999])
        self.assertEqual(self.client.get(non_existent_url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.owner)
        self.assertEqual(self.client.put(non_existent_url, self.payload, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(non_existent_url, {"period": "2024"}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(non_existent_url).status_code, status.HTTP_404_NOT_FOUND)

        non_existent_star_url = reverse("api:education-star", args=[999999])
        self.client.force_authenticate(user=self.visitor)
        self.assertEqual(self.client.post(non_existent_star_url).status_code, status.HTTP_404_NOT_FOUND)

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
                self.client.patch(self.detail_url, {"period": "Unauthorized"}, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(
                self.client.delete(self.detail_url).status_code,
                status.HTTP_403_FORBIDDEN,
            )

        # Verify DB integrity: record count and values remain strictly untouched
        self.assertEqual(Education.objects.count(), 3)
        self.edu_ui.refresh_from_db()
        self.assertEqual(self.edu_ui.school_name, "Universitas Indonesia")
        self.assertEqual(self.edu_ui.period, "2023 - 2027")
        self.assertEqual(self.edu_ui.detail, "Undergraduate Computer Science Program.")

    def test_owner_can_create_update_delete(self):
        """Verify superuser can create, update (PUT/PATCH), and delete educations."""
        self.client.force_authenticate(user=self.owner)

        # Create
        res_create = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        new_id = res_create.data["id"]
        self.assertTrue(isinstance(new_id, int))
        self.assertTrue(Education.objects.filter(pk=new_id).exists())
        self.assertEqual(Education.objects.count(), 4)

        new_detail_url = reverse("api:education-detail", args=[new_id])

        # PATCH update
        res_patch = self.client.patch(new_detail_url, {"period": "2024 - 2026"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["period"], "2024 - 2026")

        # PUT update
        updated_payload = {
            "school_name": "NUS School of Computing",
            "period": "2024 - 2026",
            "detail": "Updated scholarship program details.",
            "start_year": 2024,
        }
        res_put = self.client.put(new_detail_url, updated_payload, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.assertEqual(res_put.data["school_name"], "NUS School of Computing")

        # DELETE
        res_delete = self.client.delete(new_detail_url)
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(res_delete.content, b"")
        self.assertFalse(Education.objects.filter(pk=new_id).exists())
        self.assertEqual(Education.objects.count(), 3)

    def test_editor_can_put_and_patch_but_cannot_create_or_delete(self):
        """Verify Editor role can update via PUT and PATCH, but POST create and DELETE are forbidden."""
        self.client.force_authenticate(user=self.editor)

        # Editor cannot create new education
        res_post = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Education.objects.count(), 3)

        # Editor can PATCH existing education
        res_patch = self.client.patch(self.detail_url, {"detail": "Updated by Editor."}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.edu_ui.refresh_from_db()
        self.assertEqual(self.edu_ui.detail, "Updated by Editor.")

        # Editor can PUT existing education
        put_payload = {
            "school_name": "Universitas Indonesia - Faculty of CS",
            "period": "2023 - 2027",
            "detail": "Undergraduate CS with Editor Updates.",
            "start_year": 2023,
        }
        res_put = self.client.put(self.detail_url, put_payload, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.edu_ui.refresh_from_db()
        self.assertEqual(self.edu_ui.school_name, "Universitas Indonesia - Faculty of CS")
        self.assertEqual(self.edu_ui.detail, "Undergraduate CS with Editor Updates.")

        # Editor cannot DELETE education
        res_del = self.client.delete(self.detail_url)
        self.assertEqual(res_del.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Education.objects.count(), 3)
        self.assertTrue(Education.objects.filter(pk=self.edu_ui.id).exists())

    def test_text_validation_and_sanitization(self):
        """Verify plain text fields are sanitized and empty values or invalid types are rejected."""
        self.client.force_authenticate(user=self.owner)

        # Validation failure: empty fields after strip_tags
        for invalid_field in [
            {"school_name": "   "},
            {"school_name": "<b>  </b>"},
            {"period": "   "},
            {"period": "<i></i>"},
            {"detail": "   "},
            {"detail": "<p></p>"},
            {"start_year": "invalid_integer"},
            {"start_year": None},
        ]:
            res = self.client.post(self.list_url, {**self.payload, **invalid_field}, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Education.objects.count(), 3)

        # Sanitization: plain text fields stripped of HTML tags
        payload_with_html = {
            "school_name": "<b>Harvard University</b>",
            "period": "<i>2024 - 2028</i>",
            "detail": "<p>Liberal Arts and Computer Science</p>",
            "start_year": 2024,
        }
        res_create = self.client.post(self.list_url, payload_with_html, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        created_edu = Education.objects.get(pk=res_create.data["id"])
        self.assertEqual(created_edu.school_name, "Harvard University")
        self.assertEqual(created_edu.period, "2024 - 2028")
        self.assertEqual(created_edu.detail, "Liberal Arts and Computer Science")
        self.assertEqual(created_edu.start_year, 2024)

    def test_star_requires_login_and_toggles(self):
        """Ensure anonymous user cannot star, while authenticated users can toggle star."""
        # Unauthenticated star attempt rejected
        self.client.force_authenticate(user=None)
        res_anon = self.client.post(self.star_url)
        self.assertEqual(res_anon.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.edu_ui.starred_by.count(), 0)

        # Authenticated visitor stars education
        self.client.force_authenticate(user=self.visitor)
        res_star = self.client.post(self.star_url)
        self.assertEqual(res_star.status_code, status.HTTP_200_OK)
        self.assertTrue(res_star.data["is_starred"])
        self.assertEqual(res_star.data["star_count"], 1)
        self.assertIn(self.visitor.username, res_star.data["starred_by_names"])
        self.assertEqual(self.edu_ui.starred_by.count(), 1)

        # Authenticated visitor unstars education
        res_unstar = self.client.post(self.star_url)
        self.assertEqual(res_unstar.status_code, status.HTTP_200_OK)
        self.assertFalse(res_unstar.data["is_starred"])
        self.assertEqual(res_unstar.data["star_count"], 0)
        self.assertEqual(res_unstar.data["starred_by_names"], "")
        self.assertEqual(self.edu_ui.starred_by.count(), 0)

    def test_star_actor_cannot_be_forged_and_roles_can_star(self):
        """Verify star toggling always uses request.user even if forged body is sent,
        and all authenticated roles (regular user, editor, superuser) can toggle stars.
        """
        # Editor stars
        self.client.force_authenticate(user=self.editor)
        # Attempt to forge star actor to owner
        res_editor = self.client.post(self.star_url, {"user": self.owner.id, "user_id": self.owner.id}, format="json")
        self.assertEqual(res_editor.status_code, status.HTTP_200_OK)
        self.assertTrue(res_editor.data["is_starred"])
        self.assertEqual(res_editor.data["star_count"], 1)
        self.assertIn(self.editor.username, res_editor.data["starred_by_names"])
        self.assertNotIn(self.owner.username, res_editor.data["starred_by_names"])
        self.assertTrue(self.edu_ui.starred_by.filter(pk=self.editor.pk).exists())
        self.assertFalse(self.edu_ui.starred_by.filter(pk=self.owner.pk).exists())

        # Superuser stars
        self.client.force_authenticate(user=self.owner)
        res_owner = self.client.post(self.star_url)
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)
        self.assertEqual(res_owner.data["star_count"], 2)
        self.assertTrue(res_owner.data["is_starred"])
        self.assertIn(self.owner.username, res_owner.data["starred_by_names"])
        self.assertIn(self.editor.username, res_owner.data["starred_by_names"])

    def test_computed_fields_are_read_only(self):
        """Verify computed star fields cannot be manipulated via request payload."""
        self.client.force_authenticate(user=self.owner)
        forged_payload = {
            **self.payload,
            "star_count": 9999,
            "is_starred": True,
            "starred_by_names": "fake_owner, fake_visitor",
            "starred_by": [self.visitor.id],
        }
        response = self.client.post(self.list_url, forged_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["star_count"], 0)
        self.assertFalse(response.data["is_starred"])
        self.assertEqual(response.data["starred_by_names"], "")

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
        self.assertEqual(Education.objects.count(), 3)
        self.edu_ui.refresh_from_db()
        self.assertEqual(self.edu_ui.school_name, "Universitas Indonesia")

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
        self.assertEqual(Education.objects.count(), 4)

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
            {"period": "2023 - 2028 (CSRF Patch)"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.edu_ui.refresh_from_db()
        self.assertEqual(self.edu_ui.period, "2023 - 2028 (CSRF Patch)")

        # Editor DELETE with CSRF is forbidden by RBAC
        del_res = client.delete(self.detail_url, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(del_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Education.objects.count(), 3)
        self.assertTrue(Education.objects.filter(pk=self.edu_ui.id).exists())
