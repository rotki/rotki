import { test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { RpcSettingsPage } from '../../pages/rpc-settings-page';

test.describe.serial('settings::rpc', () => {
  let ctx: SharedTestContext;
  let pageRpc: RpcSettingsPage;

  const name = 'local';
  const endpoint = 'http://localhost:9001';

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);

    // Navigate to RPC settings once
    pageRpc = new RpcSettingsPage(ctx.sharedPage);
    await pageRpc.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add ethereum rpc', async () => {
    await pageRpc.confirmRPCmissing(name, endpoint);
    await pageRpc.addEthereumRPC(name, endpoint);
    await pageRpc.confirmRPCAddition(name, endpoint);
  });

  test('verify changed settings after changing rpc', async () => {
    await pageRpc.navigateAway();
    await pageRpc.visit();
    await pageRpc.confirmRPCAddition(name, endpoint);
  });

  test('verify settings persist after re-login', async () => {
    await ctx.app.relogin(ctx.username);
    await pageRpc.visit();
    await pageRpc.confirmRPCAddition(name, endpoint);
  });

  test('deep-link via ?tab= selects the Beacon Node and hides Add Node', async () => {
    await pageRpc.visitWithTab('eth_consensus_layer');
    await pageRpc.expectActiveTab('ETH Beacon Node');
    await pageRpc.expectAddNodeHidden();
  });

  test('clicking a rail tab updates the URL', async () => {
    await pageRpc.visit();
    await pageRpc.clickRailTab('Polkadot');
    await pageRpc.expectUrlTab('dot');
    await pageRpc.expectActiveTab('Polkadot');
  });

  test('Add Node is hidden on every single-value endpoint', async () => {
    for (const label of ['Bitcoin Mempool', 'Kusama', 'Polkadot', 'ETH Beacon Node']) {
      await pageRpc.clickRailTab(label);
      await pageRpc.expectAddNodeHidden();
    }
  });

  test('Add Node is visible on EVM chains and Solana', async () => {
    for (const label of ['Ethereum', 'Solana']) {
      await pageRpc.clickRailTab(label);
      await pageRpc.expectAddNodeVisible();
    }
  });

  test('Solana is grouped under Other endpoints, not EVM chains', async () => {
    await pageRpc.visit();
    await pageRpc.expectSolanaUnderOtherEndpoints();
  });
});

test.describe.serial('settings::rpc narrow viewport', () => {
  let ctx: SharedTestContext;
  let pageRpc: RpcSettingsPage;

  // Below the Tailwind md breakpoint (768px) the rail collapses into dropdowns.
  test.use({ viewport: { width: 600, height: 800 } });

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    pageRpc = new RpcSettingsPage(ctx.sharedPage);
    await ctx.sharedPage.locator('[data-cy=user-menu-button]').click();
    await ctx.sharedPage.locator('[data-cy=user-dropdown]').waitFor({ state: 'visible' });
    await ctx.sharedPage.locator('[data-cy=settings-button]').click();
    await ctx.sharedPage.locator('[data-cy=user-dropdown]').waitFor({ state: 'detached' });
    await ctx.sharedPage.locator('[data-cy="settings__rpc"]').click();
    await ctx.sharedPage.getByTestId('rpc-settings-dropdowns').waitFor({ state: 'visible' });
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('shows dropdown fallback instead of the rail', async () => {
    await pageRpc.expectDropdownFallbackVisible();
  });
});
