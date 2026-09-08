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

/**
 * Seeds one row of every purgeable category for the exchange under test.
 *
 * @remarks
 * The base timestamp is a minute in the past, so the purge endpoint's `to_timestamp = now()`
 * filter takes the rows in. Each helper stamps its `unique_id` from that timestamp, which is what
 * lets a reseed after a purge produce fresh rows rather than collide with the purged ones.
 */
async function seedAllCategories(request: Parameters<typeof apiSeedSwap>[0]): Promise<void> {
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

  /**
   * Returns the exchange to the full seeded set, whatever the previous test purged.
   *
   * @remarks
   * The purge runs before the reseed rather than after each test, so a test that failed partway
   * cannot leave rows behind that the next one would then count. Every test therefore starts from
   * the same known set, and the counts it asserts are the seeding's, not the previous test's.
   */
  async function resetToSeededState(request: Parameters<typeof apiSeedSwap>[0]): Promise<void> {
    await apiPurgeExchangeData(request, LOCATION, 'all');
    await seedAllCategories(request);
  }

  test.beforeEach(async ({ request }) => {
    await resetToSeededState(request);
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
