import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { type BankRequests, fakeBankEndpoints, fakeBankIdentifier, type FakeBankSetup } from '../../helpers/banks-api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { BanksPage } from '../../pages/banks-page';
import { DashboardPage } from '../../pages/dashboard-page';

const HEALTHY = 'rotki Solutions GmbH';
const REVOKED = 'Revoked key organization';
const ADDED = 'Newly added organization';
const NEEDS_TAN = 'Organization behind a TAN';

test.describe.serial('bank connections', () => {
  let ctx: SharedTestContext;
  let banksPage: BanksPage;
  let requests: BankRequests;

  const setup: FakeBankSetup = {
    connections: [
      { lastSyncTs: 1757595000, name: HEALTHY },
      { lastError: '401 Unauthorized: the API key was revoked', lastSyncTs: 1757000000, name: REVOKED },
      { lastSyncTs: 1757000000, name: NEEDS_TAN },
    ],
    failingSyncs: { [REVOKED]: '401 Unauthorized: the API key was revoked' },
    pausedSyncs: { [NEEDS_TAN]: 'Enter the TAN from your banking app' },
    usdBalance: '250',
  };

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    requests = await fakeBankEndpoints(ctx.sharedPage, setup);
    banksPage = new BanksPage(ctx.sharedPage);
    await banksPage.visitConnections();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('should list the connections with the failed sync of the revoked one', async () => {
    await expect(banksPage.connectionRow(HEALTHY)).toBeVisible();
    await expect(banksPage.connectionRow(HEALTHY).locator('[data-testid=bank-sync-error]')).toHaveCount(0);
    await expect(banksPage.connectionRow(REVOKED).locator('[data-testid=bank-sync-error]')).toBeVisible();
  });

  test('should keep the add dialog open and show the reason when Qonto rejects the key', async () => {
    setup.rejectCredentials = 'Qonto rejected the credentials: 401 Unauthorized';
    try {
      await banksPage.openAddDialog();
      await banksPage.fillConnection('Rejected organization', 'rejected-login', 'rejected-secret');
      await banksPage.save();
      await banksPage.expectSetupError('Qonto rejected the credentials');
      await expect(ctx.sharedPage.locator('[data-testid=message-dialog-description]')).toHaveCount(0);
      await banksPage.cancel();
    }
    finally {
      setup.rejectCredentials = undefined;
    }
    await expect(banksPage.connectionRow('Rejected organization')).toHaveCount(0);
  });

  test('should send the name and the credentials keyed by manifest slot when adding', async () => {
    const addedBefore = requests.added.length;
    await banksPage.openAddDialog();
    await banksPage.fillConnection(ADDED, 'organization-login', 'organization-secret');
    await banksPage.saveAndClose();

    expect(requests.added.slice(addedBefore)).toEqual([{
      connector: 'qonto',
      credentials: { api_key: 'organization-login', api_secret: 'organization-secret' },
      location: 'qonto',
      name: ADDED,
    }]);
    await expect(banksPage.connectionRow(ADDED)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await expect.poll(() => requests.synced.some(sync => sync.identifier === fakeBankIdentifier(ADDED)), { timeout: TIMEOUT_MEDIUM }).toBe(true);
  });

  test('should sync only the connection picked from its row', async () => {
    const syncedBefore = requests.synced.length;
    await banksPage.syncConnection(REVOKED);

    await expect.poll(() => requests.synced.slice(syncedBefore), { timeout: TIMEOUT_MEDIUM })
      .toEqual([expect.objectContaining({ identifier: fakeBankIdentifier(REVOKED) })]);
  });

  test('should show the bank balance on Balances > Banks', async () => {
    await banksPage.visitBalances();
    await expect(banksPage.balancesTable()).toContainText('Qonto', { timeout: TIMEOUT_MEDIUM });
    await expect(banksPage.balancesTable()).toContainText('250');
  });

  test('should name each connection in the balances toolbar with what it needs', async () => {
    await expect(banksPage.balancesConnection(HEALTHY)).toHaveAttribute('data-state', 'ok');
    const revoked = banksPage.balancesConnection(REVOKED);
    await expect(revoked).toHaveAttribute('data-state', 'failed');
    await expect(revoked).toContainText('401 Unauthorized: the API key was revoked');

    await revoked.locator('[data-testid=bank-balances-connection-action]').click();
    await expect(ctx.sharedPage).toHaveURL(/\/api-keys\/banks/);
  });

  test('should show the same bank total on the dashboard card', async () => {
    await new DashboardPage(ctx.sharedPage).visit();
    await expect(banksPage.dashboardCard()).toContainText('Qonto', { timeout: TIMEOUT_MEDIUM });
    await expect(banksPage.dashboardCard().locator('[data-testid=display-amount]')).toContainText('250');
  });

  test('should sync only the bank connection picked in the history refresh menu', async () => {
    const syncedBeforeVisit = requests.synced.length;
    await banksPage.visitHistory();
    await expect.poll(() => requests.synced.length, {
      message: 'the first history visit refreshes the banks, so wait for that refresh to start before picking one',
      timeout: TIMEOUT_MEDIUM,
    }).toBeGreaterThan(syncedBeforeVisit);
    await banksPage.openRefreshMenuBanks();
    const syncedBefore = requests.synced.length;

    await banksPage.refreshPickedBank(HEALTHY);
    await banksPage.waitForRefreshSettled();

    expect(requests.synced.slice(syncedBefore)).toEqual([expect.objectContaining({ identifier: fakeBankIdentifier(HEALTHY) })]);
  });

  test('should lead from a sync paused for a TAN to answering it with only the connection identity', async () => {
    await banksPage.visitConnections();
    await banksPage.syncConnection(NEEDS_TAN);
    await expect(banksPage.actionCenterButton()).toHaveAttribute('aria-label', /needs you now/, { timeout: TIMEOUT_MEDIUM });
    await banksPage.authenticateFromActionCenter(NEEDS_TAN);

    await expect(banksPage.dialog().locator('[data-testid=bank-auth-challenge]')).toContainText('Enter the TAN from your banking app', { timeout: TIMEOUT_MEDIUM });
    await expect(banksPage.connectionRow(NEEDS_TAN).locator('[data-testid=bank-auth-required]')).toBeVisible();
    await banksPage.answerTan('123456');

    await banksPage.dialog().waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
    expect(requests.authenticated).toEqual([{ identifier: fakeBankIdentifier(NEEDS_TAN), response: '123456' }]);
    await expect(banksPage.connectionRow(NEEDS_TAN).locator('[data-testid=bank-auth-required]')).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
    await expect(banksPage.actionCenterButton()).not.toHaveAttribute('aria-label', /needs you now/);
  });
});

test.describe.serial('bank balances without connections', () => {
  let ctx: SharedTestContext;
  let banksPage: BanksPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    await fakeBankEndpoints(ctx.sharedPage, { connections: [], usdBalance: '0' });
    banksPage = new BanksPage(ctx.sharedPage);
    await banksPage.visitBalances();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('should explain the page and open the add dialog on the bank picked', async () => {
    await expect(banksPage.balancesEmpty()).toBeVisible({ timeout: TIMEOUT_MEDIUM });
    await expect(ctx.sharedPage.locator('[data-testid=refresh-bank-balances]')).toHaveCount(0);

    await banksPage.balancesEmpty().locator('[data-testid=bank-balances-empty-shortcut][data-bank=qonto]').click();
    await banksPage.dialog().waitFor({ state: 'visible', timeout: TIMEOUT_MEDIUM });
    await expect(ctx.sharedPage.locator('[data-testid=bank-connection-secret-api_key]')).toBeVisible();
  });
});
