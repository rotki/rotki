import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { AddressBookPage } from '../../pages/address-book-page';

const ADDR_PRIVATE = '0x1111111111111111111111111111111111111111';

test.describe.serial('address book', () => {
  let ctx: SharedTestContext;
  let page: AddressBookPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new AddressBookPage(ctx.sharedPage);
    await page.visit();
    // The global address book is seeded by rotki's global DB (~500+ entries
    // shared across users). Tests stay in the private scope which is per-user
    // and starts empty.
    await page.selectScope('private');
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('switches between global and private scopes', async () => {
    await page.selectScope('global');
    await page.expectScopeActive('global');
    await page.selectScope('private');
    await page.expectScopeActive('private');
  });

  test('creates a private entry', async () => {
    await page.addEntry({ address: ADDR_PRIVATE, name: 'private one' });
    await page.expectRow(ADDR_PRIVATE, 'private one');
  });

  test('edits an entry', async () => {
    await page.editEntry(ADDR_PRIVATE, 'private renamed');
    await page.expectRow(ADDR_PRIVATE, 'private renamed');
  });

  test('deletes an entry', async () => {
    await page.deleteEntry(ADDR_PRIVATE);
    await page.expectNoRow(ADDR_PRIVATE);
  });

  test('shows validation errors when required fields are empty', async () => {
    await page.openAddDialog();
    await page.submitDialog();
    await page.expectRequiredErrors();
    await page.cancelDialog();
  });

  test('cancel button closes the dialog', async () => {
    await page.openAddDialog();
    await page.cancelDialog();
  });

  test('paginates when more than 10 entries exist', async () => {
    // Default page size is 10, so 11 entries guarantees a second page.
    for (let i = 0; i < 11; i++) {
      // Encode i in the address prefix so each entry has a unique value.
      const addr = `0x${i.toString(16).padStart(2, '0')}${'b'.repeat(38)}`;
      const name = `entry-${i.toString().padStart(2, '0')}`;
      await page.addEntry({ address: addr, name });
    }

    expect(await page.visibleRowCount()).toBe(10);
    await page.expectNextPageEnabled(true);

    await page.goToNextPage();
    expect(await page.visibleRowCount()).toBeGreaterThan(0);
    await page.expectNextPageEnabled(false);
  });

  // Runs on the 11 entries the pagination test left behind, so the filter has both something to
  // find and plenty to exclude.
  test('filters the entries by name', async () => {
    await page.filterByName('entry-03');
    await page.expectVisibleRowCount(1);
    await page.expectRowByName('entry-03');

    // The negative control: the same pill, a name nothing carries, and the row is gone. Without it
    // a filter that quietly did nothing would still have passed above, since entry-03 was on the
    // page to begin with.
    await page.clearFilters();
    await page.filterByName('no-such-entry');
    await page.expectVisibleRowCount(0);

    await page.clearFilters();
    await page.expectVisibleRowCount(10);
  });
});
