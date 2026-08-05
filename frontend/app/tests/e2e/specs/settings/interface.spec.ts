import { expect } from '@playwright/test';
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
    expect(await page.explorerMessages('address')).toContain('Only https urls are allowed');
    expect(await page.explorerSaveDisabled('address')).toBe(true);
  });

  // 'https://' passes the https rule and fails only the url rule, so this covers the url check
  // instead of duplicating the test above. A value failing BOTH rules would prove nothing here.
  test('rejects an explorer url that is only a scheme', async () => {
    await page.setExplorerUrl('address', 'https://');
    expect(await page.explorerMessages('address')).not.toBe('');
    expect(await page.explorerSaveDisabled('address')).toBe(true);
  });

  test('saves a valid explorer url and keeps it after re-login', async () => {
    await page.setExplorerUrl('address', explorerUrl);
    expect(await page.explorerSaveDisabled('address')).toBe(false);
    await page.saveExplorerUrl('address');

    // Explorers are frontend settings: only a fresh login proves what was persisted, since
    // navigating re-reads the in-memory settings repo.
    await ctx.app.relogin(ctx.username);
    await page.visit();
    expect(await page.explorerValue('address')).toBe(explorerUrl);
  });
});
