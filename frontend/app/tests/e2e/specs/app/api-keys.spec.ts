import { test } from '@playwright/test';
import { testEnv } from '../../fixtures';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { ApiKeysPage } from '../../pages/api-keys-page';

test.describe.serial('api keys', () => {
  let ctx: SharedTestContext;
  let apiKeysPage: ApiKeysPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);

    // Navigate to API keys page once
    apiKeysPage = new ApiKeysPage(ctx.sharedPage);
    await apiKeysPage.visit('api-keys-exchanges');
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add exchange key', async () => {
    const apiKey = testEnv.KRAKEN_API_KEY;
    const apiSecret = testEnv.KRAKEN_API_SECRET;
    await apiKeysPage.addExchange(apiKey, apiSecret, 'kraken', 'My Kraken');
    await apiKeysPage.exchangeIsAdded('Kraken', 'My Kraken');
  });
});
