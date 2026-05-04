import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { TagManagerPage } from '../../pages/tag-manager';

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
    expect(await page.visibleRowCount()).toBe(1);
    await page.expectTagVisible('beta');

    await page.clearSearch();
    expect(await page.visibleRowCount()).toBeGreaterThanOrEqual(3);
  });

  test('paginates when more than 10 tags exist', async () => {
    // After previous tests there are 4 tags (Contract reserved + alpha + beta + gamma).
    // Add 9 more to push total to 13 and force a second page (default page size is 10).
    for (let i = 0; i < 9; i++)
      await page.createTag(`tag-${i.toString().padStart(2, '0')}`, `tag ${i}`);

    expect(await page.visibleRowCount()).toBe(10);
    await page.expectNextPageEnabled(true);

    await page.goToNextPage();
    expect(await page.visibleRowCount()).toBeGreaterThan(0);
    await page.expectNextPageEnabled(false);
  });

  test('deletes a tag', async () => {
    await page.search('alpha');
    await page.deleteTag('alpha');
  });
});
