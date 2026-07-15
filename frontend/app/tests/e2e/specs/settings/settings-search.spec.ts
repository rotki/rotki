import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { SettingsSearchPage } from '../../pages/settings-search-page';

test.describe.serial('settings::search', () => {
  let ctx: SharedTestContext;
  let pageSearch: SettingsSearchPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    pageSearch = new SettingsSearchPage(ctx.sharedPage);
    await pageSearch.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('navigates to another tab and highlights a registry-backed setting', async () => {
    await pageSearch.searchAndSelect('language', 'Language');
    await expect(ctx.sharedPage).toHaveURL(/\/settings\/interface/);
    // #setting-language is derived from the registry anchor via SettingsItem setting-key
    await pageSearch.expectScrolledAndHighlighted('setting-language');
  });

  test('highlights a keyless action target from search', async () => {
    await pageSearch.searchAndSelect('purge data', 'Purge Data');
    await expect(ctx.sharedPage).toHaveURL(/\/settings\/database/);
    await pageSearch.expectScrolledAndHighlighted('setting-purge-data');
  });
});
