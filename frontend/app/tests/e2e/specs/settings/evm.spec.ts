import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { EvmSettingsPage } from '../../pages/evm-settings-page';

test.describe.serial('settings::evm', () => {
  let ctx: SharedTestContext;
  let evmPage: EvmSettingsPage;

  const testChain = 'eth';
  const evmchainsToSkipDetection = ['eth', 'avax', 'optimism', 'polygon_pos', 'arbitrum_one', 'base', 'gnosis', 'scroll'];

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    evmPage = new EvmSettingsPage(ctx.sharedPage);
    await evmPage.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('change chains for which to exclude token detection and validate UI message', async () => {
    for (let i = 0; i < evmchainsToSkipDetection.length; i++) {
      const chain = evmchainsToSkipDetection[i];
      const isLast = i === evmchainsToSkipDetection.length - 1;
      await evmPage.selectChainToIgnore(chain, isLast);
    }

    await ctx.sharedPage.keyboard.press('Escape');
    await evmPage.verifySkipped(evmchainsToSkipDetection);
  });

  test('displays indexer order setting section', async () => {
    await expect(evmPage.getIndexerOrderSection()).toBeVisible();
  });

  test('has default tab selected by default', async () => {
    await evmPage.verifyTabExists('default');
  });

  test('can add and remove a chain-specific indexer order', async () => {
    // First ensure the chain is not configured by removing it if it exists
    const isDisabled = await evmPage.isAddChainButtonDisabled();
    if (isDisabled) {
      // All chains are configured, remove one first
      await evmPage.removeChain(testChain);
      await evmPage.verifyTabNotExists(testChain);
    }

    // Now add the chain
    await evmPage.addChain(testChain);
    await evmPage.verifyTabExists(testChain);

    // Switch between tabs
    await evmPage.selectTab('default');
    await evmPage.selectTab(testChain);

    // Remove the chain
    await evmPage.removeChain(testChain);
    await evmPage.verifyTabNotExists(testChain);
  });

  test('verify settings persist after navigation', async () => {
    await evmPage.addChain(testChain);
    await evmPage.verifyTabExists(testChain);
    await evmPage.navigateAway();
    await evmPage.visit();
    await evmPage.verifyTabExists(testChain);
  });

  test('verify settings persist after re-login', async () => {
    await ctx.app.relogin(ctx.username);
    await evmPage.visit();
    await evmPage.verifyTabExists(testChain);
    await evmPage.verifySkipped(evmchainsToSkipDetection);
  });
});
