import { expect } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
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
  /* The ids in each helper's `unique_id` are stamped from the timestamp, so every reseed makes
     fresh rows even after a purge. In the past, so the endpoint's `to_timestamp = now()` filter
     includes them. */
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
    // Purging here starts every test from a known set and proves nothing was left behind.
    await apiPurgeExchangeData(request, LOCATION, 'all');
    await seedAllCategories(request);
  });

  // A swap expands into spend and receive, so a trade counts two; the others stay 1:1.
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
