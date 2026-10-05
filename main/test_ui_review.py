"""Opt-in evidence review using StaticLiveServerTestCase's isolated database.

UI_REVIEW=1 and UI_AUDIT_AXE_PATH enable historical incomplete-node investigation.
Reports are separate from the previous audit; initial flags are never overwritten.
"""
import json
import os
import subprocess
from pathlib import Path
import unittest

from django.test import override_settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from main import test_resource_browser as browser_tests
from main import test_desktop as desktop_tests
from main.test_helpers.contrast import calculate


GEOMETRY = """el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    const clipping = [];
    for (let p = el.parentElement; p; p = p.parentElement) {
        const ps = getComputedStyle(p), pr = p.getBoundingClientRect();
        if (/auto|scroll|hidden|clip/.test(ps.overflowX + ps.overflowY) &&
            (r.left < pr.left || r.right > pr.right || r.top < pr.top || r.bottom > pr.bottom))
            clipping.push({tag:p.tagName, id:p.id, class:p.className, overflow:ps.overflow});
    }
    const x = Math.max(0, Math.min(innerWidth - 1, r.x + r.width / 2));
    const y = Math.max(0, Math.min(innerHeight - 1, r.y + r.height / 2));
    const hit = document.elementFromPoint(x, y);
    const surfaces = [];
    for (let p = el; p; p = p.parentElement) {
        const ps = getComputedStyle(p);
        surfaces.push({tag:p.tagName, id:p.id, class:p.className,
            background:ps.backgroundColor, image:ps.backgroundImage, opacity:ps.opacity});
    }
    return {text:el.value || el.textContent.trim(), placeholder:el.getAttribute('placeholder'),
        placeholderColor:getComputedStyle(el,'::placeholder').color,
        color:s.color, fontSize:s.fontSize, fontWeight:s.fontWeight,
        rect:{x:r.x,y:r.y,width:r.width,height:r.height},
        offscreen:r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth,
        clipping, hit:hit ? {tag:hit.tagName,id:hit.id,class:hit.className} : null,
        covered:!!hit && hit !== el && !el.contains(hit) && !hit.contains(el), surfaces};
}"""

AXE = """async selectors => {
    const context = selectors ? {include:selectors} : document;
    const result = await axe.run(context, {runOnly:{type:'rule',values:['color-contrast']}});
    const simplify = rules => rules.map(rule => ({id:rule.id,nodes:rule.nodes.map(n => ({
        target:n.target,html:n.html,any:n.any,all:n.all,none:n.none,failureSummary:n.failureSummary
    }))}));
    return {violations:simplify(result.violations),incomplete:simplify(result.incomplete),
        passes:simplify(result.passes)};
}"""


@unittest.skipUnless(os.environ.get('UI_REVIEW') == '1', 'Opt-in evidence review: UI_REVIEW=1.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class IncompleteContrastReviewTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto
    login = browser_tests.ResourceBrowserTests.login

    def test_css_states_roles_and_emulated_touch_rotation(self):
        from playwright.sync_api import expect
        output = Path('Planning/qa/ui-followup')
        output.mkdir(parents=True, exist_ok=True)
        snapshots = []
        collect = """() => {
            const found = [];
            function walk(rules, source, media) {
                for (const rule of rules) {
                    if (rule.selectorText) {
                        let matches = 0;
                        try { matches = document.querySelectorAll(rule.selectorText).length; } catch {}
                        found.push({source,selector:rule.selectorText,media,matches});
                    } else if (rule.cssRules) {
                        walk(rule.cssRules,source,rule.conditionText ? [...media,rule.conditionText] : media);
                    }
                }
            }
            for (const sheet of document.styleSheets) {
                try { walk(sheet.cssRules,sheet.href,[]); } catch {}
            }
            return found;
        }"""
        def snapshot(state, role, width, theme):
            snapshots.append({'state':state,'role':role,'width':width,'theme':theme,
                              'rules':self.page.evaluate(collect)})
        for role, user in (('guest',None),('regular',self.regular),('editor',self.editor),('owner',self.owner)):
            self.context.clear_cookies()
            if user:
                self.login(user)
            for width in (360,1440):
                self.page.set_viewport_size({'width':width,'height':900})
                self.goto('/')
                for theme in ('light','dark'):
                    self.page.evaluate('theme => localStorage.setItem("theme",theme)',theme)
                    for route in ('/projects/','/experience/','/skills/','/#tech-stack','/#education','/login/'):
                        self.goto(route)
                        expect(self.page.locator('body')).to_have_attribute('data-navigation-ready','')
                        self.page.evaluate('document.fonts.ready')
                        snapshot(route,role,width,theme)
                        if route == '/skills/':
                            self.page.get_by_role('tab',name='Math',exact=True).click()
                            snapshot('skills-math',role,width,theme)
                        if route == '/#tech-stack':
                            self.page.locator('.tech-icon-wrapper').click()
                            snapshot('tools-expanded',role,width,theme)
                    if role in ('editor','owner'):
                        self.goto('/dashboard/')
                        for resource in ('projects','experience','skills','education','techstack'):
                            self.page.locator(f'[data-dashboard-tab="{resource}"]').click()
                            panel = self.page.locator(f'[data-resource="{resource}"]')
                            expect(panel.locator('tbody tr').first).to_be_visible()
                            snapshot('dashboard-'+resource,role,width,theme)
                            panel.locator('[data-resource-action="edit"]').first.click()
                            dialog = self.page.locator(f'#{resource}-dialog')
                            expect(dialog).to_be_visible()
                            snapshot('edit-dialog-'+resource,role,width,theme)
                            self.page.keyboard.press('Escape')
                            if role == 'owner':
                                panel.locator('[data-resource-action="delete"]').first.click()
                                expect(self.page.locator(f'#{resource}-delete-dialog')).to_be_visible()
                                snapshot('delete-dialog-'+resource,role,width,theme)
                                self.page.keyboard.press('Escape')
        engine = os.environ.get('UI_TEST_BROWSER','edge')
        (output / f'css-state-coverage-{engine}.json').write_text(json.dumps(snapshots,indent=2),encoding='utf-8')
        touch = self.browser.new_context(has_touch=True,viewport={'width':390,'height':844})
        page = touch.new_page()
        try:
            page.goto(self.live_server_url + '/')
            expect(page.locator('.desktop-apps')).to_be_visible()
            icon = page.locator('[data-app-id="contact"]').bounding_box()
            page.touchscreen.tap(icon['x']+icon['width']/2,icon['y']+icon['height']/2)
            expect(page.locator('#contact')).to_be_visible()
            page.locator('#id_name').fill('Retained through rotation')
            page.set_viewport_size({'width':844,'height':390})
            expect(page.locator('#id_name')).to_have_value('Retained through rotation')
            titlebar = page.locator('#contact .window-titlebar').bounding_box()
            self.assertGreaterEqual(titlebar['y'],page.locator('.desktop-menubar').bounding_box()['height'])
            page.once('dialog',lambda dialog:dialog.accept())
            close = page.locator('#contact [data-window-action="close"]').bounding_box()
            page.touchscreen.tap(close['x']+close['width']/2,close['y']+close['height']/2)
            expect(page.locator('.desktop-apps')).to_be_visible()
            (output / f'touch-emulation-{engine}.json').write_text(json.dumps({
                'browser':self.browser.version,'physical_device':False,
                'actions':['touch tap Contact','fill name','390x844 to 844x390','touch close with confirmation'],
                'retained_input':True,'titlebar_below_menu':True}),encoding='utf-8')
        finally:
            touch.close()

    def test_historical_flags_with_revealed_elements(self):
        axe_path = os.environ.get('UI_AUDIT_AXE_PATH')
        self.assertTrue(axe_path and Path(axe_path).exists(), 'A local axe-core script is required.')
        engine = os.environ.get('UI_TEST_BROWSER', 'edge')
        historical = json.loads(Path('Planning/qa/ui-plan-audit/accessibility-edge.json').read_text())
        output = Path('Planning/qa/ui-followup')
        output.mkdir(parents=True, exist_ok=True)
        self.login(self.owner)
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.abort())
        self.context.route('https://cdnjs.cloudflare.com/**', lambda route: route.abort())
        self.goto('/')
        reviews = []
        try:
            for row in historical:
                if not row['incomplete']:
                    continue
                self.page.set_viewport_size({'width':row['width'], 'height':900})
                self.page.evaluate('theme => localStorage.setItem("theme",theme)', row['theme'])
                self.goto(row['route'])
                self.page.evaluate('document.fonts.ready')
                self.page.wait_for_function('''document.getAnimations().filter(a =>
                    a.effect?.getComputedTiming().iterations !== Infinity).every(a => a.playState === 'finished')''')
                self.page.add_script_tag(path=axe_path)
                current = self.page.evaluate(AXE, None)
                if row['route'] in ('/experience/', '/#education'):
                    name = row['route'].strip('/#')
                    screenshot = output / f'{engine}-{name}-{row["width"]}-{row["theme"]}.png'
                    self.page.screenshot(path=str(screenshot), full_page=True, animations='disabled')
                nodes = []
                for rule in row['incomplete']:
                    for target in rule['nodes']:
                        locator = self.page.locator(target[0])
                        if locator.count() != 1:
                            nodes.append({'target':target,'unresolved':locator.count()})
                            continue
                        before = locator.evaluate(GEOMETRY)
                        locator.scroll_into_view_if_needed()
                        # Focus the owning region to bring an occluded window forward.
                        locator.evaluate('el => el.closest("[data-window-id]")?.querySelector("h2")?.focus({preventScroll:true})')
                        after = locator.evaluate(GEOMETRY)
                        rescan = self.page.evaluate(AXE, [target])
                        nodes.append({'target':target,'before':before,'after':after,'rescan':rescan})
                reviews.append({**{k:row[k] for k in ('width','theme','route')},
                                'initial':current,'historical_nodes':nodes})
        finally:
            (output / f'contrast-review-{engine}.json').write_text(json.dumps({
                'browser':self.browser.version,'axe':self.page.evaluate('axe.version'),
                'reviews':reviews},indent=2), encoding='utf-8')
        self.assertEqual([r for r in reviews if r['initial']['violations']], [])
        colors = [calculate(node['after']) for row in reviews for node in row['historical_nodes'] if 'after' in node]
        self.assertFalse([c for c in colors if c['unresolved']], 'Review non-flat surfaces separately.')
        self.assertFalse([c for c in colors if min(c['contrast'], c.get('placeholder_contrast', 99),
                                                  c.get('glass_minimum', 99)) < 4.5])


@unittest.skipUnless(os.environ.get('UI_LIGHTHOUSE') == '1', 'Opt-in Lighthouse: UI_LIGHTHOUSE=1.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class LighthouseEvidenceTests(StaticLiveServerTestCase):
    setUp = desktop_tests.DesktopFallbackTests.setUpTestData.__func__

    def test_mobile_public_routes(self):
        self.measure_mobile_routes((('/', 'home'), ('/projects/', 'projects')), Path('Planning/qa/ui-followup'))

    def test_mobile_remaining_public_routes(self):
        routes = (('/experience/', 'experience'), ('/skills/', 'skills'), ('/#contact', 'contact'))
        requested = os.environ.get('UI_LIGHTHOUSE_ROUTES')
        if requested:
            routes = tuple(row for row in routes if row[0] in requested.split(','))
            self.assertTrue(routes, 'Choose a remaining public route for Lighthouse.')
        self.measure_mobile_routes(routes, Path(os.environ.get('UI_LIGHTHOUSE_OUTPUT','Planning/qa/ui-state-qa')))

    def measure_mobile_routes(self, routes, output):
        runner = Path('Planning/qa/tools/lighthouse/node_modules/lighthouse/cli/index.js').resolve()
        self.assertTrue(runner.exists(), 'Install Lighthouse into the ignored QA tools directory.')
        output.mkdir(parents=True, exist_ok=True)
        results = []
        for route, name in routes:
            report = (output / f'lighthouse-{name}.json').resolve()
            process = subprocess.run(['node', str(runner), self.live_server_url + route,
                '--only-categories=performance,accessibility', '--output=json',
                f'--output-path={report}', '--chrome-flags=--headless', '--quiet'],
                text=True, capture_output=True, timeout=180,
                env={**os.environ, 'CHROME_PATH':'C:/Program Files/Google/Chrome/Application/chrome.exe'})
            (output / f'lighthouse-{name}.log').write_text(process.stdout + process.stderr, encoding='utf-8')
            self.assertEqual(process.returncode, 0, process.stderr)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertNotIn('runtimeError', data)
            results.append({'route':route, 'version':data['lighthouseVersion'],
                'fetchTime':data['fetchTime'], 'theme':'default light',
                'environment':data['environment'], 'settings':data['configSettings'],
                'metrics':{key:data['audits'][key]['numericValue'] for key in
                           ('first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift')},
                'scores':{k:v['score'] for k,v in data['categories'].items()}})
        (output / 'lighthouse-summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
