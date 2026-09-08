import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { TagManagerPage } from '../../pages/tag-manager';

const DEFAULT_PAGE_SIZE = 10;

test.describe.serial('tag manager', () => {
  let ctx: SharedTestContext;
  let page: TagManagerPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new TagManagerPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('creates a tag', async () => {
    await page.createTag('alpha', 'first tag', 'EF703C', 'FFFFF8');
    await page.expectTagVisible('alpha');
  });

  test('edits an existing tag', async () => {
    await page.editTag('alpha', 'first tag updated');
  });

  test('filters tags via search', async () => {
    await page.createTag('beta', 'second tag');
    await page.createTag('gamma', 'third tag');

    await page.search('beta');
    await page.expectVisibleRowCount(1);
    await page.expectTagVisible('beta');

    await page.clearSearch();
    await page.expectAtLeastVisibleRows(3);
  });

  test('paginates once the tags from this suite outgrow a page', async () => {
    for (let i = 0; i < DEFAULT_PAGE_SIZE; i++)
      await page.createTag(`tag-${i.toString().padStart(2, '0')}`, `tag ${i}`);

    await page.expectVisibleRowCount(DEFAULT_PAGE_SIZE);
    await page.expectNextPageEnabled(true);

    await page.goToNextPage();
    await page.expectAtLeastVisibleRows(1);
    await page.expectNextPageEnabled(false);
  });

  test('deletes a tag', async () => {
    await page.search('alpha');
    await page.deleteTag('alpha');
  });
});
