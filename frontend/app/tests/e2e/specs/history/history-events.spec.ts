import { expect, type Locator } from '@playwright/test';
import {
  assetMovementEventFixture,
  ethBlockEventFixture,
  ethDepositEventFixture,
  ethWithdrawalEventFixture,
  evmEventFixture,
  evmMultiSwapEventFixture,
  evmSwapEventFixture,
  onlineEventFixture,
  solanaEventFixture,
  solanaSwapEventFixture,
  swapEventFixture,
  TEST_EVENT_TIMESTAMP,
  TEST_PRICE_ENTRIES,
} from '../../fixtures/history-events';
import { cleanupContext, createLoggedInContext, type SharedTestContext, test } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { TIMEOUT_MEDIUM } from '../../helpers/constants';
import { seedEvmTransaction, seedHistoricPrices } from '../../helpers/seed-db';
import { EVENT_ROW, MOVEMENT_ROW, SWAP_ROW } from '../../pages/history-event-rows';
import { HistoryEventsPage } from '../../pages/history-events-page';
import { PillFilterBar } from '../../pages/pill-filter-bar';
import { RotkiApp } from '../../pages/rotki-app';

/**
 * The asset movement renders either as a matched movement or as a regular event row depending on
 * whether it pairs with another movement, so both selectors are in play. Its notes are unique to
 * this fixture, which makes them a stable anchor across either rendering and across re-sorts.
 */
function assetMovementRow(ctx: SharedTestContext): Locator {
  return ctx.sharedPage
    .locator(`${EVENT_ROW}, ${MOVEMENT_ROW}`)
    .filter({ hasText: assetMovementEventFixture.notes });
}

test.describe.serial('history events', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;

  /**
   * The rows each `add` test created, pinned by event id and handed to the tests that edit and
   * delete them.
   *
   * A later test cannot re-find them with "the first row": the table sorts timestamp DESC and every
   * test adds to it, so which event sits on top changes under them, and the online event's own
   * deletion is what moves it. Naming the row here is also what makes the edit tests assert against
   * the event they mean rather than against whatever survived.
   */
  let onlineRow: Locator;
  let swapRow: Locator;
  let solanaRow: Locator;
  let solanaSwapRow: Locator;
  let blockRow: Locator;
  let withdrawalRow: Locator;

  test.beforeAll(async ({ browser, request }) => {
    seedHistoricPrices(TEST_PRICE_ENTRIES, TEST_EVENT_TIMESTAMP);
    ctx = await createLoggedInContext(browser, request);
    page = new HistoryEventsPage(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add online history event', async () => {
    await page.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    const before = await page.rows.idsOf(EVENT_ROW);

    await page.openAddDialog();
    await page.selectEntryType('history event');
    await page.fillOnlineEventForm(onlineEventFixture);
    await page.saveForm();

    onlineRow = await page.rows.waitForNewRow(before, EVENT_ROW);
    await page.rows.expectTypeLabel(onlineRow, 'Airdrop');
    await page.rows.expectAmount(onlineRow, onlineEventFixture.amount);
    await page.rows.expectNotes(onlineRow, onlineEventFixture.notes);
  });

  test('edit online history event', async () => {
    const updatedAmount = '2.5';
    const updatedNotes = 'Updated online event notes';

    const row = onlineRow;
    await page.rows.edit(row);

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').clear();
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(updatedNotes);

    await page.saveForm();

    await page.rows.expectAmount(row, updatedAmount);
    await page.rows.expectNotes(row, updatedNotes);
  });

  test('add swap event', async () => {
    const before = await page.rows.idsOf(SWAP_ROW);

    await page.openAddDialog();
    await page.selectEntryType('swap event');
    await page.fillSwapEventForm(swapEventFixture);
    await page.saveForm();

    swapRow = await page.rows.waitForNewRow(before, SWAP_ROW);

    // Verify the swap row shows the spend asset amount
    await expect(swapRow.locator('[data-testid=event-asset]').first()).toBeVisible();
  });

  test('edit swap event', async () => {
    const updatedReceiveAmount = '3500';

    // A swap renders spend then receive, so the second amount is the one this edit changes.
    const receiveAmount = swapRow.locator('[data-testid=event-amount]').nth(1);
    const before = await receiveAmount.textContent();

    await page.rows.edit(swapRow);

    await ctx.sharedPage.locator('[data-testid=sub-event-amount][data-key=receive] input').clear();
    await ctx.sharedPage.locator('[data-testid=sub-event-amount][data-key=receive] input').fill(updatedReceiveAmount);

    await page.saveForm();

    await expect.poll(async () => receiveAmount.textContent(), { timeout: TIMEOUT_MEDIUM }).not.toBe(before);
  });

  test('delete the fee sub-event of the online swap, leaving its spend and receive', async () => {
    const rowsBeforeExpand = await page.getExpandedEventRows();
    await page.rows.expand(swapRow);

    await expect(async () => {
      const rows = await page.getExpandedEventRows();
      expect(rows).toBeGreaterThanOrEqual(rowsBeforeExpand + 3);
    }).toPass({ timeout: 10000 });

    const rowsBefore = await page.getExpandedEventRows();

    // The fee is the 3rd sub-event (index 2) within the expanded swap rows.
    await page.deleteSubEvent(2);

    await expect(async () => {
      const rowsAfter = await page.getExpandedEventRows();
      expect(rowsAfter).toBe(rowsBefore - 1);
    }).toPass({ timeout: 10000 });

    // The swap group should still exist (spend + receive remain)
    await expect(async () => {
      const swaps = await page.rows.countSwaps();
      const expandedRows = await page.getExpandedEventRows();
      expect(swaps + expandedRows).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('add asset movement event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('asset movement event');
    await page.fillAssetMovementForm(assetMovementEventFixture);
    await page.saveForm();

    // A row count cannot gate this: the previous test's expanded sub-events share the selector.
    await expect(assetMovementRow(ctx)).toHaveCount(1);
  });

  test('edit asset movement event', async () => {
    const updatedAmount = '0.75';

    // Anchored on the notes: the movement sorts to the top and shifts every index by one.
    const row = assetMovementRow(ctx);
    await row.hover();
    await row.locator('[data-testid=row-edit]').click();
    await ctx.sharedPage.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);

    await page.saveForm();

    await expect(row.locator('[data-testid=event-amount]').first()).toContainText(updatedAmount);
  });

  test('delete the named history event, since a row total cannot say which row went', async () => {
    await page.rows.delete(onlineRow);

    await expect(onlineRow).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  });

  test('add solana event', async () => {
    const before = await page.rows.idsOf(EVENT_ROW);

    await page.openAddDialog();
    await page.selectEntryType('solana event');
    await page.fillSolanaEventForm(solanaEventFixture);
    await page.saveForm();

    solanaRow = await page.rows.waitForNewRow(before, EVENT_ROW);
    await page.rows.expectTypeLabel(solanaRow, 'Airdrop');
    await page.rows.expectAmount(solanaRow, solanaEventFixture.amount);
    await page.rows.expectNotes(solanaRow, solanaEventFixture.notes);
  });

  test('edit solana event', async () => {
    const updatedAmount = '5.0';
    const updatedNotes = 'Updated solana event notes';

    const row = solanaRow;
    await page.rows.edit(row);

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').clear();
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(updatedNotes);

    await page.saveForm();

    await page.rows.expectAmount(row, updatedAmount);
    await page.rows.expectNotes(row, updatedNotes);
  });

  test('add solana swap event', async () => {
    await waitForNoRunningTasks(ctx.sharedPage);
    const before = await page.rows.idsOf(SWAP_ROW);

    await page.openAddDialog();
    await page.selectEntryType('solana swap event');
    await page.fillSolanaSwapEventForm(solanaSwapEventFixture);
    await page.saveForm();

    solanaSwapRow = await page.rows.waitForNewRow(before, SWAP_ROW);
    await expect(solanaSwapRow.locator('[data-testid=event-asset]').first()).toBeVisible();
  });

  test('edit solana swap event', async () => {
    const updatedReceiveAmount = '75';

    const receiveAmount = solanaSwapRow.locator('[data-testid=event-amount]').nth(1);
    const before = await receiveAmount.textContent();

    await page.rows.edit(solanaSwapRow);

    await ctx.sharedPage.locator('[data-testid=sub-event-amount][data-key=receive] input').clear();
    await ctx.sharedPage.locator('[data-testid=sub-event-amount][data-key=receive] input').fill(updatedReceiveAmount);

    await page.saveForm();

    await expect.poll(async () => receiveAmount.textContent(), { timeout: TIMEOUT_MEDIUM }).not.toBe(before);
  });

  test('add eth block event', async () => {
    const before = await page.rows.idsOf(EVENT_ROW);

    await page.openAddDialog();
    await page.selectEntryType('eth block event');
    await page.fillEthBlockEventForm(ethBlockEventFixture);
    await page.saveForm();

    blockRow = await page.rows.waitForNewRow(before, EVENT_ROW);
  });

  test('edit eth block event', async () => {
    const updatedAmount = '0.1';

    const row = blockRow;
    await page.rows.edit(row);

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);

    await page.saveForm();

    // Eth block events render the amount in the notes, not via event-amount
    await page.rows.expectNotes(row, updatedAmount);
  });

  test('add eth withdrawal event', async () => {
    const before = await page.rows.idsOf(EVENT_ROW);

    await page.openAddDialog();
    await page.selectEntryType('eth withdrawal event');
    await page.fillEthWithdrawalEventForm(ethWithdrawalEventFixture);
    await page.saveForm();

    withdrawalRow = await page.rows.waitForNewRow(before, EVENT_ROW);
  });

  test('edit eth withdrawal event', async () => {
    const updatedAmount = '16';

    const row = withdrawalRow;
    await page.rows.edit(row);

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);

    await page.saveForm();

    // Eth withdrawal events render the amount in the notes, not via event-amount
    await page.rows.expectNotes(row, updatedAmount);
  });

  test('delete the named solana event, which a read-then-delete of the top row would fake', async () => {
    await page.rows.delete(solanaRow);

    await expect(solanaRow).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  });

  test('delete the solana swap, the online one being left expanded by an earlier test with no row actions on its header', async () => {
    await page.rows.delete(solanaSwapRow);

    await expect(solanaSwapRow).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  });
});

test.describe.serial('evm history events', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;

  /** The rows this block's `add` tests created — see the note on the block above. */
  let evmRow: Locator;
  let evmSwapRow: Locator;
  let multiSwapRow: Locator;
  let depositRow: Locator;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, {
      seed: (username) => {
        seedHistoricPrices(TEST_PRICE_ENTRIES, TEST_EVENT_TIMESTAMP);

        seedEvmTransaction(username, evmEventFixture.txRef);
        seedEvmTransaction(username, evmSwapEventFixture.txRef);
        seedEvmTransaction(username, evmMultiSwapEventFixture.txRef);
        seedEvmTransaction(username, ethDepositEventFixture.txHash);
      },
    });

    page = new HistoryEventsPage(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('add evm event', async () => {
    await page.visit();
    await waitForNoRunningTasks(ctx.sharedPage);
    const before = await page.rows.idsOf(EVENT_ROW);

    await page.openAddDialog();
    await page.selectEntryType('evm event');
    await page.fillEvmEventForm(evmEventFixture);
    await page.saveForm();

    evmRow = await page.rows.waitForNewRow(before, EVENT_ROW);
    await page.rows.expectTypeLabel(evmRow, 'Airdrop');
    await page.rows.expectAmount(evmRow, evmEventFixture.amount);
    await page.rows.expectNotes(evmRow, evmEventFixture.notes);
  });

  test('edit evm event', async () => {
    const updatedAmount = '2.5';
    const updatedNotes = 'Updated evm event notes';

    const row = evmRow;
    await page.rows.edit(row);

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').clear();
    await ctx.sharedPage.locator('[data-testid=notes] textarea:not([aria-hidden])').fill(updatedNotes);

    await page.saveForm();

    await page.rows.expectAmount(row, updatedAmount);
    await page.rows.expectNotes(row, updatedNotes);
  });

  test('add evm swap event', async () => {
    const before = await page.rows.idsOf(SWAP_ROW);

    await page.openAddDialog();
    await page.selectEntryType('evm swap event');
    await page.fillEvmSwapEventForm(evmSwapEventFixture);
    await page.saveForm();

    evmSwapRow = await page.rows.waitForNewRow(before, SWAP_ROW);
    await expect(evmSwapRow.locator('[data-testid=event-asset]').first()).toBeVisible();
  });

  test('edit evm swap event', async () => {
    const updatedReceiveAmount = '3500';

    const receiveAmount = evmSwapRow.locator('[data-testid=event-amount]').nth(1);
    const before = await receiveAmount.textContent();

    await page.rows.edit(evmSwapRow);

    await ctx.sharedPage.locator('[data-testid=sub-event-amount][data-key=receive] input').clear();
    await ctx.sharedPage.locator('[data-testid=sub-event-amount][data-key=receive] input').fill(updatedReceiveAmount);

    await page.saveForm();

    await expect.poll(async () => receiveAmount.textContent(), { timeout: TIMEOUT_MEDIUM }).not.toBe(before);
  });

  test('add evm multi-asset swap with fees', async () => {
    await waitForNoRunningTasks(ctx.sharedPage);
    const before = await page.rows.idsOf(SWAP_ROW);

    await page.openAddDialog();
    await page.selectEntryType('evm swap event');
    await page.fillEvmMultiSwapEventForm(evmMultiSwapEventFixture);
    await page.saveForm();

    multiSwapRow = await page.rows.waitForNewRow(before, SWAP_ROW);
  });

  test('delete a sub-event of the multi-asset swap, whose six sort first on the newest timestamp', async () => {
    const rowsBeforeExpand = await page.getExpandedEventRows();
    await page.rows.expand(multiSwapRow);

    // Wait for the 6 sub-event rows to appear (on top of any existing event-rows)
    await expect(async () => {
      const rows = await page.getExpandedEventRows();
      expect(rows).toBeGreaterThanOrEqual(rowsBeforeExpand + 6);
    }).toPass({ timeout: 10000 });

    const rowsBefore = await page.getExpandedEventRows();

    // The last fee sub-event, sixth of the six this group renders first on the page.
    await page.deleteSubEvent(5);

    await expect(async () => {
      const rowsAfter = await page.getExpandedEventRows();
      expect(rowsAfter).toBe(rowsBefore - 1);
    }).toPass({ timeout: 10000 });

    // The swap group should still exist
    await expect(async () => {
      const swaps = await page.rows.countSwaps();
      // Swap rows are hidden when expanded, so check sub-events remain
      const expandedRows = await page.getExpandedEventRows();
      expect(swaps + expandedRows).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('add eth deposit event', async () => {
    const before = await page.rows.idsOf(EVENT_ROW);

    await page.openAddDialog();
    await page.selectEntryType('eth deposit event');
    await page.fillEthDepositEventForm(ethDepositEventFixture);
    await page.saveForm();

    depositRow = await page.rows.waitForNewRow(before, EVENT_ROW);
  });

  test('edit eth deposit event', async () => {
    const updatedAmount = '16';

    const row = depositRow;
    await page.rows.edit(row);

    await ctx.sharedPage.locator('[data-testid=amount] input').clear();
    await ctx.sharedPage.locator('[data-testid=amount] input').fill(updatedAmount);

    await page.saveForm();

    // Eth deposit events render the amount in the notes, not via event-amount
    await page.rows.expectNotes(row, updatedAmount);
  });

  test('the row action on the only event of a decoded evm transaction ignores it rather than deleting, since a delete would come back with the transaction', async () => {
    const ignored = ctx.sharedPage.locator('[data-testid=ignored-in-accounting]');
    await expect(ignored).toHaveCount(0);

    await page.rows.delete(evmRow);

    await expect(ignored).toHaveCount(1, { timeout: TIMEOUT_MEDIUM });
    await expect(evmRow).toHaveCount(1);
  });

  test('delete the evm swap while the multi-asset swap stays expanded, its header offering no actions', async () => {
    await page.rows.delete(evmSwapRow);

    await expect(evmSwapRow).toHaveCount(0, { timeout: TIMEOUT_MEDIUM });
  });
});

test.describe.serial('history event filter persistence', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request);
    page = new HistoryEventsPage(ctx.sharedPage);
  });

  test.afterAll(async () => {
    await cleanupContext(ctx);
  });

  test('event_subtype=none filter persists after navigation', async () => {
    await ctx.app.checkGetPremiumButton();
    await page.visit();
    await waitForNoRunningTasks(ctx.sharedPage);

    // Apply event_type and event_subtype filters
    await page.applyTableFilter('eventTypes', 'receive');
    await page.applyTableFilter('eventSubtypes', 'none');

    // Verify filters are in the URL
    await expect(async () => {
      const url = ctx.sharedPage.url();
      expect(url).toContain('eventTypes=receive');
      expect(url).toContain('eventSubtypes=none');
    }).toPass({ timeout: 5000 });

    await RotkiApp.navigateTo(ctx.sharedPage, 'dashboard');
    await expect(async () => {
      expect(ctx.sharedPage.url()).toContain('/dashboard');
    }).toPass({ timeout: 10000 });

    // Navigate back to history events
    await page.visit();
    await waitForNoRunningTasks(ctx.sharedPage);

    // Verify both filters are restored in the URL
    await expect(async () => {
      const url = ctx.sharedPage.url();
      expect(url).toContain('eventTypes=receive');
      expect(url).toContain('eventSubtypes=none');
    }).toPass({ timeout: 10000 });
  });

  // Carried over from TableFilter, where a chip's suggestions never reopened once fully closed.
  test('clicking a pill reopens its value editor', async () => {
    await page.visit();
    await waitForNoRunningTasks(ctx.sharedPage);

    const bar = new PillFilterBar(ctx.sharedPage);
    await page.applyTableFilter('eventTypes', 'receive');

    for (let attempt = 0; attempt < 2; attempt++) {
      await bar.pill('eventTypes').click();
      await expect(ctx.sharedPage.locator('[data-testid=value-select-search]')).toBeVisible();
      await bar.closeEditor();
    }
  });
});
