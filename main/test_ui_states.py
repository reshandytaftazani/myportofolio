"""Additional keyboard/long-content regressions and opt-in rendered state evidence.

All records and requests use StaticLiveServerTestCase's separate database. UI_REVIEW=1
enables color/axe evidence; originals in ui-followup are never overwritten.
"""
import json
import importlib.util
import os
from pathlib import Path
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, SimpleTestCase
from main import test_resource_browser as browser_tests
from main import test_ui_review as review
from main.models import Skill, TechStack, Experience, Education, Project


OUTPUT = Path('Planning/qa/ui-state-qa')
CODE = '''#include <iostream>
// A comment with a URL https://example.com and an accented word café
int main() {
    const double value = 3.14;
    std::string text = "'''+ ('long_code_value_' * 32) + '''";
    if (true) std::cout << text << value;
    return 0;
}'''


class ContrastColorParsingTests(SimpleTestCase):
    def test_normalized_srgb_and_alpha_match_rgb_channels(self):
        from main.test_helpers.contrast import rgba, contrast
        self.assertEqual(rgba('color(srgb 0.2 0.4 0.6 / 0.5)'),rgba('rgba(51, 102, 153, 0.5)'))
        self.assertEqual(rgba('rgb(20% 40% 60% / 50%)'),rgba('rgba(51, 102, 153, 0.5)'))
        self.assertAlmostEqual(contrast(rgba('color(srgb 1 1 1)')[:3],[0,0,0]),21)
        with self.assertRaises(ValueError):
            rgba('color(display-p3 1 0 0)')


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt for browser checks.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AdditionalUIStateTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto
    login = browser_tests.ResourceBrowserTests.login
    database_call = browser_tests.ResourceBrowserTests.database_call

    def settle(self):
        self.page.evaluate('document.fonts.ready')
        self.page.wait_for_function('''document.getAnimations().filter(a =>
            a.effect?.getComputedTiming().iterations !== Infinity).every(a => a.playState === 'finished')''')

    def theme(self, theme, width):
        self.page.set_viewport_size({'width':width, 'height':900})
        if not self.page.url.startswith(self.live_server_url):
            self.goto('/')
        self.page.evaluate('theme => localStorage.setItem("theme",theme)',theme)

    def assert_focus_visible(self, locator):
        self.assertTrue(locator.evaluate('el => el.matches(":focus-visible")'))
        style = locator.evaluate('el => ({style:getComputedStyle(el).outlineStyle,width:getComputedStyle(el).outlineWidth})')
        self.assertNotEqual(style['style'], 'none', style)
        self.assertGreaterEqual(float(style['width'].removesuffix('px')), 2, style)

    def test_keyboard_skills_tools_account_and_window_states(self):
        from playwright.sync_api import expect
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        self.context.route('https://cdnjs.cloudflare.com/**', lambda route: route.abort())
        for theme in ('light', 'dark'):
            for width in (360,1440):
                self.theme(theme,width)
                self.goto('/skills/')
                tabs = self.page.get_by_role('tab')
                expect(tabs).to_have_count(2)
                tabs.first.focus()
                self.page.keyboard.press('End')
                expect(tabs.last).to_be_focused()
                expect(tabs.last).to_have_attribute('aria-selected','true')
                self.assert_focus_visible(tabs.last)
                self.page.keyboard.press('ArrowRight')
                expect(tabs.first).to_be_focused()
                self.page.keyboard.press('ArrowLeft')
                expect(tabs.last).to_be_focused()
                self.page.keyboard.press('Home')
                expect(tabs.first).to_be_focused()
                self.goto('/#tech-stack')
                tool = self.page.locator('.tech-icon-wrapper')
                expect(tool).to_be_visible()
                tool.focus()
                self.page.keyboard.press('Space')
                expect(tool).to_have_attribute('aria-expanded','true')
                self.assert_focus_visible(tool)
                self.page.keyboard.press('Space')
                expect(tool).to_have_attribute('aria-expanded','false')
        self.login(self.editor)
        self.theme('dark',1440)
        self.goto('/skills/')  # Changing a hash alone does not reload authentication.
        self.goto('/#about')
        account = self.page.locator('.user-btn')
        account.focus()
        self.page.keyboard.press('Enter')
        expect(account).to_have_attribute('aria-expanded','true')
        self.page.keyboard.press('Tab')
        expect(self.page.locator('.user-dropdown-content a').first).to_be_focused()
        self.page.keyboard.press('Escape')
        expect(account).to_be_focused()
        expect(self.page.locator('#about')).to_be_visible()
        self.page.locator('#about [data-window-action="minimize"]').focus()
        self.page.keyboard.press('Enter')
        dock = self.page.locator('[data-dock-id="about"]')
        expect(dock).to_be_focused()
        expect(self.page.locator('#about')).to_be_hidden()
        self.page.keyboard.press('Enter')
        expect(self.page.locator('#win-title-about')).to_be_focused()
        maximize = self.page.locator('#about [data-window-action="maximize"]')
        maximize.focus()
        self.page.keyboard.press('Enter')
        expect(maximize).to_have_attribute('aria-pressed','true')
        self.page.keyboard.press('Enter')
        expect(maximize).to_have_attribute('aria-pressed','false')

    def test_long_content_and_keyboard_code_scrolling(self):
        from playwright.sync_api import expect
        title = 'UnbrokenPortfolioTitle' * 9
        def fixtures():
            Skill.objects.filter(title='C++').update(code_snippet=CODE, description='Long paragraph. ' * 150)
            TechStack.objects.update(filename=title[:47]+'.py', code_snippet=CODE, name=title[:50])
            Experience.objects.filter(title='Developer').update(title=title, company=title, description='Long description. ' * 150)
            Education.objects.update(school_name=title, detail=('Long education. ' * 150)[:255])
            Project.objects.update(title=title, description='Long project. ' * 150)
        self.database_call(fixtures)
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        self.context.route('https://cdnjs.cloudflare.com/**', lambda route: route.abort())
        for width in (360,768,1440):
            self.theme('dark',width)
            for route in ('/experience/','/projects/','/#education','/skills/','/#tech-stack'):
                self.goto(route)
                expect(self.page.locator('[data-list]:visible, #grid:visible').first).to_have_attribute('aria-busy','false')
                self.settle()
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width,route)
                if route == '/#tech-stack':
                    self.page.locator('.tech-icon-wrapper').press('Space')
                    code = self.page.locator('.mac-body')
                elif route == '/skills/':
                    code = self.page.locator('.tab-panel.active pre')
                else:
                    continue
                expect(code).to_be_visible()
                self.settle()
                bounds = code.bounding_box()
                self.assertGreaterEqual(bounds['x'],0,route)
                self.assertLessEqual(bounds['x']+bounds['width'],width,route)
                # Firefox needs an explicit keyboard entry point for scrollable code.
                expect(code).to_have_attribute('tabindex','0')
                code.focus()
                self.page.keyboard.press('ArrowRight')
                self.page.wait_for_function('el => el.scrollLeft > 0',arg=code.element_handle())
                self.assert_focus_visible(code)
                if os.environ.get('UI_REVIEW') == '1':
                    OUTPUT.mkdir(parents=True,exist_ok=True)
                    engine = os.environ.get('UI_TEST_BROWSER','edge')
                    self.page.screenshot(path=str(OUTPUT/f'{engine}-long-{route.strip("/#")}-{width}-dark.png'),
                                         full_page=True,animations='disabled')

    def test_mobile_deep_links_reserve_layout_and_release_failed_boot_hint(self):
        from playwright.sync_api import expect
        self.page.set_viewport_size({'width':390,'height':844})
        pending = []
        self.context.route('**/js/desktop/boot.js',lambda route:pending.append(route))
        for section in ('about','tech-stack','education','contact'):
            self.page.goto('about:blank')
            self.page.goto(self.live_server_url+'/#'+section,wait_until='commit')
            target = self.page.locator('#'+section)
            expect(target.locator('.window-titlebar')).to_be_visible()
            expect(self.page.locator('.desktop-scene')).to_be_hidden()
            self.assertEqual(self.page.locator('[data-window-id]:visible').count(),1)
            geometry = '''el => {
                const r=el.getBoundingClientRect();
                return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height,viewportY:r.y};
            }'''
            before = target.locator('.window-titlebar').evaluate(geometry)
            self.assertTrue(pending)
            pending.pop().continue_()
            expect(self.page.locator('body')).to_have_attribute('data-desktop-ready','')
            self.page.wait_for_load_state('load')  # The shell also normalizes native hash scrolling on load.
            after = target.locator('.window-titlebar').evaluate(geometry)
            # Native fragment scrolling changes viewport coordinates, not layout.
            self.assertGreaterEqual(after['viewportY'],self.page.locator('.desktop-menubar').bounding_box()['height'])
            for dimension in ('x','y','width','height'):
                self.assertAlmostEqual(before[dimension],after[dimension],delta=1,msg=(section,dimension))
            self.assertIsNone(self.page.locator('html').get_attribute('data-desktop-start-window'))
        self.page.goto('about:blank')
        self.page.goto(self.live_server_url+'/#contact',wait_until='commit')
        expect(self.page.locator('#contact')).to_be_visible()
        pending.pop().fulfill(content_type='text/javascript',body='window.PortfolioDesktop.fallback();')
        self.page.wait_for_load_state('domcontentloaded')
        self.assertIsNone(self.page.locator('body').get_attribute('data-desktop-ready'))
        self.assertIsNone(self.page.locator('html').get_attribute('data-desktop-start-window'))
        expect(self.page.locator('#about')).to_be_visible()
        expect(self.page.locator('.desktop-scene')).to_be_visible()
        context = self.browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
        try:
            page = context.new_page()
            page.goto(self.live_server_url+'/#contact')
            expect(page.locator('#about')).to_be_visible()
            expect(page.locator('#contact-form')).to_be_visible()
        finally:
            context.close()

    @unittest.skipUnless(os.environ.get('UI_REVIEW') == '1', 'Opt-in rendered state evidence: UI_REVIEW=1.')
    def test_loaded_libraries_and_interaction_contrast(self):
        from playwright.sync_api import expect
        axe_path = os.environ.get('UI_AUDIT_AXE_PATH')
        self.assertTrue(axe_path and Path(axe_path).exists(),'A local axe script is required.')
        OUTPUT.mkdir(parents=True,exist_ok=True)
        self.database_call(lambda: Skill.objects.filter(title='C++').update(code_snippet=CODE))
        self.login(self.owner)
        engine = os.environ.get('UI_TEST_BROWSER','edge')
        records = []
        libraries = {}

        def record(state, selectors, disabled=False):
            self.settle()
            if not self.page.evaluate('Boolean(window.axe)'):
                self.page.add_script_tag(path=axe_path)
            nodes = []
            for selector in selectors:
                for locator in self.page.locator(selector).all():
                    if not locator.is_visible():
                        continue
                    locator.scroll_into_view_if_needed()
                    geometry = locator.evaluate(review.GEOMETRY)
                    nodes.append({'selector':selector,'geometry':geometry,'calculated':review.calculate(geometry)})
            scan = self.page.evaluate(review.AXE,None)
            rules = self.page.evaluate('''() => {
                const found = [];
                function walk(rules, media) {
                    for (const rule of rules) {
                        if (rule.selectorText) {
                            let matches = 0;
                            try { matches = document.querySelectorAll(rule.selectorText).length; } catch {}
                            found.push({selector:rule.selectorText,media,matches,
                                declarations:rule.style.cssText});
                        } else if (rule.cssRules) {
                            walk(rule.cssRules, rule.conditionText ? [...media,rule.conditionText] : media);
                        }
                    }
                }
                for (const sheet of document.styleSheets) {
                    if (sheet.href?.includes('/css/shared.css')) walk(sheet.cssRules,[]);
                }
                return found;
            }''')
            records.append({'state':state,'theme':theme,'width':width,'route':self.page.url,
                            'disabled_exempt_from_text_threshold':disabled,'nodes':nodes,'axe':scan,
                            'shared_css_rules':rules})

        try:
            for theme in ('light','dark'):
                for width in (360,1440):
                    self.theme(theme,width)
                    self.goto('/skills/')
                    code = self.page.locator('.tab-panel.active pre code')
                    expect(code).to_have_attribute('data-highlighted','yes',timeout=45000)
                    self.assertGreater(code.locator('span').count(),5)
                    libraries = self.page.evaluate('({highlight:hljs.versionString,mathjax:MathJax.version})')
                    record('highlight-loaded',['.tab-panel.active pre code','.tab-panel.active pre code span','.ide-title'])
                    tabs = self.page.get_by_role('tab')
                    tabs.last.focus()
                    self.page.keyboard.press('End')
                    expect(self.page.locator('.overleaf-pdf mjx-container')).to_have_count(1,timeout=45000)
                    libraries = self.page.evaluate('({highlight:hljs.versionString,mathjax:MathJax.version})')
                    record('math-loaded-focus',['.tab-btn','.overleaf-editor code span','.pdf-paper mjx-container','.ide-title'])
                    tabs.first.hover()
                    record('skills-tab-hover',['.tab-btn'])
                    self.page.screenshot(path=str(OUTPUT/f'{engine}-skills-math-{width}-{theme}.png'),full_page=True,animations='disabled')
                    self.goto('/projects/')
                    edit = self.page.locator('[data-resource-action="edit"]').first
                    expect(edit).to_be_visible()
                    edit.hover()
                    record('project-edit-hover',['.resource-action--edit','.resource-action--edit span'])
                    edit.focus()
                    self.page.keyboard.press('Enter')
                    dialog = self.page.locator('#projects-dialog')
                    expect(dialog).to_be_visible()
                    dialog.locator('[name="title"]').fill('<b></b>')
                    dialog.locator('[type="submit"]').press('Enter')
                    expect(dialog.locator('[name="title"]')).to_have_attribute('aria-invalid','true')
                    record('project-dialog-error',['.resource-field-error','.resource-dialog input','.resource-button'])
                    self.page.keyboard.press('Escape')
                    expect(edit).to_be_focused()
                    self.page.locator('[data-resource-action="delete"]').first.press('Enter')
                    delete = self.page.locator('#projects-delete-dialog')
                    expect(delete).to_be_visible()
                    confirm = delete.locator('[data-confirm-delete]')
                    confirm.hover()
                    record('delete-dialog-hover',['#projects-delete-dialog .resource-button'])
                    confirm.focus()
                    self.page.keyboard.press('Shift+Tab')
                    expect(delete.locator('[data-close-delete]').last).to_be_focused()
                    self.assert_focus_visible(delete.locator('[data-close-delete]').last)
                    record('delete-dialog-focus',['#projects-delete-dialog .resource-button'])
                    self.page.screenshot(path=str(OUTPUT/f'{engine}-delete-dialog-{width}-{theme}.png'),full_page=True,animations='disabled')
                    self.page.keyboard.press('Escape')
                    expect(self.page.locator('#projects')).to_be_visible()
                    self.goto('/#contact')
                    pending = []
                    self.context.route(self.live_server_url+'/',lambda route:pending.append(route))
                    self.page.locator('#id_name').fill('Keyboard reviewer')
                    self.page.locator('#id_email').fill('qa@example.com')
                    self.page.locator('#id_message').fill('Retain this message after an error.')
                    send = self.page.locator('#contact-form [type="submit"]')
                    send.focus()
                    self.page.keyboard.press('Enter')
                    expect(send).to_be_disabled()
                    record('contact-pending',['#contact-form [type="submit"]'],disabled=True)
                    self.assertTrue(pending)
                    pending.pop().fulfill(status=400,json={'errors':{'email':['Please use another email address.']},'message':'Validation failed.'})
                    expect(self.page.locator('#id_email')).to_be_focused()
                    expect(send).to_be_enabled()
                    expect(self.page.locator('#id_message')).to_have_value('Retain this message after an error.')
                    record('contact-error-focus',['[data-contact-error]:visible','#id_email','[data-contact-feedback]:visible'])
                    self.page.screenshot(path=str(OUTPUT/f'{engine}-contact-error-{width}-{theme}.png'),full_page=True,animations='disabled')
                    self.context.unroute(self.live_server_url+'/')
                    # Reset fixture form before the next ordinary document navigation.
                    self.page.evaluate('document.querySelector("#contact-form").reset(); delete document.querySelector("#contact-form").dataset.dirty')
        finally:
            (OUTPUT/f'rendered-states-{engine}.json').write_text(json.dumps({
                'browser':self.browser.version,'library_versions':libraries,
                'records':records},indent=2),encoding='utf-8')
        failures = [(r['state'],r['theme'],n) for r in records if not r['disabled_exempt_from_text_threshold']
                    for n in r['nodes'] if not n['calculated']['unresolved'] and
                    min(n['calculated']['contrast'],n['calculated'].get('placeholder_contrast',99)) < 4.5]
        self.assertEqual(failures,[])
        self.assertEqual([(r['state'],r['axe']['violations']) for r in records if r['axe']['violations']],[])
