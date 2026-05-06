import fs from 'node:fs';
import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { apiGetSnapshot } from '../../helpers/snapshot-api';
import { type SnapshotFixturePaths, writeFixturesToTmp } from '../../helpers/snapshot-csv';
import { DashboardPage } from '../../pages/dashboard-page';

// Fixed snapshot timestamp seven days back, snapped to midnight UTC. Stable
// enough to be deterministic, far enough in the past to render inside the
// chart's default range, and unlikely to collide with anything else seeded by
// the e2e suite (which uses now-based timestamps).
const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60;
const SNAPSHOT_TIMESTAMP = Math.floor(Date.now() / 1000 / 86400) * 86400 - SEVEN_DAYS_SECONDS;

test.describe.serial('snapshot edit', () => {
  let ctx: SharedTestContext;
  let fixtures: SnapshotFixturePaths;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    fixtures = writeFixturesToTmp(
      SNAPSHOT_TIMESTAMP,
      [
        { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
        { amount: '0.5', assetIdentifier: 'BTC', category: 'asset', usdValue: '30000' },
        { amount: '500', assetIdentifier: 'USD', category: 'asset', usdValue: '500' },
      ],
      [
        { location: 'blockchain', usdValue: '50000' },
        { location: 'total', usdValue: '50500' },
      ],
    );
  });

  test.afterAll(async () => {
    fixtures?.cleanup();
    await cleanupContext(ctx);
  });

  test('imports a snapshot via the UI and re-logs in', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    await dashboard.openSnapshotMenu();
    const importDialog = await dashboard.openImportSnapshotDialog();
    await importDialog.uploadBalanceCsv(fixtures.balancesPath);
    await importDialog.uploadLocationCsv(fixtures.locationsPath);
    await importDialog.import();

    // Auto-logout fires ~3s after a successful import; the most reliable
    // signal that we're back at the login screen is the username field.
    // We call `login()` directly rather than `relogin()` because the auto-
    // logout has already detached the session — `relogin()` would try to
    // click a logout button that no longer exists.
    await ctx.sharedPage.locator('[data-cy=username-input]').waitFor({ state: 'visible', timeout: 10_000 });
    await ctx.app.login(ctx.username);

    await ctx.sharedPage.locator('[data-testid=net-worth-chart]').waitFor({ state: 'visible' });
  });

  test('edits a balance row and a location row', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    const exportDialog = await dashboard.openSnapshotDialogAt();
    const editDialog = await exportDialog.openEdit();

    await editDialog.editBalanceRow('ETH', '12.5');
    await editDialog.next();

    await editDialog.editLocationRow('blockchain', '40000');
    await editDialog.next();

    await editDialog.complete();

    // Use the page's request context so the GET shares the browser session
    // (the test-level `request` fixture lost its cookies during the re-login).
    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, SNAPSHOT_TIMESTAMP);
    const eth = snapshot.balances_snapshot.find(b => b.asset_identifier === 'ETH');
    const blockchain = snapshot.location_data_snapshot.find(l => l.location === 'blockchain');
    expect(eth?.amount).toBe('12.5');
    expect(blockchain?.usd_value).toBe('40000');
  });

  test('exports the snapshot zip', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    const exportDialog = await dashboard.openSnapshotDialogAt();
    const download = await exportDialog.download();
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();
    const stats = fs.statSync(downloadPath);
    expect(stats.size).toBeGreaterThan(0);
  });
});
