import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { type BankRequests, fakeBankEndpoints, type FakeBankSetup } from '../../helpers/banks-api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { BanksPage } from '../../pages/banks-page';
import { DashboardPage } from '../../pages/dashboard-page';

const HEALTHY = 'rotki Solutions GmbH';
const REVOKED = 'Revoked key organization';
const ADDED = 'Newly added organization';

test.describe.serial('bank connections', () => {
  let ctx: SharedTestContext;
  let banksPage: BanksPage;
  let requests: BankRequests;

  const setup: FakeBankSetup = {
    connections: [
      { lastSyncTs: 1757595000, name: HEALTHY },
      { lastError: '401 Unauthorized: the API key was revoked', lastSyncTs: 1757000000, name: REVOKED },
    ],
    failingSyncs: { [REVOKED]: '401 Unauthorized: the API key was revoked' },
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
      await banksPage.expectMessage('Qonto rejected the credentials');
      await banksPage.dismissMessage();
      await expect(banksPage.dialog()).toBeVisible();
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
      credentials: { api_key: 'organization-login', api_secret: 'organization-secret' },
      location: 'qonto',
      name: ADDED,
    }]);
    await expect(banksPage.connectionRow(ADDED)).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  });

  test('should sync only the connection picked from its row', async () => {
    const syncedBefore = requests.synced.length;
    await banksPage.syncConnection(REVOKED);

    await expect.poll(() => requests.synced.slice(syncedBefore), { timeout: TIMEOUT_MEDIUM })
      .toEqual([expect.objectContaining({ location: 'qonto', name: REVOKED })]);
  });

  test('should show the bank balance on Balances > Banks', async () => {
    await banksPage.visitBalances();
    await expect(banksPage.balancesCard()).toContainText('Qonto', { timeout: TIMEOUT_MEDIUM });
    await expect(banksPage.balancesCard()).toContainText('250');
  });

  test('should show the same bank total on the dashboard card', async () => {
    await new DashboardPage(ctx.sharedPage).visit();
    await expect(banksPage.dashboardCard()).toContainText('Qonto', { timeout: TIMEOUT_MEDIUM });
    await expect(banksPage.dashboardCard().locator('[data-testid=display-amount]')).toContainText('250');
  });

  test('should sync only the bank connection picked in the history refresh menu', async () => {
    await banksPage.visitHistory();
    await banksPage.openRefreshMenuBanks();
    const syncedBefore = requests.synced.length;

    await banksPage.refreshPickedBank(HEALTHY);
    await banksPage.waitForRefreshSettled();

    expect(requests.synced.slice(syncedBefore)).toEqual([expect.objectContaining({ location: 'qonto', name: HEALTHY })]);
  });
});
