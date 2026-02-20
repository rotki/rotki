import { expect, test } from '@playwright/test';
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { HistoryEventsPage } from '../../pages/history-events-page';
import { ImportPage } from '../../pages/import-page';

/**
 * Amount formatting notes:
 * Default settings: floatingPrecision=2, amountRoundingMode=ROUND_UP
 * - Values with >2 decimals are rounded up and prefixed with '<'
 *   e.g. 0.091 → "<0.10", 392.887 → "<392.89", 0.0513 → "<0.06"
 * - Values with ≤2 decimals display as-is: 5 → "5.00"
 */

test.describe.serial('csv import', () => {
  let ctx: SharedTestContext;
  let importPage: ImportPage;
  let historyPage: HistoryEventsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    importPage = new ImportPage(ctx.sharedPage);
    historyPage = new HistoryEventsPage(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('import rotki generic events', async () => {
    await importPage.visit();
    await importPage.selectSource('Custom');
    await importPage.importCsv('rotki_events', 'rotki_generic_events.csv');

    // Navigate to history and filter by coinbase (unique to this CSV: 0.091 BTC loss)
    await historyPage.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    await historyPage.applyTableFilter('location', 'coinbase');

    await expect(async () => {
      const count = await historyPage.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: TIMEOUT_MEDIUM });

    // 0.091 BTC → rounded up to 0.10 with '<' prefix
    await historyPage.verifyEventAmount('[data-cy=history-event-row]', 0, '0.10');
  });

  test('import rotki generic trades', async () => {
    await importPage.visit();
    await importPage.selectSource('Custom');
    await importPage.importCsv('rotki_trades', 'rotki_generic_trades.csv');

    // Navigate to history and filter by kraken (has LTC→BTC trade from this CSV)
    await historyPage.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    await historyPage.applyTableFilter('location', 'kraken');

    await expect(async () => {
      const count = await historyPage.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: TIMEOUT_MEDIUM });

    // 392.887 LTC → rounded up to 392.89 with '<' prefix
    await historyPage.verifyEventAmount('[data-cy=history-event-swap]', 0, '392.89');
  });

  test('import cointracking csv', async () => {
    await importPage.visit();
    await importPage.selectSource('Cointracking');
    await importPage.importCsv('cointracking', 'cointracking_trades_list.csv');

    // Navigate to history and filter by poloniex (unique: 5 XMR deposit from cointracking)
    await historyPage.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    await historyPage.applyTableFilter('location', 'poloniex');

    await expect(async () => {
      const count = await historyPage.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: TIMEOUT_MEDIUM });

    // 5.00 XMR — exact, no rounding needed
    await historyPage.verifyEventAmount('[data-cy=history-event-row]', 0, '5.00');
    await historyPage.verifyEventTypeLabel('[data-cy=history-event-row]', 0, 'Exchange deposit');
  });

  test('import nexo csv', async () => {
    await importPage.visit();
    await importPage.selectSource('Nexo');
    await importPage.importCsv('nexo', 'nexo.csv');

    // Navigate to history and filter by nexo (all nexo events have location=nexo)
    await historyPage.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    await historyPage.applyTableFilter('location', 'nexo');

    await expect(async () => {
      const count = await historyPage.getEventRows();
      const swaps = await historyPage.getSwapRows();
      expect(count + swaps).toBeGreaterThanOrEqual(5);
    }).toPass({ timeout: TIMEOUT_MEDIUM });

    // 5.37250072 NEXO fixed term interest (2024-12-28) → rounded up to 5.38 with '<' prefix
    const amountLocator = ctx.sharedPage.locator('[data-cy=event-amount]').filter({ hasText: '5.38' });
    await expect(amountLocator.first()).toBeVisible({ timeout: TIMEOUT_MEDIUM });
  });

  test('filter history events by location', async () => {
    await historyPage.visit();
    await waitForNoRunningTasks(ctx.sharedPage);

    // Apply location filter for binance (has USDT withdrawal from generic events + USDC→ETH swap from generic trades)
    await historyPage.applyTableFilter('location', 'binance');

    await expect(async () => {
      const rows = await historyPage.getEventRows();
      const swaps = await historyPage.getSwapRows();
      expect(rows + swaps).toBeGreaterThanOrEqual(2);
    }).toPass({ timeout: TIMEOUT_MEDIUM });

    // Verify the USDC→ETH swap exists: 1,875.64 USDC spend → rounded up to 1,875.64 (exact 2 decimals)
    await historyPage.verifyEventAmount('[data-cy=history-event-swap]', 0, '1,875.64');
  });
});
