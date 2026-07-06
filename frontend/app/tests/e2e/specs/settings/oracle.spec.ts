import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { OracleSettingsPage } from '../../pages/oracle-settings-page';

test.describe.serial('settings::oracle', () => {
  let ctx: SharedTestContext;
  let page: OracleSettingsPage;
  const penaltyDuration = '3600';

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new OracleSettingsPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('renders the price oracle and penalty sections', async () => {
    await page.expectSectionsRendered();
  });

  test('changes the oracle penalty duration and shows inline success', async () => {
    await page.setPenaltyDuration(penaltyDuration);
  });

  test('persists the penalty duration after re-login', async () => {
    await ctx.app.relogin(ctx.username);
    await page.visit();
    await page.expectPenaltyDuration(penaltyDuration);
  });
});
