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
});
