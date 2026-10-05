"""Multiple-window behavior using real browser input and an isolated database."""
import importlib.util
from pathlib import Path
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import TestCase, override_settings
from main import test_resource_browser as browser_tests


class MultipleWindowHTMLTests(TestCase):
    def test_every_public_document_has_one_instance_of_each_app(self):
        for route in ('/', '/projects/', '/skills/', '/experience/'):
            response = self.client.get(route)
            for app in ('about', 'education', 'tech-stack', 'contact', 'projects', 'skills', 'experience'):
                self.assertContains(response, f'data-window-id="{app}"', count=1)
            self.assertContains(response, 'js/public-resources.js', count=1)
            self.assertContains(response, 'js/projects.js', count=1)
            self.assertContains(response, 'id="contact-form"', count=1)


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class MultipleWindowBrowserTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto
    login = browser_tests.ResourceBrowserTests.login

    def prepare(self, width=1440, height=900):
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        self.context.route('https://cdnjs.cloudflare.com/**', lambda route: route.abort())
        self.page.set_viewport_size({'width': width, 'height': height})
        self.goto('/')
        self.page.wait_for_function('document.body.hasAttribute("data-desktop-ready")')

    def settle(self):
        self.page.wait_for_function('!document.querySelector("[data-window-motion]")')

    def open(self, app):
        self.page.locator(f'[data-dock-id="{app}"]').click()
        self.settle()

    def drag_to(self, app, x, y, release=True):
        rect = self.page.locator(f'#win-title-{app}').bounding_box()
        self.page.mouse.move(rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2)
        self.page.mouse.down()
        self.page.mouse.move(x, y, steps=12)
        if release:
            self.page.mouse.up()
            self.settle()

    def test_concurrent_apps_stack_limit_focus_history_and_query_isolation(self):
        from playwright.sync_api import expect
        self.prepare()
        self.page.evaluate('window.multiwindowDocument = true')
        for app in ('about', 'projects', 'skills', 'experience', 'education'):
            self.open(app)
        self.assertEqual(self.page.locator('[data-window-id]:visible').count(), 5)
        self.open('contact')
        expect(self.page.locator('#contact')).to_be_hidden()
        expect(self.page.locator('[data-window-announcement]')).to_contain_text('minimalkan')
        self.page.locator('#education [data-window-action="minimize"]').click()
        self.settle()
        self.open('contact')
        self.assertTrue(self.page.evaluate('window.multiwindowDocument'))
        self.assertEqual(self.page.locator('[data-window-id]:visible').count(), 5)
        expect(self.page.locator('#contact')).to_have_attribute('data-window-active', '')
        # Simulate an archived destination: minimize replaces the immediately current
        # history entry, so a previously minimized app needs an older saved URL.
        self.page.evaluate('''() => {
            history.pushState({desktop:1, active:'education'}, '', '/#education');
            history.pushState({desktop:1, active:'contact'}, '', '/#contact');
        }''')
        self.page.go_back(); self.settle()
        expect(self.page.locator('#education')).to_have_attribute('data-window-active', '')
        self.assertEqual(self.page.locator('[data-window-id]:visible').count(), 5)
        self.page.go_forward(); self.settle()
        expect(self.page.locator('#contact')).to_have_attribute('data-window-active', '')
        self.assertEqual(self.page.locator('[data-window-id]:visible').count(), 5)
        self.open('projects')
        self.page.locator('#search-input').fill('Portfolio')
        self.page.wait_for_url('**/projects/?title=Portfolio')
        self.open('skills')
        self.page.locator('#skills .window-titlebar h2').focus()
        expect(self.page.locator('#skills')).to_have_attribute('data-window-active', '')
        expect(self.page).to_have_url(self.live_server_url + '/skills/')
        self.page.go_back()
        expect(self.page.locator('#projects')).to_have_attribute('data-window-active', '')
        expect(self.page.locator('#search-input')).to_have_value('Portfolio')
        self.assertTrue(self.page.evaluate('window.multiwindowDocument'))
        self.assertLess(int(self.page.locator('#projects').evaluate('el => getComputedStyle(el).zIndex')), 1000)

    def test_drag_snap_interruptions_keyboard_and_reduced_motion(self):
        from playwright.sync_api import expect
        self.prepare()
        self.open('projects')
        self.drag_to('projects', 12, 240, release=False)
        expect(self.page.locator('.window-snap-preview')).to_have_attribute('data-snap', 'left')
        self.page.mouse.up(); self.settle()
        expect(self.page.locator('#projects')).to_have_attribute('data-window-snap', 'left')
        self.open('experience')
        self.drag_to('experience', 1428, 240)
        expect(self.page.locator('#experience')).to_have_attribute('data-window-snap', 'right')
        self.assertLessEqual(self.page.locator('#projects').bounding_box()['x'] + self.page.locator('#projects').bounding_box()['width'], self.page.locator('#experience').bounding_box()['x'])
        # A second pointer cannot replace the owner; cancel/lost capture/blur all recover.
        for interrupt in ('pointercancel', 'lostpointercapture', 'blur'):
            self.drag_to('experience', 900, 300, release=False)
            self.page.evaluate('''type => {
                const handle = document.querySelector('#experience [data-window-handle]');
                handle.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, pointerId:99, isPrimary:false, clientX:10,clientY:10}));
                if (type === 'blur') window.dispatchEvent(new Event('blur'));
                else handle.dispatchEvent(new PointerEvent(type,{bubbles:true,pointerId:1}));
            }''', interrupt)
            self.page.mouse.up()
            expect(self.page.locator('[data-window-dragging]')).to_have_count(0)
            expect(self.page.locator('.window-snap-preview')).to_be_hidden()
            self.drag_to('experience', 900, 330)
            self.assertEqual(self.page.locator('#experience').evaluate('el => el.style.transform'), '')
        title = self.page.locator('#win-title-experience')
        title.focus(); self.page.keyboard.press('Alt+ArrowUp'); self.settle()
        expect(self.page.locator('#experience')).to_have_attribute('data-maximized', '')
        self.page.keyboard.press('Alt+ArrowDown'); self.settle()
        self.assertIsNone(self.page.locator('#experience').get_attribute('data-maximized'))
        self.page.emulate_media(reduced_motion='reduce')
        self.page.keyboard.press('Alt+ArrowRight')
        self.assertEqual(self.page.locator('#experience').evaluate('el => el.getAnimations().length'), 0)
        self.drag_to('experience', 950, 300, release=False)
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.mouse.up()
        expect(self.page.locator('[data-window-dragging]')).to_have_count(0)
        self.assertEqual(self.page.locator('[data-window-id]:visible').count(), 1)

    def test_mobile_state_drafts_focus_offline_and_visual_matrix(self):
        from playwright.sync_api import expect
        self.prepare(390, 844)
        self.open('contact')
        name = self.page.locator('#contact-form [name="name"]')
        name.fill('Draft preserved')
        self.page.evaluate('scrollTo(0, 160)')
        saved_scroll = self.page.evaluate('scrollY')
        self.open('skills'); self.open('contact')
        expect(name).to_have_value('Draft preserved')
        self.page.wait_for_function('(top) => Math.abs(scrollY - top) < 2', arg=saved_scroll)
        self.assertEqual(self.page.locator('[data-window-id]:visible').count(), 1)
        self.page.once('dialog', lambda dialog: dialog.dismiss())
        self.page.locator('#contact [data-window-action="close"]').click()
        expect(name).to_have_value('Draft preserved')
        self.page.once('dialog', lambda dialog: dialog.accept())
        self.page.locator('#contact [data-window-action="close"]').click(); self.settle()
        expect(self.page.locator('[data-dock-id="contact"]')).to_be_focused()
        expect(self.page.locator('.desktop-scene')).to_be_visible()
        self.page.set_viewport_size({'width':1440, 'height':900})
        self.open('about'); self.open('projects')
        # Keep other apps responsive while a resource request fails.
        self.context.route('**/api/projects/**', lambda route: route.abort())
        self.page.locator('#search-input').fill('offline')
        expect(self.page.locator('#projects #error')).to_be_visible()
        expect(self.page.locator('#grid article')).to_have_count(1)
        self.open('experience')
        expect(self.page.locator('#experience')).to_be_visible()
        output = Path('Planning/qa/multiple-window')
        output.mkdir(parents=True, exist_ok=True)
        self.page.locator('#win-title-projects').focus(); self.page.keyboard.press('Alt+ArrowLeft'); self.settle()
        self.page.locator('#win-title-experience').focus(); self.page.keyboard.press('Alt+ArrowRight'); self.settle()
        self.page.evaluate('document.fonts.ready')
        self.page.screenshot(path=str(output/'desktop-light.png'), animations='disabled')
        self.page.evaluate('document.documentElement.dataset.theme = "dark"')
        self.page.screenshot(path=str(output/'desktop-dark.png'), animations='disabled')
        for width in (320, 390, 900, 1024):
            self.page.set_viewport_size({'width':width, 'height':844})
            self.open('experience')
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'), width)
            self.assertGreaterEqual(self.page.locator('#experience [data-window-action="close"]').bounding_box()['width'], 44 if width <= 900 else 28)
            self.page.screenshot(path=str(output/f'width-{width}.png'), animations='disabled')
