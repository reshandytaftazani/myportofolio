"""Optional browser regression checks using an isolated Django test database.

Install requirements-dev.txt and a Playwright Chromium browser to run these.
Windows can also use the installed Edge or Chrome browser.
"""

import importlib.util
import os
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
        requested_browser = os.environ.get('UI_TEST_BROWSER', 'edge')
        browser_type = self.playwright.firefox if requested_browser == 'firefox' else self.playwright.chromium
        browser_paths = (
            Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'),
            Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
            Path(self.playwright.chromium.executable_path),
        )
        if requested_browser == 'firefox':
            browser_paths = (Path(browser_type.executable_path),)
        elif requested_browser == 'chrome':
            browser_paths = (browser_paths[1],)
        executable = next((str(path) for path in browser_paths if path.exists()), None)
        if executable is None:
            self.playwright.stop()
            raise unittest.SkipTest('Install the requested browser with python -m playwright install.')
        try:
            self.browser = browser_type.launch(executable_path=executable, headless=True)
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

    def test_public_lists_search_errors_retry_skills_and_code(self):
        from playwright.sync_api import expect
        self.goto('/experience/')
        expect(self.page.locator('.timeline-card')).to_have_count(2)
        expect(self.page.locator('.timeline-card').first.locator('.experience-title')).to_have_text('Developer')
        self.assertEqual(self.page.locator('.experience-desc img').count(), 0)
        self.assertEqual(self.page.locator('[data-search-input]').count(), 4)
        self.context.route('**/api/experience/**', lambda route: route.fulfill(json=[]))
        self.goto('/experience/')
        expect(self.page.locator('#experience [data-empty]')).to_be_visible()
        self.context.unroute('**/api/experience/**')
        self.context.route('**/api/experience/**', lambda route: route.abort())
        self.goto('/experience/')
        expect(self.page.locator('#experience [data-error]')).to_be_visible()
        self.context.unroute('**/api/experience/**')
        self.page.locator('#experience [data-retry]').focus()
        self.page.locator('#experience [data-retry]').press('Enter')
        expect(self.page.locator('.timeline-card:visible')).to_have_count(2)
        expect(self.page.locator('#experience [data-list]')).to_be_focused()
        expect(self.page.locator('#experience [data-list]')).to_have_attribute('aria-busy', 'false')
        expect(self.page.locator('#experience [data-loading]')).to_have_attribute('role', 'status')
        self.goto('/skills/')
        expect(self.page.locator('.tab-btn')).to_have_count(2)
        expect(self.page.locator('.tab-panel.active pre code')).to_have_text('#include <iostream>')
        expect(self.page.locator('.tab-panel.active pre code')).to_have_attribute('data-highlighted', 'yes', timeout=30000)
        self.page.get_by_role('tab', name='Math', exact=True).click()
        expect(self.page.locator('.overleaf-pdf mjx-container')).to_have_count(1, timeout=30000)
        self.assertEqual(self.page.locator('[data-search-input]').count(), 4)
        expect(self.page.locator('.tab-btn')).to_have_count(2)
        expect(self.page.locator('.tab-btn.active')).to_have_text('Math')
        self.goto('/#tech-stack')
        self.assertEqual(self.page.locator('[data-search-input]').count(), 4)
        self.goto('/#education')
        expect(self.page.locator('.timeline-school')).to_have_text('University')
        self.goto('/#tech-stack')
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
            expect(self.page.locator('#toast-component')).to_be_visible()
            expect(self.page.locator('#toast-message')).to_have_text('Data berhasil ditambahkan.')
            row = root.locator('tbody tr').filter(has_text='Browser created')
            expect(row).to_have_count(1)
            row.locator('[data-resource-action="edit"]').click()
            expect(dialog).to_be_visible()
            dialog.locator(f'[name="{title_field}"]').fill('<b></b>')
            dialog.locator('[type=submit]').click()
            expect(dialog.locator('[data-form-error]')).to_be_visible()
            expect(self.page.locator('#toast-component')).to_have_class(__import__('re').compile(r'toast-error'))
            invalid = dialog.locator(f'[name="{title_field}"]')
            expect(invalid).to_have_attribute('aria-invalid', 'true')
            expect(invalid.locator('xpath=..').locator('[data-field-error]')).to_be_visible()
            expect(dialog.locator('[type=submit]')).to_be_enabled()
            dialog.locator(f'[name="{title_field}"]').fill('Browser edited')
            dialog.locator('[type=submit]').click()
            expect(dialog).not_to_be_visible()
            expect(self.page.locator('#toast-message')).to_have_text('Data berhasil diperbarui.')
            row = root.locator('tbody tr').filter(has_text='Browser edited')
            expect(row).to_have_count(1)
            row.locator('[data-resource-action="delete"]').click()
            self.page.locator(f'#{name}-delete-dialog [data-confirm-delete]').click()
            expect(row).to_have_count(0)
            expect(self.page.locator('#toast-message')).to_have_text('Data berhasil dihapus.')
            expect(root.locator('[data-search-input]')).to_have_value('Browser')

    def test_auth_toasts_survive_redirects_and_do_not_reappear(self):
        from playwright.sync_api import expect
        password = 'Browser-login-42!'
        def set_password():
            self.regular.set_password(password)
            self.regular.save()
        self.database_call(set_password)
        self.goto('/login/?next=/experience/')
        self.page.locator('[name=username]').fill(self.regular.username)
        self.page.locator('[name=password]').fill('wrong-password')
        self.page.locator('.login-submit').click()
        expect(self.page.locator('#toast-component')).to_be_visible()
        expect(self.page.locator('#toast-message')).to_have_text('Login gagal. Periksa username dan password Anda.')
        expect(self.page.locator('.messages-container')).to_be_hidden()
        expect(self.page.locator('.form-error')).to_be_visible()
        self.page.locator('[name=password]').fill(password)
        self.page.locator('.login-submit').click()
        expect(self.page).to_have_url(self.live_server_url + '/experience/')
        expect(self.page.locator('#toast-component')).to_be_visible()
        expect(self.page.locator('#toast-message')).to_have_text('Login berhasil. Selamat datang kembali!')
        self.page.reload(wait_until='domcontentloaded')
        expect(self.page.locator('#toast-component')).to_be_hidden()
        self.goto('/logout/')
        expect(self.page.locator('#toast-component')).to_be_visible()
        expect(self.page.locator('#toast-message')).to_have_text('Logout berhasil. Anda telah keluar dari akun.')
        self.assertEqual(self.page.locator('[data-open-create]').count(), 0)
        self.page.reload(wait_until='domcontentloaded')
        expect(self.page.locator('#toast-component')).to_be_hidden()

    def test_delete_error_toast_preserves_data_and_allows_retry(self):
        from playwright.sync_api import expect
        self.login(self.owner)
        self.goto('/experience/')
        self.page.locator('#experience [data-resource-action=delete]').first.click()
        dialog = self.page.locator('#experience-delete-dialog')
        pattern = '**/api/manage/experience/*/delete/'
        self.context.route(pattern, lambda route: route.fulfill(
            status=403, json={'message': 'Anda tidak memiliki izin untuk menghapus data.'}))
        dialog.locator('[data-confirm-delete]').click()
        expect(self.page.locator('#toast-component')).to_be_visible()
        expect(self.page.locator('#toast-message')).to_have_text('Anda tidak memiliki izin untuk menghapus data.')
        expect(dialog).to_be_visible()
        expect(self.page.locator('#experience .timeline-card')).to_have_count(2)
        self.context.unroute(pattern)
        dialog.locator('[data-confirm-delete]').click()
        expect(dialog).not_to_be_visible()
        expect(self.page.locator('#toast-message')).to_have_text('Data berhasil dihapus.')
        expect(self.page.locator('#experience .timeline-card')).to_have_count(1)

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
        self.assertEqual(self.page.locator('[data-search-input]').count(), 4)
        self.page.locator('#experience [data-open-create]').click()
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
        expect(self.page.locator('#toast-message')).to_have_text('Star berhasil diberikan.')
        self.page.locator('.star-form [type=submit]').click()
        expect(self.page.locator('.star-count')).to_have_text('0')
        expect(self.page.locator('.star-label')).to_have_text('Star')
        expect(self.page.locator('#toast-message')).to_have_text('Star berhasil dibatalkan.')
        self.page.locator('[data-resource-action="delete"]').click()
        self.page.locator('#projects-delete-dialog [data-confirm-delete]').click()
        expect(self.page.locator('#empty')).to_be_visible()
        self.assertEqual(self.page.request.get(self.live_server_url + '/api/projects/').json(), [])

    def test_regular_user_can_read_but_cannot_manage(self):
        from playwright.sync_api import expect
        self.login(self.regular)
        for path, app in (('/experience/', 'experience'), ('/skills/', 'skills'), ('/#tech-stack', 'tech-stack')):
            self.goto(path)
            expect(self.page.locator(f'#{app} [data-list]')).to_be_visible()
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

    def test_public_search_debounce_stars_all_roles_and_xss_modal(self):
        from playwright.sync_api import expect
        cases = (('/experience/', 'experience', 'Acme'), ('/skills/', 'skills', 'C++'),
                 ('/#education', 'education', 'University'), ('/#tech-stack', 'tech-stack', 'Python'))
        for user in (None, self.regular, self.editor, self.owner):
            self.context.clear_cookies()
            if user:
                self.login(user)
            for route, app, query in cases:
                self.goto(route)
                root = self.page.locator(f'#{app}')
                if app == 'tech-stack':
                    root.locator('summary').first.click()
                star = root.locator('.resource-star').first
                expect(star).to_be_visible()
                if user:
                    expect(star).to_have_attribute('aria-pressed', 'false')
                    star.click()
                    expect(star).to_have_attribute('aria-pressed', 'true')
                    expect(star.locator('.resource-star-count')).to_have_text('1')
                    expect(self.page.locator('#toast-message')).to_have_text('Star berhasil diberikan.')
                    star.click()
                    expect(star).to_have_attribute('aria-pressed', 'false')
                    expect(self.page.locator('#toast-message')).to_have_text('Star berhasil dibatalkan.')
                else:
                    expect(star).to_have_attribute('href', __import__('re').compile(r'^/login/\?next='))
                    star.click()
                    expect(self.page.locator('#toast-component')).to_be_visible()
                    expect(self.page.locator('#toast-message')).to_have_text('Silakan login terlebih dahulu untuk memberi star.')
                    expect(self.page.locator('.login-submit')).to_be_visible()
                    self.goto(route)
                expect(root.locator('[data-list]')).to_be_visible()
        self.context.clear_cookies()
        self.goto('/experience/')
        root = self.page.locator('#experience')
        expect(root.locator('.timeline-card')).to_have_count(2)
        requests = []
        self.page.on('request', lambda request: requests.append(request.url)
                     if '/api/experience/?q=' in request.url else None)
        search = root.locator('[data-search-input]')
        search.fill('A')
        search.fill('Ac')
        search.fill('Acme')
        expect(root.locator('[data-loading]')).to_be_visible()
        expect(root.locator('.timeline-card')).to_have_count(1)
        expect(root.locator('.experience-company')).to_have_text('Acme')
        self.assertEqual(len(requests), 1)
        search.fill('missing')
        expect(root.locator('[data-empty]')).to_be_visible()
        self.login(self.owner)
        self.goto('/experience/')
        self.page.locator('#experience [data-open-create]').click()
        dialog = self.page.locator('#experience-dialog')
        attack = '<img src="x" onerror="alert(\'XSS!\')">'
        self.fill_form(dialog, {'title': attack, 'description': 'Safe', 'category': 'volunteer'})
        dialog.locator('[type=submit]').click()
        expect(dialog.locator('#id_experience_title_error')).to_be_visible()
        expect(self.page.locator('#toast-message')).to_contain_text('sanitasi')
        alerts = []
        self.page.on('dialog', lambda alert: (alerts.append(alert.message), alert.dismiss()))
        dialog.locator('[name=title]').fill('Safe ' + attack)
        dialog.locator('[name=description]').fill('Safe ' + attack)
        dialog.locator('[type=submit]').click()
        expect(dialog).not_to_be_visible()
        expect(self.page.locator('#experience .experience-title', has_text='Safe')).to_have_text('Safe')
        self.assertEqual(self.page.locator('#experience [onerror]').count(), 0)
        self.assertEqual(alerts, [])

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
        opener = self.page.locator('#experience [data-open-create]')
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
        self.goto('/#contact')
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

    def test_desktop_windows_history_focus_mobile_and_storage(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.page.add_init_script("localStorage.setItem('desk:icon-pos:v1', '{broken')")
        self.goto('/')
        expect(self.page.locator('.desktop-introduction')).to_be_visible()
        expect(self.page.locator('#about')).to_be_hidden()
        self.page.locator('.desktop-icon[data-app-id="about"]').click()
        expect(self.page.locator('#about')).to_be_visible()
        self.page.locator('.desktop-icon[data-app-id="contact"]').click()
        expect(self.page.locator('#contact')).to_be_visible()
        name = self.page.locator('#contact-form [name="name"]')
        name.fill('Unsaved name')
        self.page.locator('#contact [data-window-action="minimize"]').click()
        expect(self.page.locator('#contact')).to_be_hidden()
        self.page.locator('[data-dock-id="contact"]').click()
        expect(name).to_have_value('Unsaved name')
        self.page.once('dialog', lambda dialog: dialog.dismiss())
        self.page.locator('#contact [data-window-action="close"]').click()
        expect(self.page.locator('#contact')).to_be_visible()
        self.page.set_viewport_size({'width': 390, 'height': 844})
        expect(name).to_have_value('Unsaved name')
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
        self.page.once('dialog', lambda dialog: dialog.accept())
        self.page.locator('#contact [data-window-action="close"]').click()
        expect(self.page.locator('.desktop-apps')).to_be_visible()
        self.page.locator('[data-dock-id="education"]').click()
        expect(self.page.locator('#education')).to_be_visible()
        self.page.go_back()
        expect(self.page.locator('#education')).to_be_hidden()
        self.page.go_forward()
        expect(self.page.locator('#education')).to_be_visible()

    def test_window_exit_can_be_reversed_without_losing_focus_or_navigating(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.goto('/')
        icon = self.page.locator('.desktop-icon[data-app-id="about"]')
        icon.press('Enter')
        about = self.page.locator('#about')
        self.page.wait_for_function('!document.querySelector("#about").getAnimations().length')
        # One event turn deliberately reverses an exit before its completion callback.
        self.page.evaluate('''() => {
            document.querySelector('#about [data-window-action="close"]').click();
            document.querySelector('.desktop-icon[data-app-id="about"]').click();
        }''')
        self.page.wait_for_timeout(500)
        expect(about).to_be_visible()
        expect(about.locator('.window-titlebar h2')).to_be_focused()
        self.assertFalse(about.evaluate('element => element.inert'))
        self.assertEqual(about.evaluate('element => getComputedStyle(element).transform'), 'none')
        icon.press('Enter')
        self.assertEqual(about.evaluate('element => element.getAnimations().length'), 0)
        self.page.keyboard.press('Escape')
        expect(about).to_be_hidden()
        expect(icon).to_be_focused()

        self.page.locator('.desktop-icon[data-app-id="experience"]').click()
        expect(self.page).to_have_url(self.live_server_url + '/experience/')
        experience = self.page.locator('#experience')
        self.page.wait_for_function('!document.querySelector("#experience").getAnimations().length')
        self.page.evaluate('''() => {
            document.querySelector('#experience [data-window-action="close"]').click();
            document.querySelector('.desktop-icon[data-app-id="experience"]').click();
        }''')
        self.page.wait_for_timeout(500)
        expect(experience).to_be_visible()
        expect(self.page).to_have_url(self.live_server_url + '/experience/')
        self.page.keyboard.press('Escape')
        expect(self.page).to_have_url(self.live_server_url + '/')

    def test_window_reduced_motion_and_blocked_session_storage_preserve_navigation(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.emulate_media(reduced_motion='reduce')
        self.page.add_init_script('''Object.defineProperty(window, 'sessionStorage', {
            get() { throw new DOMException('Storage blocked', 'SecurityError'); }
        });''')
        self.goto('/')
        self.page.locator('.desktop-icon[data-app-id="about"]').press('Enter')
        about = self.page.locator('#about')
        expect(about).to_be_visible()
        self.assertEqual(about.evaluate('element => getComputedStyle(element).transform'), 'none')
        self.page.keyboard.press('Escape')
        self.assertTrue(about.evaluate('element => element.hidden'))
        expect(self.page.locator('.desktop-apps')).to_be_visible()
        self.page.locator('.desktop-icon[data-app-id="experience"]').press('Enter')
        expect(self.page.locator('#experience')).to_be_visible()
        expect(self.page.locator('body')).to_have_attribute('data-desktop-ready', '')
        self.assertIsNone(self.page.locator('#experience').get_attribute('data-window-motion'))
        self.assertEqual(self.page.locator('#experience').evaluate('element => getComputedStyle(element).transform'), 'none')
        self.page.keyboard.press('Escape')
        expect(self.page).to_have_url(self.live_server_url + '/')
        expect(self.page.locator('.desktop-apps')).to_be_visible()

    def test_icon_keyboard_position_reset_and_blocked_storage(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.goto('/')
        icon = self.page.locator('.desktop-icon[data-app-id="about"]')
        icon.focus()
        icon.press('Alt+ArrowRight')
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('desk:icon-pos:v1')).positions.about.col"), 2)
        self.page.reload()
        self.assertEqual(self.page.locator('[data-icon-id="about"]').evaluate('node => node.style.gridColumn'), '2')
        self.page.locator('.desktop-window-menu summary').click()
        self.page.locator('[data-reset-icons]').click()
        self.assertEqual(self.page.locator('[data-icon-id="about"]').evaluate('node => node.style.gridColumn'), '1')
        self.page.add_init_script('''Object.defineProperty(window, 'localStorage', {
            get() { throw new DOMException('Storage blocked', 'SecurityError'); }
        });''')
        self.page.reload()
        expect(self.page.locator('.desktop-introduction')).to_be_visible()
        self.page.locator('.desktop-icon[data-app-id="about"]').click()
        expect(self.page.locator('#about')).to_be_visible()
        self.page.locator('[data-theme-toggle]').click()
        expect(self.page.locator('html')).to_have_attribute('data-theme', 'dark')

    def test_server_fallback_without_js_and_when_desktop_boot_fails(self):
        from playwright.sync_api import expect
        context = self.browser.new_context(java_script_enabled=False)
        page = context.new_page()
        try:
            page.goto(self.live_server_url + '/projects/?title=Port&category=Web')
            expect(page.locator('#grid h2')).to_have_text('Portfolio')
            page.goto(self.live_server_url + '/skills/')
            self.assertIn('Aktifkan JavaScript', page.locator('#skills noscript').text_content())
            expect(page.locator('#skills [data-list]')).to_be_empty()
            page.goto(self.live_server_url + '/#contact')
            expect(page.locator('#contact-form')).to_be_visible()
        finally:
            context.close()
        # Isolate the fallback app under test. The in-memory SQLite connection
        # is shared by LiveServer request threads, so parallel unrelated reads
        # must not race this test's ORM connection.
        for resource in ('skills', 'education', 'techstack', 'projects'):
            self.context.route(f'**/api/{resource}/**', lambda route: route.fulfill(json=[]))
        self.context.route('**/js/desktop/windows.js', lambda route: route.abort())
        self.goto('/experience/')
        expect(self.page.locator('#experience [data-list]')).to_be_visible()
        self.assertFalse(self.page.locator('body').get_attribute('data-desktop-ready') is not None)
        self.context.unroute('**/js/desktop/windows.js')
        self.page.add_init_script('''(() => {
            let manager;
            Object.defineProperty(window, 'PortfolioDesktop', {
                get() { return manager; },
                set(value) {
                    const init = value.init;
                    value.init = () => { init(); throw new Error('Simulated boot failure'); };
                    manager = value;
                }
            });
        })();''')
        self.goto('/experience/')
        self.page.locator('#experience .section-title').click()
        expect(self.page.locator('#experience [data-list]')).to_be_visible()
        self.assertIsNone(self.page.locator('body').get_attribute('data-desktop-ready'))

    def test_system_mobile_navigation_does_not_extend_document(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width': 360, 'height': 900})
        self.goto('/login/')
        self.assertLessEqual(self.page.evaluate('document.body.scrollWidth'), 360)
        self.page.locator('#burger-btn').click()
        expect(self.page.locator('#nav-links')).to_be_visible()
        self.assertLessEqual(self.page.evaluate('document.body.scrollWidth'), 360)
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#nav-links')).to_be_hidden()
        self.page.locator('#theme-toggle-checkbox').focus()
        self.page.locator('#theme-toggle-checkbox').press('Space')
        expect(self.page.locator('html')).to_have_attribute('data-theme', 'dark')

    def test_mobile_intro_bio_deep_link_and_project_reset(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.goto('/#about')
        expect(self.page.locator('#about')).to_be_visible()
        self.page.wait_for_function('document.readyState === "complete"')
        titlebar = self.page.locator('#about .window-titlebar').bounding_box()
        menubar = self.page.locator('.desktop-menubar').bounding_box()
        self.assertGreaterEqual(titlebar['y'], menubar['y'] + menubar['height'])
        expect(self.page.locator('.about-bio-text')).to_be_hidden()
        self.page.locator('.about-bio summary').click()
        expect(self.page.locator('.about-bio-text')).to_contain_text('Volunteer Math Olympiad Tutor')
        self.page.locator('.about-bio summary').click()
        self.page.locator('.about-primary-actions a').first.click()
        expect(self.page.locator('#grid h2')).to_have_text('Portfolio')
        self.page.locator('[data-filter="Web"]').click()
        self.page.locator('#search-input').fill('missing')
        expect(self.page.locator('#empty')).to_be_visible()
        self.page.locator('[data-projects-reset]').click()
        expect(self.page.locator('#grid h2')).to_have_text('Portfolio')
        expect(self.page.locator('#search-input')).to_have_value('')
        expect(self.page.locator('[data-filter="all"]')).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#search-input')).to_be_focused()
        self.assertNotIn('title=', self.page.url)
        self.assertNotIn('category=', self.page.url)

    def test_desktop_visual_matrix_and_unique_ids(self):
        from playwright.sync_api import expect
        import os
        output = Path('Planning/qa/ui-revamp')
        capture = os.environ.get('UI_REVAMP_SCREENSHOTS') == '1'
        if capture:
            output.mkdir(parents=True, exist_ok=True)
        for width in (360, 1024, 1440):
            self.page.set_viewport_size({'width': width, 'height': 900})
            for theme in ('light', 'dark'):
                for route, name in (('/', 'home'), ('/projects/', 'projects'), ('/#contact', 'contact'),
                                    ('/experience/', 'experience'), ('/skills/', 'skills'),
                                    ('/login/', 'login')):
                    self.goto(route)
                    self.page.evaluate('document.fonts.ready')
                    self.page.wait_for_function('!document.querySelector("[data-window-motion]")')
                    self.page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
                    if name not in ('home', 'login'):
                        expect(self.page.locator(f'#{name}')).to_be_visible()
                    if name == 'login':
                        expect(self.page.locator('.system-window')).to_be_visible()
                    self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'), (width, theme, route))
                    duplicates = self.page.evaluate('''() => {
                        const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
                        return ids.filter((id, index) => ids.indexOf(id) !== index);
                    }''')
                    self.assertEqual(duplicates, [])
                    if capture:
                        self.page.screenshot(path=str(output / f'{name}-{width}-{theme}.png'), full_page=True, animations='disabled')
