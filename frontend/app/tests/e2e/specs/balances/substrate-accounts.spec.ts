import type { FixtureBlockchainAccount } from '../../pages/types';
import { expect, test } from '@playwright/test';
import { BigNumber, Blockchain } from '@rotki/common';
import { testEnv } from '../../fixtures';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { TEST_TIMEOUT_BLOCKCHAIN } from '../../helpers/constants';
import { BlockchainAccountsPage } from '../../pages/blockchain-accounts-page';

test.describe.serial('substrate accounts', () => {
  test.setTimeout(TEST_TIMEOUT_BLOCKCHAIN);

  let ctx: SharedTestContext;
  const polkadotAccount: FixtureBlockchainAccount = {
    blockchain: Blockchain.DOT,
    inputMode: 'manual_add',
    chainName: 'Polkadot',
    address: testEnv.POLKADOT_ADDRESS,
    label: 'Polkadot 1',
    tags: [],
  };

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, {
      disableModules: true,
      rpcMockCassette: 'substrate-accounts',
      rpcMockChains: ['DOT'],
    });
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add a Polkadot account and view it in the table', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    await blockchainAccountsPage.visit('substrate');
    await blockchainAccountsPage.openAddDialog();
    await blockchainAccountsPage.addAccount(polkadotAccount);
    await blockchainAccountsPage.isEntryVisible(0, polkadotAccount);
    await expect(ctx.sharedPage.locator('[data-cy=blockchain-account-refresh]')).not.toBeDisabled();
    await waitForNoRunningTasks(ctx.sharedPage);

    const row = ctx.sharedPage.locator('[data-cy=account-table] tbody tr[data-id="row"]').first();
    const usdValueText = await row.locator('[data-cy=usd-value] [data-cy=display-amount]').textContent();
    expect(usdValueText, 'USD value should be displayed for the Polkadot account').not.toBeNull();
    expect(new BigNumber((usdValueText ?? '').replace(/,/g, '')).gt(0)).toBe(true);
  });

  test('edit a Polkadot account label', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);
    const newLabel = 'New Polkadot label';

    await blockchainAccountsPage.visit('substrate');
    await blockchainAccountsPage.editAccount(0, newLabel);
    await blockchainAccountsPage.isEntryVisible(0, { ...polkadotAccount, label: newLabel });
  });

  test('delete a Polkadot account', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    await blockchainAccountsPage.visit('substrate');
    await blockchainAccountsPage.deleteAccount(0);
  });
});
