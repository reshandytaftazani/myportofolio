"""Regressions for stars surviving Experience list replacement."""
import importlib.util
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from main import test_resource_browser as browser_tests


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt for browser checks.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'])
class ExperienceQualityTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto
    login = browser_tests.ResourceBrowserTests.login

    def check_star_refresh(self, succeeds, list_first):
        from playwright.sync_api import expect

        self.login(self.regular)
        self.page.set_viewport_size({'width': 1440 if succeeds else 390, 'height': 900})
        self.page.emulate_media(reduced_motion='reduce')
        self.goto('/experience/')
        root = self.page.locator('#experience')
        expect(root.locator('.timeline-card')).to_have_count(2)
        self.page.evaluate('window.qualityDocumentMarker = true')
        button = root.locator('.timeline-card').filter(has_text='Developer').locator('[data-action=star]')
        star_url = button.locator('xpath=..').get_attribute('action')
        pending_stars, pending_lists = [], []
        self.context.route('**/api/v1/experiences/*/star/', lambda route: pending_stars.append(route))
        source = self.page.request.get(self.live_server_url + '/api/v1/experiences/').json()
        self.context.route('**/api/v1/experiences/', lambda route: pending_lists.append(route))
        with self.page.expect_request(lambda r: r.method == 'POST' and r.url.endswith(star_url)):
            button.click()
        expect(button).to_have_attribute('aria-pressed', 'true')
        expect(self.page.locator('#metric-total-stars')).to_have_text('1')
        old_button = button.element_handle()
        with self.page.expect_request(lambda r: r.method == 'GET' and r.url.endswith('/api/v1/experiences/')):
            self.page.locator('#experience-search-form').evaluate('form => form.requestSubmit()')
        expect(root.locator('[data-list]')).to_have_attribute('aria-busy', 'true')

        def release_list():
            self.assertEqual(len(pending_lists), 1)
            pending_lists.pop().fulfill(json=source)
            self.page.wait_for_function('(button) => !button.isConnected', arg=old_button)

        def release_star():
            self.assertEqual(len(pending_stars), 1)
            held = pending_stars.pop()
            if succeeds:
                held.fulfill(response=held.fetch())
                expect(self.page.locator('#toast-message')).to_contain_text('Star berhasil diberikan')
            else:
                held.fulfill(status=500, json={'detail': 'Controlled server failure'})
                expect(self.page.locator('#toast-message')).to_contain_text('Perubahan dibatalkan')

        if list_first:
            release_list()
            expect(button).to_have_attribute('aria-pressed', 'true')
            expect(button.locator('.star-count')).to_have_text('1')
            # Replacing a card must not unlock another mutation for the same record.
            button.evaluate('button => { button.click(); button.click(); }')
            release_star()
        else:
            release_star()
            release_list()
        expected_count = '1' if succeeds else '0'
        expect(button).to_have_attribute('aria-pressed', str(succeeds).lower())
        expect(button.locator('.star-count')).to_have_text(expected_count)
        expect(self.page.locator('#metric-total-stars')).to_have_text(expected_count)
        self.assertEqual(self.page.evaluate('window.qualityDocumentMarker'), True)
        self.context.unroute('**/api/v1/experiences/')
        self.context.unroute('**/api/v1/experiences/*/star/')
        persisted = self.page.request.get(self.live_server_url + star_url.removesuffix('star/')).json()
        self.assertEqual(persisted['star_count'], int(succeeds))
        self.assertEqual(persisted['is_starred'], succeeds)
        # Settlement must also unlock the replacement card for a later user action.
        with self.page.expect_response(lambda r: r.request.method == 'POST' and r.url.endswith(star_url)) as response:
            button.click()
        self.assertEqual(response.value.status, 200)
        expect(button).to_have_attribute('aria-pressed', str(not succeeds).lower())
        expect(button.locator('.star-count')).to_have_text(str(int(not succeeds)))
        expect(self.page.locator('#metric-total-stars')).to_have_text(str(int(not succeeds)))

    def test_filtered_metrics_explain_their_scope(self):
        from playwright.sync_api import expect

        self.goto('/experience/')
        expect(self.page.locator('#metric-total-roles')).to_have_text('2')
        self.page.locator('#experience-search-input').fill('Developer')
        self.page.locator('#experience-search-form').evaluate('form => form.requestSubmit()')
        expect(self.page.locator('#experience .timeline-card')).to_have_count(1)
        expect(self.page.locator('#metric-total-roles')).to_have_text('1')
        expect(self.page.locator('#experience-metrics')).to_contain_text('Ringkasan hasil filter')

    def test_confirmation_updates_replaced_card_and_metrics(self):
        self.check_star_refresh(succeeds=True, list_first=True)

    def test_rollback_updates_replaced_card_and_metrics(self):
        self.check_star_refresh(succeeds=False, list_first=True)

    def test_old_list_response_cannot_undo_confirmed_star(self):
        self.check_star_refresh(succeeds=True, list_first=False)

    def test_old_list_response_cannot_undo_rollback(self):
        self.check_star_refresh(succeeds=False, list_first=False)
