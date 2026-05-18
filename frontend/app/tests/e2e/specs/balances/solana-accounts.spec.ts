import type { FixtureBlockchainAccount } from '../../pages/types';
import { expect, test } from '@playwright/test';
import { Blockchain } from '@rotki/common';
import { testEnv } from '../../fixtures';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { TEST_TIMEOUT_BLOCKCHAIN } from '../../helpers/constants';
import { BlockchainAccountsPage } from '../../pages/blockchain-accounts-page';

test.describe.serial('solana accounts', () => {
  test.setTimeout(TEST_TIMEOUT_BLOCKCHAIN);

  let ctx: SharedTestContext;
  const solanaAccount: FixtureBlockchainAccount = {
    blockchain: Blockchain.SOLANA,
    inputMode: 'manual_add',
    chainName: 'Solana',
    address: testEnv.SOLANA_ADDRESS,
    label: 'Solana 1',
    tags: [],
  };

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, {
      disableModules: true,
      rpcMockCassette: 'solana-accounts',
      rpcMockChains: ['SOLANA'],
    });
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add a Solana account and view it in the table', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    await blockchainAccountsPage.visit('solana');
    await blockchainAccountsPage.openAddDialog();
    await blockchainAccountsPage.addAccount(solanaAccount);
    await blockchainAccountsPage.isEntryVisible(0, solanaAccount);
    await expect(ctx.sharedPage.locator('[data-cy=blockchain-account-refresh]')).not.toBeDisabled();
    await waitForNoRunningTasks(ctx.sharedPage);
  });

  test('edit a Solana account label', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);
    const newLabel = 'New Solana label';

    await blockchainAccountsPage.visit('solana');
    await blockchainAccountsPage.editAccount(0, newLabel);
    await blockchainAccountsPage.isEntryVisible(0, { ...solanaAccount, label: newLabel });
  });

  test('delete a Solana account', async () => {
    const blockchainAccountsPage = new BlockchainAccountsPage(ctx.sharedPage);

    await blockchainAccountsPage.visit('solana');
    await blockchainAccountsPage.deleteAccount(0);
  });
});
