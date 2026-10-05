"""Header navigation and material changes in the real desktop window shell."""
import importlib.util
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from main import test_resource_browser as browser_tests


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'])
class HeaderBrowserTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto

    def prepare(self, width=390):
        self.page.set_viewport_size({'width': width, 'height': 844})
        self.goto('/')
        self.page.wait_for_function('document.body.hasAttribute("data-desktop-ready")')

    def test_compact_menu_keyboard_navigation_and_outside_dismissal(self):
        from playwright.sync_api import expect
        self.prepare()
        menu = self.page.locator('.desktop-window-menu')
        summary = menu.locator('summary')
        summary.focus()
        self.page.keyboard.press('Enter')
        expect(menu).to_have_attribute('open', '')
        expect(menu.locator('nav a')).to_have_count(7)
        self.page.keyboard.press('Tab')
        expect(menu.get_by_role('link', name='About', exact=True)).to_be_focused()
        self.page.keyboard.press('Escape')
        expect(summary).to_be_focused()
        expect(menu).not_to_have_attribute('open', '')
        summary.click()
        menu.get_by_role('link', name='Projects', exact=True).click()
        expect(self.page.locator('#projects')).to_be_visible()
        expect(menu).not_to_have_attribute('open', '')
        summary.click()
        self.page.locator('[data-theme-toggle]').click()
        expect(menu).not_to_have_attribute('open', '')

    def test_glass_tracks_page_and_active_window_scroll_and_reduced_motion(self):
        from playwright.sync_api import expect
        self.prepare()
        header = self.page.locator('.desktop-menubar')
        expect(header).not_to_have_attribute('data-header-scrolled', '')
        self.page.evaluate('window.scrollTo(0, 120)')
        expect(header).to_have_attribute('data-header-scrolled', '')
        self.page.evaluate('window.scrollTo(0, 0)')
        expect(header).not_to_have_attribute('data-header-scrolled', '')
        self.page.set_viewport_size({'width': 1440, 'height': 700})
        self.page.locator('[data-dock-id="about"]').click()
        self.page.wait_for_function('!document.querySelector("[data-window-motion]")')
        self.page.locator('#about > .container').evaluate('el => el.scrollTop = 120')
        expect(header).to_have_attribute('data-header-scrolled', '')
        self.page.locator('[data-dock-id="contact"]').click()
        expect(header).not_to_have_attribute('data-header-scrolled', '')
        self.page.emulate_media(reduced_motion='reduce')
        self.page.locator('[data-dock-id="about"]').click()
        expect(header).to_have_attribute('data-header-scrolled', '')
        self.assertLessEqual(header.evaluate('el => parseFloat(getComputedStyle(el).transitionDuration)'), .01)

    def test_header_and_intro_fit_supported_widths_and_native_menu_without_scripts(self):
        from playwright.sync_api import expect
        self.prepare()
        for width in (320, 390, 768, 901, 1100, 1101, 1199, 1440, 1920):
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'), width)
            self.assertTrue(self.page.locator('.desktop-menubar').evaluate('''el => {
                const box = el.getBoundingClientRect();
                return [...el.querySelectorAll('a,button,summary,time')].every(node => {
                    if (!node.getClientRects().length || node.closest('.desktop-menu-panel,.user-dropdown-content')) return true;
                    const r = node.getBoundingClientRect();
                    return r.left >= box.left && r.right <= box.right && r.bottom <= box.bottom;
                });
            }'''), width)
        self.context.close()
        self.context = self.browser.new_context(java_script_enabled=False, viewport={'width':390, 'height':844})
        self.page = self.context.new_page()
        self.page.goto(self.live_server_url)
        self.page.locator('.desktop-window-menu summary').click()
        # The native disclosure and real URLs also work before desktop boot.
        # Window utilities are hidden without boot, so ordinary server content remains available.
        expect(self.page.locator('.desktop-introduction')).to_be_visible()
        self.page.locator('.desktop-compact-links').get_by_role('link', name='Projects', exact=True).click()
        self.assertTrue(self.page.url.endswith('/projects/'))
        expect(self.page.locator('#projects')).to_be_visible()

    def test_long_account_button_and_dropdown_stay_inside_header(self):
        from playwright.sync_api import expect
        self.owner.username = 'portfolio-owner-with-a-long-account-name'
        browser_tests.ResourceBrowserTests.database_call(self, lambda: self.owner.save(update_fields=['username']))
        self.context.add_cookies([{'name': 'sessionid', 'value': self.session_cookies[self.owner.pk],
                                  'url': self.live_server_url}])
        self.prepare()
        button = self.page.locator('.desktop-menubar .user-btn')
        panel = self.page.locator('#desktop-account-menu')
        for width in (320, 360, 390, 768, 1100, 1101, 1360, 1361, 1440, 1920):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 900})
                self.assertTrue(button.evaluate('''el => {
                    const header = el.closest('header').getBoundingClientRect();
                    const r = el.getBoundingClientRect();
                    const chevron = el.querySelector('svg').getBoundingClientRect();
                    return r.left >= header.left + 16 && r.right <= header.right - 16
                        && r.width >= 44 && r.height >= 44 && chevron.right <= r.right;
                }'''), width)
                button.click()
                expect(button).to_have_attribute('aria-expanded', 'true')
                expect(panel.get_by_role('link', name='Dashboard')).to_be_visible()
                self.assertTrue(panel.evaluate('''el => {
                    const r = el.getBoundingClientRect();
                    return r.left >= 16 && r.right <= innerWidth - 16;
                }'''), width)
                self.page.keyboard.press('Tab')
                expect(panel.get_by_role('link', name='Dashboard')).to_be_focused()
                self.page.keyboard.press('Escape')
                expect(button).to_be_focused()
                expect(button).to_have_attribute('aria-expanded', 'false')
                expect(panel).not_to_be_visible()
                self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'), width)
