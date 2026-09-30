import type { SnapshotEditorPage } from '../../pages/snapshot-editor-page';
import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { apiGetNetValue, apiGetSnapshot, apiMarkSpam } from '../../helpers/snapshot-api';
import { type BalanceRow, type LocationRow, writeFixturesToTmp } from '../../helpers/snapshot-csv';
import { DashboardPage } from '../../pages/dashboard-page';
import { SnapshotListPage } from '../../pages/snapshot-list-page';

const DAY_SECONDS = 24 * 60 * 60;
const TODAY = Math.floor(Date.now() / 1000 / DAY_SECONDS) * DAY_SECONDS;
// One snapshot per case; all inside the fourteen days the net-value series covers.
const LOWERED_TIMESTAMP = TODAY - 7 * DAY_SECONDS;
const INFLATED_TIMESTAMP = TODAY - 8 * DAY_SECONDS;
const RECONCILE_TIMESTAMP = TODAY - 9 * DAY_SECONDS;
const NOT_SPAM_TIMESTAMP = TODAY - 10 * DAY_SECONDS;
const SPLIT_TIMESTAMP = TODAY - 11 * DAY_SECONDS;
const TYPO_TIMESTAMP = TODAY - 12 * DAY_SECONDS;
const TWO_SPAM_TIMESTAMP = TODAY - 13 * DAY_SECONDS;
const OVERDRAWN_TIMESTAMP = TODAY - 14 * DAY_SECONDS;

// A second spam token, with its own symbol so the banner can be read naming both.
const SECOND_SPAM_TOKEN = 'eip155:1/erc20:0x6982508145454Ce325dDbE47a25d4ec3d2311933';
const SECOND_SPAM_SYMBOL = 'PEPE';

// A spam token with a borrowed symbol, priced absurdly the way a spam oracle price inflates one.
const SPAM_TOKEN = 'eip155:1/erc20:0xfcaF0e4498E78d65526a507360F755178b804Ba8';
// The real token with that symbol, which is not marked as spam.
const REAL_TOKEN = 'eip155:1/erc20:0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE';
const TOKEN_SYMBOL = 'SHIB';
const INFLATED_VALUE = '1580000000000000000000000000000000';

const BLOCKCHAIN_VALUE = 51500;
const BANKS_VALUE = 1580;
const REAL_TOTAL = BLOCKCHAIN_VALUE + BANKS_VALUE;

const REAL_BALANCES: BalanceRow[] = [
  { amount: '10', assetIdentifier: 'ETH', category: 'asset', usdValue: '20000' },
  { amount: '0.5', assetIdentifier: 'BTC', category: 'asset', usdValue: '30000' },
  { amount: '1000', assetIdentifier: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', category: 'asset', usdValue: '1000' },
  { amount: '500', assetIdentifier: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F', category: 'asset', usdValue: '500' },
  { amount: '500', assetIdentifier: 'USD', category: 'asset', usdValue: '500' },
  { amount: '1000', assetIdentifier: 'EUR', category: 'asset', usdValue: '1080' },
];

/** The real holdings plus one token carrying the inflated value. */
function balancesWith(token: string, usdValue: string = INFLATED_VALUE): BalanceRow[] {
  return [...REAL_BALANCES, { amount: '500000', assetIdentifier: token, category: 'asset', usdValue }];
}

/** Lowered by hand around a modest spam value, with blockchain typed 80 short of the real holdings. */
const TYPO_SPAM_VALUE = '5000';
const TYPO_LOCATIONS: LocationRow[] = [
  { location: 'blockchain', usdValue: String(BLOCKCHAIN_VALUE - 80) },
  { location: 'banks', usdValue: String(BANKS_VALUE) },
  { location: 'total', usdValue: String(REAL_TOTAL - 80) },
];

/** What a user leaves behind by lowering the locations and the net value but keeping the inflated row. */
const LOWERED_LOCATIONS: LocationRow[] = [
  { location: 'blockchain', usdValue: String(BLOCKCHAIN_VALUE) },
  { location: 'banks', usdValue: String(BANKS_VALUE) },
  { location: 'total', usdValue: String(REAL_TOTAL) },
];

/** The snapshot as taken: the inflated value sits in the blockchain location and in the total. */
const INFLATED_LOCATIONS: LocationRow[] = [
  { location: 'blockchain', usdValue: (BigInt(INFLATED_VALUE) + BigInt(BLOCKCHAIN_VALUE)).toString() },
  { location: 'banks', usdValue: String(BANKS_VALUE) },
  { location: 'total', usdValue: (BigInt(INFLATED_VALUE) + BigInt(REAL_TOTAL)).toString() },
];

/** The inflated value spread over two locations, the way a token held on two venues ends up. */
const SPLIT_KRAKEN_SHARE = 580000000000000000000000000000000n;
const SPLIT_LOCATIONS: LocationRow[] = [
  { location: 'blockchain', usdValue: (BigInt(INFLATED_VALUE) - SPLIT_KRAKEN_SHARE + BigInt(BLOCKCHAIN_VALUE)).toString() },
  { location: 'kraken', usdValue: SPLIT_KRAKEN_SHARE.toString() },
  { location: 'banks', usdValue: String(BANKS_VALUE) },
  { location: 'total', usdValue: (BigInt(INFLATED_VALUE) + BigInt(REAL_TOTAL)).toString() },
];

test.describe.serial('removing a mispriced asset from a snapshot', () => {
  let ctx: SharedTestContext;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    await apiMarkSpam(ctx.sharedPage.request, [SPAM_TOKEN, SECOND_SPAM_TOKEN]);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  async function importSnapshot(timestamp: number, balances: BalanceRow[], locations: LocationRow[]): Promise<void> {
    const fixtures = writeFixturesToTmp(timestamp, balances, locations);
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
  }

  async function openEditor(timestamp: number): Promise<SnapshotEditorPage> {
    const list = new SnapshotListPage(ctx.sharedPage);
    await list.visit();
    return list.openEditor(timestamp);
  }

  /** The saved snapshot holds only the real rows, and the graph plots their sum. */
  async function expectCleaned(timestamp: number, token: string): Promise<void> {
    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, timestamp);
    expect(snapshot.balances_snapshot.map(item => item.asset_identifier)).not.toContain(token);
    expect(snapshot.balances_snapshot).toHaveLength(REAL_BALANCES.length);
    const locationValue = (location: string): number =>
      Number(snapshot.location_data_snapshot.find(item => item.location === location)?.usd_value);
    expect(locationValue('blockchain')).toBe(BLOCKCHAIN_VALUE);
    expect(locationValue('banks')).toBe(BANKS_VALUE);
    expect(locationValue('total')).toBe(REAL_TOTAL);

    const netValue = await apiGetNetValue(ctx.sharedPage.request);
    expect(netValue.get(timestamp)).toBe(REAL_TOTAL);
  }

  test('removes the spam balance behind a mismatch in one step', async () => {
    await importSnapshot(LOWERED_TIMESTAMP, balancesWith(SPAM_TOKEN), LOWERED_LOCATIONS);
    // The graph subtracts the ignored spam value from a total that no longer holds it.
    expect((await apiGetNetValue(ctx.sharedPage.request)).get(LOWERED_TIMESTAMP)).toBeLessThan(0);

    const editor = await openEditor(LOWERED_TIMESTAMP);
    await expect(editor.mismatchBanner).toBeVisible();
    await expect(editor.dirtyBadge).toBeHidden();
    await expect(editor.balanceDeleteButton('ETH')).toBeDisabled();
    await expect(editor.gapAssets).toHaveText(TOKEN_SYMBOL);

    await editor.removeGapRowsButton.click();

    await expect(editor.mismatchBanner).toBeHidden();
    await expect(editor.balanceDeleteButton('ETH')).toBeEnabled();
    await editor.save();
    await expectCleaned(LOWERED_TIMESTAMP, SPAM_TOKEN);
  });

  test('removes an asset that is not spam when it is the whole mismatch', async () => {
    await importSnapshot(NOT_SPAM_TIMESTAMP, balancesWith(REAL_TOKEN), LOWERED_LOCATIONS);

    const editor = await openEditor(NOT_SPAM_TIMESTAMP);
    await expect(editor.balanceDeleteButton('ETH')).toBeDisabled();
    await expect(editor.gapAssets).toHaveText(TOKEN_SYMBOL);

    await editor.removeGapRowsButton.click();

    await expect(editor.mismatchBanner).toBeHidden();
    await editor.save();
    await expectCleaned(NOT_SPAM_TIMESTAMP, REAL_TOKEN);
  });

  test('removes a spam balance the locations still hold', async () => {
    await importSnapshot(INFLATED_TIMESTAMP, balancesWith(SPAM_TOKEN), INFLATED_LOCATIONS);

    const editor = await openEditor(INFLATED_TIMESTAMP);
    await expect(editor.mismatchBanner).toBeHidden();

    await editor.showExcludedRows();
    // Only blockchain holds enough to absorb the removal, so the dialog preselects it.
    await editor.deleteBalanceRow(TOKEN_SYMBOL);

    await expect(editor.mismatchBanner).toBeHidden();
    await editor.save();
    await expectCleaned(INFLATED_TIMESTAMP, SPAM_TOKEN);
  });

  test('removes a spam balance spread over two locations without typing the shares', async () => {
    await importSnapshot(SPLIT_TIMESTAMP, balancesWith(SPAM_TOKEN), SPLIT_LOCATIONS);

    const editor = await openEditor(SPLIT_TIMESTAMP);
    await editor.showExcludedRows();
    // Kraken holds only spam, so it fills whole and blockchain gives up just the rest, keeping its real value.
    await editor.deleteBalanceRowFillingSplit(TOKEN_SYMBOL, ['kraken', 'blockchain']);

    await expect(editor.mismatchBanner).toBeHidden();
    await editor.save();
    await expectCleaned(SPLIT_TIMESTAMP, SPAM_TOKEN);
  });

  test('removes a spam balance when the typed totals are a little off and reconciles the rest', async () => {
    await importSnapshot(TYPO_TIMESTAMP, balancesWith(SPAM_TOKEN, TYPO_SPAM_VALUE), TYPO_LOCATIONS);

    const editor = await openEditor(TYPO_TIMESTAMP);
    await expect(editor.gapAssets).toHaveText(TOKEN_SYMBOL);
    await editor.removeGapRowsButton.click();

    // Only the 80 the user got wrong is left, and it is the reconcile's to place.
    await expect(editor.removeGapRowsButton).toBeHidden();
    await editor.reconcile('blockchain');
    await expect(editor.mismatchBanner).toBeHidden();

    await editor.save();
    await expectCleaned(TYPO_TIMESTAMP, SPAM_TOKEN);
  });

  test('removes several spam balances left out of the totals together', async () => {
    const balances: BalanceRow[] = [
      ...balancesWith(SPAM_TOKEN),
      { amount: '1000000', assetIdentifier: SECOND_SPAM_TOKEN, category: 'asset', usdValue: '2000000000000000000000000000000000' },
    ];
    await importSnapshot(TWO_SPAM_TIMESTAMP, balances, LOWERED_LOCATIONS);

    const editor = await openEditor(TWO_SPAM_TIMESTAMP);
    await expect(editor.gapAssets).toContainText(TOKEN_SYMBOL);
    await expect(editor.gapAssets).toContainText(SECOND_SPAM_SYMBOL);
    await editor.removeGapRowsButton.click();

    await expect(editor.mismatchBanner).toBeHidden();
    await editor.save();
    await expectCleaned(TWO_SPAM_TIMESTAMP, SPAM_TOKEN);
    const snapshot = await apiGetSnapshot(ctx.sharedPage.request, TWO_SPAM_TIMESTAMP);
    expect(snapshot.balances_snapshot.map(item => item.asset_identifier)).not.toContain(SECOND_SPAM_TOKEN);
  });

  test('points to the locations when none can absorb what the balances fall short by', async () => {
    const locations: LocationRow[] = [
      { location: 'blockchain', usdValue: '60000' },
      { location: 'banks', usdValue: '60000' },
      { location: 'total', usdValue: '120000' },
    ];
    await importSnapshot(OVERDRAWN_TIMESTAMP, REAL_BALANCES, locations);

    const editor = await openEditor(OVERDRAWN_TIMESTAMP);
    await expect(editor.mismatchBanner).toBeVisible();
    await expect(editor.noReconcileTarget).toBeVisible();
    await expect(editor.removeGapRowsButton).toBeHidden();
  });

  test('can still reconcile the difference first and then delete the spam balance', async () => {
    await importSnapshot(RECONCILE_TIMESTAMP, balancesWith(SPAM_TOKEN), LOWERED_LOCATIONS);

    const editor = await openEditor(RECONCILE_TIMESTAMP);
    await expect(editor.removeGapRowsButton).toBeVisible();

    await editor.reconcile('blockchain');
    await expect(editor.balanceDeleteButton('ETH')).toBeEnabled();

    await expect(editor.hiddenRowsChip).toBeVisible();
    await editor.revealHiddenRows();
    await editor.deleteBalanceRow(TOKEN_SYMBOL);

    await expect(editor.mismatchBanner).toBeHidden();
    await editor.save();
    await expectCleaned(RECONCILE_TIMESTAMP, SPAM_TOKEN);
  });
});
