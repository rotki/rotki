import { testEnv } from '../../fixtures';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { ExchangesPage } from '../../pages/exchanges-page';

test.describe.serial('exchanges', () => {
  let ctx: SharedTestContext;
  let exchangesPage: ExchangesPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);

    exchangesPage = new ExchangesPage(ctx.sharedPage);
    await exchangesPage.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add exchange key', async () => {
    const apiKey = testEnv.KRAKEN_API_KEY;
    const apiSecret = testEnv.KRAKEN_API_SECRET;
    await exchangesPage.addExchange(apiKey, apiSecret, 'kraken', 'My Kraken');
    await exchangesPage.exchangeIsAdded('Kraken', 'My Kraken');
  });
});
