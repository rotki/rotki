import { expect, test } from '@playwright/test';
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
import { cleanupContext, createLoggedInContext, type SharedTestContext } from '../../fixtures/test-fixtures';
import { waitForNoRunningTasks } from '../../helpers/api';
import { seedEvmTransaction, seedHistoricPrices } from '../../helpers/seed-db';
import { generateUsername } from '../../helpers/utils';
import { HistoryEventsPage } from '../../pages/history-events-page';
import { RotkiApp } from '../../pages/rotki-app';

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

  test('add asset movement event', async () => {
    await page.openAddDialog();
    await page.selectEntryType('asset movement event');
    await page.fillAssetMovementForm(assetMovementEventFixture);
    await page.saveForm();

    // Asset movements may show as matched movements or regular event rows
    await expect(async () => {
      const movements = await page.getMovementRows();
      const events = await page.getEventRows();
      expect(movements + events).toBeGreaterThanOrEqual(2);
    }).toPass({ timeout: 10000 });
  });

  test('edit asset movement event', async () => {
    const updatedAmount = '0.75';

    // Find the event that contains our deposit notes
    const movementRows = await page.getMovementRows();
    const eventRows = await page.getEventRows();

    if (movementRows > 0) {
      await page.editEvent('[data-cy=history-event-movement]', 0);
    }
    else if (eventRows > 0) {
      // The last event row should be the deposit event
      await page.editEvent('[data-cy=history-event-row]', eventRows - 1);
    }

    await ctx.sharedPage.locator('[data-cy=amount] input').clear();
    await ctx.sharedPage.locator('[data-cy=amount] input').fill(updatedAmount);

    await page.saveForm();

    if (movementRows > 0)
      await page.verifyEventAmount('[data-cy=history-event-movement]', 0, updatedAmount);
    else
      await page.verifyEventAmount('[data-cy=history-event-row]', eventRows - 1, updatedAmount);
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
    const swapsBefore = await page.getSwapRows();

    await page.deleteEvent('[data-cy=history-event-swap]', 0);

    await expect(async () => {
      const swapsAfter = await page.getSwapRows();
      expect(swapsAfter).toBeLessThan(swapsBefore);
    }).toPass({ timeout: 10000 });
  });
});

test.describe.serial('evm history events', () => {
  let ctx: SharedTestContext;
  let page: HistoryEventsPage;

  test.beforeAll(async ({ browser, request }) => {
    const username = generateUsername();

    const sharedContext = await browser.newContext();
    const sharedPage = await sharedContext.newPage();
    const app = new RotkiApp(sharedPage, request);
    await app.fasterLogin(username);

    // Seed historic prices into the global DB (plain SQLite, no lock concerns)
    seedHistoricPrices(TEST_PRICE_ENTRIES, TEST_EVENT_TIMESTAMP);

    // Seed EVM transactions while logged in (WAL mode allows concurrent writes)
    seedEvmTransaction(username, evmEventFixture.txRef);
    seedEvmTransaction(username, evmSwapEventFixture.txRef);
    seedEvmTransaction(username, evmMultiSwapEventFixture.txRef);
    seedEvmTransaction(username, ethDepositEventFixture.txHash);

    ctx = { sharedContext, sharedPage, sharedRequest: request, app, username };
    page = new HistoryEventsPage(sharedPage);
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
