import { expect, type Page, type Route } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { installMockWallet, MOCK_TX_HASH, setMockWalletRejects } from '../../helpers/mock-wallet';
import { SendPage } from '../../pages/send-page';

/** Not tracked by the test user, which never tracks anything, so the page treats it as unknown. */
const WALLET = '0x5a0b54d5dc17e0aadc383d2db43b0a0d3e029c4c';

/** Tracked only as far as the stubbed backend says so; see {@link stubTrackedWallet}. */
const TRACKED_WALLET = '0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed';

const RECIPIENT = '0x000000000000000000000000000000000000dEaD';

async function fulfillResult(route: Route, result: unknown): Promise<void> {
  await route.fulfill({ json: { message: '', result } });
}

/**
 * Makes the backend report {@link TRACKED_WALLET} as a tracked account holding 1.5 ETH, and
 * prepare any native transfer asked of it, recording each request in `transfers`.
 *
 * @remarks
 * Tracking an address for real starts balance queries against chains, which outlive the test.
 * Stubbing what the page reads instead keeps it to the requests the send form makes: the accounts
 * and the cached balances (read once the page reloads), the wallet's balance of the chosen asset,
 * the interaction check and the transfer preparation.
 */
async function stubTrackedWallet(page: Page, transfers: unknown[]): Promise<void> {
  const balance = { amount: '1.5', value: '3000' };
  const held = {
    last_refresh_ts: {},
    per_account: { eth: { [TRACKED_WALLET]: { assets: { ETH: { address: balance } }, liabilities: {} } } },
    totals: { assets: { ETH: { address: balance } }, liabilities: {} },
  };
  const nothing = { last_refresh_ts: {}, per_account: {}, totals: { assets: {}, liabilities: {} } };

  await page.route(/\/api\/1\/blockchains\/eth\/accounts(\?|$)/, async (route) => {
    if (route.request().method() !== 'GET')
      return route.continue();
    return fulfillResult(route, [{ address: TRACKED_WALLET, label: null, tags: null }]);
  });
  // A refresh's task result replaces the cached balances, so each completes with the same ones.
  const refreshTasks = new Map<number, unknown>();
  let nextTaskId = 990_001;
  const balancesFor = (url: string): unknown => {
    const chain = new URL(url).pathname.split('/').pop();
    return chain === 'eth' || chain === 'blockchains' ? held : nothing;
  };
  await page.route(/\/api\/1\/balances\/blockchains(\/[a-z0-9_]+)?(\?|$)/, async (route) => {
    const request = route.request();
    if (request.method() === 'GET')
      return fulfillResult(route, balancesFor(request.url()));
    if (request.method() !== 'POST')
      return route.continue();
    const id = nextTaskId++;
    refreshTasks.set(id, balancesFor(request.url()));
    return fulfillResult(route, { task_id: id });
  });
  await page.route('**/api/1/tasks', async (route) => {
    if (route.request().method() !== 'GET' || refreshTasks.size === 0)
      return route.continue();
    const response = await route.fetch();
    const json = await response.json();
    const result = json.result ?? { completed: [], pending: [] };
    const completed = [...new Set([...(result.completed ?? []), ...refreshTasks.keys()])];
    return route.fulfill({ json: { ...json, result: { ...result, completed } }, response });
  });
  await page.route('**/api/1/tasks/*', async (route) => {
    const id = Number(new URL(route.request().url()).pathname.split('/').pop());
    const balances = refreshTasks.get(id);
    if (route.request().method() !== 'GET' || balances === undefined)
      return route.continue();
    refreshTasks.delete(id);
    return fulfillResult(route, { outcome: { message: '', result: balances }, status: 'completed', status_code: 200 });
  });
  await page.route('**/api/1/wallet/balance', async route => fulfillResult(route, '1.5'));
  await page.route('**/api/1/wallet/interacted', async route => fulfillResult(route, true));
  await page.route('**/api/1/wallet/transfer/native', async (route) => {
    transfers.push(route.request().postDataJSON());
    return fulfillResult(route, { from: TRACKED_WALLET, nonce: 1, to: RECIPIENT, value: 100000000000000000 });
  });
}

test.describe.serial('onchain send', () => {
  let ctx: SharedTestContext;
  let sendPage: SendPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    // Stubbed so the never-interacted check cannot start a chain query; the answer is the backend's.
    await ctx.sharedPage.route('**/api/1/wallet/interacted', async route => route.fulfill({ json: { message: '', result: false } }));
    sendPage = new SendPage(ctx.sharedPage);
    await sendPage.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('should offer the connection mode and a single connect button before connecting', async () => {
    await expect(sendPage.modeSwitch).toBeVisible();
    await expect(sendPage.addressBadge).toHaveCount(0);
    await expect(ctx.sharedPage.getByRole('button', { name: 'Connect Wallet' })).toHaveCount(1);
  });

  test('should say so when no wallet is installed, once its three detection attempts give up', async () => {
    await sendPage.connect();

    await expect(sendPage.error).toContainText('No wallet providers detected', { timeout: TIMEOUT_MEDIUM * 2 });
    await sendPage.error.locator('button').click();
    await expect(sendPage.error).toHaveCount(0);
  });

  test('should connect to a wallet without moving the form', async () => {
    await installMockWallet(ctx.sharedPage, { address: WALLET });
    const recipientTop = await sendPage.topOf(sendPage.recipientField);

    await sendPage.connect();

    await expect(sendPage.addressBadge).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await expect(sendPage.modeSwitch).toHaveCount(0);
    expect(await sendPage.topOf(sendPage.recipientField)).toBe(recipientTop);
  });

  test('should name an untracked wallet in the header and offer to track it', async () => {
    await expect(sendPage.untrackedStatus).toBeVisible();
    await expect(sendPage.trackButton).toBeVisible();
  });

  test('should mark a recipient never interacted with inside the field, without moving the form', async () => {
    const fieldHeight = (await sendPage.recipientField.boundingBox())?.height;
    const trackTop = await sendPage.topOf(sendPage.trackButton);

    await sendPage.enterRecipient(RECIPIENT);

    await expect(sendPage.newAddressChip).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    expect((await sendPage.recipientField.boundingBox())?.height).toBe(fieldHeight);
    expect(await sendPage.topOf(sendPage.trackButton)).toBe(trackTop);

    await sendPage.clearRecipient();
    await expect(sendPage.newAddressChip).toHaveCount(0);
    expect((await sendPage.recipientField.boundingBox())?.height).toBe(fieldHeight);
  });

  test('should search the address book dialog and close it from its header', async () => {
    await sendPage.openAddressBook();
    const dialog = sendPage.dialog();

    await expect(dialog.locator('[data-testid=recipient-dialog-search]')).toBeVisible();
    await expect(dialog.locator('[data-testid=recipient-dialog-empty]')).toBeVisible();

    await sendPage.closeAddressBook();
  });

  test('should keep the transactions dialog one height across its tabs', async () => {
    await sendPage.openHistory();
    const dialog = sendPage.dialog();
    const heights: number[] = [];

    for (const tab of ['All', 'Completed', 'Pending', 'Failed']) {
      await dialog.getByRole('tab', { name: tab }).click();
      // Measured once the tab change has finished animating, when only one tab's content shows.
      await expect(dialog.locator('[data-testid=trade-history-empty]').locator('visible=true')).toHaveCount(1);
      heights.push(Math.round((await dialog.boundingBox())?.height ?? 0));
    }

    expect(new Set(heights).size).toBe(1);
    await sendPage.closeHistory();
  });

  test('should disconnect from the address badge', async () => {
    await sendPage.disconnect();

    await expect(sendPage.connectButton).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await expect(sendPage.modeSwitch).toBeVisible();
    await expect(sendPage.untrackedStatus).toHaveCount(0);
  });

  test('should take an untracked wallet to the account form, prefilled', async () => {
    await sendPage.connect();
    await expect(sendPage.trackButton).toBeVisible({ timeout: TIMEOUT_MEDIUM });

    await sendPage.trackButton.click();

    // The accounts page reads the address from the link and drops the query, so the form is checked.
    await expect(ctx.sharedPage).toHaveURL(/\/accounts\/evm\/accounts/);
    const address = ctx.sharedPage.locator('[data-testid=account-address-field] input').first();
    await expect(address).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await expect(address).toHaveValue(new RegExp(WALLET, 'i'));
  });
});

test.describe.serial('onchain send from a tracked wallet', () => {
  let ctx: SharedTestContext;
  let sendPage: SendPage;
  const transfers: unknown[] = [];

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    await stubTrackedWallet(ctx.sharedPage, transfers);
    sendPage = new SendPage(ctx.sharedPage);
    await sendPage.visit();
    // The accounts and balances are read once at login, so the stubbed ones need a reload to land.
    await ctx.sharedPage.reload();
    await sendPage.connectButton.waitFor({ state: 'visible' });
    await installMockWallet(ctx.sharedPage, { address: TRACKED_WALLET, chainId: '0x89' });
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('should ask to switch a wallet on another chain over to the asset\'s chain', async () => {
    await sendPage.connect();
    await expect(sendPage.addressBadge).toBeVisible({ timeout: TIMEOUT_MEDIUM });

    // The form starts on the wallet's chain; picking an asset on another is what needs the switch.
    await sendPage.chooseAsset('Ethereum', 'ETH');

    await expect(sendPage.switchNetworkButton).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await sendPage.switchNetworkButton.click();
    await expect(sendPage.sendButton).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  });

  test('should treat the wallet as tracked and show what it holds of the asset', async () => {
    await expect(sendPage.untrackedStatus).toHaveCount(0);
    await expect(sendPage.selectedBalance).toContainText('1.5', { timeout: TIMEOUT_MEDIUM });
  });

  test('should refuse an amount above what the wallet can send', async () => {
    await sendPage.enterRecipient(RECIPIENT);
    await sendPage.enterAmount('5');

    await expect(sendPage.amountError).toHaveText('Insufficient Funds');
    await expect(sendPage.sendButton).toBeDisabled();
  });

  test('should report a send the wallet rejects and keep the form as it was', async () => {
    await sendPage.enterAmount('0.1');
    await expect(sendPage.amountError).toHaveText('');
    await expect(sendPage.sendButton).toBeEnabled({ timeout: TIMEOUT_MEDIUM });
    await setMockWalletRejects(ctx.sharedPage, true);

    await sendPage.sendButton.click();

    await expect(sendPage.error).toContainText('Request is rejected by user', { timeout: TIMEOUT_MEDIUM });
    await expect(sendPage.amountInput).toHaveValue('0.1');
    await sendPage.error.locator('button').click();
  });

  test('should send, clear the form and list the transaction as completed', async () => {
    await setMockWalletRejects(ctx.sharedPage, false);
    const before = transfers.length;

    await sendPage.sendButton.click();

    await expect(sendPage.amountInput).toHaveValue('', { timeout: TIMEOUT_MEDIUM });
    expect(transfers.slice(before)).toEqual([
      expect.objectContaining({ amount: '0.1', from_address: TRACKED_WALLET, to_address: RECIPIENT }),
    ]);

    await sendPage.openHistory();
    const status = sendPage.dialog().locator('[data-testid=trade-history-status]');
    await expect(status).toHaveText('Completed', { timeout: TIMEOUT_MEDIUM });
    await expect(sendPage.dialog()).toContainText(/just now|ago/);
    await expect(sendPage.dialog()).toContainText(MOCK_TX_HASH.slice(0, 6));
    await sendPage.closeHistory();
  });
});
