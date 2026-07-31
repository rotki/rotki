import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { ModulesSettingsPage } from '../../pages/modules-settings-page';

test.describe.serial('settings::modules', () => {
  let ctx: SharedTestContext;
  let page: ModulesSettingsPage;
  const testModule = 'makerdao_dsr';
  let expectedState: boolean;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new ModulesSettingsPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('toggles a module and reflects the new state', async () => {
    const before = await page.isModuleEnabled(testModule);
    await page.toggleModule(testModule);
    expectedState = !before;
  });

  test('persists the module state after re-login', async () => {
    await ctx.app.relogin(ctx.username);
    await page.visit();
    await page.expectModuleEnabled(testModule, expectedState);
  });
});
