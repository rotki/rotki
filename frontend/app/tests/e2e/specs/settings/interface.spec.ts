import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { InterfaceSettingsPage } from '../../pages/interface-settings-page';

test.describe.serial('settings::interface', () => {
  let ctx: SharedTestContext;
  let page: InterfaceSettingsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new InterfaceSettingsPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('renders every interface settings section', async () => {
    await page.expectSectionsRendered();
  });

  test('toggles the animations setting and shows inline success', async () => {
    await page.toggleAnimations();
  });
});
