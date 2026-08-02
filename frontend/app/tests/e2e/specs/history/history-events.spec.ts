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
import { seedEvmTransaction, seedHistoricPrices } from '../../helpers/seed-db';
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
    .locator('[data-cy=history-event-row], [data-cy=history-event-movement]')
    .filter({ hasText: assetMovementEventFixture.notes });
}

test.describe.serial('history events', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;

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
    await page.openAddDialog();
    await page.selectEntryType('history event');
    await page.fillOnlineEventForm(onlineEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    await page.verifyEventTypeLabel('[data-cy=history-event-row]', 0, 'Airdrop');
    await page.verifyEventAmount('[data-cy=history-event-row]', 0, onlineEventFixture.amount);
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, onlineEventFixture.notes);
  });

  test('edit online history event', async () => {
    const updatedAmount = '2.5';
    const updatedNotes = 'Updated online event notes';

    await page.editEvent('[data-cy=history-event-row]', 0);

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);
    await ctx.sharedPage.locator('[data-cy=notes] textarea:not([aria-hidden])').clear();
    await ctx.sharedPage.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(updatedNotes);

    await page.saveForm();

    await page.verifyEventAmount('[data-cy=history-event-row]', 0, updatedAmount);
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, updatedNotes);
  });

  test('add swap event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('swap event');
    await page.fillSwapEventForm(swapEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    // Verify the swap row shows the spend asset amount
    const swapRow = ctx.sharedPage.locator('[data-cy=history-event-swap]').first();
    const assets = swapRow.locator('[data-cy=event-asset]');
    await expect(assets.first()).toBeVisible();
  });

  test('edit swap event', async () => {
    const updatedReceiveAmount = '3500';

    await page.editEvent('[data-cy=history-event-swap]', 0);

    await ctx.sharedPage.locator('[data-cy=receive-amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=receive-amount] input').fill(updatedReceiveAmount);

    await page.saveForm();

    // Verify the swap still exists after edit
    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('delete fee sub-event from online swap', async () => {
    // The swap created earlier has 3 sub-events: spend, receive, fee.
    // Expand it, delete the fee, and verify the swap group survives.
    const rowsBeforeExpand = await page.getExpandedEventRows();
    await page.expandSwap(0);

    await expect(async () => {
      const rows = await page.getExpandedEventRows();
      expect(rows).toBeGreaterThanOrEqual(rowsBeforeExpand + 3);
    }).toPass({ timeout: 10000 });

    // An expanded swap renders its collapse header instead of a swap row, so it drops out of
    // `getSwapRows` entirely while remaining a swap group. Asserted here so the difference is
    // pinned at the point it is created, rather than only mattering in `delete swap event`.
    expect(await page.getSwapGroups()).toBeGreaterThan(await page.getSwapRows());

    const rowsBefore = await page.getExpandedEventRows();

    // The fee is the 3rd sub-event (index 2) within the expanded swap rows.
    await page.deleteSubEvent(2);

    await expect(async () => {
      const rowsAfter = await page.getExpandedEventRows();
      expect(rowsAfter).toBe(rowsBefore - 1);
    }).toPass({ timeout: 10000 });

    // The swap group should still exist (spend + receive remain)
    await expect(async () => {
      const swaps = await page.getSwapRows();
      const expandedRows = await page.getExpandedEventRows();
      expect(swaps + expandedRows).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('add asset movement event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('asset movement event');
    await page.fillAssetMovementForm(assetMovementEventFixture);
    await page.saveForm();

    // Wait for the deposit itself. A row count cannot serve as the gate here: the swap expanded by
    // the previous test leaves its sub-events in the table under the same `history-event-row`
    // selector, so any `>= n` guard is already satisfied before this event arrives.
    await expect(assetMovementRow(ctx)).toHaveCount(1);
  });

  test('edit asset movement event', async () => {
    const updatedAmount = '0.75';

    // Anchor on the deposit's notes rather than on a row index. The movement sorts to the top of the
    // table (it is the newest timestamp), so every index shifts by one the moment it renders, and an
    // index picked before that would land on a swap sub-event, which carries no edit action.
    const row = assetMovementRow(ctx);
    await row.hover();
    await row.locator('[data-cy=row-edit]').click();
    await ctx.sharedPage.locator('[data-cy=bottom-dialog]').waitFor({ state: 'visible' });

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);

    await page.saveForm();

    await expect(row.locator('[data-cy=event-amount]').first()).toContainText(updatedAmount);
  });

  test('delete history event', async () => {
    const eventsBefore = await page.getEventRows();
    const swapsBefore = await page.getSwapRows();
    const movementsBefore = await page.getMovementRows();
    const totalBefore = eventsBefore + swapsBefore + movementsBefore;

    // Delete the first regular event row (the online event)
    if (eventsBefore > 0) {
      await page.deleteEvent('[data-cy=history-event-row]', 0);

      await expect(async () => {
        const eventsAfter = await page.getEventRows();
        const swapsAfter = await page.getSwapRows();
        const movementsAfter = await page.getMovementRows();
        const totalAfter = eventsAfter + swapsAfter + movementsAfter;
        expect(totalAfter).toBeLessThan(totalBefore);
      }).toPass({ timeout: 10000 });
    }
  });

  test('add solana event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('solana event');
    await page.fillSolanaEventForm(solanaEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    await page.verifyEventTypeLabel('[data-cy=history-event-row]', 0, 'Airdrop');
    await page.verifyEventAmount('[data-cy=history-event-row]', 0, solanaEventFixture.amount);
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, solanaEventFixture.notes);
  });

  test('edit solana event', async () => {
    const updatedAmount = '5.0';
    const updatedNotes = 'Updated solana event notes';

    await page.editEvent('[data-cy=history-event-row]', 0);

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);
    await ctx.sharedPage.locator('[data-cy=notes] textarea:not([aria-hidden])').clear();
    await ctx.sharedPage.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(updatedNotes);

    await page.saveForm();

    await page.verifyEventAmount('[data-cy=history-event-row]', 0, updatedAmount);
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, updatedNotes);
  });

  test('add solana swap event', async () => {
    await waitForNoRunningTasks(ctx.sharedPage);
    await page.openAddDialog();
    await page.selectEntryType('solana swap event');
    await page.fillSolanaSwapEventForm(solanaSwapEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    const swapRow = ctx.sharedPage.locator('[data-cy=history-event-swap]').first();
    const assets = swapRow.locator('[data-cy=event-asset]');
    await expect(assets.first()).toBeVisible();
  });

  test('edit solana swap event', async () => {
    const updatedReceiveAmount = '75';

    await page.editEvent('[data-cy=history-event-swap]', 0);

    await ctx.sharedPage.locator('[data-cy=receive-amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=receive-amount] input').fill(updatedReceiveAmount);

    await page.saveForm();

    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('add eth block event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('eth block event');
    await page.fillEthBlockEventForm(ethBlockEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('edit eth block event', async () => {
    const updatedAmount = '0.1';

    await page.editEvent('[data-cy=history-event-row]', 0);

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);

    await page.saveForm();

    // Eth block events render the amount in the notes, not via event-amount
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, updatedAmount);
  });

  test('add eth withdrawal event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('eth withdrawal event');
    await page.fillEthWithdrawalEventForm(ethWithdrawalEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('edit eth withdrawal event', async () => {
    const updatedAmount = '16';

    await page.editEvent('[data-cy=history-event-row]', 0);

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);

    await page.saveForm();

    // Eth withdrawal events render the amount in the notes, not via event-amount
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, updatedAmount);
  });

  test('delete solana event', async () => {
    // Read the notes of the first event row so we can verify it's gone after deletion
    const firstRow = ctx.sharedPage.locator('[data-cy=history-event-row]').first();
    const notesBefore = await firstRow.locator('[data-cy=event-notes]').textContent();

    await page.deleteEvent('[data-cy=history-event-row]', 0);

    // Wait until the deleted event's notes are no longer the first row's notes
    await expect(async () => {
      const rows = ctx.sharedPage.locator('[data-cy=history-event-row]');
      const count = await rows.count();
      if (count === 0)
        return; // all event rows gone, deletion succeeded
      const currentNotes = await rows.first().locator('[data-cy=event-notes]').textContent();
      expect(currentNotes).not.toBe(notesBefore);
    }).toPass({ timeout: 10000 });
  });

  test('delete swap event', async () => {
    // Counted with `getSwapGroups`, not `getSwapRows`: an earlier test expands a swap and never
    // collapses it, and expansion is keyed by position, so this delete re-indexes the list and
    // flips that swap back to collapsed. Against `getSwapRows` the vanishing swap and the
    // reappearing one cancel out and the count sits still while the delete plainly worked.
    const swapsBefore = await page.getSwapGroups();
    expect(swapsBefore).toBeGreaterThan(0);

    await page.deleteEvent('[data-cy=history-event-swap]', 0);

    await expect(async () => {
      const swapsAfter = await page.getSwapGroups();
      expect(swapsAfter).toBeLessThan(swapsBefore);
    }).toPass({ timeout: 10000 });
  });
});

test.describe.serial('evm history events', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;

  test.beforeAll(async ({ browser, request }) => {
    ctx = await createLoggedInContext(browser, request, {
      seed: (username) => {
        // Historic prices go into the global DB, which is plain SQLite with no lock concerns. The
        // transactions go into the user DB, so they are written here, while the account is created
        // but logged back out, rather than afterwards.
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
    await page.openAddDialog();
    await page.selectEntryType('evm event');
    await page.fillEvmEventForm(evmEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    await page.verifyEventTypeLabel('[data-cy=history-event-row]', 0, 'Airdrop');
    await page.verifyEventAmount('[data-cy=history-event-row]', 0, evmEventFixture.amount);
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, evmEventFixture.notes);
  });

  test('edit evm event', async () => {
    const updatedAmount = '2.5';
    const updatedNotes = 'Updated evm event notes';

    await page.editEvent('[data-cy=history-event-row]', 0);

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);
    await ctx.sharedPage.locator('[data-cy=notes] textarea:not([aria-hidden])').clear();
    await ctx.sharedPage.locator('[data-cy=notes] textarea:not([aria-hidden])').fill(updatedNotes);

    await page.saveForm();

    await page.verifyEventAmount('[data-cy=history-event-row]', 0, updatedAmount);
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, updatedNotes);
  });

  test('add evm swap event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('evm swap event');
    await page.fillEvmSwapEventForm(evmSwapEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    const swapRow = ctx.sharedPage.locator('[data-cy=history-event-swap]').first();
    const assets = swapRow.locator('[data-cy=event-asset]');
    await expect(assets.first()).toBeVisible();
  });

  test('edit evm swap event', async () => {
    const updatedReceiveAmount = '3500';

    await page.editEvent('[data-cy=history-event-swap]', 0);

    await ctx.sharedPage.locator('[data-cy=receive-amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=receive-amount] input').fill(updatedReceiveAmount);

    await page.saveForm();

    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('add evm multi-asset swap with fees', async () => {
    await waitForNoRunningTasks(ctx.sharedPage);
    const swapsBefore = await page.getSwapRows();

    await page.openAddDialog();
    await page.selectEntryType('evm swap event');
    await page.fillEvmMultiSwapEventForm(evmMultiSwapEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getSwapRows();
      expect(count).toBeGreaterThan(swapsBefore);
    }).toPass({ timeout: 10000 });
  });

  test('delete extra sub-event from multi-asset swap', async () => {
    // The multi-asset swap has 2 spend + 2 receive + 2 fee = 6 sub-events.
    // It was added last so it has the most recent timestamp.
    // With descending sort it appears first (index 0).
    const rowsBeforeExpand = await page.getExpandedEventRows();
    await page.expandSwap(0);

    // Wait for the 6 sub-event rows to appear (on top of any existing event-rows)
    await expect(async () => {
      const rows = await page.getExpandedEventRows();
      expect(rows).toBeGreaterThanOrEqual(rowsBeforeExpand + 6);
    }).toPass({ timeout: 10000 });

    const rowsBefore = await page.getExpandedEventRows();

    // Delete the last fee sub-event (index 5 within the swap — the 6th expanded row).
    // The swap sub-events are the first event-rows on the page since this group is first.
    await page.deleteSubEvent(5);

    await expect(async () => {
      const rowsAfter = await page.getExpandedEventRows();
      expect(rowsAfter).toBe(rowsBefore - 1);
    }).toPass({ timeout: 10000 });

    // The swap group should still exist
    await expect(async () => {
      const swaps = await page.getSwapRows();
      // Swap rows are hidden when expanded, so check sub-events remain
      const expandedRows = await page.getExpandedEventRows();
      expect(swaps + expandedRows).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('add eth deposit event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('eth deposit event');
    await page.fillEthDepositEventForm(ethDepositEventFixture);
    await page.saveForm();

    await expect(async () => {
      const count = await page.getEventRows();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });
  });

  test('edit eth deposit event', async () => {
    const updatedAmount = '16';

    await page.editEvent('[data-cy=history-event-row]', 0);

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);

    await page.saveForm();

    // Eth deposit events render the amount in the notes, not via event-amount
    await page.verifyEventNotes('[data-cy=history-event-row]', 0, updatedAmount);
  });

  test('delete evm event', async () => {
    const eventsBefore = await page.getEventRows();

    await page.deleteEvent('[data-cy=history-event-row]', 0);

    await expect(async () => {
      const eventsAfter = await page.getEventRows();
      expect(eventsAfter).toBeLessThan(eventsBefore);
    }).toPass({ timeout: 10000 });
  });

  test('delete evm swap event', async () => {
    const swapsBefore = await page.getSwapRows();

    await page.deleteEvent('[data-cy=history-event-swap]', 0);

    await expect(async () => {
      const swapsAfter = await page.getSwapRows();
      expect(swapsAfter).toBeLessThan(swapsBefore);
    }).toPass({ timeout: 10000 });
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

    // Navigate to dashboard
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

  // Carried over from the TableFilter era, where editing an applied filter chip failed to
  // re-open its suggestions once the menu had fully closed. The pill bar's equivalent is
  // clicking a pill to re-open its value editor, and it must survive the editor closing in
  // between — that close-then-reopen is what the original bug broke.
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
