"""Dock motion, navigation state and input alternatives in the real shell."""
import importlib.util
from pathlib import Path
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from main import test_resource_browser as browser_tests


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'])
class DockBrowserTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto

    def prepare(self, width=1440, height=900):
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        self.context.route('https://cdnjs.cloudflare.com/**', lambda route: route.abort())
        self.page.set_viewport_size({'width': width, 'height': height})
        self.goto('/')
        self.page.wait_for_function('document.body.hasAttribute("data-desktop-ready")')
        self.dock = self.page.locator('.desktop-dock')

    def settle(self):
        self.page.wait_for_function('!document.querySelector("[data-dock-animating], [data-window-motion]")')

    def capture(self, name):
        output = Path('Planning/qa/impeccable/artifacts/dock')
        output.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(output / name))

    def test_pointer_magnifies_neighbors_without_overlap_and_returns_to_rest(self):
        self.prepare()
        # App and external icon rows share the same baseline.
        boxes = self.dock.locator('.dock-icon').evaluate_all('nodes => nodes.map(n => n.getBoundingClientRect().top)')
        self.assertLess(max(boxes) - min(boxes), .1)
        colors = self.dock.locator('.dock-icon').evaluate_all('nodes => nodes.map(n => getComputedStyle(n).color)')
        self.assertGreaterEqual(len(set(colors)), 7)
        self.assertEqual(colors[6], colors[9])  # Contact and Email share the mail tile.
        projects = self.dock.locator('[data-dock-id="projects"]')
        projects.hover()
        self.settle()
        widths = self.dock.locator('.dock-icon').evaluate_all('nodes => nodes.map(n => n.getBoundingClientRect().width)')
        self.assertGreater(widths[3], 68)
        self.assertGreater(widths[2], 48)
        self.assertLess(widths[2], widths[3])
        self.assertTrue(self.dock.locator('.dock-icon').evaluate_all('''nodes => {
            const boxes = nodes.map(n => n.getBoundingClientRect());
            return boxes.slice(1).every((box, i) => box.left - boxes[i].right >= 7);
        }'''))
        label = projects.locator('.dock-label')
        self.assertLess(label.bounding_box()['y'] + label.bounding_box()['height'], projects.locator('.dock-icon').bounding_box()['y'])
        self.capture('after-desktop-hover.png')
        # External links receive the same motion, including the far-right edge.
        self.dock.locator('[data-dock-link="cv"]').hover()
        self.settle()
        self.assertGreater(self.dock.locator('[data-dock-link="cv"] .dock-icon').bounding_box()['width'], 68)
        self.page.mouse.move(20, 200)
        self.settle()
        self.assertAlmostEqual(projects.locator('.dock-icon').bounding_box()['width'], 48, places=1)
        projects.hover()
        self.page.evaluate('window.dispatchEvent(new Event("blur"))')
        self.assertFalse(self.dock.get_attribute('data-dock-animating'))
        self.assertAlmostEqual(projects.locator('.dock-icon').bounding_box()['width'], 48, places=1)

    def test_separator_stays_between_contact_and_github_during_magnification(self):
        self.prepare()
        divider = self.dock.locator('.dock-divider')
        resting_x = divider.bounding_box()['x']
        self.page.evaluate('''() => {
            window.separatorSamples = [];
            window.trackSeparator = true;
            let remaining = 300;
            function sample() {
                const divider = document.querySelector('.dock-divider').getBoundingClientRect();
                const contact = document.querySelector('[data-dock-id="contact"] .dock-icon').getBoundingClientRect();
                const github = document.querySelector('[data-dock-link="github"] .dock-icon').getBoundingClientRect();
                window.separatorSamples.push([divider.left - contact.right, github.left - divider.right]);
                if (window.trackSeparator && --remaining > 0) requestAnimationFrame(sample);
            }
            sample();
        }''')
        self.page.evaluate('document.documentElement.dataset.theme = "dark"')
        for selector in ('[data-dock-id="contact"]', '[data-dock-link="github"]',
                         '[data-dock-link="linkedin"]', '[data-dock-id="projects"]'):
            self.dock.locator(selector).hover()
            self.settle()
            if 'contact' in selector:
                self.assertGreater(divider.bounding_box()['x'], resting_x + 1)
                self.capture('separator-contact-hover.png')
            if 'github' in selector:
                self.assertLess(divider.bounding_box()['x'], resting_x - 1)
                self.capture('separator-github-hover.png')
        self.page.mouse.move(20, 200)
        self.settle()
        self.page.evaluate('window.trackSeparator = false')
        samples = self.page.evaluate('window.separatorSamples')
        self.assertGreater(len(samples), 10)
        self.assertGreaterEqual(min(gap for sample in samples for gap in sample), 12)
        self.assertAlmostEqual(divider.bounding_box()['x'], resting_x, places=1)
        # Preference changes clear the separator's motion alongside the icons.
        self.dock.locator('[data-dock-id="contact"]').hover()
        self.settle()
        self.page.emulate_media(reduced_motion='reduce')
        self.assertAlmostEqual(divider.bounding_box()['x'], resting_x, places=1)
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.assertFalse(divider.is_visible())
        self.capture('separator-mobile.png')

    def test_tooltip_keyboard_escape_hover_and_dark_theme(self):
        from playwright.sync_api import expect
        self.prepare()
        about = self.dock.locator('[data-dock-id="about"]')
        label = about.locator('.dock-label')
        about.hover()
        self.settle()
        expect(label).to_have_css('visibility', 'visible')
        # Moving onto the label retains it, and Escape dismisses without navigation.
        label.hover()
        expect(label).to_have_css('visibility', 'visible')
        self.page.keyboard.press('Escape')
        expect(label).to_have_css('visibility', 'hidden')
        self.page.mouse.move(20, 200)
        self.page.keyboard.press('Tab')
        about.focus()
        self.settle()
        expect(label).to_have_css('visibility', 'visible')
        self.page.keyboard.press('Escape')
        expect(about).to_be_focused()
        expect(label).to_have_css('visibility', 'hidden')
        self.page.keyboard.press('Tab')
        experience = self.dock.locator('[data-dock-id="experience"]')
        expect(experience).to_be_focused()
        expect(experience.locator('.dock-label')).to_have_css('visibility', 'visible')
        self.page.evaluate('document.documentElement.dataset.theme = "dark"')
        self.settle()
        self.capture('after-desktop-dark-keyboard.png')
        self.page.keyboard.press('Enter')
        expect(self.page.locator('#experience')).to_have_attribute('data-window-active', '')

    def test_running_active_minimized_and_closed_indicators_follow_windows(self):
        from playwright.sync_api import expect
        self.prepare()
        about = self.dock.locator('[data-dock-id="about"]')
        projects = self.dock.locator('[data-dock-id="projects"]')
        expect(about.locator('.dock-indicator')).to_have_css('opacity', '0')
        about.click()
        self.settle()
        projects.click()
        self.settle()
        expect(about).to_have_attribute('data-running', '')
        expect(about.locator('.dock-indicator')).to_have_css('opacity', '1')
        expect(projects).to_have_attribute('aria-current', 'location')
        expect(projects).to_have_attribute('aria-description', 'Jendela aktif')
        self.assertNotEqual(about.locator('.dock-indicator').evaluate('n => getComputedStyle(n).backgroundColor'),
                            projects.locator('.dock-indicator').evaluate('n => getComputedStyle(n).backgroundColor'))
        self.page.locator('#projects [data-window-action="minimize"]').click()
        self.settle()
        expect(projects).to_have_attribute('data-running', '')
        expect(projects).to_have_attribute('data-window-state', 'minimized')
        expect(about).to_have_attribute('aria-current', 'location')
        expect(projects).to_have_attribute('aria-description', 'Jendela diminimalkan')
        projects.click()
        self.settle()
        expect(projects).to_have_attribute('aria-current', 'location')
        self.page.locator('#projects [data-window-action="close"]').click()
        self.settle()
        expect(projects).not_to_have_attribute('data-running', '')
        expect(projects.locator('.dock-indicator')).to_have_css('opacity', '0')
        self.page.mouse.move(20, 200)
        self.capture('after-desktop-running.png')

    def test_mobile_scroll_touch_reduced_motion_and_no_script_navigation(self):
        from playwright.sync_api import expect
        self.prepare()
        for width in (320, 390, 768, 900, 901, 1199, 1440):
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'), width)
            box = self.dock.bounding_box()
            self.assertGreaterEqual(box['x'], 12)
            self.assertLessEqual(box['x'] + box['width'], width - 12)
        self.page.emulate_media(reduced_motion='reduce')
        projects = self.dock.locator('[data-dock-id="projects"]')
        projects.hover()
        expect(projects.locator('.dock-label')).to_have_css('visibility', 'visible')
        expect(projects.locator('.dock-icon')).to_have_css('transform', 'none')
        projects.click()
        expect(projects).to_have_attribute('aria-current', 'location')
        self.page.set_viewport_size({'width': 390, 'height': 844})
        expect(projects.locator('.dock-label')).to_have_css('transform', 'none')
        self.capture('after-mobile-reduced.png')
        self.context.close()
        self.context = self.browser.new_context(has_touch=True, is_mobile=True, viewport={'width': 320, 'height': 760})
        self.page = self.context.new_page()
        self.goto('/')
        self.page.wait_for_function('document.body.hasAttribute("data-desktop-ready")')
        self.dock = self.page.locator('.desktop-dock')
        self.capture('after-mobile-touch.png')
        contact = self.dock.locator('[data-dock-id="contact"]')
        contact.scroll_into_view_if_needed()
        contact.tap()
        expect(self.page.locator('#contact')).to_be_visible()
        self.assertGreaterEqual(contact.bounding_box()['width'], 44)
        self.assertGreaterEqual(contact.bounding_box()['height'], 44)
        expect(contact.locator('.dock-icon')).to_have_css('transform', 'matrix(1, 0, 0, 1, 0, 0)')
        self.context.close()
        self.context = self.browser.new_context(java_script_enabled=False, viewport={'width': 1440, 'height': 900})
        self.page = self.context.new_page()
        self.goto('/')
        self.page.locator('[data-dock-id="projects"]').click()
        self.assertTrue(self.page.url.endswith('/projects/'))
        expect(self.page.locator('#projects')).to_be_visible()
