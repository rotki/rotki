import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import {
  apiCountExchangeEventsByCategory,
  apiPurgeExchangeData,
  apiSeedAssetMovement,
  apiSeedHistoryEvent,
  apiSeedSwap,
} from '../../helpers/exchange-api';
import { PurgeDataPage } from '../../pages/purge-data-page';

const LOCATION = 'kraken';

async function seedAllCategories(request: Parameters<typeof apiSeedSwap>[0]): Promise<void> {
  // Tests share a backend, so re-seeds run sequentially. The IDs embedded in
  // each helper's `unique_id`/`group_identifier` are stamped from the
  // timestamp, so every reseed creates fresh rows even after a prior purge.
  // Use a base timestamp safely in the past so the default
  // `to_timestamp = now()` query filter on the events endpoint includes them.
  const base = Date.now() - 60_000;
  await apiSeedSwap(request, { location: LOCATION, sequenceIndex: 0, timestampMs: base });
  await apiSeedAssetMovement(request, { location: LOCATION, sequenceIndex: 0, timestampMs: base + 1 });
  await apiSeedHistoryEvent(request, { location: LOCATION, sequenceIndex: 0, timestampMs: base + 2 });
}

test.describe.serial('exchange purge by category', () => {
  let ctx: SharedTestContext;
  let page: PurgeDataPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, { disableModules: true });
    page = new PurgeDataPage(ctx.sharedPage);
    await page.visit();
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test.beforeEach(async ({ request }) => {
    // Wipe-and-seed so each test starts from a known {1 trade, 1 movement, 1 other}.
    // Using the purge endpoint itself for cleanup keeps setup light and verifies
    // no test leaves residual state behind.
    await apiPurgeExchangeData(request, LOCATION, 'all');
    await seedAllCategories(request);
  });

  // A single seeded swap expands into spend+receive sub-events (entry_type
  // `swap event`), so the trade-bucket count is 2 per swap. Asset movements
  // and `history event` rows stay 1:1 with seeds.
  const seededCounts = { assetMovements: 1, other: 1, trades: 2 };

  test('purges only trades', async ({ request }) => {
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual(seededCounts);
    await page.purgeExchange('Kraken', 'Trades');
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual({
      assetMovements: 1,
      other: 1,
      trades: 0,
    });
  });

  test('purges only asset movements', async ({ request }) => {
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual(seededCounts);
    await page.purgeExchange('Kraken', 'Deposits / Withdrawals');
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual({
      assetMovements: 0,
      other: 1,
      trades: 2,
    });
  });

  test('purges only other events', async ({ request }) => {
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual(seededCounts);
    await page.purgeExchange('Kraken', 'Other events');
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual({
      assetMovements: 1,
      other: 0,
      trades: 2,
    });
  });

  test('purges everything', async ({ request }) => {
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual(seededCounts);
    await page.purgeExchange('Kraken', 'All');
    expect(await apiCountExchangeEventsByCategory(request, LOCATION)).toEqual({
      assetMovements: 0,
      other: 0,
      trades: 0,
    });
  });
});
