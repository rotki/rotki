import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiIgnoreAssets } from '../../helpers/snapshot-api';
import { type SnapshotFixturePaths, writeFixturesToTmp } from '../../helpers/snapshot-csv';
import { DashboardPage } from '../../pages/dashboard-page';
import { SnapshotListPage } from '../../pages/snapshot-list-page';

const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60;
const SNAPSHOT_TIMESTAMP = Math.floor(Date.now() / 1000 / 86400) * 86400 - SEVEN_DAYS_SECONDS;

test.describe.serial('snapshot with an ignored asset', () => {
  let ctx: SharedTestContext;
  let fixtures: SnapshotFixturePaths;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    fixtures = writeFixturesToTmp(
      SNAPSHOT_TIMESTAMP,
      [
        { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
        { amount: '0.5', assetIdentifier: 'BTC', category: 'asset', usdValue: '30000' },
      ],
      [
        { location: 'blockchain', usdValue: '50000' },
        { location: 'total', usdValue: '50000' },
      ],
    );
  });

  test.afterAll(async () => {
    fixtures?.cleanup();
    await cleanupContext(ctx);
  });

  test('headlines the same net worth the snapshot list shows, with ETH ignored before the import re-login loads the list', async () => {
    await apiIgnoreAssets(ctx.sharedPage.request, ['ETH']);

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

    const list = new SnapshotListPage(ctx.sharedPage);
    await list.visit();
    // The table cell wraps the currency symbol, so compare the figures rather than the raw text.
    await expect(list.netWorth(SNAPSHOT_TIMESTAMP)).toContainText('30,000.00');

    const editor = await list.openEditor(SNAPSHOT_TIMESTAMP);
    await expect(editor.netWorth).toContainText('30,000.00');
    await expect(ctx.sharedPage.locator('[data-testid=snapshot-summary-excluded-ignored]')).toContainText('20,000');
  });
});
