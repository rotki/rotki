import { expect, type Locator, type Page } from '@playwright/test';
import { TIMEOUT_MEDIUM } from '../helpers/constants';

/**
 * Addressing, reading and acting on the rows of the history events table.
 *
 * Split out of `HistoryEventsPage` because it is one concern with one rule behind it: **a row is
 * named by the event it stands for, never by its position**. The table sorts timestamp DESC and
 * re-renders on every write, so an index resolved before a mutation names a different event after
 * it. That is not a stylistic preference — it is how the edit action ends up clicking the wrong
 * row, and how an assertion ends up reading one.
 */
export class HistoryEventRows {
  constructor(private readonly page: Page) {}

  async countEvents(): Promise<number> {
    return this.page.locator('[data-testid=history-event-row]').count();
  }

  async countSwaps(): Promise<number> {
    return this.page.locator('[data-testid=history-event-swap]').count();
  }

  async countMovements(): Promise<number> {
    return this.page.locator('[data-testid=history-event-movement]').count();
  }

  /** A row pinned to one event id — the only handle a re-sort cannot invalidate. */
  byId(eventId: string): Locator {
    return this.page.locator(`[data-event-id="${eventId}"]`);
  }

  /** The event id of the first row matching `rowSelector`. */
  async idOfFirst(rowSelector: string): Promise<string> {
    const id = await this.page.locator(rowSelector).first().getAttribute('data-event-id');
    expect(id, `${rowSelector} carries no data-event-id`).toBeTruthy();
    return id ?? '';
  }

  /**
   * The first row matching `rowSelector`, pinned to the event it stands for right now.
   *
   * Resolve this once, before anything that mutates the list, and address the row through the
   * result from then on.
   */
  async first(rowSelector: string): Promise<Locator> {
    return this.byId(await this.idOfFirst(rowSelector));
  }

  async expectTypeLabel(row: Locator, expected: string): Promise<void> {
    await expect(row.locator('[data-testid=event-type]')).toContainText(expected, { timeout: TIMEOUT_MEDIUM });
  }

  async expectNotes(row: Locator, expected: string): Promise<void> {
    await expect(row.locator('[data-testid=event-notes]')).toContainText(expected, { timeout: TIMEOUT_MEDIUM });
  }

  async expectAmount(row: Locator, expected: string): Promise<void> {
    await expect(row.locator('[data-testid=event-amount]').first()).toContainText(expected, { timeout: TIMEOUT_MEDIUM });
  }

  /**
   * Opens the edit dialog for an already-resolved row.
   *
   * The edit button is only rendered for rows that may be edited (`hideEditAction` hides it for a
   * swap sub-event and for a movement fee), so waiting on it against a position blocks for the
   * whole timeout once the list has moved such an event into that slot.
   */
  async edit(row: Locator): Promise<void> {
    await row.hover();
    await row.locator('[data-testid=row-edit]').click();
    await this.page.locator('[data-testid=bottom-dialog]').waitFor({ state: 'visible' });
  }

  async delete(row: Locator): Promise<void> {
    await row.hover();
    await row.locator('[data-testid=row-delete]').click();
    const dialog = this.page.locator('[data-testid=confirm-dialog]');
    await dialog.locator('[data-testid=button-confirm]').click();
    await dialog.waitFor({ state: 'detached', timeout: TIMEOUT_MEDIUM });
  }
}
