import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { InterfaceSettingsPage } from '../../pages/interface-settings-page';

const explorerUrl = 'https://example.com/address/';

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

  test('rejects an explorer url that is not https', async () => {
    await page.setExplorerUrl('address', 'http://example.com/address/');
    await page.expectExplorerMessage('address', 'Only https urls are allowed');
    await page.expectSaveDisabled('address');
  });

  // 'https://' fails only the url rule, so it covers that check rather than repeating the one above.
  test('rejects an explorer url that is only a scheme', async () => {
    await page.setExplorerUrl('address', 'https://');
    await page.expectExplorerRejected('address');
    await page.expectSaveDisabled('address');
  });

  test('saves a valid explorer url and keeps it after re-login', async () => {
    await page.setExplorerUrl('address', explorerUrl);
    await page.expectSaveEnabled('address');
    await page.saveExplorerUrl('address');

    // Navigating re-reads the in-memory repo, so only a fresh login proves what was persisted.
    await ctx.app.relogin(ctx.username);
    await page.visit();
    await page.expectExplorerValue('address', explorerUrl);
  });
});
