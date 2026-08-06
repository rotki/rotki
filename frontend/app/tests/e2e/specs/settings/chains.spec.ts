import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { ChainsSettingsPage } from '../../pages/chains-settings-page';

test.describe.serial('settings::chains', () => {
  let ctx: SharedTestContext;
  let chainsPage: ChainsSettingsPage;

  const testChain = 'eth';
  const evmchainsToSkipDetection = ['eth', 'avax', 'optimism', 'polygon_pos', 'arbitrum_one', 'base', 'gnosis', 'scroll'];

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    chainsPage = new ChainsSettingsPage(ctx.sharedPage);
    await chainsPage.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('groups query skipping and detection skipping under one category', async () => {
    await chainsPage.verifyChainQueriesCategory();
  });

  test('change chains to exclude from account activity detection and validate UI message', async () => {
    for (let i = 0; i < evmchainsToSkipDetection.length; i++) {
      const chain = evmchainsToSkipDetection[i];
      const isLast = i === evmchainsToSkipDetection.length - 1;
      await chainsPage.selectChainToIgnore(chain, isLast);
    }

    await ctx.sharedPage.keyboard.press('Escape');
    await chainsPage.verifySkipped(evmchainsToSkipDetection);
  });

  test('displays indexer order setting section', async () => {
    await expect(chainsPage.getIndexerOrderSection()).toBeVisible();
  });

  test('has default tab selected by default', async () => {
    await chainsPage.verifyTabExists('default');
  });

  test('can add and remove a chain-specific indexer order', async () => {
    // First ensure the chain is not configured by removing it if it exists
    const isDisabled = await chainsPage.isAddChainButtonDisabled();
    if (isDisabled) {
      // All chains are configured, remove one first
      await chainsPage.removeChain(testChain);
      await chainsPage.verifyTabNotExists(testChain);
    }

    // Now add the chain
    await chainsPage.addChain(testChain);
    await chainsPage.verifyTabExists(testChain);

    // Switch between tabs
    await chainsPage.selectTab('default');
    await chainsPage.selectTab(testChain);

    // Remove the chain
    await chainsPage.removeChain(testChain);
    await chainsPage.verifyTabNotExists(testChain);
  });

  test('verify settings persist after navigation', async () => {
    await chainsPage.addChain(testChain);
    await chainsPage.verifyTabExists(testChain);
    await chainsPage.navigateAway();
    await chainsPage.visit();
    await chainsPage.verifyTabExists(testChain);
  });

  test('verify settings persist after re-login', async () => {
    await ctx.app.relogin(ctx.username);
    await chainsPage.visit();
    await chainsPage.verifyTabExists(testChain);
    await chainsPage.verifySkipped(evmchainsToSkipDetection);
  });
});
