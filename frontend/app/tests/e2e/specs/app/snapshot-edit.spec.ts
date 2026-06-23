import fs from 'node:fs';
import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { seedHistoricPrices } from '../../helpers/seed-db';
import { apiGetSnapshot } from '../../helpers/snapshot-api';
import { type SnapshotFixturePaths, writeFixturesToTmp } from '../../helpers/snapshot-csv';
import { DashboardPage } from '../../pages/dashboard-page';
import { SnapshotListPage } from '../../pages/snapshot-list-page';

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
      // Locations must reconcile with the balances total (50500), otherwise the
      // editor loads with a sum-mismatch and locks balance editing.
      [
        { location: 'blockchain', usdValue: '50500' },
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

  test('locks balance editing on a sum-mismatch and reconciles', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    const editor = await dashboard.openSnapshotEditorAt();

    // Push a location out of sync with the balances total to force a mismatch.
    await editor.editLocationRow('blockchain', '99999');
    await expect(editor.mismatchBanner).toBeVisible();
    // Balance editing is locked until the mismatch is reconciled.
    await expect(editor.balanceEditButton('ETH')).toBeDisabled();

    await editor.reconcile();
    await expect(editor.mismatchBanner).toBeHidden();
    await expect(editor.balanceEditButton('ETH')).toBeEnabled();

    // Reconciling the self-inflicted mismatch restores the original values, so
    // nothing is left dirty and the persisted snapshot is untouched downstream.
    await expect(editor.dirtyBadge).toBeHidden();
  });

  test('discards unsaved edits via the dirty-changes flow', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    const editor = await dashboard.openSnapshotEditorAt();

    await editor.editBalanceRow('ETH', '99');
    await expect(editor.dirtyBadge).toBeVisible();
    await editor.discard();
    await expect(editor.dirtyBadge).toBeHidden();

    // Nothing was saved: the imported amount (10) is untouched.
    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, SNAPSHOT_TIMESTAMP);
    expect(snapshot.balances_snapshot.find(b => b.asset_identifier === 'ETH')?.amount).toBe('10');
  });

  test('deletes a balance row and reconciles the total', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    const editor = await dashboard.openSnapshotEditorAt();

    // The sole location (blockchain) is auto-attributed the removal.
    await editor.deleteBalanceRow('USD');
    await editor.save();

    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, SNAPSHOT_TIMESTAMP);
    expect(snapshot.balances_snapshot.find(b => b.asset_identifier === 'USD')).toBeUndefined();
    expect(snapshot.balances_snapshot.find(b => b.asset_identifier === 'ETH')).toBeDefined();
    // Removing USD (500) leaves balances (50000) and the recomputed total in sync.
    expect(snapshot.location_data_snapshot.find(l => l.location === 'total')?.usd_value).toBe('50000');
  });

  test('edits a balance row and a location row', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    const editor = await dashboard.openSnapshotEditorAt();

    await editor.editBalanceRow('ETH', '12.5');
    await editor.editLocationRow('blockchain', '40000');
    await editor.save();

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
    // The previous test left the browser on the editor page; return to the
    // dashboard so the chart is rendered again before clicking it.
    await dashboard.visit();
    const editor = await dashboard.openSnapshotEditorAt();
    const exportDialog = await editor.openExport();
    const download = await exportDialog.download();
    const downloadPath = await download.path();
    expect(downloadPath).toBeTruthy();
    const stats = fs.statSync(downloadPath);
    expect(stats.size).toBeGreaterThan(0);
  });

  test('opens the editor from the snapshot list', async () => {
    const list = new SnapshotListPage(ctx.sharedPage);
    await list.visit();
    expect(await list.hasSnapshot(SNAPSHOT_TIMESTAMP)).toBe(true);

    const editor = await list.openEditor(SNAPSHOT_TIMESTAMP);
    await editor.waitForLoaded();
  });

  test('deletes the snapshot from the list', async () => {
    const list = new SnapshotListPage(ctx.sharedPage);
    await list.visit();
    await list.deleteSnapshot(SNAPSHOT_TIMESTAMP);

    // The list is sourced from the net-value series, which the detail/list pages
    // refresh after a delete — so the row is gone without a manual reload.
    expect(await list.hasSnapshot(SNAPSHOT_TIMESTAMP)).toBe(false);
  });
});

// A separate snapshot (its own user) with TWO locations, so a balance removal can
// be split across them — the single-location suite above can't exercise this.
test.describe.serial('snapshot split editing', () => {
  let ctx: SharedTestContext;
  let fixtures: SnapshotFixturePaths;
  // A day before the other suite's snapshot; this user only ever has this one.
  const SPLIT_TIMESTAMP = SNAPSHOT_TIMESTAMP - 24 * 60 * 60;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    fixtures = writeFixturesToTmp(
      SPLIT_TIMESTAMP,
      [
        { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
        { amount: '0.5', assetIdentifier: 'BTC', category: 'asset', usdValue: '30000' },
      ],
      [
        { location: 'kraken', usdValue: '20000' },
        { location: 'blockchain', usdValue: '30000' },
        { location: 'total', usdValue: '50000' },
      ],
    );
  });

  test.afterAll(async () => {
    fixtures?.cleanup();
    await cleanupContext(ctx);
  });

  test('imports a two-location snapshot and re-logs in', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    await dashboard.openSnapshotMenu();
    const importDialog = await dashboard.openImportSnapshotDialog();
    await importDialog.uploadBalanceCsv(fixtures.balancesPath);
    await importDialog.uploadLocationCsv(fixtures.locationsPath);
    await importDialog.import();

    await ctx.sharedPage.locator('[data-cy=username-input]').waitFor({ state: 'visible', timeout: 10_000 });
    await ctx.app.login(ctx.username);
    await ctx.sharedPage.locator('[data-testid=net-worth-chart]').waitFor({ state: 'visible' });
  });

  test('deletes a balance by splitting it across locations', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    const editor = await dashboard.openSnapshotEditorAt();

    // Remove BTC (30000), drawing 10000 from kraken and 20000 from blockchain.
    await editor.deleteBalanceRowWithSplit('BTC', [
      { amount: '10000', location: 'kraken' },
      { amount: '20000', location: 'blockchain' },
    ]);
    await editor.save();

    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, SPLIT_TIMESTAMP);
    expect(snapshot.balances_snapshot.find(b => b.asset_identifier === 'BTC')).toBeUndefined();
    expect(snapshot.location_data_snapshot.find(l => l.location === 'kraken')?.usd_value).toBe('10000');
    expect(snapshot.location_data_snapshot.find(l => l.location === 'blockchain')?.usd_value).toBe('10000');
  });
});

// A separate snapshot (its own user) for adding a balance. The add form gates the
// value field on `:disabled="fetching"` while it fetches the asset's historic
// price, so we pre-seed a manual EUR->USD price into the global DB to make that
// fetch resolve instantly and auto-fill the USD value.
test.describe.serial('snapshot add balance', () => {
  let ctx: SharedTestContext;
  let fixtures: SnapshotFixturePaths;
  // Two days before the first suite's snapshot; this user only ever has this one.
  const ADD_TIMESTAMP = SNAPSHOT_TIMESTAMP - 2 * 24 * 60 * 60;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    // Manual (source_type 'A') EUR->USD price at the snapshot timestamp, so the
    // add form's historic-price fetch resolves and the value field unlocks.
    seedHistoricPrices([{ fromAsset: 'EUR', price: '1.1' }], ADD_TIMESTAMP);
    fixtures = writeFixturesToTmp(
      ADD_TIMESTAMP,
      [
        { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
      ],
      [
        { location: 'blockchain', usdValue: '20000' },
        { location: 'total', usdValue: '20000' },
      ],
    );
  });

  test.afterAll(async () => {
    fixtures?.cleanup();
    await cleanupContext(ctx);
  });

  test('imports a single-location snapshot and re-logs in', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    await dashboard.visit();
    await dashboard.openSnapshotMenu();
    const importDialog = await dashboard.openImportSnapshotDialog();
    await importDialog.uploadBalanceCsv(fixtures.balancesPath);
    await importDialog.uploadLocationCsv(fixtures.locationsPath);
    await importDialog.import();

    await ctx.sharedPage.locator('[data-cy=username-input]').waitFor({ state: 'visible', timeout: 10_000 });
    await ctx.app.login(ctx.username);
    await ctx.sharedPage.locator('[data-testid=net-worth-chart]').waitFor({ state: 'visible' });
  });

  test('adds a balance using a seeded historic price', async () => {
    const dashboard = new DashboardPage(ctx.sharedPage);
    const editor = await dashboard.openSnapshotEditorAt();

    // 100 EUR at the seeded 1.1 rate = 110 USD, attributed to the sole location.
    await editor.addBalance('EUR', '100', 'eur');
    await editor.save();

    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, ADD_TIMESTAMP);
    const eur = snapshot.balances_snapshot.find(b => b.asset_identifier === 'EUR');
    expect(eur?.amount).toBe('100');
    expect(eur?.usd_value).toBe('110');
    // The added value lands on the only location, keeping the total in sync.
    expect(snapshot.location_data_snapshot.find(l => l.location === 'blockchain')?.usd_value).toBe('20110');
    expect(snapshot.location_data_snapshot.find(l => l.location === 'total')?.usd_value).toBe('20110');
  });
});
