import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { DatabaseSettingsPage } from '../../pages/database-settings-page';

test.describe.serial('settings::database', () => {
  let ctx: SharedTestContext;
  let page: DatabaseSettingsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new DatabaseSettingsPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('renders every database settings section', async () => {
    await page.expectSectionsRendered();
  });
});
