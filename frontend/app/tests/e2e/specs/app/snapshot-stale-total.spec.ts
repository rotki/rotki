import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiGetSnapshot } from '../../helpers/snapshot-api';
import { type SnapshotFixturePaths, writeFixturesToTmp } from '../../helpers/snapshot-csv';
import { DashboardPage } from '../../pages/dashboard-page';

const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60;
const SNAPSHOT_TIMESTAMP = Math.floor(Date.now() / 1000 / 86400) * 86400 - SEVEN_DAYS_SECONDS;

test.describe.serial('snapshot with a stale stored total', () => {
  let ctx: SharedTestContext;
  let fixtures: SnapshotFixturePaths;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    // Balances and locations agree on 50000; only the stored total is stale.
    fixtures = writeFixturesToTmp(
      SNAPSHOT_TIMESTAMP,
      [
        { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
        { amount: '0.5', assetIdentifier: 'BTC', category: 'asset', usdValue: '30000' },
      ],
      [
        { location: 'blockchain', usdValue: '50000' },
        { location: 'total', usdValue: '70000' },
      ],
    );
  });

  test.afterAll(async () => {
    fixtures?.cleanup();
    await cleanupContext(ctx);
  });

  test('opens with the correction as an unsaved change and saves it', async () => {
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

    await dashboard.visit();
    const editor = await dashboard.openSnapshotEditorAt();
    await expect(editor.dirtyBadge).toBeVisible();

    await editor.save();
    await expect(editor.dirtyBadge).toBeHidden();

    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, SNAPSHOT_TIMESTAMP);
    const total = snapshot.location_data_snapshot.find(item => item.location === 'total')?.usd_value;
    expect(Number(total)).toBe(50000);
  });
});
