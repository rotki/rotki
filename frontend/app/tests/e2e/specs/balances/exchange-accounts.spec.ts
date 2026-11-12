import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { fakeExchangeEndpoints, type FakeExchangeSetup } from '../../helpers/exchange-balances-api';
import { ExchangeBalancesPage } from '../../pages/exchange-balances-page';

const MAIN = '6f1d2c3a-9b8e-4f7a-a1b2-0c9d8e7f6a51';
const BOT = 'b2e4f6a8-1c3d-4e5f-8a9b-7c6d5e4f3a22';
const SAVINGS = 'c9a8b7d6-5e4f-4a3b-9c2d-1e0f9a8b7c33';
const DORMANT = 'd4c3b2a1-0f9e-4d8c-b7a6-5f4e3d2c1b44';
const COINBASE = 'e1f2a3b4-c5d6-4e7f-8a9b-0c1d2e3f4a55';

/* Four Kraken connections, one failing its first refresh and one holding nothing, beside a single
   Coinbase connection. Values are in USD so the largest account stays largest whatever the price
   oracles answer for the other assets. */
test.describe.serial('exchange account picker', () => {
  let ctx: SharedTestContext;
  let exchangePage: ExchangeBalancesPage;

  const setup: FakeExchangeSetup = {
    connections: [
      { balances: { BTC: { amount: '0.01', value: '1000' } }, identifier: SAVINGS, location: 'kraken', name: 'Savings' },
      { balances: { USD: { amount: '500', value: '500' } }, identifier: BOT, location: 'kraken', name: 'Trading bot' },
      { balances: { ETH: { amount: '1', value: '2000' }, USD: { amount: '3000', value: '3000' } }, identifier: MAIN, location: 'kraken', name: 'Main' },
      { balances: {}, identifier: DORMANT, location: 'kraken', name: 'Dormant' },
      { balances: { USD: { amount: '100', value: '100' } }, identifier: COINBASE, location: 'coinbase', name: 'Coinbase' },
    ],
    failing: { [BOT]: 'Kraken API request failed: EAPI:Invalid nonce' },
  };

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    await fakeExchangeEndpoints(ctx.sharedPage, setup);
    await ctx.sharedPage.reload();
    exchangePage = new ExchangeBalancesPage(ctx.sharedPage);
    await exchangePage.visit();
    await exchangePage.openExchange('kraken');
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('should list every kraken connection after all accounts, the largest first', async () => {
    await exchangePage.expectPicked('All accounts');
    await exchangePage.openPicker();
    const order = async (): Promise<(string | null)[]> =>
      exchangePage.options().evaluateAll(options => options.map(option => option.getAttribute('data-account')));

    await expect.poll(async () => (await order()).slice(0, 2), { timeout: TIMEOUT_MEDIUM }).toEqual(['all', MAIN]);
    expect((await order()).slice(2)).toEqual(expect.arrayContaining([SAVINGS, BOT, DORMANT]));
  });

  test('should mark the connection whose refresh failed as not loaded, and the empty one as empty', async () => {
    const bot = exchangePage.option(BOT);
    await expect(bot.locator('[data-testid=exchange-account-option-failed]')).toBeVisible();
    await expect(bot.locator('[data-testid=exchange-account-option-unknown]')).toBeVisible();
    await expect(bot).toHaveAttribute('data-empty', 'false');

    await expect(exchangePage.option(DORMANT)).toHaveAttribute('data-empty', 'true');
    await expect(exchangePage.option(MAIN).locator('[data-testid=exchange-account-option-failed]')).toHaveCount(0);
  });

  test('should pick an account when its value is clicked, and show only its assets', async () => {
    await exchangePage.option(MAIN).locator('[data-testid=display-amount]').click();

    await exchangePage.expectPicked('Main');
    await expect(exchangePage.picker()).toHaveAttribute('aria-expanded', 'false');
    await expect(ctx.sharedPage).toHaveURL(new RegExp(`account=${MAIN}`));
    await expect(exchangePage.table()).toContainText('ETH');
    await expect(exchangePage.table()).not.toContainText('BTC');
  });

  test('should keep the picked account across a reload', async () => {
    await ctx.sharedPage.reload();

    await exchangePage.expectPicked('Main');
    await expect(exchangePage.table()).toContainText('ETH');
    await expect(exchangePage.table()).not.toContainText('BTC');
  });

  test('should call an account holding nothing empty, though another account failed', async () => {
    await exchangePage.pick(DORMANT);

    await exchangePage.expectPicked('Dormant');
    await expect(exchangePage.emptyNotice()).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await expect(exchangePage.refreshFailedNotice()).toHaveCount(0);
  });

  test('should call the failed account unknown rather than empty', async () => {
    await exchangePage.pick(BOT);

    await exchangePage.expectPicked('Trading bot');
    await expect(exchangePage.refreshFailedNotice()).toBeVisible();
  });

  test('should clear the failure once a refresh of the exchange succeeds', async () => {
    delete setup.failing[BOT];
    await exchangePage.refresh();
    await expect(exchangePage.table()).toContainText('USD', { timeout: TIMEOUT_MEDIUM });
    await expect(exchangePage.refreshFailedNotice()).toHaveCount(0);

    await exchangePage.openPicker();
    const bot = exchangePage.option(BOT);
    await expect(bot).toContainText('500');
    await expect(bot.locator('[data-testid=exchange-account-option-failed]')).toHaveCount(0);
    await expect(bot.locator('[data-testid=exchange-account-option-unknown]')).toHaveCount(0);
    await exchangePage.closePicker();
  });

  test('should offer no picker for an exchange with a single connection, and drop the pick', async () => {
    await exchangePage.openExchange('coinbase');

    await expect(ctx.sharedPage).toHaveURL(/#\/balances\/exchange\/coinbase$/);
    await expect(exchangePage.table()).toContainText('USD');
    await expect(exchangePage.picker()).toHaveCount(0);
  });
});
