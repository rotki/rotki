import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { ExternalServicesPage } from '../../pages/external-services-page';

test.describe.serial('api-keys::external-services', () => {
  let ctx: SharedTestContext;
  let page: ExternalServicesPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new ExternalServicesPage(ctx.sharedPage);
    await page.setupMocks();
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('lists the external service providers', async () => {
    await page.expectServicesRendered(['Etherscan', 'CoinGecko', 'CryptoCompare']);
  });

  test('saves an etherscan api key', async () => {
    await page.saveEtherscanKey('DUMMY_ETHERSCAN_KEY');
    await page.expectSaveSucceeded('DUMMY_ETHERSCAN_KEY');
    await page.closeDialog();
  });
});
