import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiGetIgnoredAssets, apiGetSnapshot } from '../../helpers/snapshot-api';
import { type BalanceRow, type LocationRow, writeFixturesToTmp } from '../../helpers/snapshot-csv';
import { DashboardPage } from '../../pages/dashboard-page';
import { SnapshotListPage } from '../../pages/snapshot-list-page';

const DAY_SECONDS = 24 * 60 * 60;
const TIMESTAMP = Math.floor(Date.now() / 1000 / DAY_SECONDS) * DAY_SECONDS - 3 * DAY_SECONDS;

// Marked as spam by this spec, so it must not be one another spec relies on.
const TOKEN = 'eip155:1/erc20:0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F';
const TOKEN_SYMBOL = 'SNX';

const BALANCES: BalanceRow[] = [
  { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
  { amount: '1000', assetIdentifier: TOKEN, category: 'asset', usdValue: '3000' },
];

const LOCATIONS: LocationRow[] = [
  { location: 'blockchain', usdValue: '23000' },
  { location: 'total', usdValue: '23000' },
];

test.describe('removing a snapshot balance and marking its asset as spam', () => {
  let ctx: SharedTestContext;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    const fixtures = writeFixturesToTmp(TIMESTAMP, BALANCES, LOCATIONS);
    try {
      const dashboard = new DashboardPage(ctx.sharedPage);
      await dashboard.visit();
      await dashboard.openSnapshotMenu();
      const importDialog = await dashboard.openImportSnapshotDialog();
      await importDialog.uploadBalanceCsv(fixtures.balancesPath);
      await importDialog.uploadLocationCsv(fixtures.locationsPath);
      await importDialog.import();
      // A successful import logs out after ~3s.
      await ctx.sharedPage.locator('[data-testid=username-input]').waitFor({ state: 'visible', timeout: 10_000 });
      await ctx.app.login(ctx.username);
    }
    finally {
      fixtures.cleanup();
    }
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('marks the asset as spam only once the snapshot is saved', async () => {
    const list = new SnapshotListPage(ctx.sharedPage);
    await list.visit();
    const editor = await list.openEditor(TIMESTAMP);

    await editor.deleteBalanceRowAsSpam(TOKEN_SYMBOL);

    await expect(editor.dirtyBadge).toBeVisible();
    expect(await apiGetIgnoredAssets(ctx.sharedPage.request)).not.toContain(TOKEN);

    await editor.save();

    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, TIMESTAMP);
    expect(snapshot.balances_snapshot.map(item => item.asset_identifier)).toEqual(['ETH']);
    await expect.poll(async () => apiGetIgnoredAssets(ctx.sharedPage.request)).toContain(TOKEN);
    await expect(editor.dirtyBadge).toBeHidden();
  });
});
