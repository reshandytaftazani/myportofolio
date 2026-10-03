"""Optional browser regression checks using an isolated Django test database.

Install requirements-dev.txt and a Playwright Chromium browser to run these.
Windows can also use the installed Edge or Chrome browser.
"""

import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import unittest

from django.contrib.auth.models import Group, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, override_settings

from main.models import Experience, Skill, Education, TechStack, Project


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt for browser checks.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ResourceBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='browser-owner', is_superuser=True)
        self.editor = User.objects.create_user(username='browser-editor')
        self.editor.groups.add(Group.objects.create(name='Editor'))
        self.regular = User.objects.create_user(username='browser-regular')
        Experience.objects.create(title='Developer', company='Acme', description='**Build** <img src=x onerror=alert(1)>',
                                  category='internship', started_at='2026-01-01')
        Experience.objects.create(title='Tutor', company='School', description='Teaching', started_at='2025-01-01', ended_at='2025-12-01')
        Skill.objects.create(title='C++', description='**Algorithms**', level='Advanced', code_snippet='#include <iostream>')
        Skill.objects.create(title='Math', description='Algebra', level='Expert', code_snippet=r'\begin{aligned} a &= b \end{aligned}')
        Education.objects.create(school_name='University', period='2025 - Present', detail='CS', start_year=2025)
        TechStack.objects.create(name='Python', icon_url='https://example.com/icon.svg', filename='<img src=x>.py',
                                 code_snippet='<script>alert(1)</script>\nprint(a < b)', order=0)
        Project.objects.create(title='Portfolio', description='Website', category='Web')
        self.session_cookies = {}
        for user in (self.owner, self.editor, self.regular):
            client = Client()
            client.force_login(user)
            self.session_cookies[user.pk] = client.cookies['sessionid'].value
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        executable = next((str(path) for path in (
            Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'),
            Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
            Path(self.playwright.chromium.executable_path),
        ) if path.exists()), None)
        if executable is None:
            self.playwright.stop()
            raise unittest.SkipTest('Install a browser with python -m playwright install chromium.')
        try:
            self.browser = self.playwright.chromium.launch(executable_path=executable, headless=True)
        except Exception:
            self.playwright.stop()
            raise
        self.context = self.browser.new_context(ignore_https_errors=True)
        self.context.route('https://unpkg.com/aos@*/**', lambda route: route.fulfill(
            content_type='text/javascript' if route.request.url.endswith('.js') else 'text/css',
            body='window.AOS = { init() {}, refreshHard() {} };' if route.request.url.endswith('.js') else ''))
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()
        self.assertEqual(self.errors, [])

    def login(self, user):
        self.context.add_cookies([{'name': 'sessionid', 'value': self.session_cookies[user.pk],
                                  'url': self.live_server_url}])

    def goto(self, path):
        self.page.goto(self.live_server_url + path, wait_until='domcontentloaded')

    def database_call(self, callback):
        # Playwright runs an event loop on this thread; keep synchronous ORM work separate.
        def run():
            from django.db import connections
            try:
                return callback()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(run).result()

    def test_public_lists_without_search_errors_retry_skills_and_code(self):
        from playwright.sync_api import expect
        self.goto('/experience/')
        expect(self.page.locator('.timeline-card')).to_have_count(2)
        expect(self.page.locator('.timeline-card').first.locator('.experience-title')).to_have_text('Developer')
        self.assertEqual(self.page.locator('.experience-desc img').count(), 0)
        self.assertEqual(self.page.locator('[data-search-input]').count(), 0)
        self.context.route('**/api/experience/**', lambda route: route.fulfill(json=[]))
        self.goto('/experience/')
        expect(self.page.locator('[data-empty]')).to_be_visible()
        self.context.unroute('**/api/experience/**')
        self.context.route('**/api/experience/**', lambda route: route.abort())
        self.goto('/experience/')
        expect(self.page.locator('[data-error]')).to_be_visible()
        self.context.unroute('**/api/experience/**')
        self.page.locator('[data-retry]').focus()
        self.page.locator('[data-retry]').press('Enter')
        expect(self.page.locator('.timeline-card:visible')).to_have_count(2)
        expect(self.page.locator('[data-list]')).to_be_focused()
        expect(self.page.locator('[data-list]')).to_have_attribute('aria-busy', 'false')
        expect(self.page.locator('[data-loading]')).to_have_attribute('role', 'status')
        self.goto('/skills/')
        expect(self.page.locator('.tab-btn')).to_have_count(2)
        expect(self.page.locator('.tab-panel.active pre code')).to_have_text('#include <iostream>')
        expect(self.page.locator('.tab-panel.active pre code')).to_have_attribute('data-highlighted', 'yes', timeout=30000)
        self.page.get_by_role('tab', name='Math', exact=True).click()
        expect(self.page.locator('.overleaf-pdf mjx-container')).to_have_count(1, timeout=30000)
        self.assertEqual(self.page.locator('[data-search-input]').count(), 0)
        expect(self.page.locator('.tab-btn')).to_have_count(2)
        expect(self.page.locator('.tab-btn.active')).to_have_text('Math')
        self.goto('/')
        self.assertEqual(self.page.locator('[data-search-input]').count(), 0)
        expect(self.page.locator('.timeline-school')).to_have_text('University')
        expect(self.page.locator('.tech-item')).to_have_count(1)
        self.page.locator('.tech-icon-wrapper').click()
        expect(self.page.locator('.tech-item')).to_have_class('tech-item expanded')
        expect(self.page.locator('.mac-title')).to_have_text('<img src=x>.py')
        expect(self.page.locator('.mac-body code')).to_have_text('<script>alert(1)</script>\nprint(a < b)')
        self.assertEqual(self.page.locator('.mac-title img, .mac-body script').count(), 0)
        self.assertEqual(self.page.locator('[data-open-create]').count(), 0)

    def fill_form(self, dialog, payload):
        for name, value in payload.items():
            field = dialog.locator(f'[name="{name}"]')
            if field.evaluate('(element) => element.tagName') == 'SELECT':
                field.select_option(str(value))
            else:
                field.fill(str(value))

    def test_dashboard_create_validate_edit_delete_each_resource(self):
        from playwright.sync_api import expect
        from main.test_resource_ajax import ResourceAjaxTests
        self.login(self.owner)
        self.goto('/dashboard/')
        for name, initial in ResourceAjaxTests.payloads.items():
            self.page.locator(f'[data-dashboard-tab="{name}"]').click()
            root = self.page.locator(f'[data-dashboard-resource][data-resource="{name}"]')
            expect(root.locator('[data-list]')).to_be_visible()
            root.locator('[data-search-input]').fill('Browser')
            expect(root.locator('[data-empty]')).to_be_visible()
            root.locator('[data-open-create]').click()
            dialog = self.page.locator(f'#{name}-dialog')
            expect(dialog).to_be_visible()
            payload = dict(initial)
            title_field = next(iter(payload))
            payload[title_field] = 'Browser created'
            self.fill_form(dialog, payload)
            dialog.locator('[type=submit]').click()
            expect(dialog).not_to_be_visible()
            row = root.locator('tbody tr').filter(has_text='Browser created')
            expect(row).to_have_count(1)
            row.locator('[data-resource-action="edit"]').click()
            expect(dialog).to_be_visible()
            dialog.locator(f'[name="{title_field}"]').fill('<b></b>')
            dialog.locator('[type=submit]').click()
            expect(dialog.locator('[data-form-error]')).to_be_visible()
            invalid = dialog.locator(f'[name="{title_field}"]')
            expect(invalid).to_have_attribute('aria-invalid', 'true')
            expect(invalid.locator('xpath=..').locator('[data-field-error]')).to_be_visible()
            expect(dialog.locator('[type=submit]')).to_be_enabled()
            dialog.locator(f'[name="{title_field}"]').fill('Browser edited')
            dialog.locator('[type=submit]').click()
            expect(dialog).not_to_be_visible()
            row = root.locator('tbody tr').filter(has_text='Browser edited')
            expect(row).to_have_count(1)
            row.locator('[data-resource-action="delete"]').click()
            self.page.locator(f'#{name}-delete-dialog [data-confirm-delete]').click()
            expect(row).to_have_count(0)
            expect(root.locator('[data-search-input]')).to_have_value('Browser')

    def test_editor_can_edit_but_has_no_add_delete_controls(self):
        from playwright.sync_api import expect
        self.login(self.editor)
        self.goto('/dashboard/')
        expect(self.page.locator('.dashboard-tabs')).to_be_visible()
        self.assertEqual(self.page.locator('[data-open-create]').count(), 0)
        for name in ('experience', 'skills', 'education', 'techstack', 'projects'):
            self.page.locator(f'[data-dashboard-tab="{name}"]').click()
            root = self.page.locator(f'[data-dashboard-resource][data-resource="{name}"]')
            expect(root.locator('[data-list]')).to_be_visible()
            self.assertEqual(root.locator('[data-resource-action="delete"]').count(), 0)
            root.locator('[data-resource-action="edit"]').first.click()
            dialog = self.page.locator(f'#{name}-dialog')
            expect(dialog).to_be_visible()
            dialog.locator('input:not([type=hidden])').first.fill('Editor change')
            dialog.locator('[type=submit]').click()
            expect(dialog).not_to_be_visible()
            expect(root.locator('tbody')).to_contain_text('Editor change')
        self.goto('/projects/')
        expect(self.page.locator('#grid')).to_be_visible()
        self.assertEqual(self.page.locator('[data-resource-action="delete"]').count(), 0)
        self.page.locator('[data-resource-action="edit"]').click()
        dialog = self.page.locator('#projects-dialog')
        expect(dialog).to_be_visible()
        dialog.locator('[name="title"]').fill('Project edited')
        dialog.locator('[type=submit]').click()
        expect(dialog).not_to_be_visible()
        expect(self.page.locator('#grid h2')).to_have_text('Project edited')

    def test_public_modal_refreshes_list_and_project_delete(self):
        from playwright.sync_api import expect
        self.login(self.owner)
        self.goto('/experience/')
        expect(self.page.locator('.timeline-card')).to_have_count(2)
        self.assertEqual(self.page.locator('[data-search-input]').count(), 0)
        self.page.locator('[data-open-create]').click()
        dialog = self.page.locator('#experience-dialog')
        self.fill_form(dialog, {'title': 'Unmatched', 'description': 'Saved', 'category': 'volunteer', 'company': 'Other'})
        dialog.locator('[type=submit]').click()
        expect(dialog).not_to_be_visible()
        expect(self.page.locator('.timeline-card:visible')).to_have_count(3)
        self.assertTrue(any(item['fields']['title'] == 'Unmatched' for item in
                            self.page.request.get(self.live_server_url + '/api/experience/').json()))
        self.goto('/projects/')
        expect(self.page.locator('#grid h2')).to_have_text('Portfolio')
        self.page.locator('.star-form [type=submit]').click()
        expect(self.page.locator('.star-count')).to_have_text('1')
        expect(self.page.locator('.star-label')).to_have_text('Unstar')
        self.page.locator('.star-form [type=submit]').click()
        expect(self.page.locator('.star-count')).to_have_text('0')
        expect(self.page.locator('.star-label')).to_have_text('Star')
        self.page.locator('[data-resource-action="delete"]').click()
        self.page.locator('#projects-delete-dialog [data-confirm-delete]').click()
        expect(self.page.locator('#empty')).to_be_visible()
        self.assertEqual(self.page.request.get(self.live_server_url + '/api/projects/').json(), [])

    def test_regular_user_can_read_but_cannot_manage(self):
        from playwright.sync_api import expect
        self.login(self.regular)
        for path in ('/experience/', '/skills/', '/'):
            self.goto(path)
            expect(self.page.locator('[data-list]').first).to_be_visible()
            self.assertEqual(self.page.locator('[data-open-create], [data-resource-action]').count(), 0)
        response = self.page.goto(self.live_server_url + '/dashboard/', wait_until='domcontentloaded')
        self.assertEqual(response.status, 403)

    def test_delayed_response_never_replaces_new_search(self):
        from playwright.sync_api import expect
        self.login(self.owner)
        self.goto('/dashboard/')
        root = self.page.locator('[data-dashboard-resource][data-resource="experience"]')
        expect(root.locator('tbody tr')).to_have_count(2)
        self.page.evaluate('''() => {
            const original = window.fetch;
            window.fetch = (url, options) => {
                if (new URL(url, location.origin).searchParams.get('q') !== 'Acme') return original(url, options);
                return original(url, { ...options, signal: undefined }).then(response => {
                    window.slowResponseReady = true;
                    return new Promise(resolve => setTimeout(() => resolve(response), 1200));
                });
            };
        }''')
        search = root.locator('[data-search-input]')
        search.fill('Acme')
        self.page.wait_for_function('window.slowResponseReady === true')
        search.fill('School')
        expect(root.locator('tbody tr:visible')).to_have_count(1)
        expect(root.locator('tbody')).to_contain_text('Tutor')
        self.page.wait_for_timeout(1400)
        expect(root.locator('tbody tr:visible')).to_have_count(1)
        expect(root.locator('tbody')).to_contain_text('Tutor')

    def test_projects_keyboard_retry_preserves_search_category_and_loading_status(self):
        from playwright.sync_api import expect
        self.context.route('**/api/projects/**', lambda route: route.fulfill(
            status=503, content_type='text/html', body='<h1>Unavailable</h1>'))
        self.goto('/projects/?title=Port&category=Web')
        expect(self.page.locator('#error')).to_be_visible()
        expect(self.page.locator('#error')).to_have_attribute('role', 'alert')
        self.context.unroute('**/api/projects/**')
        self.page.evaluate('''() => {
            const original = window.fetch;
            window.fetch = (url, options) => {
                if (new URL(url, location.origin).pathname !== '/api/projects/') return original(url, options);
                return new Promise(resolve => {
                    window.releaseProjects = () => resolve(original(url, options));
                });
            };
        }''')
        retry = self.page.locator('[data-projects-retry]')
        retry.focus()
        retry.press('Enter')
        expect(self.page.locator('#loading')).to_be_visible()
        expect(self.page.locator('#loading')).to_have_attribute('role', 'status')
        expect(self.page.locator('#grid')).to_have_attribute('aria-busy', 'true')
        self.page.wait_for_function('typeof window.releaseProjects === "function"')
        self.page.evaluate('window.releaseProjects()')
        expect(self.page.locator('#grid h2')).to_have_text('Portfolio')
        expect(self.page.locator('#grid')).to_have_attribute('aria-busy', 'false')
        expect(self.page.locator('#search-input')).to_have_value('Port')
        expect(self.page.locator('[data-filter="Web"]')).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#search-input')).to_be_focused()

    def test_modal_keyboard_inline_errors_and_focus_return(self):
        from playwright.sync_api import expect
        self.login(self.owner)
        self.goto('/experience/')
        expect(self.page.locator('.timeline-card')).to_have_count(2)
        opener = self.page.locator('[data-open-create]')
        opener.focus()
        opener.press('Enter')
        dialog = self.page.locator('#experience-dialog')
        title = dialog.locator('[name="title"]')
        expect(title).to_be_focused()
        first = dialog.locator('[data-close-dialog]').first
        last = dialog.locator('[type=submit]')
        last.focus()
        self.page.keyboard.press('Tab')
        expect(first).to_be_focused()
        self.page.keyboard.press('Shift+Tab')
        expect(last).to_be_focused()
        self.fill_form(dialog, {'title': '<b></b>', 'description': 'Saved', 'company': 'Acme'})
        last.click()
        error = title.locator('xpath=..').locator('[data-field-error]')
        expect(error).to_be_visible()
        expect(title).to_have_attribute('aria-invalid', 'true')
        self.assertIn(error.get_attribute('id'), title.get_attribute('aria-describedby').split())
        expect(title).to_be_focused()
        expect(dialog.locator('[data-toast-announcement]')).to_contain_text('Gagal menyimpan')
        title.fill('Corrected')
        expect(error).not_to_be_visible()
        self.assertIsNone(title.get_attribute('aria-invalid'))
        self.page.keyboard.press('Escape')
        expect(dialog).not_to_be_visible()
        expect(opener).to_be_focused()
        edit = self.page.locator('[data-resource-action="edit"]').first
        edit.focus()
        edit.press('Enter')
        expect(title).to_be_focused()
        self.page.keyboard.press('Escape')
        expect(dialog).not_to_be_visible()
        expect(edit).to_be_focused()
        delete = self.page.locator('[data-resource-action="delete"]').first
        delete.focus()
        delete.press('Enter')
        confirmation = self.page.locator('#experience-delete-dialog')
        cancel = confirmation.locator('[data-close-delete][autofocus]')
        expect(cancel).to_be_focused()
        self.page.keyboard.press('Escape')
        expect(confirmation).not_to_be_visible()
        expect(delete).to_be_focused()

    def test_contact_inline_validation_and_repeated_safe_toast_announcements(self):
        from playwright.sync_api import expect
        from main.models import ContactMessage
        self.goto('/')
        form = self.page.locator('#contact-form')
        name = form.locator('[name="name"]')
        name.fill('<b></b>')
        form.locator('[name="email"]').fill('visitor@example.com')
        form.locator('[name="message"]').fill('Hello')
        form.locator('[type=submit]').click()
        error = form.locator('#id_name_error')
        expect(error).to_be_visible()
        expect(name).to_have_attribute('aria-invalid', 'true')
        self.assertIn('id_name_error', name.get_attribute('aria-describedby').split())
        expect(name).to_be_focused()
        self.assertEqual(self.database_call(ContactMessage.objects.count), 0)
        name.fill('Visitor')
        expect(error).not_to_be_visible()
        self.assertIsNone(name.get_attribute('aria-invalid'))
        with self.page.expect_response(lambda response: response.url == self.live_server_url + '/'
                                       and response.request.method == 'POST') as saved:
            form.locator('[type=submit]').click()
        self.assertEqual(saved.value.status, 200, saved.value.text())
        self.assertEqual(saved.value.json()['status'], 'success')
        expect(name).to_have_value('')
        expect(self.page.locator('#toast-announcement')).to_contain_text('Pesan terkirim')
        self.assertEqual(self.database_call(ContactMessage.objects.count), 1)
        name.focus()
        self.page.evaluate('''() => {
            const region = document.getElementById('toast-announcement');
            window.announcements = [];
            new MutationObserver(() => {
                if (region.textContent) window.announcements.push(region.textContent);
            }).observe(region, { childList: true });
            window.showToast('Info', '<img src=x onerror=alert(1)>', 'normal', 5000);
        }''')
        region = self.page.locator('#toast-announcement')
        expect(region).to_have_text('Info. <img src=x onerror=alert(1)>')
        expect(region).to_have_attribute('role', 'status')
        expect(region).to_have_attribute('aria-live', 'polite')
        expect(region).to_have_attribute('aria-atomic', 'true')
        self.assertEqual(self.page.locator('#toast-message img, #toast-announcement img').count(), 0)
        self.page.evaluate("window.showToast('Info', '<img src=x onerror=alert(1)>', 'normal', 5000)")
        self.page.wait_for_function('window.announcements.length === 2')
        expect(name).to_be_focused()
