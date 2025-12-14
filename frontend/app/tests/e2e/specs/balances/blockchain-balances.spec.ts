import type { FixtureBlockchainAccount } from '../../pages/types';
import { expect, test } from '@playwright/test';
import { Blockchain } from '@rotki/common';
import { testEnv } from '../../fixtures';
import blockchainAccountsFixture from '../../fixtures/account-balances/blockchain-accounts.json' with { type: 'json' };
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { BALANCE_PRECISION, TEST_TIMEOUT_BLOCKCHAIN } from '../../helpers/constants';
import { BlockchainAccountsPage } from '../../pages/blockchain-accounts-page';
import { BlockchainBalancesPage } from '../../pages/blockchain-balances-page';
import { DashboardPage } from '../../pages/dashboard-page';
import { TagManager } from '../../pages/tag-manager';

test.describe.serial('blockchain balances', () => {
  // Blockchain tests can take longer due to actual blockchain queries
  test.setTimeout(TEST_TIMEOUT_BLOCKCHAIN);

  let ctx: SharedTestContext;
  let blockchainAccounts: FixtureBlockchainAccount[];

  test.beforeAll(async ({ browser, request }) => {
    blockchainAccounts = blockchainAccountsFixture.map((account): FixtureBlockchainAccount => {
      const addressMap: Record<string, string> = {
        [Blockchain.ETH]: testEnv.ETH_ADDRESS,
        [Blockchain.BTC]: testEnv.BTC_ADDRESS,
      };
      const address = addressMap[account.blockchain] ?? '';
      const blockchain = account.blockchain as Blockchain;

      return { ...account, blockchain, address };
    });

    ctx = await createLoggedInContext(browser, request, { disableModules: true });
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add an ETH account and view the account balance', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);
    const tagManager = new TagManager(ctx.sharedPage);

    await blockchainAccountsPage.visit();
    await blockchainAccountsPage.openAddDialog();
    await tagManager.addTag('[data-cy=account-tag-field]', 'public', 'Public Accounts', 'EF703C', 'FFFFF8');
    await blockchainAccountsPage.addAccount(blockchainAccounts[0]);
    await blockchainAccountsPage.isEntryVisible(0, blockchainAccounts[0]);
    await expect(ctx.sharedPage.locator('[data-cy=blockchain-account-refresh]')).not.toBeDisabled();
    await waitForNoRunningTasks(ctx.sharedPage);
  });

  test('add a BTC account and view the account balance', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    await blockchainAccountsPage.visit('bitcoin');
    await blockchainAccountsPage.openAddDialog();
    await blockchainAccountsPage.addAccount(blockchainAccounts[1]);
    await blockchainAccountsPage.isEntryVisible(0, blockchainAccounts[1]);
    await expect(ctx.sharedPage.locator('[data-cy=blockchain-account-refresh]')).not.toBeDisabled();
    await waitForNoRunningTasks(ctx.sharedPage);
  });

  test('data is reflected in dashboard', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);
    const blockchainBalancesPage = new BlockchainBalancesPage(ctx.sharedPage);
    const dashboardPage = new DashboardPage(ctx.sharedPage);

    const { total, balances } = await blockchainAccountsPage.getTotals();
    await dashboardPage.visit();
    const overallBalance = await dashboardPage.getOverallBalance();
    const nonFungibleBalance = await dashboardPage.getNonFungibleBalances();
    const totalPlusNft = total.plus(nonFungibleBalance);

    expect(overallBalance.toNumber()).toBeGreaterThanOrEqual(totalPlusNft.minus(BALANCE_PRECISION).toNumber());
    expect(overallBalance.toNumber()).toBeLessThanOrEqual(totalPlusNft.plus(BALANCE_PRECISION).toNumber());

    const dashboardBalances = await dashboardPage.getBlockchainBalances();
    const nonZeroBalances = balances.filter(x => x.value.gt(0));

    expect(nonZeroBalances.map(x => x.blockchain).sort()).toEqual(Array.from(dashboardBalances.keys()).sort());

    for (const { blockchain, value } of balances) {
      const dashboardBalance = dashboardBalances.get(blockchain);
      if (value.gt(0)) {
        expect(dashboardBalance).toBeDefined();
        expect(dashboardBalance?.toNumber()).toBeGreaterThanOrEqual(value.minus(BALANCE_PRECISION).toNumber());
        expect(dashboardBalance?.toNumber()).toBeLessThanOrEqual(value.plus(BALANCE_PRECISION).toNumber());
      }
      else {
        expect(dashboardBalance).toBeUndefined();
      }
    }

    const blockchainBalancesTotal = await blockchainBalancesPage.getTotals();
    expect(blockchainBalancesTotal.toNumber()).toBeGreaterThanOrEqual(total.minus(BALANCE_PRECISION).toNumber());
    expect(blockchainBalancesTotal.toNumber()).toBeLessThanOrEqual(total.plus(BALANCE_PRECISION).toNumber());
  });

  test('edit', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    const newLabel = 'New ETH label';
    await blockchainAccountsPage.visit();
    await blockchainAccountsPage.editAccount(0, newLabel);

    await blockchainAccountsPage.isEntryVisible(0, {
      ...blockchainAccounts[0],
      label: newLabel,
    });
  });

  test('delete', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    await blockchainAccountsPage.visit();

    // Delete ETH entry
    await blockchainAccountsPage.deleteAccount(0);

    // Delete BTC entry
    await blockchainAccountsPage.visit('bitcoin');
    await blockchainAccountsPage.deleteAccount(0);
  });
});
