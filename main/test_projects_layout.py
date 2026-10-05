"""Gallery geometry and renderer parity in the actual desktop shell."""
import importlib.util
import unittest
from concurrent.futures import ThreadPoolExecutor

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from main import test_resource_browser as browser_tests
from main.models import Project, Tag


@unittest.skipUnless(importlib.util.find_spec('playwright'), 'Install requirements-dev.txt.')
@override_settings(DEBUG=True, ALLOWED_HOSTS=['*'])
class ProjectsLayoutBrowserTests(StaticLiveServerTestCase):
    setUp = browser_tests.ResourceBrowserTests.setUp
    tearDown = browser_tests.ResourceBrowserTests.tearDown
    goto = browser_tests.ResourceBrowserTests.goto

    def prepare(self):
        self.page.emulate_media(reduced_motion='reduce')
        def seed():
            project = Project.objects.get(title='Portfolio')
            project.project_image_url = self.live_server_url + '/gallery-preview.svg'
            project.project_url = 'https://example.com/project'
            project.description = 'A readable project description with enough text to wrap naturally inside the gallery.'
            project.save()
            project.tags.add(Tag.objects.create(name='Django', slug='django'))
            Project.objects.create(title='A project with a deliberately long title to exercise wrapping', category='Other', description='A second project without an image.')
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(seed).result()
        self.context.route('**/gallery-preview.svg', lambda route: route.fulfill(
            content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><rect width="800" height="500" fill="#dbeaff"/></svg>'))

    def test_media_grid_and_sidebar_follow_window_width_and_text_scaling(self):
        from playwright.sync_api import expect
        self.prepare()
        self.page.set_viewport_size({'width': 1440, 'height': 1000})
        self.goto('/projects/')
        expect(self.page.locator('#grid .project-card')).to_have_count(2)
        self.page.wait_for_function('document.fonts.status === "loaded"')
        for state, width, height in (
            ('desktop', 1440, 1000), ('maximized', 1440, 1000),
            ('snapped', 1440, 1000), ('tablet', 1024, 900),
            ('mobile', 390, 844), ('small-mobile', 320, 740), ('text-scale', 390, 844),
        ):
            with self.subTest(state=state):
                self.page.set_viewport_size({'width': width, 'height': height})
                if state == 'maximized':
                    self.page.locator('#projects [data-window-action="maximize"]').click()
                if state == 'snapped':
                    self.page.locator('#win-title-projects').focus()
                    self.page.keyboard.press('Alt+ArrowLeft')
                if state == 'text-scale':
                    self.page.evaluate('document.documentElement.style.fontSize = "32px"')
                metrics = self.page.locator('#projects').evaluate('''root => {
                    const gallery = root.querySelector('.projects-gallery'),
                        shell = root.querySelector('.projects-shell'),
                        grid = root.querySelector('#grid'),
                        sidebar = root.querySelector('.project-sidebar'),
                        form = root.querySelector('#project-search-form'),
                        media = root.querySelector('.project-media');
                    const ss = getComputedStyle(shell);
                    return {rootWidth:root.clientWidth, rootScroll:root.scrollWidth,
                        contentWidth:shell.clientWidth - parseFloat(ss.paddingLeft) - parseFloat(ss.paddingRight),
                        collapseWidth:42 * parseFloat(getComputedStyle(document.documentElement).fontSize),
                        shellWidth:shell.clientWidth, shellScroll:shell.scrollWidth,
                        gridWidth:grid.clientWidth, gridScroll:grid.scrollWidth,
                        columns:getComputedStyle(grid).gridTemplateColumns.split(' ').length,
                        side:sidebar.getBoundingClientRect().toJSON(), gallery:gallery.getBoundingClientRect().toJSON(),
                        form:form.getBoundingClientRect().toJSON(),
                        ratio:media.clientWidth / media.clientHeight,
                        fit:getComputedStyle(root.querySelector('.project-image')).objectFit,
                        descriptionSize:parseFloat(getComputedStyle(root.querySelector('.experience-description')).fontSize)};
                }''')
                self.assertLessEqual(metrics['rootScroll'], metrics['rootWidth'] + 1)
                self.assertLessEqual(metrics['shellScroll'], metrics['shellWidth'] + 1)
                self.assertLessEqual(metrics['gridScroll'], metrics['gridWidth'] + 1)
                self.assertAlmostEqual(metrics['ratio'], 1.6, delta=.025)
                self.assertEqual(metrics['fit'], 'cover')
                self.assertGreaterEqual(metrics['descriptionSize'], 16)
                self.assertLess(metrics['form']['bottom'], metrics['gallery']['top'])
                if metrics['contentWidth'] > metrics['collapseWidth']:
                    self.assertLess(metrics['side']['right'], metrics['gallery']['left'])
                else:
                    self.assertLessEqual(metrics['side']['bottom'], metrics['gallery']['top'])
                if state in ('desktop', 'maximized'):
                    self.assertGreaterEqual(metrics['columns'], 2)
                for button in self.page.locator('#projects [data-filter]').all():
                    self.assertGreaterEqual(button.bounding_box()['height'], 44)
        expect(self.page.locator('#grid .project-category')).to_have_text(['Web', 'Other'])

    def test_category_tags_filter_reset_and_failed_image_keep_gallery_structure(self):
        from playwright.sync_api import expect
        self.prepare()
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.goto('/projects/')
        expect(self.page.locator('#grid .project-technologies')).to_have_text('Django')
        expect(self.page.locator('#grid .project-category')).to_have_text(['Web', 'Other'])
        expect(self.page.locator('#grid .project-media-placeholder')).to_have_count(1)
        self.context.unroute('**/gallery-preview.svg')
        self.context.route('**/gallery-preview.svg*', lambda route: route.abort())
        self.page.locator('[data-filter="Web"]').click()
        expect(self.page.locator('#grid .project-card')).to_have_count(1)
        self.page.locator('#grid .project-image').evaluate('img => img.src += "?failed=1"')
        expect(self.page.locator('#grid .project-media .image-fallback')).to_be_visible()
        self.page.locator('#search-input').fill('missing')
        expect(self.page.locator('#empty')).to_be_visible()
        self.page.locator('[data-projects-reset]').click()
        expect(self.page.locator('#grid .project-card')).to_have_count(2)
        expect(self.page.locator('#search-input')).to_be_focused()
        fallback = self.browser.new_context(java_script_enabled=False)
        try:
            page = fallback.new_page()
            page.goto(self.live_server_url + '/projects/?category=Web')
            expect(page.locator('#grid .project-category')).to_have_text('Web')
            expect(page.locator('#grid .project-technologies')).to_have_text('Django')
            expect(page.locator('#grid .project-media')).to_have_count(1)
        finally:
            fallback.close()
