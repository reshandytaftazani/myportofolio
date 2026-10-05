"""Plan audit regressions. StaticLiveServerTestCase always uses a separate test DB.

Set UI_AUDIT_CAPTURE=1 for evidence and UI_AUDIT_AXE_PATH to a local axe-core
script for WCAG scans. UI_TEST_BROWSER=chrome selects installed Chrome.
"""
import json
import os
import importlib.util
import unittest
from pathlib import Path
from html.parser import HTMLParser

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from main.models import Project, Skill, Education, Experience, TechStack
from main import test_desktop as desktop_tests
from main import test_resource_browser as browser_tests


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.nodes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


class ServerFormAuditTests(TestCase):
    setUpTestData = classmethod(desktop_tests.DesktopFallbackTests.setUpTestData.__func__)

    def test_edit_forms_submit_to_current_route_and_update_existing_record(self):
        from main.test_resource_ajax import ResourceAjaxTests
        cases = (
            ('projects', 'edit_project', Project, 'title'),
            ('skills', 'edit_skill', Skill, 'title'),
            ('education', 'edit_education', Education, 'school_name'),
            ('experience', 'edit_experience', Experience, 'title'),
            ('techstack', 'edit_tech_stack', TechStack, 'name'),
        )
        self.client.force_login(self.editor)
        for resource, route, model, label in cases:
            with self.subTest(resource=resource):
                item = model.objects.first()
                url = reverse('main:' + route, args=[item.pk])
                markup = Markup(self.client.get(url).content.decode())
                form = next(attrs for tag, attrs in markup.nodes if tag == 'form' and attrs.get('class') == 'project-form')
                self.assertEqual(form.get('action', url), url)
                self.assertEqual(sum(tag == 'title' for tag, _ in markup.nodes), 1)
                count = model.objects.count()
                payload = dict(ResourceAjaxTests.payloads[resource])
                payload[label] = 'Edited through server form'
                response = self.client.post(url, payload)
                self.assertEqual(response.status_code, 302)
                item.refresh_from_db()
                self.assertEqual(getattr(item, label), payload[label])
                self.assertEqual(model.objects.count(), count)

    def test_invalid_server_forms_have_resolved_error_descriptions(self):
        self.client.force_login(self.editor)
        url = reverse('main:edit_project', args=[self.project.pk])
        response = self.client.post(url, {'title': '', 'description': '', 'category': ''})
        markup = Markup(response.content.decode())
        ids = {attrs['id'] for _, attrs in markup.nodes if 'id' in attrs}
        invalid = [attrs for _, attrs in markup.nodes if attrs.get('aria-invalid') == 'true']
        self.assertTrue(invalid)
        for attrs in invalid:
            self.assertTrue(attrs.get('aria-describedby'))
            self.assertTrue(set(attrs['aria-describedby'].split()) <= ids)

    @override_settings(DEBUG=False)
    def test_system_error_pages_render_even_before_authentication(self):
        from portofolio.views import custom_500
        missing = self.client.get('/not-a-portfolio-page/')
        self.assertEqual(missing.status_code, 404)
        self.assertContains(missing, 'system-window', status_code=404)
        early_request = RequestFactory().get('/')
        error = custom_500(early_request)
        self.assertEqual(error.status_code, 500)
        self.assertContains(error, 'system-window', status_code=500)
        self.assertContains(error, 'Server Error', status_code=500)


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt for browser checks.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UIPlanBrowserTests(StaticLiveServerTestCase):
    # Reuse fixtures/launch helpers, not the existing tests themselves.
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto
    login = browser_tests.ResourceBrowserTests.login
    database_call = browser_tests.ResourceBrowserTests.database_call

    def test_project_background_refresh_does_not_shift_existing_grid(self):
        from playwright.sync_api import expect
        pending = []
        self.context.route('**/api/projects/**', lambda route: pending.append(route))
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.goto('/projects/')
        expect(self.page.locator('body')).to_have_attribute('data-desktop-ready', '')
        expect(self.page.locator('#grid')).to_have_attribute('aria-busy', 'true')
        expect(self.page.locator('#loading')).to_have_class('empty-state sr-only')
        before = self.page.locator('#grid').bounding_box()
        self.assertTrue(pending)
        pk = self.database_call(lambda: str(Project.objects.first().pk))
        pending.pop().fulfill(json=[{'pk':pk,'fields':{'title':'Portfolio','description':'Website',
                              'category':'Web','tags':[],'star_count':0,'is_starred':False}}])
        expect(self.page.locator('#grid')).to_have_attribute('aria-busy', 'false')
        after = self.page.locator('#grid').bounding_box()
        self.assertAlmostEqual(before['y'], after['y'], delta=1)

    def test_experience_cards_fill_their_timeline_column(self):
        from playwright.sync_api import expect
        for width in (768, 1024, 1440):
            self.page.set_viewport_size({'width':width,'height':900})
            self.goto('/experience/')
            card = self.page.locator('.timeline-card').first
            expect(card).to_be_visible()
            self.page.wait_for_function('!document.querySelector("[data-window-motion]")')
            expect(card.locator('.experience-title')).to_be_visible()
            bounds = card.bounding_box()
            title = card.locator('.experience-title').bounding_box()
            geometry = card.evaluate('''el => {
                const parents = [];
                for (let p=el;p && parents.length<4;p=p.parentElement) {
                    const s=getComputedStyle(p);
                    parents.push({class:p.className,width:s.width,padding:s.padding,flex:s.flex});
                }
                return parents;
            }''')
            self.assertGreaterEqual(bounds['width'], 240, (width, geometry))
            self.assertGreaterEqual(title['x'], bounds['x'])
            self.assertLessEqual(title['x'] + title['width'], bounds['x'] + bounds['width'])

    def test_system_navigation_keyboard_tablet_and_no_js_account(self):
        from playwright.sync_api import expect
        for width in (360, 768, 900, 992):
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.goto('/login/')
            expect(self.page.locator('#nav-links')).to_be_hidden()
            self.page.locator('#burger-btn').focus()
            self.page.keyboard.press('Enter')
            expect(self.page.locator('#nav-links > a').first).to_be_focused()
            self.page.keyboard.press('Escape')
            expect(self.page.locator('#burger-btn')).to_be_focused()
            expect(self.page.locator('#nav-links')).to_be_hidden()
        self.login(self.editor)
        self.goto('/dashboard/')
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.page.locator('[data-dashboard-tab]').first.focus()
        self.page.keyboard.press('ArrowDown')
        expect(self.page.locator('[data-dashboard-tab]').nth(1)).to_be_focused()
        expect(self.page.locator('.dashboard-tabs')).to_have_attribute('aria-orientation', 'vertical')
        context = self.browser.new_context(java_script_enabled=False, viewport={'width': 360, 'height': 900})
        context.add_cookies([{'name': 'sessionid', 'value': self.session_cookies[self.editor.pk], 'url': self.live_server_url}])
        page = context.new_page()
        try:
            for route in ('/login/', '/projects/'):
                page.goto(self.live_server_url + route)
                expect(page.locator('.user-dropdown-logout, .user-dropdown-content a[href="/logout/"]').last).to_be_visible()
                expect(page.locator('.user-dropdown-content a[href="/dashboard/"]').last).to_be_visible()
                self.assertLessEqual(page.evaluate('document.body.scrollWidth'), 360)
        finally:
            context.close()

    def test_libraries_unavailable_and_pointer_cancel_preserve_content(self):
        from playwright.sync_api import expect
        self.context.route('**/mathjax@*/**', lambda route: route.abort())
        self.context.route('**/highlight.js/**', lambda route: route.abort())
        self.goto('/skills/')
        expect(self.page.locator('.tab-panel.active pre code')).to_have_text('#include <iostream>')
        self.page.get_by_role('tab', name='Math', exact=True).click()
        expect(self.page.locator('.tab-panel.active pre code')).to_contain_text(r'\begin{aligned}')
        self.page.set_viewport_size({'width': 1440, 'height': 900})
        self.page.emulate_media(reduced_motion='reduce')
        self.goto('/#about')
        self.assertLess(float(self.page.locator('#about').evaluate('n => parseFloat(getComputedStyle(n).animationDuration)')), .001)
        handle = self.page.locator('#about [data-window-handle]')
        self.page.wait_for_function('!document.querySelector("[data-window-motion]")')
        before = self.page.locator('#about').bounding_box()
        position = self.page.locator('#about').evaluate('el => [el.style.getPropertyValue("--win-left"),el.style.getPropertyValue("--win-top")]')
        handle.evaluate('el => el.addEventListener("pointerdown", e => el.dataset.testPointer = e.pointerId, {once:true})')
        bounds = handle.bounding_box()
        x, y = bounds['x'] + bounds['width'] / 2, bounds['y'] + bounds['height'] / 2
        self.page.mouse.move(x, y)
        self.page.mouse.down()
        self.page.mouse.move(x + 80, y + 50)
        pointer = int(handle.get_attribute('data-test-pointer'))
        self.assertTrue(handle.evaluate('(el,id) => el.hasPointerCapture(id)',pointer))
        handle.dispatch_event('pointercancel', {'pointerId': pointer})
        self.assertEqual(self.page.locator('#about').evaluate('el => el.style.transform'),'')
        self.assertFalse(handle.evaluate('(el,id) => el.hasPointerCapture(id)',pointer))
        self.page.mouse.up()
        # CDP can return the previous compositor box immediately after cleanup.
        # Verify the committed coordinates as well as geometry on the next painted frame.
        self.page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        self.assertEqual(self.page.locator('#about').evaluate('el => [el.style.getPropertyValue("--win-left"),el.style.getPropertyValue("--win-top")]'),position)
        after = self.page.locator('#about').bounding_box()
        self.assertAlmostEqual(before['x'], after['x'], delta=1)
        self.assertAlmostEqual(before['y'], after['y'], delta=1)

    def test_responsive_themes_and_accessibility_evidence(self):
        from playwright.sync_api import expect
        output = Path('Planning/qa/ui-plan-audit')
        capture = os.environ.get('UI_AUDIT_CAPTURE') == '1'
        axe_path = os.environ.get('UI_AUDIT_AXE_PATH')
        results = []
        if capture or axe_path:
            output.mkdir(parents=True, exist_ok=True)
        self.login(self.owner)
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        self.context.route('https://cdnjs.cloudflare.com/**', lambda route: route.abort())
        routes = (('/#about', 'about'), ('/projects/', 'projects'), ('/#contact', 'contact'),
                  ('/#education', 'education'), ('/#tech-stack', 'tools'),
                  ('/experience/', 'experience'), ('/skills/', 'skills'), ('/login/', 'login'),
                  ('/register/', 'register'), ('/dashboard/', 'dashboard'),
                  ('/projects/add/', 'project-form'), ('/experience/add/', 'experience-form'),
                  ('/skills/add/', 'skill-form'), ('/education/add/', 'education-form'),
                  ('/techstack/add/', 'tools-form'))
        self.goto('/')  # Establish the test origin before setting storage preferences.
        for width in (360, 390, 768, 1024, 1280, 1440, 1920):
            self.page.set_viewport_size({'width': width, 'height': 900})
            for theme in ('light', 'dark'):
                # Initialize before paint; measuring mid-transition creates false contrast failures.
                self.page.evaluate('(theme) => localStorage.setItem("theme", theme)', theme)
                for route, name in routes:
                    self.goto(route)
                    expect(self.page.locator('html')).to_have_attribute('data-theme', theme)
                    self.page.evaluate('document.fonts.ready')
                    self.page.wait_for_function('!document.querySelector("[data-window-motion]")')
                    self.page.wait_for_function('''document.getAnimations().filter(animation =>
                        animation.effect?.getComputedTiming().iterations !== Infinity
                    ).every(animation => animation.playState === 'finished')''')
                    self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width, (width, theme, route))
                    self.assertEqual(self.page.locator('title').count(), 1)
                    duplicates = self.page.evaluate('''() => {
                        const ids = [...document.querySelectorAll('[id]')].map(node => node.id);
                        return ids.filter((id, index) => ids.indexOf(id) !== index);
                    }''')
                    self.assertEqual(duplicates, [], (width, theme, route))
                    windows = self.page.locator('[data-window-id]:visible')
                    if windows.count():
                        title = windows.first.locator('.window-titlebar').bounding_box()
                        menu = self.page.locator('.desktop-menubar').bounding_box()
                        self.assertGreaterEqual(title['y'], menu['height'], (width, theme, route))
                    if capture and width in (360, 1440):
                        self.page.screenshot(path=str(output / f'{name}-{width}-{theme}.png'), full_page=True, animations='disabled')
                    if axe_path and width in (360, 1440):
                        self.page.add_script_tag(path=axe_path)
                        audit = self.page.evaluate('''async () => {
                            const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}});
                            return {violations: r.violations.map(v => ({id:v.id, impact:v.impact,
                                nodes:v.nodes.map(n => ({target:n.target, summary:n.failureSummary}))})),
                                incomplete: r.incomplete.map(v => ({id:v.id, nodes:v.nodes.map(n => n.target)}))};
                        }''')
                        results.append({'width': width, 'theme': theme, 'route': route, **audit})
        if axe_path:
            (output / f'accessibility-{os.environ.get("UI_TEST_BROWSER", "edge")}.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        self.assertEqual([(r['width'], r['theme'], r['route'], r['violations']) for r in results if r['violations']], [])
